from django.db import models
from residents.models import ResidentProfile
from guardians.models import Guardian

class EmergencyContact(models.Model):
    class ContactType(models.TextChoices):
        PRIMARY = "primary", "Primary"
        SECONDARY = "secondary", "Secondary"

    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE, related_name="emergency_contacts")
    guardian = models.ForeignKey(Guardian, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    relation = models.CharField(max_length=50)
    contact_type = models.CharField(max_length=12, choices=ContactType.choices, default=ContactType.PRIMARY)
    is_verified = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["resident","contact_type"], name="unique_resident_emergency_contact_type")]
        ordering = ["contact_type", "created_at"]

    def save(self, *args, **kwargs):
        self.is_primary = self.contact_type == self.ContactType.PRIMARY
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_contact_type_display()}: {self.name}"
