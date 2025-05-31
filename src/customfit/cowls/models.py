# -*- coding: utf-8 -*-

from collections import namedtuple

import reversion
from dbtemplates.models import Template
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

from customfit.designs.models import AdditionalDesignElement, Design
from customfit.fields import (
    LengthField,
    NonNegSmallIntegerField,
    StrictPositiveSmallIntegerField,
)
from customfit.garment_parameters.models import (
    GradedGarmentParameters,
    GradedGarmentParametersGrade,
    IndividualGarmentParameters,
)
from customfit.helpers.math_helpers import (
    FLOATING_POINT_NOISE,
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    _find_best_approximation,
)
from customfit.pattern_spec.models import GradedPatternSpec, PatternSpec
from customfit.patterns.models import GradedPattern, IndividualPattern, Redo
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
from customfit.stitches.models import CABLE_STITCH, Stitch
from customfit.swatches.models import Gauge, Swatch

from . import helpers as CDC
from .renderers import (
    CowlPatternRendererPdfAbridged,
    CowlPatternRendererPdfFull,
    CowlPatternRendererWebFull,
    GradedCowlPatternRendererWebFull,
)

################################################################################################################
#
# Designs and patternspecs
#
################################################################################################################

# Cowl-specific templates for stitches


class StitchTemplateCowlEdge(Template):

    stitch = models.ForeignKey(Stitch, on_delete=models.CASCADE)

    def clean(self):

        super(StitchTemplateCowlEdge, self).clean()
        if not self.stitch.is_accessory_edge_stitch:
            raise ValidationError("Stitch is not an accessory-edge stitch")


class StitchTemplateCowlMain(Template):

    stitch = models.ForeignKey(Stitch, on_delete=models.CASCADE)

    def clean(self):

        super(StitchTemplateCowlMain, self).clean()
        if not self.stitch.is_accessory_main_stitch:
            raise ValidationError("Stitch is not an accessory main-stitch")


class CowlIndividualBase(models.Model):

    # Entire-cowl fields
    circumference = models.CharField(max_length=20, choices=CDC.COWL_CIRC_CHOICES)

    height = models.CharField(max_length=20, choices=CDC.COWL_HEIGHT_CHOICES)

    def min_height(self):
        return self.total_height_in_inches()

    def total_height_in_inches(self):
        inches = CDC.height_to_inches_dict[self.height]
        return inches

    def circumference_in_inches(self):
        inches = CDC.circ_to_inches_dict[self.circumference]
        return inches

    def height_text(self):
        """
        Return 'height' in a user-friendly format for template use
        """
        for val, eng in CDC.COWL_HEIGHT_CHOICES:
            if val == self.height:
                return eng
        return None

    def circumference_text(self):
        """
        Return 'circumference' in a user-friendly format for template use
        """
        for val, eng in CDC.COWL_CIRC_CHOICES:
            if val == self.circumference:
                return eng
        return None

    class Meta:
        abstract = True


