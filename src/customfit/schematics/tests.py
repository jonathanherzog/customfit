# -*- coding: utf-8 -*-


from django.core.exceptions import ValidationError
from django.test import TestCase

from customfit.garment_parameters.factories import IndividualGarmentParametersFactory
from customfit.test_garment.factories import (
    GradedPatternSpecFactory,
    GradedTestGarmentSchematicFactory,
    GradedTestPieceSchematicFactory,
    TestGarmentSchematicFactory,
    TestIndividualGarmentParametersFactory,
    TestPieceSchematicFactory,
)
from customfit.test_garment.models import TestGarmentSchematic, TestPieceSchematic
from customfit.userauth.factories import UserFactory


class _BasePieceSchematicTests(object):
    pass


class PieceSchematicsTests(TestCase, _BasePieceSchematicTests):

    def test_make_from_gp(self):
        igp = TestIndividualGarmentParametersFactory(test_field=3)
        tp = TestPieceSchematic.make_from_gp_and_container(igp)
        self.assertEqual(tp.test_field, 3.0)

    def test_add_self_to_schematic(self):
        ts = TestPieceSchematicFactory()
        ts.test_piece = None
        ts.save()

        tp = TestPieceSchematicFactory()
        tp.add_self_to_schematic(ts)
        self.assertEqual(ts.test_piece, tp)

    def test_get_garment(self):
        ts = TestGarmentSchematicFactory()
        tp = ts.test_piece
        ts2 = ts.testgarmentschematic
        self.assertEqual(ts, ts2)


class GradedPieceSchematicsTests(TestCase, _BasePieceSchematicTests):

    def test_add_self_to_schematic(self):
        piece_sch = GradedTestPieceSchematicFactory()
        garment_sch = GradedTestGarmentSchematicFactory()

        piece_sch.add_self_to_schematic(garment_sch)
        piece_sch.save()

        self.assertEqual(piece_sch.construction_schematic, garment_sch)
        self.assertIn(piece_sch, garment_sch.all_grades)

    def test_get_spec_source(self):
        gps = GradedPatternSpecFactory()
        piece_sch = GradedTestPieceSchematicFactory(
            construction_schematic__graded_garment_parameters__pattern_spec=gps
        )
        self.assertEqual(piece_sch.get_spec_source(), gps)


class _BaseConstructionSchematicTests(object):

    pass


class ConstructionSchematicTests(TestCase, _BaseConstructionSchematicTests):

    factory = TestGarmentSchematicFactory

    def test_name(self):
        cs = self.factory(individual_garment_parameters__pattern_spec__name="test name")
        self.assertEqual(cs.name, cs.individual_garment_parameters.name)

    def test_user(self):
        cs = self.factory()
        self.assertEqual(cs.user, cs.individual_garment_parameters.user)

    def test_spec_source_patternspec(self):
        cs = TestGarmentSchematicFactory()
        self.assertEqual(
            cs.get_spec_source(), cs.individual_garment_parameters.pattern_spec
        )

    def test_unicode(self):
        user = UserFactory(username="betty")
        cs = TestGarmentSchematicFactory(
            individual_garment_parameters__pattern_spec__name="test name",
            individual_garment_parameters__user=user,
        )
        self.assertEqual(str(cs), "TestGarmentSchematic/test name/betty")

    def test_save(self):
        cs = TestGarmentSchematicFactory()

        # sanity tests
        self.assertFalse(cs.customized)
        self.assertNotEqual(cs.test_piece.test_field, 10)

        # change things
        cs.customized = True
        cs.test_piece.test_field = 10
        cs.save()

        # test save
        cs.refresh_from_db()
        self.assertTrue(cs.customized)
        test_piece = cs.test_piece
        test_piece.refresh_from_db()
        self.assertEqual(test_piece.test_field, 10)

    def test_delete(self):
        cs = TestGarmentSchematicFactory()
        cs_id = cs.id
        tp_id = cs.test_piece.id

        cs.delete()
        self.assertFalse(TestGarmentSchematic.objects.filter(id=cs_id).exists())
        self.assertFalse(TestPieceSchematic.objects.filter(id=tp_id).exists())

    def test_clean(self):
        cs = TestGarmentSchematicFactory()
        cs.test_piece.test_field = 10
        cs.creation_date = None

        with self.assertRaises(ValidationError):
            cs.clean()

        try:
            cs.clean()
        except ValidationError as ve:
            # Note that this doesn't include the field-level error in cs.
            # This is because clean() doesn't check fields
            self.assertEqual(ve.messages, ["Boom!"])

    def test_clean_fields(self):
        cs = TestGarmentSchematicFactory()
        cs.test_piece.test_field = 10
        cs.creation_date = None

        with self.assertRaises(ValidationError):
            cs.clean_fields()

        try:
            cs.clean_fields()
        except ValidationError as ve:
            # Note that this doesn't include tp's error.
            # This is because clean_fields() doesn't run clean()
            self.assertEqual(ve.messages, ["This field cannot be null."])
            self.assertEqual(
                ve.message_dict, {"creation_date": ["This field cannot be null."]}
            )

    def test_clean_fields2(self):
        cs = TestGarmentSchematicFactory()
        cs.test_piece.test_field = None
        cs.creation_date = None

        with self.assertRaises(ValidationError):
            cs.clean_fields()

        try:
            cs.clean_fields()
        except ValidationError as ve:
            # Note that this doesn't include tp's error.
            # This is because our implementation of clean_fields() returns at the first error
            self.assertEqual(ve.messages, ["This field cannot be null."])
            self.assertEqual(
                ve.message_dict, {"creation_date": ["This field cannot be null."]}
            )

    def test_clean_fields3(self):
        cs = TestGarmentSchematicFactory()
        cs.test_piece.test_field = None

        with self.assertRaises(ValidationError):
            cs.clean_fields()

        try:
            cs.clean_fields()
        except ValidationError as ve:
            # Proving we do get the field-error from the sub-piece
            self.assertEqual(ve.messages, ["This field cannot be null."])
            self.assertEqual(
                ve.message_dict, {"test_field": ["This field cannot be null."]}
            )

    def test_full_clean(self):
        cs = TestGarmentSchematicFactory()
        cs.test_piece.test_field = 10
        cs.creation_date = None

        with self.assertRaises(ValidationError):
            cs.full_clean()

        try:
            cs.full_clean()
        except ValidationError as ve:
            self.assertEqual(
                set(ve.messages), set(["Boom!", "This field cannot be null."])
            )


class GradedConstructionSchematicTests(TestCase, _BaseConstructionSchematicTests):

    factory = GradedTestGarmentSchematicFactory

    def test_name(self):
        cs = self.factory(graded_garment_parameters__pattern_spec__name="test name")
        self.assertEqual(cs.name, "test name")

    def test_user(self):
        cs = self.factory()
        self.assertEqual(cs.user, cs.graded_garment_parameters.user)

    def test_spec_source(self):
        cs = self.factory()
        self.assertEqual(
            cs.get_spec_source(), cs.graded_garment_parameters.pattern_spec
        )

    def test_get_gp(self):
        gcsh = self.factory()
        self.assertEqual(gcsh.get_gp(), gcsh.graded_garment_parameters)
