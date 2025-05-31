import logging
import unittest.mock as mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from customfit.stitches.models import Stitch
from customfit.stitches.tests import StitchFactory
from customfit.swatches.tests import SwatchFactory

from .. import helpers as CDC
from ..factories import (
    CowlDesignFactory,
    CowlGarmentSchematicFactory,
    CowlIndividualGarmentParametersFactory,
    CowlPatternFactory,
    CowlPatternPiecesFactory,
    CowlPatternSpecFactory,
    CowlPieceFactory,
    CowlPieceSchematicFactory,
    CowlRedoFactory,
    GradedCowlGarmentParametersFactory,
    GradedCowlGarmentSchematicFactory,
    GradedCowlPatternSpecFactory,
    GradedCowlPieceFactory,
)
from ..models import (
    AdditionalStitch,
    CowlGarmentSchematic,
    CowlIndividualGarmentParameters,
    CowlPattern,
    CowlPatternPieces,
    CowlPatternSpec,
    CowlPiece,
    CowlPieceSchematic,
    GradedCowlGarmentParameters,
    GradedCowlGarmentSchematic,
    GradedCowlPatternPieces,
    GradedCowlPiece,
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


class CowlRedoBaseTests(object):

    def test_total_height_in_inches(self):
        des = self.factory(height=CDC.COWL_HEIGHT_AVERAGE)
        self.assertEqual(des.total_height_in_inches(), 12)

    def test_circumference_in_inches(self):
        des = self.factory(circumference=CDC.COWL_CIRC_LARGE)
        self.assertEqual(des.circumference_in_inches(), 60)

    def test_height_text(self):
        test_vectors = [
            (CDC.COWL_HEIGHT_SHORT, "short height"),
            (CDC.COWL_HEIGHT_AVERAGE, "average height"),
            (CDC.COWL_HEIGHT_TALL, "tall height"),
            (CDC.COWL_HEIGHT_EXTRA_TALL, "extra tall height"),
        ]
        for height, goal in test_vectors:
            des = self.factory(height=height)
            self.assertEqual(des.height_text(), goal, (height, goal))

    def test_circumference_text(self):
        test_vectors = [
            (CDC.COWL_CIRC_EXTRA_SMALL, "extra-small circumference"),
            (CDC.COWL_CIRC_SMALL, "small circumference"),
            (CDC.COWL_CIRC_MEDIUM, "medium circumference"),
            (CDC.COWL_CIRC_LARGE, "large circumference"),
        ]
        for circumference, goal in test_vectors:
            des = self.factory(circumference=circumference)
            self.assertEqual(des.circumference_text(), goal, (circumference, goal))


class CowlDesignBaseTests(CowlRedoBaseTests):

    def test_caston_repeats(self):

        des = self.factory(cast_on_x_mod=0, cast_on_mod_y=1)
        self.assertFalse(des.caston_repeats())

        des = self.factory(cast_on_x_mod=0, cast_on_mod_y=2)
        self.assertTrue(des.caston_repeats())

        des = self.factory(cast_on_x_mod=1, cast_on_mod_y=3)
        self.assertTrue(des.caston_repeats())

    def test_clean2(self):

        des = self.factory(height=CDC.COWL_HEIGHT_AVERAGE, edging_stitch_height=5)
        self.assertEqual(des.total_height_in_inches(), 12)  # sanity check
        with self.assertRaises(ValidationError):
            des.full_clean()

        des = self.factory(height=CDC.COWL_HEIGHT_AVERAGE, edging_stitch_height=4)
        with self.assertRaises(ValidationError):
            des.full_clean()

        des = self.factory(height=CDC.COWL_HEIGHT_AVERAGE, edging_stitch_height=2)
        # No execption, right?
        des.full_clean()


class CowlDesignTests(CowlDesignBaseTests, TestCase):

    factory = CowlDesignFactory

    def test_app_label(self):
        des = CowlDesignFactory()
        des.full_clean()
        # Note that 'cowls' is a magic string in the model-to-view framework we put in so that
        # top-level views can handle different garments. See design_wizard/views/garment_registry
        self.assertEqual(des._meta.app_label, "cowls")

    def test_compatible_swatch(self):
        swatch = SwatchFactory()
        stich = swatch.get_stitch()
        des = CowlDesignFactory()

        with mock.patch.object(Stitch, "is_compatible", return_value=True):
            self.assertTrue(des.compatible_swatch(swatch))

        with mock.patch.object(Stitch, "is_compatible", return_value=False):
            self.assertFalse(des.compatible_swatch(swatch))

    def test_isotope_classes(self):
        des = CowlDesignFactory()
        self.assertEqual(des.isotope_classes(), "cowl")

    def test_stitches_used(self):
        main_stitch = StitchFactory(name="main stitch")
        edging_stitch = StitchFactory(name="edging stitch")
        panel_stitch = StitchFactory(name="panel stitch")
        cable_stitch = StitchFactory(name="cable stitch")
        cabled_design = self.factory(
            main_stitch=main_stitch,
            edging_stitch=edging_stitch,
            panel_stitch=panel_stitch,
            cable_stitch=cable_stitch,
        )
        self.assertEqual(
            cabled_design.stitches_used(),
            [main_stitch, edging_stitch, panel_stitch, cable_stitch],
        )

    def test_stitches_used_additional_stitch(self):
        main_stitch = StitchFactory(name="main stitch")
        edging_stitch = StitchFactory(name="edging stitch")
        panel_stitch = StitchFactory(name="panel stitch")
        cable_stitch = StitchFactory(name="cable stitch")
        additional_stitch = StitchFactory(name="additional stitch")

        cabled_design = self.factory(
            main_stitch=main_stitch,
            edging_stitch=edging_stitch,
            panel_stitch=panel_stitch,
            cable_stitch=cable_stitch,
        )
        AdditionalStitch(design=cabled_design, stitch=additional_stitch).save()
        self.assertEqual(
            cabled_design.stitches_used(),
            [main_stitch, edging_stitch, panel_stitch, cable_stitch, additional_stitch],
        )

    def test_stitches_used_additional_stitch_deduplicate(self):
        main_stitch = StitchFactory(name="main stitch")
        edging_stitch = StitchFactory(name="edging stitch")
        panel_stitch = StitchFactory(name="panel stitch")
        cable_stitch = StitchFactory(name="cable stitch")

        cabled_design = self.factory(
            main_stitch=main_stitch,
            edging_stitch=edging_stitch,
            panel_stitch=panel_stitch,
            cable_stitch=cable_stitch,
        )
        AdditionalStitch(design=cabled_design, stitch=edging_stitch).save()
        self.assertEqual(
            cabled_design.stitches_used(),
            [main_stitch, edging_stitch, panel_stitch, cable_stitch],
        )

    def test_uses_stitch(self):
        main_stitch = StitchFactory(name="main stitch")
        edging_stitch = StitchFactory(name="edging stitch")
        panel_stitch = StitchFactory(name="panel stitch")
        cable_stitch = StitchFactory(name="cable stitch")
        additional_stitch = StitchFactory(name="additional stitch")
        new_stitch = StitchFactory(name="new stitch")

        cabled_design = self.factory(
            main_stitch=main_stitch,
            edging_stitch=edging_stitch,
            panel_stitch=panel_stitch,
            cable_stitch=cable_stitch,
        )
        AdditionalStitch(design=cabled_design, stitch=additional_stitch).save()

        self.assertTrue(cabled_design.uses_stitch(main_stitch))
        self.assertTrue(cabled_design.uses_stitch(additional_stitch))
        self.assertFalse(cabled_design.uses_stitch(new_stitch))


class CowlPatternspecTests(CowlDesignBaseTests, TestCase):

    factory = CowlPatternSpecFactory

    def test_app_label(self):
        des = CowlDesignFactory()
        des.full_clean()
        # Note that 'cowls' is a magic string in the model-to-view framework we put in so that
        # top-level views can handle different garments. See design_wizard/views/garment_registry
        self.assertEqual(des._meta.app_label, "cowls")

    def test_compatible_swatch(self):
        swatch = SwatchFactory()
        stich = swatch.get_stitch()
        des = CowlDesignFactory()

        with mock.patch.object(Stitch, "is_compatible", return_value=True):
            self.assertTrue(des.compatible_swatch(swatch))

        with mock.patch.object(Stitch, "is_compatible", return_value=False):
            self.assertFalse(des.compatible_swatch(swatch))

    def test_get_repeats_spec(self):
        swatch_with_repeats = SwatchFactory(
            rows_length=1,
            rows_number=5,
            stitches_length=1,
            stitches_number=7,
            use_repeats=True,
            stitches_per_repeat=7,
            additional_stitches=5,
        )

        repeats_stitch1 = StitchFactory(repeats_x_mod=1, repeats_mod_y=7)
        repeats_stitch2 = StitchFactory(repeats_x_mod=2, repeats_mod_y=7)
        no_repeats_stitch = StitchFactory(repeats_x_mod=0, repeats_mod_y=1)

        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=4,
            cast_on_mod_y=7,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch_with_repeats,
            main_stitch=repeats_stitch2,
            edging_stitch=repeats_stitch1,
        )
        self.assertEqual(pspec.get_repeats_spec(), (4, 7))

        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            main_stitch=repeats_stitch2,
            edging_stitch=repeats_stitch1,
            swatch=swatch_with_repeats,
        )
        self.assertEqual(pspec.get_repeats_spec(), (1, 7))

        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            main_stitch=repeats_stitch2,
            edging_stitch=no_repeats_stitch,
            swatch=swatch_with_repeats,
        )
        self.assertEqual(pspec.get_repeats_spec(), (2, 7))

        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            main_stitch=no_repeats_stitch,
            edging_stitch=no_repeats_stitch,
            swatch=swatch_with_repeats,
        )
        self.assertEqual(pspec.get_repeats_spec(), (0, 1))

    def test_clean(self):
        swatch = SwatchFactory(rows_length=1, rows_number=5)

        pspec = CowlPatternSpecFactory(
            swatch=swatch,
            height=CDC.COWL_HEIGHT_AVERAGE,  # 12 inches
            edging_stitch_height=3,
            horizontal_panel_rounds=10,
        )
        pspec.clean()

        pspec = CowlPatternSpecFactory(
            swatch=swatch,
            height=CDC.COWL_HEIGHT_AVERAGE,  # 12 inches
            edging_stitch_height=3,
            horizontal_panel_rounds=11,
        )
        with self.assertRaises(ValidationError):
            pspec.clean()

        pspec = CowlPatternSpecFactory(
            swatch=swatch,
            height=CDC.COWL_HEIGHT_AVERAGE,  # 12 inches
            edging_stitch_height=5.5,
            horizontal_panel_rounds=0,
        )
        with self.assertRaises(ValidationError):
            pspec.clean()

    def test_main_section_height(self):
        pspec = CowlPatternSpecFactory()
        # sanity check
        self.assertEqual(pspec.total_height_in_inches(), 12)
        self.assertEqual(pspec.edging_stitch_height, 1)
        self.assertEqual(pspec.main_section_height, 10)


