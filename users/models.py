from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    society = models.ForeignKey('societies.Society', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    class Role(models.TextChoices):
        RESIDENT = 'resident', 'Resident'
        GUARDIAN = 'guardian', 'Guardian'
        VOLUNTEER = 'volunteer', 'Volunteer'
        SECURITY = 'security', 'Security Guard'
        SECURITY_ADMIN = 'security_admin', 'Security Admin'
        SECURITY_VOLUNTEER = 'security_volunteer', 'Security Volunteer'
        ADMIN = 'admin', 'Admin'
        SOCIETY_ADMIN = 'society_admin', 'Society Admin'
        SUPERADMIN = 'superadmin', 'Super Admin'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RESIDENT)
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.role})"
