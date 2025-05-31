import logging

from customfit.design_wizard.views import BaseRedoTweakView, BaseTweakGarmentView

from ..forms import (
    TWEAK_FIELDS,
    TWEAK_FIELDS_VEST,
    TweakSweaterIndividualGarmentParameters,
    TweakSweaterRedoIndividualGarmentParameters,
)
from ..models import SweaterIndividualGarmentParameters
from customfit.helpers.math_helpers import (
    round,
    ROUND_DOWN,
)
logger = logging.getLogger(__name__)


class _TweakSweaterViewBase(object):

    model = SweaterIndividualGarmentParameters

    def get_tweak_fields(self):
        instance = self.get_object()
        if instance.has_sleeves():
            tweak_fields = TWEAK_FIELDS
        else:
            tweak_fields = TWEAK_FIELDS_VEST
        return tweak_fields

    def _get_restore_data(self):
        restore_data = super(_TweakSweaterViewBase, self)._get_restore_data()
        igp_dict = self._get_igp_dict()

        if self.request.user.profile.display_imperial:
            conversion = 1.0
            precision = 0.25
        else:
            conversion = 2.54
            precision = 0.5

        total_shoulder_width = conversion * (
            igp_dict["back_cross_back_width"] - igp_dict["back_neck_opening_width"]
        )
        one_shoulder_width = round(0.5 * total_shoulder_width, ROUND_DOWN, precision)
        restore_data["id_shoulder_width"] = one_shoulder_width
        return restore_data


class TweakSweaterView(_TweakSweaterViewBase, BaseTweakGarmentView):
    template_name = "sweaters/tweak_page.html"

    form_class = TweakSweaterIndividualGarmentParameters


class TweakRedoSweaterView(_TweakSweaterViewBase, BaseRedoTweakView):
    template_name = "sweaters/tweak_redo.html"
    form_class = TweakSweaterRedoIndividualGarmentParameters
