"""
Common (default) django settings for local (developer) environments
"""

from .base import *

SERVER = False

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",  # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        "NAME": "customfit-pre-opensource",  # Or path to database file if using sqlite3.
        "USER": "",  # Not used with sqlite3.
        "PASSWORD": "",  # Not used with sqlite3.
        "HOST": "localhost",  # Set to empty string for localhost. Not used with sqlite3.
        "PORT": "5432",  # Set to empty string for default. Not used with sqlite3.
    }
}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "brief": {
            "format": "%(asctime)s %(levelname)s %(name)s[%(funcName)s]: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",  # Change to DEBUG to see all logs in the console. Be ready for the firehose
            "class": "logging.StreamHandler",
            "formatter": "brief",
        },
    },
    "root": {
        # Send all INFO to the console
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "customfit": {
            # Provide special handling for log-lines from our code.
            "level": "DEBUG",  # Set to DEBUG for the firehose
            "handlers": ["console"],
            "propagate": False,
        }
    },
}


DJANGO_USE_EXTERNAL_CELERY = bool_from_env("DJANGO_USE_EXTERNAL_CELERY", False)
if DJANGO_USE_EXTERNAL_CELERY:

    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = CELERY_BROKER_URL
    CELERY_TASK_ALWAYS_EAGER = False
    CELERY_TASK_EAGER_PROPAGATES = False

    # Note: settings and comments taken from https://devcenter.heroku.com/articles/memcachier#django
    CACHES = {
        "default": {
            # Use pylibmc
            "BACKEND": "django.core.cache.backends.memcached.PyLibMCCache",
            # TIMEOUT is not the connection timeout! It's the default expiration
            # timeout that should be applied to keys! Setting it to `None`
            # disables expiration.
            "TIMEOUT": None,
            "LOCATION": "127.0.0.1",
            "OPTIONS": {
                # Use binary memcache protocol (needed for authentication)
                "binary": True,
                "behaviors": {
                    # Enable faster IO
                    "no_block": True,
                    "tcp_nodelay": True,
                    # Keep connection alive
                    "tcp_keepalive": True,
                    # Timeout settings
                    "connect_timeout": 2000,  # ms
                    "send_timeout": 750 * 1000,  # us
                    "receive_timeout": 750 * 1000,  # us
                    "_poll_timeout": 2000,  # ms
                    # Better failover
                    "ketama": True,
                    "remove_failed": 1,
                    "retry_timeout": 2,
                    "dead_timeout": 30,
                },
            },
        }
    }
