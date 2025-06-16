from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsObjectOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return request.user == obj
    
class IsNotAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return not request.user or not request.user.is_authenticated
    
class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
