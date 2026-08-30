from rest_framework.permissions import SAFE_METHODS, BasePermission


class CanManageJobPosting(BasePermission):
    """hr/admin manage any posting; managers may only draft (create/edit their
    own draft postings) per §6.3's 'draft only' row."""

    def has_permission(self, request, view):
        role = request.user.role
        if role in ("hr", "admin"):
            return True
        if role == "manager":
            return True  # object-level check narrows to draft-only edits
        return request.method in SAFE_METHODS

    def has_object_permission(self, request, view, obj):
        role = request.user.role
        if role in ("hr", "admin"):
            return True
        if role == "manager":
            if request.method in SAFE_METHODS:
                return True
            return obj.status == obj.Status.DRAFT
        return request.method in SAFE_METHODS
