# -*- coding: utf-8 -*-


from django.test import TestCase

from customfit.swatches.factories import GaugeFactory

from ..factories import (
    GradedCardiganPatternSpecFactory,
    GradedCardiganVestPatternSpecFactory,
    GradedSweaterPatternPiecesFactory,
    GradedSweaterPatternSpecFactory,
    GradedSweaterSchematicFactory,
    GradedVestPatternSpecFactory,
)
from ..models import (
    EdgeCompoundShapingResult,
    EdgeShapingResult,
    GradedCardiganSleeved,
    GradedCardiganVest,
    GradedSleeve,
    GradedSweaterBack,
    GradedSweaterFront,
    GradedSweaterPatternPieces,
    GradedVestBack,
    GradedVestFront,
    SweaterPiece,
    TorsoShapingResult,
)


class EdgeShapingResultTests(TestCase):

    def test_compute_full(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                GaugeFactory(),
                20,
                20,
                5,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1",
                GaugeFactory(rows=4),
                20,
                10,
                10,
                5,
                8,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2",
                GaugeFactory(rows=4),
                20,
                10,
                5,
                5,
                3,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3",
                GaugeFactory(rows=4),
                20,
                12,
                1,
                4,
                0,
                4,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_insufficient_vertical_room",
                GaugeFactory(rows=4),
                20,
                10,
                1,
                4,
                0,
                4,
                None,
                False,
                18,
                12,
            ),
            (
                "test_compute_shaping_no_height",
                GaugeFactory(rows=4),
                20,
                10,
                0,
                0,
                None,
                0,
                None,
                False,
                10,
                20,
            ),
            (
                "test_shaping_too_much_height",
                GaugeFactory(rows=4),
                14,
                10,
                10,
                2,
                38,
                2,
                0,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_full(
                larger_stitches, smaller_stitches, max_vertical_height, gauge
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertFalse(sr.max_distance_constraint_hit)

    def test_compute_full_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            EdgeShapingResult.compute_shaping_full(20, 10, -1, gauge)

    def test_compute_full_max_distance(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # max distance
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_with_max_distance",
                GaugeFactory(rows=4),
                20,
                16,
                5,
                1,
                2,
                4,
                2,
                3.5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_with_max_distance_fractional_rows",
                GaugeFactory(rows=4),
                20,
                16,
                5,
                1.1,
                2,
                4,
                2,
                3.5,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            max_distance_between_shaping_rows,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_full(
                larger_stitches,
                smaller_stitches,
                max_vertical_height,
                gauge,
                False,
                max_distance_between_shaping_rows,
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertTrue(sr.max_distance_constraint_hit)

    def test_compute_full_even(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight_even",
                GaugeFactory(),
                20,
                20,
                5,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping_even",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1_even",
                GaugeFactory(rows=4),
                20,
                10,
                10,
                5,
                7,
                5,
                1.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2_even",
                GaugeFactory(rows=4),
                20,
                10,
                5,
                5,
                3,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3_even",
                GaugeFactory(rows=4),
                20,
                12,
                1.75,
                4,
                1,
                4,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_insufficient_vertical_room_even",
                GaugeFactory(rows=4),
                20,
                10,
                1.25,
                3,
                1,
                3,
                None,
                False,
                16,
                14,
            ),
            (
                "test_compute_shaping_no_height_even",
                GaugeFactory(rows=4),
                20,
                10,
                0,
                0,
                None,
                0,
                None,
                False,
                10,
                20,
            ),
            (
                "test_shaping_too_much_height_even",
                GaugeFactory(rows=4),
                14,
                10,
                10,
                2,
                37,
                2,
                0.25,
                True,
                None,
                None,
            ),
            (
                "test_compute_compare_with_compound_shaping2",
                GaugeFactory(rows=4),
                20,
                8,
                10,
                6,
                5,
                6,
                2.25,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_full(
                larger_stitches,
                smaller_stitches,
                max_vertical_height,
                gauge,
                even_spacing=True,
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertFalse(sr.max_distance_constraint_hit)

    def test_compute_full_negative_height_even(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            EdgeShapingResult.compute_shaping_full(20, 10, -1, gauge, even_spacing=True)

    def test_compute_full_with_max_distance_fraction_rows_and_even(self):
        gauge = GaugeFactory(rows=4)
        sr = EdgeShapingResult.compute_shaping_full(20, 16, 5, gauge, True, 1.1)
        self.assertEqual(sr.rows_between_standard_shaping_rows, 3)
        self.assertEqual(sr.shaping_vertical_play, 3.75)
        self.assertEqual(sr.num_standard_shaping_rows, 2)
        self.assertEqual(sr.num_total_shaping_rows(), 2)
        self.assertEqual(sr.constraints_met, True)
        self.assertEqual(sr.best_larger_stitches, None)
        self.assertEqual(sr.best_smaller_stitches, None)
        self.assertTrue(sr.max_distance_constraint_hit)

    def test_compute_partial(self):

        vectors = [
            # name
            # larger_stitches,
            # smaller_stitches,
            # total_rows,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            ("test_compute_shaping_straight", 20, 20, 35, 0, None, 0, True, None, None),
            (
                "test_compute_shaping_single_shaping",
                22,
                20,
                20,
                1,
                None,
                1,
                True,
                None,
                None,
            ),
            ("test_compute_shaping1", 20, 10, 40, 5, 8, 5, True, None, None),
            ("test_compute_shaping2", 20, 10, 20, 5, 3, 5, True, None, None),
            ("test_compute_shaping3", 20, 12, 4, 4, 0, 4, True, None, None),
            (
                "test_compute_shaping_insufficient_vertical_room",
                20,
                10,
                4,
                4,
                0,
                4,
                False,
                18,
                12,
            ),
            ("test_compute_shaping_no_height", 20, 10, 0, 0, None, 0, False, 10, 20),
            ("test_shaping_too_much_height", 14, 10, 40, 2, 38, 2, True, None, None),
        ]

        for (
            name,
            larger_stitches,
            smaller_stitches,
            total_rows,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_partial(
                larger_stitches, smaller_stitches, total_rows
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertIsNone(sr.shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertFalse(sr.max_distance_constraint_hit)

    def test_compute_partial_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            EdgeShapingResult.compute_shaping_partial(20, 10, -4, gauge)

    def test_compute_partial_max_distance(self):

        vectors = [
            # name
            # larger_stitches,
            # smaller_stitches,
            # total_rows,
            # max distance
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_with_max_distance",
                20,
                16,
                20,
                4,
                2,
                4,
                2,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            larger_stitches,
            smaller_stitches,
            total_rows,
            max_distance_between_shaping_rows,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_partial(
                larger_stitches,
                smaller_stitches,
                total_rows,
                False,
                max_distance_between_shaping_rows,
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertIsNone(sr.shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertTrue(sr.max_distance_constraint_hit)

    def test_compute_partial_even(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight_even",
                20,
                20,
                35,
                0,
                None,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping_even",
                22,
                20,
                20,
                1,
                None,
                1,
                True,
                None,
                None,
            ),
            ("test_compute_shaping1_even", 20, 10, 40, 5, 7, 5, True, None, None),
            ("test_compute_shaping2_even", 20, 10, 20, 5, 3, 5, True, None, None),
            ("test_compute_shaping3_even", 20, 12, 7, 4, 1, 4, True, None, None),
            (
                "test_compute_shaping_insufficient_vertical_room_even",
                20,
                10,
                5,
                3,
                1,
                3,
                False,
                16,
                14,
            ),
            (
                "test_compute_shaping_no_height_even",
                20,
                10,
                0,
                0,
                None,
                0,
                False,
                10,
                20,
            ),
            (
                "test_shaping_too_much_height_even",
                14,
                10,
                40,
                2,
                37,
                2,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            larger_stitches,
            smaller_stitches,
            total_rows,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeShapingResult.compute_shaping_partial(
                larger_stitches, smaller_stitches, total_rows, even_spacing=True
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertIsNone(sr.shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)
            self.assertFalse(sr.max_distance_constraint_hit)

    def test_compute_partial_negative_height_even(self):
        with self.assertRaises(AssertionError):
            EdgeShapingResult.compute_shaping_partial(20, 10, -4, even_spacing=True)

    def test_compute_partial_with_max_distance_fraction_rows_and_even(self):
        sr = EdgeShapingResult.compute_shaping_partial(20, 16, 20, True, 4)
        self.assertEqual(sr.rows_between_standard_shaping_rows, 3)
        self.assertIsNone(sr.shaping_vertical_play)
        self.assertEqual(sr.num_standard_shaping_rows, 2)
        self.assertEqual(sr.num_total_shaping_rows(), 2)
        self.assertEqual(sr.constraints_met, True)
        self.assertEqual(sr.best_larger_stitches, None)
        self.assertEqual(sr.best_smaller_stitches, None)
        self.assertTrue(sr.max_distance_constraint_hit)


class EdgeCompoundShapingResultTests(TestCase):

    def test_clean(self):

        good_vectors = [
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_alternate_shaping_rows
            # rows_after_alternate_shaping_rows
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (0, None, 0, None, True, None, None),
            (1, None, 0, None, True, None, None),
            (2, 0, 0, None, True, None, None),
            (2, 2, 0, None, True, None, None),
            (2, 2, 1, 1, True, None, None),
            (2, 2, 1, 3, True, None, None),
            (2, 2, 2, 1, True, None, None),
            (2, 2, 2, 3, True, None, None),
        ]

        for i, (
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_alternate_shaping_rows,
            rows_after_alternate_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in enumerate(good_vectors, start=1):

            sr = EdgeCompoundShapingResult()
            sr.num_standard_shaping_rows = num_standard_shaping_rows
            sr.rows_between_standard_shaping_rows = rows_between_standard_shaping_rows
            sr.num_alternate_shaping_rows = num_alternate_shaping_rows
            sr.rows_after_alternate_shaping_rows = rows_after_alternate_shaping_rows
            sr.constraints_met = constraints_met
            sr.best_larger_stitches = best_larger_stitches
            sr.best_smaller_stitches = best_smaller_stitches

            sr.clean()

        bad_vectors = [
            (None, None, None, None, True, None, None),
            (0, None, 0, None, True, None, None),
            (1, None, 1, None, True, None, None),
            (1, 0, 1, None, True, None, None),
            (1, 1, 1, None, True, None, None),
            (1, 1, 1, 0, True, None, None),
            (0, None, 1, 2, True, None, None),
            (2, 2, 3, 1, True, None, None),
            (2, 2, 3, 3, True, None, None),
            (2, 6, 2, 4, True, None, None),
            (2, 2, 2, 2, True, None, None),
            (2, 2, 2, 4, True, None, None),
            (3, 5, 2, 5, True, None, None),
        ]

        for i, (
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_alternate_shaping_rows,
            rows_after_alternate_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in enumerate(bad_vectors, start=1):
            sr = EdgeCompoundShapingResult()
            sr.num_standard_shaping_rows = num_standard_shaping_rows
            sr.rows_between_standard_shaping_rows = rows_between_standard_shaping_rows
            sr.num_alternate_shaping_rows = num_alternate_shaping_rows
            sr.rows_after_alternate_shaping_rows = rows_after_alternate_shaping_rows

            with self.assertRaises(AssertionError):
                sr.clean()

    def test_num_total_rows(self):

        vectors = [
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_alternate_shaping_rows
            # rows_after_alternate_shaping_rows
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            # goal_total_rows
            (0, None, 0, None, True, None, None, 0),
            (1, None, 0, None, True, None, None, 1),
            (2, 0, 0, None, True, None, None, 2),
            (2, 2, 0, None, True, None, None, 4),
            (2, 2, 1, 1, True, None, None, 7),
            (2, 2, 1, 3, True, None, None, 7),
            (2, 2, 2, 1, True, None, None, 9),
            (2, 2, 2, 3, True, None, None, 11),
            (3, 6, 2, 7, True, None, None, 30),
            (3, 6, 2, 5, True, None, None, 28),
            (3, 6, 3, 7, True, None, None, 38),
            (3, 6, 3, 5, True, None, None, 34),
        ]

        for i, (
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_alternate_shaping_rows,
            rows_after_alternate_shaping_rows,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
            goal_total_rows,
        ) in enumerate(vectors, start=1):

            sr = EdgeCompoundShapingResult()
            sr.num_standard_shaping_rows = num_standard_shaping_rows
            sr.rows_between_standard_shaping_rows = rows_between_standard_shaping_rows
            sr.num_alternate_shaping_rows = num_alternate_shaping_rows
            sr.rows_after_alternate_shaping_rows = rows_after_alternate_shaping_rows
            sr.constraints_met = constraints_met
            sr.best_larger_stitches = best_larger_stitches
            sr.best_smaller_stitches = best_smaller_stitches
            sr.clean()

            self.assertEqual(sr.num_total_rows(), goal_total_rows, i)

    def test_compute(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_alternate_shaping_rows
            # rows_after_alternate_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                GaugeFactory(rows=4),
                20,
                20,
                5,
                0,
                None,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                0,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_standard_shaping",
                GaugeFactory(rows=4),
                20,
                10,
                9.25,
                5,
                8,
                0,
                None,
                5,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_compound_shaping1",
                GaugeFactory(rows=4),
                20,
                10,
                8.75,
                3,
                7,
                2,
                8,
                5,
                0.25,
                True,
                None,
                None,
            ),
            (
                "test_compute_compound_shaping2",
                GaugeFactory(rows=4),
                20,
                8,
                10,
                3,
                7,
                3,
                6,
                6,
                0.25,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_alternate_shaping_rows,
            rows_after_alternate_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = EdgeCompoundShapingResult.compute_shaping(
                larger_stitches, smaller_stitches, max_vertical_height, gauge
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_alternate_shaping_rows, num_alternate_shaping_rows)
            self.assertEqual(
                sr.rows_after_alternate_shaping_rows, rows_after_alternate_shaping_rows
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_compute_full_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            EdgeCompoundShapingResult.compute_shaping(20, 10, -1, gauge)


class TorsoShapingResultTests(TestCase):

    def test_compute_shaping(self):

        vectors = [
            # name
            # larger stitches,
            # smaller stiches,
            # max vertical height,
            # gauge
            # allow_double_darts
            # allow_triple_darts
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows,
            # use_double_darts,
            # num_doulbe_dart_shaping_rows,
            # use_triple_darts,
            # num_triple_dart_shaping_rows,
            # num_total_shaping_rows,
            # shaping_vertical_play,
            # constraints_met,
            # best_larger_stitches,
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                20,
                20,
                5,
                GaugeFactory(),
                True,
                True,
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                22,
                20,
                5,
                GaugeFactory(rows=4),
                True,
                True,
                1,
                None,
                False,
                0,
                False,
                0,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1",
                20,
                10,
                10,
                GaugeFactory(rows=4),
                True,
                True,
                5,
                7,
                False,
                0,
                False,
                0,
                5,
                1.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2",
                20,
                10,
                5,
                GaugeFactory(rows=4),
                True,
                True,
                5,
                3,
                False,
                0,
                False,
                0,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3",
                20,
                10,
                4.25,
                GaugeFactory(rows=4),
                True,
                True,
                5,
                3,
                False,
                0,
                False,
                0,
                5,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_1",
                20,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                True,
                4,
                3,
                True,
                1,
                False,
                0,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_2",
                24,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                True,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_3",
                24,
                10,
                3.25,
                GaugeFactory(rows=4),
                True,
                True,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_1",
                26,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                True,
                3,
                3,
                True,
                3,
                True,
                1,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_2",
                32,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_3",
                34,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0.75,
                False,
                32,
                12,
            ),
            (
                "test_compute_shaping_triple_4",
                34,
                10,
                3.25,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0,
                False,
                32,
                12,
            ),
            (
                "test_compute_shaping_no_vertical_room",
                34,
                10,
                0.1,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                None,
                False,
                10,
                34,
            ),
            (
                "test_shaping_triple_but_no_double",
                14,
                10,
                0.5,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                3,
                False,
                0,
                True,
                1,
                1,
                0.25,
                True,
                None,
                None,
            ),
            (
                "test_shaping_no_height",
                14,
                10,
                0,
                GaugeFactory(rows=4),
                True,
                True,
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                None,
                False,
                10,
                14,
            ),
            (
                "test_shaping_too_much_height",
                14,
                10,
                10,
                GaugeFactory(rows=4),
                True,
                True,
                2,
                7,
                False,
                0,
                False,
                0,
                2,
                7.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_no_doubles1",
                20,
                10,
                4,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0.75,
                False,
                18,
                12,
            ),
            (
                "test_compute_shaping_no_doubles2",
                24,
                10,
                4,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0.75,
                False,
                18,
                16,
            ),
            (
                "test_compute_shaping_no_doubles3",
                24,
                10,
                3.25,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0,
                False,
                18,
                16,
            ),
            (
                "test_compute_shaping_double_no_triple_1",
                26,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                False,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0.75,
                False,
                24,
                12,
            ),
            (
                "test_compute_shaping_double_no_triple_2",
                32,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                False,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0.75,
                False,
                24,
                18,
            ),
            (
                "test_compute_shaping_double_no_triple_3",
                34,
                10,
                4,
                GaugeFactory(rows=4),
                True,
                False,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0.75,
                False,
                24,
                20,
            ),
            (
                "test_compute_shaping_double_no_triple_4",
                34,
                10,
                3.25,
                GaugeFactory(rows=4),
                True,
                False,
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0,
                False,
                24,
                20,
            ),
            (
                "test_compute_shaping_no_double_no_triple_1",
                26,
                10,
                4,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0.75,
                False,
                18,
                18,
            ),
            (
                "test_compute_shaping_no_double_no_triple_2",
                32,
                10,
                4,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0.75,
                False,
                18,
                24,
            ),
            (
                "test_compute_shaping_no_double_no_triple_3",
                34,
                10,
                4,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0.75,
                False,
                18,
                26,
            ),
            (
                "test_compute_shaping_no_double_no_triple_4",
                34,
                10,
                3.25,
                GaugeFactory(rows=4),
                False,
                False,
                4,
                3,
                False,
                0,
                False,
                0,
                4,
                0,
                False,
                18,
                26,
            ),
        ]

        for (
            name,
            num_larger_stitches,
            num_smaller_stitches,
            max_vertical_height,
            gauge,
            allow_double_darts,
            allow_triple_darts,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            use_double_darts,
            num_double_dart_shaping_rows,
            use_triple_darts,
            num_triple_dart_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = TorsoShapingResult.compute_shaping(
                num_larger_stitches,
                num_smaller_stitches,
                max_vertical_height,
                gauge,
                allow_double_darts=allow_double_darts,
                allow_triple_darts=allow_triple_darts,
            )
            with self.subTest(name=name):
                self.assertEqual(
                    sr.num_standard_shaping_rows, num_standard_shaping_rows
                )
                self.assertEqual(
                    sr.rows_between_standard_shaping_rows,
                    rows_between_standard_shaping_rows,
                )
                self.assertEqual(sr.use_double_darts(), use_double_darts)
                self.assertEqual(
                    sr.num_double_dart_shaping_rows, num_double_dart_shaping_rows
                )
                self.assertEqual(sr.use_triple_darts(), use_triple_darts)
                self.assertEqual(
                    sr.num_triple_dart_shaping_rows, num_triple_dart_shaping_rows
                )
                self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
                self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
                self.assertEqual(sr.constraints_met, constraints_met)
                self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
                self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_shaping_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            TorsoShapingResult.compute_shaping(14, 10, -1, gauge)

    def test_error_condition(self):
        with self.assertRaises(AssertionError):
            TorsoShapingResult.compute_shaping(
                20,
                20,
                5,
                GaugeFactory(),
                allow_double_darts=False,
                allow_triple_darts=True,
            )


class SweaterPieceTests(TestCase):

    def test_compute_marker_shaping(self):

        vectors = [
            # name
            # larger stitches,
            # smaller stiches,
            # max vertical height,
            # gauge
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows,
            # use_double_darts,
            # num_doulbe_dart_shaping_rows,
            # use_triple_darts,
            # num_triple_dart_shaping_rows,
            # num_total_shaping_rows,
            # shaping_vertical_play,
            # constraints_met,
            # best_larger_stitches,
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                20,
                20,
                5,
                GaugeFactory(),
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                22,
                20,
                5,
                GaugeFactory(rows=4),
                1,
                None,
                False,
                0,
                False,
                0,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1",
                20,
                10,
                10,
                GaugeFactory(rows=4),
                5,
                7,
                False,
                0,
                False,
                0,
                5,
                1.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2",
                20,
                10,
                5,
                GaugeFactory(rows=4),
                5,
                3,
                False,
                0,
                False,
                0,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3",
                20,
                10,
                4.25,
                GaugeFactory(rows=4),
                5,
                3,
                False,
                0,
                False,
                0,
                5,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_1",
                20,
                10,
                4,
                GaugeFactory(rows=4),
                4,
                3,
                True,
                1,
                False,
                0,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_2",
                24,
                10,
                4,
                GaugeFactory(rows=4),
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_double_3",
                24,
                10,
                3.25,
                GaugeFactory(rows=4),
                4,
                3,
                True,
                3,
                False,
                0,
                7,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_1",
                26,
                10,
                4,
                GaugeFactory(rows=4),
                3,
                3,
                True,
                3,
                True,
                1,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_2",
                32,
                10,
                4,
                GaugeFactory(rows=4),
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_triple_3",
                34,
                10,
                4,
                GaugeFactory(rows=4),
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0.75,
                False,
                32,
                12,
            ),
            (
                "test_compute_shaping_triple_4",
                34,
                10,
                3.25,
                GaugeFactory(rows=4),
                0,
                3,
                True,
                3,
                True,
                4,
                7,
                0,
                False,
                32,
                12,
            ),
            (
                "test_compute_shaping_no_vertical_room",
                34,
                10,
                0.1,
                GaugeFactory(rows=4),
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                None,
                False,
                10,
                34,
            ),
            (
                "test_shaping_triple_but_no_double",
                14,
                10,
                0.5,
                GaugeFactory(rows=4),
                0,
                3,
                False,
                0,
                True,
                1,
                1,
                0.25,
                True,
                None,
                None,
            ),
            (
                "test_shaping_no_height",
                14,
                10,
                0,
                GaugeFactory(rows=4),
                0,
                None,
                False,
                0,
                False,
                0,
                0,
                None,
                False,
                10,
                14,
            ),
            (
                "test_shaping_too_much_height",
                14,
                10,
                10,
                GaugeFactory(rows=4),
                2,
                7,
                False,
                0,
                False,
                0,
                2,
                7.75,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            num_larger_stitches,
            num_smaller_stitches,
            max_vertical_height,
            gauge,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            use_double_darts,
            num_double_dart_shaping_rows,
            use_triple_darts,
            num_triple_dart_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = SweaterPiece.compute_marker_shaping(
                num_larger_stitches, num_smaller_stitches, max_vertical_height, gauge
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.use_double_darts(), use_double_darts)
            self.assertEqual(
                sr.num_double_dart_shaping_rows, num_double_dart_shaping_rows
            )
            self.assertEqual(sr.use_triple_darts(), use_triple_darts)
            self.assertEqual(
                sr.num_triple_dart_shaping_rows, num_triple_dart_shaping_rows
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_shaping_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            SweaterPiece.compute_marker_shaping(14, 10, -1, gauge)

    def test_compute_edge_shaping(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                GaugeFactory(),
                20,
                20,
                5,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1",
                GaugeFactory(rows=4),
                20,
                10,
                10,
                5,
                8,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2",
                GaugeFactory(rows=4),
                20,
                10,
                5,
                5,
                3,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3",
                GaugeFactory(rows=4),
                20,
                12,
                1,
                4,
                0,
                4,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_insufficient_vertical_room",
                GaugeFactory(rows=4),
                20,
                10,
                1,
                4,
                0,
                4,
                None,
                False,
                18,
                12,
            ),
            (
                "test_compute_shaping_no_height",
                GaugeFactory(rows=4),
                20,
                10,
                0,
                0,
                None,
                0,
                None,
                False,
                10,
                20,
            ),
            (
                "test_shaping_too_much_height",
                GaugeFactory(rows=4),
                14,
                10,
                10,
                2,
                38,
                2,
                0,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = SweaterPiece.compute_edge_shaping(
                larger_stitches, smaller_stitches, max_vertical_height, gauge
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_compute_shaping_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            SweaterPiece.compute_edge_shaping(20, 10, -1, gauge)

    def test_compute_edge_shaping_max_distance(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # max distance
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_with_max_distance",
                GaugeFactory(rows=4),
                20,
                16,
                5,
                1,
                2,
                4,
                2,
                3.5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_with_max_distance_fractional_rows",
                GaugeFactory(rows=4),
                20,
                16,
                5,
                1.1,
                2,
                4,
                2,
                3.5,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            max_distance_between_shaping_rows,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = SweaterPiece.compute_edge_shaping(
                larger_stitches,
                smaller_stitches,
                max_vertical_height,
                gauge,
                False,
                max_distance_between_shaping_rows,
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_compute_edge_shaping_even(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight_even",
                GaugeFactory(),
                20,
                20,
                5,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping_even",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping1_even",
                GaugeFactory(rows=4),
                20,
                10,
                10,
                5,
                7,
                5,
                1.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping2_even",
                GaugeFactory(rows=4),
                20,
                10,
                5,
                5,
                3,
                5,
                0.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping3_even",
                GaugeFactory(rows=4),
                20,
                12,
                1.75,
                4,
                1,
                4,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_insufficient_vertical_room_even",
                GaugeFactory(rows=4),
                20,
                10,
                1.25,
                3,
                1,
                3,
                None,
                False,
                16,
                14,
            ),
            (
                "test_compute_shaping_no_height_even",
                GaugeFactory(rows=4),
                20,
                10,
                0,
                0,
                None,
                0,
                None,
                False,
                10,
                20,
            ),
            (
                "test_shaping_too_much_height_even",
                GaugeFactory(rows=4),
                14,
                10,
                10,
                2,
                37,
                2,
                0.25,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = SweaterPiece.compute_edge_shaping(
                larger_stitches,
                smaller_stitches,
                max_vertical_height,
                gauge,
                even_spacing=True,
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_compute_shaping_negative_height_even(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            SweaterPiece.compute_edge_shaping(20, 10, -1, gauge, even_spacing=True)

    def test_compute_shaping_with_max_distance_fraction_rows_and_even(self):
        gauge = GaugeFactory(rows=4)
        sr = SweaterPiece.compute_edge_shaping(20, 16, 5, gauge, True, 1.1)
        self.assertEqual(sr.rows_between_standard_shaping_rows, 3)
        self.assertEqual(sr.shaping_vertical_play, 3.75)
        self.assertEqual(sr.num_standard_shaping_rows, 2)
        self.assertEqual(sr.num_total_shaping_rows(), 2)
        self.assertEqual(sr.constraints_met, True)
        self.assertEqual(sr.best_larger_stitches, None)
        self.assertEqual(sr.best_smaller_stitches, None)

    def test_compute_compound_edge_shaping(self):

        vectors = [
            # name
            # gauge
            # larger_stitches,
            # smaller_stitches,
            # max_vertical_height,
            # num_standard_shaping_rows,
            # rows_between_standard_shaping_rows
            # num_alternate_shaping_rows
            # rows_after_alternate_shaping_rows
            # num_total_shaping_rows
            # shaping_vertical_play
            # constraints_met
            # best_larger_stitches
            # best_smaller_stitches
            (
                "test_compute_shaping_straight",
                GaugeFactory(rows=4),
                20,
                20,
                5,
                0,
                None,
                0,
                None,
                0,
                5,
                True,
                None,
                None,
            ),
            (
                "test_compute_shaping_single_shaping",
                GaugeFactory(rows=4),
                22,
                20,
                5,
                1,
                None,
                0,
                None,
                1,
                4.75,
                True,
                None,
                None,
            ),
            (
                "test_compute_standard_shaping",
                GaugeFactory(rows=4),
                20,
                10,
                9.25,
                5,
                8,
                0,
                None,
                5,
                0,
                True,
                None,
                None,
            ),
            (
                "test_compute_compound_shaping1",
                GaugeFactory(rows=4),
                20,
                10,
                8.75,
                3,
                7,
                2,
                8,
                5,
                0.25,
                True,
                None,
                None,
            ),
            (
                "test_compute_compound_shaping2",
                GaugeFactory(rows=4),
                20,
                8,
                10,
                3,
                7,
                3,
                6,
                6,
                0.25,
                True,
                None,
                None,
            ),
        ]

        for (
            name,
            gauge,
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            num_standard_shaping_rows,
            rows_between_standard_shaping_rows,
            num_alternate_shaping_rows,
            rows_after_alternate_shaping_rows,
            num_total_shaping_rows,
            shaping_vertical_play,
            constraints_met,
            best_larger_stitches,
            best_smaller_stitches,
        ) in vectors:

            sr = SweaterPiece.compute_compound_edge_shaping(
                larger_stitches, smaller_stitches, max_vertical_height, gauge
            )
            self.assertEqual(sr.num_standard_shaping_rows, num_standard_shaping_rows)
            self.assertEqual(
                sr.rows_between_standard_shaping_rows,
                rows_between_standard_shaping_rows,
            )
            self.assertEqual(sr.num_alternate_shaping_rows, num_alternate_shaping_rows)
            self.assertEqual(
                sr.rows_after_alternate_shaping_rows, rows_after_alternate_shaping_rows
            )
            self.assertEqual(sr.num_total_shaping_rows(), num_total_shaping_rows)
            self.assertEqual(sr.shaping_vertical_play, shaping_vertical_play, name)
            self.assertEqual(sr.constraints_met, constraints_met)
            self.assertEqual(sr.best_larger_stitches, best_larger_stitches)
            self.assertEqual(sr.best_smaller_stitches, best_smaller_stitches)

    def test_compute_compound_edge_shaping_negative_height(self):
        gauge = GaugeFactory(rows=4)
        with self.assertRaises(AssertionError):
            SweaterPiece.compute_compound_edge_shaping(20, 10, -1, gauge)


class GradedSweaterPatternPiecesTest(TestCase):

    def test_make_pullover_sleeved(self):
        pspec = GradedSweaterPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gpp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(len(gpp.sweater_backs), 5)
        self.assertEqual(len(gpp.sweater_fronts), 5)
        self.assertEqual(len(gpp.sleeves), 5)
        self.assertEqual(len(gpp.vest_backs), 0)
        self.assertEqual(len(gpp.vest_fronts), 0)
        self.assertEqual(len(gpp.cardigan_sleeveds), 0)
        self.assertEqual(len(gpp.cardigan_vests), 0)

        # check sort keys
        for grade in gcs.graded_garment_parameters.all_grades:
            back = GradedSweaterBack.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            front = GradedSweaterFront.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            sleeve = GradedSleeve.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            bust = back.actual_bust + front.actual_bust
            self.assertEqual(front.sort_key, bust)
            self.assertEqual(back.sort_key, bust)
            self.assertEqual(sleeve.sort_key, bust)

    def test_make_pullover_vest(self):
        pspec = GradedVestPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gpp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(len(gpp.sweater_backs), 0)
        self.assertEqual(len(gpp.sweater_fronts), 0)
        self.assertEqual(len(gpp.sleeves), 0)
        self.assertEqual(len(gpp.vest_backs), 5)
        self.assertEqual(len(gpp.vest_fronts), 5)
        self.assertEqual(len(gpp.cardigan_sleeveds), 0)
        self.assertEqual(len(gpp.cardigan_vests), 0)

        # check sort keys
        for grade in gcs.graded_garment_parameters.all_grades:
            back = GradedVestBack.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            front = GradedVestFront.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            bust = back.actual_bust + front.actual_bust
            self.assertEqual(front.sort_key, bust)
            self.assertEqual(back.sort_key, bust)

    def test_make_cardigan_sleeved(self):
        pspec = GradedCardiganPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gpp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(len(gpp.sweater_backs), 5)
        self.assertEqual(len(gpp.sweater_fronts), 0)
        self.assertEqual(len(gpp.sleeves), 5)
        self.assertEqual(len(gpp.vest_backs), 0)
        self.assertEqual(len(gpp.vest_fronts), 0)
        self.assertEqual(len(gpp.cardigan_sleeveds), 5)
        self.assertEqual(len(gpp.cardigan_vests), 0)

        # check sort keys
        for grade in gcs.graded_garment_parameters.all_grades:
            back = GradedSweaterBack.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            front = GradedCardiganSleeved.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            sleeve = GradedSleeve.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            bust = back.actual_bust + front.total_front_finished_bust
            self.assertEqual(front.sort_key, bust)
            self.assertEqual(back.sort_key, bust)
            self.assertEqual(sleeve.sort_key, bust)

    def test_make_cardigan_vest(self):
        pspec = GradedCardiganVestPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gpp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(len(gpp.sweater_backs), 0)
        self.assertEqual(len(gpp.sweater_fronts), 0)
        self.assertEqual(len(gpp.sleeves), 0)
        self.assertEqual(len(gpp.vest_backs), 5)
        self.assertEqual(len(gpp.vest_fronts), 0)
        self.assertEqual(len(gpp.cardigan_sleeveds), 0)
        self.assertEqual(len(gpp.cardigan_vests), 5)

        # check sort keys
        for grade in gcs.graded_garment_parameters.all_grades:
            back = GradedVestBack.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            front = GradedCardiganVest.objects.get(
                graded_pattern_pieces=gpp, schematic__gp_grade=grade
            )
            bust = back.actual_bust + front.total_front_finished_bust
            self.assertEqual(front.sort_key, bust)
            self.assertEqual(back.sort_key, bust)

    def test_factory(self):
        GradedSweaterPatternPiecesFactory()

    def test_area_list(self):
        pspec = GradedCardiganVestPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gspp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(
            gspp.area_list(),
            [1044.6799999999998, 1146.8400000000001, 1249.64, 1356.8000000000002, 1470.8799999999999]
        )

    def test_yards(self):
        pspec = GradedCardiganVestPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gspp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        print(gspp.yards())
        self.assertEqual(
            gspp.yards(),
            [1472.0, 1615.0, 1760.0, 1911.0, 2072.0]
        )

    def test_total_neckline_pickup_stitches(self):
        pspec = GradedVestPatternSpecFactory()
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        gpp = GradedSweaterPatternPieces.make_from_schematic(gcs)
        self.assertEqual(len(gpp.vest_backs), 5)
        self.assertEqual(len(gpp.vest_fronts), 5)

        neckline_stitches_list = gpp.total_neckline_pickup_stitches()
        self.assertEqual(len(neckline_stitches_list), 5)

        goal_list = [
            x.neckline.stitches_to_pick_up() + y.neckline.stitches_to_pick_up()
            for (x, y) in zip(gpp.vest_backs, gpp.vest_fronts)
        ]
        self.assertEqual(goal_list, neckline_stitches_list)
