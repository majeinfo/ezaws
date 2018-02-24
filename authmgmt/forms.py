<<<<<<< HEAD
from django.utils.translation import ugettext as _
from captcha.fields import CaptchaField
import pytz
from django import forms
from aws.definitions import available_regions


class SubscribeForm(forms.Form):
    username = forms.CharField(max_length=75, label=_('Choose your login'))
    email = forms.EmailField(max_length=64, label=_('Indicate a valid email address'), help_text=_("It will only be used to send you Alert Mails"))
    password = forms.CharField(widget=forms.PasswordInput, label=_('Choose a password'))
    password2 = forms.CharField(widget=forms.PasswordInput, label=_('Please, enter your password again'))
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

=======
from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=75, label='Votre identifiant')
    password = forms.CharField(widget=forms.PasswordInput, label='Mot de passe')
>>>>>>> e86af261ef096ba887135da1d22bc86847fce2f8
