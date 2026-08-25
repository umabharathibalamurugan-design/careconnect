from django.urls import path
from . import views

urlpatterns = [
    path('guards/', views.SecurityGuardListCreateView.as_view()),
    path('guards/<int:pk>/', views.SecurityGuardDetailView.as_view()),
]