class CowlDesignBase(models.Model):

    edging_stitch_height = LengthField(
        validators=[
            MinValueValidator(
                0.25,
                message="Ensure this value is greater than or equal to \xc2&quot;/0.5cm",
            ),
            MaxValueValidator(
                4, message="Ensure this value is less than or equal to 4&quot;/10.5cm"
            ),
        ],
        help_text="How high you'd like the edging stitch pattern to be, in inches. "
        "Note: will be applied twice-- once at cast on and once at cast off.",
    )

    # Edge fields
    cast_on_x_mod = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text=" How many extra stitches are required at cast on. (If no repeats, put 0.)",
    )

    cast_on_mod_y = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="How many stitches are in a full repeat at cast on. (If no repeats, put 1.)",
    )

    edging_stitch = models.ForeignKey(
        Stitch,
        limit_choices_to={"is_accessory_edge_stitch": True},
        related_name="%(app_label)s_edging_stitch_%(class)s",
        on_delete=models.CASCADE,
    )

    # Main-body fields

    main_stitch = models.ForeignKey(
        Stitch,
        limit_choices_to={"is_accessory_main_stitch": True},
        related_name="%(app_label)s_main_stitch_%(class)s",
        on_delete=models.CASCADE,
    )

    cable_stitch = models.ForeignKey(
        Stitch,
        blank=True,
        null=True,
        limit_choices_to={"stitch_type": CABLE_STITCH},
        on_delete=models.CASCADE,
        related_name="%(app_label)s_cable_stitch_%(class)s",
    )

    extra_cable_stitches = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="How many extra stitches to add for a cable. (If none, put 0.)",
    )

    extra_cable_stitches_are_main_pattern_only = models.BooleanField(
        default=False,
        help_text="If true, then extra_cable_stitches are added to main pattern counts but not cast-on or bind-off",
    )

    panel_stitch = models.ForeignKey(
        Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_panel_stitch": True},
        on_delete=models.CASCADE,
        related_name="%(app_label)s_panel_stitch_%(class)s",
    )

    horizontal_panel_rounds = NonNegSmallIntegerField(
        default=0, help_text="How many stitches to devote to each horizontal panel"
    )

    def caston_repeats(self):
        return self.cast_on_mod_y > 1

    def _base_stitches_used(self):
        base_list = [
            self.main_stitch,
            self.edging_stitch,
            self.panel_stitch,
            self.cable_stitch,
        ]
        return_me = []
        for i in base_list:
            if i is not None:
                if i not in return_me:
                    return_me.append(i)
        return return_me

    def clean(self):
        super(CowlDesignBase, self).clean()

        if self.min_height() <= (
            (3 * self.edging_stitch_height) + FLOATING_POINT_NOISE
        ):
            raise ValidationError(
                "Edging-height cannot be more than one-third the total/minimum height"
            )

    class Meta:
        abstract = True


class FirstEdgingTemplate(Template):
    """
    Template for cast-on and initial edging. Replaces default template(s) when present
    """

    pass


class FinalEdgingTemplate(Template):
    """
    Template for final edging and cast-off. Replaces default template(s) when present
    """

    pass


class MainSectionTemplate(Template):
    """
    Template for between the two edgings. Replaces default template(s) when present
    """

    pass


class CowlDesign(Design, CowlDesignBase, CowlIndividualBase):
    # Subclasses from CowlIndividualBase so that it can store default
    # height, circ

    first_edging_template = models.ForeignKey(
        FirstEdgingTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        on_delete=models.CASCADE,
        help_text="Replaces default template(s) when present. Note: Template should start with "
        "{% load pattern_conventions %} and be 'complete' HTML (include liminal p or h3 tags).",
    )

    final_edging_template = models.ForeignKey(
        FinalEdgingTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        on_delete=models.CASCADE,
        help_text="Replaces default template(s) when present. Note: Template should start with "
        "{% load pattern_conventions %} and be 'complete' HTML (include liminal p or h3 tags).",
    )

    main_section_template = models.ForeignKey(
        MainSectionTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        on_delete=models.CASCADE,
        help_text="Replaces default template(s) when present. Note: Template should start with "
        "{% load pattern_conventions %} and be 'complete' HTML (include liminal p or h3 tags).",
    )

    def compatible_swatch(self, swatch):
        """
        Return True iff the swatch is compatible with this design. At the
        moment, this means only that the repeats of the swatch's allover
        stitch is compatible with the allover stitches of this design.
        """
        # Cannot be factored out to CowlDesignBase without MRO problems
        swatch_stitch = swatch.get_stitch()
        return swatch_stitch.is_compatible(self.main_stitch)

    def stitches_used(self):
        base_list = self._base_stitches_used()
        additional_stitches = [adls.stitch for adls in self.additionalstitch_set.all()]
        full_list = base_list + additional_stitches
        return_me = []
        for i in full_list:
            if i is not None:
                if i not in return_me:
                    return_me.append(i)
        return return_me

    def uses_stitch(self, stitch):
        return stitch in self.stitches_used()

    def isotope_classes(self):
        return "cowl"


