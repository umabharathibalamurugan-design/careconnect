from django.urls import path
from .views import AssistantChatView, AssistantBriefingView
urlpatterns=[path('chat/',AssistantChatView.as_view()),path('briefing/',AssistantBriefingView.as_view())]
