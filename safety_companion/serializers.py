from rest_framework import serializers
from .models import SafetyProfile, SafetyRouteSegment, WellnessCheckIn


class SafetyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyProfile
        exclude = ("resident",)
        read_only_fields = ("updated_at",)


class SafetyRouteSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SafetyRouteSegment
        fields = "__all__"
        read_only_fields = ("contributor", "society", "reports", "created_at", "updated_at")

    def validate_safety_score(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Safety score must be between 0 and 100.")
        return value

    def validate_distance_m(self, value):
        if value <= 0:
            raise serializers.ValidationError("distance_m must be greater than zero.")
        return value


class WellnessCheckInSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellnessCheckIn
        fields = "__all__"
        read_only_fields = (
            "resident", "status", "prompt_sent_at", "completed_at",
            "missed_notified_at", "created_at",
        )
