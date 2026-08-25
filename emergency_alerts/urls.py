from django.urls import path
from . import views

urlpatterns = [
    path('admin/', views.AdminEmergencyAlertListView.as_view(), name='admin-emergency-alerts'),
    path('', views.EmergencyAlertListCreateView.as_view()),
    path('<int:pk>/', views.EmergencyAlertDetailView.as_view()),
]
