from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, permissions
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from .filters import GroupMessageFilter

from .models import DirectMessage, Group
from .serializers import (
    DirectMessageSerializer, GroupSerializer, GroupMessageSerializer,
    LeaveGroupSerializer, TransferOwnershipSerializer, RemoveMembersSerializer,
    DeleteGroupSerializer, AddGroupMembersSerializer,
)
from .permissions import IsGroupMember

User = get_user_model()
from users.utils import is_blocked



class DirectMessageViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin,
    mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = DirectMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def get_other_user(self):
        username = self.kwargs.get("username")
        if not username:
            raise NotFound("Username parameter required")
        return get_object_or_404(User, username=username)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return DirectMessage.objects.none()
        other = self.get_other_user()
        return DirectMessage.objects.filter(
            Q(sender=self.request.user, recipient=other) |
            Q(sender=other, recipient=self.request.user)
        ).order_by("-created_at")

    def perform_create(self, serializer):
        recipient = self.get_other_user()
        if is_blocked(self.request.user, recipient):
            raise PermissionDenied()
        serializer.save(sender=self.request.user, recipient=recipient)

    def perform_destroy(self, instance):
        if instance.sender != self.request.user:
            raise PermissionDenied("You can only delete messages you sent")
        instance.delete()


class GroupViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin,
    mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "pk"

    def perform_create(self, serializer):
        group = serializer.save(owner=self.request.user)
        group.members.add(self.request.user)

        members = self.request.data.get('members', '')
        if members:
            # Split by commas, strip spaces
            usernames = [username.strip() for username in members.split(',') if username.strip()]
            users_to_add = User.objects.filter(username__in=usernames).exclude(id=self.request.user.id)
            allowed_users = [u for u in users_to_add if not is_blocked(self.request.user, u)]
            group.members.add(*allowed_users)

    def get_queryset(self):
        return Group.objects.filter(members=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        return {
            'leave': LeaveGroupSerializer,
            'transfer_owner': TransferOwnershipSerializer,
            'remove_members': RemoveMembersSerializer,
            'delete_group': DeleteGroupSerializer,
            'add_members': AddGroupMembersSerializer,
        }.get(self.action, GroupSerializer)

    def get_object(self):
        pk = self.kwargs.get('pk')
        print(f"Received group pk: {pk} (type: {type(pk)})")
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            raise NotFound("Invalid group id")
        return get_object_or_404(Group, pk=pk)


    def get_group(self):
        group_pk = self.kwargs.get("group_pk")
        try:
            group_pk = int(group_pk)
        except (ValueError, TypeError):
            raise NotFound("Invalid group id")
        return get_object_or_404(Group, pk=group_pk, members=self.request.user)


    def _owner_required(self, group):
        if self.request.user != group.owner:
            raise PermissionDenied("Only the group owner can perform this action.")

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        group = self.get_object()
        if request.user == group.owner:
            return Response({"detail": "Owner cannot leave the group."}, status=400)
        if request.user not in group.members.all():
            return Response({"detail": "You are not a member of this group."}, status=404)
        group.members.remove(request.user)
        return Response({"detail": "You have left the group."})

    @action(detail=True, methods=['post'])
    def transfer_owner(self, request, pk=None):
        group = self.get_object()
        self._owner_required(group)
        serializer = self.get_serializer(data=request.data, context={'group': group, 'request': request})
        serializer.is_valid(raise_exception=True)
        group.owner = get_object_or_404(User, username=serializer.validated_data['new_owner_username'])
        group.save()
        return Response({"detail": f"Ownership transferred to {group.owner.username}."})

    @action(detail=True, methods=['post'])
    def remove_members(self, request, pk=None):
        group = self.get_object()
        self._owner_required(group)
        serializer = self.get_serializer(data=request.data, group=group, current_user=request.user)
        serializer.is_valid(raise_exception=True)
        group.members.remove(*serializer.validated_data['members'])
        return Response({"removed": [u.username for u in serializer.validated_data['members']]})

    @action(detail=True, methods=['post'])
    def delete_group(self, request, pk=None):
        group = self.get_object()
        self._owner_required(group)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data.get('confirm'):
            return Response({"detail": "Please confirm deletion."}, status=400)
        group.delete()
        return Response({"detail": "Group successfully deleted."})

    @action(detail=True, methods=['post'])
    def add_members(self, request, pk=None):
        group = self.get_object()
        self._owner_required(group)
        serializer = self.get_serializer(data=request.data, group=group, current_user=request.user)
        serializer.is_valid(raise_exception=True)

        members_to_add = [
            member for member in serializer.validated_data['members']
            if not is_blocked(request.user, member)
        ]

        group.members.add(*members_to_add)
        return Response({"detail": "Members added successfully."})


class GroupMessagesViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    serializer_class = GroupMessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsGroupMember]
    filter_backends = [DjangoFilterBackend]
    filterset_class = GroupMessageFilter

    def get_group(self):
        group_pk = self.kwargs.get("group_pk")
        try:
            group_pk = int(group_pk)
        except (ValueError, TypeError):
            raise NotFound("Invalid group id")
        return get_object_or_404(Group, pk=group_pk, members=self.request.user)

    def get_queryset(self):
        return self.get_group().messages.all().order_by("-created_at")

    def perform_create(self, serializer):
        group = self.get_group()
        for member in group.members.all():
            if is_blocked(self.request.user, member):
                raise PermissionDenied()
        serializer.save(group=group, sender=self.request.user)
