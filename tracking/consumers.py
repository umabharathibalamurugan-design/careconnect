import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SocietyTrackingConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket for a society's live map dashboard.
    Connect: ws://<host>/ws/tracking/<society_id>/
    Every time any guard/volunteer/resident in that society posts a location
    update via POST /api/tracking/update/, all connected clients receive it
    instantly as a JSON message: {"type": "location_update", "data": {...}}
    """

    async def connect(self):
        self.society_id = self.scope['url_route']['kwargs']['society_id']
        self.group_name = f"society_{self.society_id}_tracking"

        if self.scope['user'] is None or self.scope['user'].is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def location_update(self, event):
        await self.send_json({
            "type": "location_update",
            "data": event["data"],
        })
