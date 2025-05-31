import smtplib
from unittest.mock import MagicMock, patch

from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from customfit.celery_tasks import tasks
from customfit.userauth.factories import UserFactory


class CeleryWorkingTest(TestCase):

    # This class tests that celery and Redis are receiving tasks and executing them.
    # If you don't want to test this (in your local dev setup, for example) then
    # set CELERY_TASK_ALWAYS_EAGER to True in your settings file.

    def test_celery_working(self):
        async_result = tasks.test_task.delay(2, 2)
        x = async_result.get(timeout=10)
        self.assertEqual(x, 4)
