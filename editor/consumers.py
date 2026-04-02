import json
from channels.generic.websocket import AsyncWebsocketConsumer

class EditorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Название "комнаты" (проекта), к которой подключается пользователь
        self.room_name = 'shared_editor'
        self.room_group_name = f'chat_{self.room_name}'

        # Входим в группу (комнату)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Покидаем группу при отключении
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Получение сообщения от WebSocket (от одного пользователя)
    async def receive(self, text_data):
        data = json.loads(text_data)
        
        # Пересылаем сообщение всем остальным участникам группы
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'editor_message',
                'message': data['message']
            }
        )

    # Метод для отправки сообщения обратно в WebSocket
    async def editor_message(self, event):
        message = event['message']

        # Отправляем данные на фронтенд
        await self.send(text_data=json.dumps({
            'message': message
        }))