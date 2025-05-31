import django.test

from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory

from ..factories import SweaterPatternSpecFactory, make_buttonband_from_pspec
from ..helpers import sweater_design_choices as SDC


class ButtonBandTest(django.test.TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_button_band_regression_seven_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 7)
        self.assertEqual(bb.evenly_spaced_buttonholes, True)
        self.assertEqual(bb.margin_stitches, 5)
        self.assertEqual(bb.inter_buttonhole_stitches, 11)
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")
        self.assertEqual(bb.stitches_before_first_buttonhole(), 5)
        self.assertEqual(bb.num_interior_buttonholes(), 5)

        total_stitches = sum(
            [
                bb.STITCHES_IN_BUTTONHOLE * bb.num_buttonholes,
                2 * bb.margin_stitches,
                bb.inter_buttonhole_stitches * (bb.num_buttonholes - 1),
            ]
        )
        self.assertEqual(bb.stitches, total_stitches)

    def test_button_band_regression_three_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=3,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 3)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

    def test_button_band_regression_one_button(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=1,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 1)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

    def test_button_band_regression_zero_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=0,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 0)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

    def test_area(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=10, stitches_length=1, stitches_number=5
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.area(), 72)


class VeeneckButtonBandTest(django.test.TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_button_band_regression_seven_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 7)
        self.assertEqual(bb.evenly_spaced_buttonholes, True)
        self.assertEqual(bb.margin_stitches, 5)
        self.assertEqual(bb.inter_buttonhole_stitches, 11)
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")
        self.assertEqual(bb.stitches_before_first_buttonhole(), 5)
        self.assertEqual(bb.num_interior_buttonholes(), 5)

        total_stitches = sum(
            [
                bb.STITCHES_IN_BUTTONHOLE * bb.num_buttonholes,
                2 * bb.margin_stitches,
                bb.inter_buttonhole_stitches * (bb.num_buttonholes - 1),
            ]
        )
        self.assertEqual(bb.stitches, total_stitches)

        self.assertEqual(bb.neckline_pickup_stitches, 112)
        self.assertEqual(
            bb.total_veeneck_cardigan_stitches(),
            sum([2 * bb.stitches, bb.neckline_pickup_stitches]),
        )

    def test_area(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.total_veeneck_cardigan_stitches(), 292)
        self.assertEqual(bb.area(), 116.8)

    def test_button_band_regression_three_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=3,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 3)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

        self.assertEqual(bb.neckline_pickup_stitches, 112)
        self.assertEqual(
            bb.total_veeneck_cardigan_stitches(),
            sum([2 * bb.stitches, bb.neckline_pickup_stitches]),
        )

    def test_button_band_regression_one_button(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=1,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 1)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

        self.assertEqual(bb.neckline_pickup_stitches, 112)
        self.assertEqual(
            bb.total_veeneck_cardigan_stitches(),
            sum([2 * bb.stitches, bb.neckline_pickup_stitches]),
        )

    def test_button_band_regression_zero_buttons(self):
        swatch = SwatchFactory(rows_length=1, rows_number=10)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=0,
        )
        bb = make_buttonband_from_pspec(pspec)

        self.assertEqual(bb.height, 2)
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.num_buttonholes, 0)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertIsNone(bb.margin_stitches)
        self.assertIsNone(bb.inter_buttonhole_stitches)
        self.assertIsNone(bb.stitches_before_first_buttonhole())
        self.assertIsNone(bb.num_interior_buttonholes())
        self.assertEqual(bb.half_height(), 1)
        self.assertEqual(bb.half_height_in_rows(), 10)
        self.assertEqual(bb.half_height_in_rows_rs(), 11)
        self.assertEqual(bb.half_height_in_rows_ws(), 10)
        self.assertEqual(bb.height_in_rows(), 20)
        self.assertEqual(bb.height_in_rows_rs(), 21)
        self.assertEqual(bb.height_in_rows_ws(), 20)
        self.assertEqual(bb.edging_stitch_patterntext(), "Garter Stitch")

        self.assertEqual(bb.neckline_pickup_stitches, 112)
        self.assertEqual(
            bb.total_veeneck_cardigan_stitches(),
            sum([2 * bb.stitches, bb.neckline_pickup_stitches]),
        )
