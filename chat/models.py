from django.db import models
from django.contrib.auth import get_user_model
from narma.model_utils.models import TimeStampedModel
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class DirectMessage(TimeStampedModel):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f"{self.sender} ➜ {self.recipient}: {self.message[:20]}"

class Group(TimeStampedModel):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, related_name='owned_groups', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='group_memberships')

    def __str__(self):
        return self.name
    
class GroupMessage(TimeStampedModel):
    group = models.ForeignKey(Group, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f"{self.sender} @ {self.group.name}: {self.content[:20]}"
