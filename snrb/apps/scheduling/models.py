from django.db import models

from apps.accounts.models import CustomerProfile
from apps.barbershop.models import Barber, Service


class Appointment(models.Model):
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'PENDING_PAYMENT', 'Pending Payment'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        CANCELED = 'CANCELED', 'Canceled'
        COMPLETED = 'COMPLETED', 'Completed'
        NO_SHOW = 'NO_SHOW', 'No Show'
        CANCELED_WITH_PENALTY = 'CANCELED_WITH_PENALTY', 'Canceled with Penalty'
        REFUNDED = 'REFUNDED', 'Refunded'

    class PaymentType(models.TextChoices):
        SUBSCRIPTION = 'SUBSCRIPTION', 'Subscription'
        SINGLE_PERCENTAGE = 'SINGLE_PERCENTAGE', 'Single Percentage'

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    barber = models.ForeignKey(
        Barber,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointments'
    )
    
    date_time = models.DateTimeField()
    end_time = models.DateTimeField(
        help_text="Calculated as date_time + service.duration_minutes"
    )
    
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT
    )
    payment_type = models.CharField(
        max_length=30,
        choices=PaymentType.choices
    )
    
    cancellation_reason = models.TextField(blank=True, null=True)
    canceled_by = models.CharField(max_length=50, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.full_name} with {self.barber.user.email} at {self.date_time}"
