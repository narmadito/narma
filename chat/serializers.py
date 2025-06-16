from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.utils import is_blocked
from .models import DirectMessage, Group, GroupMessage
from friends.models import Friend

User = get_user_model()


class DirectMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectMessage
        fields = ['id', 'sender', 'recipient', 'message', 'created_at']
        read_only_fields = ['id', 'sender', 'recipient', 'created_at']


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.CharField(
        write_only=True,
        help_text="Enter usernames of your friends separated by commas, e.g., randomuser, user, user123"
    )
    member_details = serializers.SerializerMethodField(read_only=True)
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'owner_username', 'members', 'member_details', 'created_at']
        read_only_fields = ['id', 'owner_username', 'created_at']

    def get_member_details(self, obj):
        return [{'id': user.id, 'username': user.username} for user in obj.members.all()]

    def validate_members(self, value):
        usernames = [u.strip() for u in value.split(',')]
        request_user = self.context['request'].user

        if request_user.username in usernames:
            raise serializers.ValidationError("You cannot add yourself.")

        if len(usernames) + 1 > 10:
            raise serializers.ValidationError("Maximum of 10 users allowed in a group including you.")

        existing_users = User.objects.filter(username__in=usernames)
        existing_usernames = set(existing_users.values_list('username', flat=True))

        friend_usernames = set(
            Friend.objects.filter(user=request_user).values_list('friend__username', flat=True)
        )

        invalid_usernames = [
            u for u in usernames if u not in existing_usernames or u not in friend_usernames
        ]

        if invalid_usernames:
            raise serializers.ValidationError(
                f"Some users do not exist or are not your friends: {', '.join(invalid_usernames)}"
            )

        # ახალი: დაბლოკილი მომხმარებლების გამორჩევა
        blocked_users = [u.username for u in existing_users if is_blocked(request_user, u)]
        if blocked_users:
            raise serializers.ValidationError(
                f"Cannot add some users"
            )

        return existing_users

    def create(self, validated_data):
        users = validated_data.pop('members', [])
        owner = self.context['request'].user

        allowed_users = [u for u in users if not is_blocked(owner, u)]

        validated_data['owner'] = owner
        group = Group.objects.create(**validated_data)
        group.members.set(allowed_users + [owner])
        return group


class GroupMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source='sender.username', read_only=True)

    class Meta:
        model = GroupMessage
        fields = ['id', 'sender_username', 'content', 'created_at']
        read_only_fields = ['id', 'sender_username', 'created_at']


class LeaveGroupSerializer(serializers.Serializer):
    pass


class TransferOwnershipSerializer(serializers.Serializer):
    new_owner_username = serializers.CharField()

    def validate_new_owner_username(self, value):
        request_user = self.context['request'].user
        group = self.context['group']

        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        if user == request_user:
            raise serializers.ValidationError("You cannot transfer ownership to yourself.")

        if user not in group.members.all():
            raise serializers.ValidationError("User must be a member of the group.")

        return value


class RemoveMembersSerializer(serializers.Serializer):
    members = serializers.CharField(
        help_text='Enter usernames separated by commas, e.g., user1, user2'
    )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def validate_members(self, value):
        usernames = [u.strip() for u in value.split(',') if u.strip()]
        if not usernames:
            raise serializers.ValidationError("At least one user must be specified.")

        if self.current_user.username in usernames:
            raise serializers.ValidationError("You cannot remove yourself.")

        users = User.objects.filter(username__in=usernames)
        found_usernames = set(users.values_list('username', flat=True))
        group_member_usernames = set(self.group.members.values_list('username', flat=True))

        invalid_usernames = [
            username for username in usernames
            if username not in found_usernames or username not in group_member_usernames
        ]

        if invalid_usernames:
            raise serializers.ValidationError(
                f"These users are not members of the group or do not exist: {', '.join(invalid_usernames)}"
            )

        self.validated_users = users
        return value

    def validate(self, attrs):
        attrs['members'] = getattr(self, 'validated_users', [])
        return attrs


class DeleteGroupSerializer(serializers.Serializer):
    confirm = serializers.BooleanField(help_text="Set true to confirm group deletion")


class AddGroupMembersSerializer(serializers.Serializer):
    members = serializers.CharField(
        help_text='Enter usernames separated by commas, e.g., user1, user2'
    )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

    def validate_members(self, value):
        usernames = [u.strip() for u in value.split(',') if u.strip()]
        if not usernames:
            raise serializers.ValidationError("At least one user must be specified.")

        group_members = set(self.group.members.values_list('username', flat=True))
        if any(username in group_members for username in usernames):
            raise serializers.ValidationError("Some users are already members of the group.")

        if len(group_members) + len(usernames) > 10:
            raise serializers.ValidationError("Maximum of 10 members allowed in a group.")

        existing_users = User.objects.filter(username__in=usernames)
        existing_usernames = set(existing_users.values_list('username', flat=True))

        friend_usernames = set(
            Friend.objects.filter(user=self.current_user).values_list('friend__username', flat=True)
        )

        invalid_usernames = [
            u for u in usernames if u not in existing_usernames or u not in friend_usernames
        ]

        if invalid_usernames:
            raise serializers.ValidationError(
                f"Some users do not exist or are not your friends: {', '.join(invalid_usernames)}"
            )

        self.validated_users = existing_users
        return value

    def validate(self, attrs):
        attrs['members'] = self.validated_users
        return attrs
