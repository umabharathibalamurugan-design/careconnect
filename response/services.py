from django.utils import timezone
from django.db import models
from math import radians, sin, cos, sqrt, atan2
from notifications.models import Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import NotificationDelivery, AlertResponse, IncidentUpdate, ResponderAssignment


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    a1, o1, a2, o2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    da, do = a2 - a1, o2 - o1
    a = sin(da / 2) ** 2 + cos(a1) * cos(a2) * sin(do / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def responder_reliability(user):
    responses = AlertResponse.objects.filter(responder=user)
    completed = responses.filter(status='completed').count()
    accepted = responses.exclude(status__in=['notified', 'rejected']).count()
    avg = responses.filter(response_time_seconds__isnull=False).aggregate(avg=models.Avg('response_time_seconds')).get('avg') or 0
    speed = max(0, 40 - float(avg) / 10)
    completion = min(40, completed * 2)
    participation = min(20, accepted)
    return round(min(100, 40 + speed + completion + participation), 1)


def smart_match_alert(alert):
    """Return the best available volunteer for an alert without creating a second notification storm."""
    from volunteers.models import Volunteer
    from tracking.models import LiveLocation
    society_id = alert.resident.flat.block.society_id
    busy_ids = set(ResponderAssignment.objects.filter(
        responder__role='volunteer',
        status__in=['assigned', 'accepted', 'on_way', 'arrived'],
        alert__status__in=['open', 'acknowledged', 'active', 'escalated'],
    ).values_list('responder_id', flat=True))
    volunteers = Volunteer.objects.filter(
        society_id=society_id, is_active=True, available_for_emergency=True, user__role='volunteer'
    ).select_related('user', 'assigned_block')
    best = None
    for v in volunteers:
        if v.user_id in busy_ids:
            continue
        loc = LiveLocation.objects.filter(user=v.user, is_sharing=True).first()
        distance = None
        if loc and alert.latitude is not None and alert.longitude is not None:
            distance = haversine_km(alert.latitude, alert.longitude, loc.latitude, loc.longitude)
        reliability = responder_reliability(v.user)
        role_bonus = 15 if v.role == Volunteer.VolunteerRole.DISASTER_RESPONSE else 0
        distance_score = max(0, 45 - (distance or 2.0) * 12)
        score = round(min(100, 40 + distance_score + role_bonus + reliability * 0.25), 1)
        candidate=(score, -(distance if distance is not None else 9999), reliability, v, loc)
        if best is None or candidate[:3] > best[:3]:
            best=candidate
    if not best:
        return None
    score, neg_distance, reliability, volunteer, loc = best
    distance = -neg_distance if neg_distance < 0 else None
    return {
        'volunteer': volunteer, 'location': loc, 'distance_km': None if distance == 9999 else round(distance, 3),
        'reliability_score': reliability, 'match_score': score
    }


def notify_user(user, title, message, alert=None, notification_type='emergency'):
    """Create a real in-app notification and delivery records for one user."""
    n = Notification.objects.create(
        recipient=user,
        notification_type=notification_type,
        title=title,
        message=message,
        alert=alert,
    )
    NotificationDelivery.objects.create(
        notification=n,
        channel='in_app',
        status='delivered',
        delivered_at=timezone.now(),
    )
    for channel in ('push', 'sms', 'email'):
        NotificationDelivery.objects.create(
            notification=n,
            channel=channel,
            status='pending',
        )
    if alert is not None:
        AlertResponse.objects.get_or_create(
            alert=alert,
            responder=user,
            defaults={'role': user.role, 'status': 'notified'},
        )
    # Real-time in-app delivery. If the user is offline, the database notification
    # remains available for the next dashboard load.
    try:
        async_to_sync(get_channel_layer().group_send)(
            f'user_{user.id}_notifications',
            {'type': 'notification_event', 'payload': {
                'type': 'notification', 'notification_id': n.id, 'alert_id': alert.id if alert else None,
                'title': title, 'message': message, 'notification_type': notification_type,
                'created_at': n.created_at.isoformat(), 'action_url': f'/emergency-history/?alert={alert.id}' if alert else '/notifications/'
            }}
        )
    except Exception:
        pass
    return n


def _society_users(alert):
    """Return admins/security/guardians/responders who should see incident updates."""
    users = set()
    from users.models import User
    from volunteers.models import Volunteer
    from security.models import SecurityGuard

    society_id = alert.resident.flat.block.society_id

    # Society-level control room users. The current User model does not carry a
    # society FK, so all admin/society-admin accounts are included for reliable
    # demo delivery rather than silently dropping the notification.
    users.update(User.objects.filter(role__in=['admin', 'society_admin', 'superadmin', 'security_admin']))

    for guardian in alert.resident.guardians.select_related('user').all():
        if guardian.can_receive_alerts:
            users.add(guardian.user)

    users.update(User.objects.filter(
        id__in=Volunteer.objects.filter(
            society_id=society_id,
            is_active=True,
            available_for_emergency=True,
        ).values_list('user_id', flat=True)
    ))
    users.update(User.objects.filter(
        id__in=SecurityGuard.objects.filter(
            society_id=society_id,
            is_on_duty=True,
        ).values_list('user_id', flat=True)
    ))
    return users


def participants_for_alert(alert, include_resident=False):
    users = _society_users(alert)
    if include_resident:
        users.add(alert.resident.user)
    return users


def notify_participants(alert, title, message, exclude=None, include_resident=True):
    """Push the same event to everyone who needs to know about an incident."""
    excluded_ids = {u.id for u in (exclude or [])}
    sent = 0
    for user in participants_for_alert(alert, include_resident=include_resident):
        if user.id in excluded_ids:
            continue
        notify_user(user, title, message, alert=alert)
        sent += 1
    return sent


def notify_resolution(alert, actor, note=''):
    """Close the loop: notify everyone and explicitly release other responders."""
    name = actor.get_full_name() or actor.username
    note_text = f' Note: {note}' if note else ''

    notify_participants(
        alert,
        f'Incident #{alert.id} resolved',
        f'Incident #{alert.id} has been resolved by {name}.{note_text}',
        exclude=[actor],
        include_resident=True,
    )

    # Everyone who received/accepted this incident is told to stop responding.
    for response in alert.responses.select_related('responder').exclude(responder=actor):
        if response.status not in ('completed', 'rejected'):
            notify_user(
                response.responder,
                f'No further response required - #{alert.id}',
                f'Incident #{alert.id} is resolved. No further response is required.',
                alert=alert,
            )
            response.status = 'completed'
            response.save(update_fields=['status', 'updated_at'])
            ResponderAssignment.objects.filter(
                alert=alert,
                responder=response.responder,
            ).update(status='completed', updated_at=timezone.now())


def record_update(alert, actor, status, note=''):
    return IncidentUpdate.objects.create(
        alert=alert,
        actor=actor,
        status=status,
        note=note,
    )


def auto_escalate_expired():
    from emergency_alerts.models import EmergencyAlert
    expired = EmergencyAlert.objects.filter(
        status__in=['open', 'acknowledged', 'active'],
        escalation_deadline__isnull=False,
        escalation_deadline__lte=timezone.now(),
    ).select_related('resident__user')
    for alert in expired:
        alert.status = 'escalated'
        alert.priority = 'critical'
        alert.save(update_fields=['status', 'priority', 'updated_at'])
        notify_participants(
            alert,
            f'ESCALATED SOS #{alert.id}',
            f'Emergency #{alert.id} requires immediate response.',
            include_resident=True,
        )
        record_update(alert, alert.resident.user, 'escalated', 'Response window expired; alert auto-escalated')
