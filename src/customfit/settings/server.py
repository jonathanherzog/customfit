"""
Common (default) django settings for all server environments
"""

import logging
import os
import re
import sys

import dj_database_url
from celery.schedules import crontab

from .base import *

# Get an instance of a logger
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# ------------------------> core django configurations <------------------------
# ------------------------------------------------------------------------------


# APP CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# DEBUG
# ------------------------------------------------------------------------------
"""
If you would like DEBUG to be True on a server,
heroku config:set DJANGO_DEBUG=True
Don't do that unless you know what you're doing.
When done,
heroku config:set DJANGO_DEBUG=False
"""
DEBUG = bool_from_env("DJANGO_DEBUG", False)


SERVER = True


# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------

# Per Heroku: parse database configuration from $DATABASE_URL
DATABASES["default"] = dj_database_url.config()


# CELERY CONFIGURATION
# ------------------------------------------------------------------------------

# Heroku Redis on Heroku, localhost as fallback
CELERY_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_DEFAULT_RATE_LIMIT = "10/s"
# Staging, testing, and production might have different limits
# for max-connections. Setting this to production's here so as
# to be as safe for production as possible. But we should/will
# over-write this in the Heroku server settings files just to
# be safe.
CELERY_REDIS_MAX_CONNECTIONS = 50


# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
# Allow all host headers. This should be overridden with specific servers
# in child settings files for security reasons.
ALLOWED_HOSTS = ["*"]

# See https://docs.djangoproject.com/en/1.5/topics/security/#ssl-https
# If we enable these, we're going to need to force https sitewide or
# unpredictable behavior results. And that means auditing for insecure
# content we might potentially be serving inline and doing something about it.
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

# Enables @secure_required; overrides base.py.
HTTPS_SUPPORT = True


# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------

# The cached loader is faster, but it's a pain to develop around since your
# template changes aren't reflected on reload.

TEMPLATES[0]["OPTIONS"]["loaders"] = [
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]


# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATIC_ROOT = "staticfiles"
STATIC_URL = "/static/"

STATICFILES_DIRS = (os.path.join(BASE_DIR, "static"),)


# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# URL CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------


# First, formatters to eliminate the following messages:
# * "celery@a314de2a-c963-4ddd-9445-bed345fb2fbc ready." from celery.redirected
# * "Created temporary file '/tmp/tmpRtPu3N'" from xhtml2pdf
# * "Not Found: /some_url" from django.request
#
# Note: we deal with things like RemovedInDjango19Warning by setting the
# PYTHONWARNING environment variable to 'ignore' (like we do for production/testing
# through the Heroku interface)


class Xhtml2pdfLogFilter(CFLogMessageFilter):
    def _match_message(self, msg, args):
        message = msg % args
        return message.startswith("Created temporary file")


class CeleryRedirectedFilter(CFLogMessageFilter):
    def _match_message(self, msg, args):
        message = msg % args
        return re.match("celery@[0-9a-f-]+ ready.", message) is not None


class NotFoundFilter(CFLogMessageFilter):
    def _match_message(self, msg, args):
        message = msg % args
        return message.startswith("Not Found: /")


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            # The default format doesn't include the name of the module/function. Let's include them
            "format": "%(asctime)s %(levelname)s %(name)s[%(funcName)s %(lineno)d]: %(message)s",
        },
    },
    "filters": {
        # A few of our third-party library produce irrelevant warning messages. Here are
        # some filters to remove them. Note: they should only be used in module-specific
        # loggers at the end of this configuration
        "temp_file": {
            "()": Xhtml2pdfLogFilter,
        },
        "celery_ready": {
            "()": CeleryRedirectedFilter,
        },
        "not_found": {
            "()": NotFoundFilter,
        },
    },
    "handlers": {
        # This will log everything at DEBUG level or above to standard-out, where it will
        # appear in Heroku's logs and be sent automatically to PaperTrail.
        # See http://codeinthehole.com/writing/console-logging-to-stdout-in-django .
        # Also http://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps/#logging-via-the-heroku-add-on
        # Note: the root logger will filter out everything below INFO, but
        # setting this handler to DEBUG lets sub-loggers bypass root to make sure
        # DEBUG level info makes it out to the console.
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": sys.stdout,
            "formatter": "verbose",
        },
    },
    # The backbone of this configuration is here, in the definition of this root logger. It will send
    # any log-line of INFO or higher (i.e., all log lines) to the sentry and console handlers. Sub-handlers
    # that want anything below INFO logged are configured to send those log-lines directly to handlers
    "root": {"handlers": ["console"], "level": "INFO"},
    # All loggers defined here provide special handling for log-lines from specific sources. In some cases,
    # we want to keep them from propogating up to the root handler so as to not cause infinite loops of error.
    # In other cases, we want to filter out extraneous warnings so as to not clutter up Sentry.
    "loggers": {
        # xhtml2pdf keeps producing 'warnings' of the form: "Created temporary file '/tmp/tmpRtPu3N'"
        # Let's remove those
        "xhtml2pdf": {
            "filters": ["temp_file"],
        },
        # celery keeps producing 'warnings' of the form: "celery@a314de2a-c963-4ddd-9445-bed345fb2fbc ready."
        # Let's remove those
        "celery.redirected": {
            "filters": ["celery_ready"],
        },
        # No, Django, we don't consider a 404 to be a WARNING.
        "django.request": {
            "filters": ["not_found"],
        },
    },
}


