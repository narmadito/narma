from django.db import models
from django.contrib.auth import get_user_model
from narma.model_utils.models import TimeStampedModel

User = get_user_model()

class Post(TimeStampedModel):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    media = models.FileField(upload_to='posts/', blank=True, null=True)

    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    visibility = models.CharField(
        max_length=10,
        choices=VISIBILITY_CHOICES,
        default='public'
    )

    def __str__(self):
        return self.title


class PostReaction(TimeStampedModel):
    REACTION_CHOICES = [
        ('like', 'Like'),
        ('dislike', 'Dislike'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reactions')
    reaction = models.CharField(max_length=7, choices=REACTION_CHOICES)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f'{self.user.username} {self.reaction}d "{self.post.title}"'

class Comment(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return f'{self.author.username}: {self.text[:30]}'

class FavoritePost(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f'{self.user.username} favorited "{self.post.title}"'
