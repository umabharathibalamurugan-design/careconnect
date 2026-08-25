from rest_framework import generics, permissions
from django.db.models import Q
from emergency_alerts.models import EmergencyAlert
from emergency_alerts.serializers import EmergencyAlertSerializer


class AdminEmergencyAlertListView(generics.ListAPIView):
    serializer_class = EmergencyAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from response.services import auto_escalate_expired
        auto_escalate_expired()
        role = str(self.request.user.role).lower()
        if role not in ('admin', 'society_admin', 'superadmin', 'security_admin', 'security', 'security_volunteer'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Admin privileges are required to view emergency alerts.')
        qs = EmergencyAlert.objects.all().select_related('resident__user').order_by('-created_at')
        if role in ('admin', 'superadmin'):
            return qs
        society_id = getattr(self.request.user, 'society_id', None)
        if role == 'security':
            profile = getattr(self.request.user, 'guard_profile', None)
            society_id = getattr(profile, 'society_id', society_id)
        if role == 'society_admin' and society_id:
            return qs.filter(resident__flat__block__society_id=society_id)
        if role == 'security_admin' and society_id:
            return qs.filter(resident__flat__block__society_id=society_id)
        if role in ('security', 'security_volunteer') and society_id:
            from response.models import ResponderAssignment
            assigned = set(ResponderAssignment.objects.filter(responder=self.request.user, alert__status__in=['open','acknowledged','active','escalated']).values_list('alert_id', flat=True))
            society_alerts = qs.filter(resident__flat__block__society_id=society_id)
            return society_alerts.filter(id__in=assigned) | society_alerts.filter(priority='critical', status__in=['open','acknowledged','active','escalated'])
        return qs.none()


class EmergencyAlertListCreateView(generics.ListCreateAPIView):
    serializer_class = EmergencyAlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from response.services import auto_escalate_expired
        auto_escalate_expired()
        user = self.request.user
        role = str(user.role).lower()
        base = EmergencyAlert.objects.all().select_related('resident__user').order_by('-created_at')
        if role in ('admin', 'superadmin'):
            return base
        if role in ('society_admin','security_admin','security','security_volunteer'):
            society_id = getattr(user, 'society_id', None)
            if role in ('security','security_admin','security_volunteer'):
                profile = getattr(user, 'guard_profile', None)
                society_id = getattr(profile, 'society_id', society_id)
            if not society_id:
                return base.none()
            society_base = base.filter(resident__flat__block__society_id=society_id)
            if role in ('security','security_volunteer'):
                from response.models import ResponderAssignment
                assigned = ResponderAssignment.objects.filter(responder=user, alert__status__in=['open','acknowledged','active','escalated']).values_list('alert_id', flat=True)
                return society_base.filter(Q(id__in=assigned) | Q(priority='critical', status__in=['open','acknowledged','active','escalated']))
            return society_base
        if role == 'volunteer':
            from volunteers.models import Volunteer
            v = Volunteer.objects.filter(user=user).first()
            if v and v.society_id:
                return base.filter(
                    resident__flat__block__society_id=v.society_id,
                    status__in=['open', 'acknowledged', 'active', 'escalated'],
                )
            return base.none()
        if role == 'guardian':
            from guardians.models import Guardian
            links = Guardian.objects.filter(user=user).values_list('resident_id', flat=True)
            return base.filter(resident_id__in=links)
        return base.filter(resident__user=user)

    def perform_create(self, serializer):
        if str(self.request.user.role).lower() != 'resident':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only residents can create emergency alerts. Use the SOS endpoint.')
        from residents.models import ResidentProfile
        resident = ResidentProfile.objects.get(user=self.request.user)
        serializer.save(resident=resident)


class EmergencyAlertDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = EmergencyAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    queryset = EmergencyAlert.objects.all().select_related('resident__user')

    def perform_update(self, serializer):
        data_status = self.request.data.get('status')
        if isinstance(data_status, str):
            serializer.validated_data['status'] = data_status.lower()

        previous_status = serializer.instance.status
        alert = serializer.save()

        if alert.status == 'resolved':
            from django.utils import timezone
            alert.resolved_at = timezone.now()
            alert.closed_by = self.request.user
            alert.closure_note = self.request.data.get('closure_note', alert.closure_note or 'Incident resolved from Response Center.')
            alert.save(update_fields=['resolved_at', 'closed_by', 'closure_note', 'updated_at'])

        from response.services import record_update, notify_resolution, notify_participants
        record_update(alert, self.request.user, alert.status, 'Incident status updated from Response Center')

        if previous_status != alert.status:
            actor_name = self.request.user.get_full_name() or self.request.user.username
            if alert.status == 'resolved':
                notify_resolution(alert, self.request.user, alert.closure_note)
            elif alert.status == 'cancelled':
                notify_participants(
                    alert,
                    f'Incident #{alert.id} cancelled',
                    f'Incident #{alert.id} was cancelled by {actor_name}. No further response is required.',
                    exclude=[self.request.user],
                    include_resident=True,
                )
            elif alert.status == 'escalated':
                notify_participants(
                    alert,
                    f'Incident #{alert.id} escalated',
                    f'Incident #{alert.id} was escalated by {actor_name} and requires immediate response.',
                    exclude=[self.request.user],
                    include_resident=True,
                )
            else:
                notify_participants(
                    alert,
                    f'Incident #{alert.id} status updated',
                    f'Incident #{alert.id} is now {alert.get_status_display()}. Updated by {actor_name}.',
                    exclude=[self.request.user],
                    include_resident=True,
                )