# STORAGES CONFIGURATION
# ------------------------------------------------------------------------------

INSTALLED_APPS += ("storages",)

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
    },
}

# will look for s3 access credentials in AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables

# AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', None)
# AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
AWS_QUERYSTRING_AUTH = False
# Google recommends that  images be cached for over a month.
AWS_HEADERS = {"Cache-Control": "max-age=3024000,public"}

# See https://bitbucket.org/david/django-storages/pull-request/89/add-fast-collectstatic-management-command/diff
AWS_S3_FAST_COLLECTSTATIC = True

# # Fixes certificate problem (*.s3.amazonaws.com not matching e.g.,
# # https://some-bucket.s3.us-east-1.amazonaws.com/
# from boto.s3.connection import ProtocolIndependentOrdinaryCallingFormat
# AWS_S3_CALLING_FORMAT = ProtocolIndependentOrdinaryCallingFormat()


# CACHE CONFIGURATION
# ------------------------------------------------------------------------------

# Make sure to only configure cache on servers where we've provisioned it.
if "MEMCACHIER_SERVERS" in list(os.environ.keys()):

    # Translate settings from memcachier (one particular service) into
    # provider-agnostic settings.
    os.environ["MEMCACHE_SERVERS"] = os.environ.get("MEMCACHIER_SERVERS", "").replace(
        ",", ";"
    )
    os.environ["MEMCACHE_USERNAME"] = os.environ.get("MEMCACHIER_USERNAME", "")
    os.environ["MEMCACHE_PASSWORD"] = os.environ.get("MEMCACHIER_PASSWORD", "")

    # Note: settings and comments taken from https://devcenter.heroku.com/articles/memcachier#django
    CACHES = {
        "default": {
            # Use pylibmc
            "BACKEND": "django.core.cache.backends.memcached.PyLibMCCache",
            # TIMEOUT is not the connection timeout! It's the default expiration
            # timeout that should be applied to keys! Setting it to `None`
            # disables expiration.
            "TIMEOUT": 2 * 24 * 60 * 60,  # 2 days
            "LOCATION": os.environ["MEMCACHE_SERVERS"],
            "OPTIONS": {
                # Use binary memcache protocol (needed for authentication)
                "binary": True,
                "username": os.environ["MEMCACHE_USERNAME"],
                "password": os.environ["MEMCACHE_PASSWORD"],
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

    """
    If we have a cache, let's use it to make our django_session lookups
    faster. Once we hit about 4500 users we started getting critical worker
    timeout issues multiple times per day; lookups on the
    django_sessions table were the plurality of database hits.
    See also https://docs.djangoproject.com/en/1.5/topics/http/sessions/ .
    """
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"


# ------------------------------------------------------------------------------
# -----------------> third-party and customfit configurations <-----------------
# ------------------------------------------------------------------------------


# CUSTOMFIT GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# TEST RUNNER CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# RAVELRY CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# CELERY CONFIGURATION
# ------------------------------------------------------------------------------

# Heroku doesn't have cron; celery is how we can schedule things.
# This requires that there be a celery worker process; it should be a no-op if
# one isn't running.
CELERY_TIMEZONE = "US/Eastern"  # for ease of reading for dev team

CELERY_BEAT_SCHEDULE = {
    "clearsessions_nightly": {
        "task": "customfit.celery_tasks.tasks.celery_clearsessions",
        "schedule": crontab(hour=4, minute=0),  # most users should be asleep
    },
}

# Servers should be using Redis unless explicitly set otherwise
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

# DJANGO-CMS CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# EASY THUMBNAILS CONFIGURATION
# ------------------------------------------------------------------------------

THUMBNAIL_DEFAULT_STORAGE = "storages.backends.s3.S3Storage"

# COMPRESSING LESS
PRECOMPRESS_LESS = True


# DJANGO reCAPTCHA CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides


# CRISPY FORMS CONFIGURATION
# ------------------------------------------------------------------------------

# No overrides
