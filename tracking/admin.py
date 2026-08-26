from django.contrib import admin
from .models import LiveLocation, LocationHistory

admin.site.register(LiveLocation)
admin.site.register(LocationHistory)
