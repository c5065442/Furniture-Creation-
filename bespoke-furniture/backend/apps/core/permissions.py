from rest_framework.permissions import SAFE_METHODS, BasePermission

STAFF_ROLES = {"ADMIN", "SALES", "WAREHOUSE"}


class IsStaff(BasePermission):
    """Allows access only to authenticated users with a staff role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in STAFF_ROLES)


class IsStaffOrReadOnly(BasePermission):
    """Public read access; writes restricted to staff roles."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in STAFF_ROLES)


class IsDriver(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "DRIVER")
