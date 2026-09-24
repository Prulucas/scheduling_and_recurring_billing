from rest_framework import serializers
from .models import Appointment

class AppointmentSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    barber_email = serializers.CharField(source='barber.user.email', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)

    class Meta:
        model = Appointment
        fields = (
            'id', 'customer', 'customer_name', 'barber', 'barber_email', 
            'service', 'service_name', 'date_time', 'end_time', 
            'status', 'payment_type', 'cancellation_reason', 'canceled_by'
        )
        read_only_fields = ('end_time', 'status', 'payment_type', 'cancellation_reason', 'canceled_by', 'customer')


class CreateAppointmentSerializer(serializers.Serializer):
    barber_id = serializers.IntegerField()
    service_id = serializers.IntegerField()
    date_time = serializers.DateTimeField()
    payment_type = serializers.ChoiceField(choices=Appointment.PaymentType.choices)
