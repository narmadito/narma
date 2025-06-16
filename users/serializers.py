from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
from narma.utils.image_validators import validate_image_size, validate_image_resolution
from .models import Block
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'profile_picture')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'password2', 'profile_picture']

    def validate_profile_picture(self, image):
        if image:
            validate_image_size(image)
            validate_image_resolution(image)
        return image

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        profile_picture = validated_data.pop('profile_picture', None)

        user = User.objects.create_user(**validated_data)

        if profile_picture:
            user.profile_picture = profile_picture
        else:
            user.profile_picture = 'profiles/default.jpg'

        user.is_active = False
        user.save()
        return user


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user with this email found")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid64 = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Passwords do not match"})

        try:
            uid = force_str(urlsafe_base64_decode(attrs['uid64']))
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError, KeyError):
            raise serializers.ValidationError({"message": "User not found"})

        token = attrs['token']
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError({"message": "Token is invalid or expired"})

        attrs['user'] = user
        return attrs
    
    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.save()

class EmailCodeResendSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"message": "User with this email not found"})

        if user.is_active:
            raise serializers.ValidationError({"message": "User is already active"})

        attrs['user'] = user
        return attrs

from users.models import EmailVerificationCode

class EmailCodeConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()

    def validate(self, attrs):
        email = attrs['email']
        code = attrs['code']

        try:
            user = User.objects.get(email=email)
            verification_code = EmailVerificationCode.objects.get(user=user)

            if verification_code.code != code:
                raise serializers.ValidationError({"message": "Code is incorrect"})

            if verification_code.is_expired():
                raise serializers.ValidationError({"message": "Code has expired"})
                
        except (User.DoesNotExist, EmailVerificationCode.DoesNotExist):
            raise serializers.ValidationError({"message": "User or verification code not found"})

        attrs['user'] = user
        return attrs

class PasswordConfirmationSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)

class EmailChangeRequestCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = self.context['request'].user
        if value != user.email:
            raise serializers.ValidationError("This is not your current email.")
        return value

class EmailChangeConfirmCodeSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    new_email = serializers.EmailField()

class NewEmailCodeConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

class UsernameChangeSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    new_username = serializers.CharField()



class ProfilePictureUpdateSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=True)

    class Meta:
        model = User
        fields = ['profile_picture']

    def validate_profile_picture(self, image):
        validate_image_size(image)
        validate_image_resolution(image)
        return image


class BlockUserSerializer(serializers.Serializer):
    blocked_username = serializers.CharField(
        write_only=True,
        label="Block"
    )

    def validate_blocked_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Provide a username.")
        return value

    def create(self, validated_data):
        blocker = self.context['request'].user
        username = validated_data['blocked_username']
        if username == blocker.username:
            raise serializers.ValidationError("You cannot block yourself.")
        
        try:
            blocked_user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        
        block, created = Block.objects.get_or_create(blocker=blocker, blocked=blocked_user)
        if not created:
            raise serializers.ValidationError("User is already blocked.")
        return [block]



class UnblockUserSerializer(serializers.Serializer):
    username = serializers.CharField()

    def validate_username(self, value):
        try:
            user = User.objects.get(username=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist.")
        return user

    def save(self, **kwargs):
        request_user = self.context['request'].user
        blocked_user = self.validated_data['username']

        try:
            block = Block.objects.get(blocker=request_user, blocked=blocked_user)
            block.delete()
            return {"detail": f"User '{blocked_user.username}' successfully unblocked."}
        except Block.DoesNotExist:
            raise serializers.ValidationError("This user is not blocked.")

        
class BlockListSerializer(serializers.ModelSerializer):
    blocked = serializers.CharField(source='blocked.username')

    class Meta:
        model = Block
        fields = ['id', 'blocked']
