from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scheduling.models import Appointment
from apps.billing.models import PaymentTransaction


class WebhookView(APIView):
    """
    Receives webhook events from the payment gateway.
    """
    authentication_classes = []  # Open endpoint, validate via signature in real scenarios
    permission_classes = []

    def post(self, request):
        event = request.data.get('event')
        transaction_id = request.data.get('transaction_id')
        
        if event == 'payment_confirmed':
            self.handle_payment_confirmed(transaction_id)
            
        elif event == 'payment_failed':
            self.handle_payment_failed(transaction_id)
            
        # Other events: subscription_renewed, subscription_canceled, etc.
        
        return Response({'status': 'received'}, status=status.HTTP_200_OK)

    def handle_payment_confirmed(self, transaction_id):
        # 1. Update Transaction status
        transaction = PaymentTransaction.objects.filter(gateway_transaction_id=transaction_id).first()
        if not transaction:
            return
            
        transaction.status = PaymentTransaction.Status.PAID
        transaction.save()
        
        # 2. If this is a reservation fee, confirm the appointment
        if transaction.transaction_type == PaymentTransaction.Type.RESERVATION_FEE and transaction.appointment:
            appointment = transaction.appointment
            appointment.status = Appointment.Status.CONFIRMED
            appointment.save()
            
            # NOTE: Unlock the Redis slot if we were keeping it just for checkout?
            # Actually, once confirmed, the slot is definitively taken in DB, 
            # so the Redis lock can just naturally expire or be deleted.
            from apps.scheduling.slot_lock import unlock_slot
            slot_str = appointment.date_time.strftime('%Y-%m-%dT%H:%M:%S')
            unlock_slot(appointment.barber.id, slot_str)
            
            # TODO (Phase 6): Dispatch WebSocket notification that appointment is confirmed!

    def handle_payment_failed(self, transaction_id):
        transaction = PaymentTransaction.objects.filter(gateway_transaction_id=transaction_id).first()
        if not transaction:
            return
            
        transaction.status = PaymentTransaction.Status.PENDING # Or FAILED
        transaction.save()
        
        # If reservation fee fails, cancel appointment
        if transaction.transaction_type == PaymentTransaction.Type.RESERVATION_FEE and transaction.appointment:
            appointment = transaction.appointment
            appointment.status = Appointment.Status.CANCELED
            appointment.cancellation_reason = "Payment failed"
            appointment.save()
            
            # Free up the slot
            from apps.scheduling.slot_lock import unlock_slot
            slot_str = appointment.date_time.strftime('%Y-%m-%dT%H:%M:%S')
            unlock_slot(appointment.barber.id, slot_str)
