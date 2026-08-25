from django.db import models
from django.conf import settings
from societies.models import Society


class SecurityGuard(models.Model):
    class Shift(models.TextChoices):
        MORNING = 'morning', 'Morning (6AM-2PM)'
        EVENING = 'evening', 'Evening (2PM-10PM)'
        NIGHT = 'night', 'Night (10PM-6AM)'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='guard_profile')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='security_guards')
    gate_assigned = models.CharField(max_length=100, blank=True)
    shift = models.CharField(max_length=20, choices=Shift.choices, default=Shift.MORNING)
    is_on_duty = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.gate_assigned or 'Unassigned'}"
