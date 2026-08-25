from django.urls import path
from . import views

urlpatterns = [
    path('', views.VisitorListCreateView.as_view()),
    path('<int:pk>/', views.VisitorDetailView.as_view()),
]
