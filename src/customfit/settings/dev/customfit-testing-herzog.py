import os

from ..server import *


def always_show_toolbar(request):
    return True


if DEBUG:
    # Override debug-toolbar's logic about showing the toolbar (specifically, that our IP is in INTERNAL_IPS
    DEBUG_TOOLBAR_CONFIG["SHOW_TOOLBAR_CALLBACK"] = (
        "customfit.settings.dev.customfit-testing-herzog.always_show_toolbar"
    )


ALLOWED_HOSTS = []

AWS_STORAGE_BUCKET_NAME = None
STATIC_URL = "https://" + AWS_STORAGE_BUCKET_NAME + "/"
ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"

# from http://www.laurii.info/2013/05/improve-s3boto-djangostorages-performance-custom-settings/
AWS_S3_CUSTOM_DOMAIN = AWS_STORAGE_BUCKET_NAME


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            # The default format doesn't include the name of the module/function. Let's include them
            "format": "%(asctime)s %(levelname)s %(name)s[%(funcName)s]: %(message)s",
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
    # any log-line of INFO or higher (i.e., all log lines) to the console handlers. Sub-handlers
    # that want anything below INFO logged are configured to send those log-lines directly to handlers
    "root": {"handlers": ["console"], "level": "DEBUG"},
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
        #
        # What about things like RemovedInDjango19Warning and other warnings? We deal with those by
        # setting the PYTHONWARNINGS environment variable to 'ignore' in the Heroku web interface.
        #
        # We really do want everything produced by yarnstores.helpers to be logged to PaperTrail.
        # In particular we want debug information from copy_one_knitter to be logged in case we
        # need to go back and diagnose a problem.
        "customfit.yarnstores.helpers": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": True,
        },
    },
}
