from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from django.urls import path, include
from .views import DirectMessageViewSet, GroupViewSet, GroupMessagesViewSet

router = DefaultRouter()
router.register('groups', GroupViewSet, basename='groups')

groups_router = routers.NestedDefaultRouter(router, 'groups', lookup='group')
groups_router.register('messages', GroupMessagesViewSet, basename='group-messages')

dm_list = DirectMessageViewSet.as_view({'get': 'list', 'post': 'create'})
dm_detail = DirectMessageViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'})

urlpatterns = [
    path('dm/<str:username>/', dm_list, name='user-messages-list-create'),
    path('dm/<str:username>/<int:pk>/', dm_detail, name='user-messages-detail'),

    path('', include(router.urls)),
    path('', include(groups_router.urls)),
]