class GradedCowlPatternspecTests(TestCase):

    def test_clean(self):

        pspec = GradedCowlPatternSpecFactory(
            edging_stitch_height=2, row_gauge=20, horizontal_panel_rounds=10
        )
        pspec.clean()

        pspec = GradedCowlPatternSpecFactory(
            row_gauge=20, edging_stitch_height=2, horizontal_panel_rounds=11
        )
        with self.assertRaises(ValidationError):
            pspec.clean()


################################################################################################################
#
# Garment parameters
#
################################################################################################################


class CowlIndividualGarmentParametersTests(TestCase):

    def test_make_from_patternspec(self):

        pspec = CowlPatternSpecFactory(height=CDC.COWL_HEIGHT_AVERAGE)
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(igp.height, 12)

        pspec = CowlPatternSpecFactory(circumference=CDC.COWL_CIRC_MEDIUM)
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(igp.circumference, 42)

        pspec = CowlPatternSpecFactory(edging_stitch_height=2.5)
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(igp.edging_height, 2.5)

        pspec = CowlPatternSpecFactory()
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(igp.pattern_spec, pspec)
        self.assertIsNone(igp.redo)

    def test_make_from_redo(self):
        redo = CowlRedoFactory(height=CDC.COWL_HEIGHT_AVERAGE)
        igp = CowlIndividualGarmentParameters.make_from_redo(redo.user, redo)
        self.assertEqual(igp.height, 12)

        redo = CowlRedoFactory(circumference=CDC.COWL_CIRC_MEDIUM)
        igp = CowlIndividualGarmentParameters.make_from_redo(redo.user, redo)
        self.assertEqual(igp.circumference, 42)

        redo = CowlRedoFactory(
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec__edging_stitch_height=2.5
        )
        igp = CowlIndividualGarmentParameters.make_from_redo(redo.user, redo)
        self.assertEqual(igp.edging_height, 2.5)

        redo = CowlRedoFactory()
        igp = CowlIndividualGarmentParameters.make_from_redo(redo.user, redo)
        self.assertEqual(igp.redo, redo)
        self.assertIsNone(igp.pattern_spec)

    def test_spec_height_test(self):

        pspec = CowlPatternSpecFactory(height=CDC.COWL_HEIGHT_AVERAGE)
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(igp.spec_height_text(), "average height")

    def test_spec_circ_test(self):

        pspec1 = CowlPatternSpecFactory(circumference=CDC.COWL_CIRC_MEDIUM)
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec1.user, pspec1)
        self.assertEqual(igp.spec_circ_text(), "medium circumference")

    def test_swatch(self):

        pspec1 = CowlPatternSpecFactory()
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec1.user, pspec1)
        self.assertEqual(igp.swatch, pspec1.swatch)

    def test_clean(self):

        # Edging-height can't take up more than 1/3rd the total height
        igp = CowlIndividualGarmentParametersFactory(height=12, edging_height=2)
        # no validation error, right?
        igp.full_clean()

        igp = CowlIndividualGarmentParametersFactory(height=12, edging_height=4)
        with self.assertRaises(ValidationError):
            igp.full_clean()

        igp = CowlIndividualGarmentParametersFactory(height=12, edging_height=5)
        with self.assertRaises(ValidationError):
            igp.full_clean()

        # Edging + horizontal panel must leave 2 inches

        swatch = SwatchFactory(rows_length=1, rows_number=5)

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=10)
        igp = CowlIndividualGarmentParametersFactory(
            height=12, edging_height=3, pattern_spec=pspec
        )
        igp.clean()

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=11)
        igp = CowlIndividualGarmentParametersFactory(
            height=12, edging_height=3, pattern_spec=pspec
        )
        with self.assertRaises(ValidationError):
            igp.clean()

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=0)
        igp = CowlIndividualGarmentParametersFactory(
            height=4, edging_height=1, pattern_spec=pspec
        )
        igp.clean()

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=0)
        igp = CowlIndividualGarmentParametersFactory(
            height=4, edging_height=1.1, pattern_spec=pspec
        )
        with self.assertRaises(ValidationError):
            igp.clean()

    def test_negative_circ(self):
        igp = CowlIndividualGarmentParametersFactory(circumference=-1)
        with self.assertRaises(ValidationError) as ex:
            igp.full_clean()

        self.assertEqual(
            ex.exception.message_dict,
            {"circumference": ["Ensure this value is greater than or equal to 18."]},
        )


