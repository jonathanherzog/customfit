"""
Django settings for the production server
"""

import os

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .server import *

# SENTRY CONFIGURATION (First, so it can capture errors from the rest of the file)
# ------------------------------------------------------------------------------


sentry_sdk.init(dsn=os.environ["SENTRY_DSN"], integrations=[DjangoIntegration()])


ALLOWED_HOSTS = [
    # Fill me in
]

AWS_STORAGE_BUCKET_NAME = None  # Fill me in
STATIC_URL = "https://" + AWS_STORAGE_BUCKET_NAME + ".s3.us-east-1.amazonaws.com/"
ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"

# from http://www.laurii.info/2013/05/improve-s3boto-djangostorages-performance-custom-settings/
AWS_S3_CUSTOM_DOMAIN = AWS_STORAGE_BUCKET_NAME + ".s3.us-east-1.amazonaws.com"


IS_PRODUCTION_SERVER = True


# fast-chamber-9619 uses a mini plan (RedisToGo) with a max-connection limit of 50
CELERY_REDIS_MAX_CONNECTIONS = 50

THUMBNAIL_DEBUG = False

# Heroku Redis URLs are self-signed
CELERY_BROKER_URL = os.getenv("REDIS_URL") + "?ssl_cert_reqs=CERT_NONE"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
