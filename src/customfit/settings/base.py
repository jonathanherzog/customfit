"""
Common (default) django settings for all environments
"""

import logging
import os
import secrets
import sys

# Things which must be defined first, as settings rely on them.
home = os.path.expanduser("~")
PROJECT_ROOT = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..")


def rel(*x):
    return os.path.abspath(os.path.join(PROJECT_ROOT, *x))


def str_from_env(env_var_name, default):
    """
    Get the (string) value of the environment variable. If it is not
    defined, return default value.
    """
    if env_var_name in os.environ:
        str_val = os.environ.get(env_var_name)
        return str_val
    else:
        return default


def bool_from_env(env_var_name, default):
    """
    Get the (string) value of the environment variable and
    convert to a boolean in a human-friendly way. If it is not
    defined or not recognized as a known value, return default value.
    """
    assert default in [True, False]  # Note that True/False are just names for 1/0
    str_val = str_from_env(env_var_name, None)
    if str_val is None:
        return default
    else:
        str_val = str_val.lower()
        if str_val in ["true", "yes", "on", "1"]:
            return True
        elif str_val in ["false", "no", "off", "0"]:
            return False
        else:
            # includes the case where str_val == ''
            return default


class CFLogMessageFilter(logging.Filter):
    """
    Change LogRecord log-level objects based on their message. Why?
    Our Sentry instance is cluttered by unneeded messages from third-party libraries.
    We can use this to reduce the log-level of specific records based
    on their message, allowing us to downgrade, for example:

    * "Created temporary file '/tmp/tmpdskfjsdf'" from xhtml2pdf.util,
    * "celery@a314de2a-c963-4ddd-9445-bed345fb2fbc ready." from celery.redirect

    and other log-messages that we know are not actually errors or warnings
    (despite being logged as such).

    To use: subclass, and implement _match_message(). You can also redefine
    new_log_level if you want it to be given a log-level other than INFO, and
    old_log_level if the target log-record is not at WARNING.
    """

    old_log_level = logging.WARNING
    new_log_level = logging.INFO

    def _match_message(self, message):
        raise NotImplementedError

    def filter(self, record):
        if self._match_message(record.msg, record.args):
            if record.levelno == self.old_log_level:
                record.levelno = self.new_log_level
                record.levelname = logging.getLevelName(self.new_log_level)
        # Return 0 if the record is to be forgotten, non-zero for the record to be logged
        return 1


# ------------------------------------------------------------------------------
# ------------------------> core django configurations <------------------------
# ------------------------------------------------------------------------------

# APP CONFIGURATION
# ------------------------------------------------------------------------------

INSTALLED_APPS = (
    ###########################################################################
    #
    # Core Apps
    #
    ###########################################################################
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.admindocs",
    "django.contrib.redirects",
    ###########################################################################
    #
    # Third-party Apps
    #
    ###########################################################################
    # Misc
    # ----------------------------------
    "dbtemplates",  # must come before our own apps
    "crispy_forms",
    "crispy_bootstrap3",
    #    'admin_honeypot',
    "clear_cache",
    "django_markdown2",
    "django_recaptcha",
    "reversion",
    # Optimizations
    # ------------
    "easy_thumbnails",
    "easy_thumbnails.optimize",
    # For admin/customer support
    # --------------------------
    "impersonate",
    ###########################################################################
    #
    # Our Apps
    #
    ###########################################################################
    "customfit.stitches",
    "customfit.designs",
    "customfit.pattern_spec",
    "customfit.garment_parameters",
    "customfit.schematics",
    "customfit.pieces",
    "customfit.patterns",
    "customfit.design_wizard",
    "customfit.graded_wizard",
    "customfit.swatches",
    "customfit.bodies",
    "customfit.userauth",
    "customfit.uploads",
    "customfit.celery_tasks",
    "customfit.sweaters",
    "customfit.cowls",
    "customfit.knitting_calculators",
    "customfit.test_garment",
)


# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    # GZipMiddleware needs to be first; middleware
    # classes execute in reverse order to how they're defined, and these
    # need to apply after all other possible modifications to the HTML.
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "impersonate.middleware.ImpersonateMiddleware",
    "django.contrib.redirects.middleware.RedirectFallbackMiddleware",
]


# DEBUG
# ------------------------------------------------------------------------------

# By setting this an an environment variable, it is easy to switch debug on in
# servers to do a quick test.
DEBUG = bool_from_env("DJANGO_DEBUG", True)


# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------

FIXTURE_DIRS = (rel("fixtures"),)


# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------

ADMINS = ()

