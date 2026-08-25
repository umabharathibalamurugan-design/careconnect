from rest_framework import serializers
from .models import Guardian


class GuardianSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Guardian
        fields = '__all__'
