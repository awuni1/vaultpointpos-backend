from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Allows access only to admin users."""

    message = 'Access restricted to administrators only.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsManager(BasePermission):
    """Allows access to admin and manager users."""

    message = 'Access restricted to managers and administrators.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ['admin', 'manager']
        )


class IsCashier(BasePermission):
    """Allows access to any authenticated user (admin, manager, cashier)."""

    message = 'Authentication required.'

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAdminOrManager(BasePermission):
    """Allows access to admin and manager users (alias for IsManager)."""

    message = 'Access restricted to administrators and managers.'

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ['admin', 'manager']
        )