class AdditionalStitch(models.Model):

    design = models.ForeignKey(
        CowlDesign,
        db_index=True,
        help_text="The design that should include this additional stitch",
        on_delete=models.CASCADE,
    )

    stitch = models.ForeignKey(
        Stitch, related_name="%(app_label)s_%(class)s_stitch", on_delete=models.CASCADE
    )


class _BaseCowlPatternSpec(models.Model):
    class Meta:
        abstract = True

    def get_caston_edging_template(self):
        return self._stitch_or_design_template(
            "first_edging_template",
            self.edging_stitch,
            self.edging_stitch_height > 0,
            "cowl_caston_edge_template",
            "cowls/cowl_pattern_spec",
            "default_first_edging.html",
        )

    def get_castoff_edging_template(self):
        return self._stitch_or_design_template(
            "final_edging_template",
            self.edging_stitch,
            self.edging_stitch_height > 0,
            "cowl_castoff_edge_template",
            "cowls/cowl_pattern_spec",
            "default_final_edging.html",
        )

    def get_main_section_template(self):
        return self._stitch_or_design_template(
            "main_section_template",
            self.main_stitch,
            self._main_stitch_template_boolean(),
            "cowl_main_section_template",
            "cowls/cowl_pattern_spec",
            "default_main_section.html",
        )

    def get_repeats_spec(self):
        # repeats in the design trumps the edge stitch, which trumps the main stitch.
        # Always ignore the swatch

        if self.caston_repeats():
            return (self.cast_on_x_mod, self.cast_on_mod_y)
        elif self.edging_stitch.use_repeats:
            return (self.edging_stitch.repeats_x_mod, self.edging_stitch.repeats_mod_y)
        elif self.main_stitch.use_repeats:
            return (self.main_stitch.repeats_x_mod, self.main_stitch.repeats_mod_y)
        else:
            return (0, 1)

    def get_garment(self):
        return "cowls"

    @property
    def gauge(self):
        return Gauge(self.get_stitch_gauge(), self.get_row_gauge())

    def stitches_used(self):
        stitch_list = self._base_stitches_used()
        if self.design_origin is not None:
            additional_stitches = [
                adls.stitch for adls in self.design_origin.additionalstitch_set.all()
            ]
            stitch_list += additional_stitches
        return_me = []
        for i in stitch_list:
            if i is not None:
                if i not in return_me:
                    return_me.append(i)
        return return_me


class CowlPatternSpec(
    PatternSpec, _BaseCowlPatternSpec, CowlDesignBase, CowlIndividualBase
):

    def compatible_swatch(self, swatch):
        """
        Return True iff the swatch is compatible with this design. At the
        moment, this means only that the repeats of the swatch's allover
        stitch is compatible with the allover stitches of this design.
        """
        # Cannot be factored out to CowlDesignBase without MRO problems
        swatch_stitch = swatch.get_stitch()
        return swatch_stitch.is_compatible(self.main_stitch)

    def get_igp_class(self):
        return CowlIndividualGarmentParameters

    def get_row_gauge(self):
        return self.swatch.get_gauge().rows

    def get_stitch_gauge(self):
        return self.swatch.get_gauge().stitches

    @property
    def main_section_height(self):
        return self.total_height_in_inches() - (2 * self.edging_stitch_height)

    def _main_stitch_template_boolean(self):
        # return True if it's valid for the pattern to have a main pattern-stitch
        return self.main_section_height > 0

    def clean(self):
        super(CowlPatternSpec, self).clean()

        # We may not have a swatch if the user didn't provide one (or provided an invalid one) in a form.
        # That error will be caught elsewhere, but we don't want it throwing an exception here.
        try:
            swatch = self.swatch
        except Swatch.DoesNotExist:
            pass
        else:
            # Need to ensure that the cowl is tall enough for all the elements
            row_gauge = swatch.get_gauge().rows
            horizontal_panel_height = self.horizontal_panel_rounds / row_gauge
            necessary_height = sum(
                [
                    2 * self.edging_stitch_height,
                    2 * horizontal_panel_height,
                    2,  # need at least two inches for middle
                ]
            )

            if self.total_height_in_inches() < necessary_height:
                raise ValidationError("Not tall enough")


