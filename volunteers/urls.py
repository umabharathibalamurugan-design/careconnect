from django.urls import path
from . import views

urlpatterns = [
    path('', views.VolunteerListCreateView.as_view()),
    path('<int:pk>/', views.VolunteerDetailView.as_view()),
    path('tasks/', views.VolunteerTaskListCreateView.as_view()),
]
