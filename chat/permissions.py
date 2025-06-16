from rest_framework import permissions
from .models import Group

class IsGroupMember(permissions.BasePermission):
    def has_permission(self, request, view):
        group_id = view.kwargs.get("group_pk")
        if not group_id:
            return False
        return Group.objects.filter(pk=group_id, members=request.user).exists()
