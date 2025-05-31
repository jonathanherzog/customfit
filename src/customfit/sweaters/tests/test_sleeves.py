import itertools

import django.test
from django.core.exceptions import ValidationError

from customfit.bodies.factories import BodyFactory, SimpleBodyFactory, get_csv_body
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ..factories import (
    GradedSweaterPatternPiecesFactory,
    GradedSweaterSchematicFactory,
    SweaterPatternSpecFactory,
    create_csv_combo,
    create_sleeve,
    make_sleeve_from_ips,
    make_sleeve_from_pspec,
    make_sweaterback_from_pspec,
)
from ..helpers import sweater_design_choices as SDC
from ..models import (
    GradedSleeve,
    GradedSweaterBack,
    SweaterIndividualGarmentParameters,
    SweaterSchematic,
)

# helper functions


def _compare_sleevecap_to_backpiece(sl, backpiece, msg):
    armhole_depth = backpiece.hem_to_shoulders - backpiece.hem_to_armhole_shaping_start
    cap_height = sl.actual_armcap_heights
    difference = armhole_depth - cap_height
    new_msg = "%s - %s = %s, %s" % (cap_height, armhole_depth, difference, msg)
    assert difference >= 0.25, new_msg
    assert difference <= 3.1, new_msg


class SleeveTest(django.test.TestCase):

    maxDiff = None

    def setUp(self):

        StitchFactory(
            name="Folded hem",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        )

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

        StitchFactory(
            name="Other Stitch",
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=False,
        )

    def test_sleeve_cable(self):

        # Control/comparison
        pspec = SweaterPatternSpecFactory()
        sl_control = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl_control.cast_ons, 45)
        self.assertEqual(sl_control.bicep_stitches, 67)
        self.assertEqual(sl_control.armscye_c, 13)
        self.assertEqual(sl_control.actual_wrist, 9)
        self.assertEqual(sl_control.actual_bicep, 13.4)
        self.assertAlmostEqual(sl_control.area(), 501.485, 1)
        self.assertEqual(sl_control.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl_control.post_bead_game_stitch_count, 21)

        #
        #  Positive extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=5,
            sleeve_cable_extra_stitches_caston_only=False,
        )
        sl = make_sleeve_from_pspec(pspec)

        # should change from control
        self.assertEqual(sl.cast_ons, 50)
        self.assertEqual(sl.bicep_stitches, 72)
        self.assertEqual(sl.armscye_c, 18)
        self.assertEqual(sl.pre_bead_game_stitch_count, 56)
        self.assertEqual(sl.post_bead_game_stitch_count, 26)
        extra_area = 5 / pspec.swatch.get_gauge().stitches * sl.actual_total_height
        extra_area *= 2  # double it to get area for both sleeves
        # Can't use assertAlmostEqual for the next bit-- they differ by more than 0.1
        self.assertLess(abs(sl_control.area() + extra_area - sl.area()), 0.5)

        # should not change from control
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)

        #
        # zero extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=0,
            sleeve_cable_extra_stitches_caston_only=False,
        )
        sl = make_sleeve_from_pspec(pspec)

        # Everything should match control
        self.assertEqual(sl.cast_ons, sl_control.cast_ons)
        self.assertEqual(sl.bicep_stitches, sl_control.bicep_stitches)
        self.assertEqual(sl.armscye_c, sl_control.armscye_c)
        self.assertEqual(sl.area(), sl_control.area())
        self.assertEqual(
            sl.pre_bead_game_stitch_count, sl_control.pre_bead_game_stitch_count
        )
        self.assertEqual(
            sl.post_bead_game_stitch_count, sl_control.post_bead_game_stitch_count
        )
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)

        #
        # negative extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=-5,
            sleeve_cable_extra_stitches_caston_only=False,
        )
        sl = make_sleeve_from_pspec(pspec)

        # Should change from control
        self.assertEqual(sl.cast_ons, 40)
        self.assertEqual(sl.bicep_stitches, 62)
        self.assertEqual(sl.armscye_c, 8)
        self.assertEqual(sl.pre_bead_game_stitch_count, 46)
        self.assertEqual(sl.post_bead_game_stitch_count, 16)

        extra_area = 5 / pspec.swatch.get_gauge().stitches * sl.actual_total_height
        extra_area *= 2  # double it to get area for both sleeves
        # Can't use assertAlmostEqual for the next bit-- they differ by more than 0.1
        self.assertLess(abs(sl_control.area() - extra_area - sl.area()), 0.5)

        # should not change from control
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)

        # Too many negative extra stitches
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=-20,
            sleeve_cable_extra_stitches_caston_only=False,
        )
        with self.assertRaises(AssertionError):
            make_sleeve_from_pspec(pspec)

    def test_sleeve_cable_caston_only(self):

        # Control/comparison
        pspec = SweaterPatternSpecFactory()
        sl_control = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl_control.cast_ons, 45)
        self.assertEqual(sl_control.bicep_stitches, 67)
        self.assertEqual(sl_control.armscye_c, 13)
        self.assertEqual(sl_control.actual_wrist, 9)
        self.assertEqual(sl_control.actual_bicep, 13.4)
        self.assertAlmostEqual(sl_control.area(), 501.485, 1)
        self.assertEqual(sl_control.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl_control.post_bead_game_stitch_count, 21)

        #
        #  Positive extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=5,
            sleeve_cable_extra_stitches_caston_only=True,
        )
        sl = make_sleeve_from_pspec(pspec)

        # should change from control
        self.assertEqual(sl.cast_ons, 50)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.armscye_c, 13)
        self.assertEqual(sl.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl.post_bead_game_stitch_count, 21)
        # caston-only stitches do not affect the area of a piece
        self.assertEqual(sl_control.area(), sl.area())

        # should not change from control
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)

        #
        # zero extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=0,
            sleeve_cable_extra_stitches_caston_only=True,
        )
        sl = make_sleeve_from_pspec(pspec)

        # Everything should match control
        self.assertEqual(sl.cast_ons, sl_control.cast_ons)
        self.assertEqual(sl.bicep_stitches, sl_control.bicep_stitches)
        self.assertEqual(sl.armscye_c, sl_control.armscye_c)
        self.assertEqual(sl.area(), sl_control.area())
        self.assertEqual(
            sl.pre_bead_game_stitch_count, sl_control.pre_bead_game_stitch_count
        )
        self.assertEqual(
            sl.post_bead_game_stitch_count, sl_control.post_bead_game_stitch_count
        )
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)

        #
        # negative extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=-5,
            sleeve_cable_extra_stitches_caston_only=True,
        )
        sl = make_sleeve_from_pspec(pspec)

        # Should change from control
        self.assertEqual(sl.cast_ons, 40)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.armscye_c, 13)
        self.assertEqual(sl.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl.post_bead_game_stitch_count, 21)
        # caston-only stitches do not affect the area of a piece
        self.assertEqual(sl_control.area(), sl.area())

        # should not change from control
        self.assertEqual(
            sl.num_sleeve_increase_rows, sl_control.num_sleeve_increase_rows
        )
        self.assertEqual(
            sl.inter_sleeve_increase_rows, sl_control.inter_sleeve_increase_rows
        )
        self.assertEqual(
            sl.num_sleeve_compound_increase_rows,
            sl_control.num_sleeve_compound_increase_rows,
        )
        self.assertEqual(
            sl.rows_after_compound_shaping_rows,
            sl_control.rows_after_compound_shaping_rows,
        )
        self.assertEqual(sl.armscye_x, sl_control.armscye_x)
        self.assertEqual(sl.armscye_y, sl_control.armscye_y)
        self.assertEqual(sl.six_count_beads, sl_control.six_count_beads)
        self.assertEqual(sl.four_count_beads, sl_control.four_count_beads)
        self.assertEqual(sl.two_count_beads, sl_control.two_count_beads)
        self.assertEqual(sl.one_count_beads, sl_control.one_count_beads)
        self.assertEqual(sl.armscye_d, sl_control.armscye_d)
        self.assertEqual(sl.actual_wrist_to_cap, sl_control.actual_wrist_to_cap)
        self.assertEqual(sl.actual_armcap_heights, sl_control.actual_armcap_heights)
        self.assertEqual(sl.actual_wrist, sl_control.actual_wrist)
        self.assertEqual(sl.actual_bicep, sl_control.actual_bicep)

        # Too many negative extra stitches
        pspec = SweaterPatternSpecFactory(
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=-50,
            sleeve_cable_extra_stitches_caston_only=True,
        )
        with self.assertRaises(AssertionError):
            make_sleeve_from_pspec(pspec)

    def test_sleeve_regression_tapered(self):
        sl = create_sleeve()
        self.assertEqual(sl.cast_ons, 45)
        self.assertEqual(sl.inter_sleeve_increase_rows, 9)
        self.assertEqual(sl.num_sleeve_increase_repetitions, 10)
        self.assertEqual(sl.num_sleeve_increase_rows, 11)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.armscye_x, 5)
        self.assertEqual(sl.armscye_y, 3)
        self.assertEqual(sl.six_count_beads, 1)
        self.assertEqual(sl.four_count_beads, 1)
        self.assertEqual(sl.two_count_beads, 13)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.armscye_d, 2)
        self.assertEqual(sl.armscye_c, 13)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 17.5)
        self.assertEqual(sl.actual_wrist, 9)
        self.assertEqual(sl.actual_bicep, 13.4)
        self.assertEqual(sl.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl.post_bead_game_stitch_count, 21)
        self.assertAlmostEqual(sl.actual_armcap_heights, 6.428, places=2)
        self.assertAlmostEqual(sl.actual_total_height, 23.928, places=2)

        self.assertEqual(sl.wrist_hem_height_in_rows, 4)
        self.assertEqual(sl.last_shaping_height_in_rows, 107)
        self.assertEqual(sl.actual_wrist_to_cap_in_rows, 122)

        self.assertFalse(sl.is_straight)

        self.assertEqual(sl.last_shaping_to_cap_in_rows, 16)

        self.assertEqual(sl.inter_sleeve_increase_rows_plus_one, 10)
        self.assertFalse(sl.shaping_row_on_ws)
        self.assertAlmostEqual(sl.first_shaping_height, 1.0, 3)
        self.assertEqual(sl.first_shaping_height_in_rows, 7)

        self.assertAlmostEqual(sl.area(), 501.485, 1)

    def test_sleeve_regression_straight(self):
        pspec = SweaterPatternSpecFactory(sleeve_shape=SDC.SLEEVE_STRAIGHT)
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons, 67)
        self.assertEqual(sl.inter_sleeve_increase_rows, None)
        self.assertEqual(sl.num_sleeve_increase_repetitions, None)
        self.assertEqual(sl.num_sleeve_increase_rows, None)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.armscye_x, 5)
        self.assertEqual(sl.armscye_y, 3)
        self.assertEqual(sl.six_count_beads, 1)
        self.assertEqual(sl.four_count_beads, 1)
        self.assertEqual(sl.two_count_beads, 13)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.pre_bead_game_stitch_count, 51)
        self.assertEqual(sl.post_bead_game_stitch_count, 21)
        self.assertEqual(sl.armscye_d, 2)
        self.assertEqual(sl.armscye_c, 13)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 17.5)
        self.assertAlmostEqual(sl.actual_wrist, 13.4)
        self.assertAlmostEqual(sl.actual_bicep, 13.4)
        self.assertAlmostEqual(sl.actual_armcap_heights, 6.428, places=2)
        self.assertAlmostEqual(sl.actual_total_height, 23.928, places=2)

        self.assertEqual(sl.wrist_hem_height_in_rows, 4)

        self.assertIsNone(sl.last_shaping_height_in_rows)
        self.assertIsNone(sl.last_shaping_to_cap_in_rows)

        self.assertAlmostEqual(sl.area(), 571.857, 1)
        self.assertIsNone(sl.inter_sleeve_increase_rows_plus_one)
        self.assertIsNone(sl.shaping_row_on_ws)
        self.assertEqual(sl.first_shaping_height, None)
        self.assertEqual(sl.first_shaping_height_in_rows, None)

    def test_sleeve_regression_bell(self):
        pspec = SweaterPatternSpecFactory(
            sleeve_shape=SDC.SLEEVE_BELL, bell_type=SDC.BELL_MODERATE
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons, 80)
        self.assertEqual(sl.inter_sleeve_increase_rows, 19)
        self.assertEqual(sl.num_sleeve_increase_repetitions, 5)
        self.assertEqual(sl.num_sleeve_increase_rows, 6)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 68)
        self.assertEqual(sl.armscye_x, 5)
        self.assertEqual(sl.armscye_y, 3)
        self.assertEqual(sl.six_count_beads, 1)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.two_count_beads, 15)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.pre_bead_game_stitch_count, 52)
        self.assertEqual(sl.post_bead_game_stitch_count, 20)
        self.assertEqual(sl.armscye_d, 2)
        self.assertEqual(sl.armscye_c, 12)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 17.5)
        self.assertEqual(sl.actual_wrist, 16)
        self.assertAlmostEqual(sl.actual_bicep, 13.6)
        self.assertAlmostEqual(sl.actual_armcap_heights, 6.428, places=2)
        self.assertAlmostEqual(sl.actual_total_height, 23.928, places=2)

        self.assertEqual(sl.wrist_hem_height_in_rows, 4)
        self.assertEqual(sl.actual_wrist_to_cap_in_rows, 122)

        self.assertFalse(sl.is_straight)
        self.assertEqual(sl.last_shaping_height_in_rows, 107)
        self.assertEqual(sl.last_shaping_to_cap_in_rows, 16)

        self.assertEqual(sl.inter_sleeve_increase_rows_plus_one, 20)
        self.assertFalse(sl.shaping_row_on_ws)

        self.assertAlmostEqual(sl.first_shaping_height, 1.0, 3)
        self.assertEqual(sl.first_shaping_height_in_rows, 7)

        self.assertAlmostEqual(sl.area(), 620.228, 1)

    def test_too_many_beads_bug(self):
        pspec = create_csv_combo("Test 3", "Sport stitch repeats", "Test 1")
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons, 72)
        self.assertEqual(sl.inter_sleeve_increase_rows, None)
        self.assertEqual(sl.num_sleeve_increase_repetitions, None)
        self.assertEqual(sl.num_sleeve_increase_rows, None)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 72)
        self.assertEqual(sl.armscye_x, 6)
        self.assertEqual(sl.armscye_y, 2)
        self.assertEqual(sl.six_count_beads, 3)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.two_count_beads, 14)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.pre_bead_game_stitch_count, 56)
        self.assertEqual(sl.post_bead_game_stitch_count, 22)
        self.assertEqual(sl.armscye_d, 2)
        self.assertEqual(sl.armscye_c, 14)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 1)
        self.assertEqual(sl.actual_wrist, 12)
        self.assertEqual(sl.actual_bicep, 12)
        self.assertEqual(sl.actual_armcap_heights, 6.875)
        self.assertEqual(sl.actual_total_height, 7.875)

        self.assertIsNone(sl.inter_sleeve_increase_rows_plus_one)
        self.assertIsNone(sl.shaping_row_on_ws)

        self.assertAlmostEqual(sl.area(), 122.541, 1)

    def test_coverage_big_bells1(self):
        pspec = SweaterPatternSpecFactory(
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_BELL,
            bell_type=SDC.BELL_EXTREME,
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sleeve.sleeve_cast_on_width = 50
        ips.save()
        sl = make_sleeve_from_ips(ips)

        self.assertEqual(sl.cast_ons, 136)
        self.assertEqual(sl.inter_sleeve_increase_rows, 0)
        self.assertEqual(sl.num_sleeve_increase_repetitions, 33)
        self.assertEqual(sl.num_sleeve_increase_rows, 34)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 68)
        self.assertEqual(sl.actual_wrist, 27.2)
        self.assertEqual(sl.actual_bicep, 13.6)
        self.assertAlmostEqual(sl.area(), 363.19999, 1)

    def test_coverage_big_bells2(self):
        swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=5, additional_stitches=2
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_BELL,
            bell_type=SDC.BELL_EXTREME,
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sleeve.sleeve_cast_on_width = 50
        ips.save()
        sl = make_sleeve_from_ips(ips)

        self.assertEqual(sl.cast_ons, 127)
        self.assertEqual(sl.inter_sleeve_increase_rows, 0)
        self.assertEqual(sl.num_sleeve_increase_repetitions, 29)
        self.assertEqual(sl.num_sleeve_increase_rows, 30)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.actual_wrist, 25.4)
        self.assertEqual(sl.actual_bicep, 13.4)
        self.assertAlmostEqual(sl.area(), 342.914, 1)

    def test_sleeve_regression_max_distance_between_shaping(self):
        swatch = SwatchFactory(rows_length=1, rows_number=4)
        pspec = SweaterPatternSpecFactory(
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            swatch=swatch,
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sleeve.sleeve_cast_on_width = 9
        ips.sleeve.bicep_width = 9.5
        ips.save()
        sl = make_sleeve_from_ips(ips)
        self.assertEqual(sl.num_sleeve_increase_rows, 2)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.inter_sleeve_increase_rows, 20)

    def test_sleeve_regression_even_shaping_rows(self):
        swatch = SwatchFactory(rows_length=1, rows_number=4)
        pspec = SweaterPatternSpecFactory(
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            swatch=swatch,
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sleeve.sleeve_cast_on_width = 4
        ips.sleeve.bicep_width = 10
        ips.save()
        sl = make_sleeve_from_ips(ips)
        self.assertEqual(sl.inter_sleeve_increase_rows, 3)

    def test_sleeve_regression_odd_shaping_rows(self):
        swatch = SwatchFactory(rows_length=1, rows_number=4)
        pspec = SweaterPatternSpecFactory(
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            swatch=swatch,
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sleeve.sleeve_cast_on_width = 4
        ips.sleeve.bicep_width = 11
        ips.save()
        sl = make_sleeve_from_ips(ips)
        self.assertEqual(sl.inter_sleeve_increase_rows, 2)

    def test_sleeve_cap_too_short(self):
        sl = create_sleeve()
        self.assertGreater(sl.actual_armcap_heights, 5.0)

    def test_shaping_constraints_not_met(self):
        pspec = create_csv_combo("Test 9", "DK Stitch repeats", "Test 8")
        make_sleeve_from_pspec(pspec)

    def test_sleeve_cap_too_short_test3_1(self):
        pspec = create_csv_combo("Test 3", "Cascade 220 St st", "Test 5")
        sl = make_sleeve_from_pspec(pspec)
        back = make_sweaterback_from_pspec(pspec)
        _compare_sleevecap_to_backpiece(sl, back, "hardcoded Test 3")

    def test_sleevecap_too_short2(self):
        pspec = create_csv_combo("Test 1", "Bulky St st", "Test 3")
        sl = make_sleeve_from_pspec(pspec)
        back = make_sweaterback_from_pspec(pspec)
        _compare_sleevecap_to_backpiece(sl, back, "hardcoded test 2")

    def test_small_sleevecap(self):
        swatch = SwatchFactory(
            rows_number=40, rows_length=6.25, stitches_number=36, stitches_length=8.5
        )
        body_dict = {
            "waist_circ": 38.5,
            "bust_circ": 42,
            "upper_torso_circ": 37,
            "wrist_circ": 6,
            "forearm_circ": 9.5,
            "bicep_circ": 12.25,
            "elbow_circ": 10,
            "armpit_to_short_sleeve": 3.5,
            "armpit_to_elbow_sleeve": 9,
            "armpit_to_three_quarter_sleeve": 15.75,
            "armpit_to_full_sleeve": 20.25,
            "inter_nipple_distance": 9,
            "armpit_to_waist": 7,
            "armhole_depth": 7.75,
            "armpit_to_high_hip": 7 + 3.5,
            "armpit_to_med_hip": 7 + 5.5,
            "armpit_to_low_hip": 7 + 7,
            "armpit_to_tunic": 7 + 11.5,
            "high_hip_circ": 42,
            "med_hip_circ": 44.25,
            "low_hip_circ": 43.75,
            "tunic_circ": 43.75,
        }
        body = BodyFactory(**body_dict)
        pspec = SweaterPatternSpecFactory(body=body, swatch=swatch)
        sl = make_sleeve_from_pspec(pspec)
        back = make_sweaterback_from_pspec(pspec)

        self.assertAlmostEqual(back._compute_armhole_circumference(), 9.25, 2)
        self.assertEqual(sl.armscye_x, 4)
        self.assertEqual(sl.armscye_y, 2)
        self.assertEqual(sl.armscye_c, 11)
        self.assertEqual(sl.armscye_d, 2)

    def test_one_bead(self):
        swatch = SwatchFactory(
            stitches_number=27,
            stitches_length=3.5625,
            rows_number=29,
            rows_length=2.9375,
        )

        body = get_csv_body("Test 2")
        waist_to_shoulder = body.armpit_to_waist + body.armhole_depth
        body.waist_to_armpit = 9
        body.armhole_depth = waist_to_shoulder - body.waist_to_armpit
        pspec = SweaterPatternSpecFactory(
            body=body,
            swatch=swatch,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_THREEQUARTER,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            hip_edging_stitch=StitchFactory(name="Folded hem"),
            hip_edging_height=1.5,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_height=1,
            neck_edging_stitch=StitchFactory(name="Other Stitch"),
            neck_edging_height=5,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.one_count_beads, 6)
        self.assertEqual(sl.two_count_beads, 15)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.six_count_beads, 0)

        waist_to_shoulder = body.waist_to_armpit + body.armhole_depth
        body.waist_to_armpit = 10
        body.armhole_depth = waist_to_shoulder - body.waist_to_armpit
        pspec = SweaterPatternSpecFactory(
            body=body,
            swatch=swatch,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_THREEQUARTER,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            hip_edging_stitch=StitchFactory(name="Folded hem"),
            hip_edging_height=1.5,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_height=1,
            neck_edging_stitch=StitchFactory(name="Other Stitch"),
            neck_edging_height=5,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.one_count_beads, 20)
        self.assertEqual(sl.two_count_beads, 1)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.six_count_beads, 0)

        waist_to_shoulder = body.waist_to_armpit + body.armhole_depth
        body.waist_to_armpit = 10.2
        body.armhole_depth = waist_to_shoulder - body.waist_to_armpit
        pspec = SweaterPatternSpecFactory(
            body=body,
            swatch=swatch,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_THREEQUARTER,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            hip_edging_stitch=StitchFactory(name="Folded hem"),
            hip_edging_height=1.5,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_height=1,
            neck_edging_stitch=StitchFactory(name="Other Stitch"),
            neck_edging_height=5,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.one_count_beads, 18)
        self.assertEqual(sl.two_count_beads, 0)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.six_count_beads, 0)

    def test_sleeve_mismatched_parity(self):
        body = get_csv_body("Test 1")
        swatch = SwatchFactory(
            stitches_length=4,
            stitches_number=20,
            rows_length=4,
            rows_number=24,
            use_repeats=True,
            stitches_per_repeat=3,
            additional_stitches=2,
        )
        pspec = SweaterPatternSpecFactory(
            body=body,
            swatch=swatch,
            garment_fit=SDC.FIT_HOURGLASS_TIGHT,
            sleeve_length=SDC.SLEEVE_ELBOW,
        )
        make_sleeve_from_pspec(pspec)

    def test_stitches(self):
        pspec = SweaterPatternSpecFactory(
            sleeve_allover_stitch=StitchFactory(name="Stockinette")
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.allover_stitch, StitchFactory(name="Stockinette"))
        self.assertIsNone(sl.caston_repeats(), None)

        pspec = SweaterPatternSpecFactory(
            sleeve_allover_stitch=StitchFactory(name="allover stitch"),
            sleeve_edging_stitch=StitchFactory(name="edging stitch"),
            sleeve_cable_stitch=StitchFactory(name="cable stitch"),
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.allover_stitch, StitchFactory(name="allover stitch"))
        self.assertEqual(sl.hem_stitch, StitchFactory(name="edging stitch"))
        self.assertEqual(sl.cable_stitch, StitchFactory(name="cable stitch"))

    def test_repeats(self):

        # For comparison
        # Note: need to get gauge just right to avoid a caston
        # that duplicates a later repeat target
        swatch = SwatchFactory(stitches_length=4, stitches_number=22)
        pspec = SweaterPatternSpecFactory(swatch=swatch)
        sl = make_sleeve_from_pspec(pspec)
        # Note: 50 is 2 mod 4 and 2 mod 3
        self.assertEqual(sl.cast_ons, 50)

        # Note: Cabled check is 1 mod 4
        # one-by-one rib does not use repeats
        pspec = SweaterPatternSpecFactory(
            sleeve_allover_stitch=StitchFactory(name="Cabled Check Stitch"),
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            swatch=swatch,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons % 4, 1)

        repeats_swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=3, additional_stitches=1
        )
        pspec = SweaterPatternSpecFactory(
            sleeve_allover_stitch=StitchFactory(name="Stockinette"),
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            swatch=repeats_swatch,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons % 3, 1)

        # Open mesh lace is 0 mod 3
        pspec = SweaterPatternSpecFactory(
            sleeve_allover_stitch=StitchFactory(name="Stockinette"),
            sleeve_edging_stitch=StitchFactory(name="Open Mesh Lace"),
            swatch=swatch,
        )
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons % 3, 0)

    def test_tapered_simple_body(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        # Sanity check: make sure that SimpleBodyFactory acts as we expect
        self.assertIsNone(body.forearm_circ)
        self.assertIsNone(body.elbow_circ)

        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
        )
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)

    def test_edging_height(self):
        # If the edging height would go into the sleeve cap, then adjust it to be 0.5 inches
        user = UserFactory()

        # sanity-check: arm long enough for edging
        long_arm_body = BodyFactory(armpit_to_short_sleeve=4)

        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            body=long_arm_body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_SHORT,
            sleeve_edging_height=3,
        )
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)

        self.assertEqual(sl.wrist_hem_height, 3)

        # test: arm and edging exactly the same length
        long_arm_body = BodyFactory(armpit_to_short_sleeve=3)

        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            body=long_arm_body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_SHORT,
            sleeve_edging_height=3,
        )
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.wrist_hem_height, 3)

        # test: shorter_than_edging
        long_arm_body = BodyFactory(armpit_to_short_sleeve=1)

        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            body=long_arm_body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_SHORT,
            sleeve_edging_height=3,
        )
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.wrist_hem_height, 0.5)

    def test_drop_shoulders(self):

        # control
        pspec = SweaterPatternSpecFactory(construction=SDC.CONSTRUCTION_SET_IN_SLEEVE)
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)
        self.assertEqual(sl.cast_ons, 45)
        self.assertEqual(sl.num_sleeve_increase_rows, 11)
        self.assertEqual(sl.inter_sleeve_increase_rows, 9)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, None)
        self.assertEqual(sl.rows_after_compound_shaping_rows, None)
        self.assertEqual(sl.bicep_stitches, 67)
        self.assertEqual(sl.armscye_x, 5)
        self.assertEqual(sl.armscye_y, 3)
        self.assertEqual(sl.armscye_c, 13)
        self.assertEqual(sl.armscye_d, 2)
        self.assertEqual(sl.rows_in_cap, 45)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.two_count_beads, 13)
        self.assertEqual(sl.four_count_beads, 1)
        self.assertEqual(sl.six_count_beads, 1)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 17.5)
        self.assertAlmostEqual(sl.actual_armcap_heights, 6.43, 1)
        self.assertFalse(sl.is_drop_shoulder)
        self.assertTrue(sl.is_set_in_sleeve)

        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        sl = make_sleeve_from_pspec(pspec)

        # sanity check:
        self.assertEqual(pspec.swatch.get_gauge().rows, 7)
        self.assertEqual(pspec.swatch.get_gauge().stitches, 5)

        self.assertEqual(sl.cast_ons, 45)
        self.assertEqual(sl.num_sleeve_increase_rows, 13)
        self.assertEqual(sl.inter_sleeve_increase_rows, 4)
        self.assertEqual(sl.num_sleeve_compound_increase_rows, 12)
        self.assertEqual(sl.rows_after_compound_shaping_rows, 3)
        self.assertEqual(sl.bicep_stitches, 95)
        self.assertEqual(sl.armscye_x, 0)
        self.assertEqual(sl.armscye_y, 0)
        self.assertEqual(sl.armscye_c, 95)
        self.assertEqual(sl.armscye_d, 0)
        self.assertEqual(sl.one_count_beads, 0)
        self.assertEqual(sl.two_count_beads, 0)
        self.assertEqual(sl.four_count_beads, 0)
        self.assertEqual(sl.six_count_beads, 0)
        self.assertEqual(sl.wrist_hem_height, 0.5)
        self.assertEqual(sl.actual_wrist_to_cap, 17.5)
        self.assertEqual(sl.actual_armcap_heights, 0)

        self.assertEqual(sl.actual_total_height, sl.actual_wrist_to_cap)
        self.assertTrue(sl.is_drop_shoulder)
        self.assertFalse(sl.is_set_in_sleeve)
        self.assertEqual(sl.pre_bead_game_stitch_count, 95)
        self.assertEqual(sl.post_bead_game_stitch_count, 95)
        self.assertEqual(sl.actual_wrist_to_cap_in_rows, 122)
        self.assertEqual(sl.rows_in_cap, 0)
        self.assertEqual(sl.actual_wrist_to_end_in_rows, 122)
        self.assertEqual(sl.last_shaping_to_cap_in_rows, 8)
        self.assertAlmostEqual(sl.area(), 492.0, 1)

    def test_clean_shaping(self):
        good_vectors = [
            # Machine generated, but human inspected
            (None, None, None, None),
            (1, None, None, None),
            (1, None, 0, None),
            (2, 0, None, None),
            (2, 0, 0, None),
            (2, 0, 1, 1),
            (2, 0, 1, 2),
            (2, 0, 1, 3),
            (2, 0, 2, 1),
            (2, 0, 2, 2),
            (2, 0, 2, 3),
            (2, 1, None, None),
            (2, 1, 0, None),
            (2, 1, 1, 0),
            (2, 1, 1, 2),
            (2, 1, 1, 3),
            (2, 1, 2, 0),
            (2, 1, 2, 2),
            (2, 1, 2, 3),
            (2, 2, None, None),
            (2, 2, 0, None),
            (2, 2, 1, 0),
            (2, 2, 1, 1),
            (2, 2, 1, 3),
            (2, 2, 2, 0),
            (2, 2, 2, 1),
            (2, 2, 2, 3),
            (2, 3, None, None),
            (2, 3, 0, None),
            (2, 3, 1, 0),
            (2, 3, 1, 1),
            (2, 3, 1, 2),
            (2, 3, 2, 0),
            (2, 3, 2, 1),
            (2, 3, 2, 2),
            (3, 0, None, None),
            (3, 0, 0, None),
            (3, 0, 2, 1),
            (3, 0, 2, 2),
            (3, 0, 2, 3),
            (3, 0, 3, 1),
            (3, 0, 3, 2),
            (3, 0, 3, 3),
            (3, 1, None, None),
            (3, 1, 0, None),
            (3, 1, 2, 0),
            (3, 1, 2, 2),
            (3, 1, 2, 3),
            (3, 1, 3, 0),
            (3, 1, 3, 2),
            (3, 1, 3, 3),
            (3, 2, None, None),
            (3, 2, 0, None),
            (3, 2, 2, 0),
            (3, 2, 2, 1),
            (3, 2, 2, 3),
            (3, 2, 3, 0),
            (3, 2, 3, 1),
            (3, 2, 3, 3),
            (3, 3, None, None),
            (3, 3, 0, None),
            (3, 3, 2, 0),
            (3, 3, 2, 1),
            (3, 3, 2, 2),
            (3, 3, 3, 0),
            (3, 3, 3, 1),
            (3, 3, 3, 2),
        ]

        sleeve = create_sleeve()
        for v in itertools.product(
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
        ):
            (std_rows, inter_std_rows, compound_rows, after_compound_rows) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            if v in good_vectors:
                sleeve.full_clean()
            else:
                with self.assertRaises(ValidationError):
                    sleeve.full_clean()

    def test_is_straight(self):

        sleeve = create_sleeve()
        for v in itertools.product(
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
        ):
            (std_rows, inter_std_rows, compound_rows, after_compound_rows) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            try:
                sleeve.full_clean()
            except ValidationError:
                pass
            else:
                if std_rows or compound_rows:
                    self.assertFalse(sleeve.is_straight)
                else:
                    self.assertTrue(sleeve.is_straight)

    def test_num_sleeve_increase_repetitions(self):
        sleeve = create_sleeve()
        for v in itertools.product(
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
            [None, 0, 1, 2, 3],
        ):
            (std_rows, inter_std_rows, compound_rows, after_compound_rows) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            try:
                sleeve.full_clean()
            except ValidationError:
                pass
            else:
                if compound_rows:
                    self.assertEqual(sleeve.num_sleeve_increase_repetitions, None)
                elif not std_rows:
                    self.assertEqual(sleeve.num_sleeve_increase_repetitions, None)
                else:
                    self.assertEqual(
                        sleeve.num_sleeve_increase_repetitions, std_rows - 1
                    )

    def test_rows_in_shaping(self):

        sleeve = create_sleeve()
        with self.assertRaises(AssertionError):
            sleeve.num_sleeve_increase_rows = None
            sleeve.inter_sleeve_increase_rows = None
            sleeve.num_sleeve_compound_increase_rows = None
            sleeve.rows_after_compound_shaping_rows = None
            sleeve._rows_in_shaping()

        vectors = [
            (1, None, None, None, 1),
            (1, None, 0, None, 1),
            (2, 0, None, None, 2),
            (2, 0, 0, None, 2),
            (2, 0, 1, 1, 4),
            (2, 0, 1, 2, 5),
            (2, 0, 1, 3, 6),
            (2, 0, 2, 1, 5),
            (2, 0, 2, 2, 6),
            (2, 0, 2, 3, 7),
            (2, 1, None, None, 3),
            (2, 1, 0, None, 3),
            (2, 1, 1, 0, 4),
            (2, 1, 1, 2, 6),
            (2, 1, 1, 3, 7),
            (2, 1, 2, 0, 6),
            (2, 1, 2, 2, 8),
            (2, 1, 2, 3, 9),
            (2, 2, None, None, 4),
            (2, 2, 0, None, 4),
            (2, 2, 1, 0, 5),
            (2, 2, 1, 1, 6),
            (2, 2, 1, 3, 8),
            (2, 2, 2, 0, 8),
            (2, 2, 2, 1, 9),
            (2, 2, 2, 3, 11),
            (2, 3, None, None, 5),
            (2, 3, 0, None, 5),
            (2, 3, 1, 0, 6),
            (2, 3, 1, 1, 7),
            (2, 3, 1, 2, 8),
            (2, 3, 2, 0, 10),
            (2, 3, 2, 1, 11),
            (2, 3, 2, 2, 12),
            (3, 0, None, None, 3),
            (3, 0, 0, None, 3),
            (3, 0, 2, 1, 7),
            (3, 0, 2, 2, 9),
            (3, 0, 2, 3, 11),
            (3, 0, 3, 1, 8),
            (3, 0, 3, 2, 10),
            (3, 0, 3, 3, 12),
            (3, 1, None, None, 5),
            (3, 1, 0, None, 5),
            (3, 1, 2, 0, 7),
            (3, 1, 2, 2, 11),
            (3, 1, 2, 3, 13),
            (3, 1, 3, 0, 9),
            (3, 1, 3, 2, 13),
            (3, 1, 3, 3, 15),
            (3, 2, None, None, 7),
            (3, 2, 0, None, 7),
            (3, 2, 2, 0, 9),
            (3, 2, 2, 1, 11),
            (3, 2, 2, 3, 15),
            (3, 2, 3, 0, 12),
            (3, 2, 3, 1, 14),
            (3, 2, 3, 3, 18),
            (3, 3, None, None, 9),
            (3, 3, 0, None, 9),
            (3, 3, 2, 0, 11),
            (3, 3, 2, 1, 13),
            (3, 3, 2, 2, 15),
            (3, 3, 3, 0, 15),
            (3, 3, 3, 1, 17),
            (3, 3, 3, 2, 19),
        ]

        for v in vectors:
            (
                std_rows,
                inter_std_rows,
                compound_rows,
                after_compound_rows,
                rows_in_shaping,
            ) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            self.assertEqual(sleeve._rows_in_shaping(), rows_in_shaping)

    def test_rows_in_compound_shaping_rows_plus_one(self):
        vectors = [
            (None, None, None, None, None),
            (1, None, None, None, None),
            (1, None, 0, None, None),
            (2, 0, None, None, None),
            (2, 0, 0, None, None),
            (2, 0, 1, 1, 2),
            (2, 0, 1, 2, 3),
            (2, 0, 1, 3, 4),
            (2, 1, 1, 0, 1),
            (2, 1, 1, 2, 3),
            (2, 1, 1, 3, 4),
        ]

        sleeve = create_sleeve()
        for v in vectors:
            (
                std_rows,
                inter_std_rows,
                compound_rows,
                after_compound_rows,
                rows_plus_one,
            ) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            self.assertEqual(
                sleeve.rows_after_compound_shaping_rows_plus_one, rows_plus_one
            )

    def test_shaping_rows_on_ws(self):
        vectors = [
            (None, None, None, None, None),
            (1, None, None, None, False),
            (1, None, 0, None, False),
            (2, 0, None, None, True),
            (2, 0, 0, None, True),
            (2, 0, 1, 1, True),
            (2, 0, 1, 2, True),
            (2, 1, None, None, False),
            (2, 1, 0, None, False),
            (2, 1, 1, 0, True),
            (2, 1, 1, 2, True),
            (2, 1, 1, 3, False),
        ]

        sleeve = create_sleeve()
        for v in vectors:
            (
                std_rows,
                inter_std_rows,
                compound_rows,
                after_compound_rows,
                shaping_on_ws,
            ) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            self.assertEqual(sleeve.shaping_row_on_ws, shaping_on_ws)

    def test_num_shaping_rows_and_minus_one(self):
        vectors = [
            (None, None, None, None, 0, None),
            (1, None, None, None, 1, 0),
            (1, None, 0, None, 1, 0),
            (2, 0, None, None, 2, 1),
            (2, 0, 0, None, 2, 1),
            (2, 0, 1, 1, 3, 2),
            (2, 0, 1, 2, 3, 2),
            (2, 0, 1, 3, 3, 2),
            (2, 0, 2, 1, 4, 3),
            (2, 0, 2, 2, 4, 3),
            (2, 0, 2, 3, 4, 3),
        ]

        sleeve = create_sleeve()
        for v in vectors:
            (
                std_rows,
                inter_std_rows,
                compound_rows,
                after_compound_rows,
                num_shaping_rows,
                minus_one,
            ) = v
            sleeve.num_sleeve_increase_rows = std_rows
            sleeve.inter_sleeve_increase_rows = inter_std_rows
            sleeve.num_sleeve_compound_increase_rows = compound_rows
            sleeve.rows_after_compound_shaping_rows = after_compound_rows

            self.assertEqual(sleeve.num_shaping_rows(), num_shaping_rows)
            self.assertEqual(sleeve.num_shaping_rows_minus_one(), minus_one)


class GradedSleeveTests(django.test.TestCase):

    def test_make(self):
        from ..helpers.secret_sauce import ease_tolerances as _ease_tolerances
        from ..helpers.secret_sauce import rounding_directions as _rounding_directions

        gcs = GradedSweaterSchematicFactory()
        spec_source = gcs.get_spec_source()
        fit = spec_source.garment_fit
        roundings = _rounding_directions[fit]
        ease_tolerances = _ease_tolerances[fit]

        back_piece_schematic = gcs.sweater_back_schematics.order_by(
            "GradedSweaterBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        sweater_back = GradedSweaterBack.make(
            graded_pattern_pieces, back_piece_schematic, roundings, ease_tolerances
        )
        sweater_back.sort_key = 40

        sl_sch = gcs.sleeve_schematics.get(
            GradedSleeveSchematic___gp_grade__grade=sweater_back.schematic.gp_grade.grade
        )
        GradedSleeve.make(sl_sch, sweater_back, roundings, ease_tolerances, spec_source)
