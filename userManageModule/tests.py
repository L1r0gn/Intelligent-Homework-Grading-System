from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()

class UserProfileUpdateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='old_password_123',
            wx_nickName='Old Nick',
            phone=13800000000
        )
        self.url = reverse('api_user_profile_update')

    def test_authentication_required(self):
        response = self.client.patch(self.url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_profile_info(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'wx_nickName': 'New Nick',
            'phone': 13900000000,
            'email': 'new@example.com',
            'gender': 1
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.wx_nickName, 'New Nick')
        self.assertEqual(self.user.phone, 13900000000)
        self.assertEqual(self.user.email, 'new@example.com')
        self.assertEqual(self.user.gender, 1)

    def test_update_password_success(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'current_password': 'old_password_123',
            'new_password': 'new_password_456',
            'confirm_password': 'new_password_456'
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify password changed (must re-fetch user to check auth against DB)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('new_password_456'))

    def test_update_password_wrong_current(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'current_password': 'wrong_password',
            'new_password': 'new_password_456',
            'confirm_password': 'new_password_456'
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)

    def test_update_password_mismatch(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'current_password': 'old_password_123',
            'new_password': 'new_password_456',
            'confirm_password': 'new_password_789'
        }
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data)

    def test_invalid_phone(self):
        self.client.force_authenticate(user=self.user)
        data = {'phone': 123} # too short
        response = self.client.patch(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
