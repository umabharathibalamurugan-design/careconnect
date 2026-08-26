from decimal import Decimal
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import LiveLocation, LocationHistory
from .serializers import LiveLocationSerializer, LocationUpdateSerializer, LocationHistorySerializer


def haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


class UpdateLocationView(APIView):
    """
    POST /api/tracking/update/
    The logged-in user (guard, volunteer, or resident) pushes their current GPS fix.
    Call this every 5-15 seconds from the mobile app / browser geolocation API
    for a near-real-time trail. Also broadcasts instantly over WebSocket.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        live, _ = LiveLocation.objects.update_or_create(
            user=request.user,
            defaults={
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'accuracy_meters': data.get('accuracy_meters'),
                'battery_level': data.get('battery_level'),
                'is_sharing': data.get('is_sharing', True),
                'society_id': data.get('society'),
            }
        )

        LocationHistory.objects.create(
            user=request.user,
            latitude=data['latitude'],
            longitude=data['longitude'],
        )

        # Push instantly to anyone watching this society's live map over WebSocket
        if live.society_id:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"society_{live.society_id}_tracking",
                {
                    "type": "location.update",
                    "data": LiveLocationSerializer(live).data,
                }
            )

        return Response(LiveLocationSerializer(live).data, status=status.HTTP_200_OK)


class MyLocationView(generics.RetrieveAPIView):
    serializer_class = LiveLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return LiveLocation.objects.get(user=self.request.user)


class UserLiveLocationView(generics.RetrieveAPIView):
    """GET /api/tracking/live/<user_id>/ - view a specific user's current location
    (e.g. admin/security dashboard checking a guard or volunteer)."""
    serializer_class = LiveLocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = LiveLocation.objects.all()
    lookup_url_kwarg = 'user_id'
    lookup_field = 'user_id'

    def get_queryset(self):
        target = self.kwargs.get('user_id')
        role = str(getattr(self.request.user, 'role', '')).lower()
        if role in ('admin', 'superadmin'):
            return LiveLocation.objects.filter(user_id=target)
        if role == 'society_admin':
            return LiveLocation.objects.filter(user_id=target, society_id=getattr(self.request.user, 'society_id', None))
        if role == 'guardian':
            from guardians.models import Guardian
            allowed = Guardian.objects.filter(user=self.request.user, can_track_location=True).values_list('resident__user_id', flat=True)
            return LiveLocation.objects.filter(user_id=target, user_id__in=allowed)
        if role == 'resident' and str(target) == str(self.request.user.id):
            return LiveLocation.objects.filter(user_id=target)
        return LiveLocation.objects.none()


class SocietyLiveMapView(generics.ListAPIView):
    """GET /api/tracking/society/<society_id>/live-map/
    All users currently sharing their live location within a society -
    powers a live map dashboard (guards + volunteers + residents who opted in)."""
    serializer_class = LiveLocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        society_id = self.kwargs['society_id']
        user_role = str(getattr(self.request.user, 'role', '')).lower()
        if user_role == 'society_admin' and str(getattr(self.request.user, 'society_id', '')) != str(society_id):
            return LiveLocation.objects.none()
        if user_role == 'guardian':
            from guardians.models import Guardian
            allowed = Guardian.objects.filter(user=self.request.user, can_track_location=True).values_list('resident__user_id', flat=True)
            return LiveLocation.objects.filter(society_id=society_id, is_sharing=True, user_id__in=allowed)
        qs = LiveLocation.objects.filter(society_id=society_id, is_sharing=True)
        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(user__role=role)
        return qs


class NearbyLiveUsersView(APIView):
    """GET /api/tracking/nearby/?lat=..&lng=..&radius_km=1&role=security
    Find active guards/volunteers near a given point - e.g. 'nearest available
    guard' during an emergency alert."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            lat = Decimal(request.query_params['lat'])
            lng = Decimal(request.query_params['lng'])
        except (KeyError, Exception):
            return Response({'detail': 'lat and lng query params are required'}, status=400)

        radius_km = float(request.query_params.get('radius_km', 2))
        role = request.query_params.get('role')

        qs = LiveLocation.objects.filter(is_sharing=True)
        if role:
            qs = qs.filter(user__role=role)

        results = []
        for loc in qs.select_related('user'):
            dist = haversine_km(lat, lng, loc.latitude, loc.longitude)
            if dist <= radius_km:
                item = LiveLocationSerializer(loc).data
                item['distance_km'] = round(dist, 3)
                results.append(item)

        results.sort(key=lambda x: x['distance_km'])
        return Response(results)


class LocationHistoryView(generics.ListAPIView):
    """GET /api/tracking/history/<user_id>/ - patrol trail / audit history."""
    serializer_class = LocationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LocationHistory.objects.filter(user_id=self.kwargs['user_id'])[:200]