class GradedCowlPatternSpec(GradedPatternSpec, _BaseCowlPatternSpec, CowlDesignBase):

    row_gauge = models.FloatField(help_text="Number of rows over four inches")
    stitch_gauge = models.FloatField(help_text="Number of stitches over four inches")

    def get_igp_class(self):
        return GradedCowlGarmentParameters

    def min_height(self):
        return CDC.height_to_inches_dict[CDC.COWL_HEIGHT_SHORT]

    def get_row_gauge(self):
        return self.row_gauge / 4.0

    def get_stitch_gauge(self):
        return self.stitch_gauge / 4.0

    def _main_stitch_template_boolean(self):
        # return True if it's valid for the pattern to have a main pattern-stitch
        rows_per_inch = self.row_gauge / 4.0
        horizontal_panel_height = self.horizontal_panel_rounds / rows_per_inch
        non_main_heights = 2 * sum([horizontal_panel_height, self.edging_stitch_height])
        min_main_stitch_height = self.min_height() - non_main_heights
        return min_main_stitch_height > 0

    def clean(self):
        super(GradedPatternSpec, self).clean()

        # Need to ensure that the cowl is tall enough for all the elements
        # Note: graded cowls are only well-formed if all graded have a main-stitch element or none.
        # Currently, we're enforcing that they all do (which is something we also enforce for single-graded cowls)
        rows_per_inch = self.row_gauge / 4.0
        horizontal_panel_height = self.horizontal_panel_rounds / rows_per_inch
        necessary_height = sum(
            [
                2 * self.edging_stitch_height,
                2 * horizontal_panel_height,
                2,  # need at least two inches for middle
            ]
        )

        if self.min_height() < necessary_height:
            msg = "Not tall enough. Must be at least %s inches" % necessary_height
            raise ValidationError(msg)

    def all_grades(self):
        return [
            CowlPatternSpec(
                height=CDC.COWL_HEIGHT_SHORT, circumference=CDC.COWL_CIRC_EXTRA_SMALL
            ),
            CowlPatternSpec(
                height=CDC.COWL_HEIGHT_AVERAGE, circumference=CDC.COWL_CIRC_SMALL
            ),
            CowlPatternSpec(
                height=CDC.COWL_HEIGHT_TALL, circumference=CDC.COWL_CIRC_MEDIUM
            ),
            CowlPatternSpec(
                height=CDC.COWL_HEIGHT_EXTRA_TALL, circumference=CDC.COWL_CIRC_LARGE
            ),
        ]


class CowlCircumferenceField(LengthField):
    _lower_limit = 18


################################################################################################################
#
# Garment Parameters
#
################################################################################################################


class CowlGarmentDimensions(models.Model):
    class Meta:
        abstract = True

    height = LengthField(help_text="Height of the cowl in inches")
    circumference = CowlCircumferenceField(
        help_text="Circumference of the cowl in inches"
    )

    def set_garment_dimensions(self, spec_source):
        self.height = spec_source.total_height_in_inches()
        self.circumference = spec_source.circumference_in_inches()


class CowlGarmentParametersTopLevelFields(models.Model):
    class Meta:
        abstract = True

    edging_height = LengthField(
        help_text="Height of the edging (on both top and bottom)"
    )

    def set_top_level_fields(self, spec_source, user):
        self.edging_height = spec_source.edging_stitch_height
        self.user = user


