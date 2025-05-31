import logging

from celery import shared_task
from django.contrib.auth.models import User

from customfit.patterns.models import IndividualPattern
from customfit.patterns.views import (
    IndividualPatternPdfView,
    IndividualPatternShortPdfView,
)

LOGGER = logging.getLogger(__name__)


class MockRequest(object):
    def __init__(self, user, session):
        self.user = user
        self.session = session
        self.META = {"REMOTE_ADDR": None}


@shared_task
def _cache_pattern(pattern_id, user_id, session=None):
    if session is None:
        session = {}
    LOGGER.info("Starting task _cache_pattern")
    pattern = IndividualPattern.even_unapproved.get(id=pattern_id)
    user = User.objects.get(id=user_id)

    # Cache the patterntext
    pattern.prefill_patterntext_cache()

    # Cache the PDFs
    mock_request = MockRequest(user, session)
    IndividualPatternPdfView(object=pattern, request=mock_request).make_pdf()
    IndividualPatternShortPdfView(object=pattern, request=mock_request).make_pdf()


def cache_pattern(pattern, request):
    # It is important that this function return quickly, so all the work happens in a celery task
    _cache_pattern.delay(pattern.id, request.user.id, None)


def uncache_pattern(pattern):

    # Flush the PDFs
    IndividualPatternPdfView(object=pattern).flush_cached_pdf()
    IndividualPatternShortPdfView(object=pattern).flush_cached_pdf()

    # Flush patterntext
    pattern.flush_patterntext_cache()
