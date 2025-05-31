from django.core.exceptions import ValidationError
from django.test import TestCase

from ..factories import (
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    SweaterRedoFactory,
)
from ..helpers import sweater_design_choices as SDC


class RedoModelTests(TestCase):

    def test_clean_hourglass_silhouette_and_fits(self):

        for silhouette in [SDC.SILHOUETTE_HALF_HOURGLASS, SDC.SILHOUETTE_HOURGLASS]:
            pattern = SweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette, garment_fit=SDC.FIT_HOURGLASS_AVERAGE
                )
            )
            for fit in SDC.FITS:
                redo = SweaterRedoFactory(pattern=pattern, garment_fit=fit)
                if fit in SDC.FIT_HOURGLASS:
                    redo.clean()
                else:
                    with self.assertRaisesRegex(
                        ValidationError,
                        "Hourglass/half-hourglass garments need hourglass fit",
                    ):
                        redo.clean()

    def test_clean_non_hourglass_silhouette_and_fits(self):

        for silhouette in [
            SDC.SILHOUETTE_ALINE,
            SDC.SILHOUETTE_TAPERED,
            SDC.SILHOUETTE_STRAIGHT,
        ]:
            pattern = SweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette, garment_fit=SDC.FIT_WOMENS_AVERAGE
                )
            )
            for fit in SDC.FITS:
                redo = SweaterRedoFactory(pattern=pattern, garment_fit=fit)
                if fit in SDC.FIT_HOURGLASS:
                    with self.assertRaisesRegex(
                        ValidationError,
                        "Non-hourglass/half-hourglass garments cannot use hourglass fits",
                    ):
                        redo.clean()
                else:
                    redo.clean()
