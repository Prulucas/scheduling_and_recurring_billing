from django.db import models

from apps.accounts.models import CustomerProfile
from apps.scheduling.models import Appointment


class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    appointment_quota = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Number of appointments allowed per period. Null means unlimited."
    )
    interval = models.CharField(
        max_length=20,
        default='MONTHLY',
        choices=[('MONTHLY', 'Monthly')]
    )
    gateway_plan_id = models.CharField(
        max_length=100, blank=True, null=True,
        help_text="ID of the plan in the external payment gateway"
    )

    def __str__(self):
        return f"{self.name} - R${self.price}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        PAST_DUE = 'PAST_DUE', 'Past Due'
        CANCELED = 'CANCELED', 'Canceled'
        TRIALING = 'TRIALING', 'Trialing'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.RESTRICT,
        related_name='subscriptions'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE
    )
    
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    
    gateway_subscription_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    
    appointments_used_this_period = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.full_name} - {self.plan.name} ({self.status})"


class PaymentTransaction(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PAID = 'PAID', 'Paid'
        REFUNDED = 'REFUNDED', 'Refunded'
        RETAINED_AS_FINE = 'RETAINED_AS_FINE', 'Retained as Fine'

    class Type(models.TextChoices):
        SUBSCRIPTION_FEE = 'SUBSCRIPTION_FEE', 'Subscription Fee'
        RESERVATION_FEE = 'RESERVATION_FEE', 'Reservation Fee'
        REFUND = 'REFUND', 'Refund'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_transactions'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payment_transactions'
    )
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Gateway fee or specific reservation fee amount"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=Type.choices
    )
    
    gateway_transaction_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction {self.id} - R${self.amount} - {self.status}"
