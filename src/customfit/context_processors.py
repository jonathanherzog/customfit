# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.template import Context, Template

logger = logging.getLogger(__name__)


def on_production_server(request):
    return {"on_production_server": settings.IS_PRODUCTION_SERVER}


def precompress_less(request):
    """
    Returns a boolean we use to decide whether to use css precompiled from less
    or to recompile less on the fly. (Defaults to on-the-fly compilation locally
    and precompression on servers.)
    """
    return {"precompress_less": settings.PRECOMPRESS_LESS}
