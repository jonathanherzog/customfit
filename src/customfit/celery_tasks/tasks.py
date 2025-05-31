"""
This file holds all the tasks we'd like to execute asynchronously.
"""

import logging

from celery import shared_task
from django.core import management

logger = logging.getLogger(__name__)


# For testing that celery/redis is working. See .tests.TestCeleryWorking
@shared_task
def test_task(a, b):
    logger.info("test_celery_working called with input %s and %s", a, b)
    return a + b


#
# Misc utility tasks
#


@shared_task
def celery_clearsessions():
    """
    Clears the django_sessions table periodically so that performance
    doesn't get hosed by lookups in huge table whenever people are
    using wizards.
    """
    management.call_command("clearsessions", verbosity=0)
