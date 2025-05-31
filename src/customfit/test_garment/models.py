# -*- coding: utf-8 -*-


import reversion
from django.core.exceptions import ValidationError
from django.db import models

# Create your models here.
from customfit.bodies.models import Body, GradeSet
from customfit.designs.models import AdditionalDesignElement, Design
from customfit.fields import LengthField, NonNegFloatField
from customfit.garment_parameters.models import (
    GradedGarmentParameters,
    GradedGarmentParametersGrade,
    IndividualGarmentParameters,
)
from customfit.helpers.math_helpers import round
from customfit.pattern_spec.models import GradedPatternSpec, PatternSpec
from customfit.patterns.models import GradedPattern, IndividualPattern, Redo
from customfit.patterns.renderers import (
    GradedTestPatternRendererPdfAbridged,
    GradedTestPatternRendererPdfFull,
    GradedTestPatternRendererWebFull,
    TestPatternRendererPdfAbridged,
    TestPatternRendererPdfFull,
    TestPatternRendererWebFull,
)
from customfit.pieces.models import (
    AreaMixin,
    GradedPatternPiece,
    GradedPatternPieces,
    PatternPiece,
    PatternPieces,
)
from customfit.schematics.models import (
    ConstructionSchematic,
    GradedConstructionSchematic,
    GradedPieceSchematic,
    PieceSchematic,
)
from customfit.stitches.models import Stitch
from customfit.swatches.models import Gauge

####################################################################################################################
#
# Designs
#
####################################################################################################################


class TestDesign(Design):
    stitch1 = models.ForeignKey(Stitch, on_delete=models.CASCADE)
    test_length = LengthField()

    def compatible_swatch(self, swatch):
        # Just to implment something non-trivial:
        swatch_stitch = swatch.get_stitch()
        return self.stitch1.is_compatible(swatch_stitch)


class TestDesignWithBody(TestDesign):
    pass


####################################################################################################################
#
# PatternSpecs
#
####################################################################################################################


class BaseTestPatternSpec(models.Model):
    stitch1 = models.ForeignKey(Stitch, on_delete=models.CASCADE)
    test_length = LengthField()

    @property
    def gauge(self):
        return Gauge(10, 12)

    def stitches_used(self):
        return [self.stitch1]

    def compatible_swatch(self, swatch):
        return swatch.get_stitch().is_compatible(self.stitch1)

    def get_garment(self):
        return "test_garment"

    class Meta:
        abstract = True


class TestPatternSpec(PatternSpec, BaseTestPatternSpec):

    def get_igp_class(self):
        return TestGarmentParameters


class TestPatternSpecWithBody(TestPatternSpec):

    body = models.ForeignKey(Body, on_delete=models.CASCADE)

    def get_igp_class(self):
        return TestGarmentParametersWithBody


class GradedTestPatternSpec(GradedPatternSpec, BaseTestPatternSpec):

    row_gauge = models.FloatField()
    stitch_gauge = models.FloatField()

    grade_set = models.ForeignKey(GradeSet, on_delete=models.CASCADE)

    # convenience property, not required by superclass
    @property
    def all_grades(self):
        return self.grade_set.grades

    def get_igp_class(self):
        return GradedTestGarmentParameters


####################################################################################################################
#
# Garment Parameters
#
####################################################################################################################


class _TestBaseGarmentParameters(models.Model):
    test_field = LengthField()

    class Meta:
        abstract = True


class TestGarmentParameterBodyLevelFields(models.Model):
    test_field_from_body = LengthField()

    class Meta:
        abstract = True


# This next line contains a magic string created by Django-polymorphic to hold the
# pointer from the SweaterIndividualGarmentParameters table to the IndividualGarmentParameters
# table. This magic string can be manually overwritten (see the Django docs on multi-table
# inheritance) so don't do that.
@reversion.register(follow=["individualgarmentparameters_ptr"])
class TestGarmentParameters(IndividualGarmentParameters, _TestBaseGarmentParameters):

    @classmethod
    def make_from_redo(cls, user, redo):
        igp = cls()
        igp.redo = redo
        igp.pattern_spec = None
        igp.user = user
        igp.test_field = redo.test_length
        igp.full_clean()
        igp.save()
        return igp

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        igp = cls()
        igp.pattern_spec = pattern_spec
        igp.user = user
        igp.redo = None
        igp.test_field = pattern_spec.test_length
        igp.full_clean()
        igp.save()
        return igp


