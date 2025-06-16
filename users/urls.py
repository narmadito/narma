from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    RegisterViewSet, ProfileViewSet, PublicProfileViewSet, UserListViewSet,
    ResetPasswordViewSet, PasswordResetConfirmViewSet, EmailChangeViewSet, BlockViewSet
)

router = DefaultRouter()
router.register('users', UserListViewSet, basename='user')
router.register('register', RegisterViewSet, basename='user-registration')
router.register('profile', PublicProfileViewSet, basename='profile')
router.register('reset_password', ResetPasswordViewSet, basename='reset')
router.register('email_change', EmailChangeViewSet, basename='email-change')
router.register('blocks', BlockViewSet, basename='blocks')


urlpatterns = [
    path('password_reset_confirm/<uidb64>/<token>/', PasswordResetConfirmViewSet.as_view({'post': 'create'}), name='password_reset_confirm'),
    path('', include(router.urls)),
]
