from django.db import models
from django.conf import settings
from residents.models import ResidentProfile


class Guardian(models.Model):
    class GuardianRole(models.TextChoices):
        PRIMARY = 'primary', 'Primary Guardian'
        SECONDARY = 'secondary', 'Secondary Guardian'
        EMERGENCY_CONTACT = 'emergency_contact', 'Emergency Contact'
        CARETAKER = 'caretaker', 'Caretaker'
        LEGAL_GUARDIAN = 'legal_guardian', 'Legal Guardian'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE, related_name='guardians')
    relation = models.CharField(max_length=50)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # --- NEW: role-based access for guardians ---
    role = models.CharField(max_length=30, choices=GuardianRole.choices, default=GuardianRole.SECONDARY)
    can_approve_visitors = models.BooleanField(default=False)
    can_receive_alerts = models.BooleanField(default=True)
    can_track_location = models.BooleanField(default=False)  # allowed to view resident's live location

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
