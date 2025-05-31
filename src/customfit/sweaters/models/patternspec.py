# -*- coding: utf-8 -*-
import logging

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from customfit.bodies.models import Body, GradeSet
from customfit.pattern_spec.models import GradedPatternSpec, PatternSpec
from customfit.swatches.models import Gauge, Swatch

from ..helpers import sweater_design_choices as SDC
from .designs import SweaterDesignBase

logger = logging.getLogger(__name__)

MAKE_YOUR_OWN_SWEATER = "make_your_own_sweater"


class GarmentFitField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 25
        kwargs["choices"] = SDC.GARMENT_FIT_CHOICES
        super(GarmentFitField, self).__init__(*args, **kwargs)


class BaseSweaterPatternSpec(SweaterDesignBase):

    silhouette = models.CharField(max_length=25, choices=SDC.SILHOUETTE_CHOICES)

    construction = models.CharField(max_length=15, choices=SDC.SUPPORTED_CONSTRUCTIONS)

    garment_fit = GarmentFitField()

    @property
    def is_hourglass(self):
        return self.silhouette == SDC.SILHOUETTE_HOURGLASS

    @property
    def is_half_hourglass(self):
        return self.silhouette == SDC.SILHOUETTE_HALF_HOURGLASS

    @property
    def is_straight(self):
        return self.silhouette == SDC.SILHOUETTE_STRAIGHT

    @property
    def is_aline(self):
        return self.silhouette == SDC.SILHOUETTE_ALINE

    @property
    def is_tapered(self):
        return self.silhouette == SDC.SILHOUETTE_TAPERED

    @property
    def is_set_in_sleeve(self):
        return self.construction == SDC.CONSTRUCTION_SET_IN_SLEEVE

    @property
    def is_drop_shoulder(self):
        return self.construction == SDC.CONSTRUCTION_DROP_SHOULDER

    def get_garment(self):
        return "sweaters"

    def silhouette_patterntext(self):
        # Note: get_silhouette_display() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_silhouette_display()

    def drop_shoulder_armhole_length_patterntext(self):
        # Note: get_silhouette_display() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_drop_shoulder_additional_armhole_depth_display()

    @staticmethod
    def get_neckline_class(neckline_id):
        from .pieces import (
            BackNeckline,
            BoatNeck,
            CrewNeck,
            ScoopNeck,
            TurksAndCaicosNeck,
            VeeNeck,
        )

        class_dict = {
            SDC.NECK_BACK: BackNeckline,  # for completeness
            SDC.NECK_VEE: VeeNeck,
            SDC.NECK_CREW: CrewNeck,
            SDC.NECK_SCOOP: ScoopNeck,
            SDC.NECK_BOAT: BoatNeck,
            SDC.NECK_TURKS_AND_CAICOS: TurksAndCaicosNeck,
        }
        return class_dict[neckline_id]

    def _get_first_nontrivial_repeats(self, stitch_list):
        """
        Given a list of Stitches, returns the RepeatSpec for the first
        stitch in the list to use repeats. Returns None if no stitch uses
        repeats.
        """
        for stitch in stitch_list:
            if stitch is not None:
                if stitch.use_repeats:
                    return stitch.get_repeats_spec()
        return None

    def fit_patterntext(self):
        # Note: get_garment_fit_display() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_garment_fit_display()

    def get_waist_hem_template(self):
        return self._stitch_or_design_template(
            "waist_hem_template",
            self.hip_edging_stitch,
            self.hip_edging_height > 0,
            "waist_hem_stitch_template",
            "sweater_pattern_spec",
            "waist_hem.html",
        )

    def get_sleeve_hem_template(self):
        return self._stitch_or_design_template(
            "sleeve_hem_template",
            self.sleeve_edging_stitch,
            self.sleeve_edging_height > 0,
            "sleeve_hem_template",
            "sweater_pattern_spec",
            "sleeve_hem.html",
        )

    def get_trim_armhole_template(self):
        return self._stitch_or_design_template(
            "trim_armhole_template",
            self.armhole_edging_stitch,
            self.armhole_edging_height > 0,
            "trim_armhole_template",
            "sweater_pattern_spec",
            "trim_armhole.html",
        )

    def get_trim_neckline_template(self):
        return self._stitch_or_design_template(
            "trim_neckline_template",
            self.neck_edging_stitch,
            self.neck_edging_height > 0,
            "trim_neckline_template",
            "sweater_pattern_spec",
            "trim_neckline.html",
        )

    def get_button_band_template(self):
        return self._stitch_or_design_template(
            "button_band_template",
            self.button_band_edging_stitch,
            self.button_band_edging_height > 0,
            "button_band_template",
            "sweater_pattern_spec",
            "button_band.html",
        )

    def get_button_band_veeneck_template(self):
        return self._stitch_or_design_template(
            "button_band_veeneck_template",
            self.button_band_edging_stitch,
            self.button_band_edging_height > 0,
            "button_band_veeneck_template",
            "sweater_pattern_spec",
            "button_band_veeneck.html",
        )

    def get_extra_finishing_template(self):
        return self._get_from_origin("extra_finishing_template")

    def get_additional_element_stitches(self):
        design_origin = self.design_origin
        if design_origin is not None:
            return design_origin.get_additional_element_stitches()
        else:
            return []

    def clean(self):
        """
        This validates that elements of the *garment itself* - the design
        choices and the swatch - are internally consistent (e.g. the swatch
        repeat count respects the pattern stitch repeat count; the silhouette
        and fit are compatible).

        Validation that depends on *the relationship between the body and the
        garment* is deferred to IGP.

        The reason for this is that the body can change after the PatternSpec
        is created, if users add missing measurements, so we need to defer
        that validation. However, users cannot change their gauges, and if they
        change things like garment fit we'll create a new PatternSpec.
        Therefore, not only is this the first place where we have all of the
        design choices and the swatch set, but it's safe to validate here
        because those properties will not change.

        (Note: if it ever becomes possible to use multiple swatches in one
        garment, reconsider this clean() method.)
        """
        super(BaseSweaterPatternSpec, self).clean()

        errors = []

        # Check that design is an hourglass silhouette iff
        # the selected fit is an hourglass fit.
        if self.silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:
            if self.garment_fit not in SDC.FIT_HOURGLASS:
                errors.append(
                    ValidationError(
                        "Must use hourglass fit with hourglass/half-hourglass silhouette"
                    )
                )

        else:
            if self.garment_fit in SDC.FIT_HOURGLASS:
                errors.append(
                    ValidationError(
                        "Cannot use hourglass fit with non-hourglass/half-hourglass silhouette"
                    )
                )

        # If drop-shoulder is allowed, then must set default depth
        if self.is_drop_shoulder:
            if self.drop_shoulder_additional_armhole_depth is None:
                errors.append(
                    ValidationError(
                        "Drop-shoulder sweaters need a valid drop-shoulder armhole depth"
                    )
                )

        # If default_depth must be blank if drop-shoulder not allowed
        if not self.is_drop_shoulder:
            if self.drop_shoulder_additional_armhole_depth is not None:
                errors.append(
                    ValidationError(
                        "Non-drop-shoulder sweaters should not set drop-shoulder armhole depth."
                    )
                )

        # Note: We used to also test that the fit matched the 'gender' of the
        # body (man/woman/child, with all fits matching the UNSTATED gender).
        # We deliberately decided to stop doing that as (1) the engine does
        # not require it, and (2) why not let people apply any fit they want,
        # if they are willing to jump through a few extra UI hoops to do so?

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class SweaterPatternSpec(PatternSpec, BaseSweaterPatternSpec):

    # Should really be called IndividualSweaterPatternSpec, but called just this for historical reasons.

    body = models.ForeignKey(
        Body,
        help_text="Body for which this design is intended",
        related_name="+",
        on_delete=models.CASCADE,
    )

    @property
    def gauge(self):
        return self.swatch.get_gauge()

    def get_igp_class(self):
        from .garment_parameters import SweaterIndividualGarmentParameters

        return SweaterIndividualGarmentParameters

    def __str__(self):
        return "PatternSpec %s/%s" % (self.name, self.user)

    def front_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the waist hem for
        front pieces. This will be the first non-trivial repeat from the
        following list:

        * Front allover stitch repeats,
        * Swatch allover stitch repeats,
        * Waist edging stitch repeats

        Returns None if there are no non-trivial repeats.
        """
        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [
            self.front_allover_stitch,
            self.swatch.get_stitch(),
            self.hip_edging_stitch,
        ]

        return self._get_first_nontrivial_repeats(stitches)

    def back_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the waist hem for
        back pieces. This will be the first non-trivial repeat from the
        following list:

        * Back allover stitch repeats,
        * Swatch allover stitch repeats,
        * Waist edging stitch repeats
        """

        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [
            self.back_allover_stitch,
            self.swatch.get_stitch(),
            self.hip_edging_stitch,
        ]

        return self._get_first_nontrivial_repeats(stitches)

    def sleeve_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the hem for
        sleeves. This will be the first non-trivial repeat from the
        following list:

        * Sleeve allover stitch repeats,
        * Swatch allover stitch repeats,
        * Sleeve edging stitch repeats
        """
        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [
            self.sleeve_allover_stitch,
            self.swatch.get_stitch(),
            self.sleeve_edging_stitch,
        ]

        return self._get_first_nontrivial_repeats(stitches)

    def clean(self):
        super(SweaterPatternSpec, self).clean()
        errors = []
        # Is the allover stitch from the swatch compatible with the allover
        # stitches of the design?
        try:
            swatch = self.swatch
        except Swatch.DoesNotExist:
            errors.append(ValidationError("Please choose a swatch"))
        else:
            swatch_stitch = swatch.get_stitch()
            if not swatch_stitch.is_compatible(self.front_allover_stitch):
                errors.append(
                    ValidationError(
                        "Sorry, but the stitch repeat count "
                        "of your swatch does not match the "
                        "repeat count of the front allover "
                        "stitch.  Please choose a new "
                        "swatch or new front allover stitch."
                    )
                )
            if not swatch_stitch.is_compatible(self.back_allover_stitch):
                errors.append(
                    ValidationError(
                        "Sorry, but the stitch repeat count "
                        "of your swatch does not match the "
                        "repeat count of the back allover "
                        "stitch.  Please choose a new "
                        "swatch or new back allover stitch."
                    )
                )
            if not swatch_stitch.is_compatible(self.sleeve_allover_stitch):
                errors.append(
                    ValidationError(
                        "Sorry, but the stitch repeat count "
                        "of your swatch does not match the "
                        "repeat count of the sleeve allover "
                        "stitch.  Please choose a new "
                        "swatch or new sleeve allover stitch."
                    )
                )
            if errors:
                raise ValidationError(errors)


class GradedSweaterPatternSpec(GradedPatternSpec, BaseSweaterPatternSpec):

    gradeset = models.ForeignKey(GradeSet, related_name="+", on_delete=models.CASCADE)

    row_gauge = models.FloatField(help_text="Number of rows over four inches")
    stitch_gauge = models.FloatField(
        help_text="Number of stitches over four inches",
        validators=[MinValueValidator(12)],
    )

    @property
    def gauge(self):
        return Gauge(self.get_stitch_gauge(), self.get_row_gauge())

    def get_row_gauge(self):
        return self.row_gauge / 4.0

    def get_stitch_gauge(self):
        return self.stitch_gauge / 4.0

    def all_grades(self):
        return self.gradeset.grades

    def front_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the waist hem for
        front pieces. This will be the first non-trivial repeat from the
        following list:

        * Front allover stitch repeats,
        * Waist edging stitch repeats

        Returns None if there are no non-trivial repeats.
        """
        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [self.front_allover_stitch, self.hip_edging_stitch]

        return self._get_first_nontrivial_repeats(stitches)

    def back_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the waist hem for
        back pieces. This will be the first non-trivial repeat from the
        following list:

        * Back allover stitch repeats,
        * Waist edging stitch repeats
        """

        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [self.back_allover_stitch, self.hip_edging_stitch]

        return self._get_first_nontrivial_repeats(stitches)

    def sleeve_repeats(self):
        """
        Return a RepeatsSpec to use when casting on the hem for
        sleeves. This will be the first non-trivial repeat from the
        following list:

        * Sleeve allover stitch repeats,
        * Sleeve edging stitch repeats
        """
        # Note: the order of the following list
        # reflects domain-specific knowledge
        stitches = [self.sleeve_allover_stitch, self.sleeve_edging_stitch]

        return self._get_first_nontrivial_repeats(stitches)

    def get_igp_class(self):
        from .garment_parameters import SweaterGradedGarmentParameters

        return SweaterGradedGarmentParameters

    def __str__(self):
        return "GradedPatternSpec %s/%s" % (self.name, self.user)
