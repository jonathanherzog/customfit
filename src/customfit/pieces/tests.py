# -*- coding: utf-8 -*-


from django.test import TestCase

from customfit.pieces.models import PatternPiece
from customfit.test_garment.factories import (
    GradedTestPatternPieceFactory,
    GradedTestPatternPiecesFactory,
    TestPatternPiecesFactory,
)


class IndividualPatternPiecesTests(TestCase):

    def test_delete(self):
        tpps = TestPatternPiecesFactory()
        piece = tpps.test_piece

        tpps.delete()
        with self.assertRaises(PatternPiece.DoesNotExist):
            piece.refresh_from_db()


class GradedPatternPiecesTests(TestCase):

    def test_all_pieces(self):
        gpps = GradedTestPatternPiecesFactory()
        self.assertEqual(len(gpps.all_pieces), 5)
        prev_pieces = list(gpps.all_pieces)

        gpp = GradedTestPatternPieceFactory(graded_pattern_pieces=gpps)

        gpp.refresh_from_db()
        gpps.refresh_from_db()

        self.assertEqual(len(gpps.all_pieces), 6)
        self.assertIn(gpp, list(gpps.all_pieces))
        for x in prev_pieces:
            self.assertIn(x, list(gpps.all_pieces))


class GradedPatternPieceTests(TestCase):

    def test_add_self_to_piece_list(self):
        gpps = GradedTestPatternPiecesFactory()
        self.assertEqual(len(gpps.all_pieces), 5)

        gpp = GradedTestPatternPieceFactory()
        gpp.add_self_to_piece_list(gpps)

        gpp.refresh_from_db()
        gpps.refresh_from_db()

        self.assertEqual(gpp.graded_pattern_pieces, gpps)
        self.assertIn(gpp, gpps.all_pieces)
        self.assertEqual(len(gpps.all_pieces), 6)

    def test_sort_order(self):
        gpps = GradedTestPatternPiecesFactory()
        self.assertEqual(len(gpps.all_pieces), 5)
        returned_order = [p.sort_key for p in gpps.all_pieces]
        sorted_order = sorted(returned_order)
        self.assertEqual(returned_order, sorted_order)
        self.assertLess(returned_order[0], returned_order[4])
