import itertools

import django.test

import customfit.helpers.row_parities as RCP
from customfit.bodies.factories import BodyFactory, get_csv_body
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ..factories import (
    GradedCardiganPatternSpecFactory,
    GradedCardiganVestPatternSpecFactory,
    GradedSweaterPatternPiecesFactory,
    GradedSweaterSchematicFactory,
    GradedVestPatternSpecFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    create_cardigan_sleeved,
    create_sweater_front,
    make_cardigan_sleeved_from_pspec,
    make_sweaterfront_from_ips,
    make_sweaterfront_from_pspec,
    make_vestfront_from_pspec,
)
from ..helpers import sweater_design_choices as SDC
from ..helpers.secret_sauce import ease_tolerances, rounding_directions
from ..models import (
    GradedCardiganSleeved,
    GradedCardiganVest,
    GradedSweaterBack,
    GradedSweaterFront,
    GradedVestBack,
    GradedVestFront,
    SweaterIndividualGarmentParameters,
    SweaterSchematic,
)


class SweaterFrontTest(django.test.TestCase):

    def setUp(self):

        StitchFactory(
            name="2x2 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
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

    def test_sweater_front_regression1(self):
        sf = create_sweater_front()
        self.assertEqual(sf.cast_ons, 98)
        self.assertEqual(sf.pre_marker, 25)
        self.assertEqual(sf.post_marker, 25)
        self.assertEqual(sf.inter_marker, 48)
        self.assertEqual(sf.waist_hem_height, 1.5)
        self.assertEqual(sf.has_waist_decreases, True)
        self.assertFalse(sf.any_waist_decreases_on_ws)
        self.assertEqual(sf.num_waist_standard_decrease_rows, 5)
        self.assertEqual(sf.num_waist_double_dart_rows, 0)
        self.assertEqual(sf.num_waist_triple_dart_rows, 0)
        self.assertEqual(sf.num_bust_standard_increase_rows, 7)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sf.num_bust_triple_dart_rows, 0)
        self.assertEqual(sf.num_waist_decrease_rows_knitter_instructions, 5)
        self.assertEqual(sf.num_waist_standard_decrease_rows, 5)
        self.assertEqual(sf.num_waist_standard_decrease_repetitions, 4)
        self.assertEqual(sf.rows_between_waist_standard_decrease_rows, 5)
        self.assertEqual(sf.waist_double_darts, False)
        self.assertEqual(sf.waist_double_dart_marker, None)
        self.assertEqual(sf.waist_inter_double_marker, None)
        self.assertEqual(sf.num_waist_double_dart_decrease_repetitions, None)
        self.assertEqual(sf.num_waist_non_double_dart_decrease_repetitions, None)
        self.assertEqual(
            sf.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(sf.waist_triple_darts, False)
        self.assertEqual(sf.waist_triple_dart_marker, None)
        self.assertEqual(sf.waist_inter_triple_marker, None)
        self.assertEqual(sf.num_waist_triple_dart_repetitions, None)
        self.assertEqual(sf.begin_decreases_height, 2.9285714285714284)
        self.assertEqual(sf.hem_to_waist, 7.5)
        self.assertEqual(sf.waist_stitches, 88)
        self.assertEqual(sf.has_bust_increases, True)
        self.assertFalse(sf.any_bust_increases_on_ws)
        self.assertEqual(sf.num_bust_increase_rows_knitter_instructions, 7)
        self.assertEqual(sf.num_bust_standard_increase_rows, 7)
        self.assertEqual(sf.num_bust_standard_increase_repetitions, 6)
        self.assertEqual(sf.rows_between_bust_standard_increase_rows, 7)
        self.assertEqual(sf.bust_pre_standard_dart_marker, 20)
        self.assertEqual(sf.bust_double_darts, False)
        self.assertEqual(sf.bust_pre_double_dart_marker, None)
        self.assertEqual(sf.bust_inter_double_dart_markers, None)
        self.assertEqual(sf.bust_inter_double_and_standard_dart_markers, None)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(sf.num_bust_non_double_dart_increase_repetitions, None)
        self.assertEqual(
            sf.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(sf.bust_triple_darts, False)
        self.assertEqual(sf.bust_pre_triple_dart_marker, None)
        self.assertEqual(sf.bust_inter_triple_dart_markers, None)
        self.assertEqual(sf.bust_inter_double_and_triple_dart_markers, None)
        self.assertEqual(sf.num_bust_triple_dart_repetitions, None)
        self.assertEqual(sf.hem_to_bust_increase_end, 14.5)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 16)
        self.assertEqual(sf.armhole_x, 5)
        self.assertEqual(sf.armhole_y, 3)
        self.assertEqual(sf.armhole_z, 7)
        self.assertEqual(sf.hem_to_neckline_shaping_start, 18)
        self.assertAlmostEqual(sf.hem_to_neckline_shaping_end, 23.57, 2)
        self.assertEqual(sf.hem_to_shoulders, 24)
        self.assertEqual(sf.first_shoulder_bindoff, 9)
        self.assertEqual(sf.second_shoulder_bindoff, 8)
        self.assertEqual(sf.num_shoulder_stitches, 17)
        self.assertEqual(sf.actual_hip, 19.600000000000001)
        self.assertEqual(sf.actual_waist, 17.600000000000001)
        self.assertEqual(sf.actual_bust, 20.399999999999999)
        self.assertEqual(sf.actual_armhole_depth, 8)
        self.assertEqual(sf.actual_shoulder_stitch_width, 3.3999999999999999)
        self.assertAlmostEqual(sf.actual_armhole_circumference, 9.7555, 2)
        self.assertEqual(sf.hem_to_waist, 7.5)
        self.assertEqual(sf.actual_hem_to_armhole, 16)
        self.assertEqual(sf.actual_waist_to_armhole, 8.5)
        self.assertEqual(sf.actual_hem_to_shoulder, 24)
        self.assertEqual(sf.bust_use_standard_markers, True)

        self.assertAlmostEqual(sf.area(), 411.85, 1)
        self.assertEqual(sf.actual_neck_opening_width, 7.6)

        self.assertEqual(sf.cross_chest_stitches, 72)

    def test_sweater_front_regression2(self):
        user = UserFactory()
        swatch = SwatchFactory(rows_number=4, stitches_number=10)
        body = get_csv_body("Test 5")
        pspec = SweaterPatternSpecFactory(body=body, swatch=swatch)
        sf = make_sweaterfront_from_pspec(pspec)

        self.assertEqual(sf.cast_ons, 165)
        self.assertEqual(sf.pre_marker, 41)
        self.assertEqual(sf.post_marker, 41)
        self.assertEqual(sf.inter_marker, 83)
        self.assertEqual(sf.waist_hem_height, 1.5)
        self.assertEqual(sf.has_waist_decreases, True)
        self.assertFalse(sf.any_waist_decreases_on_ws)
        self.assertEqual(sf.num_waist_standard_decrease_rows, 1)
        self.assertEqual(sf.num_waist_double_dart_rows, 3)
        self.assertEqual(sf.num_waist_triple_dart_rows, 3)
        self.assertEqual(sf.num_bust_standard_increase_rows, 2)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(sf.num_bust_triple_dart_rows, 4)
        self.assertEqual(sf.num_waist_decrease_rows_knitter_instructions, 7)
        self.assertEqual(sf.num_waist_standard_decrease_rows, 1)
        self.assertEqual(sf.num_waist_standard_decrease_repetitions, 0)
        self.assertEqual(sf.rows_between_waist_standard_decrease_rows, 3)
        self.assertEqual(sf.waist_double_darts, True)
        self.assertEqual(sf.waist_double_dart_marker, 20)
        self.assertEqual(sf.waist_inter_double_marker, 21)
        self.assertEqual(sf.num_waist_double_dart_decrease_repetitions, 2)
        self.assertEqual(sf.num_waist_non_double_dart_decrease_repetitions, 0)
        self.assertEqual(
            sf.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(sf.waist_triple_darts, True)
        self.assertEqual(sf.waist_triple_dart_marker, 10)
        self.assertEqual(sf.waist_inter_triple_marker, 10)
        self.assertEqual(sf.num_waist_triple_dart_repetitions, 2)
        self.assertEqual(sf.begin_decreases_height, 2.75)
        self.assertEqual(sf.hem_to_waist, 7.0)
        self.assertEqual(sf.waist_stitches, 145)
        self.assertEqual(sf.has_bust_increases, True)
        self.assertFalse(sf.any_bust_increases_on_ws)
        self.assertEqual(sf.num_bust_increase_rows_knitter_instructions, 11)
        self.assertEqual(sf.num_bust_standard_increase_rows, 2)
        self.assertEqual(sf.num_bust_standard_increase_repetitions, 1)
        self.assertEqual(sf.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(sf.bust_pre_standard_dart_marker, 34)
        self.assertEqual(sf.bust_double_darts, True)
        self.assertEqual(sf.bust_pre_double_dart_marker, 14)
        self.assertEqual(sf.bust_inter_double_dart_markers, 117)
        self.assertEqual(sf.bust_inter_double_and_standard_dart_markers, 20)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(sf.num_bust_non_double_dart_increase_repetitions, 0)
        self.assertEqual(
            sf.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(sf.bust_triple_darts, True)
        self.assertEqual(sf.bust_pre_triple_dart_marker, 7)
        self.assertEqual(sf.bust_inter_triple_dart_markers, 131)
        self.assertEqual(sf.bust_inter_double_and_triple_dart_markers, 7)
        self.assertEqual(sf.num_bust_triple_dart_repetitions, 3)
        self.assertEqual(sf.hem_to_bust_increase_end, 12.25)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 13.5)
        self.assertEqual(sf.armhole_x, 10)
        self.assertEqual(sf.armhole_y, 9)
        self.assertEqual(sf.armhole_z, 2)
        self.assertEqual(sf.hem_to_neckline_shaping_start, 11.75)
        self.assertEqual(sf.hem_to_neckline_shaping_end, 20.5)
        self.assertEqual(sf.hem_to_shoulders, 20.5)
        self.assertEqual(sf.first_shoulder_bindoff, 17)
        self.assertEqual(sf.second_shoulder_bindoff, 16)
        self.assertEqual(sf.num_shoulder_stitches, 33)
        self.assertEqual(sf.actual_hip, 16.5)
        self.assertEqual(sf.actual_waist, 14.5)
        self.assertEqual(sf.actual_bust, 17.5)
        self.assertEqual(sf.actual_armhole_depth, 7)
        self.assertEqual(sf.actual_shoulder_stitch_width, 3.2999999999999998)
        self.assertAlmostEqual(sf.actual_armhole_circumference, 8.4198, 2)
        self.assertEqual(sf.hem_to_waist, 7)
        self.assertEqual(sf.actual_hem_to_armhole, 13.5)
        self.assertEqual(sf.actual_waist_to_armhole, 6.5)
        self.assertEqual(sf.actual_hem_to_shoulder, 20.5)
        self.assertEqual(sf.bust_use_standard_markers, True)

        self.assertAlmostEqual(sf.area(), 293.28, 1)
        self.assertEqual(sf.actual_neck_opening_width, 6.7)

        self.assertIsNone(sf.cross_chest_stitches)

    def test_below_armhole_straight(self):
        user = UserFactory()
        swatch = SwatchFactory(rows_number=4, stitches_number=10)
        body = get_csv_body("Test 1")
        pspec = SweaterPatternSpecFactory(body=body, swatch=swatch)
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()

        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.save()
        sf = make_sweaterfront_from_ips(ips)
        self.assertEqual(sf.num_bust_standard_increase_rows, 8)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 7)
        self.assertEqual(sf.num_bust_triple_dart_rows, 0)
        self.assertEqual(sf.hem_to_waist, 7.5)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 16)
        # Note: you would expect a below_armpit_straight of 1.5 to limit
        # hem_to_bust_increase_end to 14.5 or less, but the bust-shaping
        # logic allows it to violate that limit by one row-height in order to
        # avoid a rounding error during the schematic-loop
        self.assertLessEqual(sf.hem_to_bust_increase_end, 14.75)
        sf.delete()

        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sweater_front.below_armpit_straight = 2.5
        ips.save()
        sf = make_sweaterfront_from_ips(ips)
        self.assertEqual(sf.num_bust_standard_increase_rows, 5)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 6)
        self.assertEqual(sf.num_bust_triple_dart_rows, 2)
        self.assertEqual(sf.hem_to_waist, 7.5)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 16)
        # Note: you would expect a below_armpit_straight of 2.5 to limit
        # hem_to_bust_increase_end to 13.5 or less, but the bust-shaping
        # logic allows it to violate that limit by one row-height in order to
        # avoid a rounding error during the schematic-loop
        self.assertLessEqual(sf.hem_to_bust_increase_end, 13.75)

        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.sweater_front.below_armpit_straight = 5
        ips.save()
        sf = make_sweaterfront_from_ips(ips)
        self.assertEqual(sf.num_bust_standard_increase_rows, 2)
        self.assertEqual(sf.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(sf.num_bust_triple_dart_rows, 4)
        self.assertEqual(sf.hem_to_waist, 7.5)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 16)
        # Note: you would expect a below_armpit_straight of 5 to limit
        # hem_to_bust_increase_end to 11 or less, but the bust-shaping
        # logic allows it to violate that limit if it cannot acheive the
        # bust shaping within that constraint.
        self.assertEqual(sf.hem_to_bust_increase_end, 12.75)

    def test_row_count_neck_above_armhole(self):
        pspec = SweaterPatternSpecFactory(
            neckline_depth=2, neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )

        sf = make_sweaterfront_from_pspec(pspec)

        self.assertGreater(sf.waist_hem_height_in_rows, 0)
        self.assertGreater(sf.begin_decreases_height_in_rows, 0)
        self.assertGreater(sf.hem_to_waist_in_rows, 0)
        self.assertGreater(sf.last_decrease_to_waist_in_rows, 0)
        self.assertGreater(sf.hem_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_neckline_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_increase_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_increase_to_neckline_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_decrease_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_decrease_to_neckline_in_rows(RCP.WS), 0)
        self.assertGreater(sf.hem_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.hem_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.last_increase_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_increase_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_increase_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.last_decrease_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_decrease_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_decrease_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.hem_to_shoulders_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_shoulders_in_rows(RCP.WS), 0)
        self.assertEqual(sf.armhole_to_neckline_in_rows(RCP.RS, RCP.RS), 14)
        self.assertEqual(sf.armhole_to_neckline_in_rows(RCP.WS, RCP.RS), 15)
        self.assertEqual(sf.armhole_to_neckline_in_rows(RCP.RS, RCP.WS), 13)
        self.assertEqual(sf.armhole_to_neckline_in_rows(RCP.WS, RCP.WS), 14)
        self.assertGreater(sf.first_armhole_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.first_armhole_to_neckline_in_rows(RCP.WS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.RS, RCP.WS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.WS, RCP.WS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.RS, RCP.RS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.WS, RCP.RS), 0)

        self.assertIsNone(sf.neckline_to_armhole_in_rows(RCP.RS, RCP.WS))
        self.assertIsNone(sf.neckline_to_armhole_in_rows(RCP.WS, RCP.WS))
        self.assertIsNone(sf.neckline_to_armhole_in_rows(RCP.RS, RCP.RS))
        self.assertIsNone(sf.neckline_to_armhole_in_rows(RCP.WS, RCP.RS))

        self.assertEqual(sf.cross_chest_stitches, 72)

    def test_row_count_neck_below_armhole(self):
        pspec = SweaterPatternSpecFactory(
            neckline_depth=4, neckline_depth_orientation=SDC.BELOW_ARMPIT
        )
        sf = make_sweaterfront_from_pspec(pspec)

        self.assertGreater(sf.waist_hem_height_in_rows, 0)
        self.assertGreater(sf.begin_decreases_height_in_rows, 0)
        self.assertGreater(sf.hem_to_waist_in_rows, 0)
        self.assertGreater(sf.last_decrease_to_waist_in_rows, 0)
        self.assertGreater(sf.hem_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_neckline_in_rows(RCP.WS), 0)
        self.assertGreater(sf.hem_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.hem_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.last_increase_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_increase_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_increase_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.last_decrease_to_armhole_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_decrease_to_armhole_in_rows(RCP.WS), 0)
        self.assertGreater(sf.last_decrease_to_first_armhole_in_rows, 0)
        self.assertGreater(sf.hem_to_shoulders_in_rows(RCP.RS), 0)
        self.assertGreater(sf.hem_to_shoulders_in_rows(RCP.WS), 0)

        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.RS, RCP.WS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.WS, RCP.WS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.RS, RCP.RS), 0)
        self.assertGreater(sf.armhole_to_shoulders_in_rows(RCP.WS, RCP.RS), 0)
        self.assertGreater(sf.neckline_to_armhole_in_rows(RCP.RS, RCP.WS), 0)
        self.assertGreater(sf.neckline_to_armhole_in_rows(RCP.WS, RCP.WS), 0)
        self.assertGreater(sf.neckline_to_armhole_in_rows(RCP.RS, RCP.RS), 0)
        self.assertGreater(sf.neckline_to_armhole_in_rows(RCP.WS, RCP.RS), 0)

        self.assertGreater(sf.last_decrease_to_neckline_in_rows(RCP.RS), 0)
        self.assertGreater(sf.last_decrease_to_neckline_in_rows(RCP.WS), 0)
        self.assertIsNone(sf.last_increase_to_neckline_in_rows(RCP.RS))
        self.assertIsNone(sf.last_increase_to_neckline_in_rows(RCP.WS))
        self.assertIsNone(sf.armhole_to_neckline_in_rows(RCP.RS, RCP.RS))
        self.assertIsNone(sf.armhole_to_neckline_in_rows(RCP.WS, RCP.RS))
        self.assertIsNone(sf.armhole_to_neckline_in_rows(RCP.RS, RCP.WS))
        self.assertIsNone(sf.armhole_to_neckline_in_rows(RCP.WS, RCP.WS))
        self.assertIsNone(sf.first_armhole_to_neckline_in_rows(RCP.RS))
        self.assertIsNone(sf.first_armhole_to_neckline_in_rows(RCP.WS))

        self.assertIsNone(sf.cross_chest_stitches)

    def test_stitches(self):
        sf = create_sweater_front()

        self.assertEqual(sf.allover_stitch, StitchFactory(name="Other Stitch"))
        self.assertIsNone(sf.caston_repeats(), None)

    def test_repeats(self):

        # For comparison
        pspec = SweaterPatternSpecFactory()
        sf = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf.cast_ons, 98)

        # Note: Cabled check is 1 mod 4
        # one-by-one rib does not use repeats
        pspec = SweaterPatternSpecFactory(
            front_allover_stitch=StitchFactory(name="Cabled Check Stitch"),
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        sf = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf.cast_ons % 4, 1)

        repeats_swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=3, additional_stitches=1
        )
        pspec = SweaterPatternSpecFactory(
            front_allover_stitch=StitchFactory(name="Stockinette"),
            swatch=repeats_swatch,
        )
        sf = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf.cast_ons % 3, 1)

        # Open mesh lace is 0 mod 3
        pspec = SweaterPatternSpecFactory(
            front_allover_stitch=StitchFactory(name="Stockinette"),
            hip_edging_stitch=StitchFactory(name="Open Mesh Lace"),
        )
        sf = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf.cast_ons % 3, 0)

    def test_half_hourglass(self):

        # For comparison
        pspec = SweaterPatternSpecFactory()
        sf1 = make_sweaterfront_from_pspec(pspec)
        self.assertGreater(sf1.cast_ons, sf1.waist_stitches)
        self.assertGreater(sf1.bust_stitches, sf1.waist_stitches)

        pspec = SweaterPatternSpecFactory(silhouette=SDC.SILHOUETTE_HALF_HOURGLASS)
        sf2 = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf2.cast_ons, sf2.waist_stitches)
        self.assertEqual(sf2.bust_stitches, sf2.waist_stitches)

    def test_half_hourglass_error_case(self):

        swatch = SwatchFactory(
            stitches_number=31, stitches_length=6.25, rows_number=31, rows_length=4.5
        )

        body_dict = {
            "name": "error-case body",
            "waist_circ": 32,
            "bust_circ": 41.25,
            "upper_torso_circ": 37.75,
            "wrist_circ": 6.5,
            "forearm_circ": 9.5,
            "bicep_circ": 12,
            "elbow_circ": 11,
            "armpit_to_short_sleeve": 3,
            "armpit_to_elbow_sleeve": 6.5,
            "armpit_to_three_quarter_sleeve": 11.5,
            "armpit_to_full_sleeve": 18,
            "inter_nipple_distance": 7.75,
            "armpit_to_waist": 8.75,
            "armhole_depth": 8,
            "armpit_to_high_hip": 8.75 + 5.5,
            "armpit_to_med_hip": 8.75 + 7,
            "armpit_to_low_hip": 8.75 + 8.5,
            "armpit_to_tunic": 8.75 + 11,
            "high_hip_circ": 38,
            "med_hip_circ": 39.5,
            "low_hip_circ": 40,
            "tunic_circ": 41,
        }
        body = BodyFactory(**body_dict)

        design_dict = {
            "name": "error-case design",
            "garment_type": SDC.PULLOVER_SLEEVED,
            "sleeve_length": SDC.SLEEVE_FULL,
            "sleeve_shape": SDC.SLEEVE_TAPERED,
            "neckline_style": SDC.NECK_VEE,
            "torso_length": SDC.LOW_HIP_LENGTH,
            "neckline_width": SDC.NECK_AVERAGE,
            "neckline_depth": 3,
            "neckline_depth_orientation": SDC.BELOW_ARMPIT,
            "silhouette": SDC.SILHOUETTE_HALF_HOURGLASS,
            "back_allover_stitch": StitchFactory(name="Stockinette"),
            "front_allover_stitch": StitchFactory(name="Cabled Check Stitch"),
            "sleeve_allover_stitch": StitchFactory(name="Stockinette"),
            "hip_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "hip_edging_height": 2,
            "sleeve_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "sleeve_edging_height": 2,
            "button_band_edging_stitch": None,
            "button_band_edging_height": None,
            "button_band_allowance": None,
            "number_of_buttons": None,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "neck_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "neck_edging_height": 1.5,
            "armhole_edging_stitch": None,
            "armhole_edging_height": None,
            "body": body,
            "swatch": swatch,
        }
        pspec = SweaterPatternSpecFactory(**design_dict)
        sf = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf.cast_ons, sf.waist_stitches)
        self.assertEqual(sf.bust_stitches, sf.waist_stitches)

    def test_is_piece_methods(self):
        piece = create_sweater_front()
        self.assertFalse(piece.is_sweater_back)
        self.assertFalse(piece.is_vest_back)
        self.assertTrue(piece.is_sweater_front)
        self.assertFalse(piece.is_vest_front)
        self.assertFalse(piece.is_cardigan_sleeved)
        self.assertFalse(piece.is_cardigan_vest)

    def test_cross_chest_stitches(self):
        # Check the current implementation: this is None if necklines
        # go below the armhole shaping, valid number otherwise

        pspec1 = SweaterPatternSpecFactory(
            neckline_depth=1, neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )
        sf1 = make_sweaterfront_from_pspec(pspec1)
        self.assertEqual(sf1.bust_stitches, 102)
        self.assertEqual(sf1.armhole_n, 15)
        self.assertEqual(sf1.cross_chest_stitches, 72)

        pspec2 = SweaterPatternSpecFactory(
            neckline_depth=0.5, neckline_depth_orientation=SDC.BELOW_ARMPIT
        )
        sf2 = make_sweaterfront_from_pspec(pspec2)
        self.assertEqual(sf2.bust_stitches, 102)
        self.assertEqual(sf2.armhole_n, 15)
        self.assertIsNone(sf2.cross_chest_stitches)

        pspec3 = SweaterPatternSpecFactory(
            neckline_depth=4.0, neckline_depth_orientation=SDC.BELOW_ARMPIT
        )
        sf3 = make_sweaterfront_from_pspec(pspec3)
        self.assertIsNone(sf3.bust_stitches)
        self.assertIsNone(sf3.cross_chest_stitches)

    def test_cables(self):

        #
        # Control/comparison
        #
        pspec = SweaterPatternSpecFactory(neckline_style=SDC.NECK_CREW)
        sf_control = make_sweaterfront_from_pspec(pspec)
        self.assertEqual(sf_control.cast_ons, 98)
        self.assertEqual(sf_control.inter_marker, 48)
        self.assertEqual(sf_control.waist_inter_double_marker, None)
        self.assertEqual(sf_control.waist_stitches, 88)
        self.assertEqual(sf_control.bust_inter_double_dart_markers, None)
        self.assertEqual(sf_control.bust_inter_standard_dart_markers, 48)
        self.assertEqual(sf_control.bust_inter_triple_dart_markers, None)
        self.assertEqual(sf_control.bust_stitches, 102)
        self.assertEqual(sf_control._bust_stitches_internal_use, 102)
        self.assertEqual(sf_control.armhole_x, 5)
        self.assertEqual(sf_control.armhole_y, 3)
        self.assertEqual(sf_control.armhole_z, 7)
        self.assertEqual(sf_control.first_shoulder_bindoff, 9)
        self.assertEqual(sf_control.num_shoulder_stitches, 17)
        self.assertEqual(sf_control.actual_hip, 19.600000000000001)
        self.assertEqual(sf_control.actual_waist, 17.600000000000001)
        self.assertEqual(sf_control.actual_bust, 20.399999999999999)
        self.assertAlmostEqual(sf_control.area(), 393.2, 1)
        self.assertEqual(sf_control.actual_neck_opening_width, 7.6)
        self.assertEqual(sf_control.cross_chest_stitches, 72)
        self.assertEqual(sf_control.neckline.stitches_across_neckline(), 38)

        #
        # Positive extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=5,
            neckline_style=SDC.NECK_CREW,
        )
        sf = make_sweaterfront_from_pspec(pspec)
        # should grow
        self.assertEqual(sf.cast_ons, 103)
        self.assertEqual(sf.inter_marker, 53)
        self.assertEqual(sf.waist_inter_double_marker, None)
        self.assertEqual(sf.waist_stitches, 93)
        self.assertEqual(sf.bust_inter_double_dart_markers, None)
        self.assertEqual(sf.bust_inter_standard_dart_markers, 53)
        self.assertEqual(sf.bust_inter_triple_dart_markers, None)
        self.assertEqual(sf.bust_stitches, 107)
        self.assertEqual(sf.cross_chest_stitches, 77)
        self.assertEqual(sf._bust_stitches_internal_use, 107)
        self.assertEqual(sf.neckline.stitches_across_neckline(), 43)

        extra_area = (
            5
            * sf.hem_to_neckline_shaping_start
            / sf.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        self.assertLessEqual(abs(sf.area() - (sf_control.area() + extra_area)), 2)

        # Should stay unchanged
        self.assertEqual(sf.armhole_x, sf_control.armhole_x)
        self.assertEqual(sf.armhole_y, sf_control.armhole_y)
        self.assertEqual(sf.armhole_z, sf_control.armhole_z)
        self.assertEqual(sf.first_shoulder_bindoff, sf_control.first_shoulder_bindoff)
        self.assertEqual(sf.num_shoulder_stitches, sf_control.num_shoulder_stitches)
        self.assertEqual(sf.actual_hip, sf_control.actual_hip)
        self.assertEqual(sf.actual_waist, sf_control.actual_waist)
        self.assertEqual(sf.actual_bust, sf_control.actual_bust)
        self.assertEqual(
            sf.actual_neck_opening_width, sf_control.actual_neck_opening_width
        )

        #
        # zero extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=0,
            neckline_style=SDC.NECK_CREW,
        )
        sf = make_sweaterfront_from_pspec(pspec)
        # should grow
        self.assertEqual(sf.cast_ons, sf_control.cast_ons)
        self.assertEqual(sf.inter_marker, sf_control.inter_marker)
        self.assertEqual(
            sf.waist_inter_double_marker, sf_control.waist_inter_double_marker
        )
        self.assertEqual(sf.waist_stitches, sf_control.waist_stitches)
        self.assertEqual(
            sf.bust_inter_double_dart_markers, sf_control.bust_inter_double_dart_markers
        )
        self.assertEqual(
            sf.bust_inter_standard_dart_markers,
            sf_control.bust_inter_standard_dart_markers,
        )
        self.assertEqual(
            sf.bust_inter_triple_dart_markers, sf_control.bust_inter_triple_dart_markers
        )
        self.assertEqual(sf.bust_stitches, sf_control.bust_stitches)
        self.assertEqual(sf.cross_chest_stitches, sf_control.cross_chest_stitches)
        self.assertEqual(
            sf._bust_stitches_internal_use, sf_control._bust_stitches_internal_use
        )
        self.assertEqual(
            sf.neckline.stitches_across_neckline(),
            sf_control.neckline.stitches_across_neckline(),
        )

        self.assertEqual(sf.area(), sf_control.area())

        # Should stay unchanged
        self.assertEqual(sf.armhole_x, sf_control.armhole_x)
        self.assertEqual(sf.armhole_y, sf_control.armhole_y)
        self.assertEqual(sf.armhole_z, sf_control.armhole_z)
        self.assertEqual(sf.first_shoulder_bindoff, sf_control.first_shoulder_bindoff)
        self.assertEqual(sf.num_shoulder_stitches, sf_control.num_shoulder_stitches)
        self.assertEqual(sf.actual_hip, sf_control.actual_hip)
        self.assertEqual(sf.actual_waist, sf_control.actual_waist)
        self.assertEqual(sf.actual_bust, sf_control.actual_bust)
        self.assertEqual(
            sf.actual_neck_opening_width, sf_control.actual_neck_opening_width
        )

        #
        # Negative extra stitches
        #
        pspec = SweaterPatternSpecFactory(
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=-5,
            neckline_style=SDC.NECK_CREW,
        )
        sf = make_sweaterfront_from_pspec(pspec)
        # should grow
        self.assertEqual(sf.cast_ons, 93)
        self.assertEqual(sf.inter_marker, 43)
        self.assertEqual(sf.waist_inter_double_marker, None)
        self.assertEqual(sf.waist_stitches, 83)
        self.assertEqual(sf.bust_inter_double_dart_markers, None)
        self.assertEqual(sf.bust_inter_standard_dart_markers, 43)
        self.assertEqual(sf.bust_inter_triple_dart_markers, None)
        self.assertEqual(sf.bust_stitches, 97)
        self.assertEqual(sf.cross_chest_stitches, 67)
        self.assertEqual(sf._bust_stitches_internal_use, 97)
        self.assertEqual(sf.neckline.stitches_across_neckline(), 33)

        extra_area = (
            5
            * sf.hem_to_neckline_shaping_start
            / sf.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        self.assertLessEqual(abs(sf.area() - (sf_control.area() - extra_area)), 1)

        # Should stay unchanged
        self.assertEqual(sf.armhole_x, sf_control.armhole_x)
        self.assertEqual(sf.armhole_y, sf_control.armhole_y)
        self.assertEqual(sf.armhole_z, sf_control.armhole_z)
        self.assertEqual(sf.first_shoulder_bindoff, sf_control.first_shoulder_bindoff)
        self.assertEqual(sf.num_shoulder_stitches, sf_control.num_shoulder_stitches)
        self.assertEqual(sf.actual_hip, sf_control.actual_hip)
        self.assertEqual(sf.actual_waist, sf_control.actual_waist)
        self.assertEqual(sf.actual_bust, sf_control.actual_bust)
        self.assertEqual(
            sf.actual_neck_opening_width, sf_control.actual_neck_opening_width
        )

    def test_straight_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterfront_from_pspec(pspec)

    def test_aline_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterfront_from_pspec(pspec)

    def test_tapered_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterfront_from_pspec(pspec)

    def test_hourglass_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterfront_from_pspec(pspec)

    def test_half_hourglass_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        make_sweaterfront_from_pspec(pspec)

    def test_drop_shoulder(self):
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        sf = make_sweaterfront_from_pspec(pspec)

        self.assertEqual(pspec.swatch.get_gauge().stitches, 5)

        self.assertEqual(sf.armhole_x, 3)
        self.assertEqual(sf.armhole_y, 0)
        self.assertEqual(sf.armhole_z, 0)
        self.assertAlmostEqual(sf.actual_armhole_circumference, 9.957, 2)
        self.assertEqual(sf.hem_to_armhole_shaping_start, 14.5)
        self.assertEqual(sf.hem_to_shoulders, 24)

        self.assertEqual(sf.armhole_n, 3)
        self.assertAlmostEqual(sf.area(), 502.7, 3)

        self.assertEqual(sf.rows_in_armhole_shaping_pullover(RCP.WS), 2)
        self.assertEqual(sf.rows_in_armhole_shaping_pullover(RCP.RS), 2)
        self.assertEqual(sf.rows_in_armhole_shaping_cardigan(RCP.WS), 1)
        self.assertEqual(sf.rows_in_armhole_shaping_cardigan(RCP.RS), 1)


class CardiganSleevedTest(django.test.TestCase):

    longMessage = True

    def setUp(self):

        StitchFactory(
            name="2x2 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
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

    def test_cardigan_sleeved_regression1(self):
        cs = create_cardigan_sleeved()
        cs.clean()
        self.assertEqual(cs.cast_ons, 49)
        self.assertEqual(cs.pre_marker, 25)
        self.assertEqual(cs.post_marker, 25)
        self.assertEqual(cs.inter_marker, 24)
        self.assertEqual(cs.waist_hem_height, 1.5)
        self.assertEqual(cs.has_waist_decreases, True)
        self.assertFalse(cs.any_waist_decreases_on_ws)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 5)
        self.assertEqual(cs.num_waist_double_dart_rows, 0)
        self.assertEqual(cs.num_waist_triple_dart_rows, 0)
        self.assertEqual(cs.num_bust_standard_increase_rows, 7)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(cs.num_bust_triple_dart_rows, 0)
        self.assertEqual(cs.num_waist_decrease_rows_knitter_instructions, 5)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 5)
        self.assertEqual(cs.num_waist_standard_decrease_repetitions, 4)
        self.assertEqual(cs.rows_between_waist_standard_decrease_rows, 5)
        self.assertEqual(cs.waist_double_darts, False)
        self.assertEqual(cs.waist_double_dart_marker, None)
        self.assertEqual(cs.waist_inter_double_marker, None)
        self.assertEqual(cs.num_waist_double_dart_decrease_repetitions, None)
        self.assertEqual(cs.num_waist_non_double_dart_decrease_repetitions, None)
        self.assertEqual(
            cs.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(cs.waist_triple_darts, False)
        self.assertEqual(cs.waist_triple_dart_marker, None)
        self.assertEqual(cs.waist_inter_triple_marker, None)
        self.assertEqual(cs.num_waist_triple_dart_repetitions, None)
        self.assertEqual(cs.begin_decreases_height, 2.9285714285714284)
        self.assertEqual(cs.hem_to_waist, 7.5)
        self.assertEqual(cs.waist_stitches, 44)
        self.assertEqual(cs.has_bust_increases, True)
        self.assertFalse(cs.any_bust_increases_on_ws)
        self.assertEqual(cs.num_bust_increase_rows_knitter_instructions, 7)
        self.assertEqual(cs.num_bust_standard_increase_rows, 7)
        self.assertEqual(cs.num_bust_standard_increase_repetitions, 6)
        self.assertEqual(cs.rows_between_bust_standard_increase_rows, 7)
        self.assertEqual(cs.bust_pre_standard_dart_marker, 20)
        self.assertEqual(cs.bust_double_darts, False)
        self.assertEqual(cs.bust_pre_double_dart_marker, None)
        self.assertEqual(cs.bust_inter_double_dart_markers, None)
        self.assertEqual(cs.bust_inter_double_and_standard_dart_markers, None)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(cs.num_bust_non_double_dart_increase_repetitions, None)
        self.assertEqual(
            cs.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(cs.bust_triple_darts, False)
        self.assertEqual(cs.bust_pre_triple_dart_marker, None)
        self.assertEqual(cs.bust_inter_triple_dart_markers, None)
        self.assertEqual(cs.bust_inter_double_and_triple_dart_markers, None)
        self.assertEqual(cs.num_bust_triple_dart_repetitions, None)
        self.assertEqual(cs.hem_to_bust_increase_end, 14.5)
        self.assertEqual(cs.hem_to_armhole_shaping_start, 16)
        self.assertEqual(cs.armhole_x, 5)
        self.assertEqual(cs.armhole_y, 3)
        self.assertEqual(cs.armhole_z, 7)
        self.assertEqual(cs.hem_to_neckline_shaping_start, 18)
        self.assertAlmostEqual(cs.hem_to_neckline_shaping_end, 23.57, 2)
        self.assertEqual(cs.hem_to_shoulders, 24)
        self.assertEqual(cs.first_shoulder_bindoff, 9)
        self.assertEqual(cs.second_shoulder_bindoff, 8)
        self.assertEqual(cs.num_shoulder_stitches, 17)
        self.assertEqual(cs.actual_hip, 9.8000000000000007)
        self.assertEqual(cs.actual_waist, 8.8000000000000007)
        self.assertEqual(cs.actual_bust, 10.199999999999999)
        self.assertEqual(cs.actual_armhole_depth, 8)
        self.assertEqual(cs.actual_shoulder_stitch_width, 3.3999999999999999)
        self.assertAlmostEqual(cs.actual_armhole_circumference, 9.7555, 2)
        self.assertEqual(cs.hem_to_waist, 7.5)
        self.assertEqual(cs.actual_hem_to_armhole, 16)
        self.assertEqual(cs.actual_waist_to_armhole, 8.5)
        self.assertEqual(cs.actual_hem_to_shoulder, 24)
        self.assertEqual(cs.bust_use_standard_markers, True)

        self.assertAlmostEqual(cs.area(), 435.2, 1)
        self.assertEqual(cs.actual_button_band_allowance, 0)
        self.assertEqual(cs.actual_button_band_height, 0)
        self.assertEqual(cs.total_front_finished_bust, 20.4)
        self.assertEqual(cs.total_front_finished_hip, 19.6)
        self.assertEqual(cs.total_front_finished_waist, 17.6)

        self.assertEqual(cs.total_front_cast_ons, 98)
        self.assertEqual(cs.neckline.stitches_to_pick_up(), 72)
        self.assertEqual(cs.total_neckline_stitches_to_pick_up(), 72)

        self.assertEqual(cs.actual_neck_opening_width, 7.6)

        self.assertEqual(cs.cross_chest_stitches, 36)

        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.RS), 113)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.RS), 16)
        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.WS), 112)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.WS), 17)

        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.RS), 127)
        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.WS), 126)

        # Neckline starts before armhole shaping end
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.RS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.RS))

    def test_cardigan_sleeved_regression2(self):
        user = UserFactory()
        swatch = SwatchFactory(rows_number=4, stitches_number=10)
        body = get_csv_body("Test 5")
        pspec = SweaterPatternSpecFactory(
            body=body,
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            button_band_allowance=0,
            button_band_edging_height=0,
        )
        pspec.full_clean()
        cs = make_cardigan_sleeved_from_pspec(pspec)
        cs.clean()

        self.assertEqual(cs.cast_ons, 83)
        self.assertEqual(cs.pre_marker, 41)
        self.assertEqual(cs.post_marker, 41)
        self.assertEqual(cs.inter_marker, 42)
        self.assertEqual(cs.waist_hem_height, 1.5)
        self.assertEqual(cs.has_waist_decreases, True)
        self.assertFalse(cs.any_waist_decreases_on_ws)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 1)
        self.assertEqual(cs.num_waist_double_dart_rows, 3)
        self.assertEqual(cs.num_waist_triple_dart_rows, 3)
        self.assertEqual(cs.num_bust_standard_increase_rows, 2)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(cs.num_bust_triple_dart_rows, 4)
        self.assertEqual(cs.num_waist_decrease_rows_knitter_instructions, 7)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 1)
        self.assertEqual(cs.num_waist_standard_decrease_repetitions, 0)
        self.assertEqual(cs.rows_between_waist_standard_decrease_rows, 3)
        self.assertEqual(cs.waist_double_darts, True)
        self.assertEqual(cs.waist_double_dart_marker, 20)
        self.assertEqual(cs.waist_inter_double_marker, 21)
        self.assertEqual(cs.num_waist_double_dart_decrease_repetitions, 2)
        self.assertEqual(cs.num_waist_non_double_dart_decrease_repetitions, 0)
        self.assertEqual(
            cs.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(cs.waist_triple_darts, True)
        self.assertEqual(cs.waist_triple_dart_marker, 10)
        self.assertEqual(cs.waist_inter_triple_marker, 10)
        self.assertEqual(cs.num_waist_triple_dart_repetitions, 2)
        self.assertEqual(cs.begin_decreases_height, 2.75)
        self.assertEqual(cs.hem_to_waist, 7)
        self.assertEqual(cs.waist_stitches, 73)
        self.assertEqual(cs.has_bust_increases, True)
        self.assertFalse(cs.any_bust_increases_on_ws)
        self.assertEqual(cs.num_bust_increase_rows_knitter_instructions, 11)
        self.assertEqual(cs.num_bust_standard_increase_rows, 2)
        self.assertEqual(cs.num_bust_standard_increase_repetitions, 1)
        self.assertEqual(cs.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(cs.bust_pre_standard_dart_marker, 34)
        self.assertEqual(cs.bust_double_darts, True)
        self.assertEqual(cs.bust_pre_double_dart_marker, 14)
        self.assertEqual(cs.bust_inter_double_dart_markers, 59)
        self.assertEqual(cs.bust_inter_double_and_standard_dart_markers, 20)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 5)
        self.assertEqual(cs.num_bust_non_double_dart_increase_repetitions, 0)
        self.assertEqual(
            cs.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(cs.bust_triple_darts, True)
        self.assertEqual(cs.bust_pre_triple_dart_marker, 7)
        self.assertEqual(cs.bust_inter_triple_dart_markers, 66)
        self.assertEqual(cs.bust_inter_double_and_triple_dart_markers, 7)
        self.assertEqual(cs.num_bust_triple_dart_repetitions, 3)
        self.assertEqual(cs.hem_to_bust_increase_end, 12.25)
        self.assertEqual(cs.hem_to_armhole_shaping_start, 13.5)
        self.assertEqual(cs.armhole_x, 10)
        self.assertEqual(cs.armhole_y, 9)
        self.assertEqual(cs.armhole_z, 2)
        self.assertEqual(cs.hem_to_neckline_shaping_start, 11.5)
        self.assertEqual(cs.hem_to_neckline_shaping_end, 20.5)
        self.assertEqual(cs.hem_to_shoulders, 20.5)
        self.assertEqual(cs.first_shoulder_bindoff, 17)
        self.assertEqual(cs.second_shoulder_bindoff, 16)
        self.assertEqual(cs.num_shoulder_stitches, 33)
        self.assertEqual(cs.actual_hip, 8.3000000000000007)
        self.assertEqual(cs.actual_waist, 7.2999999999999998)
        self.assertEqual(cs.actual_bust, 8.8000000000000007)
        self.assertEqual(cs.actual_armhole_depth, 7)
        self.assertEqual(cs.actual_shoulder_stitch_width, 3.2999999999999998)
        self.assertAlmostEqual(cs.actual_armhole_circumference, 8.4198, 2)
        self.assertEqual(cs.hem_to_waist, 7)
        self.assertEqual(cs.actual_hem_to_armhole, 13.5)
        self.assertEqual(cs.actual_waist_to_armhole, 6.5)
        self.assertEqual(cs.actual_hem_to_shoulder, 20.5)
        self.assertEqual(cs.bust_use_standard_markers, True)

        self.assertAlmostEqual(cs.area(), 324.65, 1)
        self.assertEqual(cs.actual_button_band_allowance, -0.1)
        self.assertEqual(cs.actual_button_band_height, -0.1)
        self.assertEqual(cs.total_front_finished_bust, 17.5)
        self.assertEqual(cs.total_front_finished_hip, 16.5)
        self.assertEqual(cs.total_front_finished_waist, 14.5)

        self.assertEqual(cs.total_front_cast_ons, 166)
        self.assertEqual(cs.neckline.stitches_to_pick_up(), 193)
        self.assertEqual(cs.total_neckline_stitches_to_pick_up(), 193)

        self.assertEqual(cs.actual_neck_opening_width, 6.7)

        self.assertIsNone(cs.cross_chest_stitches)

        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.RS), 55)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.RS), 6)
        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.WS), 54)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.WS), 7)

        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.RS), 47)
        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.WS), 46)

        # Neckline starts  before armhole shaping end
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.RS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.RS))

    def test_cardigan_sleeved_empty_neckline_regression1(self):

        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)

        # First, get a reference neckline-width (in stitches)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            button_band_edging_height=1,
            button_band_allowance=None,
            button_band_allowance_percentage=100,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        cs.clean()

        # Sanity checks before we go on
        self.assertTrue(cs.neckline.empty())
        self.assertIsNone(cs.neckline.total_depth())

        self.assertEqual(cs.cast_ons, 30)
        self.assertEqual(cs.pre_marker, 25)
        self.assertEqual(cs.post_marker, 25)
        self.assertEqual(cs.inter_marker, 5)
        self.assertEqual(cs.waist_hem_height, 1.5)
        self.assertEqual(cs.has_waist_decreases, True)
        self.assertFalse(cs.any_waist_decreases_on_ws)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 5)
        self.assertEqual(cs.num_waist_double_dart_rows, 0)
        self.assertEqual(cs.num_waist_triple_dart_rows, 0)
        self.assertEqual(cs.num_bust_standard_increase_rows, 7)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(cs.num_bust_triple_dart_rows, 0)
        self.assertEqual(cs.num_waist_decrease_rows_knitter_instructions, 5)
        self.assertEqual(cs.num_waist_standard_decrease_rows, 5)
        self.assertEqual(cs.num_waist_standard_decrease_repetitions, 4)
        self.assertEqual(cs.rows_between_waist_standard_decrease_rows, 7)
        self.assertEqual(cs.waist_double_darts, False)
        self.assertEqual(cs.waist_double_dart_marker, None)
        self.assertEqual(cs.waist_inter_double_marker, None)
        self.assertEqual(cs.num_waist_double_dart_decrease_repetitions, None)
        self.assertEqual(cs.num_waist_non_double_dart_decrease_repetitions, None)
        self.assertEqual(
            cs.num_waist_non_double_dart_decrease_repetitions_minus_one, None
        )
        self.assertEqual(cs.waist_triple_darts, False)
        self.assertEqual(cs.waist_triple_dart_marker, None)
        self.assertEqual(cs.waist_inter_triple_marker, None)
        self.assertEqual(cs.num_waist_triple_dart_repetitions, None)
        self.assertEqual(cs.begin_decreases_height, 2.375)
        self.assertEqual(cs.hem_to_waist, 7.5)
        self.assertEqual(cs.waist_stitches, 25)
        self.assertEqual(cs.has_bust_increases, True)
        self.assertEqual(cs.num_bust_increase_rows_knitter_instructions, 7)
        self.assertEqual(cs.num_bust_standard_increase_rows, 7)
        self.assertEqual(cs.num_bust_standard_increase_repetitions, 6)
        self.assertEqual(cs.rows_between_bust_standard_increase_rows, 7)
        self.assertEqual(cs.bust_pre_standard_dart_marker, 20)
        self.assertEqual(cs.bust_double_darts, False)
        self.assertEqual(cs.bust_pre_double_dart_marker, None)
        self.assertEqual(cs.bust_inter_double_dart_markers, None)
        self.assertEqual(cs.bust_inter_double_and_standard_dart_markers, None)
        self.assertEqual(cs.num_bust_double_dart_increase_rows, 0)
        self.assertEqual(cs.num_bust_non_double_dart_increase_repetitions, None)
        self.assertEqual(
            cs.num_bust_non_double_dart_increase_repetitions_minus_one, None
        )
        self.assertEqual(cs.bust_triple_darts, False)
        self.assertEqual(cs.bust_pre_triple_dart_marker, None)
        self.assertEqual(cs.bust_inter_triple_dart_markers, None)
        self.assertEqual(cs.bust_inter_double_and_triple_dart_markers, None)
        self.assertEqual(cs.num_bust_triple_dart_repetitions, None)
        self.assertEqual(cs.hem_to_bust_increase_end, 13.625)
        self.assertEqual(cs.hem_to_armhole_shaping_start, 16)
        self.assertEqual(cs.armhole_x, 4)
        self.assertEqual(cs.armhole_y, 2)
        self.assertEqual(cs.armhole_z, 9)
        self.assertEqual(cs.hem_to_neckline_shaping_start, None)
        self.assertEqual(cs.hem_to_neckline_shaping_end, None)
        self.assertEqual(cs.hem_to_shoulders, 24)
        self.assertEqual(cs.first_shoulder_bindoff, 9)
        self.assertEqual(cs.second_shoulder_bindoff, 8)
        self.assertEqual(cs.num_shoulder_stitches, 17)
        self.assertEqual(cs.actual_hip, 6.0)
        self.assertEqual(cs.actual_waist, 5)
        self.assertEqual(cs.actual_bust, 6.4)
        self.assertEqual(cs.actual_armhole_depth, 8)
        self.assertEqual(cs.actual_shoulder_stitch_width, 3.3999999999999999)
        self.assertAlmostEqual(cs.actual_armhole_circumference, 9.5814, 2)
        self.assertEqual(cs.hem_to_waist, 7.5)
        self.assertEqual(cs.actual_hem_to_armhole, 16)
        self.assertEqual(cs.actual_waist_to_armhole, 8.5)
        self.assertEqual(cs.actual_hem_to_shoulder, 24)
        self.assertEqual(cs.bust_use_standard_markers, True)

        self.assertAlmostEqual(cs.area(), 252.8, 1)
        self.assertEqual(cs.actual_button_band_allowance, 7.6)
        self.assertEqual(cs.actual_button_band_height, 1)
        # Note: becuase the cardigan has buttons, we use the trim-height instead of actual allowance to
        # compute widths
        self.assertEqual(cs.total_front_finished_bust, 13.8)
        self.assertEqual(cs.total_front_finished_hip, 13.0)
        self.assertEqual(cs.total_front_finished_waist, 11.0)

        self.assertEqual(cs.total_front_cast_ons, 60)
        self.assertEqual(cs.neckline.stitches_to_pick_up(), 0)
        self.assertEqual(cs.total_neckline_stitches_to_pick_up(), 0)

        self.assertEqual(cs.cross_chest_stitches, 17)

        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.RS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.WS))
        self.assertIsNone(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.RS))

    def test_button_band_regression1(self):

        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        bb = cs.make_buttonband()

        self.assertEqual(cs.hem_to_neckline_shaping_start, 18)
        self.assertEqual(cs.gauge.stitches, 5)
        self.assertEqual(cs.actual_button_band_allowance, 0.8)
        self.assertEqual(cs.actual_button_band_height, 0.8)
        self.assertEqual(cs.actual_bust, 9.8)
        self.assertAlmostEqual(cs.total_front_finished_bust, 20.6, 1)

        self.assertEqual(bb.height, 1)
        self.assertEqual(bb.stitch_pattern, StitchFactory(name="1x1 Ribbing"))
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.evenly_spaced_buttonholes, True)
        self.assertEqual(bb.num_buttonholes, 6)
        self.assertEqual(bb.margin_stitches, 4)
        self.assertEqual(bb.inter_buttonhole_stitches, 14)

        # methods
        self.assertEqual(bb.half_height(), 0.5)
        self.assertEqual(bb.edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(bb.stitches_before_first_buttonhole(), 4)
        self.assertEqual(bb.num_interior_buttonholes(), 4)

    def test_neckline_after_armhole_ends(self):

        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)

        # First, get a reference neckline-width (in stitches)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            neckline_depth=2,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            button_band_edging_height=1,
            button_band_allowance=3,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        cs.clean()

        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.RS), 129)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.RS), 20)
        self.assertEqual(cs.hem_to_armhole_in_rows(RCP.WS), 128)
        self.assertEqual(cs.rows_in_armhole_shaping_cardigan(RCP.WS), 21)

        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.RS), 177)
        self.assertEqual(cs.hem_to_neckline_in_rows(RCP.WS), 176)

        # Neckline starts  before armhole shaping end
        self.assertEqual(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.WS), 28)
        self.assertEqual(cs.last_armhole_to_neckline_in_rows(RCP.WS, RCP.RS), 29)
        self.assertEqual(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.WS), 28)
        self.assertEqual(cs.last_armhole_to_neckline_in_rows(RCP.RS, RCP.RS), 29)

    def test_button_band_regression2(self):

        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        bb = cs.make_buttonband()

        self.assertEqual(cs.hem_to_neckline_shaping_start, 18)
        self.assertEqual(cs.gauge.stitches, 5)
        self.assertEqual(cs.actual_button_band_allowance, 0.8)
        self.assertEqual(cs.actual_button_band_height, 0.8)
        self.assertEqual(cs.actual_bust, 9.8)
        self.assertAlmostEqual(cs.total_front_finished_bust, 20.6, 1)

        self.assertEqual(bb.height, 1)
        self.assertEqual(bb.stitch_pattern, StitchFactory(name="1x1 Ribbing"))
        self.assertEqual(bb.stitches, 90)
        self.assertEqual(bb.evenly_spaced_buttonholes, False)
        self.assertEqual(bb.num_buttonholes, 2)
        self.assertEqual(bb.margin_stitches, None)
        self.assertEqual(bb.inter_buttonhole_stitches, None)

        # methods
        self.assertEqual(bb.half_height(), 0.5)
        self.assertEqual(bb.edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(bb.stitches_before_first_buttonhole(), None)
        self.assertEqual(bb.num_interior_buttonholes(), None)

    def test_button_band_percentage1(self):

        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)

        # First, get a reference neckline-width (in stitches)
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            button_band_edging_height=1,
            button_band_allowance=0,
            button_band_allowance_percentage=None,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        p = SweaterPatternFactory.from_pspec(pspec)
        cs = p.get_front_piece()
        cs.full_clean()
        gp = p.pieces.schematic.individual_garment_parameters

        reference_neckline_stitches = cs.neckline.stitches_across_neckline()
        self.assertEqual(reference_neckline_stitches, 38)

        # Now, check that button-band-allowance-percentage has the expected
        # effects

        # You'd think that 50% would give 19 and 150% would give 37, but
        # cardigan necklines must have an even number of stitches

        percentages = [50, 0, 100, -50]
        goal_results = [20, 38, 0, 58]

        for percent, goal in zip(percentages, goal_results):
            pspec = SweaterPatternSpecFactory(
                swatch=swatch,
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=SDC.NECK_VEE,
                button_band_edging_height=1,
                button_band_allowance=None,
                button_band_allowance_percentage=percent,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                number_of_buttons=2,
            )
            p = SweaterPatternFactory.from_pspec(pspec)
            cs = p.get_front_piece()
            cs.full_clean()
            # You'd think that the number of stitches would be 1.5 * 38 = 57, but
            # cardigan necklines need to have an even number of stitches
            self.assertEqual(cs.neckline.stitches_across_neckline(), goal)

            if percent == 100:
                self.assertTrue(cs.neckline.empty())

            if percent == 0:
                self.assertAlmostEqual(
                    cs.actual_hip, gp.hip_width_front / 2.0, delta=0.1
                )
                self.assertAlmostEqual(
                    cs.actual_waist, gp.waist_width_front / 2.0, delta=0.1
                )
                self.assertAlmostEqual(
                    cs.actual_bust, gp.bust_width_front / 2.0, delta=0.1
                )

            if percent < 0:
                self.assertGreater(cs.actual_hip, gp.hip_width_front / 2.0)
                self.assertGreater(cs.actual_waist, gp.waist_width_front / 2.0)
                self.assertGreater(cs.actual_bust, gp.bust_width_front / 2.0)

    def test_button_band_percentage2(self):

        # Make sure that a percentage of 100 gives empty necklines in all
        # fits
        user = UserFactory()
        swatch = SwatchFactory(rows_number=8)

        fits = SDC.FIT_HOURGLASS
        necklines = [SDC.NECK_BOAT, SDC.NECK_CREW, SDC.NECK_SCOOP, SDC.NECK_VEE]
        errors = 0

        for fit, neck in itertools.product(fits, necklines):

            pspec = SweaterPatternSpecFactory(
                swatch=swatch,
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=neck,
                garment_fit=fit,
                button_band_edging_height=1,
                button_band_allowance=None,
                button_band_allowance_percentage=100,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                number_of_buttons=0,
            )
            cs = make_cardigan_sleeved_from_pspec(pspec)
            msgs = ""
            if cs.neckline.empty():
                msgs += "GOOD: %s %s\n" % (fit, neck)
            else:
                errors += 1
                msgs += "BAD: %s %s\n" % (fit, neck)
        self.assertEqual(errors, 0, msgs)

    def test_repeats(self):

        # For comparison
        pspec = SweaterPatternSpecFactory(
            button_band_edging_height=1,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        self.assertEqual(cs.cast_ons, 47)

        # Note: Cabled check is 1 mod 4
        # one-by-one rib does not use repeats
        pspec = SweaterPatternSpecFactory(
            button_band_edging_height=1,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
            front_allover_stitch=StitchFactory(name="Cabled Check Stitch"),
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        self.assertEqual(cs.cast_ons % 4, 1)

        repeats_swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=3, additional_stitches=1
        )
        pspec = SweaterPatternSpecFactory(
            button_band_edging_height=1,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
            front_allover_stitch=StitchFactory(name="Stockinette"),
            swatch=repeats_swatch,
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        self.assertEqual(cs.cast_ons % 3, 1)

        # Open mesh lace is 0 mod 3
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
            front_allover_stitch=StitchFactory(name="Stockinette"),
            hip_edging_stitch=StitchFactory(name="Open Mesh Lace"),
        )
        cs = make_cardigan_sleeved_from_pspec(pspec)
        self.assertEqual(cs.cast_ons % 3, 0)

    def test_button_band_percentage_repeats(self):

        # Test that button-bands never get wider than necklines, even
        # when defined to be 100% of neckline. Use variety of conditions
        user = UserFactory()

        # Make a variety of swatches
        swatches = [
            SwatchFactory(
                use_repeats=True, stitches_per_repeat=3, additional_stitches=1
            ),
            SwatchFactory(
                use_repeats=True, stitches_per_repeat=20, additional_stitches=0
            ),
        ]

        # Use a variety of necklines
        necklines = [
            SDC.NECK_VEE,
            SDC.NECK_SCOOP,
            SDC.NECK_CREW,
            SDC.NECK_BOAT,
        ]

        # And lastly, use a variety of percentages.
        # Note: though negative percentages are legal, the tests below
        # were written for non-negative percentages only
        percentages = [0, 25, 50, 75, 95, 96, 97, 98, 99, 100]

        # Now, check each combination:
        for swatch in swatches:

            # first, get reference point:
            pspec = SweaterPatternSpecFactory(
                swatch=swatch,
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=SDC.NECK_VEE,
                button_band_edging_height=1,
                button_band_allowance=0,
                button_band_allowance_percentage=None,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                number_of_buttons=2,
            )
            cs = make_cardigan_sleeved_from_pspec(pspec)
            cs.full_clean()

            reference_neckline_stitches = cs.neckline.stitches_across_neckline()
            reference_total = sum(
                [cs.neckline.stitches_across_neckline(), cs.actual_button_band_stitches]
            )

            # Now, run through combinations

            for neckline, percentage in itertools.product(necklines, percentages):

                pspec = SweaterPatternSpecFactory(
                    swatch=swatch,
                    garment_type=SDC.CARDIGAN_SLEEVED,
                    neckline_style=neckline,
                    button_band_edging_height=0,
                    button_band_allowance=None,
                    button_band_allowance_percentage=percentage,
                    button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                    number_of_buttons=0,
                )
                cs = make_cardigan_sleeved_from_pspec(pspec)
                cs.full_clean()

                neckline_stitches = cs.neckline.stitches_across_neckline()
                buttonband_stitches = cs.actual_button_band_stitches

                self.assertGreaterEqual(neckline_stitches, 0)
                self.assertLessEqual(neckline_stitches, reference_neckline_stitches)

                # buttonband stitches can be less than zero, but
                # should never be more than the width of the referecne
                # neckline
                self.assertLessEqual(buttonband_stitches, reference_total)

                self.assertEqual(
                    neckline_stitches + buttonband_stitches, reference_total
                )

    def test_cardigan_sanity_checks(self):

        # Test that the cardigan pieces add up and will 'act' like a single
        # pullover
        user = UserFactory()

        # Make a variety of swatches
        swatches = [
            SwatchFactory(),
            SwatchFactory(
                use_repeats=True, stitches_per_repeat=3, additional_stitches=1
            ),
            SwatchFactory(
                use_repeats=True, stitches_per_repeat=20, additional_stitches=0
            ),
        ]

        # Use a variety of necklines
        necklines = [
            SDC.NECK_VEE,
            SDC.NECK_SCOOP,
            SDC.NECK_CREW,
            SDC.NECK_BOAT,
        ]

        percentages = [-100, -50, -1, 0, 1, 10, 25, 50, 75, 90, 99, 100]

        for combination in itertools.product(swatches, necklines, percentages):

            (swatch, neckline, percentage) = combination
            # get pullover for reference

            pspec = SweaterPatternSpecFactory(
                swatch=swatch,
                garment_type=SDC.PULLOVER_SLEEVED,
                neckline_style=neckline,
            )
            sf = make_sweaterfront_from_pspec(pspec)

            # Now get e cardigan front
            # first, get reference point:
            pspec = SweaterPatternSpecFactory(
                swatch=swatch,
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=neckline,
                button_band_edging_height=1,
                button_band_allowance=None,
                button_band_allowance_percentage=percentage,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                number_of_buttons=0,
            )
            cs = make_cardigan_sleeved_from_pspec(pspec)

            # Now we do some sanity checks

            # Check 1: do the CF and SF have the same values, when appropriate?
            self.assertEqual(sf.armhole_n, cs.armhole_n, combination)
            self.assertEqual(
                sf.num_shoulder_stitches, cs.num_shoulder_stitches, combination
            )

            # Check 2: Do the two pieces, when combined with the the button
            # band, match the pullover?
            cardi_total_co_st = sum([cs.actual_button_band_stitches, cs.cast_ons * 2])
            self.assertEqual(sf.cast_ons, cardi_total_co_st, combination)

            cardi_total_waist_st = sum(
                [cs.actual_button_band_stitches, cs.waist_stitches * 2]
            )
            self.assertEqual(sf.waist_stitches, cardi_total_waist_st, combination)

            cardi_total_bust_st = sum(
                [cs.actual_button_band_stitches, cs._bust_stitches_internal_use * 2]
            )
            self.assertEqual(
                sf._bust_stitches_internal_use, cardi_total_bust_st, combination
            )

            # Check 3: do the internal values for the CS add up?

            bust_stitches = cs._bust_stitches_internal_use
            top_bindoffs = sum(
                [
                    cs.armhole_n,
                    cs.num_shoulder_stitches,
                    cs.neckline.stitches_across_neckline() / 2,
                ]
            )
            self.assertEqual(bust_stitches, top_bindoffs, combination)

    def test_half_hourglass(self):

        # For comparison
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cf1 = make_cardigan_sleeved_from_pspec(pspec)
        self.assertGreater(cf1.cast_ons, cf1.waist_stitches)
        self.assertGreater(cf1.bust_stitches, cf1.waist_stitches)

        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
        )
        cf2 = make_cardigan_sleeved_from_pspec(pspec)
        self.assertTrue(cf2.is_straight)
        self.assertIsNone(cf2.waist_stitches)
        self.assertEqual(cf2.bust_stitches, cf2.cast_ons)

    def test_half_hourglass_error_case(self):

        swatch = SwatchFactory(
            stitches_number=31, stitches_length=6.25, rows_number=31, rows_length=4.5
        )

        body_dict = {
            "name": "error-case body",
            "waist_circ": 32,
            "bust_circ": 41.25,
            "upper_torso_circ": 37.75,
            "wrist_circ": 6.5,
            "forearm_circ": 9.5,
            "bicep_circ": 12,
            "elbow_circ": 11,
            "armpit_to_short_sleeve": 3,
            "armpit_to_elbow_sleeve": 6.5,
            "armpit_to_three_quarter_sleeve": 11.5,
            "armpit_to_full_sleeve": 18,
            "inter_nipple_distance": 7.75,
            "armpit_to_waist": 8.75,
            "armhole_depth": 8,
            "armpit_to_high_hip": 8.75 + 5.5,
            "armpit_to_med_hip": 8.75 + 7,
            "armpit_to_low_hip": 8.75 + 8.5,
            "armpit_to_tunic": 8.75 + 11,
            "high_hip_circ": 38,
            "med_hip_circ": 39.5,
            "low_hip_circ": 40,
            "tunic_circ": 41,
        }
        body = BodyFactory(**body_dict)

        design_dict = {
            "name": "error-case design",
            "garment_type": SDC.CARDIGAN_SLEEVED,
            "sleeve_length": SDC.SLEEVE_FULL,
            "sleeve_shape": SDC.SLEEVE_TAPERED,
            "neckline_style": SDC.NECK_VEE,
            "torso_length": SDC.LOW_HIP_LENGTH,
            "neckline_width": SDC.NECK_AVERAGE,
            "neckline_depth": 3,
            "neckline_depth_orientation": SDC.BELOW_ARMPIT,
            "silhouette": SDC.SILHOUETTE_HALF_HOURGLASS,
            "back_allover_stitch": StitchFactory(name="Stockinette"),
            "front_allover_stitch": StitchFactory(name="Cabled Check Stitch"),
            "sleeve_allover_stitch": StitchFactory(name="Stockinette"),
            "hip_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "hip_edging_height": 2,
            "sleeve_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "sleeve_edging_height": 2,
            "button_band_edging_stitch": StitchFactory(name="2x2 Ribbing"),
            "button_band_edging_height": 1.5,
            "button_band_allowance": 1.5,
            "number_of_buttons": 7,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "neck_edging_stitch": None,
            "neck_edging_height": None,
            "armhole_edging_stitch": None,
            "armhole_edging_height": None,
            "body": body,
            "swatch": swatch,
        }
        pspec = SweaterPatternSpecFactory(**design_dict)
        cf = make_cardigan_sleeved_from_pspec(pspec)
        self.assertTrue(cf.is_straight)
        self.assertIsNone(cf.waist_stitches)
        self.assertEqual(cf.bust_stitches, cf.cast_ons)

    def test_is_piece_methods(self):
        piece = create_cardigan_sleeved()
        self.assertFalse(piece.is_sweater_back)
        self.assertFalse(piece.is_vest_back)
        self.assertFalse(piece.is_sweater_front)
        self.assertFalse(piece.is_vest_front)
        self.assertTrue(piece.is_cardigan_sleeved)
        self.assertFalse(piece.is_cardigan_vest)

    def test_cross_chest_stitches(self):
        # Check the current implementation: this is None if necklines
        # go below the armhole shaping, valid number otherwise

        pspec1 = SweaterPatternSpecFactory(
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs1 = make_cardigan_sleeved_from_pspec(pspec1)
        self.assertEqual(cs1.bust_stitches, 49)
        self.assertEqual(cs1.armhole_n, 15)
        self.assertEqual(cs1.cross_chest_stitches, 34)

        pspec2 = SweaterPatternSpecFactory(
            neckline_depth=0.5,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs2 = make_cardigan_sleeved_from_pspec(pspec2)
        self.assertEqual(cs2.bust_stitches, 49)
        self.assertIsNone(cs2.cross_chest_stitches)

        pspec3 = SweaterPatternSpecFactory(
            neckline_depth=4.0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cs3 = make_cardigan_sleeved_from_pspec(pspec3)
        self.assertIsNone(cs3.bust_stitches)
        self.assertIsNone(cs3.cross_chest_stitches)

    def test_cables(self):

        # For comparison
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        cf_control = make_cardigan_sleeved_from_pspec(pspec)
        self.assertEqual(cf_control.cast_ons, 47)
        self.assertEqual(cf_control.inter_marker, 22)
        self.assertEqual(cf_control.waist_inter_double_marker, None)
        self.assertEqual(cf_control.waist_stitches, 42)
        self.assertEqual(cf_control.bust_inter_double_dart_markers, None)
        self.assertEqual(cf_control.bust_inter_standard_dart_markers, 22)
        self.assertEqual(cf_control.bust_inter_triple_dart_markers, None)
        self.assertEqual(cf_control.bust_stitches, 49)
        self.assertEqual(cf_control._bust_stitches_internal_use, 49)
        self.assertEqual(cf_control.armhole_x, 5)
        self.assertEqual(cf_control.armhole_y, 3)
        self.assertEqual(cf_control.armhole_z, 7)
        self.assertEqual(cf_control.first_shoulder_bindoff, 9)
        self.assertEqual(cf_control.num_shoulder_stitches, 17)
        self.assertEqual(cf_control.actual_hip, 9.4)
        self.assertEqual(cf_control.actual_waist, 8.4)
        self.assertEqual(cf_control.actual_bust, 9.8)
        self.assertAlmostEqual(cf_control.area(), 416.0, 1)
        self.assertEqual(cf_control.actual_neck_opening_width, 7.6)
        self.assertEqual(cf_control.cross_chest_stitches, 34)
        self.assertEqual(cf_control.neckline.stitches_across_neckline(), 34)
        self.assertEqual(cf_control.actual_button_band_stitches, 4.0)

        #
        # positive 'extra' cable stitches
        #
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=5,
        )
        cf = make_cardigan_sleeved_from_pspec(pspec)
        # Should increase
        self.assertEqual(cf.cast_ons, 52)
        self.assertEqual(cf.inter_marker, 27)
        self.assertEqual(cf.waist_inter_double_marker, None)
        self.assertEqual(cf.waist_stitches, 47)
        self.assertEqual(cf.bust_inter_double_dart_markers, None)
        self.assertEqual(cf.bust_inter_standard_dart_markers, 27)
        self.assertEqual(cf.bust_inter_triple_dart_markers, None)
        self.assertEqual(cf.bust_stitches, 54)
        self.assertEqual(cf._bust_stitches_internal_use, 54)
        self.assertEqual(cf.cross_chest_stitches, 39)
        self.assertEqual(
            cf.neckline.stitches_across_neckline(), 44
        )  # Yes, really-- add 10 instead of 5

        extra_area = (
            5
            * cf.hem_to_neckline_shaping_start
            / cf.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        extra_area *= 2  # Double it, so that you get the extra area of both sides
        self.assertLessEqual(cf.area() / (cf_control.area() + extra_area), 1.02)
        self.assertGreaterEqual(cf.area() / (cf_control.area() + extra_area), 0.98)

        # Should remain unchanged
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(cf.armhole_x, cf_control.armhole_x)
        self.assertEqual(cf.armhole_y, cf_control.armhole_y)
        self.assertEqual(cf.armhole_z, cf_control.armhole_z)
        self.assertEqual(cf.first_shoulder_bindoff, cf_control.first_shoulder_bindoff)
        self.assertEqual(cf.num_shoulder_stitches, cf_control.num_shoulder_stitches)
        self.assertEqual(cf.actual_hip, cf_control.actual_hip)
        self.assertEqual(cf.actual_waist, cf_control.actual_waist)
        self.assertEqual(cf.actual_bust, cf_control.actual_bust)
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(
            cf.actual_neck_opening_width, cf_control.actual_neck_opening_width
        )

        #
        # zero 'extra' cable stitches
        #
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=0,
        )
        cf = make_cardigan_sleeved_from_pspec(pspec)
        # Should remain unchanged
        self.assertEqual(cf.cast_ons, cf_control.cast_ons)
        self.assertEqual(cf.inter_marker, cf_control.inter_marker)
        self.assertEqual(
            cf.waist_inter_double_marker, cf_control.waist_inter_double_marker
        )
        self.assertEqual(cf.waist_stitches, cf_control.waist_stitches)
        self.assertEqual(
            cf.bust_inter_double_dart_markers, cf_control.bust_inter_double_dart_markers
        )
        self.assertEqual(
            cf.bust_inter_standard_dart_markers,
            cf_control.bust_inter_standard_dart_markers,
        )
        self.assertEqual(
            cf.bust_inter_triple_dart_markers, cf_control.bust_inter_triple_dart_markers
        )
        self.assertEqual(cf.bust_stitches, cf_control.bust_stitches)
        self.assertEqual(
            cf._bust_stitches_internal_use, cf_control._bust_stitches_internal_use
        )
        self.assertEqual(cf.cross_chest_stitches, cf_control.cross_chest_stitches)
        self.assertEqual(
            cf.neckline.stitches_across_neckline(),
            cf_control.neckline.stitches_across_neckline(),
        )
        self.assertEqual(cf.area(), cf_control.area())
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(cf.armhole_x, cf_control.armhole_x)
        self.assertEqual(cf.armhole_y, cf_control.armhole_y)
        self.assertEqual(cf.armhole_z, cf_control.armhole_z)
        self.assertEqual(cf.first_shoulder_bindoff, cf_control.first_shoulder_bindoff)
        self.assertEqual(cf.num_shoulder_stitches, cf_control.num_shoulder_stitches)
        self.assertEqual(cf.actual_hip, cf_control.actual_hip)
        self.assertEqual(cf.actual_waist, cf_control.actual_waist)
        self.assertEqual(cf.actual_bust, cf_control.actual_bust)
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(
            cf.actual_neck_opening_width, cf_control.actual_neck_opening_width
        )

        #
        # negative 'extra' cable stitches
        #
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=-5,
        )
        cf = make_cardigan_sleeved_from_pspec(pspec)
        # Should increase
        self.assertEqual(cf.cast_ons, 42)
        self.assertEqual(cf.inter_marker, 17)
        self.assertEqual(cf.waist_inter_double_marker, None)
        self.assertEqual(cf.waist_stitches, 37)
        self.assertEqual(cf.bust_inter_double_dart_markers, None)
        self.assertEqual(cf.bust_inter_standard_dart_markers, 17)
        self.assertEqual(cf.bust_inter_triple_dart_markers, None)
        self.assertEqual(cf.bust_stitches, 44)
        self.assertEqual(cf._bust_stitches_internal_use, 44)
        self.assertEqual(cf.cross_chest_stitches, 29)
        self.assertEqual(
            cf.neckline.stitches_across_neckline(), 24
        )  # Yes, really-- subtrace 10 instead of 5

        extra_area = (
            5
            * cf.hem_to_neckline_shaping_start
            / cf.schematic.get_spec_source().swatch.get_gauge().stitches
        )
        extra_area *= 2  # Double it, so that you get the extra area of both sides
        self.assertLessEqual(cf.area() / (cf_control.area() - extra_area), 1.02)
        self.assertGreaterEqual(cf.area() / (cf_control.area() - extra_area), 0.98)

        # Should remain unchanged
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(cf.armhole_x, cf_control.armhole_x)
        self.assertEqual(cf.armhole_y, cf_control.armhole_y)
        self.assertEqual(cf.armhole_z, cf_control.armhole_z)
        self.assertEqual(cf.first_shoulder_bindoff, cf_control.first_shoulder_bindoff)
        self.assertEqual(cf.num_shoulder_stitches, cf_control.num_shoulder_stitches)
        self.assertEqual(cf.actual_hip, cf_control.actual_hip)
        self.assertEqual(cf.actual_waist, cf_control.actual_waist)
        self.assertEqual(cf.actual_bust, cf_control.actual_bust)
        self.assertEqual(
            cf.actual_button_band_stitches, cf_control.actual_button_band_stitches
        )
        self.assertEqual(
            cf.actual_neck_opening_width, cf_control.actual_neck_opening_width
        )

    def test_straight_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        make_cardigan_sleeved_from_pspec(pspec)

    def test_aline_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        make_cardigan_sleeved_from_pspec(pspec)

    def test_tapered_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        make_cardigan_sleeved_from_pspec(pspec)

    def test_hourglass_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        make_cardigan_sleeved_from_pspec(pspec)

    def test_half_hourglass_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        make_cardigan_sleeved_from_pspec(pspec)

    def test_circumferences_with_buttons(self):

        # For cardigans with buttons, widths are computed as left-front + right-front + trim height

        buttons_pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=3,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        buttons_pspec.full_clean()
        buttons_cardigan = make_cardigan_sleeved_from_pspec(buttons_pspec)

        self.assertEqual(buttons_cardigan.actual_bust, 8.8)  # sanity check
        self.assertEqual(buttons_cardigan.total_front_finished_bust, 18.6)

        self.assertEqual(buttons_cardigan.actual_waist, 7.4)  # sanity check
        self.assertEqual(buttons_cardigan.total_front_finished_waist, 15.8)

        self.assertEqual(buttons_cardigan.actual_hip, 8.4)  # sanity check
        self.assertEqual(buttons_cardigan.total_front_finished_hip, 17.8)

    def test_total_front_finished_bust(self):

        # For cardigans with buttons, widths are computed as left-front + right-front + allowance

        no_buttons_pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=3,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=0,
        )
        no_buttons_pspec.full_clean()
        no_buttons_cardigan = make_cardigan_sleeved_from_pspec(no_buttons_pspec)

        self.assertEqual(
            no_buttons_cardigan.actual_button_band_allowance, 2.8
        )  # sanity check

        self.assertEqual(no_buttons_cardigan.actual_bust, 8.8)  # sanity check
        # We get some pathological floating-point errors here, so need to use AlmostEqual
        self.assertAlmostEqual(no_buttons_cardigan.total_front_finished_bust, 20.4, 10)

        self.assertEqual(no_buttons_cardigan.actual_waist, 7.4)  # sanity check
        # We get some pathological floating-point errors here, so need to use AlmostEqual
        self.assertAlmostEqual(no_buttons_cardigan.total_front_finished_waist, 17.6, 10)

        self.assertEqual(no_buttons_cardigan.actual_hip, 8.4)  # sanity check
        # We get some pathological floating-point errors here, so need to use AlmostEqual
        self.assertAlmostEqual(no_buttons_cardigan.total_front_finished_hip, 19.6, 10)


