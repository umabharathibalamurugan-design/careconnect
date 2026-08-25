from django.shortcuts import get_object_or_404
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from emergency_alerts.models import EmergencyAlert
from residents.models import ResidentProfile
from volunteers.models import Volunteer
from security.models import SecurityGuard
from users.models import User
from .models import AlertResponse, ResponderAssignment, IncidentMessage, IncidentUpdate, NotificationDelivery, IncidentAudio, SafetyCheckIn
from .serializers import AlertResponseSerializer, ResponderAssignmentSerializer, IncidentMessageSerializer, IncidentUpdateSerializer, NotificationDeliverySerializer
from .services import notify_user, notify_participants, notify_resolution, record_update, smart_match_alert, responder_reliability, haversine_km




def can_access_alert(user, alert):
    role = str(getattr(user, 'role', '')).lower()
    if role in ('admin','superadmin'):
        return True
    if role == 'resident':
        return alert.resident.user_id == user.id
    society_id = getattr(user, 'society_id', None) or getattr(getattr(user, 'guard_profile', None), 'society_id', None) or getattr(getattr(user, 'volunteer_profile', None), 'society_id', None)
    try:
        alert_society = alert.resident.flat.block.society_id
    except Exception:
        alert_society = None
    if role in ('society_admin','security_admin'):
        return bool(society_id and alert_society == society_id)
    if role in ('security','security_volunteer','volunteer'):
        assigned = ResponderAssignment.objects.filter(alert=alert, responder=user).exists()
        return assigned or (society_id == alert_society and alert.priority == 'critical' and alert.status in ('open','acknowledged','active','escalated'))
    if role == 'guardian':
        from guardians.models import Guardian
        return Guardian.objects.filter(user=user, resident=alert.resident).exists()
    return False

def participants(alert):
    from .services import participants_for_alert
    return participants_for_alert(alert, include_resident=False)



class SafetyCheckInView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _expire(self, user):
        now = timezone.now()
        overdue = SafetyCheckIn.objects.filter(user=user, status='active', due_at__lte=now)
        for checkin in overdue:
            checkin.status = 'missed'
            checkin.save(update_fields=['status'])
            try:
                notify_participants_for_checkin(checkin)
            except Exception:
                pass

    def get(self, request):
        self._expire(request.user)
        rows = SafetyCheckIn.objects.filter(user=request.user)[:20]
        return Response([{
            'id': x.id, 'status': x.status, 'due_at': x.due_at, 'created_at': x.created_at,
            'completed_at': x.completed_at,
        } for x in rows])

    def post(self, request):
        minutes = int(request.data.get('minutes', 30))
        if minutes not in (30, 60, 120):
            return Response({'detail': 'Choose 30, 60 or 120 minutes.'}, status=400)
        # Keep one active timer per user.
        SafetyCheckIn.objects.filter(user=request.user, status='active').update(status='cancelled')
        due = timezone.now() + timedelta(minutes=minutes)
        checkin = SafetyCheckIn.objects.create(user=request.user, due_at=due)
        return Response({'id': checkin.id, 'status': checkin.status, 'due_at': checkin.due_at}, status=201)


class SafetyCheckInActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        checkin = get_object_or_404(SafetyCheckIn, pk=pk, user=request.user)
        action = request.data.get('action')
        if action == 'safe':
            checkin.status = 'completed'
            checkin.completed_at = timezone.now()
            checkin.save(update_fields=['status','completed_at'])
            return Response({'id': checkin.id, 'status': checkin.status})
        if action == 'cancel':
            checkin.status = 'cancelled'
            checkin.save(update_fields=['status'])
            return Response({'id': checkin.id, 'status': checkin.status})
        return Response({'detail': 'Use action=safe or action=cancel.'}, status=400)


def notify_participants_for_checkin(checkin):
    # Safety check-in is deliberately low-noise: notify guardians only when a timer is missed.
    try:
        from guardians.models import Guardian
        resident = getattr(checkin.user, 'residentprofile', None)
        if not resident:
            return
        guardians = Guardian.objects.filter(resident=resident, can_receive_alerts=True).select_related('user')
        for guardian in guardians:
            notify_user(
                guardian.user,
                'Safety check-in missed',
                f'{checkin.user.get_full_name() or checkin.user.username} did not confirm their safety by {checkin.due_at.astimezone().strftime("%I:%M %p")}. Please check on them.',
                notification_type='emergency',
            )
    except Exception:
        return


class SmartResponderMatchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        match = smart_match_alert(alert)
        if not match:
            return Response({'matched': False, 'detail': 'No available volunteer is currently eligible.'})
        v, loc = match['volunteer'], match['location']
        return Response({
            'matched': True, 'responder_id': v.user_id, 'responder_name': v.user.get_full_name() or v.user.username,
            'volunteer_role': v.get_role_display(), 'distance_km': match['distance_km'],
            'reliability_score': match['reliability_score'], 'match_score': match['match_score'],
            'latitude': float(loc.latitude) if loc else None, 'longitude': float(loc.longitude) if loc else None,
        })


class ResponderAvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from volunteers.models import Volunteer
        from tracking.models import LiveLocation
        society_id = request.query_params.get('society')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        qs = Volunteer.objects.filter(is_active=True).select_related('user', 'society', 'assigned_block')
        if society_id:
            qs = qs.filter(society_id=society_id)
        elif getattr(request.user, 'role', '') == 'volunteer':
            profile = getattr(request.user, 'volunteer_profile', None)
            if profile: qs = qs.filter(society_id=profile.society_id)
        busy_ids=set(ResponderAssignment.objects.filter(
            responder__role='volunteer', status__in=['assigned','accepted','on_way','arrived'],
            alert__status__in=['open','acknowledged','active','escalated']
        ).values_list('responder_id', flat=True))
        now=timezone.now()
        rows=[]
        for v in qs:
            loc=LiveLocation.objects.filter(user=v.user).first()
            busy=v.user_id in busy_ids
            offline=(not v.available_for_emergency) or (loc is not None and (now-loc.last_updated).total_seconds()>600)
            state='busy' if busy else ('offline' if offline else 'available')
            distance=None
            if lat and lng and loc and loc.is_sharing:
                distance=round(haversine_km(lat,lng,loc.latitude,loc.longitude),3)
            completed=AlertResponse.objects.filter(responder=v.user,status='completed').count()
            rows.append({'id':v.user_id,'name':v.user.get_full_name() or v.user.username,'username':v.user.username,'role':v.get_role_display(),'state':state,'distance_km':distance,'reliability_score':responder_reliability(v.user),'completed_incidents':completed,'block':v.assigned_block.name if v.assigned_block else None,'last_seen':loc.last_updated if loc else None})
        order={'available':0,'busy':1,'offline':2}
        rows.sort(key=lambda x:(order[x['state']], x['distance_km'] if x['distance_km'] is not None else 9999))
        return Response({'summary':{'total':len(rows),'available':sum(x['state']=='available' for x in rows),'busy':sum(x['state']=='busy' for x in rows),'offline':sum(x['state']=='offline' for x in rows)},'responders':rows})


class SOSCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if str(request.user.role).lower() != 'resident':
            return Response({'detail': 'Only residents can activate SOS.'}, status=403)
        resident = get_object_or_404(ResidentProfile, user=request.user)
        data = request.data
        lat = data.get('latitude')
        lng = data.get('longitude')
        if lat in (None, '') or lng in (None, ''):
            return Response({'detail': 'GPS latitude and longitude are required.'}, status=400)
        window = int(data.get('response_window_minutes', 2))
        alert = EmergencyAlert.objects.create(
            resident=resident,
            alert_type=data.get('alert_type', 'SOS Emergency'),
            message=data.get('message', 'Emergency SOS activated'),
            priority='critical',
            status='open',
            latitude=lat,
            longitude=lng,
            response_window_minutes=window,
            escalation_deadline=timezone.now() + timedelta(minutes=window),
        )
        msg = f'{request.user.get_full_name() or request.user.username} activated an emergency SOS. Location: {lat}, {lng}'
        sent = notify_participants(alert, f'SOS Alert #{alert.id}', msg, include_resident=False)

        # Smart Volunteer Matching: identify the best available responder using
        # live GPS distance, emergency role, current workload and response history.
        match = smart_match_alert(alert)
        if match:
            responder = match['volunteer'].user
            ResponderAssignment.objects.update_or_create(
                alert=alert, responder=responder,
                defaults={'assigned_by': None, 'status': 'assigned'},
            )
            notify_user(
                responder,
                f'Smart match — Incident #{alert.id}',
                f'CareConnect selected you as the recommended responder. Match score {match["match_score"]}/100' +
                (f', approximately {match["distance_km"]} km away.' if match['distance_km'] is not None else '.'),
                alert=alert, notification_type='volunteer',
            )
            record_update(alert, request.user, 'smart_matched',
                          f'Recommended responder: {responder.username} (score {match["match_score"]})')

        # Confirmation for the resident proves that the alert was registered.
        notify_user(
            request.user,
            f'SOS #{alert.id} registered',
            f'Your SOS was registered successfully. GPS location captured and {sent} response-network user(s) notified.',
            alert=alert,
        )
        record_update(alert, request.user, 'open', 'SOS activated with GPS location')
        return Response({
            'alert_id': alert.id,
            'status': alert.status,
            'latitude': str(alert.latitude),
            'longitude': str(alert.longitude),
            'notified_users': sent,
            'smart_match': ({
                'responder_id': match['volunteer'].user_id,
                'responder_name': match['volunteer'].user.get_full_name() or match['volunteer'].user.username,
                'distance_km': match['distance_km'],
                'reliability_score': match['reliability_score'],
                'match_score': match['match_score'],
            } if match else None),
        }, status=201)


class CancelSOSView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        if str(request.user.role).lower() != 'resident' or alert.resident.user_id != request.user.id:
            return Response({'detail': 'Only the resident who created the SOS can cancel it.'}, status=403)
        if alert.status not in ('open', 'acknowledged', 'active', 'escalated'):
            return Response({'detail': 'This emergency can no longer be cancelled.'}, status=400)
        if (timezone.now() - alert.created_at).total_seconds() > 15:
            return Response({'detail': 'The cancellation window has expired.'}, status=400)
        alert.status = 'cancelled'
        alert.save(update_fields=['status', 'updated_at'])
        record_update(alert, request.user, 'cancelled', 'SOS cancelled by resident within the cancellation window')
        notify_participants(
            alert,
            f'SOS #{alert.id} cancelled',
            f'{request.user.get_full_name() or request.user.username} cancelled the emergency alert. No response is required.',
            exclude=[request.user],
            include_resident=False,
        )
        return Response({'alert_id': alert.id, 'status': 'cancelled'})


class AlertResponseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        if not can_access_alert(request.user, alert):
            return Response({'detail': 'You do not have access to this incident.'}, status=403)
        role = str(request.user.role).lower()
        action = request.data.get('action', 'accepted')
        if role == 'resident':
            if alert.resident.user_id != request.user.id or action != 'completed':
                return Response({'detail': 'Residents can only close their own emergency with confirmation.'}, status=403)
        elif role not in ('volunteer','security','security_volunteer','security_admin','admin','society_admin','superadmin'):
            return Response({'detail': 'This role is not an emergency responder.'}, status=403)
        response, _ = AlertResponse.objects.get_or_create(
            alert=alert,
            responder=request.user,
            defaults={'role': request.user.role},
        )
        now = timezone.now()
        responder_name = request.user.get_full_name() or request.user.username

        if action == 'accepted':
            response.status = 'accepted'
            response.accepted_at = now
            response.response_time_seconds = max(0, int((now - alert.created_at).total_seconds()))
            response.save()
            ResponderAssignment.objects.update_or_create(
                alert=alert,
                responder=request.user,
                defaults={'assigned_by': request.user, 'status': 'accepted'},
            )
            if alert.status in ('open', 'acknowledged'):
                alert.status = 'acknowledged'
                alert.save(update_fields=['status', 'updated_at'])
            record_update(alert, request.user, 'acknowledged', f'{request.user.username} accepted the emergency')
            notify_participants(
                alert,
                f'Responder accepted - #{alert.id}',
                f'{responder_name} accepted Incident #{alert.id} and is taking responsibility for the response.',
                exclude=[request.user],
                include_resident=True,
            )
        elif action in ('rejected', 'on_way', 'arrived', 'completed'):
            response.status = action
            response.save(update_fields=['status', 'updated_at'])
            assignment, _ = ResponderAssignment.objects.update_or_create(
                alert=alert,
                responder=request.user,
                defaults={'assigned_by': request.user, 'status': action},
            )

            if action == 'rejected':
                record_update(alert, request.user, 'rejected', f'{responder_name} declined the emergency')
                notify_participants(
                    alert,
                    f'Responder declined - #{alert.id}',
                    f'{responder_name} declined Incident #{alert.id}. Other available responders may respond.',
                    exclude=[request.user],
                    include_resident=True,
                )
            elif action == 'on_way':
                if alert.status in ('open', 'acknowledged'):
                    alert.status = 'active'
                    alert.save(update_fields=['status', 'updated_at'])
                record_update(alert, request.user, 'on_way', f'{responder_name} is on the way')
                notify_participants(
                    alert,
                    f'Responder on the way - #{alert.id}',
                    f'{responder_name} is on the way to Incident #{alert.id}.',
                    exclude=[request.user],
                    include_resident=True,
                )
            elif action == 'arrived':
                if alert.status != 'resolved':
                    alert.status = 'active'
                    alert.save(update_fields=['status', 'updated_at'])
                record_update(alert, request.user, 'arrived', f'{responder_name} has arrived at the emergency location')
                notify_participants(
                    alert,
                    f'Responder arrived - #{alert.id}',
                    f'{responder_name} has arrived at Incident #{alert.id}.',
                    exclude=[request.user],
                    include_resident=True,
                )
            elif action == 'completed':
                alert.status = 'resolved'
                alert.resolved_at = now
                alert.closed_by = request.user
                alert.closure_note = request.data.get('closure_note', alert.closure_note or 'Responder marked the incident completed.')
                alert.save(update_fields=['status', 'resolved_at', 'closed_by', 'closure_note', 'updated_at'])
                record_update(alert, request.user, 'resolved', alert.closure_note)
                notify_resolution(alert, request.user, alert.closure_note)

        return Response(AlertResponseSerializer(response).data)


class AlertAssignmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if str(request.user.role).lower() not in ('admin', 'society_admin', 'superadmin', 'security_admin'):
            return Response({'detail': 'Only admin or security can assign responders.'}, status=403)
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        responder = get_object_or_404(User, pk=request.data.get('responder_id'))
        assignment = ResponderAssignment.objects.update_or_create(
            alert=alert,
            responder=responder,
            defaults={'assigned_by': request.user, 'status': 'assigned'},
        )[0]
        notify_user(
            responder,
            f'Responder Assigned - Alert #{alert.id}',
            f'You have been assigned to emergency #{alert.id}. Please review the live GPS location and respond.',
            alert=alert,
        )
        notify_participants(
            alert,
            f'Responder assigned - #{alert.id}',
            f'{responder.get_full_name() or responder.username} has been assigned to Incident #{alert.id}.',
            exclude=[request.user, responder],
            include_resident=True,
        )
        record_update(alert, request.user, 'responder_assigned', f'Assigned to {responder.username}')
        return Response(ResponderAssignmentSerializer(assignment).data, status=201)


class AlertResponsesView(generics.ListAPIView):
    serializer_class = AlertResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        alert = get_object_or_404(EmergencyAlert, pk=self.kwargs['pk'])
        if not can_access_alert(self.request.user, alert):
            raise PermissionDenied('You do not have access to this incident.')
        return AlertResponse.objects.filter(alert_id=self.kwargs['pk']).select_related('responder')


class AlertAssignmentsView(generics.ListAPIView):
    serializer_class = ResponderAssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        alert = get_object_or_404(EmergencyAlert, pk=self.kwargs['pk'])
        if not can_access_alert(self.request.user, alert):
            raise PermissionDenied('You do not have access to this incident.')
        return ResponderAssignment.objects.filter(alert_id=self.kwargs['pk']).select_related('responder')


