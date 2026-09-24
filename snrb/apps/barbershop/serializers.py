from rest_framework import serializers

from .models import Barber, Service, WorkSchedule


class BarberSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Barber
        fields = ('id', 'email', 'bio', 'is_active')


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ('id', 'name', 'duration_minutes', 'price', 'is_active')


class WorkScheduleSerializer(serializers.ModelSerializer):
    day_of_week_display = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = WorkSchedule
        fields = (
            'id', 'day_of_week', 'day_of_week_display', 'start_time', 'end_time',
            'break_start', 'break_end'
        )
