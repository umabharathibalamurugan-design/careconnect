from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from .models import SecurityGuard
from .serializers import SecurityGuardSerializer


ADMIN_ROLES = {'security_admin', 'society_admin', 'admin', 'superadmin'}
RESPONDER_ROLES = {'security_volunteer', 'security'}


def society_for(user):
    if user.role in ('admin', 'superadmin'):
        return None
    profile = getattr(user, 'guard_profile', None)
    return getattr(profile, 'society_id', None) or getattr(user, 'society_id', None)


class SecurityGuardListCreateView(generics.ListCreateAPIView):
    serializer_class = SecurityGuardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = str(user.role).lower()
        if role in ADMIN_ROLES:
            qs = SecurityGuard.objects.select_related('user', 'society').all()
            sid = society_for(user)
            if role == 'security_admin' and sid:
                qs = qs.filter(society_id=sid)
            return qs
        if role in RESPONDER_ROLES:
            return SecurityGuard.objects.filter(user=user).select_related('user', 'society')
        raise PermissionDenied('Security workspace access is required.')

    def perform_create(self, serializer):
        if str(self.request.user.role).lower() not in ADMIN_ROLES:
            raise PermissionDenied('Only Security Admin or higher roles can create security staff.')
        serializer.save()


class SecurityGuardDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SecurityGuardSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = str(user.role).lower()
        if role in ADMIN_ROLES:
            qs = SecurityGuard.objects.select_related('user', 'society').all()
            sid = society_for(user)
            if role == 'security_admin' and sid:
                qs = qs.filter(society_id=sid)
            return qs
        if role in RESPONDER_ROLES:
            return SecurityGuard.objects.filter(user=user)
        return SecurityGuard.objects.none()

    def update(self, request, *args, **kwargs):
        if str(request.user.role).lower() not in ADMIN_ROLES:
            raise PermissionDenied('Security Volunteers can view their own profile but cannot edit security administration data.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if str(request.user.role).lower() not in ADMIN_ROLES:
            raise PermissionDenied('Only Security Admin can remove security staff.')
        return super().destroy(request, *args, **kwargs)