class TaperedFrontTest(django.test.TestCase):

    def test_shaping_rate(self):

        # Sanity check:
        # When bust is 47 inches, we're fine with 3 rows between shaping rows
        body = BodyFactory(
            med_hip_circ=40,
            bust_circ=47,
        )
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            rows_length=1,
            rows_number=7,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_TAPERED,
            body=body,
            swatch=swatch,
        )
        vf = make_vestfront_from_pspec(pspec)
        self.assertEqual(vf.rows_between_bust_standard_increase_rows, 3)
        self.assertEqual(vf.cast_ons, 95)
        self.assertEqual(vf.num_bust_standard_increase_rows, 21)
        self.assertFalse(vf.any_waist_decreases_on_ws)
        self.assertFalse(vf.any_bust_increases_on_ws)

        # When bust is 48 inches, we go down to 2 rows
        body = BodyFactory(
            med_hip_circ=40,
            bust_circ=48,
        )
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            rows_length=1,
            rows_number=7,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_TAPERED,
            body=body,
            swatch=swatch,
        )
        vf = make_vestfront_from_pspec(pspec)
        self.assertEqual(vf.rows_between_bust_standard_increase_rows, 2)
        self.assertEqual(vf.cast_ons, 95)
        self.assertEqual(vf.num_bust_standard_increase_rows, 24)
        self.assertFalse(vf.any_waist_decreases_on_ws)
        self.assertTrue(vf.any_bust_increases_on_ws)