# This next line contains a magic string created by Django-polymorphic to hold the
# pointer from the SweaterIndividualGarmentParameters table to the IndividualGarmentParameters
# table. This magic string can be manually overwritten (see the Django docs on multi-table
# inheritance) so don't do that.
@reversion.register(follow=["individualgarmentparameters_ptr"])
class CowlIndividualGarmentParameters(
    IndividualGarmentParameters,
    CowlGarmentParametersTopLevelFields,
    CowlGarmentDimensions,
):

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):

        assert isinstance(pattern_spec, CowlPatternSpec)

        igp = cls()

        igp.set_garment_dimensions(pattern_spec)
        igp.set_top_level_fields(pattern_spec, user)
        igp.pattern_spec = pattern_spec

        igp.full_clean()
        igp.save()
        return igp

    @classmethod
    def make_from_redo(cls, user, redo):
        assert isinstance(redo, CowlRedo)

        igp = cls()

        igp.set_garment_dimensions(redo)
        igp.set_top_level_fields(redo, user)
        igp.redo = redo

        igp.full_clean()
        igp.save()
        return igp

    def spec_height_text(self):
        """
        Return the 'height' of the spec_source, suitable for templates
        """
        spec_source = self.get_spec_source()
        return spec_source.height_text()

    def spec_circ_text(self):
        """
        Return the 'height' of the spec_source, suitable for templates
        """
        spec_source = self.get_spec_source()
        return spec_source.circumference_text()

    @property
    def swatch(self):
        spec_source = self.get_spec_source()
        return spec_source.swatch

    def clean(self):
        super(CowlIndividualGarmentParameters, self).clean()

        if self.height <= (3 * self.edging_height):
            raise ValidationError(
                "Edging-height cannot be more than one-third the total height"
            )

        # Need to ensure that the cowl is tall enough for all the elements
        spec_source = self.get_spec_source()
        row_gauge = spec_source.swatch.get_gauge().rows
        horizontal_panel_height = spec_source.horizontal_panel_rounds / row_gauge

        necessary_height = sum(
            [
                2 * self.edging_height,
                2 * horizontal_panel_height,
                2,  # need at least two inches for middle
            ]
        )

        if self.height < necessary_height:
            raise ValidationError(
                "Edging height too tall for cowl. (Must leave 2 inches / 5.5 cm for main stitch.)"
            )


class CowlGradedGarmentParametersGrade(
    GradedGarmentParametersGrade, CowlGarmentDimensions
):
    pass


class GradedCowlGarmentParameters(
    GradedGarmentParameters, CowlGarmentParametersTopLevelFields
):

    # required by superclass
    @classmethod
    @transaction.atomic  # see comment below as to why this is needed
    def make_from_patternspec(cls, user, pattern_spec):
        igp = cls()
        igp.set_top_level_fields(pattern_spec, user)
        igp.pattern_spec = pattern_spec
        igp.save()
        for grade in pattern_spec.all_grades():
            igp_grade = CowlGradedGarmentParametersGrade()
            igp_grade.set_garment_dimensions(grade)
            igp_grade.graded_garment_parameters = igp
            igp_grade.full_clean()
            igp_grade.save()
        # Note: due to changes in Django, we cannot call this before igp is saved. (If we do
        # GradedGarmentParameters.all_grades fails because igp does not yet have a pk). So,
        # we call it here, but wrap the whole thing in a transaction to revert the database
        # if full_clean fails (and hence raises a ValidationError)
        igp.full_clean()
        return igp

    def clean(self):
        super(GradedCowlGarmentParameters, self).clean()
        for grade in self.all_grades:
            grade.clean()

            if grade.height <= (3 * self.edging_height):
                msg = (
                    "Edging-height cannot be more than one-third the total height. Grade height: %s, edging height: %s"
                    % (grade.height, self.edging_height)
                )
                raise ValidationError(msg)

            spec_source = self.get_spec_source()
            row_gauge = spec_source.row_gauge / 4.0
            horizontal_panel_height = spec_source.horizontal_panel_rounds / row_gauge

            necessary_height = sum(
                [
                    2 * self.edging_height,
                    2 * horizontal_panel_height,
                    2,  # need at least two inches for middle
                ]
            )

            if grade.height < necessary_height:
                msg = (
                    "Grade too short for edging or panel: %s. Must leave 2 inches / 5.5 cm for main stitch."
                    % grade.height
                )
                raise ValidationError(msg)

    def get_schematic_class(self):
        return GradedCowlGarmentSchematic


