from django.db import models
from django.conf import settings
from societies.models import Society


class LiveLocation(models.Model):
    """Current live GPS position of a user (guard / volunteer / resident)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='live_location')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='live_locations', null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    accuracy_meters = models.FloatField(null=True, blank=True)
    battery_level = models.PositiveSmallIntegerField(null=True, blank=True)
    is_sharing = models.BooleanField(default=True)  # user can toggle live sharing on/off
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} @ ({self.latitude}, {self.longitude})"


class LocationHistory(models.Model):
    """Trail of past positions - useful for guard patrol routes / audit."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='location_history')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [models.Index(fields=['user', '-recorded_at'])]

    def __str__(self):
        return f"{self.user.username} @ {self.recorded_at}"
