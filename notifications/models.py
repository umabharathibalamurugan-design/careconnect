from django.db import models
from django.conf import settings


class Notification(models.Model):
    class Type(models.TextChoices):
        GENERAL = 'general', 'General'
        VISITOR = 'visitor', 'Visitor'
        EMERGENCY = 'emergency', 'Emergency'
        VOLUNTEER = 'volunteer', 'Volunteer'
        TRACKING = 'tracking', 'Tracking'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    alert = models.ForeignKey('emergency_alerts.EmergencyAlert', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=Type.choices, default=Type.GENERAL)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
