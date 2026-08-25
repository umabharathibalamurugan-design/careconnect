from rest_framework import serializers
from .models import NotificationDelivery,AlertResponse,ResponderAssignment,IncidentMessage,IncidentUpdate
class NotificationDeliverySerializer(serializers.ModelSerializer):
 class Meta: model=NotificationDelivery; fields='__all__'
class AlertResponseSerializer(serializers.ModelSerializer):
 responder_name=serializers.CharField(source='responder.username',read_only=True)
 class Meta: model=AlertResponse; fields='__all__'
class ResponderAssignmentSerializer(serializers.ModelSerializer):
 responder_name=serializers.CharField(source='responder.username',read_only=True)
 class Meta: model=ResponderAssignment; fields='__all__'
class IncidentMessageSerializer(serializers.ModelSerializer):
 sender_name=serializers.CharField(source='sender.username',read_only=True)
 class Meta: model=IncidentMessage; fields='__all__'; read_only_fields=['sender']
class IncidentUpdateSerializer(serializers.ModelSerializer):
 actor_name=serializers.CharField(source='actor.username',read_only=True)
 class Meta: model=IncidentUpdate; fields='__all__'