MANAGERS = ADMINS

ADMIN_SITE_PATH = "makewearsudo"

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------

# Overridden by real config in all server and personal settings files.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "customfit_django.db",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    }
}

# Model configuration
# ------------------------------------------------------------------------------

# See https://docs.djangoproject.com/en/3.2/releases/3.2/#customizing-type-of-auto-created-primary-keys
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = "America/New_York"

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = "en"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Make this unique, and don't share it with anybody.
SECRET_KEY = str_from_env("DJANGO_SECRET_KEY", secrets.token_hex(256))


# See https://docs.djangoproject.com/en/dev/releases/1.6/#default-session-serialization-switched-to-json
SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"

MIGRATION_MODULES = {}  # We will add to this below

IS_PRODUCTION_SERVER = False  # overridden in production.py

# Required for the 'debug' template variable to exist; we use this to control
# how we build less files.
INTERNAL_IPS = ("127.0.0.1",)


# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": False,
        "DIRS": ["customfit/templates", rel("templates")],
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "customfit.context_processors.on_production_server",
                "customfit.context_processors.precompress_less",
                "django.template.context_processors.request",
            ],
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
                # Note that we are NOT including dbtemplates here as we intend
                # to load them through model fields, not through template names.
            ],
        },
    }
]


# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------

# Absolute filesystem path to the directory that will hold collected static
# files.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = rel("collectedstatic")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = "/static/"

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    rel("static"),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------

MEDIA_ROOT = rel("media")

MEDIA_URL = "/media/"


# URL CONFIGURATION
# ------------------------------------------------------------------------------

ROOT_URLCONF = "customfit.urls"

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = "customfit.wsgi.application"


# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = ("customfit.userauth.backends.CaseInsensitiveModelBackend",)

# Where to find the login URL
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"


# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------

# Deprecated. The original declaration of LOGGING, here, was shadowed by declarations
# in local.py and server.py. This makes sense, actually. Our logging needs are so
# different in the 'heroku server' case and the 'local development' case that it
# makes sense to have totally separate declarations that are independently crafted.


# STORAGES CONFIGURATION
# ------------------------------------------------------------------------------

# base.py uses default storage
# server.py sets up Amazon S3 storage, except for the storage bucket
# staging.py and production.py have their own buckets
# if you would like to test amazon on localhost, try the following code from:
#
# if ENABLE_S3:
#     INSTALLED_APPS += (
#         'storages',
#     )
#     DEFAULT_FILE_STORAGE = 'storages.backends.s3.S3Storage"'
#     AWS_ACCESS_KEY_ID = None
#     AWS_SECRET_ACCESS_KEY = None
#     AWS_QUERYSTRING_AUTH = False
#     AWS_STORAGE_BUCKET_NAME = None
#
# see http://django-storages.readthedocs.org/en/latest/backends/amazon-S3.html


# CACHE CONFIGURATION
# ------------------------------------------------------------------------------

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


# ERROR-PAGE CONFIGURATION
# ------------------------------------------------------------------------------

# Because we user Heroku, we actually need to deal with two possible error
# pages: one that Django will use when it catches an error, and one that
# Heroku will use when Django itself crashes or falls into an infinite loop.
# The latter will be a static page which is put in S3 by 'collectstatic'. So
# rather than maintain two separate templates for what is really the same page,
# we will just tell Django to redirect to Heroku's page. See urls.py for the
# actual implementation of this redirect, but we will set the URL for the
# error-page here.

# User heroku's maintenance page (with a production-valid default)
# Note: becuase the staticfiles app uses settings from this file, I'm not
# sure that we can use it to create the following URL. Unfortunately, the
# better-safe-than-sorry principle leads me to violate DRY and hard-code the
# full url.
DEFAULT_ERROR_PAGE = (
    "//https://somebucket.s3.us-east-1.amazonaws.com/error-pages/site-error.html"
)

ERROR_PAGE_URL = os.environ.get("ERROR_PAGE_URL", DEFAULT_ERROR_PAGE)


# ------------------------------------------------------------------------------
# -----------------> third-party and customfit configurations <-----------------
# ------------------------------------------------------------------------------


# CUSTOMFIT GENERAL CONFIGURATION
# ------------------------------------------------------------------------------

# How many photos can people upload for a given body/pattern/swatch?
MAX_PICTURES = 10


# Enables @secure_required in src/customfit/decorators.py.
# Should be True in production. May be false elsewhere.
# We could require https everywhere, but should not do so unless we can verify
# that all our third-party content (streaming videos, images, bootstrap, fonts)
# can be served securely - if we're https and they're http users will get scary
# warning messages.
HTTPS_SUPPORT = False


