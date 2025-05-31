"""
Django settings for the staging server
"""

from .server import *

ALLOWED_HOSTS = []

AWS_STORAGE_BUCKET_NAME = None
STATIC_URL = "https://" + AWS_STORAGE_BUCKET_NAME + "/"
ADMIN_MEDIA_PREFIX = STATIC_URL + "admin/"

# from http://www.laurii.info/2013/05/improve-s3boto-djangostorages-performance-custom-settings/
AWS_S3_CUSTOM_DOMAIN = AWS_STORAGE_BUCKET_NAME


# customfit-testing uses a micro plan (RedisToGo) with a max-connection limit of 50
CELERY_REDIS_MAX_CONNECTIONS = 50
