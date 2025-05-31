from customfit.design_wizard.views import (
    AddMissingMeasurementsViewBase,
    AddMissingMeasurementsViewPatternspecMixin,
    AddMissingMeasurementsViewRedoMixin,
)

from ..models import SweaterIndividualGarmentParameters


class SweaterAddMissingMeasurementsMixin(object):

    def get_igp_class(self):
        return SweaterIndividualGarmentParameters


class SweaterAddMissingMeasurementsView(  # warning: order matters
    SweaterAddMissingMeasurementsMixin,
    AddMissingMeasurementsViewPatternspecMixin,
    AddMissingMeasurementsViewBase,
):

    pass


class SweaterAddMissingMeasurementsToRedoView(
    SweaterAddMissingMeasurementsMixin,
    AddMissingMeasurementsViewBase,
    AddMissingMeasurementsViewRedoMixin,
):

    def _check_consistency(self, request):
        redo = self.get_spec_source()
        self._check_redo_consistency_base(request, redo)
        super(SweaterAddMissingMeasurementsToRedoView, self)._check_consistency(request)
