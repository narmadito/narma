from django.db.models import Q
from .models import Block

def is_blocked(user1, user2):
    return Block.objects.filter(
        Q(blocker=user1, blocked=user2) |
        Q(blocker=user2, blocked=user1)
    ).exists()