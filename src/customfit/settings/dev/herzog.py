"""
Jonathan Herzog's personal Django settings file
"""

from ..local import *

DEBUG = True

# See below for unit-test optimizations that might overwrite this
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        "NAME": "customfit_django",  # Or path to database file if using sqlite3.
        "USER": "",  # Not used with sqlite3.
        "PASSWORD": "",  # Not used with sqlite3.
        "HOST": "localhost",  # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "5432",  # Set to empty string for default. Not used with sqlite3.
    }
}


ALLOWED_HOSTS = ["*"]


HTML_MINIFY = True

THUMBNAIL_DEBUG = False

if bool_from_env("DJANGO_FAST_TESTS", False):

    PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)
    # DATABASES = {
    #     'default': {
    #         'ENGINE': 'django.db.backends.sqlite3',
    #         'NAME': 'mydatabase',
    #     }
    # }
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    BROKER_BACKEND = "memory"

    # Skip migrations when creating test databases

    class DisableMigrations(object):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            return None

    MIGRATION_MODULES = DisableMigrations()


# Selenium tests won't parallelize without the following
DJANGO_LIVE_TEST_SERVER_ADDRESS = "localhost:8000-8100"
import os

os.environ["DJANGO_LIVE_TEST_SERVER_ADDRESS"] = DJANGO_LIVE_TEST_SERVER_ADDRESS

SILENCED_SYSTEM_CHECKS = ["fields.W342"]

# INSTALLED_APPS += ('django_extensions',)
