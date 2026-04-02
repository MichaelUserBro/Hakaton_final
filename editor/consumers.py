import json
from channels.generic.websocket import AsyncWebsocketConsumer

class EditorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        from urllib.parse import parse_qs
        qs = parse_qs(self.scope['query_string'].decode())
        project_id = qs.get('project_id', ['global'])[0]

        self.room_group_name = f'editor_{project_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', {})
        msg_type = message.get('type', '')

        # Все типы сообщений пересылаем всем в комнате
        # (update, awareness, awareness_remove, awareness_request)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'editor_message',
                'message': message,
                'sender_channel': self.channel_name
            }
        )

    async def editor_message(self, event):
        message = event['message']
        sender = event.get('sender_channel', '')

        # Все сообщения отправляем всем кроме отправителя
        if self.channel_name != sender:
            await self.send(text_data=json.dumps({'message': message}))