class IncidentChatView(generics.ListCreateAPIView):
    serializer_class = IncidentMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        alert = get_object_or_404(EmergencyAlert, pk=self.kwargs['pk'])
        if not can_access_alert(self.request.user, alert):
            raise PermissionDenied('You do not have access to this incident.')
        return IncidentMessage.objects.filter(alert_id=self.kwargs['pk']).select_related('sender').order_by('created_at')

    def perform_create(self, serializer):
        alert = get_object_or_404(EmergencyAlert, pk=self.kwargs['pk'])
        if not can_access_alert(self.request.user, alert):
            raise PermissionDenied('You do not have access to this incident.')
        serializer.save(sender=self.request.user, alert=alert)
        notify_participants(
            alert,
            f'Incident update - #{alert.id}',
            f'{self.request.user.get_full_name() or self.request.user.username}: {serializer.instance.message}',
            exclude=[self.request.user],
            include_resident=True,
        )


class IncidentUpdatesView(generics.ListAPIView):
    serializer_class = IncidentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        alert = get_object_or_404(EmergencyAlert, pk=self.kwargs['pk'])
        if not can_access_alert(self.request.user, alert):
            raise PermissionDenied('You do not have access to this incident.')
        return IncidentUpdate.objects.filter(alert_id=self.kwargs['pk']).select_related('actor').order_by('-created_at')


class EscalateAlertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        role = str(request.user.role).lower()
        if role == 'resident' and alert.resident.user_id != request.user.id:
            return Response({'detail': 'You can only escalate your own emergency.'}, status=403)
        if role not in ('resident','admin', 'society_admin', 'superadmin', 'security_admin', 'security','security_volunteer'):
            return Response({'detail': 'This role cannot escalate an emergency.'}, status=403)
        alert.status = 'escalated'
        alert.priority = 'critical'
        alert.save(update_fields=['status', 'priority', 'updated_at'])
        notify_participants(
            alert,
            f'ESCALATED SOS #{alert.id}',
            f'Emergency #{alert.id} requires immediate response.',
            exclude=[request.user],
            include_resident=True,
        )
        record_update(alert, request.user, 'escalated', 'Emergency escalation requested; nearby emergency services should be contacted through the configured deployment process.')
        return Response({'status': 'escalated'})


class NotificationDeliveryView(generics.ListAPIView):
    serializer_class = NotificationDeliverySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationDelivery.objects.filter(notification__recipient=self.request.user).order_by('-created_at')



