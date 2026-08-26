from decimal import Decimal
from math import radians, sin, cos, sqrt, atan2
from django.db import transaction
from django.utils import timezone
from emergency_alerts.models import EmergencyAlert
from response.services import notify_participants, notify_user, record_update
from .models import SafetySignal, SafetyProfile, WellnessCheckIn, SafetyRouteSegment


def resident_for_user(user):
    return getattr(user, "residentprofile", None)


def _society_id(resident):
    try:
        return resident.flat.block.society_id
    except Exception:
        return None


def create_safety_incident(user, signal_type, message, latitude=None, longitude=None,
                           confidence=None, metadata=None, priority="critical"):
    resident = resident_for_user(user)
    if not resident:
        raise ValueError("This account is not linked to a ResidentProfile.")
    alert_type = {
        "silent_sos": "Silent SOS",
        "fall": "Automatic Fall Detection",
        "inactivity": "Automatic Inactivity Alert",
        "voice_distress": "Voice Distress Detection",
    }.get(signal_type, "Safety Companion Alert")

    with transaction.atomic():
        alert = EmergencyAlert.objects.create(
            resident=resident,
            alert_type=alert_type,
            message=message,
            status="active",
            priority=priority,
            latitude=latitude,
            longitude=longitude,
            response_window_minutes=2,
            escalation_deadline=timezone.now() + timezone.timedelta(minutes=2),
        )
        signal = SafetySignal.objects.create(
            user=user,
            signal_type=signal_type,
            confidence=confidence,
            latitude=latitude,
            longitude=longitude,
            metadata=metadata or {},
            incident=alert,
        )
        record_update(alert, user, "active", f"Safety Companion automatically created {alert_type}.")
        notified = notify_participants(
            alert,
            f"{alert_type} #{alert.id}",
            message,
            exclude=[user],
            include_resident=True,
        )
    return alert, signal, notified


def _schedule_next_daily(checkin):
    delta = checkin.response_deadline - checkin.scheduled_for
    next_scheduled = checkin.scheduled_for + timezone.timedelta(days=1)
    next_deadline = next_scheduled + delta
    WellnessCheckIn.objects.create(
        resident=checkin.resident,
        scheduled_for=next_scheduled,
        response_deadline=next_deadline,
        message=checkin.message,
    )


def complete_wellness_check(checkin):
    if checkin.status not in ("scheduled", "prompted"):
        return False
    checkin.status = "completed"
    checkin.completed_at = timezone.now()
    checkin.save(update_fields=["status", "completed_at"])
    _schedule_next_daily(checkin)
    return True


def process_wellness_checks(now=None):
    """Run from a scheduler/cron every minute. No Celery/Redis is required."""
    now = now or timezone.now()
    prompted = 0
    missed = 0

    # First mark checks that have reached their prompt time.
    due = WellnessCheckIn.objects.filter(
        status="scheduled", scheduled_for__lte=now
    ).select_related("resident__user")
    for check in due:
        check.status = "prompted"
        check.prompt_sent_at = now
        check.save(update_fields=["status", "prompt_sent_at"])
        notify_user(
            check.resident.user,
            "Daily wellness check",
            check.message,
            notification_type="general",
        )
        prompted += 1

    # Then escalate checks that passed the response deadline.
    overdue = WellnessCheckIn.objects.filter(
        status="prompted",
        response_deadline__lte=now,
        missed_notified_at__isnull=True,
    ).select_related("resident__user")
    for check in overdue:
        check.status = "missed"
        check.missed_notified_at = now
        check.save(update_fields=["status", "missed_notified_at"])
        from guardians.models import Guardian
        guardians = Guardian.objects.filter(
            resident=check.resident, can_receive_alerts=True
        ).select_related("user")
        for guardian in guardians:
            notify_user(
                guardian.user,
                "Wellness check missed",
                (
                    f"{check.resident.user.get_full_name() or check.resident.user.username} "
                    f"did not respond to the scheduled wellness check. "
                    "This is a lower-severity welfare alert, not a full SOS."
                ),
                notification_type="general",
            )
        _schedule_next_daily(check)
        missed += 1
    return {"prompted": prompted, "missed": missed}


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    a1, o1, a2, o2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    da, do = a2 - a1, o2 - o1
    a = sin(da / 2) ** 2 + cos(a1) * cos(a2) * sin(do / 2) ** 2
    return r * 2 * atan2(sqrt(a), sqrt(1 - a))


