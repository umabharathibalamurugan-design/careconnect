from django.urls import path
from . import views

urlpatterns = [
    path('update/', views.UpdateLocationView.as_view()),
    path('me/', views.MyLocationView.as_view()),
    path('live/<int:user_id>/', views.UserLiveLocationView.as_view()),
    path('society/<int:society_id>/live-map/', views.SocietyLiveMapView.as_view()),
    path('nearby/', views.NearbyLiveUsersView.as_view()),
    path('history/<int:user_id>/', views.LocationHistoryView.as_view()),
]
