from django.urls import path
from django.contrib.auth import views as auth_views
from . import auth

urlpatterns = [
    #url(r'^login', auth_views.LoginView.as_view(template_name='login.html'), name='auth_login'),
    path('login', auth.loginAction, name='auth_login'),
    path('logout', auth.logoutAction, name='auth_logout'),
    path('signup', auth.signupAction, name='auth_signup'),
    path('profile', auth.editProfileAction, name='auth_profile'),
    path('change_password', auth.changePasswordAction, name='change_password'),
    path('password_reset/done', auth_views.password_reset_done, { 'template_name': 'password_reset_done.html'}, name='password_reset_done'),
    path('password_reset', auth_views.password_reset, { 'template_name': 'password_reset_form.html',
                                                        'extra_email_context': { 'domain': 'ezaws.delamarche.com', 'site_name': 'EZAws' }}, name='password_reset'),
    path('reset/<uidb64>/<token>', auth_views.password_reset_confirm, { 'template_name': 'password_reset_confirm.html', }, name='password_reset_confirm'),
    path('reset/done', auth_views.password_reset_complete, { 'template_name': 'password_reset_complete.html', }, name='password_reset_complete'),
    path('check_key/<cust_name>', auth.checkKeyAction, name='check_key'),
    path('hook_deploy', auth.hookDeployAction, name='hook_deploy'),
    path('', auth.indexAction, name='auth_index'),
]