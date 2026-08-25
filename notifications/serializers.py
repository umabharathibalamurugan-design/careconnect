from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    delivery_status = serializers.SerializerMethodField()
    alert_id = serializers.IntegerField(source='alert_id', read_only=True)
    action_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['recipient', 'delivery_status']

    def get_action_url(self, obj):
        return f'/emergency-history/?alert={obj.alert_id}' if obj.alert_id else None

    def get_delivery_status(self, obj):
        rows = list(obj.deliveries.all())
        return [
            {
                'channel': row.channel,
                'status': row.status,
                'delivered_at': row.delivered_at,
            }
            for row in rows
        ]
