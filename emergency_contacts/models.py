from django.db import models
from residents.models import ResidentProfile
from guardians.models import Guardian


class EmergencyContact(models.Model):

    resident = models.ForeignKey(
        ResidentProfile,
        on_delete=models.CASCADE,
        related_name="emergency_contacts"
    )

    guardian = models.ForeignKey(
        Guardian,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(
        max_length=100
    )

    phone_number = models.CharField(
        max_length=15
    )

    relation = models.CharField(
        max_length=50
    )

    is_verified = models.BooleanField(
        default=False
    )

    is_primary = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.name