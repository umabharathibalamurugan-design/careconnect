from django.db import models
from residents.models import ResidentProfile


class Visitor(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CHECKED_IN = 'checked_in', 'Checked In'
        CHECKED_OUT = 'checked_out', 'Checked Out'

    resident = models.ForeignKey(ResidentProfile, on_delete=models.CASCADE, related_name='visitors')
    visitor_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    purpose = models.CharField(max_length=200)
    visit_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.visitor_name
