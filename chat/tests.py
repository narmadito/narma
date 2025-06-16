from django.test import TestCase
from django.contrib.auth import get_user_model

from .serializers import (
    GroupSerializer,
    AddGroupMembersSerializer,
    RemoveMembersSerializer,
    TransferOwnershipSerializer,
    LeaveGroupSerializer,
    DeleteGroupSerializer,
)
from friends.models import Friend
from .models import Group

User = get_user_model()


class GroupSerializerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@gmail.com', password='pass')
        self.friend1 = User.objects.create_user(username='friend1', email='friend1@gmail.com', password='pass')
        self.friend2 = User.objects.create_user(username='friend2', email='friend2@gmail.com', password='pass')
        self.not_friend = User.objects.create_user(username='notfriend', email='notfriend@gmail.com', password='pass')

        Friend.objects.create(user=self.owner, friend=self.friend1)
        Friend.objects.create(user=self.owner, friend=self.friend2)

        self.context = {'request': type('Request', (), {'user': self.owner})()}

    def test_valid_members(self):
        data = {'name': 'Group1', 'members': 'friend1, friend2'}
        serializer = GroupSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_add_self(self):
        data = {'name': 'Group1', 'members': 'owner, friend1'}
        serializer = GroupSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('You cannot add yourself.', str(serializer.errors))

    def test_members_must_be_friends(self):
        data = {'name': 'Group1', 'members': 'notfriend'}
        serializer = GroupSerializer(data=data, context=self.context)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Some users do not exist or are not your friends', str(serializer.errors))

    def test_create_group_success(self):
        data = {'name': 'Group1', 'members': 'friend1, friend2'}
        serializer = GroupSerializer(data=data, context=self.context)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        group = serializer.save()
        self.assertEqual(group.owner, self.owner)

        self.assertIn(self.owner, group.members.all())
        self.assertIn(self.friend1, group.members.all())
        self.assertIn(self.friend2, group.members.all())


class AddGroupMembersSerializerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner2@gmail.com', password='pass')
        self.friend1 = User.objects.create_user(username='friend1', email='friend1_2@gmail.com', password='pass')
        self.friend2 = User.objects.create_user(username='friend2', email='friend2_2@gmail.com', password='pass')

        Friend.objects.create(user=self.owner, friend=self.friend1)
        Friend.objects.create(user=self.owner, friend=self.friend2)

        self.group = Group.objects.create(name='Group2', owner=self.owner)
        self.group.members.set([self.owner])

    def test_add_valid_members(self):
        data = {'members': 'friend1, friend2'}
        serializer = AddGroupMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_add_already_member(self):
        self.group.members.add(self.friend1)
        data = {'members': 'friend1'}
        serializer = AddGroupMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('already members', str(serializer.errors))

    def test_cannot_add_non_friend(self):
        not_friend = User.objects.create_user(username='notfriend', email='notfriend2@gmail.com', password='pass')
        data = {'members': 'notfriend'}
        serializer = AddGroupMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('do not exist or are not your friends', str(serializer.errors))


class RemoveGroupMembersSerializerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner3@gmail.com', password='pass')
        self.friend1 = User.objects.create_user(username='friend1', email='friend1_3@gmail.com', password='pass')
        self.friend2 = User.objects.create_user(username='friend2', email='friend2_3@gmail.com', password='pass')

        self.group = Group.objects.create(name='Group3', owner=self.owner)
        self.group.members.set([self.owner, self.friend1, self.friend2])

    def test_remove_valid_member(self):
        data = {'members': 'friend1'}
        serializer = RemoveMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_remove_self(self):
        data = {'members': 'owner'}
        serializer = RemoveMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('cannot remove yourself', str(serializer.errors))

    def test_cannot_remove_non_member(self):
        data = {'members': 'notamember'}
        serializer = RemoveMembersSerializer(
            data=data,
            group=self.group,
            current_user=self.owner,
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('not members of the group or do not exist', str(serializer.errors))


class TransferOwnershipSerializerTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner4@gmail.com', password='pass')
        self.friend = User.objects.create_user(username='friend', email='friend4@gmail.com', password='pass')
        self.not_member = User.objects.create_user(username='notmember', email='notmember4@gmail.com', password='pass')

        self.group = Group.objects.create(name='Group4', owner=self.owner)
        self.group.members.set([self.owner, self.friend])

    def test_transfer_to_member(self):
        data = {'new_owner_username': 'friend'}
        serializer = TransferOwnershipSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.owner})(), 'group': self.group}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_cannot_transfer_to_self(self):
        data = {'new_owner_username': 'owner'}
        serializer = TransferOwnershipSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.owner})(), 'group': self.group}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('cannot transfer ownership to yourself', str(serializer.errors))

    def test_cannot_transfer_to_non_member(self):
        data = {'new_owner_username': 'notmember'}
        serializer = TransferOwnershipSerializer(
            data=data,
            context={'request': type('Request', (), {'user': self.owner})(), 'group': self.group}
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('must be a member of the group', str(serializer.errors))


class OtherSerializersTests(TestCase):
    def test_leave_group_serializer_is_valid(self):
        serializer = LeaveGroupSerializer(data={})
        self.assertTrue(serializer.is_valid())

    def test_delete_group_serializer_requires_confirm(self):
        serializer = DeleteGroupSerializer(data={'confirm': True})
        self.assertTrue(serializer.is_valid())
        serializer = DeleteGroupSerializer(data={'confirm': False})
        self.assertTrue(serializer.is_valid())

        serializer = DeleteGroupSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertIn('confirm', serializer.errors)
