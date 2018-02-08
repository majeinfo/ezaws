"""
Django settings for ezaws project.

Generated by 'django-admin startproject' using Django 1.9.7.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '6unrc3bpywlk17-r5uwr+3vumt3h@94fi9pmjwnd_fey8kr+^+'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ['DEBUG'] if 'DEBUG' in os.environ else True

# Current Version
VERSION = os.environ['VERSION'] if 'VERSION' in os.environ else 'dev'

ALLOWED_HOSTS = [ 'localhost', 'ezaws.delamarche.com' ]

DEFAULT_FROM_EMAIL = 'support@delamarche.com'
EMAIL_HOST = os.environ['EMAIL_HOST'] if 'EMAIL_HOST' in os.environ else 'smtp.free.fr'
EMAIL_SUBJECT_PREFIX = 'ezaws'


# Application definition

INSTALLED_APPS = [
    'ezaws',
    'web',
    'authmgmt',
    'aws',
    'captcha',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'bootstrap4',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'web.middleware.CustomerNameMiddleware',
    #'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ezaws.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'ezaws.context_processors.global_settings',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ezaws.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ['DB_NAME'] if 'DB_NAME' in os.environ else 'ezaws',
        'USER': os.environ['DB_USER'] if 'DB_USER' in os.environ else 'ezaws',
        'PASSWORD': os.environ['DB_PASSWORD'] if 'DB_PASSWORD' in os.environ else 'ezaws',
        'HOST': os.environ['DB_HOST'] if 'DB_HOST' in os.environ else 'localhost',
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)
STATIC_URL = '/static/'

#LOGIN_URL = '/auth/login'
LOGIN_URL = '/'
LOGOUT_REDIRECT_URL = '/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'logfile': {                # define and name a handler
            'level': 'DEBUG',
            'class': 'logging.FileHandler', # set the logging class to log to a file
            'formatter': 'verbose',         # define the formatter to associate
            #'filename': os.path.join(PROJECT_ROOT, '../../log/resa5.log') # log file
            'filename': '/tmp/ezaws.log'
        },
        'pricing_logfile': {                # define and name a handler
            'level': 'DEBUG',
            'class': 'logging.FileHandler', # set the logging class to log to a file
            'formatter': 'verbose',         # define the formatter to associate
            #'filename': os.path.join(PROJECT_ROOT, '../../log/resa5.log') # log file
            'filename': '/tmp/ezaws-pricing.log'
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'general' : {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'pricing' : {
            'handlers': ['pricing_logfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends' : {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}
