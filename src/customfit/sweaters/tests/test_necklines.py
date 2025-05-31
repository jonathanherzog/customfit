"""
Unit tests for the neckline classes.

"""

import os
import os.path

import django.test
from django.template.loader import render_to_string

from customfit.helpers.math_helpers import ROUND_DOWN
from customfit.helpers.row_parities import RS, WS
from customfit.patterns.renderers import PieceList
from customfit.swatches.factories import SwatchFactory

from ..models import (
    BackNeckline,
    BoatNeck,
    CrewNeck,
    ScoopNeck,
    TurksAndCaicosNeck,
    VeeNeck,
)


class BackNecklineTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 11
        bn = BackNeckline.make(
            stitches_goal,
            depth_goal,
            swatch.get_gauge(),
            rounding,
            ease_tolerances,
            shoulder_stitches,
        )
        bn.full_clean()
        self.assertEqual(bn.bindoff_stitches, 20)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 64)
        self.assertEqual(bn.stitches_before_initial_bindoffs, 13)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.5)
        self.assertEqual(bn.stitches_across_neckline(), 24)
        self.assertEqual(bn.stitches_to_pick_up(), 64)
        self.assertEqual(bn.rows_in_neckline(), 32)
        self.assertEqual(bn.rows_in_pullover_shaping(), 5)
        self.assertEqual(bn.area(), 19.2)

    def test_make_odd(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 11
        bn = BackNeckline.make(
            stitches_goal,
            depth_goal,
            swatch.get_gauge(),
            rounding,
            ease_tolerances,
            shoulder_stitches,
        )
        bn.full_clean()
        self.assertEqual(bn.bindoff_stitches, 21)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 65)
        self.assertEqual(bn.stitches_before_initial_bindoffs, 13)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.5)
        self.assertEqual(bn.stitches_across_neckline(), 25)
        self.assertEqual(bn.stitches_to_pick_up(), 65)
        self.assertEqual(bn.rows_in_neckline(), 32)
        self.assertEqual(bn.rows_in_pullover_shaping(), 5)
        self.assertEqual(bn.area(), 20)

    def test_make_super_chunky(self):
        depth_goal = 1
        swatch = SwatchFactory(
            rows_length=1, rows_number=2.5, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 11
        bn = BackNeckline.make(
            stitches_goal,
            depth_goal,
            swatch.get_gauge(),
            rounding,
            ease_tolerances,
            shoulder_stitches,
        )
        bn.full_clean()
        self.assertEqual(bn.rows_in_neckline(), 3)
        self.assertEqual(bn.bindoff_stitches, 25)
        self.assertEqual(bn.neckline_depth, 1.2)
        self.assertEqual(bn.pickup_stitches, 37)
        self.assertEqual(bn.stitches_before_initial_bindoffs, 11)
        self.assertEqual(bn.total_depth(), 1.2)
        self.assertEqual(bn.depth_to_shaping_end(), 1.2)
        self.assertEqual(bn.stitches_across_neckline(), 25)
        self.assertEqual(bn.stitches_to_pick_up(), 37)
        self.assertEqual(bn.rows_in_pullover_shaping(), 0)
        self.assertEqual(bn.rows_in_neckline(), 3)

    def test_error_case(self):
        depth_goal = 1
        swatch = SwatchFactory(
            rows_length=1, rows_number=4.5, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 11
        bn = BackNeckline.make(
            stitches_goal,
            depth_goal,
            swatch.get_gauge(),
            rounding,
            ease_tolerances,
            shoulder_stitches,
        )
        bn.full_clean()
        self.assertEqual(bn.bindoff_stitches, 20)
        self.assertEqual(bn.neckline_depth, 5.0 / 4.5)
        self.assertEqual(bn.stitches_before_initial_bindoffs, 13)
        self.assertEqual(bn.total_depth(), 5.0 / 4.5)
        self.assertAlmostEqual(bn.depth_to_shaping_end(), 1.0 / 4.5, 8)
        self.assertEqual(bn.stitches_across_neckline(), 24)
        self.assertEqual(bn.rows_in_neckline(), 5)
        self.assertEqual(bn.rows_in_pullover_shaping(), 5)

    def test_error_case2(self):
        depth_goal = 1
        swatch = SwatchFactory(
            rows_length=5.5, rows_number=24.0, stitches_length=5.0, stitches_number=14.0
        )
        stitches_goal = 18
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 8
        bn = BackNeckline.make(
            stitches_goal,
            depth_goal,
            swatch.get_gauge(),
            rounding,
            ease_tolerances,
            shoulder_stitches,
        )
        bn.full_clean()
        # before floating-point truncation:
        self.assertEqual(bn.rows_in_neckline(), 5)
        self.assertEqual(bn.neckline_depth, 1.1458333333333335)

        # Mimic the floating-point truncation from saving to the database
        bn.neckline_depth = 1.14583333332

        # Ensure that we can recover from truncation
        self.assertEqual(bn.rows_in_neckline(), 5)
        self.assertEqual(bn.rows_in_pullover_shaping(), 5)

    def test_zero_stitches(self):
        depth_goal = 1
        swatch = SwatchFactory(
            rows_length=1, rows_number=4.5, stitches_length=1, stitches_number=5
        )
        stitches_goal = 0
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        shoulder_stitches = 11
        with self.assertRaises(AssertionError):
            bn = BackNeckline.make(
                stitches_goal,
                depth_goal,
                swatch.get_gauge(),
                rounding,
                ease_tolerances,
                shoulder_stitches,
            )


class VeeNeckTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertEqual(vn.rows_per_decrease, 2)
        self.assertEqual(vn.decrease_rows, 12)
        self.assertEqual(vn.pickup_stitches, 48)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.depth_to_shaping_end(), 4 - (25 / 8))
        self.assertEqual(vn.stitches_across_neckline(), 24)
        self.assertEqual(vn.stitches_to_pick_up(), 48)
        self.assertAlmostEqual(vn.area(), 11.1, 1)
        self.assertEqual(vn.rows_in_pullover_shaping(), 25)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 23)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 23)

    def test_make_odd(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 1)
        self.assertEqual(vn.rows_per_decrease, 2)
        self.assertEqual(vn.decrease_rows, 12)
        self.assertEqual(vn.pickup_stitches, 49)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.depth_to_shaping_end(), 0.875)
        self.assertEqual(vn.stitches_across_neckline(), 25)
        self.assertEqual(vn.stitches_to_pick_up(), 49)
        self.assertEqual(vn.area(), 12.1875)
        self.assertEqual(vn.rows_in_pullover_shaping(), 25)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 23)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 23)

    def test_max_before_need_more_depth(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 64
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()
        self.assertEqual(vn.depth, 4.25)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertEqual(vn.rows_per_decrease, 1)
        self.assertEqual(vn.decrease_rows, 32)
        self.assertEqual(vn.pickup_stitches, 77)
        self.assertEqual(vn.total_depth(), 4.25)
        self.assertEqual(vn.depth_to_shaping_end(), 0)
        self.assertEqual(vn.stitches_across_neckline(), 64)
        self.assertEqual(vn.stitches_to_pick_up(), 77)
        self.assertEqual(vn.rows_in_pullover_shaping(), 34)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 32)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 32)

    def test_need_more_depth(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 66
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()
        self.assertEqual(vn.depth, 4.5)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertEqual(vn.rows_per_decrease, 1)
        self.assertEqual(vn.decrease_rows, 33)
        self.assertEqual(vn.total_depth(), 4.5)
        self.assertEqual(vn.pickup_stitches, 81)
        self.assertEqual(vn.depth_to_shaping_end(), 0.125)
        self.assertEqual(vn.stitches_across_neckline(), 66)
        self.assertEqual(vn.stitches_to_pick_up(), 81)
        self.assertEqual(vn.rows_in_pullover_shaping(), 35)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 33)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 33)

    def test_make_zero(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 0
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertTrue(vn.empty())

        self.assertIsNone(vn.depth)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertIsNone(vn.rows_per_decrease)
        self.assertEqual(vn.decrease_rows, 0)
        self.assertIsNone(vn.total_depth())
        self.assertEqual(vn.pickup_stitches, 0)
        self.assertIsNone(vn.depth_to_shaping_end())
        self.assertEqual(vn.stitches_across_neckline(), 0)
        self.assertEqual(vn.stitches_to_pick_up(), 0)
        self.assertEqual(vn.rows_in_pullover_shaping(), 0)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 0)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 0)

    def test_make_1(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 1
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertFalse(vn.empty())
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 1)
        self.assertIsNone(vn.rows_per_decrease)
        self.assertEqual(vn.decrease_rows, 0)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.pickup_stitches, 41)
        self.assertEqual(vn.depth_to_shaping_end(), 3.875)
        self.assertEqual(vn.stitches_across_neckline(), 1)
        self.assertEqual(vn.stitches_to_pick_up(), 41)
        self.assertEqual(vn.rows_in_pullover_shaping(), 1)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 0)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 0)

    def test_make_2(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 2
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertFalse(vn.empty())
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertIsNone(vn.rows_per_decrease)
        self.assertEqual(vn.decrease_rows, 1)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.pickup_stitches, 41)
        self.assertEqual(vn.depth_to_shaping_end(), 3.75)
        self.assertEqual(vn.stitches_across_neckline(), 2)
        self.assertEqual(vn.stitches_to_pick_up(), 41)
        self.assertEqual(vn.rows_in_pullover_shaping(), 2)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 1)

    def test_make_3(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 3
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertFalse(vn.empty())
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 1)
        self.assertIsNone(vn.rows_per_decrease)
        self.assertEqual(vn.decrease_rows, 1)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.pickup_stitches, 42)
        self.assertEqual(vn.depth_to_shaping_end(), 3.75)
        self.assertEqual(vn.stitches_across_neckline(), 3)
        self.assertEqual(vn.stitches_to_pick_up(), 42)
        self.assertEqual(vn.rows_in_pullover_shaping(), 2)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 1)

    def test_make_4(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 4
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertFalse(vn.empty())
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 0)
        self.assertEqual(vn.rows_per_decrease, 29)
        self.assertEqual(vn.decrease_rows, 2)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.pickup_stitches, 40)
        self.assertEqual(vn.stitches_across_neckline(), 4)
        self.assertEqual(vn.stitches_to_pick_up(), 40)
        self.assertEqual(vn.rows_in_pullover_shaping(), 32)
        self.assertEqual(vn.depth_to_shaping_end(), 0)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 30)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 30)

    def test_make_5(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        swatch.save()
        stitches_goal = 5
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        vn = VeeNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        vn.full_clean()

        self.assertFalse(vn.empty())
        self.assertEqual(vn.depth, 4)
        self.assertEqual(vn.extra_bindoffs, 1)
        self.assertEqual(vn.rows_per_decrease, 29)
        self.assertEqual(vn.decrease_rows, 2)
        self.assertEqual(vn.total_depth(), 4)
        self.assertEqual(vn.pickup_stitches, 41)
        self.assertEqual(vn.stitches_across_neckline(), 5)
        self.assertEqual(vn.stitches_to_pick_up(), 41)
        self.assertEqual(vn.rows_in_pullover_shaping(), 32)
        self.assertEqual(vn.depth_to_shaping_end(), 0)
        self.assertEqual(vn.rows_in_cardigan_shaping(RS), 30)
        self.assertEqual(vn.rows_in_cardigan_shaping(WS), 30)


class CrewNeckTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()
        self.assertEqual(cn.depth, 4)
        self.assertFalse(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 6)
        self.assertEqual(cn.center_bindoffs, 12)
        self.assertEqual(cn.neck_edge_decreases, 3)
        self.assertEqual(cn.rs_edge_decreases, 3)
        self.assertEqual(cn.pickup_stitches, 57)
        self.assertEqual(cn.center_bindoffs_cardigan(), 6)
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 4 - (9 / 8))
        self.assertEqual(cn.stitches_across_neckline(), 24)
        self.assertEqual(cn.stitches_to_pick_up(), 57)
        self.assertIsNone(cn.no_rs_decreases_two_stitch_bindoffs())
        self.assertIsNone(cn.no_rs_decreases_one_stitch_bindoffs())
        self.assertAlmostEqual(cn.area(), 18.1, 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 9)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 9)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 10)

    def test_make_odd(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()
        self.assertEqual(cn.depth, 4)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 6)
        self.assertEqual(cn.center_bindoffs, 11)
        self.assertEqual(cn.neck_edge_decreases, 4)
        self.assertEqual(cn.rs_edge_decreases, 3)
        self.assertEqual(cn.pickup_stitches, 57)
        self.assertRaises(AssertionError, cn.center_bindoffs_cardigan)
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 2.625)
        self.assertEqual(cn.stitches_across_neckline(), 25)
        self.assertEqual(cn.stitches_to_pick_up(), 57)
        self.assertIsNone(cn.no_rs_decreases_two_stitch_bindoffs())
        self.assertIsNone(cn.no_rs_decreases_one_stitch_bindoffs())
        self.assertAlmostEqual(cn.area(), 17.925, 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 11)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 11)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 10)

    def test_compress(self):
        depth_goal = 2.25
        swatch = SwatchFactory(
            rows_length=1, rows_number=4, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()
        self.assertEqual(cn.depth, 2.25)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 6)
        self.assertEqual(cn.center_bindoffs, 11)
        self.assertEqual(cn.neck_edge_decreases, 5)
        self.assertEqual(cn.rs_edge_decreases, 2)
        self.assertEqual(cn.pickup_stitches, 37)
        self.assertRaises(AssertionError, cn.center_bindoffs_cardigan)
        self.assertEqual(cn.total_depth(), 2.25)
        self.assertEqual(cn.depth_to_shaping_end(), 0)
        self.assertEqual(cn.stitches_across_neckline(), 25)
        self.assertEqual(cn.stitches_to_pick_up(), 37)
        self.assertIsNone(cn.no_rs_decreases_two_stitch_bindoffs())
        self.assertIsNone(cn.no_rs_decreases_one_stitch_bindoffs())
        self.assertEqual(cn.rows_in_pullover_shaping(), 9)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 9)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 10)

    def test_need_more_depth1(self):
        depth_goal = 0.5
        swatch = SwatchFactory(
            rows_length=1, rows_number=4, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()
        self.assertEqual(cn.depth, 2)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 6)
        self.assertEqual(cn.center_bindoffs, 11)
        self.assertEqual(cn.neck_edge_decreases, 7)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 35)
        self.assertRaises(AssertionError, cn.center_bindoffs_cardigan)
        self.assertEqual(cn.total_depth(), 2)
        self.assertEqual(cn.depth_to_shaping_end(), 0)
        self.assertEqual(cn.stitches_across_neckline(), 25)
        self.assertEqual(cn.stitches_to_pick_up(), 35)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 2)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 3)
        self.assertAlmostEqual(cn.area(), 6.3, 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 8)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 8)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 8)

    def test_compress_bindoffs(self):
        depth_goal = 0.5
        swatch = SwatchFactory(
            rows_length=1, rows_number=4, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertEqual(cn.neck_edge_decreases, 7)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 2)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 3)

        cn.neck_edge_decreases = 8
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 2)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 4)

        cn.neck_edge_decreases = 9
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 2)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 5)

        cn.neck_edge_decreases = 10
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 3)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 4)

        cn.neck_edge_decreases = 11
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 3)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 5)

        cn.neck_edge_decreases = 12
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 3)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 6)

        cn.neck_edge_decreases = 13
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 3)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 7)

        cn.neck_edge_decreases = 14
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 4)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 6)

    def test_make_zero(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 0
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertTrue(cn.empty())

        self.assertEqual(cn.depth, None)
        self.assertFalse(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 0)
        self.assertEqual(cn.center_bindoffs, 0)
        self.assertEqual(cn.neck_edge_decreases, 0)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 0)
        self.assertEqual(cn.center_bindoffs_cardigan(), 0)
        self.assertEqual(cn.total_depth(), None)
        self.assertIsNone(cn.depth_to_shaping_end())
        self.assertEqual(cn.stitches_across_neckline(), 0)
        self.assertEqual(cn.stitches_to_pick_up(), 0)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 0)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 0)
        self.assertEqual(cn.rows_in_pullover_shaping(), 0)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 0)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 0)

    def test_make_one(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 1
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertFalse(cn.empty())
        self.assertEqual(cn.depth, 4)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 1)
        self.assertEqual(cn.center_bindoffs, 1)
        self.assertEqual(cn.neck_edge_decreases, 0)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 41)
        with self.assertRaises(AssertionError):
            # Cardigan necks must have even number of stitchs
            cn.center_bindoffs_cardigan()
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 3.875)
        self.assertEqual(cn.stitches_across_neckline(), 1)
        self.assertEqual(cn.stitches_to_pick_up(), 41)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 0)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 0)
        self.assertEqual(cn.rows_in_pullover_shaping(), 1)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 1)

    def test_make_two(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 2
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertFalse(cn.empty())
        self.assertEqual(cn.depth, 4)
        self.assertFalse(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 0)
        self.assertEqual(cn.center_bindoffs, 0)
        self.assertEqual(cn.neck_edge_decreases, 1)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 41)
        self.assertEqual(cn.center_bindoffs_cardigan(), 0)
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 3.875)
        self.assertEqual(cn.stitches_across_neckline(), 2)
        self.assertEqual(cn.stitches_to_pick_up(), 41)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 0)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 1)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 1)

    def test_make_three(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 3
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertFalse(cn.empty())
        self.assertEqual(cn.depth, 4)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 1)
        self.assertEqual(cn.center_bindoffs, 1)
        self.assertEqual(cn.neck_edge_decreases, 1)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 42)
        with self.assertRaises(AssertionError):
            # Cardigan necks must have even number of stitchs
            cn.center_bindoffs_cardigan()
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 3.75)
        self.assertEqual(cn.stitches_across_neckline(), 3)
        self.assertEqual(cn.stitches_to_pick_up(), 42)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 0)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 2)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 2)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 2)

    def test_make_four(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 4
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertFalse(cn.empty())
        self.assertEqual(cn.depth, 4)
        self.assertFalse(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 1)
        self.assertEqual(cn.center_bindoffs, 2)
        self.assertEqual(cn.neck_edge_decreases, 1)
        self.assertEqual(cn.rs_edge_decreases, 0)
        self.assertEqual(cn.pickup_stitches, 43)
        self.assertEqual(cn.center_bindoffs_cardigan(), 1)
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 3.75)
        self.assertEqual(cn.stitches_across_neckline(), 4)
        self.assertEqual(cn.stitches_to_pick_up(), 43)
        self.assertEqual(cn.no_rs_decreases_two_stitch_bindoffs(), 0)
        self.assertEqual(cn.no_rs_decreases_one_stitch_bindoffs(), 1)
        self.assertEqual(cn.rows_in_pullover_shaping(), 2)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 2)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 2)

    def test_make_five(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 5
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        cn = CrewNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        cn.full_clean()

        self.assertFalse(cn.empty())
        self.assertEqual(cn.depth, 4)
        self.assertTrue(cn.marker_before_center_stitch)
        self.assertEqual(cn.bindoffs_before_marker, 1)
        self.assertEqual(cn.center_bindoffs, 1)
        self.assertEqual(cn.neck_edge_decreases, 1)
        self.assertEqual(cn.rs_edge_decreases, 1)
        self.assertEqual(cn.pickup_stitches, 42)
        with self.assertRaises(AssertionError):
            # Cardigan necks must have even number of stitchs
            cn.center_bindoffs_cardigan()
        self.assertEqual(cn.total_depth(), 4)
        self.assertEqual(cn.depth_to_shaping_end(), 3.625)
        self.assertEqual(cn.stitches_across_neckline(), 5)
        self.assertEqual(cn.stitches_to_pick_up(), 42)
        self.assertIsNone(cn.no_rs_decreases_two_stitch_bindoffs())
        self.assertIsNone(cn.no_rs_decreases_one_stitch_bindoffs())
        self.assertEqual(cn.rows_in_pullover_shaping(), 3)
        self.assertEqual(cn.rows_in_cardigan_shaping(RS), 3)
        self.assertEqual(cn.rows_in_cardigan_shaping(WS), 4)


class ScoopNeckTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 40
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()
        self.assertFalse(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 8)
        self.assertEqual(sn.y_bindoffs, 5)
        self.assertEqual(sn.z_bindoffs, 4)
        self.assertEqual(sn.q_bindoffs, 3)
        self.assertEqual(sn.pickup_stitches, 84)
        self.assertEqual(sn.initial_bindoffs, 16)
        self.assertEqual(sn.total_depth(), 6)
        self.assertEqual(sn.depth_to_shaping_end(), 3.125)
        self.assertEqual(sn.stitches_across_neckline(), 40)
        self.assertEqual(sn.stitches_to_pick_up(), 84)
        self.assertEqual(sn.initial_bindoffs_cardigan(), 8)
        self.assertAlmostEqual(sn.area(), 41.725, 1)
        self.assertEqual(sn.rows_in_pullover_shaping(), 23)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 23)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 24)

    def test_make_odd(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 41
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()
        self.assertTrue(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 8)
        self.assertEqual(sn.y_bindoffs, 6)
        self.assertEqual(sn.z_bindoffs, 4)
        self.assertEqual(sn.q_bindoffs, 3)
        self.assertEqual(sn.pickup_stitches, 83)
        self.assertEqual(sn.initial_bindoffs, 15)
        self.assertEqual(sn.total_depth(), 6)
        self.assertEqual(sn.depth_to_shaping_end(), 6 - (25 / 8))
        self.assertEqual(sn.stitches_across_neckline(), 41)
        self.assertEqual(sn.stitches_to_pick_up(), 83)
        self.assertRaises(AssertionError, sn.initial_bindoffs_cardigan)
        self.assertAlmostEqual(sn.area(), 41.25, 1)
        self.assertEqual(sn.rows_in_pullover_shaping(), 25)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 25)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 24)

    def test_not_enough_depth(self):
        depth_goal = 2
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 41
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()
        self.assertTrue(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 8)
        self.assertEqual(sn.y_bindoffs, 6)
        self.assertEqual(sn.z_bindoffs, 4)
        self.assertEqual(sn.q_bindoffs, 3)
        self.assertEqual(sn.pickup_stitches, 54)
        self.assertEqual(sn.initial_bindoffs, 15)
        self.assertEqual(sn.total_depth(), 3.125)
        self.assertEqual(sn.depth_to_shaping_end(), 0)
        self.assertEqual(sn.stitches_across_neckline(), 41)
        self.assertEqual(sn.stitches_to_pick_up(), 54)
        self.assertRaises(AssertionError, sn.initial_bindoffs_cardigan)
        self.assertEqual(sn.rows_in_pullover_shaping(), 25)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 25)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 24)

    def test_make_zero(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 0
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertTrue(sn.empty())

        self.assertFalse(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 0)
        self.assertEqual(sn.y_bindoffs, 0)
        self.assertEqual(sn.z_bindoffs, 0)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 0)
        self.assertEqual(sn.initial_bindoffs, 0)
        self.assertIsNone(sn.total_depth())
        self.assertIsNone(sn.depth_to_shaping_end())
        self.assertEqual(sn.stitches_across_neckline(), 0)
        self.assertEqual(sn.stitches_to_pick_up(), 0)
        self.assertEqual(sn.initial_bindoffs_cardigan(), 0)
        self.assertEqual(sn.rows_in_pullover_shaping(), 0)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 0)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 0)

    def test_make_one(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 1
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertFalse(sn.empty())
        self.assertEqual(sn.total_depth(), 4)
        self.assertTrue(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 1)
        self.assertEqual(sn.y_bindoffs, 0)
        self.assertEqual(sn.z_bindoffs, 0)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 40)
        self.assertEqual(sn.initial_bindoffs, 1)
        self.assertEqual(sn.depth_to_shaping_end(), 3.875)
        self.assertEqual(sn.stitches_across_neckline(), 1)
        self.assertEqual(sn.stitches_to_pick_up(), 40)
        self.assertEqual(sn.rows_in_pullover_shaping(), 1)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 1)
        with self.assertRaises(AssertionError):
            # Cardigan necklines must have even number of stitches
            sn.initial_bindoffs_cardigan()

    def test_make_two(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 2
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertFalse(sn.empty())
        self.assertEqual(sn.total_depth(), 4)
        self.assertFalse(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 0)
        self.assertEqual(sn.y_bindoffs, 1)
        self.assertEqual(sn.z_bindoffs, 0)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 40)
        self.assertEqual(sn.initial_bindoffs, 0)
        self.assertEqual(sn.depth_to_shaping_end(), 3.75)
        self.assertEqual(sn.stitches_across_neckline(), 2)
        self.assertEqual(sn.stitches_to_pick_up(), 40)
        self.assertEqual(sn.initial_bindoffs_cardigan(), 0)
        self.assertEqual(sn.rows_in_pullover_shaping(), 2)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 2)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 2)

    def test_make_three(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 3
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertFalse(sn.empty())
        self.assertEqual(sn.total_depth(), 4)
        self.assertTrue(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 1)
        self.assertEqual(sn.y_bindoffs, 1)
        self.assertEqual(sn.z_bindoffs, 0)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 41)
        self.assertEqual(sn.initial_bindoffs, 1)
        self.assertEqual(sn.depth_to_shaping_end(), 3.75)
        self.assertEqual(sn.stitches_across_neckline(), 3)
        self.assertEqual(sn.stitches_to_pick_up(), 41)
        self.assertEqual(sn.rows_in_pullover_shaping(), 2)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 2)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 2)
        with self.assertRaises(AssertionError):
            # Cardigan necklines must have even number of stitches
            sn.initial_bindoffs_cardigan()

    def test_make_four(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 4
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertFalse(sn.empty())
        self.assertEqual(sn.total_depth(), 4)
        self.assertFalse(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 0)
        self.assertEqual(sn.y_bindoffs, 1)
        self.assertEqual(sn.z_bindoffs, 1)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 42)
        self.assertEqual(sn.initial_bindoffs, 0)
        self.assertEqual(sn.depth_to_shaping_end(), 3.625)
        self.assertEqual(sn.stitches_across_neckline(), 4)
        self.assertEqual(sn.stitches_to_pick_up(), 42)
        self.assertEqual(sn.initial_bindoffs_cardigan(), 0)
        self.assertEqual(sn.rows_in_pullover_shaping(), 3)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 3)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 4)

    def test_make_five(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 5
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        sn = ScoopNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        sn.full_clean()

        self.assertFalse(sn.empty())
        self.assertEqual(sn.total_depth(), 4)
        self.assertEqual(sn.depth_to_shaping_end(), 3.625)
        self.assertTrue(sn.marker_before_center_stitch)
        self.assertEqual(sn.bindoff_stitches_before_marker, 1)
        self.assertEqual(sn.y_bindoffs, 1)
        self.assertEqual(sn.z_bindoffs, 1)
        self.assertEqual(sn.q_bindoffs, 0)
        self.assertEqual(sn.pickup_stitches, 43)
        self.assertEqual(sn.initial_bindoffs, 1)
        self.assertEqual(sn.depth_to_shaping_end(), 3.625)
        self.assertEqual(sn.stitches_across_neckline(), 5)
        self.assertEqual(sn.stitches_to_pick_up(), 43)
        self.assertEqual(sn.rows_in_pullover_shaping(), 3)
        self.assertEqual(sn.rows_in_cardigan_shaping(RS), 3)
        self.assertEqual(sn.rows_in_cardigan_shaping(WS), 4)
        with self.assertRaises(AssertionError):
            # Cardigan necklines must have even number of stitches
            sn.initial_bindoffs_cardigan()


class BoatNeckTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()
        self.assertEqual(bn.bottom_bindoffs, 20)
        self.assertEqual(bn.side_bindoffs, 2)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 64)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.5)
        self.assertEqual(bn.stitches_across_neckline(), 24)
        self.assertEqual(bn.stitches_to_pick_up(), 64)
        self.assertEqual(bn.marker_before_center_stitch(), False)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 10)
        self.assertEqual(bn.bottom_bindoffs_cardigan(), 10)
        self.assertEqual(bn.area(), 19.2)
        self.assertEqual(bn.rows_in_pullover_shaping(), 4)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 5)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 4)

    def test_make_odd(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()
        self.assertEqual(bn.bottom_bindoffs, 21)
        self.assertEqual(bn.side_bindoffs, 2)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 65)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.5)
        self.assertEqual(bn.stitches_across_neckline(), 25)
        self.assertEqual(bn.stitches_to_pick_up(), 65)
        self.assertEqual(bn.marker_before_center_stitch(), True)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 10)
        self.assertRaises(AssertionError, bn.bottom_bindoffs_cardigan)
        self.assertEqual(bn.area(), 20)
        self.assertEqual(bn.rows_in_pullover_shaping(), 4)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 5)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 4)

    def test_not_enough_depth(self):
        depth_goal = 0
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()
        self.assertEqual(bn.bottom_bindoffs, 20)
        self.assertEqual(bn.side_bindoffs, 2)
        self.assertEqual(bn.neckline_depth, 0.5)
        self.assertEqual(bn.pickup_stitches, 29)
        self.assertEqual(bn.total_depth(), 0.5)
        self.assertEqual(bn.depth_to_shaping_end(), 0)
        self.assertEqual(bn.stitches_across_neckline(), 24)
        self.assertEqual(bn.stitches_to_pick_up(), 29)
        self.assertEqual(bn.marker_before_center_stitch(), False)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 10)
        self.assertEqual(bn.bottom_bindoffs_cardigan(), 10)
        self.assertEqual(bn.rows_in_pullover_shaping(), 4)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 5)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 4)

    def test_make_zero(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 0
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()

        self.assertTrue(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 0)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, None)
        self.assertEqual(bn.pickup_stitches, 0)
        self.assertEqual(bn.total_depth(), None)
        self.assertEqual(bn.depth_to_shaping_end(), None)
        self.assertEqual(bn.stitches_across_neckline(), 0)
        self.assertEqual(bn.stitches_to_pick_up(), 0)
        self.assertEqual(bn.marker_before_center_stitch(), False)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 0)
        self.assertEqual(bn.bottom_bindoffs_cardigan(), 0)
        self.assertEqual(bn.rows_in_pullover_shaping(), 0)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 0)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 0)

    def test_make_one(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 1
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()

        self.assertFalse(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 1)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 41)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.875)
        self.assertEqual(bn.stitches_across_neckline(), 1)
        self.assertEqual(bn.stitches_to_pick_up(), 41)
        self.assertEqual(bn.marker_before_center_stitch(), True)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 0)
        self.assertEqual(bn.rows_in_pullover_shaping(), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 1)
        with self.assertRaises(AssertionError):
            # Cardigans must have even number of stitches
            bn.bottom_bindoffs_cardigan()

    def test_make_two(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 2
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()

        self.assertFalse(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 2)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 42)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.875)
        self.assertEqual(bn.stitches_across_neckline(), 2)
        self.assertEqual(bn.stitches_to_pick_up(), 42)
        self.assertEqual(bn.marker_before_center_stitch(), False)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 1)
        self.assertEqual(bn.bottom_bindoffs_cardigan(), 1)
        self.assertEqual(bn.rows_in_pullover_shaping(), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 1)

    def test_make_three(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 3
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()

        self.assertFalse(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 3)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 43)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.875)
        self.assertEqual(bn.stitches_across_neckline(), 3)
        self.assertEqual(bn.stitches_to_pick_up(), 43)
        self.assertEqual(bn.marker_before_center_stitch(), True)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 1)
        self.assertEqual(bn.rows_in_pullover_shaping(), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 1)
        with self.assertRaises(AssertionError):
            # Cardigans must have even number of stitches
            bn.bottom_bindoffs_cardigan()

    def test_make_four(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 4
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        bn.full_clean()

        self.assertFalse(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 4)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 44)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.875)
        self.assertEqual(bn.stitches_across_neckline(), 4)
        self.assertEqual(bn.stitches_to_pick_up(), 44)
        self.assertEqual(bn.marker_before_center_stitch(), False)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 2)
        self.assertEqual(bn.bottom_bindoffs_cardigan(), 2)
        self.assertEqual(bn.rows_in_pullover_shaping(), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 1)

    def test_make_five(self):
        depth_goal = 4
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 5
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        bn = BoatNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )

        self.assertFalse(bn.empty())
        self.assertEqual(bn.bottom_bindoffs, 5)
        self.assertEqual(bn.side_bindoffs, 0)
        self.assertEqual(bn.neckline_depth, 4)
        self.assertEqual(bn.pickup_stitches, 45)
        self.assertEqual(bn.total_depth(), 4)
        self.assertEqual(bn.depth_to_shaping_end(), 3.875)
        self.assertEqual(bn.stitches_across_neckline(), 5)
        self.assertEqual(bn.stitches_to_pick_up(), 45)
        self.assertEqual(bn.marker_before_center_stitch(), True)
        self.assertEqual(bn.bindoff_stitches_before_marker(), 2)
        self.assertEqual(bn.rows_in_pullover_shaping(), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(RS), 1)
        self.assertEqual(bn.rows_in_cardigan_shaping(WS), 1)
        with self.assertRaises(AssertionError):
            # Cardigans must have even number of stitches
            bn.bottom_bindoffs_cardigan()