class GradedSweaterFrontTests(django.test.TestCase):

    def test_make(self):
        gpsc = GradedSweaterSchematicFactory()
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit

        back_piece_schematic = gpsc.sweater_back_schematics.order_by(
            "GradedSweaterBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        sweater_back = GradedSweaterBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        front_piece_schematic = gpsc.sweater_front_schematics.order_by(
            "GradedSweaterFrontSchematic___gp_grade__grade__bust_circ"
        )[4]
        gsb = GradedSweaterFront.make(
            graded_pattern_pieces,
            sweater_back,
            front_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )


class GradedSweaterFrontTests(django.test.TestCase):

    def test_make(self):
        gpsc = GradedSweaterSchematicFactory()
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit

        back_piece_schematic = gpsc.sweater_back_schematics.order_by(
            "GradedSweaterBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        sweater_back = GradedSweaterBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        front_piece_schematic = gpsc.sweater_front_schematics.order_by(
            "GradedSweaterFrontSchematic___gp_grade__grade__bust_circ"
        )[4]
        gsb = GradedSweaterFront.make(
            front_piece_schematic,
            sweater_back,
            rounding_directions[fit],
            ease_tolerances[fit],
        )


class GradedVestFrontTests(django.test.TestCase):

    def test_make(self):
        pspec = GradedVestPatternSpecFactory()
        gpsc = GradedSweaterSchematicFactory.from_pspec(pspec)
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit
        roundings = rounding_directions[fit]
        eases = ease_tolerances[fit]

        back_piece_schematic = gpsc.vest_back_schematics.order_by(
            "GradedVestBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        vest_back = GradedVestBack.make(
            graded_pattern_pieces, back_piece_schematic, roundings, eases
        )

        front_piece_schematic = gpsc.vest_front_schematics.order_by(
            "GradedVestFrontSchematic___gp_grade__grade__bust_circ"
        )[4]
        gsb = GradedVestFront.make(front_piece_schematic, vest_back, roundings, eases)


