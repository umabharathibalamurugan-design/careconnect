from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'user', None) == request.user


def role_is(user, *roles):
    return bool(user and user.is_authenticated and str(getattr(user, 'role', '')).lower() in roles)


class IsRole(permissions.BasePermission):
    """Role gate for API endpoints. Example: IsRole('security_admin')."""
    allowed_roles = ()

    def __init__(self, *roles):
        self.allowed_roles = tuple(roles)

    def has_permission(self, request, view):
        return role_is(request.user, *self.allowed_roles)


class IsSecurityAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return role_is(request.user, 'security_admin', 'society_admin', 'admin', 'superadmin')


class IsSecurityResponder(permissions.BasePermission):
    def has_permission(self, request, view):
        return role_is(request.user, 'security_volunteer', 'security', 'volunteer', 'security_admin', 'society_admin', 'admin', 'superadmin')