# CELERY CONFIGURATION
# ------------------------------------------------------------------------------


# Overridden in server.py, can be overridden in local.py
CELERY_TASK_ALWAYS_EAGER = (
    True  # do you don't need redis/celery processes just to run tests
)
CELERY_TASK_EAGER_PROPAGATES = True


# EASY THUMBNAILS CONFIGURATION
# ------------------------------------------------------------------------------


THUMBNAIL_ALIASES = {
    "": {
        # Project-wide aliases
        # Note: setting widths to the pixel-widths specified in bootstrap,
        # plus an additional 20%. Also, we experimented with image-qualities
        # of 50% or less but decided we didn't like them.
        # _crop aliases yield square pictures, which are cropped rather
        # than distorted. The ',0' option horizontally centers (default) and
        # crops from the top down - this will safeguard pictures containing
        # people's heads from decapitation.
        # They are named in accordance with Bootstrap naming conventions for
        # grid layout classes.
        "col-md-1": {
            "size": (72, 5008),
        },
        "col-md-1-square": {
            "size": (72, 72),
            "crop": ",0",
        },
        "col-md-2": {
            "size": (168, 5008),
        },
        "col-md-2-square": {
            "size": (168, 168),
            "crop": ",0",
        },
        "col-md-3": {
            "size": (264, 5008),
        },
        "col-md-3-square": {
            "size": (264, 264),
            "crop": ",0",
        },
        "col-md-4": {
            "size": (360, 5008),
        },
        "col-md-4-square": {
            "size": (360, 360),
            "crop": ",0",
        },
        "col-md-5": {
            "size": (456, 5008),
        },
        "col-md-5-square": {
            "size": (456, 456),
            "crop": ",0",
        },
        "col-md-6": {
            "size": (552, 5008),
        },
        "col-md-6-square": {
            "size": (552, 552),
            "crop": ",0",
        },
        "col-md-7": {
            "size": (648, 5008),
        },
        "col-md-7-square": {
            "size": (648, 648),
            "crop": ",0",
        },
        "col-md-8": {
            "size": (744, 5008),
        },
        "col-md-8-square": {
            "size": (744, 744),
            "crop": ",0",
        },
        "col-md-9": {
            "size": (840, 5008),
        },
        "col-md-9-square": {
            "size": (840, 840),
            "crop": ",0",
        },
        "col-md-10": {
            "size": (936, 5008),
        },
        "col-md-10-square": {
            "size": (936, 936),
            "crop": ",0",
        },
        "col-md-11": {
            "size": (1032, 5008),
        },
        "col-md-11-square": {
            "size": (1032, 1032),
            "crop": ",0",
        },
        "col-md-12": {
            "size": (1128, 5008),
        },
        "col-md-12-square": {
            "size": (1128, 1128),
            "crop": ",0",
        },
        "col-md-4-split": {  # needed for alt images on personalize-design page
            "size": (180, 5008),
        },
        "awesome-crop": {
            "size": (264, 396),
            "crop": ",0",
        },
    }
}

THUMBNAIL_OPTIMIZE_COMMAND = {
    "png": "optipng {filename}",
    "gif": "optipng {filename}",
    "jpeg": "jpegoptim {filename}",
    "jpg": "jpegoptim {filename}",
}

THUMBNAIL_DEBUG = True


# DJANGO reCAPTCHA CONFIGURATION
# ------------------------------------------------------------------------------

RECAPTCHA_PUBLIC_KEY = os.environ.get("RECAPTCHA_PUBLIC_KEY", "none")
RECAPTCHA_PRIVATE_KEY = os.environ.get("RECAPTCHA_PRIVATE_KEY", "none")

# CRISPY FORMS CONFIGURATION
# ------------------------------------------------------------------------------

CRISPY_TEMPLATE_PACK = "bootstrap3"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap3"

# LESS COMPRESSION

COMPRESS_OFFLINE = False
PRECOMPRESS_LESS = False


# Django-debug-toolbar
# -----------------------
TESTING = "test" in sys.argv
if DEBUG and not TESTING:
    MIDDLEWARE += [
        "debug_toolbar.middleware.DebugToolbarMiddleware",
    ]

    INSTALLED_APPS += ("debug_toolbar",)
    DEBUG_TOOLBAR_CONFIG = {
        "PROFILER_MAX_DEPTH": int(
            str_from_env("DJANGO_DEBUG_TOOLBAR_PROFILER_MAX_DEPTH", "10")
        )
    }
