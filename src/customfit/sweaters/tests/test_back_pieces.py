import django.test

from customfit.bodies.factories import BodyFactory, get_csv_body
from customfit.helpers.row_parities import RS, WS
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ..exceptions import ArmholeShapingError
from ..factories import (
    GradedSweaterPatternPiecesFactory,
    GradedSweaterSchematicFactory,
    SweaterBackSchematicFactory,
)
from ..factories import SweaterPatternSpecFactory as PatternSpecFactory
from ..factories import (
    create_sweater_back,
    make_sweaterback_from_pspec,
    make_vestback_from_pspec,
)
from ..helpers import sweater_design_choices as SDC
from ..helpers.secret_sauce import ease_tolerances, rounding_directions
from ..models import GradedSweaterBack, GradedVestBack, SweaterBack


class SweaterBackTest(django.test.TestCase):

    def setUp(self):
        StitchFactory(
            name="Stockinette",
            user_visible=True,
            is_waist_hem_stitch=False,
            is_sleeve_hem_stitch=False,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=False,
            is_allover_stitch=True,
            is_panel_stitch=False,
        )

        StitchFactory(
            name="Cabled Check Stitch",
            user_visible=True,
            # Note: following line is not true in production any more
            repeats_x_mod=1,
            repeats_mod_y=4,
            is_waist_hem_stitch=False,
            is_sleeve_hem_stitch=False,
            is_neckline_hem_stitch=False,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=False,
            is_allover_stitch=True,
            is_panel_stitch=False,
        )

        StitchFactory(
            name="1x1 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        )

        StitchFactory(
            name="Open Mesh Lace",
            user_visible=True,
            repeats_x_mod=0,
            repeats_mod_y=3,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=False,
        )

    def test_sweater_back_regression_1(self):
        sb = create_sweater_back()
        self.assertEqual(sb.cast_ons, 98)
        self.assertEqual(sb.waist_hem_height, 1.5)
        self.assertEqual(sb.hem_to_waist, 7.5)
        self.assertEqual(sb.begin_decreases_height, 2.9285714285714284)
        self.assertEqual(sb.pre_marker, 33)
        self.assertEqual(sb.post_marker, 33)
        self.assertEqual(sb.inter_marker, 32)
        self.assertEqual(sb.has_waist_decreases, True)
        self.assertFalse(sb.any_waist_decreases_on_ws)
        self.assertEqual(sb.num_waist_standard_decrease_rows, 5)
        self.assertEqual(sb.num_waist_double_dart_rows, 0)
        self.assertEqual(sb.num_waist_triple_dart_rows, 0)
        self.assertEqual(sb.num_bust_standard_increase_rows, 6)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sb.num_bust_triple_dart_rows, 0)
        self.assertEqual(sb.num_waist_decrease_rows_knitter_instructions, 5)
        self.assertEqual(sb.num_waist_standard_decrease_rows, 5)
        self.assertEqual(sb.num_waist_standard_decrease_repetitions, 4)
        self.assertEqual(sb.rows_between_waist_standard_decrease_rows, 5)
        self.assertEqual(sb.waist_double_darts, False)
        self.assertEqual(sb.waist_double_dart_marker, None)
        self.assertEqual(sb.waist_inter_double_marker, None)
        self.assertEqual(sb.num_waist_double_dart_decrease_repetitions, None)
        self.assertEqual(sb.num_waist_non_double_dart_decrease_repetitions, None)
        self.assertEqual(
            sb.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(sb.waist_triple_darts, False)
        self.assertEqual(sb.waist_triple_dart_marker, None)
        self.assertEqual(sb.waist_inter_triple_marker, None)
        self.assertEqual(sb.num_waist_triple_dart_repetitions, None)
        self.assertEqual(sb.waist_stitches, 88)
        self.assertEqual(sb.has_bust_increases, True)
        self.assertFalse(sb.any_bust_increases_on_ws)
        self.assertEqual(sb.num_bust_increase_rows_knitter_instructions, 6)
        self.assertEqual(sb.num_bust_standard_increase_rows, 6)
        self.assertEqual(sb.num_bust_standard_increase_repetitions, 5)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 9)
        self.assertEqual(sb.bust_pre_standard_dart_marker, 28)
        self.assertEqual(sb.bust_double_darts, False)
        self.assertEqual(sb.bust_pre_double_dart_marker, None)
        self.assertEqual(sb.bust_inter_double_dart_markers, None)
        self.assertEqual(sb.bust_inter_double_and_standard_dart_markers, None)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sb.num_bust_non_double_dart_increase_repetitions, None)
        self.assertEqual(
            sb.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(sb.bust_triple_darts, False)
        self.assertEqual(sb.bust_pre_triple_dart_marker, None)
        self.assertEqual(sb.bust_inter_triple_dart_markers, None)
        self.assertEqual(sb.bust_inter_double_and_triple_dart_markers, None)
        self.assertEqual(sb.num_bust_triple_dart_repetitions, None)
        self.assertEqual(sb.bust_stitches, 100)
        self.assertAlmostEqual(sb.hem_to_bust_increase_end, 14.7857, 3)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 16)
        self.assertEqual(sb.armhole_x, 5)
        self.assertEqual(sb.armhole_y, 3)
        self.assertEqual(sb.armhole_z, 7)
        self.assertEqual(sb.hem_to_neckline_shaping_start, 23)
        self.assertEqual(sb.hem_to_neckline_shaping_end, 23 + (4 / 7))
        self.assertEqual(sb.hem_to_shoulders, 24)
        self.assertEqual(sb.first_shoulder_bindoff, 9)
        self.assertEqual(sb.second_shoulder_bindoff, 8)
        self.assertEqual(sb.num_shoulder_stitches, 17)
        self.assertEqual(sb.actual_hip, 19.600000000000001)
        self.assertEqual(sb.actual_waist, 17.600000000000001)
        self.assertEqual(sb.actual_bust, 20)
        self.assertEqual(sb.actual_armhole_depth, 8)
        self.assertEqual(sb.actual_shoulder_stitch_width, 3.3999999999999999)
        self.assertAlmostEqual(sb.actual_armhole_circumference, 9.755, 2)
        self.assertEqual(sb.cross_chest_stitches, 70)
        self.assertEqual(sb.actual_cross_chest, 14)
        self.assertEqual(sb.actual_neck_opening, 7.2000000000000002)
        self.assertEqual(sb.hem_to_waist, 7.5)
        self.assertEqual(sb.actual_hem_to_armhole, 16)
        self.assertEqual(sb.actual_waist_to_armhole, 8.5)
        self.assertEqual(sb.actual_hem_to_shoulder, 24)
        self.assertEqual(sb.bust_use_standard_markers, True)

        self.assertEqual(sb.waist_hem_height_in_rows, 10)
        self.assertEqual(sb.begin_decreases_height_in_rows, 20)
        self.assertEqual(sb.hem_to_waist_in_rows, 52)
        self.assertEqual(sb._first_decrease_row, 21)
        self.assertEqual(sb.last_decrease_row, 45)
        self.assertEqual(sb._rows_in_decreases(), 25)
        self.assertEqual(sb._first_increase_row, 53)
        self.assertEqual(sb.last_increase_row, 103)
        self.assertEqual(sb._rows_in_increases(), 51)
        self.assertEqual(sb.last_decrease_to_waist_in_rows, 8)
        self.assertEqual(sb.hem_to_neckline_in_rows(RS), 161)
        self.assertEqual(sb.hem_to_neckline_in_rows(WS), 162)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(RS), 59)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(WS), 60)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(RS), 117)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(WS), 118)
        self.assertEqual(sb.hem_to_armhole_in_rows(RS), 113)
        self.assertEqual(sb.hem_to_armhole_in_rows(WS), 112)
        self.assertEqual(sb.hem_to_first_armhole_in_rows, 112)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(RS), 11)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(WS), 10)
        self.assertEqual(sb.last_increase_to_first_armhole_in_rows, 10)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(RS), 69)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(WS), 68)
        self.assertEqual(sb.last_decrease_to_first_armhole_in_rows, 68)
        self.assertEqual(sb.hem_to_shoulders_in_rows(RS), 169)
        self.assertEqual(sb.hem_to_shoulders_in_rows(WS), 168)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, RS), None)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, WS), None)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, RS), 48)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, WS), 49)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, RS), 49)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, WS), 50)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(RS), 49)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(WS), 50)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(WS), 17)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(RS), 16)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(WS), 17)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(RS), 18)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, WS), 55)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, WS), 56)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, RS), 56)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, RS), 57)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, WS), 34)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, RS), 33)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, WS), 32)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, RS), 31)
        self.assertAlmostEqual(sb.actual_last_increase_to_first_armhole, 1.42857, 3)

        self.assertAlmostEqual(sb.area(), 421.6, 1)

        self.assertEqual(sb.actual_neck_opening_width, 36 / 5)

    def test_sweater_back_regression2(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_number=10, stitches_length=1
        )
        body = get_csv_body("Test 5")
        pspec = PatternSpecFactory(body=body, swatch=swatch)
        sb = make_sweaterback_from_pspec(pspec)

        self.assertEqual(sb.cast_ons, 165)
        self.assertEqual(sb.pre_marker, 55)
        self.assertEqual(sb.post_marker, 55)
        self.assertEqual(sb.inter_marker, 55)
        self.assertEqual(sb.waist_hem_height, 1.5)
        self.assertEqual(sb.has_waist_decreases, True)
        self.assertFalse(sb.any_waist_decreases_on_ws)
        self.assertEqual(sb.num_waist_standard_decrease_rows, 1)
        self.assertEqual(sb.num_waist_double_dart_rows, 3)
        self.assertEqual(sb.num_waist_triple_dart_rows, 3)
        self.assertEqual(sb.num_bust_standard_increase_rows, 2)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(sb.num_bust_triple_dart_rows, 4)
        self.assertEqual(sb.num_waist_decrease_rows_knitter_instructions, 7)
        self.assertEqual(sb.num_waist_standard_decrease_repetitions, 0)
        self.assertEqual(sb.rows_between_waist_standard_decrease_rows, 3)
        self.assertEqual(sb.waist_double_darts, True)
        self.assertEqual(sb.waist_double_dart_marker, 27)
        self.assertEqual(sb.waist_inter_double_marker, 28)
        self.assertEqual(sb.num_waist_double_dart_decrease_repetitions, 2)
        self.assertEqual(sb.num_waist_non_double_dart_decrease_repetitions, 0)
        self.assertEqual(
            sb.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(sb.waist_triple_darts, True)
        self.assertEqual(sb.waist_triple_dart_marker, 13)
        self.assertEqual(sb.waist_inter_triple_marker, 14)
        self.assertEqual(sb.num_waist_triple_dart_repetitions, 2)
        self.assertEqual(sb.begin_decreases_height, 2.75)
        self.assertEqual(sb.hem_to_waist, 7.0)
        self.assertEqual(sb.waist_stitches, 145)
        self.assertEqual(sb.has_bust_increases, True)
        self.assertFalse(sb.any_bust_increases_on_ws)
        self.assertEqual(sb.num_bust_increase_rows_knitter_instructions, 11)
        self.assertEqual(sb.num_bust_standard_increase_rows, 2)
        self.assertEqual(sb.num_bust_standard_increase_repetitions, 1)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sb.bust_pre_standard_dart_marker, 48)
        self.assertEqual(sb.bust_double_darts, True)
        self.assertEqual(sb.bust_pre_double_dart_marker, 21)
        self.assertEqual(sb.bust_inter_double_dart_markers, 103)
        self.assertEqual(sb.bust_inter_double_and_standard_dart_markers, 27)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(sb.num_bust_non_double_dart_increase_repetitions, 0)
        self.assertEqual(
            sb.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(sb.bust_triple_darts, True)
        self.assertEqual(sb.bust_pre_triple_dart_marker, 10)
        self.assertEqual(sb.bust_inter_triple_dart_markers, 125)
        self.assertEqual(sb.bust_inter_double_and_triple_dart_markers, 11)
        self.assertEqual(sb.bust_stitches, 175)
        self.assertEqual(sb.num_bust_triple_dart_repetitions, 3)
        self.assertEqual(sb.hem_to_bust_increase_end, 12.25)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 13.5)
        self.assertEqual(sb.armhole_x, 10)
        self.assertEqual(sb.armhole_y, 9)
        self.assertEqual(sb.armhole_z, 2)
        self.assertEqual(sb.hem_to_neckline_shaping_start, 19.5)
        self.assertEqual(sb.hem_to_neckline_shaping_end, 19.5)
        self.assertEqual(sb.hem_to_shoulders, 20.5)
        self.assertEqual(sb.first_shoulder_bindoff, 17)
        self.assertEqual(sb.second_shoulder_bindoff, 16)
        self.assertEqual(sb.num_shoulder_stitches, 33)
        self.assertEqual(sb.actual_hip, 16.5)
        self.assertEqual(sb.actual_waist, 14.5)
        self.assertEqual(sb.actual_bust, 17.5)
        self.assertEqual(sb.actual_armhole_depth, 7)
        self.assertEqual(sb.actual_shoulder_stitch_width, 3.2999999999999998)
        self.assertAlmostEqual(sb.actual_armhole_circumference, 8.4198, 2)
        self.assertEqual(sb.cross_chest_stitches, 133)
        self.assertEqual(sb.actual_cross_chest, 13.300000000000001)
        self.assertEqual(sb.actual_neck_opening, 6.7)
        self.assertEqual(sb.hem_to_waist, 7)
        self.assertEqual(sb.actual_hem_to_armhole, 13.5)
        self.assertEqual(sb.actual_waist_to_armhole, 6.5)
        self.assertEqual(sb.actual_hem_to_shoulder, 20.5)
        self.assertEqual(sb.bust_use_standard_markers, True)

        self.assertEqual(sb.waist_hem_height_in_rows, 6)
        self.assertEqual(sb.begin_decreases_height_in_rows, 12)
        self.assertEqual(sb.hem_to_waist_in_rows, 28)
        self.assertEqual(sb.last_decrease_to_waist_in_rows, 4)
        self.assertEqual(sb.hem_to_neckline_in_rows(RS), 79)
        self.assertEqual(sb.hem_to_neckline_in_rows(WS), 78)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(RS), 31)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(WS), 30)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(RS), 55)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(WS), 54)
        self.assertEqual(sb.hem_to_armhole_in_rows(RS), 55)
        self.assertEqual(sb.hem_to_armhole_in_rows(WS), 54)
        self.assertEqual(sb.hem_to_first_armhole_in_rows, 54)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(RS), 7)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(WS), 6)
        self.assertEqual(sb.last_increase_to_first_armhole_in_rows, 6)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(RS), 31)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(WS), 30)
        self.assertEqual(sb.last_decrease_to_first_armhole_in_rows, 30)
        self.assertEqual(sb.hem_to_shoulders_in_rows(RS), 83)
        self.assertEqual(sb.hem_to_shoulders_in_rows(WS), 82)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, RS), None)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, WS), None)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, WS), 23)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, RS), 24)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, WS), 24)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, RS), 25)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(RS), 25)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(WS), 24)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(WS), 7)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(RS), 6)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(WS), 7)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(RS), 8)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, WS), 27)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, WS), 28)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, RS), 28)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, RS), 29)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, WS), 18)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, RS), 19)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, WS), 16)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, RS), 17)

        self.assertAlmostEqual(sb.area(), 315.9, 1)
        self.assertEqual(sb.actual_neck_opening_width, 6.7)

    def test_is_piece_methods(self):
        piece = create_sweater_back()
        self.assertTrue(piece.is_sweater_back)
        self.assertFalse(piece.is_vest_back)
        self.assertFalse(piece.is_sweater_front)
        self.assertFalse(piece.is_vest_front)
        self.assertFalse(piece.is_cardigan_sleeved)
        self.assertFalse(piece.is_cardigan_vest)

    def test_sweater_back_corner_case1(self):
        """
        A weird corner case in which we get a triple-dart row in waist and
        bust, but no double-dart rows in either.
        """

        user = UserFactory()
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_length=1, stitches_number=4
        )
        body = BodyFactory(
            armpit_to_high_hip=5.5,
            armpit_to_waist=2,
            armhole_depth=15,
            high_hip_circ=45,
            bust_circ=45,
            waist_circ=43,
        )

        pspec = PatternSpecFactory(
            body=body,
            swatch=swatch,
            torso_length=SDC.HIGH_HIP_LENGTH,
            hip_edging_height=1.5,
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, 79)
        self.assertEqual(sb.waist_hem_height, 1.5)
        self.assertEqual(sb.hem_to_waist, 4)
        self.assertEqual(sb.has_waist_decreases, True)
        self.assertFalse(sb.any_waist_decreases_on_ws)
        self.assertEqual(sb.num_waist_standard_decrease_rows, 0)
        self.assertEqual(sb.num_waist_double_dart_rows, 0)
        self.assertEqual(sb.num_waist_triple_dart_rows, 1)
        self.assertEqual(sb.begin_decreases_height, 3)
        self.assertEqual(sb.pre_marker, 26)
        self.assertEqual(sb.post_marker, 26)
        self.assertEqual(sb.inter_marker, 27)
        self.assertEqual(sb.num_bust_standard_increase_rows, 0)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sb.num_bust_triple_dart_rows, 1)
        self.assertEqual(sb.num_waist_decrease_rows_knitter_instructions, 1)
        self.assertEqual(sb.num_waist_standard_decrease_repetitions, None)
        self.assertEqual(sb.rows_between_waist_standard_decrease_rows, 3)
        # TODO: Change this next one when templates can gracefully deal with this corner case
        self.assertEqual(sb.waist_double_darts, True)
        # TODO: this one too
        self.assertEqual(sb.waist_double_dart_marker, 13)
        self.assertEqual(sb.waist_inter_double_marker, 13)
        self.assertEqual(sb.num_waist_double_dart_decrease_repetitions, None)
        self.assertEqual(sb.num_waist_non_double_dart_decrease_repetitions, None)
        self.assertEqual(
            sb.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(sb.waist_triple_darts, True)
        self.assertEqual(sb.waist_triple_dart_marker, 6)
        self.assertEqual(sb.waist_inter_triple_marker, 7)
        self.assertEqual(sb.num_waist_triple_dart_repetitions, 0)
        self.assertEqual(sb.waist_stitches, 75)

        self.assertEqual(sb.has_bust_increases, True)
        self.assertFalse(sb.any_bust_increases_on_ws)
        self.assertEqual(sb.num_bust_increase_rows_knitter_instructions, 1)
        self.assertEqual(sb.num_bust_standard_increase_rows, 0)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sb.num_bust_triple_dart_rows, 1)
        self.assertEqual(sb.num_bust_standard_increase_repetitions, None)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sb.bust_pre_standard_dart_marker, 25)
        # TODO: fix this when ready to gracefully deal with this corner case
        self.assertEqual(sb.bust_double_darts, True)
        # TODO: fix this when ready to gracefully deal with this corner case
        self.assertEqual(sb.bust_pre_double_dart_marker, 12)
        # TODO: fix this when ready to gracefully deal with this corner case
        self.assertEqual(sb.bust_inter_double_dart_markers, 51)
        self.assertEqual(sb.bust_inter_double_and_standard_dart_markers, 13)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sb.num_bust_non_double_dart_increase_repetitions, None)
        self.assertEqual(
            sb.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(sb.bust_triple_darts, True)
        self.assertEqual(sb.bust_pre_triple_dart_marker, 5)
        self.assertEqual(sb.bust_inter_triple_dart_markers, 65)
        self.assertEqual(sb.bust_inter_double_and_triple_dart_markers, 7)
        self.assertEqual(sb.num_bust_triple_dart_repetitions, 0)
        self.assertEqual(sb.bust_stitches, 79)
        self.assertEqual(sb.hem_to_bust_increase_end, 4.25)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 5.5)
        self.assertEqual(sb.armhole_x, 4)
        self.assertEqual(sb.armhole_y, 2)
        self.assertEqual(sb.armhole_z, 5)
        self.assertEqual(sb.hem_to_neckline_shaping_start, 19.5)
        self.assertEqual(sb.hem_to_neckline_shaping_end, 19.5)
        self.assertEqual(sb.hem_to_shoulders, 20.5)
        self.assertEqual(sb.first_shoulder_bindoff, 7)
        self.assertEqual(sb.second_shoulder_bindoff, 7)
        self.assertEqual(sb.num_shoulder_stitches, 14)
        self.assertEqual(sb.actual_hip, 19.75)
        self.assertEqual(sb.actual_waist, 18.75)
        self.assertEqual(sb.actual_bust, 19.75)
        self.assertEqual(sb.actual_armhole_depth, 15.0)
        self.assertEqual(sb.actual_shoulder_stitch_width, 3.5)
        self.assertAlmostEqual(sb.actual_armhole_circumference, 16.295, 3)
        self.assertEqual(sb.cross_chest_stitches, 57)
        self.assertEqual(sb.actual_cross_chest, 14.25)
        self.assertEqual(sb.actual_neck_opening, 7.25)
        self.assertEqual(sb.hem_to_waist, 4)
        self.assertEqual(sb.actual_hem_to_armhole, 5.5)
        self.assertEqual(sb.actual_waist_to_armhole, 1.5)
        self.assertEqual(sb.actual_hem_to_shoulder, 20.5)
        self.assertEqual(sb.bust_use_standard_markers, True)

        self.assertEqual(sb.waist_hem_height_in_rows, 6)
        self.assertEqual(sb.begin_decreases_height_in_rows, 12)
        self.assertEqual(sb.hem_to_waist_in_rows, 16)
        self.assertEqual(sb.last_decrease_to_waist_in_rows, 4)
        self.assertEqual(sb.hem_to_neckline_in_rows(RS), 79)
        self.assertEqual(sb.hem_to_neckline_in_rows(WS), 78)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(RS), 63)
        self.assertEqual(sb.last_increase_to_neckline_in_rows(WS), 62)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(RS), 67)
        self.assertEqual(sb.last_decrease_to_neckline_in_rows(WS), 66)
        self.assertEqual(sb.hem_to_armhole_in_rows(RS), 23)
        self.assertEqual(sb.hem_to_armhole_in_rows(WS), 22)
        self.assertEqual(sb.hem_to_first_armhole_in_rows, 22)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(RS), 7)
        self.assertEqual(sb.last_increase_to_armhole_in_rows(WS), 6)
        self.assertEqual(sb.last_increase_to_first_armhole_in_rows, 6)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(RS), 11)
        self.assertEqual(sb.last_decrease_to_armhole_in_rows(WS), 10)
        self.assertEqual(sb.last_decrease_to_first_armhole_in_rows, 10)
        self.assertEqual(sb.hem_to_shoulders_in_rows(RS), 83)
        self.assertEqual(sb.hem_to_shoulders_in_rows(WS), 82)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, RS), None)
        self.assertEqual(sb.neckline_to_armhole_in_rows(WS, WS), None)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, WS), 55)
        self.assertEqual(sb.armhole_to_neckline_in_rows(RS, RS), 56)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, WS), 56)
        self.assertEqual(sb.armhole_to_neckline_in_rows(WS, RS), 57)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(RS), 57)
        self.assertEqual(sb.first_armhole_to_neckline_in_rows(WS), 56)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(WS), 13)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(RS), 12)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(WS), 13)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(RS), 14)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, WS), 59)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, WS), 60)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(RS, RS), 60)
        self.assertEqual(sb.armhole_to_shoulders_in_rows(WS, RS), 61)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, WS), 44)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, RS), 45)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, WS), 42)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(RS, RS), 43)

        self.assertAlmostEqual(sb.area(), 315.1, 1)

    def test_bust_heights1(self):
        """
        Testing that the bust-shaping heights work as expected:
        one inch below armpits
        """
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_length=1, stitches_number=4
        )
        sbs = SweaterBackSchematicFactory(
            armpit_height=7 + 2.75,
            bust_width=19.625,
            sweaterschematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        sbs.save()
        sb = SweaterBack.make(
            swatch,
            sbs,
            rounding_directions[SDC.FIT_HOURGLASS_AVERAGE],
            ease_tolerances[SDC.FIT_HOURGLASS_AVERAGE],
        )

        self.assertEqual(sb.hem_to_waist, 7.5)
        self.assertEqual(sb.waist_stitches, 70)
        self.assertEqual(sb.bust_stitches, 80)
        self.assertEqual(sb.num_bust_standard_increase_rows, 0)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 1)
        self.assertEqual(sb.num_bust_triple_dart_rows, 2)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sb.hem_to_bust_increase_end, 8.75)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 9.75)

    def test_bust_heights2(self):
        """
        Testing that the bust-shaping heights work as expected:
        push up to half-inch below armpits
        """
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_length=1, stitches_number=4
        )
        sbs = SweaterBackSchematicFactory(
            armpit_height=7 + 3.25,
            bust_width=21.5,
            sweaterschematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        sbs.save()
        sb = SweaterBack.make(
            swatch,
            sbs,
            rounding_directions[SDC.FIT_HOURGLASS_AVERAGE],
            ease_tolerances[SDC.FIT_HOURGLASS_AVERAGE],
        )

        self.assertEqual(sb.hem_to_waist, 7.5)
        self.assertEqual(sb.waist_stitches, 70)
        self.assertEqual(sb.bust_stitches, 86)
        self.assertEqual(sb.num_bust_standard_increase_rows, 0)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 2)
        self.assertEqual(sb.num_bust_triple_dart_rows, 3)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sb.hem_to_bust_increase_end, 9.75)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 10.25)

    def test_armhole_circ_error(self):
        """
        Testing that the bust-shaping heights work as expected:
        push up to half-inch below armpits
        """
        swatch = SwatchFactory(
            rows_number=6.4, rows_length=1, stitches_length=1, stitches_number=4.24
        )
        sbs = SweaterBackSchematicFactory(
            armpit_height=7 + 3.25,
            bust_width=21.5,
            sweaterschematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        sbs.save()
        sb = SweaterBack.make(
            swatch,
            sbs,
            rounding_directions[SDC.FIT_HOURGLASS_AVERAGE],
            ease_tolerances[SDC.FIT_HOURGLASS_AVERAGE],
        )

        sb.armhole_x = 4
        sb.armhole_y = 2
        sb.armhole_3 = 5
        sb.hem_to_shoulders = 7.75 + sb.hem_to_armhole_shaping_start

        self.assertAlmostEqual(sb._compute_armhole_circumference(), 9.643, 2)

    def test_bust_heights3(self):
        """
        Testing that the bust-shaping heights work as expected:
        push up to armpits
        """
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_length=1, stitches_number=4
        )
        sbs = SweaterBackSchematicFactory(
            armpit_height=7 + 2.75,
            bust_width=20.5,
            sweaterschematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        sbs.save()
        sb = SweaterBack.make(
            swatch,
            sbs,
            rounding_directions[SDC.FIT_HOURGLASS_AVERAGE],
            ease_tolerances[SDC.FIT_HOURGLASS_AVERAGE],
        )

        self.assertEqual(sb.hem_to_waist, 7.5)
        self.assertEqual(sb.waist_stitches, 70)
        self.assertEqual(sb.bust_stitches, 82)
        self.assertEqual(sb.num_bust_standard_increase_rows, 2)
        self.assertEqual(sb.num_bust_double_dart_increase_rows, 2)
        self.assertEqual(sb.num_bust_triple_dart_rows, 1)
        self.assertEqual(sb.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sb.hem_to_bust_increase_end, 9.75)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 9.75)

    def test_stitches(self):
        sb = create_sweater_back()

        self.assertEqual(sb.allover_stitch, StitchFactory(name="Stockinette"))
        self.assertIsNone(sb.caston_repeats(), None)

    def test_repeats(self):

        # For comparison
        pspec = PatternSpecFactory()
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, 98)

        # Note: Cabled check is 1 mod 4
        # one-by-one rib does not use repeats
        pspec = PatternSpecFactory(
            back_allover_stitch=StitchFactory(name="Cabled Check Stitch"),
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons % 4, 1)

        repeats_swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=3, additional_stitches=1
        )
        pspec = PatternSpecFactory(
            back_allover_stitch=StitchFactory(name="Stockinette"), swatch=repeats_swatch
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons % 3, 1)

        # Open mesh lace is 0 mod 3
        pspec = PatternSpecFactory(
            back_allover_stitch=StitchFactory(name="Stockinette"),
            hip_edging_stitch=StitchFactory(name="Open Mesh Lace"),
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons % 3, 0)

    def test_half_hourglass(self):

        # For comparison
        pspec = PatternSpecFactory()
        sb1 = make_sweaterback_from_pspec(pspec)

        pspec = PatternSpecFactory(silhouette=SDC.SILHOUETTE_HALF_HOURGLASS)
        sb2 = make_sweaterback_from_pspec(pspec)

        self.assertEqual(sb1.cast_ons, sb2.cast_ons)
        self.assertEqual(sb1.waist_stitches, sb2.waist_stitches)
        self.assertEqual(sb1.bust_stitches, sb2.bust_stitches)

    def test_cables(self):

        #
        # Control/comparison
        #
        pspec = PatternSpecFactory()
        sb_control = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb_control.cast_ons, 98)
        self.assertEqual(sb_control.inter_marker, 32)
        self.assertEqual(sb_control.waist_inter_double_marker, None)
        self.assertEqual(sb_control.waist_stitches, 88)
        self.assertEqual(sb_control.bust_inter_double_dart_markers, None)
        self.assertEqual(sb_control.bust_inter_standard_dart_markers, 32)
        self.assertEqual(sb_control.bust_inter_triple_dart_markers, None)
        self.assertEqual(sb_control.bust_stitches, 100)
        self.assertEqual(sb_control._bust_stitches_internal_use, 100)
        self.assertAlmostEqual(sb_control.area(), 421.6, 1)
        self.assertEqual(sb_control.actual_neck_opening_width, 7.2)
        self.assertEqual(sb_control.actual_neck_opening, 7.2)
        self.assertEqual(sb_control.actual_hip, 19.600000000000001)
        self.assertEqual(sb_control.actual_waist, 17.600000000000001)
        self.assertEqual(sb_control.actual_bust, 20)
        self.assertEqual(sb_control.actual_cross_chest, 14)
        self.assertEqual(sb_control.actual_neck_opening, 7.2000000000000002)
        self.assertEqual(sb_control.neckline.stitches_across_neckline(), 36)
        self.assertEqual(sb_control.num_shoulder_stitches, 17)
        self.assertEqual(sb_control.first_shoulder_bindoff, 9)
        #
        # Positive extra stitches
        #
        pspec = PatternSpecFactory(
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            back_cable_extra_stitches=5,
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, 103)
        self.assertEqual(sb.inter_marker, 37)
        self.assertEqual(sb.waist_inter_double_marker, None)
        self.assertEqual(sb.waist_stitches, 93)
        self.assertEqual(sb.bust_inter_double_dart_markers, None)
        self.assertEqual(sb.bust_inter_standard_dart_markers, 37)
        self.assertEqual(sb.bust_inter_triple_dart_markers, None)
        self.assertEqual(sb.bust_stitches, 105)
        self.assertEqual(sb._bust_stitches_internal_use, 105)

        extra_area = (
            5
            * sb.hem_to_neckline_shaping_start
            / sb.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        self.assertLessEqual(abs(sb.area() - (sb_control.area() + extra_area)), 1)

        # Should not change
        self.assertEqual(sb.actual_hip, sb_control.actual_hip)
        self.assertEqual(sb.actual_waist, sb_control.actual_waist)
        self.assertEqual(sb.actual_bust, sb_control.actual_bust)
        self.assertEqual(sb.actual_cross_chest, sb_control.actual_cross_chest)
        self.assertEqual(sb.actual_neck_opening, sb_control.actual_neck_opening)
        self.assertEqual(sb.armhole_x, sb_control.armhole_x)
        self.assertEqual(sb.armhole_y, sb_control.armhole_y)
        self.assertEqual(sb.armhole_z, sb_control.armhole_z)
        self.assertEqual(sb.first_shoulder_bindoff, sb_control.first_shoulder_bindoff)
        self.assertEqual(sb.num_shoulder_stitches, sb_control.num_shoulder_stitches)
        self.assertEqual(
            sb.actual_neck_opening_width, sb_control.actual_neck_opening_width
        )

        #
        # zero extra stitches
        #
        pspec = PatternSpecFactory(
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            back_cable_extra_stitches=0,
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, sb_control.cast_ons)
        self.assertEqual(sb.inter_marker, sb_control.inter_marker)
        self.assertEqual(
            sb.waist_inter_double_marker, sb_control.waist_inter_double_marker
        )
        self.assertEqual(sb.waist_stitches, sb_control.waist_stitches)
        self.assertEqual(
            sb.bust_inter_double_dart_markers, sb_control.bust_inter_double_dart_markers
        )
        self.assertEqual(
            sb.bust_inter_standard_dart_markers,
            sb_control.bust_inter_standard_dart_markers,
        )
        self.assertEqual(
            sb.bust_inter_triple_dart_markers, sb_control.bust_inter_triple_dart_markers
        )
        self.assertEqual(sb.bust_stitches, sb_control.bust_stitches)
        self.assertEqual(
            sb._bust_stitches_internal_use, sb_control._bust_stitches_internal_use
        )
        self.assertEqual(sb.area(), sb_control.area())
        self.assertEqual(
            sb.neckline.stitches_across_neckline(),
            sb_control.neckline.stitches_across_neckline(),
        )
        self.assertEqual(
            sb.actual_neck_opening_width, sb_control.actual_neck_opening_width
        )
        self.assertEqual(sb.actual_hip, sb_control.actual_hip)
        self.assertEqual(sb.actual_waist, sb_control.actual_waist)
        self.assertEqual(sb.actual_bust, sb_control.actual_bust)
        self.assertEqual(sb.actual_cross_chest, sb_control.actual_cross_chest)
        self.assertEqual(sb.actual_neck_opening, sb_control.actual_neck_opening)
        self.assertEqual(sb.armhole_x, sb_control.armhole_x)
        self.assertEqual(sb.armhole_y, sb_control.armhole_y)
        self.assertEqual(sb.armhole_z, sb_control.armhole_z)
        self.assertEqual(sb.first_shoulder_bindoff, sb_control.first_shoulder_bindoff)
        self.assertEqual(sb.num_shoulder_stitches, sb_control.num_shoulder_stitches)

        #
        # negative extra stitches
        #
        pspec = PatternSpecFactory(
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            back_cable_extra_stitches=-5,
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, 93)
        self.assertEqual(sb.inter_marker, 27)
        self.assertEqual(sb.waist_inter_double_marker, None)
        self.assertEqual(sb.waist_stitches, 83)
        self.assertEqual(sb.bust_inter_double_dart_markers, None)
        self.assertEqual(sb.bust_inter_standard_dart_markers, 27)
        self.assertEqual(sb.bust_inter_triple_dart_markers, None)
        self.assertEqual(sb.bust_stitches, 95)
        self.assertEqual(sb._bust_stitches_internal_use, 95)

        missing_area = (
            5
            * sb.hem_to_neckline_shaping_start
            / sb.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        self.assertLessEqual(abs(sb.area() - (sb_control.area() - missing_area)), 1)
        self.assertEqual(sb.neckline.stitches_across_neckline(), 31)

        # Should not change
        self.assertEqual(
            sb.actual_neck_opening_width, sb_control.actual_neck_opening_width
        )
        self.assertEqual(sb.actual_hip, sb_control.actual_hip)
        self.assertEqual(sb.actual_waist, sb_control.actual_waist)
        self.assertEqual(sb.actual_bust, sb_control.actual_bust)
        self.assertEqual(sb.actual_cross_chest, sb_control.actual_cross_chest)
        self.assertEqual(sb.actual_neck_opening, sb_control.actual_neck_opening)
        self.assertEqual(sb.armhole_x, sb_control.armhole_x)
        self.assertEqual(sb.armhole_y, sb_control.armhole_y)
        self.assertEqual(sb.armhole_z, sb_control.armhole_z)
        self.assertEqual(sb.first_shoulder_bindoff, sb_control.first_shoulder_bindoff)
        self.assertEqual(sb.num_shoulder_stitches, sb_control.num_shoulder_stitches)

    def test_straight_silhouette(self):
        pspec = PatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterback_from_pspec(pspec)

    def test_aline_silhouette(self):
        pspec = PatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterback_from_pspec(pspec)

    def test_tapered_silhouette(self):
        pspec = PatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterback_from_pspec(pspec)

    def test_drop_shoulder(self):
        pspec = PatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        sb = make_sweaterback_from_pspec(pspec)

        self.assertEqual(pspec.swatch.get_gauge().stitches, 5)

        self.assertEqual(sb.armhole_x, 3)
        self.assertEqual(sb.armhole_y, 0)
        self.assertEqual(sb.armhole_z, 0)
        self.assertAlmostEqual(sb.actual_armhole_circumference, 9.957, 2)
        self.assertEqual(sb.hem_to_armhole_shaping_start, 14.5)
        self.assertEqual(sb.hem_to_shoulders, 24)

        self.assertEqual(sb.armhole_n, 3)
        self.assertEqual(sb.area(), 520.2)

        self.assertEqual(sb.rows_in_armhole_shaping_pullover(WS), 2)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(RS), 2)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(WS), 1)
        self.assertEqual(sb.rows_in_armhole_shaping_cardigan(RS), 1)

    def test_armhole_shaping(self):

        swatch = SwatchFactory(
            stitches_length=1, stitches_number=10, rows_length=1, rows_number=4
        )
        pspec = PatternSpecFactory(
            swatch=swatch, construction=SDC.CONSTRUCTION_SET_IN_SLEEVE
        )
        sb = make_sweaterback_from_pspec(pspec)

        # If the height of the armhole is high, we should see about 1 inch of armhole_n (10 stitches) allocated to x,
        # y set to two stitches, and the rest to z

        xyz = sb._calculate_armhole_shaping(40, 100)
        self.assertEqual(xyz, (10, 2, 28))

        # This should be the case so long as the shaping (2 rows for all of x, 2 rows for all of y,
        # 2 two stitches per z) is less than 35% of the armcap height. In this case, that turns into
        # (2 + 2 + 56) rows < .35 * height, or height > 42.85 inches

        xyz = sb._calculate_armhole_shaping(40, 43)
        self.assertEqual(xyz, (10, 2, 28))

        # Below that, though, we should see stitches removed from z and moved to y, but x unchanged-- at first,
        xyz = sb._calculate_armhole_shaping(40, 42.7)
        self.assertEqual(xyz, (10, 3, 27))

        xyz = sb._calculate_armhole_shaping(40, 41)
        self.assertEqual(xyz, (10, 4, 26))

        xyz = sb._calculate_armhole_shaping(40, 39)
        self.assertEqual(xyz, (10, 5, 25))

        xyz = sb._calculate_armhole_shaping(40, 33)
        self.assertEqual(xyz, (10, 9, 21))

        # Eventually, we should see x increase
        xyz = sb._calculate_armhole_shaping(40, 32)
        self.assertEqual(xyz, (11, 9, 20))

        # We should see x and y increase together and stitches disappear from z
        xyz = sb._calculate_armhole_shaping(40, 31)
        self.assertEqual(xyz, (11, 10, 19))

        xyz = sb._calculate_armhole_shaping(40, 30)
        self.assertEqual(xyz, (12, 10, 18))

        xyz = sb._calculate_armhole_shaping(40, 29)
        self.assertEqual(xyz, (12, 10, 18))

        xyz = sb._calculate_armhole_shaping(40, 25)
        self.assertEqual(xyz, (13, 12, 15))

        xyz = sb._calculate_armhole_shaping(40, 20)
        self.assertEqual(xyz, (15, 14, 11))

        xyz = sb._calculate_armhole_shaping(40, 15)
        self.assertEqual(xyz, (17, 15, 8))

        xyz = sb._calculate_armhole_shaping(40, 10)
        self.assertEqual(xyz, (19, 17, 4))

        xyz = sb._calculate_armhole_shaping(40, 9)
        self.assertEqual(xyz, (19, 17, 4))

        xyz = sb._calculate_armhole_shaping(40, 8)
        self.assertEqual(xyz, (19, 18, 3))

        xyz = sb._calculate_armhole_shaping(40, 7)
        self.assertEqual(xyz, (20, 18, 2))

        xyz = sb._calculate_armhole_shaping(40, 6)
        self.assertEqual(xyz, (20, 18, 2))

        xyz = sb._calculate_armhole_shaping(40, 5)
        self.assertEqual(xyz, (20, 19, 1))

        # And now things start to get really interesting. The lowest hieght we can handle is one where
        # 35% of the height is enough for 4 rows: 2 for all of X, none for y (which will be set to zero)
        # and 2 rows for a z-value of 1. So 4 rows = 35% of height, or height = 2.85714. And we will go through
        # some denerate cases before then.

        # The case above should remain stable so long as we have enough height for 6 rows to fit in 35%,
        # or height > 1.5 inches / .35 = 4.2857
        xyz = sb._calculate_armhole_shaping(40, 4.29)
        self.assertEqual(xyz, (20, 19, 1))

        # Then y should disappear entirely
        xyz = sb._calculate_armhole_shaping(40, 4.28)
        self.assertEqual(xyz, (39, 0, 1))

        xyz = sb._calculate_armhole_shaping(40, 2.9)
        self.assertEqual(xyz, (39, 0, 1))

        # Lower than that, and we should fail to find armhole shaping:
        with self.assertRaises(ArmholeShapingError):
            sb._calculate_armhole_shaping(40, 2.8)

        # Now let's test what happens when the number of armhole stitches starts to shrink
        xyz = sb._calculate_armhole_shaping(20, 100)
        self.assertEqual(xyz, (10, 2, 8))

        xyz = sb._calculate_armhole_shaping(15, 100)
        self.assertEqual(xyz, (10, 2, 3))

        xyz = sb._calculate_armhole_shaping(14, 100)
        self.assertEqual(xyz, (10, 2, 2))

        xyz = sb._calculate_armhole_shaping(13, 100)
        self.assertEqual(xyz, (10, 2, 1))

        xyz = sb._calculate_armhole_shaping(12, 100)
        self.assertEqual(xyz, (10, 0, 2))

        xyz = sb._calculate_armhole_shaping(11, 100)
        self.assertEqual(xyz, (10, 0, 1))

        # We need at least 1 inch of stitches + 1 stitch = 11 stitches, so this should throw an error
        with self.assertRaises(ArmholeShapingError):
            xyz = sb._calculate_armhole_shaping(10, 100)

        with self.assertRaises(ArmholeShapingError):
            xyz = sb._calculate_armhole_shaping(1, 100)

        with self.assertRaises(ArmholeShapingError):
            xyz = sb._calculate_armhole_shaping(0, 100)

        with self.assertRaises(ArmholeShapingError):
            xyz = sb._calculate_armhole_shaping(-1, 100)

    def test_arm_to_shoulder_count_bug(self):
        swatch = SwatchFactory(
            stitches_length=4, stitches_number=15, rows_length=4, rows_number=23
        )

        sb = create_sweater_back(
            hem_to_armhole_shaping_start=15.5,
            armhole_x=3,
            armhole_y=2,
            armhole_z=2,
            hem_to_shoulders=23.0,
        )
        sb.neckline.bindoff_stitches = 27
        sb.neckline.neckline_depth = 1.04347826087
        sb.neckline.pickup_stitches = 38
        sb.neckline.stitches_before_initial_bindoffs = 17
        sb.neckline.save()
        # This needs to be separate, for some reason
        sb.swatch = swatch
        sb.schematic.sweaterschematic.individual_garment_parameters.pattern_spec.swatch = (
            swatch
        )
        sb.save()

        self.assertEqual(sb.hem_to_armhole_in_rows(WS), 90)
        self.assertEqual(sb.rows_in_armhole_shaping_pullover(WS), 7)
        self.assertEqual(sb.last_armhole_to_neckline_in_rows(WS, WS), 30)
        self.assertEqual(sb.hem_to_shoulders_in_rows(RS), 133)
        self.assertEqual(sb.hem_to_shoulders_in_rows(WS), 132)
        self.assertEqual(sb.last_armhole_to_shoulders_in_rows(WS, RS), 36)
        self.assertEqual(sb.last_armhole_to_shoulders_in_rows(WS, WS), 35)

        sb.delete()

    def drop_shoulder_bug_1(self):
        swatch = SwatchFactory(
            stitches_number=26.0, stitches_length=4.0, rows_number=50, rows_length=5.25
        )
        pspec = PatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW,
            torso_length=SDC.MED_HIP_LENGTH,
            neckline_width=SDC.NECK_OTHERWIDTH,
            neckline_other_val_percentage=60,
            neckline_depth=3.5,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_TIGHT,
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            swatch=swatch,
        )
        sb = make_sweaterback_from_pspec(pspec)
        self.assertEqual(sb.cast_ons, 147)
        self.assertEqual(sb.armhole_x, 4)
        self.assertEqual(sb.armhole_y, 0)
        self.assertEqual(sb.armhole_z, 0)
        self.assertEqual(sb.cross_chest_stitches, 147 - 8)


