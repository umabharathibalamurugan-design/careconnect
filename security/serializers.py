from rest_framework import serializers
from .models import SecurityGuard


class SecurityGuardSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityGuard
        fields = '__all__'
