from django.conf import settings
from django.db import models


class Barber(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='barber_profile',
        limit_choices_to={'role': 'BARBER'}
    )
    bio = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Barber: {self.user.email}"


class Service(models.Model):
    name = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField(
        help_text="Duration of the service in minutes"
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - R${self.price}"


class WorkSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    barber = models.ForeignKey(
        Barber,
        on_delete=models.CASCADE,
        related_name='work_schedules'
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Optional break times (e.g., lunch)
    break_start = models.TimeField(blank=True, null=True)
    break_end = models.TimeField(blank=True, null=True)

    class Meta:
        unique_together = ('barber', 'day_of_week')

    def __str__(self):
        return f"{self.barber.user.email} - {self.get_day_of_week_display()}"
