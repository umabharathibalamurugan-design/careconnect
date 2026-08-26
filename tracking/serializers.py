from rest_framework import serializers
from .models import LiveLocation, LocationHistory


class LiveLocationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)

    class Meta:
        model = LiveLocation
        fields = ['id', 'user', 'username', 'role', 'society', 'latitude', 'longitude',
                   'accuracy_meters', 'battery_level', 'is_sharing', 'last_updated']
        read_only_fields = ['user', 'last_updated']


class LocationUpdateSerializer(serializers.Serializer):
    """Payload the client sends every few seconds to push its current GPS fix."""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    accuracy_meters = serializers.FloatField(required=False, allow_null=True)
    battery_level = serializers.IntegerField(required=False, allow_null=True)
    is_sharing = serializers.BooleanField(required=False, default=True)
    society = serializers.IntegerField(required=False, allow_null=True)


class LocationHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationHistory
        fields = '__all__'
