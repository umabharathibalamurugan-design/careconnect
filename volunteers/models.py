from django.db import models
from django.conf import settings
from societies.models import Society, Block


class Volunteer(models.Model):
    class VolunteerRole(models.TextChoices):
        SECURITY_HELPER = 'security_helper', 'Security Helper'
        EVENT_COORDINATOR = 'event_coordinator', 'Event Coordinator'
        MAINTENANCE = 'maintenance', 'Maintenance & Repairs'
        CLEANLINESS = 'cleanliness', 'Cleanliness Drive'
        SPORTS_FITNESS = 'sports_fitness', 'Sports & Fitness'
        ELDERLY_CARE = 'elderly_care', 'Elderly Care'
        DISASTER_RESPONSE = 'disaster_response', 'Disaster / Emergency Response'
        GENERAL = 'general', 'General Volunteer'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='volunteer_profile')
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='volunteers')
    assigned_block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True, related_name='volunteers')
    role = models.CharField(max_length=30, choices=VolunteerRole.choices, default=VolunteerRole.GENERAL)
    is_active = models.BooleanField(default=True)
    available_for_emergency = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class VolunteerTask(models.Model):
    class Status(models.TextChoices):
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    volunteer = models.ForeignKey(Volunteer, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ASSIGNED)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"
