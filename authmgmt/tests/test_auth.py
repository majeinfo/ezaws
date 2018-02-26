from django.test import TestCase, RequestFactory
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib import messages
from web.models import User, Customer
import captcha.conf.settings as cap_settings
from authmgmt.auth import signupAction

cap_settings.CAPTCHA_TEST_MODE = True


class AuthTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        user = User.objects.create_user('bob', 'bob@example.com', 'password')
        user.save()

    def setup_request(self, request):
        middleware = SessionMiddleware()
        middleware.process_request(request)
        middleware = MessageMiddleware()
        middleware.process_request(request)

    def test_signup_empty(self):
        request = self.factory.get('/auth/signup')
        response = signupAction(request)
        self.assertNotContains(response, 'class="alert')
        self.assertTrue(response.status_code, 200)

    def test_signup_user_password_mismatch(self):
        data = {
            'username': 'alice', 'email': 'alice@example.com',
            'password': 'x', 'password2': 'x2', 'captcha_0': 'PASSED', 'captcha_1': 'PASSED'
        }
        request = self.factory.post('/auth/signup', data)
        self.setup_request(request)
        response = signupAction(request)
        #print(response.content)
        self.assertContains(response, 'Passwords mismatch', status_code=200)

    def test_signup_user_already_exists(self):
        data = {
            'username': 'bob', 'email': 'bob@example.com',
            'password': 'x', 'password2': 'x', 'captcha_0': 'PASSED', 'captcha_1': 'PASSED'
        }
        request = self.factory.post('/auth/signup', data)
        self.setup_request(request)
        response = signupAction(request)
        #print(response.content)
        self.assertContains(response, 'Username already exists', status_code=200)

    def test_signup_user_ok(self):
        data = {
            'username': 'alice', 'email': 'alice@example.com',
            'password': 'x', 'password2': 'x', 'captcha_0': 'PASSED', 'captcha_1': 'PASSED'
        }
        request = self.factory.post('/auth/signup', data)
        self.setup_request(request)
        response = signupAction(request)
        self.assertTrue(response.status_code, 302)


