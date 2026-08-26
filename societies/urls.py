from django.urls import path
from . import views

urlpatterns = [
    path('', views.SocietyListCreateView.as_view()),
    path('blocks/', views.BlockListCreateView.as_view()),
    path('flats/', views.FlatListCreateView.as_view()),
]
