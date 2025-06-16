from django.contrib import admin
from .models import DirectMessage, Group, GroupMessage

@admin.register(DirectMessage)
class DirectMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'message', 'created_at')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner')

@admin.register(GroupMessage)
class GroupMessageAdmin(admin.ModelAdmin):
    list_display = ('group', 'sender', 'content', 'created_at')
