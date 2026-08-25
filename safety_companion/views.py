from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import SafetyProfile, SafetyRouteSegment, SafetySignal, WellnessCheckIn
from .serializers import SafetyProfileSerializer, SafetyRouteSegmentSerializer, WellnessCheckInSerializer
from .services import (
    resident_for_user, create_safety_incident, compute_safe_route,
    complete_wellness_check,
)


class ResidentOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and resident_for_user(request.user))


def _coords(data):
    lat = data.get("latitude", data.get("lat"))
    lng = data.get("longitude", data.get("lng"))
    if lat is None or lng is None:
        return None, None
    lat, lng = float(lat), float(lng)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("Invalid latitude/longitude.")
    return lat, lng


class SafetyProfileView(APIView):
    permission_classes = [ResidentOnly]

    def get(self, request):
        resident = resident_for_user(request.user)
        profile, _ = SafetyProfile.objects.get_or_create(resident=resident)
        return Response(SafetyProfileSerializer(profile).data)

    def patch(self, request):
        resident = resident_for_user(request.user)
        profile, _ = SafetyProfile.objects.get_or_create(resident=resident)
        serializer = SafetyProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SilentSOSView(APIView):
    permission_classes = [ResidentOnly]

    def post(self, request):
        resident = resident_for_user(request.user)
        profile, _ = SafetyProfile.objects.get_or_create(resident=resident)
        if not profile.companion_enabled or not profile.silent_sos_enabled:
            return Response({"detail": "Silent SOS is disabled for this account."}, status=403)
        try:
            lat, lng = _coords(request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        # Mobile supplies a unique press/session id. Repeated retries within 5 seconds
        # do not create duplicate incidents.
        press_id = str(request.data.get("trigger_id", "")).strip()
        if press_id:
            existing = SafetySignal.objects.filter(
                user=request.user, signal_type="silent_sos",
                metadata__trigger_id=press_id,
            ).select_related("incident").first()
            if existing and existing.incident_id:
                return Response({"incident_id": existing.incident_id, "duplicate": True})

        alert, signal, notified = create_safety_incident(
            request.user, "silent_sos",
            "Silent SOS activated by a rapid triple key-press. The resident may be unable to interact with the screen.",
            latitude=lat, longitude=lng,
            confidence=Decimal("1.00"),
            metadata={
                "trigger_id": press_id,
                "trigger": "rapid_triple_press",
                "silent": True,
                "client_timestamp": request.data.get("client_timestamp"),
            },
        )
        return Response({
            "incident_id": alert.id,
            "signal_id": signal.id,
            "status": alert.status,
            "priority": alert.priority,
            "notified_users": notified,
            "silent": True,
        }, status=201)


class SafetySignalView(APIView):
    permission_classes = [ResidentOnly]

    allowed = {"fall", "inactivity", "voice_distress"}

    def post(self, request):
        signal_type = str(request.data.get("signal_type", "")).lower()
        if signal_type not in self.allowed:
            return Response({"detail": "Unsupported safety signal."}, status=400)

        resident = resident_for_user(request.user)
        profile, _ = SafetyProfile.objects.get_or_create(resident=resident)
        enabled = {
            "fall": profile.fall_detection_enabled,
            "inactivity": profile.inactivity_detection_enabled,
            "voice_distress": profile.voice_distress_enabled,
        }[signal_type]
        if not profile.companion_enabled or not enabled:
            return Response({"detail": f"{signal_type} detection is disabled."}, status=403)

        try:
            lat, lng = _coords(request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

        try:
            confidence = Decimal(str(request.data.get("confidence", "1")))
        except Exception:
            return Response({"detail": "confidence must be numeric."}, status=400)
        if not 0 <= confidence <= 1:
            return Response({"detail": "confidence must be between 0 and 1."}, status=400)

        if signal_type == "voice_distress" and confidence < Decimal("0.75"):
            return Response({"triggered": False, "reason": "confidence_below_threshold"}, status=200)

        message = {
            "fall": "Automatic fall detection reported a possible fall. Please check the resident.",
            "inactivity": "Automatic inactivity detection reported prolonged inactivity. Please check the resident.",
            "voice_distress": "On-device voice distress detection identified a distress pattern.",
        }[signal_type]
        alert, signal, notified = create_safety_incident(
            request.user, signal_type, message,
            latitude=lat, longitude=lng,
            confidence=confidence,
            metadata=request.data.get("metadata") or {},
        )
        return Response({
            "triggered": True,
            "incident_id": alert.id,
            "signal_id": signal.id,
            "status": alert.status,
            "priority": alert.priority,
            "notified_users": notified,
        }, status=201)


class SafetyRouteSegmentView(APIView):
    permission_classes = [ResidentOnly]

    def get(self, request):
        resident = resident_for_user(request.user)
        society_id = resident.flat.block.society_id if getattr(resident, "flat", None) and getattr(resident.flat, "block", None) else None
        qs = SafetyRouteSegment.objects.filter(active=True)
        if society_id:
            qs = qs.filter(society_id=society_id)
        return Response(SafetyRouteSegmentSerializer(qs[:500], many=True).data)

    def post(self, request):
        resident = resident_for_user(request.user)
        society_id = resident.flat.block.society_id
        data = request.data.copy()
        data.pop("society", None)
        data.pop("contributor", None)
        serializer = SafetyRouteSegmentSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        # Aggregate repeated reports for the same directed edge rather than creating
        # a new graph edge every time someone rates the same road.
        existing = SafetyRouteSegment.objects.filter(
            society_id=society_id,
            start_lat=vd["start_lat"], start_lng=vd["start_lng"],
            end_lat=vd["end_lat"], end_lng=vd["end_lng"],
            one_way=vd["one_way"],
        ).first()
        if existing:
            old_n = existing.reports
            new_n = old_n + 1
            existing.safety_score = ((existing.safety_score * old_n) + vd["safety_score"]) / new_n
            existing.reports = new_n
            existing.distance_m = vd["distance_m"]
            existing.active = True
            existing.save(update_fields=["safety_score", "reports", "distance_m", "active", "updated_at"])
            return Response(SafetyRouteSegmentSerializer(existing).data)
        obj = serializer.save(contributor=request.user, society_id=society_id)
        return Response(SafetyRouteSegmentSerializer(obj).data, status=201)


class SafeRouteView(APIView):
    permission_classes = [ResidentOnly]

    def post(self, request):
        start = request.data.get("start") or {}
        end = request.data.get("end") or {}
        if "lat" not in start or "lng" not in start or "lat" not in end or "lng" not in end:
            return Response({"detail": "start and end must contain lat and lng."}, status=400)
        try:
            result = compute_safe_route(
                request.user,
                start,
                end,
                safety_weight=request.data.get("safety_weight"),
                max_snap_m=float(request.data.get("max_snap_m", 250)),
            )
        except (ValueError, TypeError) as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(result)


class WellnessView(APIView):
    permission_classes = [ResidentOnly]

    def get(self, request):
        resident = resident_for_user(request.user)
        qs = WellnessCheckIn.objects.filter(resident=resident)[:20]
        return Response(WellnessCheckInSerializer(qs, many=True).data)

    def post(self, request):
        resident = resident_for_user(request.user)
        profile, _ = SafetyProfile.objects.get_or_create(resident=resident)
        if not profile.wellness_enabled:
            return Response({"detail": "Daily wellness check-ins are disabled."}, status=403)

        scheduled_for = request.data.get("scheduled_for")
        if scheduled_for:
            dt = parse_datetime(scheduled_for)
            if dt is None:
                return Response({"detail": "scheduled_for must be ISO-8601."}, status=400)
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt)
        else:
            # Default: next 09:00 in the server/user timezone.
            now = timezone.localtime()
            tomorrow = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            dt = tomorrow

        timeout = int(request.data.get("timeout_minutes", profile.wellness_timeout_minutes))
        if not 5 <= timeout <= 240:
            return Response({"detail": "timeout_minutes must be between 5 and 240."}, status=400)

        obj = WellnessCheckIn.objects.create(
            resident=resident,
            scheduled_for=dt,
            response_deadline=dt + timedelta(minutes=timeout),
            message=str(request.data.get("message", "Daily wellness check: are you okay?"))[:255],
        )
        return Response(WellnessCheckInSerializer(obj).data, status=201)


class WellnessActionView(APIView):
    permission_classes = [ResidentOnly]

    def post(self, request, pk):
        resident = resident_for_user(request.user)
        check = get_object_or_404(WellnessCheckIn, pk=pk, resident=resident)
        action = str(request.data.get("action", "")).lower()
        if action == "safe":
            if complete_wellness_check(check):
                return Response({"id": check.id, "status": check.status, "completed_at": check.completed_at})
            return Response({"detail": "This check-in is no longer actionable."}, status=409)
        if action == "cancel":
            if check.status in ("scheduled", "prompted"):
                check.status = "cancelled"
                check.save(update_fields=["status"])
                return Response({"id": check.id, "status": check.status})
            return Response({"detail": "This check-in is no longer cancellable."}, status=409)
        return Response({"detail": "Use action=safe or action=cancel."}, status=400)
