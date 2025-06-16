from django.db import models
from users.models import User
from narma.model_utils.models import TimeStampedModel
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied


class FriendRequest(TimeStampedModel):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    is_accepted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('from_user', 'to_user')

    def __str__(self):
        return f"{self.from_user.username} ➜ {self.to_user.username}"

class Friend(models.Model):
    user = models.ForeignKey(User, related_name='friends', on_delete=models.CASCADE)
    friend = models.ForeignKey(User, related_name='friend_of', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'friend')

    def __str__(self):
        return f"{self.user.username} ↔ {self.friend.username}"
    