class VestBackTest(django.test.TestCase):

    def test_rows_in_armhole(self):

        pspec = PatternSpecFactory(garment_type=SDC.PULLOVER_VEST)
        vb = make_vestback_from_pspec(pspec)
        self.assertEqual(vb.armhole_n, 15)
        self.assertEqual(vb.armhole_x, 5)
        self.assertEqual(vb.armhole_y, 3)
        self.assertEqual(vb.armhole_z, 7)
        self.assertEqual(vb.rows_in_armhole_shaping_pullover(RS), 18)
        self.assertEqual(vb.rows_in_armhole_shaping_pullover(WS), 19)

        vb.armhole_y = 0
        self.assertEqual(vb.rows_in_armhole_shaping_pullover(RS), 16)
        self.assertEqual(vb.rows_in_armhole_shaping_pullover(WS), 15)


class AlineBackTest(django.test.TestCase):

    def test_shaping_rate(self):

        # Sanity check:
        # When hip is 51 inches, we're fine with 3 rows between shaping rows
        body = BodyFactory(
            med_hip_circ=51,
            bust_circ=41,
        )
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            rows_length=1,
            rows_number=7,
        )
        pspec = PatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            swatch=swatch,
        )
        vb = make_vestback_from_pspec(pspec)
        self.assertEqual(vb.rows_between_waist_standard_decrease_rows, 3)
        self.assertEqual(vb.cast_ons, 143)
        self.assertEqual(vb.num_waist_standard_decrease_rows, 22)
        self.assertFalse(vb.any_waist_decreases_on_ws)
        self.assertFalse(vb.any_bust_increases_on_ws)

        # When hip is 52 inches, we should go down to 2 rows between shaping rows
        body = BodyFactory(
            med_hip_circ=52,
            bust_circ=41,
        )
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            rows_length=1,
            rows_number=7,
        )
        pspec = PatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            swatch=swatch,
        )
        vb = make_vestback_from_pspec(pspec)
        self.assertEqual(vb.rows_between_waist_standard_decrease_rows, 2)
        self.assertEqual(vb.cast_ons, 145)
        self.assertEqual(vb.num_waist_standard_decrease_rows, 23)
        self.assertTrue(vb.any_waist_decreases_on_ws)
        self.assertFalse(vb.any_bust_increases_on_ws)


