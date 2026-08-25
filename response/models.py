from django.conf import settings
from django.db import models
from emergency_alerts.models import EmergencyAlert
class NotificationDelivery(models.Model):
    CHANNELS=[('in_app','In App'),('push','Push'),('sms','SMS'),('email','Email')]
    STATUSES=[('pending','Pending'),('sent','Sent'),('delivered','Delivered'),('failed','Failed')]
    notification=models.ForeignKey('notifications.Notification',on_delete=models.CASCADE,related_name='deliveries')
    channel=models.CharField(max_length=20,choices=CHANNELS)
    status=models.CharField(max_length=20,choices=STATUSES,default='pending')
    delivered_at=models.DateTimeField(null=True,blank=True)
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
class AlertResponse(models.Model):
    STATUSES=[('notified','Notified'),('accepted','Accepted'),('rejected','Rejected'),('on_way','On Way'),('arrived','Arrived'),('completed','Completed')]
    alert=models.ForeignKey(EmergencyAlert,on_delete=models.CASCADE,related_name='responses')
    responder=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='alert_responses')
    role=models.CharField(max_length=30)
    status=models.CharField(max_length=20,choices=STATUSES,default='notified')
    response_time_seconds=models.PositiveIntegerField(null=True,blank=True)
    accepted_at=models.DateTimeField(null=True,blank=True)
    updated_at=models.DateTimeField(auto_now=True)
    created_at=models.DateTimeField(auto_now_add=True)
    class Meta: unique_together=('alert','responder')
class ResponderAssignment(models.Model):
    STATUSES=[('assigned','Assigned'),('accepted','Accepted'),('on_way','On Way'),('arrived','Arrived'),('completed','Completed'),('cancelled','Cancelled')]
    alert=models.ForeignKey(EmergencyAlert,on_delete=models.CASCADE,related_name='assignments')
    responder=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='emergency_assignments')
    assigned_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='assignments_made')
    status=models.CharField(max_length=20,choices=STATUSES,default='assigned')
    assigned_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    class Meta: unique_together=('alert','responder')
class IncidentMessage(models.Model):
    alert=models.ForeignKey(EmergencyAlert,on_delete=models.CASCADE,related_name='messages')
    sender=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='incident_messages')
    message=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
class IncidentUpdate(models.Model):
    alert=models.ForeignKey(EmergencyAlert,on_delete=models.CASCADE,related_name='incident_updates')
    actor=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='incident_updates')
    status=models.CharField(max_length=30)
    note=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)

class IncidentAudio(models.Model):
    alert=models.ForeignKey(EmergencyAlert,on_delete=models.CASCADE,related_name='audio_notes')
    sender=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name='incident_audio')
    audio=models.FileField(upload_to='incident_audio/%Y/%m/%d/')
    created_at=models.DateTimeField(auto_now_add=True)


class SafetyCheckIn(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='safety_checkins')
    due_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.status} - {self.due_at}'
