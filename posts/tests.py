from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Post, PostReaction, Comment, FavoritePost
from friends.models import Friend

User = get_user_model()

class PostViewSetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='user1', email='user1@example.com', password='pass123')
        self.friend = User.objects.create_user(username='user2', email='user2@example.com', password='pass123')
        self.other_user = User.objects.create_user(username='user3', password='pass123')

        Friend.objects.create(user=self.user, friend=self.friend)
        Friend.objects.create(user=self.friend, friend=self.user)

        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')


        self.public_post = Post.objects.create(
            author=self.other_user,
            title="Public Post",
            description="Visible to everyone",
            visibility="public"
        )
        self.friends_post = Post.objects.create(
            author=self.friend,
            title="Friends Post",
            description="Visible to friends",
            visibility="friends"
        )
        self.private_post = Post.objects.create(
            author=self.other_user,
            title="Private Post",
            description="Not visible to others",
            visibility="private"
        )

    def test_create_post(self):
        url = reverse('post-list')
        data = {'title': 'New Post', 'description': 'test desc', 'visibility': 'public'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Post.objects.count(), 4)

    def test_list_posts_with_mutual_friend(self):
        url = reverse('post-list')
        response = self.client.get(url)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn("Public Post", titles)
        self.assertIn("Friends Post", titles)
        self.assertNotIn("Private Post", titles)


    def test_delete_post_by_owner(self):
        post = Post.objects.create(author=self.user, title='Delete Me', visibility='public')
        url = reverse('post-detail', args=[post.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_post_by_non_owner(self):
        url = reverse('post-detail', args=[self.public_post.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_comment(self):
        url = reverse('post-comment', args=[self.public_post.pk])
        data = {'text': 'Nice post!'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 1)

    def test_get_comments(self):
        Comment.objects.create(post=self.public_post, author=self.user, text='Comment 1')
        url = reverse('post-comments', args=[self.public_post.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_react_to_post(self):
        url = reverse('post-react', args=[self.public_post.pk])
        data = {'reaction': 'like'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(PostReaction.objects.count(), 1)

    def test_change_reaction(self):
        PostReaction.objects.create(post=self.public_post, user=self.user, reaction='like')
        url = reverse('post-react', args=[self.public_post.pk])
        data = {'reaction': 'dislike'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reaction = PostReaction.objects.get(post=self.public_post, user=self.user)
        self.assertEqual(reaction.reaction, 'dislike')

    def test_add_to_favorites(self):
        url = reverse('post-favorite', args=[self.public_post.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FavoritePost.objects.count(), 1)

    def test_unfavorite_post(self):
        FavoritePost.objects.create(user=self.user, post=self.public_post)
        url = reverse('post-unfavorite', args=[self.public_post.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(FavoritePost.objects.count(), 0)

    def test_view_favorites(self):
        FavoritePost.objects.create(user=self.user, post=self.public_post)
        url = reverse('post-favorites')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
