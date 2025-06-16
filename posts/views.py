from rest_framework import viewsets, mixins, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
from .models import Post, PostReaction, FavoritePost
from .serializers import PostSerializer, PostReactionSerializer, CommentSerializer, MinimalPostActionSerializer
from friends.models import Friend
from users.models import Block
User = get_user_model()

def get_mutual_friends(user):
    friends1 = Friend.objects.filter(user=user).values_list('friend_id', flat=True)
    friends2 = Friend.objects.filter(friend=user).values_list('user_id', flat=True)
    mutual_ids = set(friends1).intersection(friends2)
    return User.objects.filter(id__in=mutual_ids)


class PostViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'react':
            return PostReactionSerializer
        elif self.action in ['comment', 'comments']:
            return CommentSerializer
        elif self.action in ['favorite', 'unfavorite']:
            return MinimalPostActionSerializer
        return PostSerializer


    def get_queryset(self):
        user = self.request.user

        queryset = Post.objects.filter(visibility='public')

        if user.is_authenticated:
            mutual_friends = get_mutual_friends(user)
            queryset = Post.objects.filter(
                Q(visibility='public') |
                Q(author=user) |
                Q(visibility='friends', author__in=mutual_friends)
            )

            blocked_ids = Block.objects.filter(
                Q(blocker=user) | Q(blocked=user)
            ).values_list('blocker_id', 'blocked_id')

            blocked_user_ids = set()
            for blocker_id, blocked_id in blocked_ids:
                if blocker_id != user.id:
                    blocked_user_ids.add(blocker_id)
                if blocked_id != user.id:
                    blocked_user_ids.add(blocked_id)

            queryset = queryset.exclude(author__id__in=blocked_user_ids)
        
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        post = self.get_object()
        if post.author != request.user:
            return Response(
                {'error': 'You do not have permission to delete this post.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def react(self, request, pk=None):
        post = self.get_object()
        reaction_type = request.data.get('reaction')

        if reaction_type not in ['like', 'dislike']:
            return Response({'error': 'Invalid reaction'}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = PostReaction.objects.update_or_create(
            user=request.user,
            post=post,
            defaults={'reaction': reaction_type}
        )

        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def comment(self, request, pk=None):
        post = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user, post=post)
            return Response(
                {
                    "message": "Comment added successfully",
                    "comment": serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def comments(self, request, pk=None):
        post = self.get_object()
        comments = post.comments.order_by('-created_at')
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        post = self.get_object()

        if FavoritePost.objects.filter(user=request.user, post=post).exists():
            return Response({'message': 'Post is already in favorites.'}, status=status.HTTP_200_OK)

        favorite = FavoritePost.objects.create(user=request.user, post=post)
        return Response({'message': 'Post added to favorites.'}, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def favorites(self, request):
        favorites = FavoritePost.objects.filter(user=request.user).select_related('post')
        posts = [fav.post for fav in favorites]
        serializer = PostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unfavorite(self, request, pk=None):
        post = self.get_object()
        try:
            favorite = FavoritePost.objects.get(user=request.user, post=post)
            favorite.delete()
            return Response({'message': 'Post removed from favorites.'}, status=status.HTTP_200_OK)
        except FavoritePost.DoesNotExist:
            return Response({'error': 'Post was not in favorites.'}, status=status.HTTP_400_BAD_REQUEST)