# Which IGP fields can the user tweak?
COWL_TWEAK_FIELDS = ["height", "circumference"]


################################################################################################################
#
# Schematics
#
################################################################################################################


class _BaseCowlPieceSchematic(models.Model):
    class Meta:
        abstract = True

    height = LengthField()
    circumference = LengthField()
    edging_height = LengthField()

    def _get_piece_values(self, gp):
        self.height = gp.height
        self.circumference = gp.circumference

    def clean(self):
        super(_BaseCowlPieceSchematic, self).clean()

        if self.height <= (3 * self.edging_height):
            raise ValidationError("Edging-height more than  one-third the total height")


class CowlPieceSchematic(PieceSchematic, _BaseCowlPieceSchematic):

    schematic_field_name = "cowl_piece"

    def _get_values_from_gp(self, gp):
        self._get_piece_values(gp)
        self.edging_height = gp.edging_height

    def get_spec_source(self):
        cowl_garment_schematic = self.cowlgarmentschematic
        spec_source = cowl_garment_schematic.get_spec_source()
        return spec_source


class GradedCowlPieceSchematic(GradedPieceSchematic, _BaseCowlPieceSchematic):

    # required by superclass
    def _get_values_from_gp_and_grade(self, gp, grade):
        self._get_piece_values(grade)
        self.edging_height = gp.edging_height
        # note: do not save yet

    def get_spec_source(self):
        spec_source = self.construction_schematic.get_spec_source()
        return spec_source

    class Meta:
        pass


class CowlGarmentSchematic(ConstructionSchematic):

    cowl_piece = models.OneToOneField(CowlPieceSchematic, on_delete=models.CASCADE)

    @classmethod
    def make_from_garment_parameters(cls, igp):
        cowl_piece = CowlPieceSchematic.make_from_gp_and_container(igp)

        attributes = {
            "individual_garment_parameters": igp,
            "customized": False,
            "cowl_piece": cowl_piece,
        }

        return cls(**attributes)

    def sub_pieces(self):
        return [self.cowl_piece]

    def get_schematic_image(self):
        return "img/Cowl_Schematic.png"


class GradedCowlGarmentSchematic(GradedConstructionSchematic):

    # required by superclass
    @classmethod
    def make_from_garment_parameters(cls, gp):
        return_me = cls(graded_garment_parameters=gp)
        return_me.save()
        for gp_grade in gp.all_grades:
            grade = GradedCowlPieceSchematic.make_from_gp_grade_and_container(
                gp, gp_grade, return_me
            )
            grade.save()
        return return_me

    def get_pieces_class(self):
        return GradedCowlPatternPieces


################################################################################################################
#
# Pieces
#
################################################################################################################


