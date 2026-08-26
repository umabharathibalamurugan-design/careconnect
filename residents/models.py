from django.db import models
from django.conf import settings
from societies.models import Flat


class ResidentProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    flat = models.ForeignKey(Flat, on_delete=models.CASCADE, related_name='residents')
    is_owner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