class GradedCardiganSleevedTests(django.test.TestCase):

    def test_make(self):
        pspec = GradedCardiganPatternSpecFactory()
        gpsc = GradedSweaterSchematicFactory.from_pspec(pspec)
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit

        back_piece_schematic = gpsc.sweater_back_schematics.order_by(
            "GradedSweaterBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        sweater_back = GradedSweaterBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        front_piece_schematic = gpsc.cardigan_sleeved_schematics.order_by(
            "GradedCardiganSleevedSchematic___gp_grade__grade__bust_circ"
        )[4]
        gsb = GradedCardiganSleeved.make(
            front_piece_schematic,
            sweater_back,
            rounding_directions[fit],
            ease_tolerances[fit],
        )


class GradedCardiganVestTests(django.test.TestCase):

    def test_make(self):
        pspec = GradedCardiganVestPatternSpecFactory()
        gpsc = GradedSweaterSchematicFactory.from_pspec(pspec)
        graded_pattern_pieces = GradedSweaterPatternPiecesFactory()
        fit = gpsc.get_spec_source().garment_fit

        back_piece_schematic = gpsc.vest_back_schematics.order_by(
            "GradedVestBackSchematic___gp_grade__grade__bust_circ"
        )[4]
        vest_back = GradedVestBack.make(
            graded_pattern_pieces,
            back_piece_schematic,
            rounding_directions[fit],
            ease_tolerances[fit],
        )

        front_piece_schematic = gpsc.cardigan_vest_schematics.order_by(
            "GradedCardiganVestSchematic___gp_grade__grade__bust_circ"
        )[4]
        gsb = GradedCardiganVest.make(
            front_piece_schematic,
            vest_back,
            rounding_directions[fit],
            ease_tolerances[fit],
        )
