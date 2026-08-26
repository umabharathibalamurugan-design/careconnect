from django.contrib import admin
from .models import NotificationDelivery,AlertResponse,ResponderAssignment,IncidentMessage,IncidentUpdate
for m in (NotificationDelivery,AlertResponse,ResponderAssignment,IncidentMessage,IncidentUpdate): admin.site.register(m)