class GradedSweaterBackTests(django.test.TestCase):

    def test_make(self):
        gpsc = GradedSweaterSchematicFactory()
        back_piece_schematic = gpsc.sweater_back_schematics.order_by(
            "GradedSweaterBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit
        gsb = GradedSweaterBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        # print(gsb.__dict__)
        # for k,v in gsb.__dict__.items():
        #     print("    %s = %s" % (k,v))
        # subfactory_kwargs = "bindoff_stitches=%s, stitches_before_initial_bindoffs=%s, neckline_depth=%s, pickup_stitches=%s, row_gauge=%s, stitch_gauge=%s" % (gsb.neckline.bindoff_stitches,
        #                                                                                                                         gsb.neckline.stitches_before_initial_bindoffs,
        #                                                                                                                         gsb.neckline.neckline_depth,
        #                                                                                                                                                         gsb.neckline.pickup_stitches,
        #                                                                                                                                                         gsb.neckline.row_gauge,
        #                                                                                                                                                         gsb.neckline.stitch_gauge,
        #                                                                                                                                                         )
        # print("    neckline = SubFactory(BackNecklineFactory, %s)" % subfactory_kwargs)
        # print("    graded_pattern_pieces = SubFactory(GradedSweaterPatternPiecesFactory)")
        # print("    schematic = SubFactory(GradedSweaterBackSchematicFactory, construction_schematic=SelfAttribute('..graded_pattern_pieces.schematic'))")
        # print(gsb.neckline.__dict__)

    # def test_factory(self):
    #     GradedSweaterBackFactory()


class GradedVestBackTests(django.test.TestCase):

    def test_make(self):
        gpsc = GradedSweaterSchematicFactory.from_pspec_kwargs(
            garment_type=SDC.PULLOVER_VEST,
            sleeve_length=None,
            sleeve_shape=None,
            bell_type=None,
            sleeve_edging_stitch=None,
            sleeve_edging_height=None,
            armhole_edging_stitch=StitchFactory(),
            armhole_edging_height=2,
        )
        back_piece_schematic = gpsc.vest_back_schematics.order_by(
            "GradedVestBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit
        gsb = GradedVestBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        # print(gsb.__dict__)
        # for k,v in gsb.__dict__.items():
        #     print("    %s = %s" % (k,v))
        # subfactory_kwargs = "bindoff_stitches=%s, stitches_before_initial_bindoffs=%s, neckline_depth=%s, pickup_stitches=%s, row_gauge=%s, stitch_gauge=%s" % (gsb.neckline.bindoff_stitches,
        #                                                                                                                         gsb.neckline.stitches_before_initial_bindoffs,
        #                                                                                                                         gsb.neckline.neckline_depth,
        #                                                                                                                                                         gsb.neckline.pickup_stitches,
        #                                                                                                                                                         gsb.neckline.row_gauge,
        #                                                                                                                                                         gsb.neckline.stitch_gauge,
        #                                                                                                                                                         )
        # print("    neckline = SubFactory(BackNecklineFactory, %s)" % subfactory_kwargs)
        # print("    graded_pattern_pieces = SubFactory(GradedSweaterPatternPiecesFactory)")
        # print("    schematic = SubFactory(GradedVestBackSchematicFactory, construction_schematic=SelfAttribute('..graded_pattern_pieces.schematic'))")
        # print(gsb.neckline.__dict__)

    #
    # def test_factory(self):
    #     GradedVestBackFactory()