class GradedCowlGarmentParametersTests(TestCase):

    def test_make_from_patternspec(self):
        pspec = GradedCowlPatternSpecFactory()

        ggp = GradedCowlGarmentParameters.make_from_patternspec(pspec.user, pspec)

        self.assertEqual(ggp.user, pspec.user)
        self.assertEqual(ggp.pattern_spec, pspec)
        self.assertEqual(ggp.edging_height, pspec.edging_stitch_height)

        grade_values = set((g.height, g.circumference) for g in ggp.all_grades)
        self.assertEqual(grade_values, set([(10, 20), (12, 26), (16, 42), (20, 60)]))

    def test_clean(self):
        ggp = GradedCowlGarmentParametersFactory()
        ggp.clean()

        ggp = GradedCowlGarmentParametersFactory(edging_height=4)
        with self.assertRaises(ValidationError):
            ggp.clean()

        ggp = GradedCowlGarmentParametersFactory(
            edging_height=3,
            pattern_spec__horizontal_panel_rounds=11,
            pattern_spec__row_gauge=20,
        )
        with self.assertRaises(ValidationError):
            ggp.clean()


################################################################################################################
#
# Schematics
#
################################################################################################################


class CowlPieceSchematicTests(TestCase):

    def test_get_values_from_gp(self):
        gp = CowlIndividualGarmentParametersFactory(
            height=11.1, circumference=66.9, edging_height=2
        )
        cps = CowlPieceSchematic()
        cps._get_values_from_gp(gp)
        self.assertEqual(cps.height, 11.1)
        self.assertEqual(cps.circumference, 66.9)
        self.assertEqual(cps.edging_height, 2)

    def test_get_spec_source(self):
        cpattern_spec = CowlPatternSpecFactory()
        ccs = CowlGarmentSchematicFactory(
            individual_garment_parameters__pattern_spec=cpattern_spec
        )
        piece = ccs.cowl_piece
        self.assertEqual(piece.get_spec_source(), cpattern_spec)

        # need to implement redos
        cowl_redo = CowlRedoFactory()
        ccs = CowlGarmentSchematicFactory(
            individual_garment_parameters__pattern_spec=None,
            individual_garment_parameters__redo=cowl_redo,
        )
        piece = ccs.cowl_piece
        self.assertEqual(piece.get_spec_source(), cowl_redo)

    def test_clean(self):

        sch = CowlPieceSchematicFactory(height=12, edging_height=3)
        # no validation error, right?
        sch.full_clean()

        sch = CowlPieceSchematicFactory(height=12, edging_height=4)
        with self.assertRaises(ValidationError):
            sch.full_clean()

        sch = CowlPieceSchematicFactory(height=12, edging_height=5)
        with self.assertRaises(ValidationError):
            sch.full_clean()


