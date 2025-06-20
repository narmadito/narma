
from datetime import timedelta
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import mixins, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.exceptions import PermissionDenied
from .utils import is_blocked

from .serializers import (
    RegisterSerializer, UserSerializer, PasswordResetSerializer, PasswordResetConfirmSerializer,
    EmailCodeConfirmSerializer, EmailCodeResendSerializer, PasswordConfirmationSerializer,
    EmailChangeRequestCodeSerializer, EmailChangeConfirmCodeSerializer, NewEmailCodeConfirmSerializer,
    UsernameChangeSerializer, ProfilePictureUpdateSerializer, BlockUserSerializer, UnblockUserSerializer,
    BlockListSerializer
)
from .permissions import IsNotAuthenticated
from users.models import EmailVerificationCode
from .models import Block

User = get_user_model()


def generate_code():
    return str(random.randint(100000, 999999))


def send_code_email(subject, message, to_email):
    send_mail(subject, message, 'no-reply@example.com', [to_email])


class RegisterViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [IsNotAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            self.send_verification_code(user)
            return Response({"detail": "User registered successfully. Verification code sent to email."}, status=201)
        return Response(serializer.errors, status=400)

    def send_verification_code(self, user):
        code = generate_code()
        EmailVerificationCode.objects.update_or_create(user=user, defaults={'code': code, 'created_at': timezone.now()})
        send_code_email("Your verification code", f"Hello {user.username},\n\nYour verification code is: {code}", user.email)

    @action(detail=False, methods=["post"], serializer_class=EmailCodeResendSerializer)
    def resend_code(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        existing_code = EmailVerificationCode.objects.filter(user=user).first()
        if existing_code and (timezone.now() - existing_code.created_at) < timedelta(minutes=1):
            wait = 60 - int((timezone.now() - existing_code.created_at).total_seconds())
            return Response({"detail": f"Please wait {wait} seconds before requesting a new code."}, status=429)

        self.send_verification_code(user)
        return Response({"message": "Verification code resent successfully."})

    @action(detail=False, methods=['post'], serializer_class=EmailCodeConfirmSerializer)
    def confirm_code(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            user.is_active = True
            user.save()
            return Response({"message": "Your account is now active ✅"}, status=200)
        return Response(serializer.errors, status=400)


class ProfileViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.UpdateModelMixin):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user



class PublicProfileViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    lookup_field = 'username'

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object()

        if request.user.is_authenticated and is_blocked(request.user, user):
            raise PermissionDenied("You are not allowed to perform this action.")

        return super().retrieve(request, *args, **kwargs)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], serializer_class=PasswordConfirmationSerializer)
    def delete_account(self, request, username=None):
        if self.get_object() != request.user:
            return Response({"detail": "You are not allowed to delete someone else's account."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['password']):
            return Response({'password': ['Incorrect password.']}, status=400)

        request.user.delete()
        return Response({'detail': 'Account deleted successfully.'}, status=204)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], serializer_class=UsernameChangeSerializer)
    def change_username(self, request, username=None):
        user = self.get_object()
        if user != request.user:
            return Response({"detail": "You can't change someone else's username."}, status=403)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not user.check_password(serializer.validated_data['password']):
            return Response({'password': ['Incorrect password.']}, status=400)

        new_username = serializer.validated_data['new_username']
        if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            return Response({'new_username': ['This username is already taken.']}, status=400)

        user.username = new_username
        user.save()
        return Response({'detail': 'Username changed successfully.', 'new_username': new_username}, status=200)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], serializer_class=ProfilePictureUpdateSerializer, parser_classes=[MultiPartParser, FormParser])
    def update_image(self, request, username=None):
        user = self.get_object()
        if user != request.user:
            return Response({"detail": "You can't update someone else's profile."}, status=403)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        profile_picture = serializer.validated_data.get('profile_picture')
        if profile_picture:
            user.profile_picture = profile_picture
            user.save()
            return Response({'detail': 'Profile picture updated successfully.', 'data': serializer.data}, status=200)

        return Response({'detail': 'No profile picture provided.'}, status=400)



class UserListViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]


class ResetPasswordViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(email=serializer.validated_data['email'])
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"http://localhost/password_reset_confirm/{uid}/{token}/"
            send_code_email("Reset Password", f"Click the link to reset your password: {reset_url}", user.email)
            return Response({"message": 'Sent successfully'}, status=200)
        return Response(serializer.errors, status=400)


class PasswordResetConfirmViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('uidb64', openapi.IN_PATH, description="User ID (Base64 encoded)", type=openapi.TYPE_STRING),
        openapi.Parameter('token', openapi.IN_PATH, description="Password reset token", type=openapi.TYPE_STRING),
    ])
    def create(self, request, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password updated successfully"}, status=200)
        return Response(serializer.errors, status=400)


class EmailChangeViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailChangeRequestCodeSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data['email'] != request.user.email:
            return Response({"email": "This is not your current email."}, status=400)

        code = generate_code()
        EmailVerificationCode.objects.update_or_create(user=request.user, defaults={'code': code, 'created_at': timezone.now()})
        send_code_email("Verification Code", f"Your verification code is: {code}", request.user.email)
        return Response({"message": "Verification code sent to your current email."})

    @action(detail=False, methods=['post'], serializer_class=EmailChangeConfirmCodeSerializer)
    def confirm_old_email_code(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        code = serializer.validated_data['code']
        new_email = serializer.validated_data['new_email']

        evc = EmailVerificationCode.objects.filter(user=user).first()
        if not evc:
            return Response({"detail": "Please request a verification code first."}, status=400)
        if evc.code != code:
            return Response({"code": "Invalid code."}, status=400)
        if User.objects.filter(email=new_email).exists():
            return Response({"new_email": "This email is already taken."}, status=400)

        new_email_code = generate_code()
        evc.new_email = new_email
        evc.new_email_code = new_email_code
        evc.new_email_code_created_at = timezone.now()
        evc.save()

        send_code_email("Confirm your new email", f"Your confirmation code is: {new_email_code}", new_email)
        return Response({"message": "Verification code sent to your new email."})

    @action(detail=False, methods=['post'], serializer_class=NewEmailCodeConfirmSerializer)
    def confirm_new_email_code(self, request):
        code = request.data.get('code')
        user = request.user
        evc = EmailVerificationCode.objects.filter(user=user).first()

        if not evc:
            return Response({"detail": "Please request a verification code first."}, status=400)
        if evc.new_email_code != code:
            return Response({"code": "Invalid code."}, status=400)
        if evc.is_new_email_code_expired():
            return Response({"code": "Code expired."}, status=400)
        if not evc.new_email:
            return Response({"new_email": "No new email to confirm."}, status=400)

        user.email = evc.new_email
        user.save()
        evc.delete()

        return Response({"message": "Email successfully changed ✅"}, status=200)

class BlockViewSet(mixins.CreateModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    queryset = Block.objects.all()
    permission_classes = [IsAuthenticated]

    

    def get_serializer_class(self):
        if self.action == 'unblock':
            return UnblockUserSerializer
        elif self.action == 'list':
            return BlockListSerializer
        return BlockUserSerializer
    
    def get_queryset(self):
        return Block.objects.filter(blocker=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        blocks = serializer.save()
        return Response({"detail": f"Blocked {len(blocks)} user(s)."}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='unblock')
    def unblock(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        success = serializer.save()
        if success:
            return Response({"detail": "User unblocked successfully."}, status=status.HTTP_200_OK)
        return Response({"detail": "User was not blocked."}, status=status.HTTP_400_BAD_REQUEST)
