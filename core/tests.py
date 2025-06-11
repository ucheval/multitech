# from django.test import TestCase, Client
# from django.urls import reverse
# from django.contrib.auth.models import User
# from .models import Course, AuditLog, Notification, Profile
# from .forms import CourseForm

# class CreateCourseTest(TestCase):
#     def setUp(self):
#         self.client = Client()
#         self.admin = User.objects.create_superuser(username='admin', password='testpass', email='admin@example.com')
#         Profile.objects.create(user=self.admin, user_type='student')  # Add profile for consistency
#         self.client.login(username='admin', password='testpass')

#     def test_create_course_success(self):
#         data = {
#             'title': 'Python Programming',
#             'description': 'Learn Python basics.',
#             'duration': 8,
#             'level': 'Beginner',
#             'price': '5000.00'
#         }
#         response = self.client.post(reverse('create_course'), data)
#         self.assertRedirects(response, reverse('admin_dashboard'))
#         self.assertTrue(Course.objects.filter(title='Python Programming').exists())
#         self.assertTrue(AuditLog.objects.filter(action='Course Created').exists())
#         self.assertTrue(Notification.objects.filter(message__contains='Python Programming').exists())

#     def test_invalid_duration(self):
#         data = {
#             'title': 'Invalid Course',
#             'description': 'Test course.',
#             'duration': -1,
#             'level': 'Intermediate',
#             'price': '1000.00'
#         }
#         response = self.client.post(reverse('create_course'), data)
#         self.assertEqual(response.status_code, 200)
#         self.assertContains(response, 'Duration must be a positive integer.')