class CowlGarmentSchematicTests(TestCase):

    def test_make_from_garment_parameters(self):

        gp = CowlIndividualGarmentParametersFactory(
            height=11, circumference=78, edging_height=1.5
        )

        ccs = CowlGarmentSchematic.make_from_garment_parameters(gp)

        self.assertEqual(ccs.individual_garment_parameters, gp)
        self.assertFalse(ccs.customized)
        piece = ccs.cowl_piece
        self.assertEqual(piece.height, 11)
        self.assertEqual(piece.circumference, 78)
        self.assertEqual(piece.edging_height, 1.5)

    def test_sub_pieces(self):

        css = CowlGarmentSchematicFactory()
        self.assertEqual(css.sub_pieces(), [css.cowl_piece])


class GradedCowlGarmentSchematicTests(TestCase):

    def test_make_from_garment_parameters(self):
        gp = GradedCowlGarmentParametersFactory()

        gcs = GradedCowlGarmentSchematic.make_from_garment_parameters(gp)

        grade_vals = set(
            (g.height, g.circumference, g.edging_height) for g in gcs.all_grades
        )
        goal_set = set(
            [
                (10, 20, 1),
                (12, 26, 1),
                (16, 42, 1),
                (20, 60, 1),
            ]
        )
        self.assertEqual(grade_vals, goal_set)


