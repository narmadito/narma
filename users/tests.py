from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from users.models import EmailVerificationCode
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class UserFlowTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('user-registration-list')
        self.login_url = reverse('token_obtain_pair')
        self.user_list_url = reverse('user-list')
        self.password_reset_url = reverse('reset-list')
        self.email_change_url = reverse('email-change-list')
        self.resend_code_url = reverse('user-registration-resend-code')
        self.confirm_code_url = reverse('user-registration-confirm-code')
        self.confirm_old_code_url = reverse('email-change-confirm-old-email-code')
        self.confirm_new_code_url = reverse('email-change-confirm-new-email-code')

        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "strong_password_123",
            "password2": "strong_password_123",
        }

    def test_registration_and_verification_flow(self):
        response = self.client.post(self.register_url, data=self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.user_data['email'])
        evc = EmailVerificationCode.objects.get(user=user)
        confirm_data = {"email": user.email, "code": evc.code}
        response = self.client.post(self.confirm_code_url, data=confirm_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_resend_code_rate_limit(self):
        self.client.post(self.register_url, data=self.user_data)
        response = self.client.post(self.resend_code_url, data={"email": self.user_data["email"]})
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_email_change_flow(self):
        user = User.objects.create_user(
            username=self.user_data["username"],
            email=self.user_data["email"],
            password=self.user_data["password"],
            is_active=True
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.email_change_url, data={"email": user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evc = EmailVerificationCode.objects.get(user=user)
        old_code = evc.code
        new_email = "newemail@example.com"
        response = self.client.post(self.confirm_old_code_url, data={"code": old_code, "new_email": new_email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evc.refresh_from_db()
        new_email_code = evc.new_email_code
        response = self.client.post(self.confirm_new_code_url, data={"code": new_email_code})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.email, new_email)

    def test_delete_account(self):
        user = User.objects.create_user(
            username="deleteuser",
            email="delete@example.com",
            password="pass1234",
            is_active=True
        )
        self.client.force_authenticate(user)
        url = reverse('profile-delete-account', kwargs={"username": user.username})
        response = self.client.post(url, data={"password": "wrongpass"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(url, data={"password": "pass1234"})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(User.DoesNotExist):
            User.objects.get(pk=user.pk)

    def test_change_username(self):
        user = User.objects.create_user(
            username="oldusername",
            email="user@example.com",
            password="pass1234",
            is_active=True
        )
        self.client.force_authenticate(user)
        url = reverse('profile-change-username', kwargs={"username": user.username})
        response = self.client.post(url, data={"password": "wrongpass", "new_username": "newusername"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(url, data={"password": "pass1234", "new_username": "newusername"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.username, "newusername")
    
    def get_test_image_file(self):
        image = Image.new('RGB', (500, 500), color='red')
        byte_arr = BytesIO()
        image.save(byte_arr, format='JPEG')
        byte_arr.seek(0)
        return SimpleUploadedFile("test_image.jpg", byte_arr.read(), content_type="image/jpeg")

    def test_update_profile_picture(self):
        user = User.objects.create_user(
            username="picuser",
            email="pic@example.com",
            password="pass1234",
            is_active=True
        )
        self.client.force_authenticate(user)

        url = reverse('profile-update-image', kwargs={"username": user.username})

        image = self.get_test_image_file()
        response = self.client.post(url, data={"profile_picture": image}, format='multipart')
        self.assertEqual(response.status_code, 200)

        user.refresh_from_db()
        self.assertIn("test_image", user.profile_picture.name)
