from django.contrib import admin
from .models import SafetyProfile, SafetyRouteSegment, SafetySignal, WellnessCheckIn

@admin.register(SafetyProfile)
class SafetyProfileAdmin(admin.ModelAdmin):
    list_display = ("resident", "companion_enabled", "silent_sos_enabled", "fall_detection_enabled",
                    "inactivity_detection_enabled", "voice_distress_enabled", "wellness_enabled")

@admin.register(SafetyRouteSegment)
class SafetyRouteSegmentAdmin(admin.ModelAdmin):
    list_display = ("society", "start_lat", "start_lng", "end_lat", "end_lng", "distance_m", "safety_score", "reports", "active")
    list_filter = ("active", "one_way", "society")
    search_fields = ("start_lat", "start_lng", "end_lat", "end_lng")

@admin.register(SafetySignal)
class SafetySignalAdmin(admin.ModelAdmin):
    list_display = ("user", "signal_type", "confidence", "incident", "created_at")
    list_filter = ("signal_type",)

@admin.register(WellnessCheckIn)
class WellnessCheckInAdmin(admin.ModelAdmin):
    list_display = ("resident", "scheduled_for", "response_deadline", "status", "completed_at", "missed_notified_at")
    list_filter = ("status",)