################################################################################################################
#
# Pieces
#
################################################################################################################


class _BaseCowlPieceTests(object):

    def test_first_main_section_row(self):
        piece = self.factory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.first_main_section_row, 11)

    def test_last_main_section_row(self):
        piece = self.factory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.last_main_section_row, 89)

    def test_first_row_castoff_section(self):
        piece = self.factory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.first_row_castoff_section, 90)


class CowlPieceTests(TestCase, _BaseCowlPieceTests):

    factory = CowlPieceFactory

    def make_piece_from_patternspec(self, pspec):
        igp = CowlIndividualGarmentParameters.make_from_patternspec(pspec.user, pspec)
        sch = CowlGarmentSchematic.make_from_garment_parameters(igp)
        sch.save()
        piece = CowlPiece.make(sch)
        return (piece, sch.cowl_piece)

    def test_make_no_repeats_no_cable(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 294)
        self.assertEqual(cp.main_pattern_stitches, 294)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_make_no_repeats_yes_cable1(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=5,
            extra_cable_stitches_are_main_pattern_only=False,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 294 + 5)
        self.assertEqual(cp.main_pattern_stitches, 294 + 5)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_make_no_repeats_yes_cable2(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=5,
            extra_cable_stitches_are_main_pattern_only=True,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 294)
        self.assertEqual(cp.main_pattern_stitches, 294 + 5)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_make_yes_repeats_no_cable(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(4, 7)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 298)  # 4 mod 7
        self.assertEqual(cp.main_pattern_stitches, 298)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_make_yes_repeats_yes_cable1(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=5,
            extra_cable_stitches_are_main_pattern_only=False,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 36)

        self.assertEqual(cp.cast_on_stitches, 252 + 5)
        self.assertEqual(cp.main_pattern_stitches, 252 + 5)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_make_yes_repeats_yes_cable1(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_length=1, stitches_number=7
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=5,
            extra_cable_stitches_are_main_pattern_only=True,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 294)
        self.assertEqual(cp.main_pattern_stitches, 294 + 5)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_swatch_is_ignored(self):

        swatch = SwatchFactory(
            rows_length=1,
            rows_number=5,
            stitches_length=1,
            stitches_number=7,
            use_repeats=True,
            stitches_per_repeat=7,
            additional_stitches=5,
        )
        pspec = CowlPatternSpecFactory(
            extra_cable_stitches=0,
            cast_on_x_mod=0,
            cast_on_mod_y=1,
            height=CDC.COWL_HEIGHT_AVERAGE,
            circumference=CDC.COWL_CIRC_MEDIUM,
            swatch=swatch,
        )
        with mock.patch.object(
            CowlPatternSpec, "get_repeats_spec", return_value=(0, 1)
        ):
            (cp, cps) = self.make_piece_from_patternspec(pspec)

        # sanity check:
        self.assertEqual(cps.height, 12)
        self.assertEqual(cps.edging_height, 1)
        self.assertEqual(cps.circumference, 42)

        self.assertEqual(cp.cast_on_stitches, 294)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)

    def test_first_main_section_row(self):
        piece = CowlPieceFactory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.first_main_section_row, 11)

    def test_last_main_section_row(self):
        piece = CowlPieceFactory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.last_main_section_row, 89)

    def test_first_row_castoff_section(self):
        piece = CowlPieceFactory(total_rows=100, edging_height_in_rows=10)
        self.assertEqual(piece.first_row_castoff_section, 90)

    def test_first_row_second_horizontal_panel(self):
        pspec = CowlPatternSpecFactory(horizontal_panel_rounds=10)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        self.assertEqual(piece.first_row_second_horizontal_panel, 80)

        pspec = CowlPatternSpecFactory(horizontal_panel_rounds=0)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        self.assertIsNone(piece.first_row_second_horizontal_panel)

    def test_first_row_second_horizontal_panel_in_inches(self):
        swatch = SwatchFactory(rows_number=5, rows_length=1)
        pspec = CowlPatternSpecFactory(horizontal_panel_rounds=10, swatch=swatch)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        self.assertEqual(piece.first_row_second_horizontal_panel_in_inches, 80 / 5)

        pspec = CowlPatternSpecFactory(horizontal_panel_rounds=0, swatch=swatch)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        self.assertIsNone(piece.first_row_second_horizontal_panel_in_inches)

    def test_edging_stitch(self):
        stitch = StitchFactory(name="test edging stitch")
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec__edging_stitch=stitch
        )
        self.assertEqual(piece.edging_stitch, stitch)

    def test_main_stitch(self):
        stitch = StitchFactory(name="test main stitch")
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec__main_stitch=stitch
        )
        self.assertEqual(piece.main_stitch, stitch)

    def test_edging_stitch_name(self):
        stitch = StitchFactory(name="test edging stitch")
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec__edging_stitch=stitch
        )
        self.assertEqual(piece.edging_stitch_name(), "test edging stitch")

    def test_main_stitch_name(self):
        stitch = StitchFactory(name="test main stitch")
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec__main_stitch=stitch
        )
        self.assertEqual(piece.main_stitch_name(), "test main stitch")

    def test_get_spec_source(self):
        pattern_spec = CowlPatternSpecFactory()
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=pattern_spec,
            schematic__individual_garment_parameters__redo=None,
        )
        self.assertEqual(piece.get_spec_source(), pattern_spec)

        redo = CowlRedoFactory()
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=None,
            schematic__individual_garment_parameters__redo=redo,
        )
        self.assertEqual(piece.get_spec_source(), redo)

    def test_get_swatch(self):
        pattern_spec = CowlPatternSpecFactory()
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=pattern_spec,
            schematic__individual_garment_parameters__redo=None,
        )
        self.assertEqual(piece.swatch, pattern_spec.swatch)

        redo = CowlRedoFactory()
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=None,
            schematic__individual_garment_parameters__redo=redo,
        )
        self.assertEqual(piece.swatch, redo.swatch)

    def test_get_gauge(self):
        swatch = SwatchFactory(
            rows_number=11.2, rows_length=1, stitches_number=9.4, stitches_length=1
        )
        pattern_spec = CowlPatternSpecFactory(swatch=swatch)
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=pattern_spec,
            schematic__individual_garment_parameters__redo=None,
        )
        piece_gauge = piece.gauge
        self.assertEqual(piece_gauge.rows, 11.2)
        self.assertEqual(piece_gauge.stitches, 9.4)

        swatch = SwatchFactory(
            rows_number=11.3, rows_length=1, stitches_number=9.5, stitches_length=1
        )
        redo = CowlRedoFactory(swatch=swatch)
        piece = CowlPieceFactory(
            schematic__individual_garment_parameters__pattern_spec=None,
            schematic__individual_garment_parameters__redo=redo,
        )
        piece_gauge = piece.gauge
        self.assertEqual(piece_gauge.rows, 11.3)
        self.assertEqual(piece_gauge.stitches, 9.5)

    def test_actual_circumference(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=7, stitches_length=1, stitches_number=5
        )
        piece = CowlPieceFactory(
            cast_on_stitches=100,
            schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(piece.actual_circumference(), 20)

    def test_actual_height(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=7, stitches_length=1, stitches_number=5
        )
        piece = CowlPieceFactory(
            total_rows=70,
            schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(piece.actual_height(), 10)

    def test_area(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=7, stitches_length=1, stitches_number=5
        )
        piece = CowlPieceFactory(
            total_rows=70,
            cast_on_stitches=100,
            schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(piece.area(), (70 / 7) * (100 / 5))

    def test_actual_edging_height(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=7, stitches_length=1, stitches_number=5
        )
        piece = CowlPieceFactory(
            edging_height_in_rows=14,
            schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(piece.actual_edging_height(), 2)

    def test_cast_on_to_main_section_end_in_inches(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=10, stitches_length=1, stitches_number=5
        )
        piece = CowlPieceFactory(
            total_rows=90,
            edging_height_in_rows=10,
            schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(piece.cast_on_to_main_section_end_in_inches(), 7.9)

    def test_get_pattern(self):
        pattern = CowlPatternFactory()
        piece = pattern.pieces.cowl
        self.assertEqual(piece.get_pattern(), pattern)

    def test_clean(self):

        # Test that an edging is no more than 1/3rd the height of the cowl
        piece = CowlPieceFactory(total_rows=90, edging_height_in_rows=10)
        # No validation error
        piece.full_clean()

        piece = CowlPieceFactory(total_rows=91, edging_height_in_rows=31)
        # No validation error
        piece.full_clean()

        piece = CowlPieceFactory(total_rows=90, edging_height_in_rows=45)
        with self.assertRaises(ValidationError):
            piece.full_clean()

        piece = CowlPieceFactory(total_rows=90, edging_height_in_rows=50)
        with self.assertRaises(ValidationError):
            piece.full_clean()

        # Test that there's at least two inches of 'straight' in the middle
        swatch = SwatchFactory(rows_length=1, rows_number=5)

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=10)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=35,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        piece.clean()

        pspec = CowlPatternSpecFactory(swatch=swatch, horizontal_panel_rounds=10)
        piece = CowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=36,
            schematic__individual_garment_parameters__pattern_spec=pspec,
        )
        with self.assertRaises(ValidationError):
            piece.clean()


class GradedCowlPieceTests(TestCase, _BaseCowlPieceTests):

    factory = GradedCowlPieceFactory

    def test_first_row_second_horizontal_panel(self):
        pspec = GradedCowlPatternSpecFactory(horizontal_panel_rounds=10)
        piece = GradedCowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec=pspec,
        )
        self.assertEqual(piece.first_row_second_horizontal_panel, 80)

        pspec = GradedCowlPatternSpecFactory(horizontal_panel_rounds=0)
        piece = GradedCowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec=pspec,
        )
        self.assertIsNone(piece.first_row_second_horizontal_panel)

    def test_first_row_second_horizontal_panel_in_inches(self):
        pspec = GradedCowlPatternSpecFactory(horizontal_panel_rounds=10, row_gauge=20)
        piece = GradedCowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec=pspec,
        )
        self.assertEqual(piece.first_row_second_horizontal_panel_in_inches, 80 / 5)

        pspec = GradedCowlPatternSpecFactory(horizontal_panel_rounds=0, row_gauge=20)
        piece = GradedCowlPieceFactory(
            total_rows=100,
            edging_height_in_rows=10,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec=pspec,
        )
        self.assertIsNone(piece.first_row_second_horizontal_panel_in_inches)

    def test_edging_stitch(self):
        stitch = StitchFactory(name="test edging stitch")
        piece = GradedCowlPieceFactory(
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__edging_stitch=stitch
        )
        self.assertEqual(piece.edging_stitch, stitch)

    def test_main_stitch(self):
        stitch = StitchFactory(name="test main stitch")
        piece = GradedCowlPieceFactory(
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__main_stitch=stitch
        )
        self.assertEqual(piece.main_stitch, stitch)

    def test_edging_stitch_name(self):
        stitch = StitchFactory(name="test edging stitch")
        piece = GradedCowlPieceFactory(
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__edging_stitch=stitch
        )
        self.assertEqual(piece.edging_stitch_name(), "test edging stitch")

    def test_main_stitch_name(self):
        stitch = StitchFactory(name="test main stitch")
        piece = GradedCowlPieceFactory(
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__main_stitch=stitch
        )
        self.assertEqual(piece.main_stitch_name(), "test main stitch")

    def test_get_spec_source(self):
        pattern_spec = GradedCowlPatternSpecFactory()
        piece = GradedCowlPieceFactory(
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec=pattern_spec
        )
        self.assertEqual(piece.get_spec_source(), pattern_spec)

    def test_actual_circumference(self):
        piece = GradedCowlPieceFactory(
            cast_on_stitches=100,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__row_gauge=28,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__stitch_gauge=20,
        )
        self.assertEqual(piece.actual_circumference(), 20)

    def test_actual_height(self):
        piece = GradedCowlPieceFactory(
            total_rows=70,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__row_gauge=28,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__stitch_gauge=20,
        )
        self.assertEqual(piece.actual_height(), 10)

    def test_area(self):
        piece = GradedCowlPieceFactory(
            total_rows=70,
            cast_on_stitches=100,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__row_gauge=28,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__stitch_gauge=20,
        )
        self.assertEqual(piece.area(), (70 / 7) * (100 / 5))

    def test_actual_edging_height(self):
        piece = GradedCowlPieceFactory(
            edging_height_in_rows=14,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__row_gauge=28,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__stitch_gauge=20,
        )
        self.assertEqual(piece.actual_edging_height(), 2)

    def test_cast_on_to_main_section_end_in_inches(self):
        piece = GradedCowlPieceFactory(
            total_rows=90,
            edging_height_in_rows=10,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__row_gauge=40,
            graded_pattern_pieces__schematic__graded_garment_parameters__pattern_spec__stitch_gauge=20,
        )
        self.assertEqual(piece.cast_on_to_main_section_end_in_inches(), 7.9)

    def test_get_pattern(self):
        pattern = CowlPatternFactory()
        piece = pattern.pieces.cowl
        self.assertEqual(piece.get_pattern(), pattern)


