from rest_framework.permissions import BasePermission


class IsHRorAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("hr", "admin"))


class IsManagerOfPerson(BasePermission):
    """Object-level: manager may access records of their direct reports only."""

    def has_object_permission(self, request, view, obj):
        person = getattr(obj, "person", obj)
        emp = getattr(person, "employment", None)
        return bool(emp and emp.manager and emp.manager.user_id == request.user.id)


class IsSelf(BasePermission):
    def has_object_permission(self, request, view, obj):
        person = getattr(obj, "person", obj)
        return person.user_id == request.user.id


class IsManagerOrHRorAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role in ("manager", "hr", "admin")
        )
