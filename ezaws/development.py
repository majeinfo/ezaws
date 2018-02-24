from os import environ
from .settings import *

EMAIL_HOST = 'smtp.free.fr'
DEBUG = True

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE += [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]
