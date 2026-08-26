from rest_framework import serializers
from .models import Volunteer, VolunteerTask


class VolunteerTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = VolunteerTask
        fields = '__all__'
        read_only_fields = ['volunteer']


class VolunteerSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    tasks = VolunteerTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Volunteer
        fields = '__all__'
