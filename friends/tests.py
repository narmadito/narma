from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from friends.models import FriendRequest, Friend

User = get_user_model()

class FriendViewSetTests(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', email='alice@example.com', password='pass123')
        self.user2 = User.objects.create_user(username='bob', email='bob@example.com', password='pass123')
        self.user3 = User.objects.create_user(username='charlie', email='charlie@example.com', password='pass123')

        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)


    def test_send_friend_request(self):
        url = reverse('friend_request-list')
        data = {'to_user_username': 'bob'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FriendRequest.objects.count(), 1)

    def test_send_duplicate_friend_request(self):
        FriendRequest.objects.create(from_user=self.user1, to_user=self.user2)
        url = reverse('friend_request-list')
        data = {'to_user_username': 'bob'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_friend_request(self):
        fr = FriendRequest.objects.create(from_user=self.user1, to_user=self.user2)
        self.client.force_authenticate(user=self.user2)
        url = reverse('friend_request-accept', kwargs={'pk': fr.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(FriendRequest.objects.filter(id=fr.id).exists())
        self.assertEqual(Friend.objects.count(), 2)

    def test_decline_friend_request(self):
        fr = FriendRequest.objects.create(from_user=self.user1, to_user=self.user2)
        self.client.force_authenticate(user=self.user2)
        url = reverse('friend_request-decline', kwargs={'pk': fr.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(FriendRequest.objects.filter(id=fr.id).exists())
        self.assertEqual(Friend.objects.count(), 0)

    def test_view_friends(self):
        Friend.objects.create(user=self.user1, friend=self.user2)
        Friend.objects.create(user=self.user2, friend=self.user1)
        url = reverse('friend-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        if 'results' in data:
            friends_list = data['results']
        else:
            friends_list = data

        self.assertEqual(len(friends_list), 1)
        self.assertEqual(friends_list[0]['friend']['username'], 'bob')


    def test_unfriend(self):
        f1 = Friend.objects.create(user=self.user1, friend=self.user2)
        Friend.objects.create(user=self.user2, friend=self.user1)
        url = reverse('friend-unfriend', kwargs={'pk': f1.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Friend.objects.count(), 0)
