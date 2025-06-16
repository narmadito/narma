from django.contrib import admin
from .models import Post, PostReaction, Comment, FavoritePost

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'visibility', 'created_at')
    search_fields = ('title', 'author__username')
    list_filter = ('visibility', 'created_at')

@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'reaction', 'created_at')
    list_filter = ('reaction',)
    search_fields = ('user__username', 'post__title')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('author__username', 'post__title', 'text')

@admin.register(FavoritePost)
class FavoritePostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__username', 'post__title')
