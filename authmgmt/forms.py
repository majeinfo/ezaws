from django.utils.translation import gettext as _
from captcha.fields import CaptchaField
import pytz
from django import forms
from aws.definitions import available_regions


class SubscribeForm(forms.Form):
    username = forms.CharField(max_length=75, label=_('Choose your login'), initial='my_username')
    email = forms.EmailField(max_length=64, label=_('Indicate a valid email address'), help_text=_("It will only be used to send you Alert Mails"), initial='me@domain.com')
    password = forms.CharField(widget=forms.PasswordInput, label=_('Choose a password'), initial='my_password')
    password2 = forms.CharField(widget=forms.PasswordInput, label=_('Please, enter your password again'), initial='my_password')
    captcha = CaptchaField()


class LoginForm(forms.Form):
    username = forms.CharField(max_length=75, label='Login')
    password = forms.CharField(widget=forms.PasswordInput, label='Password')


class ProfileForm(forms.Form):
    console_url = forms.URLField(max_length=200, label=_('URL to your AWS Console'), required=False)
    access_key = forms.CharField(max_length=64, label=_('AWS Access Key'))
    secret_key = forms.CharField(max_length=64, label=_('AWS Secret Key'))
    owner_id = forms.CharField(max_length=16, label=_('AWS Account ID'))
    region = forms.ChoiceField(choices=map(lambda x: (x, x), available_regions), label=_('Default AWS Region'))
    timezone = forms.ChoiceField(choices=map(lambda x: (x, x), pytz.common_timezones), label=_('Your Timezone'))


class AWSParmsForm(forms.Form):
    aws_resource_tag_name = forms.CharField(max_length=32, label=_('Resource Tag Name'), required=True, initial='NAME',
                                            help_text=_("This is the Tag Name used to retrieve your AWS Resource Names"))

