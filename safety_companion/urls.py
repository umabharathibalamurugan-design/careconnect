from django.urls import path
from .views import (
    SafetyProfileView, SilentSOSView, SafetySignalView,
    SafetyRouteSegmentView, SafeRouteView, WellnessView, WellnessActionView,
)

urlpatterns = [
    path("profile/", SafetyProfileView.as_view(), name="safety-profile"),
    path("silent-sos/", SilentSOSView.as_view(), name="silent-sos"),
    path("signals/", SafetySignalView.as_view(), name="safety-signal"),
    path("route-segments/", SafetyRouteSegmentView.as_view(), name="route-segments"),
    path("safe-route/", SafeRouteView.as_view(), name="safe-route"),
    path("wellness/", WellnessView.as_view(), name="wellness"),
    path("wellness/<int:pk>/action/", WellnessActionView.as_view(), name="wellness-action"),
]
