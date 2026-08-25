from rest_framework import serializers
from .models import EmergencyAlert
class EmergencyAlertSerializer(serializers.ModelSerializer):
    resident_name=serializers.SerializerMethodField()
    resident_username=serializers.SerializerMethodField()
    resident_phone=serializers.SerializerMethodField()
    class Meta:
        model=EmergencyAlert
        fields=['id','resident','resident_name','resident_username','resident_phone','alert_type','message','status','priority','latitude','longitude','response_window_minutes','escalation_deadline','resolved_at','closed_by','closure_note','created_at','updated_at']
        read_only_fields=['id','resident_name','resident_username','created_at','updated_at','resolved_at','closed_by']
    def get_resident_name(self,obj):
        user=obj.resident.user
        return user.get_full_name() or user.username
    def get_resident_username(self,obj): return obj.resident.user.username
    def get_resident_phone(self,obj): return obj.resident.user.phone_number or ''
