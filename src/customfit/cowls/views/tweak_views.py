import logging

from customfit.design_wizard.views import BaseRedoTweakView, BaseTweakGarmentView

from ..forms import (
    TweakCowlIndividualGarmentParameters,
    TweakCowlRedoIndividualGarmentParameters,
)
from ..models import COWL_TWEAK_FIELDS, CowlIndividualGarmentParameters

logger = logging.getLogger(__name__)


class _TweakCowlViewBase(object):

    model = CowlIndividualGarmentParameters

    def get_tweak_fields(self):
        return COWL_TWEAK_FIELDS


class TweakCowlView(_TweakCowlViewBase, BaseTweakGarmentView):

    template_name = "cowls/tweak_page.html"
    form_class = TweakCowlIndividualGarmentParameters


class TweakRedoCowlView(_TweakCowlViewBase, BaseRedoTweakView):
    template_name = "cowls/tweak_redo.html"
    form_class = TweakCowlRedoIndividualGarmentParameters
