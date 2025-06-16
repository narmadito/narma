from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import FriendRequest, Friend
from .serializers import FriendRequestSerializer, FriendSerializer
from users.utils import is_blocked


class FriendRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = FriendRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(to_user=self.request.user)

    def get_serializer_context(self):
        return {'request': self.request}

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        fr = self.get_object()
        if fr.to_user != request.user:
            raise PermissionDenied("Cannot accept this request.")
        if fr.is_accepted:
            return Response({"detail": "Already accepted."}, status=400)

        fr.is_accepted = True
        fr.save()
        Friend.objects.get_or_create(user=fr.from_user, friend=fr.to_user)
        Friend.objects.get_or_create(user=fr.to_user, friend=fr.from_user)
        fr.delete()
        return Response({'status': 'Friendship accepted ✅'}, status=200)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk=None):
        fr = self.get_object()
        if fr.to_user != request.user:
            raise PermissionDenied("Cannot decline this request.")
        if fr.is_accepted:
            return Response({"detail": "Already accepted."}, status=400)

        fr.delete()
        return Response({'status': 'Friend request declined ❌'}, status=200)


class FriendViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet
):
    serializer_class = FriendSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Friend.objects.filter(user=user)
        for friendship in qs:
            if is_blocked(user, friendship.friend) or is_blocked(friendship.friend, user):
                Friend.objects.filter(user=user, friend=friendship.friend).delete()
                Friend.objects.filter(user=friendship.friend, friend=user).delete()
        return Friend.objects.filter(user=user)

    def get_object(self):
        queryset = self.get_queryset()
        filter_kwargs = {'pk': self.kwargs.get(self.lookup_field)}
        try:
            obj = queryset.get(**filter_kwargs)
        except Friend.DoesNotExist:
            raise NotFound(detail="No Friend matches the given query.")
        self.check_object_permissions(self.request, obj)
        return obj

    @action(detail=True, methods=['post'])
    def unfriend(self, request, pk=None):
        friend = self.get_object()
        Friend.objects.filter(user=friend.user, friend=friend.friend).delete()
        Friend.objects.filter(user=friend.friend, friend=friend.user).delete()
        return Response({'status': 'Friend removed.'}, status=200)
