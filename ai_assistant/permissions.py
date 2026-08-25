from rest_framework.permissions import BasePermission

class CareConnectAssistantPermission(BasePermission):
    message = 'CareConnect Assistant requires an authenticated CareConnect user.'
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