class TestGarmentParametersWithBody(
    TestGarmentParameters, TestGarmentParameterBodyLevelFields
):

    @classmethod
    def make_from_redo(cls, user, redo):
        igp = cls()
        igp.redo = redo
        igp.pattern_spec = None
        igp.user = user
        igp.test_field = redo.test_length
        igp.test_field_from_body = redo.body.bust_circ
        igp.full_clean()
        igp.save()
        return igp

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        igp = cls()
        igp.pattern_spec = pattern_spec
        igp.user = user
        igp.redo = None
        igp.test_field = pattern_spec.test_length
        igp.test_field_from_body = pattern_spec.body.bust_circ
        igp.full_clean()
        igp.save()
        return igp

    @classmethod
    def missing_body_fields(cls, patternspec):
        body = patternspec.body
        body_fields = body._meta.fields
        body_field_dict = {f.name: f for f in body_fields}

        needed_measurements = [
            body_field_dict["bust_circ"],
            body_field_dict["wrist_circ"],
            body_field_dict["elbow_circ"],
            body_field_dict["bicep_circ"],
            body_field_dict["forearm_circ"],
        ]
        return set(
            field for field in needed_measurements if getattr(body, field.name) is None
        )


class GradedTestGarmentParametersGrade(
    GradedGarmentParametersGrade, TestGarmentParameterBodyLevelFields
):
    pass


class GradedTestGarmentParameters(GradedGarmentParameters, _TestBaseGarmentParameters):

    # required by superclass
    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        igp = cls()
        igp.user = user
        igp.pattern_spec = pattern_spec
        igp.test_field = pattern_spec.test_length
        igp.full_clean()
        igp.save()
        for grade in pattern_spec.all_grades:
            igp_grade = GradedTestGarmentParametersGrade()
            igp_grade.test_field = pattern_spec.test_length
            igp_grade.test_field_from_body = grade.bust_circ
            igp_grade.graded_garment_parameters = igp
            igp_grade.full_clean()
            igp_grade.save()
        return igp

    def get_schematic_class(self):
        return GradedTestGarmentSchematic


####################################################################################################################
#
# Schematics
#
####################################################################################################################


class _BaseTestPieceSchematic(models.Model):

    class Meta:
        abstract = True

    test_field = models.FloatField()

    def clean(self):
        if self.test_field == 10:
            raise ValidationError("Boom!")


class TestPieceSchematic(PieceSchematic, _BaseTestPieceSchematic):

    schematic_field_name = "test_piece"

    def get_spec_source(self):
        garment_schematic = self.testgarmentschematic
        return garment_schematic.get_spec_source()

    def _get_values_from_gp(self, gp):
        self.test_field = gp.test_field


class GradedTestPieceSchematic(GradedPieceSchematic, _BaseTestPieceSchematic):

    test_field_from_body = models.FloatField()

    # required by superclass
    def _get_values_from_gp_and_grade(self, gp, grade):
        self.test_field = gp.test_field
        self.test_field_from_body = grade.test_field_from_body
        # note: do not save yet


class TestGarmentSchematic(ConstructionSchematic):

    test_piece = models.OneToOneField(TestPieceSchematic, on_delete=models.CASCADE)

    piece_class = TestPieceSchematic

    def sub_pieces(self):
        return [self.test_piece]

    @classmethod
    def make_from_garment_parameters(cls, gp):
        test_piece = cls.piece_class.make_from_gp_and_container(gp)
        return_me = cls(test_piece=test_piece, individual_garment_parameters=gp)
        return return_me


class GradedTestGarmentSchematic(GradedConstructionSchematic):

    # required by superclass
    @classmethod
    def make_from_garment_parameters(cls, gp):
        return_me = cls(graded_garment_parameters=gp)
        return_me.save()
        for gp_grade in gp.all_grades:
            grade = GradedTestPieceSchematic.make_from_gp_grade_and_container(
                gp, gp_grade, return_me
            )
            grade.save()
        return return_me

    def get_pieces_class(self):
        return GradedTestPatternPieces


####################################################################################################################
#
# Pieces
#
####################################################################################################################


class _BaseTestPatternPiece(models.Model):
    class Meta:
        abstract = True

    test_field = models.FloatField()

    def area(self):
        return 1.0

    def trim_area(self):
        return 0.0


class TestPatternPiece(PatternPiece, _BaseTestPatternPiece):
    #
    # Subclasses should implement:
    #
    # * get_pattern(self) -- returning the pattern it belongs to or None

    _pattern_field_name = "test_piece"

    @classmethod
    def make_from_schematic(cls, piece_schematic):
        return_me = cls(test_field=piece_schematic.test_field)
        return_me.save()
        return return_me

    @property
    def schematic(self):
        test_pattern_pieces = self.testpatternpieces
        return test_pattern_pieces.schematic.test_piece


class GradedTestPatternPiece(GradedPatternPiece, _BaseTestPatternPiece):
    #
    # Subclasses should implement:
    #
    # * get_pattern(self) -- returning the pattern it belongs to or None

    class Meta:
        ordering = ["sort_key"]

    @classmethod
    def make_from_schematic_and_container(cls, grade_schematic, container):
        return_me = cls(
            graded_pattern_pieces=container,
            test_field=grade_schematic.test_field_from_body,
            sort_key=grade_schematic.test_field_from_body,
        )
        return_me.save()
        return return_me