class _BaseCowlPiece(models.Model):
    class Meta:
        abstract = True

    cast_on_stitches = StrictPositiveSmallIntegerField()
    main_pattern_stitches = StrictPositiveSmallIntegerField()
    edging_height_in_rows = StrictPositiveSmallIntegerField()
    total_rows = StrictPositiveSmallIntegerField()

    @property
    def first_main_section_row(self):
        return self.edging_height_in_rows + 1

    @property
    def last_main_section_row(self):
        return self.total_rows - self.edging_height_in_rows - 1

    @property
    def first_row_castoff_section(self):
        return self.last_main_section_row + 1

    @property
    def first_row_second_horizontal_panel(self):
        spec_source = self.get_spec_source()
        if spec_source.horizontal_panel_rounds:
            return self.first_row_castoff_section - spec_source.horizontal_panel_rounds
        else:
            return None

    @property
    def first_row_second_horizontal_panel_in_inches(self):
        first_row_second_horizontal_panel = self.first_row_second_horizontal_panel
        if first_row_second_horizontal_panel is None:
            return None
        else:
            row_gauge = self.gauge.rows
            return first_row_second_horizontal_panel / row_gauge

    @property
    def edging_stitch(self):
        spec_source = self.get_spec_source()
        return spec_source.edging_stitch

    @property
    def main_stitch(self):
        spec_source = self.get_spec_source()
        return spec_source.main_stitch

    def main_stitch_name(self):
        main_stitch = self.main_stitch
        return main_stitch.name

    def edging_stitch_name(self):
        edging_stitch = self.edging_stitch
        return edging_stitch.name

    def actual_circumference(self):
        return self.cast_on_stitches / self.gauge.stitches

    def actual_height(self):
        return self.total_rows / self.gauge.rows

    def area(self):
        return self.actual_circumference() * self.actual_height()

    def actual_edging_height(self):
        return self.edging_height_in_rows / self.gauge.rows

    def cast_on_to_main_section_end_in_inches(self):
        return self.last_main_section_row / self.gauge.rows

    def _inner_make(self, schematic):

        spec_source = schematic.get_spec_source()

        goal_height = schematic.height
        goal_circ = schematic.circumference
        goal_edging_height = schematic.edging_height

        row_gauge = spec_source.get_row_gauge()
        stitch_gauge = spec_source.get_stitch_gauge()

        total_rows = _find_best_approximation(
            goal_height, row_gauge, ROUND_UP, float("inf")
        )

        edging_height_in_rows = _find_best_approximation(
            goal_edging_height, row_gauge, ROUND_DOWN, float("inf")
        )

        (x_mod, mod_y) = spec_source.get_repeats_spec()

        cast_on_stitches = _find_best_approximation(
            goal_circ, stitch_gauge, ROUND_ANY_DIRECTION, float("inf"), x_mod, mod_y
        )

        main_pattern_stitches = cast_on_stitches

        if spec_source.extra_cable_stitches:
            main_pattern_stitches += spec_source.extra_cable_stitches
            if not spec_source.extra_cable_stitches_are_main_pattern_only:
                cast_on_stitches += spec_source.extra_cable_stitches

        self.cast_on_stitches = cast_on_stitches
        self.main_pattern_stitches = main_pattern_stitches
        self.edging_height_in_rows = edging_height_in_rows
        self.total_rows = total_rows

    def clean(self):
        super(_BaseCowlPiece, self).clean()

        if self.total_rows <= (2 * self.edging_height_in_rows):
            raise ValidationError("Edging height more than half the full height")

        needed_rows = sum(
            [
                2 * self.edging_height_in_rows,
                2 * self.get_spec_source().horizontal_panel_rounds,
                2
                * self.get_spec_source()
                .swatch.get_gauge()
                .rows,  # 2 inches for the filler rows
            ]
        )
        if self.total_rows < needed_rows:
            raise ValidationError("Not tall enough for all elements")


class CowlPiece(PatternPiece, _BaseCowlPiece):

    schematic = models.OneToOneField(CowlGarmentSchematic, on_delete=models.CASCADE)

    _pattern_field_name = "cowl"

    def get_spec_source(self):
        return self.schematic.get_spec_source()

    @property
    def swatch(self):
        spec_source = self.get_spec_source()
        return spec_source.swatch

    @property
    def gauge(self):
        return self.swatch.get_gauge()

    def get_pattern(self):
        return self.cowlpatternpieces.individualpattern

    @classmethod
    def make(cls, schematic):
        return_me = cls(schematic=schematic)
        return_me._inner_make(schematic.cowl_piece)
        return_me.full_clean()
        return_me.save()
        return return_me


class CowlAreaMixin(AreaMixin):
    def _trim_area(self):
        return 0


class CowlPatternPieces(CowlAreaMixin, PatternPieces):

    cowl = models.OneToOneField(CowlPiece, on_delete=models.CASCADE)

    def sub_pieces(self):
        return [self.cowl]

    @classmethod
    def make_from_individual_pieced_schematic(cls, ips):
        parameters = {"schematic": ips}

        cowl = CowlPiece.make(ips)
        parameters["cowl"] = cowl

        instance = cls(**parameters)
        return instance

    def get_schematic_image(self):
        return self.schematic.get_schematic_image()


