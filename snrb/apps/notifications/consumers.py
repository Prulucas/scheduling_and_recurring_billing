import json
from channels.generic.websocket import AsyncWebsocketConsumer

class BarberDashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # We assume the barber ID is passed in the URL or they are authenticated
        # For simplicity in this MVP, we'll grab barber_id from URL route kwargs
        self.barber_id = self.scope['url_route']['kwargs']['barber_id']
        self.group_name = f'barber_{self.barber_id}'

        # Join the barber's specific notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from room group
    async def appointment_event(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'appointment_event',
            'data': message
        }))