class TestGarmentAreaMixin(AreaMixin):

    def _trim_area(self):
        return self.test_piece.trim_area()


class _BaseTestPatternPieces(models.Model):

    class Meta:
        abstract = True


class TestPatternPieces(TestGarmentAreaMixin, PatternPieces, _BaseTestPatternPieces):

    test_piece = models.OneToOneField(TestPatternPiece, on_delete=models.CASCADE)
    test_piece_class = TestPatternPiece

    def sub_pieces(self):
        return [self.test_piece]

    @classmethod
    def make_from_schematic(cls, test_schematic):
        test_piece_schematic = test_schematic.test_piece
        test_piece = cls.test_piece_class.make_from_schematic(test_piece_schematic)
        return_me = cls()
        return_me.schematic = test_schematic
        return_me.test_piece = test_piece
        return return_me


class GradedTestPatternPieces(GradedPatternPieces, _BaseTestPatternPieces):

    @classmethod
    def make_from_schematic(cls, graded_construction_schematic):
        return_me = cls()
        return_me.schematic = graded_construction_schematic
        return_me.save()
        for grade_schematic in graded_construction_schematic.all_grades:
            grade = GradedTestPatternPiece.make_from_schematic_and_container(
                grade_schematic, return_me
            )
        return return_me

    def get_pattern_class(self):
        return GradedTestPattern

    def area_list(self):

        # First, a helper class
        class TestGarmentGradeArea(TestGarmentAreaMixin):
            def __init__(self, test_piece, *args, **kwargs):
                self.test_piece = test_piece
                super(TestGarmentGradeArea, self).__init__(*args, **kwargs)

            def sub_pieces(self):
                return [self.test_piece]

        areas = [TestGarmentGradeArea(piece).area() for piece in self.all_pieces]
        return areas


####################################################################################################################
#
# Patterns
#
####################################################################################################################


class _BaseTestPattern(models.Model):

    def get_schematic_display_context(self):
        context = {}

        context["dimensions"] = [
            ("test length", self.pieces.test_piece.test_field),
        ]

        return context

    @classmethod
    def make_from_individual_pattern_pieces(cls, user, ipp):
        parameters = {"user": user, "name": ipp.schematic.name, "pieces": ipp}

        instance = cls(**parameters)
        return instance

    @property
    def main_stitch(self):
        return self.get_spec_source().stitch1

    class Meta:
        abstract = True


class TestIndividualPattern(IndividualPattern, _BaseTestPattern):

    @classmethod
    def make_from_individual_pattern_pieces(cls, user, ipp):
        parameters = {"user": user, "name": ipp.schematic.name, "pieces": ipp}

        instance = cls(**parameters)
        return instance

    abridged_pdf_renderer_class = TestPatternRendererPdfAbridged
    full_pdf_renderer_class = TestPatternRendererPdfFull
    web_renderer_class = TestPatternRendererWebFull


class GradedTestPattern(_BaseTestPattern, GradedPattern):

    @classmethod
    def make_from_graded_pattern_pieces(cls, gpp):
        parameters = {"name": gpp.schematic.name, "pieces": gpp}

        instance = cls(**parameters)
        return instance

    abridged_pdf_renderer_class = GradedTestPatternRendererPdfAbridged
    full_pdf_renderer_class = GradedTestPatternRendererPdfFull
    web_renderer_class = GradedTestPatternRendererWebFull


class TestAdditionalDesignElement(AdditionalDesignElement):
    #
    # Note-- we originally used AdditionalSleeveElements in our tests, and we just copied it here
    # when we broke customfit_app into patterns & sweaters
    #

    start_location_value = NonNegFloatField(help_text="Can be zero, but not negative.")

    START_AFTER_CASTON = "start_after_caston"
    START_BEFORE_CAP = "start_before_cap"
    START_TYPE_CHOICES = [
        (START_AFTER_CASTON, "inches after castons"),
        (START_BEFORE_CAP, "inches before cap-shaping start"),
    ]
    start_location_type = models.CharField(max_length=20, choices=START_TYPE_CHOICES)

    def start_row(self, armcap_height_in_inches, gauge):
        if self.start_location_type == self.START_AFTER_CASTON:
            start_height = self.start_location_value
        else:
            assert self.start_location_type == self.START_BEFORE_CAP
            start_height = armcap_height_in_inches - self.start_location_value

        # Additional elements should always start on RS row, so start row should be odd
        start_row_float = start_height * gauge.rows
        start_row = round(start_row_float, multiple=2, mod=1)

        # And if they end up being below the sleeve start, then (unlike body pieces)
        # we just shift them up to the start.
        if start_row < 1:
            return 1
        else:
            return int(start_row)


####################################################################################################################
#
# Redos
#
####################################################################################################################


class TestRedo(Redo):

    test_length = LengthField()

    def get_igp_class(self):
        return TestGarmentParameters


class TestRedoWithBody(TestRedo):
    body = models.ForeignKey(Body, on_delete=models.CASCADE)