class SocietyIntelligenceView(APIView):
    """Society-level safety intelligence: incidents, hotspots, response performance and load."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = str(getattr(request.user, 'role', '')).lower()
        if role not in ('admin', 'society_admin', 'superadmin'):
            return Response({'detail': 'Admin/Society Admin privileges are required.'}, status=403)

        alerts = EmergencyAlert.objects.all().select_related('resident__user', 'resident__flat__block')
        if role in ('society_admin','security_admin'):
            society_id = getattr(request.user, 'society_id', None) or getattr(getattr(request.user, 'guard_profile', None), 'society_id', None)
            if not society_id:
                return Response({'detail': 'Society Admin is not assigned to a society.'}, status=403)
            alerts = alerts.filter(resident__flat__block__society_id=society_id)
        total = alerts.count()
        active = alerts.filter(status__in=['open','acknowledged','active','escalated']).count()
        resolved = alerts.filter(status='resolved').count()

        by_type = list(alerts.values('alert_type').annotate(count=Count('id')).order_by('-count')[:8])
        by_status = list(alerts.values('status').annotate(count=Count('id')).order_by('-count'))
        hotspot_rows = alerts.exclude(resident__flat__block__isnull=True).values(
            'resident__flat__block__name'
        ).annotate(count=Count('id')).order_by('-count')[:8]
        hotspots = [{'block': x['resident__flat__block__name'] or 'Unknown', 'count': x['count']} for x in hotspot_rows]

        response_rows = []
        vol_qs = Volunteer.objects.filter(is_active=True).select_related('user','assigned_block')
        if role == 'society_admin':
            vol_qs = vol_qs.filter(society_id=request.user.society_id)
        for v in vol_qs:
            responses = AlertResponse.objects.filter(responder=v.user)
            completed = responses.filter(status='completed').count()
            avg = responses.filter(response_time_seconds__isnull=False).aggregate(avg=Avg('response_time_seconds'))['avg']
            active_load = ResponderAssignment.objects.filter(
                responder=v.user, status__in=['assigned','accepted','on_way','arrived'],
                alert__status__in=['open','acknowledged','active','escalated']
            ).count()
            response_rows.append({
                'id': v.user_id, 'name': v.user.get_full_name() or v.user.username,
                'block': v.assigned_block.name if v.assigned_block else None,
                'role': v.get_role_display(), 'available': bool(v.available_for_emergency),
                'active_load': active_load, 'completed': completed,
                'avg_response_seconds': round(float(avg),1) if avg is not None else None,
                'reliability_score': responder_reliability(v.user),
            })
        response_rows.sort(key=lambda x: (-x['reliability_score'], x['active_load']))

        ownership = []
        for alert in alerts.filter(status__in=['open','acknowledged','active','escalated']).order_by('-created_at')[:10]:
            assignment = alert.assignments.filter(status__in=['assigned','accepted','on_way','arrived']).select_related('responder').order_by('-updated_at').first()
            ownership.append({
                'alert_id': alert.id, 'type': alert.alert_type, 'status': alert.status,
                'owner': (assignment.responder.get_full_name() or assignment.responder.username) if assignment else None,
                'owner_id': assignment.responder_id if assignment else None,
                'owner_status': assignment.status if assignment else 'unassigned',
                'created_at': alert.created_at,
            })

        avg_response = AlertResponse.objects.filter(response_time_seconds__isnull=False).aggregate(avg=Avg('response_time_seconds'))['avg']
        return Response({
            'summary': {
                'total_incidents': total, 'active_incidents': active, 'resolved_incidents': resolved,
                'avg_response_seconds': round(float(avg_response),1) if avg_response is not None else None,
                'available_volunteers': sum(1 for x in response_rows if x['available'] and x['active_load']==0),
                'busy_volunteers': sum(1 for x in response_rows if x['active_load']>0),
                'overloaded_volunteers': sum(1 for x in response_rows if x['active_load']>=2),
            },
            'by_type': by_type, 'by_status': by_status, 'hotspots': hotspots,
            'responders': response_rows[:12], 'ownership': ownership,
        })

class OpenIncidentsView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = __import__('emergency_alerts.serializers', fromlist=['EmergencyAlertSerializer']).EmergencyAlertSerializer

    def get_queryset(self):
        qs = EmergencyAlert.objects.all().select_related('resident__user').filter(
            status__in=['open', 'acknowledged', 'active', 'escalated']
        ).order_by('-created_at')
        role = str(getattr(self.request.user, 'role', '')).lower()
        if role in ('admin', 'superadmin'):
            return qs
        society_id = getattr(self.request.user, 'society_id', None)
        if role == 'society_admin' and society_id:
            return qs.filter(resident__flat__block__society_id=society_id)
        if role in ('volunteer','security_volunteer','security'):
            society_id = getattr(getattr(self.request.user, 'volunteer_profile', None), 'society_id', None) or getattr(getattr(self.request.user, 'guard_profile', None), 'society_id', None)
            assigned = ResponderAssignment.objects.filter(responder=self.request.user).values_list('alert_id', flat=True)
            return qs.filter(resident__flat__block__society_id=society_id).filter(Q(id__in=assigned) | Q(priority='critical'))
        return qs.filter(resident__user=self.request.user)


class IncidentAudioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        if not can_access_alert(request.user, alert):
            return Response({'detail': 'You do not have access to this incident.'}, status=403)
        audio = request.FILES.get('audio')
        if not audio:
            return Response({'detail': 'Audio file is required.'}, status=400)
        obj = IncidentAudio.objects.create(alert=alert, sender=request.user, audio=audio)
        notify_participants(
            alert,
            f'Audio incident note - #{alert.id}',
            f'{request.user.get_full_name() or request.user.username} added an audio note to Incident #{alert.id}.',
            exclude=[request.user],
            include_resident=True,
        )
        return Response({'id': obj.id, 'audio': request.build_absolute_uri(obj.audio.url), 'created_at': obj.created_at}, status=201)

    def get(self, request, pk):
        alert = get_object_or_404(EmergencyAlert, pk=pk)
        if not can_access_alert(request.user, alert):
            return Response({'detail': 'You do not have access to this incident.'}, status=403)
        return Response([
            {
                'id': x.id,
                'sender': x.sender.username,
                'audio': request.build_absolute_uri(x.audio.url),
                'created_at': x.created_at,
            }
            for x in alert.audio_notes.select_related('sender').order_by('created_at')
        ])
