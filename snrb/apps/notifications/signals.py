from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.scheduling.models import Appointment

@receiver(post_save, sender=Appointment)
def notify_barber_of_appointment(sender, instance, created, **kwargs):
    """
    Sends a WebSocket notification to the barber when an appointment is created or its status changes.
    """
    channel_layer = get_channel_layer()
    group_name = f'barber_{instance.barber.id}'
    
    event_type = 'created' if created else 'updated'
    
    message = {
        'event': event_type,
        'appointment_id': instance.id,
        'customer_name': instance.customer.full_name,
        'service': instance.service.name if instance.service else 'N/A',
        'date_time': instance.date_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'status': instance.status
    }

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'appointment_event',
            'message': message
        }
    )