class GradedCowlPiece(GradedPatternPiece, _BaseCowlPiece):

    class Meta:
        ordering = ["sort_key"]

    @classmethod
    def make_from_schematic_and_container(cls, grade_schematic, container):
        return_me = cls()
        return_me.graded_pattern_pieces = container
        return_me._inner_make(grade_schematic)
        return_me.sort_key = return_me.total_rows
        return_me.save()
        return return_me

    def get_spec_source(self):
        spec_source = self.graded_pattern_pieces.get_spec_source()
        return spec_source

    @property
    def gauge(self):
        spec_source = self.get_spec_source()
        row_gauge = spec_source.get_row_gauge()
        stitch_gauge = spec_source.get_stitch_gauge()
        return Gauge(stitch_gauge, row_gauge)


class GradedCowlPatternPieces(GradedPatternPieces):

    def get_pattern_class(self):
        return GradedCowlPattern

    @classmethod
    def make_from_schematic(cls, graded_construction_schematic):
        return_me = cls()
        return_me.schematic = graded_construction_schematic
        return_me.save()
        for grade_schematic in graded_construction_schematic.all_grades:
            grade = GradedCowlPiece.make_from_schematic_and_container(
                grade_schematic, return_me
            )
        return return_me

    def area_list(self):

        # First, a helper class
        class CowlGradeArea(CowlAreaMixin):
            def __init__(self, cowl_piece, *args, **kwargs):
                self.cowl_piece = cowl_piece
                super(CowlGradeArea, self).__init__(*args, **kwargs)

            def sub_pieces(self):
                return [self.cowl_piece]

        areas = [CowlGradeArea(piece).area() for piece in self.all_pieces]
        return areas


################################################################################################################
#
# Pattern
#
################################################################################################################


class CowlPattern(IndividualPattern):

    @classmethod
    def make_from_individual_pattern_pieces(cls, user, ipp):
        parameters = {"user": user, "name": ipp.schematic.name, "pieces": ipp}
        instance = cls(**parameters)
        return instance

    def get_schematic_display_context(self):
        context = {}

        context["schematic_image"] = self.pieces.get_schematic_image()
        context["dimensions"] = [
            ("actual height", self.actual_height()),
            ("actual circumference", self.actual_circumference()),
            ("actual edging height", self.actual_edging_height()),
        ]

        return context

    abridged_pdf_renderer_class = CowlPatternRendererPdfAbridged
    full_pdf_renderer_class = CowlPatternRendererPdfFull
    web_renderer_class = CowlPatternRendererWebFull

    def actual_height(self):
        return self.pieces.cowl.actual_height()

    def actual_circumference(self):
        return self.pieces.cowl.actual_circumference()

    def actual_edging_height(self):
        return self.pieces.cowl.actual_edging_height()

    @property
    def main_stitch(self):
        return self.get_spec_source().main_stitch

    @property
    def gauge(self):
        return self.get_spec_source().gauge


class GradedCowlPattern(GradedPattern):

    @classmethod
    def make_from_graded_pattern_pieces(cls, gpp):
        parameters = {"name": gpp.schematic.name, "pieces": gpp}

        instance = cls(**parameters)
        return instance

    abridged_pdf_renderer_class = None
    full_pdf_renderer_class = None
    web_renderer_class = GradedCowlPatternRendererWebFull

    @property
    def gauge(self):
        return self.get_spec_source().gauge


################################################################################################################
#
# Redo
#
################################################################################################################


class CowlRedo(Redo, CowlIndividualBase):

    def clean(self):
        super(CowlRedo, self).clean()

        if self.total_height_in_inches() <= (
            (3 * self.edging_stitch_height) + FLOATING_POINT_NOISE
        ):
            raise ValidationError("Edging-height more than one-third the total height")
