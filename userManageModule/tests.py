from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import className, ClassTeacher
from .forms import UserAddForm, ClassForm

User = get_user_model()

class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(username='testuser', password='password123', user_attribute=1)
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('password123'))
        self.assertEqual(user.user_attribute, 1)

class ClassNameModelTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='password', user_attribute=2)

    def test_create_class_auto_code(self):
        cls = className.objects.create(name='Test Class', created_by=self.teacher)
        self.assertIsNotNone(cls.code)
        self.assertEqual(len(cls.code), 6)
        self.assertEqual(cls.created_by, self.teacher)

    def test_class_string_representation(self):
        cls = className.objects.create(name='Test Class', created_by=self.teacher)
        self.assertEqual(str(cls), 'Test Class')

class UserFormTest(TestCase):
    def test_user_add_form_valid(self):
        form_data = {
            'username': 'newuser',
            'password': 'password123',
            'password_confirm': 'password123',
            'user_attribute': 1,
            'wx_nickName': 'New User'
        }
        form = UserAddForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_user_add_form_password_mismatch(self):
        form_data = {
            'username': 'newuser',
            'password': 'password123',
            'password_confirm': 'password456',
            'user_attribute': 1
        }
        form = UserAddForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

class ClassFormTest(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username='teacher', password='password', user_attribute=2)
        self.existing_class = className.objects.create(name='Existing Class', code='ABC123', created_by=self.teacher)

    def test_class_form_valid(self):
        form_data = {
            'name': 'New Class',
            'grade': '2024',
            'description': 'Test Description'
        }
        form = ClassForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_class_form_duplicate_code(self):
        form_data = {
            'name': 'Duplicate Class',
            'code': 'ABC123' # Same as existing
        }
        form = ClassForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('code', form.errors)

class AdminViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(username='admin', password='password', user_attribute=3)
        self.student_user = User.objects.create_user(username='student', password='password', user_attribute=1)
        self.teacher_user = User.objects.create_user(username='teacher', password='password', user_attribute=2)

    def test_admin_access_user_list(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('user_list'))
        self.assertEqual(response.status_code, 200)

    def test_non_admin_access_denied(self):
        self.client.login(username='student', password='password')
        response = self.client.get(reverse('user_list'))
        # Should redirect to question_list or dashboard depending on implementation, or show error
        # Based on admin_required decorator logic: redirect to question_list or dashboard
        self.assertEqual(response.status_code, 302) 

    def test_user_add_view(self):
        self.client.login(username='admin', password='password')
        response = self.client.post(reverse('user_add'), {
            'username': 'createduser',
            'password': 'password123',
            'password_confirm': 'password123',
            'user_attribute': 1,
            'wx_nickName': 'Created User'
        })
        self.assertEqual(response.status_code, 302) # Redirects on success
        self.assertTrue(User.objects.filter(username='createduser').exists())

class ClassViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(username='admin', password='password', user_attribute=3)
        self.teacher_user = User.objects.create_user(username='teacher', password='password', user_attribute=2)
        self.student_user = User.objects.create_user(username='student', password='password', user_attribute=1)
        self.client.login(username='admin', password='password')
        self.cls = className.objects.create(name='Test Class', created_by=self.admin_user)

    def test_class_list_view(self):
        response = self.client.get(reverse('class_list_web'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Class')

    def test_class_create_view(self):
        response = self.client.post(reverse('class_create_web'), {
            'name': 'New Web Class',
            'grade': '2025'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(className.objects.filter(name='New Web Class').exists())

    def test_class_detail_view(self):
        response = self.client.get(reverse('class_detail_web', args=[self.cls.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.cls.name)

    def test_add_student_to_class(self):
        response = self.client.post(reverse('class_add_student_web', args=[self.cls.id]), {
            'student': self.student_user.id
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.student_user, self.cls.members.all())

    def test_add_teacher_to_class(self):
        response = self.client.post(reverse('class_add_teacher_web', args=[self.cls.id]), {
            'teacher': self.teacher_user.id,
            'subject': 'Math'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClassTeacher.objects.filter(class_obj=self.cls, teacher=self.teacher_user, subject='Math').exists())

    def test_search_student_api(self):
        response = self.client.get(reverse('search_students_api'), {'q': 'student'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(len(data['results']) > 0)
        self.assertEqual(data['results'][0]['id'], self.student_user.id)
