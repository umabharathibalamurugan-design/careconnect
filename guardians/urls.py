from django.urls import path
from . import views

urlpatterns = [
    path('', views.GuardianListCreateView.as_view()),
    path('<int:pk>/', views.GuardianDetailView.as_view()),
]
