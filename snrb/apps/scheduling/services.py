from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.billing.gateway.factory import get_payment_gateway
from apps.billing.models import Subscription, PaymentTransaction
from .models import Appointment
from .slot_lock import lock_slot, unlock_slot


class SchedulingService:
    """
    Business logic for scheduling appointments.
    """

    @staticmethod
    def book_subscription_appointment(customer_profile, barber, service, date_time):
        """
        Flow for active subscribers.
        1. Check active subscription and quota.
        2. Create appointment.
        3. Increment usage.
        """
        # 1. Validate subscription
        subscription = Subscription.objects.filter(
            customer=customer_profile,
            status=Subscription.Status.ACTIVE
        ).first()

        if not subscription:
            raise ValidationError("O cliente não possui uma assinatura ativa.")

        if subscription.plan.appointment_quota is not None:
            if subscription.appointments_used_this_period >= subscription.plan.appointment_quota:
                raise ValidationError("Cota de agendamentos mensais excedida.")

        # 2. Try to acquire Redis lock just to be safe from immediate double-click
        slot_str = date_time.strftime('%Y-%m-%dT%H:%M:%S')
        if not lock_slot(barber.id, slot_str, ttl=30):
            raise ValidationError("Horário está sendo reservado por outra pessoa.")

        try:
            # 3. Create confirmed appointment
            appointment = Appointment.objects.create(
                customer=customer_profile,
                barber=barber,
                service=service,
                date_time=date_time,
                end_time=date_time + timedelta(minutes=service.duration_minutes),
                status=Appointment.Status.CONFIRMED,
                payment_type=Appointment.PaymentType.SUBSCRIPTION
            )

            # 4. Increment usage
            subscription.appointments_used_this_period += 1
            subscription.save()

            return appointment
        finally:
            # We can release the lock since DB transaction is complete and 
            # our DB query for available slots will filter it out now.
            unlock_slot(barber.id, slot_str)


    @staticmethod
    def book_single_appointment(customer_profile, barber, service, date_time):
        """
        Flow for single booking (Avulso).
        1. Lock slot in Redis for 15 minutes.
        2. Create pending appointment.
        3. Create transaction (10% fee).
        4. Charge via gateway.
        """
        slot_str = date_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # 1. Lock slot for 15 minutes to allow payment
        if not lock_slot(barber.id, slot_str, ttl=900):
            raise ValidationError("Horário indisponível ou já em processo de pagamento.")

        try:
            # 2. Create pending appointment
            appointment = Appointment.objects.create(
                customer=customer_profile,
                barber=barber,
                service=service,
                date_time=date_time,
                end_time=date_time + timedelta(minutes=service.duration_minutes),
                status=Appointment.Status.PENDING_PAYMENT,
                payment_type=Appointment.PaymentType.SINGLE_PERCENTAGE
            )

            # 3. Create Transaction (10% fee)
            fee_amount = (service.price * Decimal('0.10')).quantize(Decimal('0.01'))
            
            transaction = PaymentTransaction.objects.create(
                customer=customer_profile,
                appointment=appointment,
                amount=fee_amount,
                fee_amount=fee_amount,
                transaction_type=PaymentTransaction.Type.RESERVATION_FEE
            )

            # 4. Charge Gateway
            gateway = get_payment_gateway()
            gw_txn_id = gateway.create_charge(
                amount=float(fee_amount),
                description=f"Taxa de Reserva - {service.name}",
                metadata={'appointment_id': appointment.id}
            )
            
            transaction.gateway_transaction_id = gw_txn_id
            transaction.save()

            return appointment
            
        except Exception as e:
            # If something fails, unlock slot
            unlock_slot(barber.id, slot_str)
            raise ValidationError(f"Erro ao processar agendamento avulso: {str(e)}")

    @staticmethod
    def cancel_appointment(appointment, user, reason=""):
        """
        Cancels an appointment. 
        If customer cancels late, it might become NO_SHOW or require manual refund.
        For simplicity, we mark it CANCELED and Barber decides on refunds.
        """
        if appointment.status in [Appointment.Status.CANCELED, Appointment.Status.REFUNDED, Appointment.Status.COMPLETED]:
            raise ValidationError("Agendamento já processado/cancelado.")

        appointment.status = Appointment.Status.CANCELED
        appointment.cancellation_reason = reason
        appointment.canceled_by = user.role
        appointment.save()

        # Free the slot if it was pending
        if appointment.status == Appointment.Status.PENDING_PAYMENT:
            slot_str = appointment.date_time.strftime('%Y-%m-%dT%H:%M:%S')
            unlock_slot(appointment.barber.id, slot_str)

    @staticmethod
    def approve_refund(appointment):
        """
        Barber approves a refund for a canceled reservation.
        """
        if appointment.payment_type != Appointment.PaymentType.SINGLE_PERCENTAGE:
            raise ValidationError("Somente reservas avulsas possuem taxa para reembolso.")
            
        transaction = appointment.payment_transactions.filter(
            transaction_type=PaymentTransaction.Type.RESERVATION_FEE,
            status=PaymentTransaction.Status.PAID
        ).first()

        if not transaction:
            raise ValidationError("Nenhuma taxa foi paga para este agendamento.")

        gateway = get_payment_gateway()
        gateway.refund_charge(transaction.gateway_transaction_id)
        
        transaction.status = PaymentTransaction.Status.REFUNDED
        transaction.save()
        
        appointment.status = Appointment.Status.REFUNDED
        appointment.save()

    @staticmethod
    def mark_no_show(appointment):
        """
        Customer did not show up. 10% fee is retained as penalty.
        """
        appointment.status = Appointment.Status.NO_SHOW
        appointment.save()
        
        transaction = appointment.payment_transactions.filter(
            transaction_type=PaymentTransaction.Type.RESERVATION_FEE,
            status=PaymentTransaction.Status.PAID
        ).first()
        
        if transaction:
            transaction.status = PaymentTransaction.Status.RETAINED_AS_FINE
            transaction.save()
