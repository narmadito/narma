from django.contrib import admin
from .models import FriendRequest, Friend

@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'from_user', 'to_user', 'is_accepted', 'created_at')
    list_filter = ('is_accepted', 'created_at')
    search_fields = ('from_user__username', 'to_user__username')

@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'friend')
    search_fields = ('user__username', 'friend__username')
