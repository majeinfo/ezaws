from os import environ
from .settings import *

EMAIL_HOST = 'localhost'
SECRET_KEY = environ["SECRET_KEY"]
DEBUG = False