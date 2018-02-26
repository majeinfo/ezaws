from django.test import TestCase
from authmgmt.forms import SubscribeForm, LoginForm, ProfileForm
import captcha.conf.settings as cap_settings

cap_settings.CAPTCHA_TEST_MODE = True


class SubscribeFormTestCase(TestCase):
    def setUp(self):
        pass

    def test_invalid_form_empty(self):
        data = { }
        form = SubscribeForm(data=data)
        self.assertFalse(form.is_valid())

    def test_valid_form(self):
        data = { 'username': 'bob', 'email': 'bob@example.com',
                 'password': 'x', 'password2': 'x', 'captcha_0': 'PASSED', 'captcha_1': 'PASSED' }
        form = SubscribeForm(data=data)
        #form.is_valid()
        #print(form.errors.as_data())
        self.assertTrue(form.is_valid())