class TestCowlPatternPieces(TestCase):

    def test_sub_pieces(self):
        cpps = CowlPatternPiecesFactory()
        self.assertEqual(cpps.sub_pieces(), [cpps.cowl])

    def test_trim_area(self):
        cpps = CowlPatternPiecesFactory()
        self.assertEqual(cpps._trim_area(), 0)

    def test_make_from_ips(self):

        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_number=7, stitches_length=1
        )
        ccs = CowlGarmentSchematicFactory(
            individual_garment_parameters__pattern_spec__swatch=swatch,
            cowl_piece__height=12,
            cowl_piece__circumference=36,
            cowl_piece__edging_height=1,
        )
        cpps = CowlPatternPieces.make_from_individual_pieced_schematic(ccs)
        cp = cpps.cowl
        self.assertEqual(cp.cast_on_stitches, 36 * 7)
        self.assertEqual(cp.edging_height_in_rows, 5)
        self.assertEqual(cp.total_rows, 60)


class GradedCowlPatternPiecesTests(TestCase):

    def test_make_from_schematic(self):
        schematic = GradedCowlGarmentSchematicFactory()
        gpp = GradedCowlPatternPieces.make_from_schematic(schematic)

        expected_values = [
            (100, 100, 5, 43),
            (130, 130, 5, 51),
            (210, 210, 5, 68),
            (300, 300, 5, 85),
        ]
        pieces = gpp.all_pieces
        self.assertEqual(len(expected_values), len(pieces))

        for grade, vector in zip(pieces, expected_values):
            tuple = (
                grade.cast_on_stitches,
                grade.main_pattern_stitches,
                grade.edging_height_in_rows,
                grade.total_rows,
            )
            self.assertEqual(tuple, vector)

    def test_area_list(self):
        schematic = GradedCowlGarmentSchematicFactory()
        gpp = GradedCowlPatternPieces.make_from_schematic(schematic)
        self.assertEqual(gpp.area_list(), [202.35294117647058, 312.0, 672.0, 1200.0])


