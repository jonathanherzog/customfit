# -*- coding: utf-8 -*-


from django.test import TestCase

from .factories import (
    GradedTestGarmentParametersFactory,
    GradedTestGarmentParametersGradeFactory,
    GradedTestGarmentSchematicFactory,
    GradedTestPatternPiecesFactory,
    GradedTestPatternSpecFactory,
    GradedTestPieceSchematicFactory,
    TestPatternPieceFactory,
    TestPatternPiecesFactory,
    TestPatternSpecFactory,
)
from .models import (
    GradedTestGarmentParameters,
    GradedTestGarmentSchematic,
    GradedTestPattern,
    GradedTestPatternPiece,
    GradedTestPatternPieces,
)


class GradedTestGarmentParametersTests(TestCase):

    def test_make_from_patternspec(self):
        gps = GradedTestPatternSpecFactory()
        self.assertEqual(len(gps.all_grades), 5)

        ggp = GradedTestGarmentParameters.make_from_patternspec(gps.user, gps)
        self.assertIsNotNone(ggp.id)
        self.assertEqual(len(ggp.all_grades), 5)

        bust_circs = set(g.bust_circ for g in gps.all_grades)
        test_fields = set(g.test_field_from_body for g in ggp.all_grades)
        self.assertEqual(bust_circs, test_fields)
        self.assertEqual(len(bust_circs), 5)


class GradedTestPieceSchematicTests(TestCase):

    def test_get_values(self):
        grade = GradedTestGarmentParametersGradeFactory(test_field_from_body=28)
        self.assertEqual(grade.test_field_from_body, 28)  # sanity check
        ps = GradedTestPieceSchematicFactory()
        ps._get_values_from_gp_and_grade(grade.graded_garment_parameters, grade)
        ps.save()
        ps.refresh_from_db()
        self.assertIsNotNone(ps.id)
        self.assertEqual(ps.test_field_from_body, 28)


class GradedTestGarmentSchematicTests(TestCase):

    def test_make_from_gp(self):
        gp = GradedTestGarmentParametersFactory()
        gtgs = GradedTestGarmentSchematic.make_from_garment_parameters(gp)

        self.assertIsNotNone(gtgs.id)
        self.assertEqual(gtgs.graded_garment_parameters, gp)
        self.assertEqual(len(gtgs.all_grades), 5)

        piece_field_values = set(p.test_field_from_body for p in gtgs.all_grades)
        gp_values = set(s.test_field_from_body for s in gp.all_grades)
        self.assertEqual(piece_field_values, gp_values)
        self.assertEqual(len(piece_field_values), 5)


class GradedTestPatternPieceTests(TestCase):

    def test_make_from_schematic_and_container(self):
        container = GradedTestPatternPiecesFactory()
        schematic = GradedTestPieceSchematicFactory(test_field_from_body=17)
        piece_sch = GradedTestPatternPiece.make_from_schematic_and_container(
            schematic, container
        )

        self.assertIsNotNone(piece_sch.id)
        piece_sch.refresh_from_db()
        self.assertEqual(piece_sch.test_field, 17)
        self.assertEqual(piece_sch.graded_pattern_pieces, container)


class GradedTestPatternPiecesTests(TestCase):

    def test_make_from_schematic(self):
        gtgs = GradedTestGarmentSchematicFactory()
        self.assertEqual(gtgs.all_grades.count(), 5)  # sanity check

        gpps = GradedTestPatternPieces.make_from_schematic(gtgs)
        self.assertEqual(gpps.schematic, gtgs)
        self.assertEqual(gpps.all_pieces.count(), 5)

        piece_field_values = set(p.test_field for p in gpps.all_pieces)
        schematic_field_values = set(s.test_field_from_body for s in gtgs.all_grades)
        self.assertEqual(piece_field_values, schematic_field_values)
        self.assertEqual(len(piece_field_values), 5)

    def test_area_list(self):
        gpp = GradedTestPatternPiecesFactory()
        self.assertEqual(gpp.area_list(), [1.0, 1.0, 1.0, 1.0, 1.0])


class GradedTestPatternTests(TestCase):

    def test_make_from_gpp(self):
        gpp = GradedTestPatternPiecesFactory()
        p = GradedTestPattern.make_from_graded_pattern_pieces(gpp)
        self.assertEqual(
            p.name, gpp.schematic.graded_garment_parameters.pattern_spec.name
        )
        self.assertEqual(p.pieces, gpp)
