from rest_framework import serializers
from .models import FriendRequest, Friend
from users.models import User
from users.utils import is_blocked


class FriendRequestSerializer(serializers.ModelSerializer):
    from_user_username = serializers.CharField(source='from_user.username', read_only=True)
    to_user_username = serializers.CharField(write_only=True)
    to_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = FriendRequest
        fields = [
            'id',
            'from_user',
            'from_user_username',
            'to_user',
            'to_user_username',
            'is_accepted',
            'created_at',
        ]
        read_only_fields = ['from_user', 'to_user', 'is_accepted', 'created_at']

    def validate_to_user_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this username does not exist.")

        request_user = self.context['request'].user

        if request_user == user:
            raise serializers.ValidationError("You cannot send a friend request to yourself.")

        from users.utils import is_blocked
        if is_blocked(request_user, user) or is_blocked(user, request_user):
            raise serializers.ValidationError("You cannot send a friend request to this user.")

        return user


    def create(self, validated_data):
        from_user = self.context['request'].user
        to_user = validated_data.pop('to_user_username')

        if is_blocked(from_user, to_user) or is_blocked(to_user, from_user):
            raise serializers.ValidationError("You cannot send a request to this user.")

        if Friend.objects.filter(user=from_user, friend=to_user).exists():
            raise serializers.ValidationError("You are already friends with this user.")

        if FriendRequest.objects.filter(from_user=from_user, to_user=to_user).exists():
            raise serializers.ValidationError("Friend request already sent.")

        reverse_request = FriendRequest.objects.filter(from_user=to_user, to_user=from_user).first()
        if reverse_request:
            Friend.objects.get_or_create(user=from_user, friend=to_user)
            Friend.objects.get_or_create(user=to_user, friend=from_user)
            reverse_request.delete()

        return FriendRequest.objects.create(from_user=from_user, to_user=to_user)


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class FriendSerializer(serializers.ModelSerializer):
    friend = UserShortSerializer(read_only=True)

    class Meta:
        model = Friend
        fields = ['id', 'friend']