################################################################################################################
#
# patterns
#
################################################################################################################


class TestCowlPattern(TestCase):

    def test_make_from_ipp(self):

        cipp = CowlPatternPiecesFactory(
            schematic__individual_garment_parameters__pattern_spec__name="test name"
        )
        user = cipp.schematic.get_spec_source().user
        pattern = CowlPattern.make_from_individual_pattern_pieces(user, cipp)
        self.assertEqual(pattern.user, user)
        self.assertEqual(pattern.name, "test name")
        self.assertEqual(pattern.pieces, cipp)

    def test_get_schematic_display_context(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_number=7, stitches_length=1
        )
        pattern = CowlPatternFactory(
            pieces__cowl__cast_on_stitches=350,
            pieces__cowl__total_rows=50,
            pieces__cowl__edging_height_in_rows=15,
            pieces__schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        goal_context = {
            "dimensions": [
                ("actual height", 10),
                ("actual circumference", 50),
                ("actual edging height", 3),
            ],
            "schematic_image": "img/Cowl_Schematic.png",
        }
        self.assertEqual(pattern.get_schematic_display_context(), goal_context)

    def test_actual_height(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_number=7, stitches_length=1
        )
        pattern = CowlPatternFactory(
            pieces__cowl__cast_on_stitches=350,
            pieces__cowl__total_rows=50,
            pieces__cowl__edging_height_in_rows=15,
            pieces__schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(pattern.actual_height(), 10)

    def test_actual_circumference(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_number=7, stitches_length=1
        )
        pattern = CowlPatternFactory(
            pieces__cowl__cast_on_stitches=350,
            pieces__cowl__total_rows=50,
            pieces__cowl__edging_height_in_rows=15,
            pieces__schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(pattern.actual_circumference(), 50)

    def test_actual_edging_height(self):
        swatch = SwatchFactory(
            rows_length=1, rows_number=5, stitches_number=7, stitches_length=1
        )
        pattern = CowlPatternFactory(
            pieces__cowl__cast_on_stitches=350,
            pieces__cowl__total_rows=50,
            pieces__cowl__edging_height_in_rows=15,
            pieces__schematic__individual_garment_parameters__pattern_spec__swatch=swatch,
        )
        self.assertEqual(pattern.actual_edging_height(), 3)


class TestCowlRedo(TestCase, CowlRedoBaseTests):
    factory = CowlRedoFactory

    def test_clean2(self):

        des = self.factory(
            height=CDC.COWL_HEIGHT_AVERAGE,
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec__edging_stitch_height=7,
        )
        self.assertEqual(des.total_height_in_inches(), 12)  # sanity check
        with self.assertRaises(ValidationError):
            des.full_clean()

        des = self.factory(
            height=CDC.COWL_HEIGHT_AVERAGE,
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec__edging_stitch_height=4,
        )
        with self.assertRaises(ValidationError):
            des.full_clean()

        des = self.factory(
            height=CDC.COWL_HEIGHT_AVERAGE,
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec__edging_stitch_height=2,
        )
        # No execption, right?
        des.full_clean()
