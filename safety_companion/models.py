from django.conf import settings
from django.db import models
from residents.models import ResidentProfile


class SafetyProfile(models.Model):
    """Per-resident settings; references the existing ResidentProfile instead of duplicating it."""
    resident = models.OneToOneField(
        ResidentProfile, on_delete=models.CASCADE, related_name="safety_profile"
    )
    companion_enabled = models.BooleanField(default=True)
    silent_sos_enabled = models.BooleanField(default=True)
    fall_detection_enabled = models.BooleanField(default=True)
    inactivity_detection_enabled = models.BooleanField(default=True)
    voice_distress_enabled = models.BooleanField(default=False)
    wellness_enabled = models.BooleanField(default=False)
    triple_press_window_ms = models.PositiveIntegerField(default=900)
    inactivity_minutes = models.PositiveIntegerField(default=60)
    wellness_timeout_minutes = models.PositiveIntegerField(default=30)
    safety_route_weight = models.DecimalField(max_digits=4, decimal_places=2, default=2.00)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Safety profile: {self.resident}"


class SafetyRouteSegment(models.Model):
    """Crowd-sourced directed road segment. The app can submit map-provider road edges."""
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="safety_route_segments"
    )
    society = models.ForeignKey(
        "societies.Society", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="safety_route_segments"
    )
    start_lat = models.DecimalField(max_digits=9, decimal_places=6)
    start_lng = models.DecimalField(max_digits=9, decimal_places=6)
    end_lat = models.DecimalField(max_digits=9, decimal_places=6)
    end_lng = models.DecimalField(max_digits=9, decimal_places=6)
    distance_m = models.PositiveIntegerField()
    safety_score = models.DecimalField(max_digits=5, decimal_places=2, default=50)
    reports = models.PositiveIntegerField(default=1)
    one_way = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["society", "active"]),
            models.Index(fields=["start_lat", "start_lng"]),
            models.Index(fields=["end_lat", "end_lng"]),
        ]

    def __str__(self):
        return f"{self.start_lat},{self.start_lng} -> {self.end_lat},{self.end_lng} ({self.safety_score})"


class SafetySignal(models.Model):
    SIGNALS = [
        ("silent_sos", "Silent SOS"),
        ("fall", "Fall"),
        ("inactivity", "Inactivity"),
        ("voice_distress", "Voice Distress"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safety_signals")
    signal_type = models.CharField(max_length=30, choices=SIGNALS)
    confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    incident = models.ForeignKey(
        "emergency_alerts.EmergencyAlert", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="safety_signals"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "signal_type", "created_at"])]


class WellnessCheckIn(models.Model):
    STATUS = [
        ("scheduled", "Scheduled"),
        ("prompted", "Prompted"),
        ("completed", "Completed"),
        ("missed", "Missed"),
        ("cancelled", "Cancelled"),
    ]
    resident = models.ForeignKey(
        ResidentProfile, on_delete=models.CASCADE, related_name="companion_wellness_checks"
    )
    scheduled_for = models.DateTimeField()
    response_deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS, default="scheduled")
    prompt_sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    missed_notified_at = models.DateTimeField(null=True, blank=True)
    message = models.CharField(max_length=255, default="Daily wellness check: are you okay?")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_for"]
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
            models.Index(fields=["status", "response_deadline"]),
        ]

    def __str__(self):
        return f"{self.resident} - {self.status} - {self.scheduled_for}"
