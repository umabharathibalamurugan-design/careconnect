from django.contrib import admin
from .models import AssistantSession, AssistantMessage
admin.site.register(AssistantSession)
admin.site.register(AssistantMessage)
