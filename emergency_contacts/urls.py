from django.urls import path
from .views import EmergencyContactListCreateView,EmergencyContactDetailView,EmergencyContactVerifyView
urlpatterns=[path('',EmergencyContactListCreateView.as_view()),path('<int:pk>/',EmergencyContactDetailView.as_view()),path('<int:pk>/verify/',EmergencyContactVerifyView.as_view())]
