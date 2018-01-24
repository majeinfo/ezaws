from django import forms

class LoginForm(forms.Form):
    username = forms.CharField(max_length=75, label='Votre identifiant')
    password = forms.CharField(widget=forms.PasswordInput, label='Mot de passe')