def _node(lat, lng, precision=5):
    return (round(float(lat), precision), round(float(lng), precision))


def _edge_cost(distance_m, safety_score, safety_weight):
    """Distance is the base cost; unsafe edges are penalized exponentially."""
    safety_penalty = max(0.0, min(1.0, (100.0 - float(safety_score)) / 100.0))
    return float(distance_m) * (1.0 + float(safety_weight) * safety_penalty)


def compute_safe_route(user, start, end, safety_weight=None, max_snap_m=250):
    """Dijkstra over crowd-sourced road edges. Nodes are geotagged segment endpoints."""
    resident = resident_for_user(user)
    if not resident:
        raise ValueError("Resident profile is required for safe-route navigation.")
    society_id = _society_id(resident)

    profile = SafetyProfile.objects.filter(resident=resident).first()
    weight = float(safety_weight if safety_weight is not None else (profile.safety_route_weight if profile else 2.0))

    segments = SafetyRouteSegment.objects.filter(active=True)
    if society_id is not None:
        segments = segments.filter(society_id=society_id)
    segments = list(segments)

    if not segments:
        raise ValueError("No crowd-sourced safety route segments exist for this society yet.")

    s = (float(start["lat"]), float(start["lng"]))
    t = (float(end["lat"]), float(end["lng"]))

    # Add virtual start/end nodes to the nearest road endpoints.
    nodes = {}
    edges = {}
    for seg in segments:
        a = _node(seg.start_lat, seg.start_lng)
        b = _node(seg.end_lat, seg.end_lng)
        nodes[a] = True; nodes[b] = True
        edges.setdefault(a, []).append((b, seg))
        if not seg.one_way:
            edges.setdefault(b, []).append((a, seg))

    def nearest(point):
        best = None
        for n in nodes:
            d = haversine_m(point[0], point[1], n[0], n[1])
            if best is None or d < best[0]:
                best = (d, n)
        return best

    start_near = nearest(s)
    end_near = nearest(t)
    if not start_near or not end_near:
        raise ValueError("Unable to snap the requested points to the safety road graph.")
    if start_near[0] > max_snap_m or end_near[0] > max_snap_m:
        raise ValueError("Start/end point is too far from the crowd-sourced safety graph.")

    start_node, end_node = start_near[1], end_near[1]

    # Dijkstra with a heap; predecessor stores the segment used.
    import heapq
    dist = {start_node: 0.0}
    prev = {}
    heap = [(0.0, start_node)]
    visited = set()

    while heap:
        cost, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        if u == end_node:
            break
        for v, seg in edges.get(u, []):
            new_cost = cost + _edge_cost(seg.distance_m, seg.safety_score, weight)
            if new_cost < dist.get(v, float("inf")):
                dist[v] = new_cost
                prev[v] = (u, seg)
                heapq.heappush(heap, (new_cost, v))

    if end_node not in dist:
        raise ValueError("No connected safe route was found between these points.")

    path_nodes = [end_node]
    used_segments = []
    cur = end_node
    while cur != start_node:
        parent, seg = prev[cur]
        path_nodes.append(parent)
        used_segments.append(seg)
        cur = parent
    path_nodes.reverse()
    used_segments.reverse()

    distance = sum(seg.distance_m for seg in used_segments)
    weighted = dist[end_node]
    safety = (
        sum(float(seg.safety_score) * seg.distance_m for seg in used_segments) / distance
        if distance else 0
    )
    return {
        "path": [{"lat": p[0], "lng": p[1]} for p in path_nodes],
        "distance_m": round(distance),
        "weighted_cost": round(weighted, 2),
        "average_safety_score": round(safety, 2),
        "segments": [
            {
                "id": seg.id,
                "safety_score": float(seg.safety_score),
                "distance_m": seg.distance_m,
                "reports": seg.reports,
            }
            for seg in used_segments
        ],
        "safety_weight": weight,
    }
