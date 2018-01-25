"""ezaws URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.9/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
#from django.conf.urls import url, include
from django.urls import include, path
from django.contrib import admin
from django.contrib.auth.decorators import login_required
#from decorator_include import decorator_include
import web, authmgmt

'''
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    #url(r'^web/', decorator_include(login_required, 'web.urls')),
    url(r'^web/', decorator_include(login_required, 'web.urls')),
    url(r'^auth/', include('authmgmt.urls')),
    url(r'^$', login_required(web.views.index)),
]
'''

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('web/', include('web.urls')),
    path('auth/', include('authmgmt.urls')),
    path('', login_required(web.views.index)),
]

