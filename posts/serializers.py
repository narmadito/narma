from rest_framework import serializers
from .models import Post, PostReaction, PostReaction, Comment, FavoritePost
from narma.utils.image_validators import validate_image_size, validate_image_resolution

class PostSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'author', 'description',
            'media', 'visibility', 'created_at',
            'likes_count', 'dislikes_count'
        ]

    def get_likes_count(self, obj):
        return obj.reactions.filter(reaction='like').count()

    def get_dislikes_count(self, obj):
        return obj.reactions.filter(reaction='dislike').count()

    def validate_media(self, media):
        if media:
            validate_image_size(media)
            validate_image_resolution(media)
        return media


class PostReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostReaction
        fields = ['id', 'reaction', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Comment
        fields = ['text', 'author']


class FavoritePostSerializer(serializers.ModelSerializer):
    class Meta:
        model = FavoritePost
        fields = ['id', 'post', 'user', 'created_at']
        read_only_fields = ['id', 'post', 'user', 'created_at']

class MinimalPostActionSerializer(serializers.Serializer):
    post = serializers.PrimaryKeyRelatedField(read_only=True)