class TurksAndCaicosNeckTest(django.test.TestCase):

    def test_make_even(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        tcn = TurksAndCaicosNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        tcn.full_clean()
        tcn.save()
        self.assertEqual(tcn.bottom_bindoffs, 20)
        self.assertEqual(tcn.side_bindoffs, 2)
        self.assertEqual(tcn.neckline_depth, 6)
        self.assertEqual(tcn.pickup_stitches, 49)
        self.assertEqual(tcn.total_depth(), 6)
        self.assertEqual(tcn.depth_to_shaping_end(), 2.0)
        self.assertEqual(tcn.stitches_across_neckline(), 24)
        self.assertEqual(tcn.stitches_to_pick_up(), 49)
        self.assertEqual(tcn.marker_before_center_stitch(), False)
        self.assertEqual(tcn.bindoff_stitches_before_marker(), 10)
        self.assertEqual(tcn.bottom_bindoffs_cardigan(), 10)
        self.assertEqual(tcn.lace_stitches, 12)
        self.assertEqual(tcn.lace_height_in_inches(), 3.5)
        self.assertEqual(tcn.lace_height_in_rows(), 27)
        self.assertEqual(tcn.area(), 12)
        self.assertEqual(tcn.rows_in_pullover_shaping(), 4)
        tcn.delete()

    def test_make_odd(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 25
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        tcn = TurksAndCaicosNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        tcn.full_clean()
        tcn.save()
        self.assertEqual(tcn.bottom_bindoffs, 21)
        self.assertEqual(tcn.side_bindoffs, 2)
        self.assertEqual(tcn.neckline_depth, 6)
        self.assertEqual(tcn.pickup_stitches, 50)
        self.assertEqual(tcn.total_depth(), 6)
        self.assertEqual(tcn.depth_to_shaping_end(), 2.0)
        self.assertEqual(tcn.stitches_across_neckline(), 25)
        self.assertEqual(tcn.stitches_to_pick_up(), 50)
        self.assertEqual(tcn.marker_before_center_stitch(), True)
        self.assertEqual(tcn.bindoff_stitches_before_marker(), 10)
        self.assertRaises(AssertionError, tcn.bottom_bindoffs_cardigan)
        self.assertEqual(tcn.lace_stitches, 12)
        self.assertEqual(tcn.lace_height_in_inches(), 3.5)
        self.assertEqual(tcn.lace_height_in_rows(), 27)
        self.assertEqual(tcn.area(), 12.5)
        self.assertEqual(tcn.rows_in_pullover_shaping(), 4)
        tcn.delete()

    def test_not_enough_depth(self):
        depth_goal = 5.49
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 24
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        with self.assertRaises(AssertionError):
            TurksAndCaicosNeck.make(
                stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
            )

    def test_not_enough_stitches(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        stitches_goal = 14
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None
        with self.assertRaises(AssertionError):
            TurksAndCaicosNeck.make(
                stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
            )

    def test_wide_neck(self):
        depth_goal = 6
        swatch = SwatchFactory(
            rows_length=1, rows_number=8, stitches_length=1, stitches_number=5
        )
        rounding = {"neckline_pickup_stitches": ROUND_DOWN}
        ease_tolerances = None

        stitches_goal = 91
        tcn = TurksAndCaicosNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        self.assertEqual(tcn.lace_stitches, 72)

        stitches_goal = 104
        tcn = TurksAndCaicosNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        self.assertEqual(tcn.lace_stitches, 72)

        stitches_goal = 105
        tcn = TurksAndCaicosNeck.make(
            stitches_goal, depth_goal, swatch.get_gauge(), rounding, ease_tolerances
        )
        self.assertEqual(tcn.lace_stitches, 84)
