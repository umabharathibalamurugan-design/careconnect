from django.urls import path
from . import views

urlpatterns = [
    path('', views.ResidentProfileListCreateView.as_view()),
    path('<int:pk>/', views.ResidentProfileDetailView.as_view()),
]
