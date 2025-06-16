from django.contrib.auth.models import AbstractUser
from django.db import models
from narma.model_utils.models import TimeStampedModel
from datetime import timedelta
from django.utils import timezone

class User(AbstractUser, TimeStampedModel):
    email = models.EmailField(unique=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return self.username

class EmailVerificationCode(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_code')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    new_email = models.EmailField(null=True, blank=True)
    new_email_code = models.CharField(max_length=6, null=True, blank=True)
    new_email_code_created_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def is_new_email_code_expired(self):
        if not self.new_email_code_created_at:
            return True
        return timezone.now() > self.new_email_code_created_at + timedelta(minutes=10)

    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
class Block(TimeStampedModel):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_initiated')
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blocks_received')

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"