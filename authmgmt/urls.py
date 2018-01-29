from django.conf.urls import url
from django.contrib.auth import views as auth_views
from . import auth

urlpatterns = [
    #url(r'^login', auth_views.LoginView.as_view(template_name='login.html'), name='auth_login'),
    url(r'^login', auth.loginAction, name='auth_login'),
    url(r'^logout', auth.logoutAction, name='auth_logout'),
    url(r'^hook_deploy', auth.hookDeploy, name='hook_deploy'),
]