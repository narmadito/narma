from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FriendRequestViewSet, FriendViewSet

router = DefaultRouter()
router.register('friend_requests', FriendRequestViewSet, basename='friend_request')
router.register('friends', FriendViewSet, basename='friend')

urlpatterns = [
    path('', include(router.urls)),
]
