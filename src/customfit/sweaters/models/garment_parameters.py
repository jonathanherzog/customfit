import logging
import math
from collections import defaultdict

import reversion
from django.core.exceptions import ValidationError
from django.db import models

import customfit.sweaters.helpers.sweater_design_choices as SDC
from customfit.bodies.models import Body, Grade
from customfit.fields import LengthField
from customfit.garment_parameters.models import (
    GradedGarmentParameters,
    GradedGarmentParametersGrade,
    IndividualGarmentParameters,
    MissingMeasurement,
)
from customfit.patterns.templatetags.pattern_conventions import length_fmt

from ..helpers.magic_constants import (
    ALINE_WAIST_TO_BUST,
    BUSTTOARMPIT,
    BUSTY_WOMAN_THRESHOLD,
    CROSS_CHEST_EASE_FOR_DROP_SHOULDER_NECKLINE,
    DROP_SHOULDER_ARMHOLE_DEPTH_INCHES,
    DROP_SHOULDER_FRONT_BUST_THRESHOLDS,
    FORCED_SHAPING_BACK_HIP,
    MIN_ARMHOLE_WIDTH_DROP_SHOULDER,
    MIN_ARMHOLE_WIDTH_SET_IN_SLEEVE,
    MINIMUM_ALINE_BUST_CIRC_TO_HIP_CIRC_DIFF,
    MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF,
    NECKDEPTH,
    NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR,
    NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS,
    ONEINCH,
    UPPER_TORSO_EASE_FOR_DROP_SHOULDER_NECKLINE,
    childrens_cross_chest_table,
    mens_cross_chest_table,
    womens_cross_chest_table,
)
from ..helpers.secret_sauce import bell_eases, get_eases, neck_width_ratio

logger = logging.getLogger(__name__)


class _SweaterGarmentParametersTopLevel(models.Model):
    class Meta:
        abstract = True


class _SweaterGarmentDimensions(models.Model):
    class Meta:
        abstract = True

    ############################################################################
    #
    # Body heights
    #
    ############################################################################

    # Currently, waist_height_front and waist_height_back are always set to
    # the same height. This may change in the future,
    # so we're keeping both fields in the model.

    waist_height_front = LengthField(
        blank=True,
        null=True,  # Will be None for non-hourglass garments
        help_text="Front length from hip cast-ons to waist-shaping (in inches)",
    )

    waist_height_back = LengthField(
        blank=True,
        null=True,  # Will be None for non-hourglass garments
        help_text="Back length from hip cast-ons to waist-shaping (in inches)",
    )

    armpit_height = LengthField(
        help_text="Length, along side, from armhole shaping to hip-cast-ons (in inches)"
    )

    armhole_depth = LengthField(
        help_text="Vertical distance from shoulder-top straight down to armhole-start (in inches)"
    )

    below_armhole_straight = LengthField(
        # Note: this field was added late, and so the initial ~55K IGPs
        # did not have it. Rather than allowing those schematics to have
        # None in this field, we gave them a default value of 1.5 (the then-current
        # value of BUSTTOARMPIT). If you need to perform some sort of migration or
        # computation on schematics, be aware that a value of exactly 1.5 here
        # is likely to be bogus.
        help_text="Ideal amount of straight distance between end of "
        "bust shaping and beginning of armhole shaping. "
        "Engine will violate this parameter if it needs additional "
        "vertical distance for the desired shaping."
    )

    back_neck_depth = LengthField(
        help_text="Vertical distance from shoulder-top to bottom of back neck (in inches)"
    )

    front_neck_depth = LengthField(
        help_text="Vertical distance from shoulder-top to bottom of front neck (in inches)"
    )

    ############################################################################
    #
    # Body widths
    #
    ############################################################################

    hip_width_back = LengthField(
        help_text="Width of garment back at cast-on (in inches)"
    )

    hip_width_front = LengthField(
        help_text="Width of garment front at bottom-hem  (in inches)"
    )

    bust_width_back = LengthField(help_text="Width of garment back at bust (in inches)")

    bust_width_front = LengthField(
        help_text="Width of garment front at bust (in inches)"
    )

    back_cross_back_width = LengthField(
        help_text="Width remaining between armholes after armhole shaping (sweater "
        "back; in inches)"
    )

    back_neck_opening_width = LengthField(
        help_text="Width of the neck opening (in inches)"
    )

    # Note: the following two fields are only not None for hourglas
    # silhouettes

    waist_width_back = LengthField(
        blank=True, null=True, help_text="Width of garment back at waist (in inches)"
    )

    waist_width_front = LengthField(
        blank=True, null=True, help_text="Width of garment front at waist (in inches)"
    )

    ############################################################################
    #
    # Sleeve measurements. Will be None for vests
    #
    ############################################################################

    sleeve_to_armcap_start_height = LengthField(
        null=True,
        blank=True,
        help_text="Length from sleeve cast-ons to top of armscye (in inches)",
    )

    bicep_width = LengthField(
        null=True, blank=True, help_text="Width of the sleeve at the bicep (in inches)"
    )

    sleeve_cast_on_width = LengthField(
        null=True,
        blank=True,
        help_text="Width of the sleeve at cast-on  (wherever that falls on the arm; in inches)",
    )

    ############################################################################
    #
    # Missing measurements
    #
    ############################################################################

    hip_length_dict = {
        SDC.HIGH_HIP_LENGTH: "armpit_to_high_hip",
        SDC.MED_HIP_LENGTH: "armpit_to_med_hip",
        SDC.LOW_HIP_LENGTH: "armpit_to_low_hip",
        SDC.TUNIC_LENGTH: "armpit_to_tunic",
    }

    hip_circ_dict = {
        SDC.HIGH_HIP_LENGTH: "high_hip_circ",
        SDC.MED_HIP_LENGTH: "med_hip_circ",
        SDC.LOW_HIP_LENGTH: "low_hip_circ",
        SDC.TUNIC_LENGTH: "tunic_circ",
    }

    sleeve_length_dict = {
        SDC.SLEEVE_SHORT: "armpit_to_short_sleeve",
        SDC.SLEEVE_ELBOW: "armpit_to_elbow_sleeve",
        SDC.SLEEVE_THREEQUARTER: "armpit_to_three_quarter_sleeve",
        SDC.SLEEVE_FULL: "armpit_to_full_sleeve",
    }

    arm_circ_dict = {
        SDC.SLEEVE_SHORT: "bicep_circ",
        SDC.SLEEVE_ELBOW: "elbow_circ",
        SDC.SLEEVE_THREEQUARTER: "forearm_circ",
        SDC.SLEEVE_FULL: "wrist_circ",
    }

    @classmethod
    def _inner_missing_body_fields(cls, patternspec, grade):

        body_fields = grade._meta.fields
        body_field_dict = {f.name: f for f in body_fields}
        needed_fields = set()

        # Helper function
        def add_needed_field(field_name):
            needed_fields.add(body_field_dict[field_name])

        add_needed_field("armhole_depth")
        add_needed_field(cls.hip_length_dict[patternspec.torso_length])

        if patternspec.is_hourglass or patternspec.is_half_hourglass:
            add_needed_field("bust_circ")
            add_needed_field("upper_torso_circ")
            add_needed_field("med_hip_circ")
            add_needed_field("waist_circ")
            add_needed_field("armpit_to_waist")
            # Note: the following is only needed in certain cases, but
            # it is too complex to try to describe those cases here.
            add_needed_field(cls.hip_circ_dict[patternspec.torso_length])
        else:
            add_needed_field("waist_circ")
            add_needed_field("bust_circ")

            if patternspec.is_aline:
                add_needed_field(cls.hip_circ_dict[patternspec.torso_length])
            elif patternspec.is_tapered:
                add_needed_field(cls.hip_circ_dict[patternspec.torso_length])
            else:
                assert patternspec.is_straight
                add_needed_field(cls.hip_circ_dict[patternspec.torso_length])

        if patternspec.has_sleeves():
            add_needed_field(cls.sleeve_length_dict[patternspec.sleeve_length])
            if not patternspec.is_drop_shoulder:
                add_needed_field("bicep_circ")
            if patternspec.sleeve_shape == SDC.SLEEVE_TAPERED:
                add_needed_field(cls.arm_circ_dict[patternspec.sleeve_length])

        add_needed_field("bust_circ")

        # Add more fields for properties and methods other than _make

        # hip_circ_original
        add_needed_field(cls.hip_circ_dict[patternspec.torso_length])

        # waist_ease
        if not patternspec.is_hourglass:
            add_needed_field("waist_circ")

        # bicep_ease
        if (
            patternspec.has_sleeves()
            and patternspec.construction != SDC.CONSTRUCTION_DROP_SHOULDER
        ):
            add_needed_field("bicep_circ")

        # sleeve_ease
        if patternspec.has_sleeves():
            add_needed_field(cls.arm_circ_dict[patternspec.sleeve_length])

        # adjust_for_negative_ease, unadjust_for_negative_ease
        add_needed_field(cls.hip_circ_dict[patternspec.torso_length])
        add_needed_field("bust_circ")

        # Now we have all of the needed fields in needed_fields.
        # Return (as a set) all that are None
        missing_fields = set(
            field for field in needed_fields if getattr(grade, field.name) is None
        )

        return missing_fields

    ############################################################################
    #
    # Useful measurement properties
    #
    ############################################################################

    @property
    def hip_circ_total(self):
        """
        Total circumference of the garment at the hip (in inches).
        Equal to sum of front and back.
        """
        return self.hip_width_front + self.hip_width_back

    @property
    def waist_circ_total(self):
        """
        Total circumference of the garment at the waist (in inches).
        Equal to sum of front and back.
        """
        if any([self.waist_width_front is None, self.waist_width_back is None]):
            return None
        else:
            return self.waist_width_front + self.waist_width_back

    @property
    def hip_circ_original(self):
        """
        This returns the hip circ of the *original body* at the cast-on height
        (needed in templates). This may be quite different from the garment
        circ at cast-on (which not only adds eases, but may be based on a
        different circumference entirely - e.g. a tunic will have a cast-on
        width sufficient to accommodate hips, and may therefore have a cast-on
        width based on a hip circ rather than the tunic circ).
        """

        spec_source = self.get_spec_source()
        return self._get_relevant_grade_attr(
            self.hip_circ_dict, spec_source.torso_length
        )

    @property
    def bust_circ_total(self):
        """
        Total circumference of the garment at the bust (in inches).
        Equal to sum of front and back.
        """
        return self.bust_width_front + self.bust_width_back

    #
    # Properties for eases
    # -------------------------------------------------------------------------
    @property
    def bust_ease(self):
        return self.bust_circ_total - self.grade.bust_circ

    @property
    def waist_ease(self):
        if self.waist_circ_total:
            if self.grade.waist_circ:
                return self.waist_circ_total - self.grade.waist_circ
            else:
                raise MissingMeasurement("waist_circ")
        else:
            return None

    @property
    def hip_ease(self):
        return self.hip_circ_total - self._get_hip_circ()

    @property
    def bicep_ease(self):
        if self.bicep_width:
            if self.grade.bicep_circ:
                return self.bicep_width - self.grade.bicep_circ
            else:
                raise MissingMeasurement("bicep_circ")
        else:
            return None

    @property
    def sleeve_ease(self):
        if self.sleeve_cast_on_width:
            return self.sleeve_cast_on_width - self._get_relevant_arm_circ_from_body()
        else:
            return None

    #
    # Properties for garment heights
    # -------------------------------------------------------------------------

    @property
    def shoulder_height(self):
        return sum([self.armpit_height, self.armhole_depth])

    @property
    def back_neck_height(self):
        return self.shoulder_height - self.back_neck_depth

    @property
    def front_neck_height(self):
        return self.shoulder_height - self.front_neck_depth

    @property
    def torso_hem_height(self):
        spec_source = self.get_spec_source()
        return spec_source.hip_edging_height

    @property
    def button_band_edging_height(self):
        spec_source = self.get_spec_source()
        return spec_source.button_band_edging_height

    @property
    def sleeve_edging_height(self):
        spec_source = self.get_spec_source()
        if spec_source.has_sleeves():
            return spec_source.sleeve_edging_height
        else:
            return None

    @property
    def waist_to_armhole(self):
        assert self.waist_height_front == self.waist_height_back
        if self.waist_height_front is None:
            return None
        else:
            return self.armpit_height - self.waist_height_front

    @property
    def shoulder_height(self):
        return sum([self.armpit_height, self.armhole_depth])

    @property
    def back_neck_height(self):
        return self.shoulder_height - self.back_neck_depth

    @property
    def front_neck_height(self):
        return self.shoulder_height - self.front_neck_depth

    #
    # Other properties
    # -------------------------------------------------------------------------

    @property
    def fit_text(self):
        spec_source = self.get_spec_source()
        fit = spec_source.garment_fit
        return SDC.GARMENT_FIT_USER_TEXT[fit]

    @property
    def silhouette_text(self):
        spec_source = self.get_spec_source()
        silhouette = spec_source.silhouette
        return SDC.SILHOUETTE_USER_TEXT[silhouette]

    @property
    def button_band_allowance(self):
        """
        Gap between cardigan fronts (in inches). Note: if this not is None,
        then button_band_allowance_percentage must be None.
        """
        spec_source = self.get_spec_source()
        return spec_source.button_band_allowance

    @property
    def button_band_allowance_percentage(self):
        """
        Gap between cardigan fronts (as percentage of neck width).
        Note: if this not is None, then button_band_allowance must be None.
        """
        spec_source = self.get_spec_source()
        return spec_source.button_band_allowance_percentage

    @property
    def front_neck_opening_width(self):
        # If the front bust is bigger than the back bust, then the additional
        # width is pushed into the neckline.
        return sum(
            [self.back_neck_opening_width, self.bust_width_front, -self.bust_width_back]
        )

    @property
    def waist_to_armhole(self):
        assert self.waist_height_front == self.waist_height_back
        if self.waist_height_front is None:
            return None
        else:
            return self.armpit_height - self.waist_height_front

    @property
    def shoulder_height(self):
        return sum([self.armpit_height, self.armhole_depth])

    @property
    def back_neck_height(self):
        return self.shoulder_height - self.back_neck_depth

    @property
    def front_neck_height(self):
        return self.shoulder_height - self.front_neck_depth

    ############################################################################
    #
    # Adjust/unadjust for negative ease
    #
    ############################################################################

    def adjust_lengths_for_negative_ease(self):
        """
        Increase some of the lengths (sleeve, hem-to-waist, armhole-to-waist)
        if there is negative ease in the circumferences. Note that this
        changes the internal models. If you run this twice, you will increase
        lengths twice. (Called out into its own method so that it
        can be used both in _inner_make() and in the
        TweakIndividualGarmentParameters form.
        """

        # Note: if you modify this method, you need to also modify
        # unadjust_lengths_for_negative_ease

        hip_ease = self.hip_circ_total - self._get_hip_circ()
        if hip_ease < NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS:
            # NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS is negative, and so
            # hip_ease must be negative, too. We negate it before the
            # multiplication, below, so that length_to_add will be positive
            # and thus easier to think about.
            length_to_add = -hip_ease * NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR
            if self.waist_height_front is not None:
                self.waist_height_front += length_to_add
            if self.waist_height_back is not None:
                self.waist_height_back += length_to_add
            self.armpit_height += length_to_add

        if self.grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")
        bust_ease = self.bust_circ_total - self.grade.bust_circ
        if bust_ease < NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS:
            # NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS is negative, and so
            # bust_ease must be negative, too. We negate it before the
            # multiplication, below, so that length_to_add will be positive
            # and thus easier to think about.
            length_to_add = -bust_ease * NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR
            self.armpit_height += length_to_add

    def unadjust_lengths_for_negative_ease(self):
        """
        Return what the waist-heights and armhole height to what they
        *would* have been before they were adjusted for negative ease.
        Used in the TweakIndividualGarmentParameters to present the user
        with the as-worn lengths (as opposed to the as-knit) lengths
        stored in this model.

        Returns tuple: (re-adjusted waist-height-front,
                        re-adjusted waist-height-back,
                        re-adjusted armhole-height,
                        re-adjusted sleeve-to-armcap-start-height)
        """

        # Note: if you modify this method, you need to also modify
        # adjust_lengths_for_negative_ease

        readj_waist_height_front = self.waist_height_front
        readj_waist_height_back = self.waist_height_back
        readj_armpit_height = self.armpit_height
        readj_sleeve_length = self.sleeve_to_armcap_start_height

        hip_ease = self.hip_circ_total - self._get_hip_circ()
        if hip_ease < NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS:
            # NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS is negative, and so
            # hip_ease must be negative, too. As in
            # adjust_lengths_for_negative_ease, we negate it before the
            # multiplication, below, so that length_added will be positive
            # and thus easier to think about.
            length_added = -hip_ease * NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR
            if readj_waist_height_front is not None:
                readj_waist_height_front -= length_added
            if readj_waist_height_back is not None:
                readj_waist_height_back -= length_added
            readj_armpit_height -= length_added

        if self.grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")
        bust_ease = self.bust_circ_total - self.grade.bust_circ
        if bust_ease < NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS:
            # NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS is negative, and so
            # bust_ease must be negative, too. As in
            # adjust_lengths_for_negative_ease, we negate it before the
            # multiplication, below, so that length_added will be positive
            # and thus easier to think about.
            length_added = -bust_ease * NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR
            readj_armpit_height -= length_added

        return (
            readj_waist_height_front,
            readj_waist_height_back,
            readj_armpit_height,
            readj_sleeve_length,
        )

    ############################################################################
    #
    # _set_garment_dimensions()
    #
    ############################################################################

    def set_garment_dimensions(self, spec_source, grade):
        """
        Does all the hard, messy work of setting the parameters of a
        IndividualGarmentParameters from user-level inputs.
        """

        #################################################################
        # Set-up
        #################################################################

        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)

        #################################################################
        # Torso measurements, set up.
        ##################################################################

        if grade.armhole_depth is None:
            raise MissingMeasurement("armhole_depth")

        pre_ease_armhole_depth = grade.armhole_depth
        # Needed for neckline-depth computation; not saved with model
        self.sis_armhole_depth = sum([pre_ease_armhole_depth, eases["armhole_depth"]])
        if spec_source.is_drop_shoulder:
            self.armhole_depth = sum(
                [
                    self.sis_armhole_depth,
                    DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[
                        spec_source.drop_shoulder_additional_armhole_depth
                    ],
                ]
            )
        else:
            self.armhole_depth = self.sis_armhole_depth

        self.armpit_height = sum(
            [self._get_relevant_hip_height_from_body(), -eases["armhole_depth"]]
        )
        if spec_source.is_drop_shoulder:
            self.armpit_height -= DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[
                spec_source.drop_shoulder_additional_armhole_depth
            ]

        self.below_armhole_straight = BUSTTOARMPIT

        if spec_source.is_hourglass or spec_source.is_half_hourglass:

            if grade.armpit_to_waist is None:
                raise MissingMeasurement("armpit_to_waist")
            self.waist_height_front = sum(
                [self._get_relevant_hip_height_from_body(), -grade.armpit_to_waist]
            )
            self.waist_height_back = self.waist_height_front

        else:
            self.waist_height_front = None
            self.waist_height_back = None

        ################################################################
        # Torso measurements, broken into cases
        #
        # Note: each _inner_make_silhouette() method needs to
        # set the *final* values of:
        #
        # * self.hip_width_front
        # * self.hip_width_back
        # * self.bust_width_front
        # * self.bust_width_back
        # * self.waist_width_front
        # * self.waist_width_back
        # * self.back_cross_back_width
        #
        ################################################################

        if spec_source.is_hourglass:
            self._inner_make_hourglass(
                spec_source, grade, back_waist_shaping_only=False
            )
        elif spec_source.is_half_hourglass:
            self._inner_make_hourglass(spec_source, grade, back_waist_shaping_only=True)
        elif spec_source.is_tapered:
            self._inner_make_tapered(spec_source, grade)
        elif spec_source.is_aline:
            self._inner_make_aline(spec_source, grade)
        else:
            assert spec_source.is_straight
            self._inner_make_straight(spec_source, grade)

        ##################################################################
        # Sleeves
        ###################################################################

        if spec_source.has_sleeves():

            self.sleeve_to_armcap_start_height = (
                self._get_relevant_sleeve_length_from_body()
            )

            if spec_source.is_drop_shoulder:
                self.bicep_width = self.armhole_depth * 2
            else:
                if grade.bicep_circ is None:
                    raise MissingMeasurement("bicep_circ")
                self.bicep_width = grade.bicep_circ + eases["bicep"]

            # Always make short sleeves straight
            if any(
                [
                    spec_source.sleeve_shape == SDC.SLEEVE_STRAIGHT,
                    spec_source.sleeve_length == SDC.SLEEVE_SHORT,
                ]
            ):
                self.sleeve_cast_on_width = self.bicep_width
            elif spec_source.sleeve_shape == SDC.SLEEVE_TAPERED:
                arm_circ = self._get_relevant_arm_circ_from_body()
                self.sleeve_cast_on_width = arm_circ + eases[spec_source.sleeve_length]

            # TODO: Does anything here need to change?
            elif spec_source.sleeve_shape == SDC.SLEEVE_BELL:
                self.sleeve_cast_on_width = (
                    grade.bicep_circ + bell_eases[spec_source.bell_type]
                )
            else:
                raise ValueError(
                    "Bad value for sleeve_shape %s", spec_source.sleeve_shape
                )

        #################################################################
        # neckline
        #################################################################

        self.back_neck_depth = NECKDEPTH

        if spec_source.neckline_depth_orientation == SDC.BELOW_SHOULDERS:
            self.front_neck_depth = spec_source.neckline_depth
        elif spec_source.neckline_depth_orientation == SDC.BELOW_ARMPIT:
            self.front_neck_depth = self.sis_armhole_depth + spec_source.neckline_depth
        else:
            assert spec_source.neckline_depth_orientation == SDC.ABOVE_ARMPIT
            self.front_neck_depth = self.sis_armhole_depth - spec_source.neckline_depth

        # If the construction is *not* drop-shoulder, we compute neckhole width from
        # the actual cross-back of the garment. If it *is* drop-shoulder, we use
        # the cross-chest we *would* have gotten from a non-drop-shoulder construction
        if not spec_source.is_drop_shoulder:
            cross_back_width_for_neck = self.back_cross_back_width
        else:
            cross_back_width_for_neck = self._compute_cross_back(
                grade,
                CROSS_CHEST_EASE_FOR_DROP_SHOULDER_NECKLINE,
                UPPER_TORSO_EASE_FOR_DROP_SHOULDER_NECKLINE,
            )

        if spec_source.neckline_width == SDC.NECK_OTHERWIDTH:
            self.back_neck_opening_width = (
                cross_back_width_for_neck
                * spec_source.neckline_other_val_percentage
                / 100
            )
        else:
            self.back_neck_opening_width = (
                cross_back_width_for_neck * neck_width_ratio[spec_source.neckline_width]
            )

        ##############
        # Other
        ##############

        if grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")
        grade_bust_circ = grade.bust_circ

        ####################
        # Sanity checks
        ####################

        if all([self.waist_width_front is not None, self.hip_width_front is not None]):
            assert self.waist_width_front <= self.hip_width_front, (
                self.waist_width_front,
                self.hip_width_front,
            )

    def _inner_make_non_hourglass_helper(self, spec_source, grade):
        # The three non-hourglass shapes share a lot of initial logic,
        # so we factor it out here. _inner_make_tapered/aline/straight
        # will call this to set up everything but the hip widths (though
        # they might also change the bust-widths, too)

        #################################################################
        # Set-up
        #################################################################

        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)

        # Not hourglass, so there are no waist-widths
        self.waist_width_back = None
        self.waist_width_front = None

        if grade.waist_circ is None:
            raise MissingMeasurement("waist_circ")
        if grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")

        bust_circ = grade.bust_circ + eases["bust"]

        # Drop-shoulder special case
        if (
            (grade.upper_torso_circ is not None)
            and self.is_drop_shoulder
            and (grade.bust_circ - grade.upper_torso_circ >= BUSTY_WOMAN_THRESHOLD)
        ):
            upper_torso_circ = grade.upper_torso_circ + eases["bust"]
            self.bust_width_back = upper_torso_circ / 2.0
            if (
                upper_torso_circ
                > grade.bust_circ + DROP_SHOULDER_FRONT_BUST_THRESHOLDS[fit]
            ):
                self.bust_width_front = upper_torso_circ / 2.0
            else:
                self.bust_width_front = (
                    grade.bust_circ
                    + DROP_SHOULDER_FRONT_BUST_THRESHOLDS[fit]
                    - self.bust_width_back
                )

        else:
            # bust front and back for all other cases

            # Bust back
            if all([fit in SDC.FIT_WOMENS, grade.upper_torso_circ is not None]):
                if grade.bust_circ - grade.upper_torso_circ >= BUSTY_WOMAN_THRESHOLD:
                    upper_torso_circ = grade.upper_torso_circ + eases["upper_torso"]
                    self.bust_width_back = upper_torso_circ / 2.0
                else:
                    self.bust_width_back = bust_circ / 2.0

            else:
                self.bust_width_back = bust_circ / 2.0

            # Bust front (defaults, may be overridden in shape-specific helpers)
            if grade.waist_circ > grade.bust_circ:

                waist_circ = grade.waist_circ + eases["waist"]
                self.bust_width_front = waist_circ - self.bust_width_back

            else:
                self.bust_width_front = bust_circ - self.bust_width_back

        # cross-back width
        if self.is_drop_shoulder:
            self.back_cross_back_width = self.bust_width_back - (
                2 * MIN_ARMHOLE_WIDTH_DROP_SHOULDER
            )
        else:
            self.back_cross_back_width = self._compute_cross_back(
                grade, eases["cross_chest"], eases["upper_torso"]
            )

    def _inner_make_straight(self, spec_source, grade):

        # Developer's note: this *must* produce an IGP with
        # a straight torso shape.

        # Set-up
        self._inner_make_non_hourglass_helper(spec_source, grade)
        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)

        # For men and children's fits, we're done.
        # For women's fits, we need to make sure that the
        # grade circumference is based on the largest of:
        # bust, waist, hips
        if fit in SDC.FIT_WOMENS:
            if grade.bust_circ is None:
                raise MissingMeasurement("bust_circ")
            total_bust_circ = self.bust_width_back + self.bust_width_front
            if grade.waist_circ is None:
                raise MissingMeasurement("waist_circ")
            total_waist_circ = grade.waist_circ + eases["waist"]
            total_hip_circ = self._get_hip_circ() + eases["cast_on"]
            total_body_circ = max([total_bust_circ, total_hip_circ, total_waist_circ])

            # Now, how to split this between front and back? Depends on which
            # is the largest circumference?
            if total_bust_circ == total_body_circ:
                # Bust is the largest (or the same as the other largest), stick with the
                # logic from _inner_make_non_hourglass_helper
                pass
            elif total_hip_circ == total_body_circ:
                # Hip is the largest measurement
                self.bust_width_back = total_body_circ / 2.0
                self.bust_width_front = total_body_circ - self.bust_width_back
            # No elif needed. If waist is the largest circ, then _helper() has
            # already done the right thing.

        # And now, the part that defines this as a straight garment
        self.hip_width_front = self.bust_width_front
        self.hip_width_back = self.bust_width_back

        # TODO: remove assert after testing.
        # Test that the garment is straight on the front and back
        assert self.waist_width_back is None
        assert self.waist_width_front is None
        assert self.hip_width_front == self.bust_width_front
        assert self.hip_width_back == self.bust_width_back

    def _inner_make_tapered(self, spec_source, grade):

        # Developer's note: this *must* produce an IGP with
        # a tapered torso shape.

        self._inner_make_non_hourglass_helper(spec_source, grade)
        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)

        # We need that the bust is at least
        # MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF bigger than hips. Is it?
        # If not, increase busts
        hip_circ = self._get_hip_circ() + eases["cast_on"]
        bust_circ = sum([self.bust_width_front, self.bust_width_back])
        bust_circ_delta = bust_circ - hip_circ
        if bust_circ_delta > MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF:
            # We're good.
            pass
        else:
            # We need to increase bust so that it is larger than hips by
            # MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF
            old_bust_circ = bust_circ
            new_bust_circ = hip_circ + MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF
            # TODO: remove assert after testing
            assert new_bust_circ >= old_bust_circ
            bust_circ_growth = new_bust_circ - old_bust_circ
            self.bust_width_back += bust_circ_growth / 2.0
            self.bust_width_front += bust_circ_growth / 2.0

        # TODO: remove assert after testign
        bust_circ = sum([self.bust_width_front, self.bust_width_back])
        assert bust_circ >= hip_circ + MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF
        assert bust_circ > hip_circ

        # Hip front and hip back should be the same so long as it keeps the
        # front 'sufficiently' smaller than the bust (where 'sufficiently
        # means MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF / 2). If the
        # hip is too large, shrink it down to 'sufficiently' smaller and widen
        # the back to pick up the slack.
        self.hip_width_front = hip_circ / 2.0
        sufficiently_smaller = MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF / 2.0
        if self.hip_width_front > self.bust_width_front - sufficiently_smaller:
            self.hip_width_front = self.bust_width_front - sufficiently_smaller

        self.hip_width_back = hip_circ - self.hip_width_front

        # TODO: remove assert after testing.
        # Test that the garment is tapered on the front (sufficiently) and
        # back (at all)
        assert self.waist_width_back is None
        assert self.waist_width_front is None
        assert self.hip_width_front <= (self.bust_width_front - sufficiently_smaller)
        assert self.hip_width_back <= self.bust_width_back
        assert hip_circ == sum([self.hip_width_front, self.hip_width_back])

    def _inner_make_aline(self, spec_source, grade):

        # Developer's note: this *must* produce an IGP with
        # an a-line torso shape.

        self._inner_make_non_hourglass_helper(spec_source, grade)

        # Override _non_hourglass_helper for front busts (undoing special logic there for
        # when waist is bigger than bust)
        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)
        bust_circ = grade.bust_circ + eases["bust"]
        self.bust_width_front = bust_circ - self.bust_width_back

        # Figure out what the hip-circ should be
        eases_hip_circ = self._get_hip_circ() + eases["cast_on"]
        min_hip_circ = sum(
            [
                self.bust_width_front,
                self.bust_width_back,
                MINIMUM_ALINE_BUST_CIRC_TO_HIP_CIRC_DIFF,
            ]
        )
        hip_circ = max([eases_hip_circ, min_hip_circ])

        # Hip front and hip back should be the same so long as it keeps the
        # front 'sufficiently' larger than the bust (where 'sufficiently
        # means MINIMUM_ALINE_BUST_CIRC_TO_HIP_CIRC_DIFF / 2). If the
        # hip is too small, raise it up to 'sufficiently' larger and shrink
        # the back to pick up the slack.
        self.hip_width_front = hip_circ / 2.0
        sufficiently_larger = MINIMUM_ALINE_BUST_CIRC_TO_HIP_CIRC_DIFF / 2.0
        if self.hip_width_front < self.bust_width_front + sufficiently_larger:
            self.hip_width_front = self.bust_width_front + sufficiently_larger

        self.hip_width_back = hip_circ - self.hip_width_front

        # TODO: remove assert after testing.
        # Test that the garment is a-line on the front (sufficiently) and
        # back (at all)
        assert self.waist_width_back is None
        assert self.waist_width_front is None
        assert self.hip_width_front >= self.bust_width_front + sufficiently_larger
        assert self.hip_width_back > self.bust_width_back
        assert hip_circ == sum([self.hip_width_front, self.hip_width_back])

    def _inner_make_hourglass(self, spec_source, grade, back_waist_shaping_only=False):

        #################################################################
        # Set-up
        #################################################################

        fit = spec_source.garment_fit
        eases = get_eases(fit, spec_source.silhouette, spec_source.construction)

        #################################################################
        # Body widths / circumferences
        #################################################################

        # First, determine whether or not there need to be
        # bust-darts
        bust_darts = False
        if grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")
        if grade.upper_torso_circ is None:
            raise MissingMeasurement("upper_torso_circ")
        if grade.bust_circ - grade.upper_torso_circ > BUSTY_WOMAN_THRESHOLD:
            bust_darts = True

        # Now, determine which case we are in and get grade widths
        # accordingly

        if grade.med_hip_circ is None:
            raise MissingMeasurement("med_hip_circ")
        if grade.waist_circ is None:
            raise MissingMeasurement("waist_circ")

        hip_waist_diff = grade.med_hip_circ - grade.waist_circ
        bust_waist_diff = grade.bust_circ - grade.waist_circ
        hip_height = spec_source.torso_length
        fit = spec_source.garment_fit

        if (hip_waist_diff >= 10) and (bust_waist_diff >= 10):
            # case zero
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case0"
            )
            self.compute_widths_simple_case(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (hip_waist_diff >= 4) and (bust_waist_diff >= 10):
            assert hip_waist_diff < 10, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 1
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case1"
            )
            self.compute_widths_simple_case(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (bust_waist_diff >= 4) and (hip_waist_diff >= 10):
            assert bust_waist_diff < 10, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 2
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case2"
            )
            self.compute_widths_simple_case(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (bust_waist_diff >= 4) and (hip_waist_diff >= 4):
            assert bust_waist_diff < 10, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            assert hip_waist_diff < 10, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 3
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case3"
            )
            self.compute_widths_simple_case(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (hip_waist_diff >= 4) and (bust_waist_diff >= 0):
            assert bust_waist_diff < 4, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 4
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case4"
            )
            self.compute_widths_case_four(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (hip_waist_diff >= 1) and (bust_waist_diff >= 4):
            assert hip_waist_diff < 4, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 5
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case5"
            )
            self.compute_widths_case_five_six(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif (hip_waist_diff >= 1) and (bust_waist_diff >= 0):
            assert bust_waist_diff < 4, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            assert hip_waist_diff < 4, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 6
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case6"
            )
            self.compute_widths_case_five_six(
                bust_darts, grade, case_eases, hip_height, fit
            )
        elif hip_waist_diff >= 1:
            assert bust_waist_diff < 0, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 7
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case7"
            )
            self.compute_widths_case_seven_and_nine(
                bust_darts, grade, case_eases, hip_height, fit
            )

        elif bust_waist_diff >= 0:
            assert hip_waist_diff < 1, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 8
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case8"
            )
            self.compute_widths_case_eight(
                bust_darts, grade, case_eases, hip_height, fit
            )

        else:
            assert bust_waist_diff <= 0, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            assert hip_waist_diff <= 1, "%s, %s" % (hip_waist_diff, bust_waist_diff)
            # case 9
            case_eases = get_eases(
                fit, spec_source.silhouette, spec_source.construction, case="case9"
            )
            self.compute_widths_case_seven_and_nine(
                bust_darts, grade, case_eases, hip_height, fit
            )

        # Now we adjust front-widths and eases for the case where the spec_source
        # calls for back waist_shaping only. Note that we are not adjusting the
        # back. Very much the opposite: this spec_source choice should result in a
        # rectangle front and an unchanged back. (That is, the back one would
        # have gotten by setting self.back_waist_shaping_only to False.)

        if back_waist_shaping_only:
            max_front_width = max(
                [self.waist_width_front, self.hip_width_front, self.bust_width_front]
            )

            self.bust_width_front = max_front_width
            self.waist_width_front = max_front_width
            self.hip_width_front = max_front_width

        # Now that we know what our eases actually are,
        # we can use them to compute the heights:

        self.adjust_lengths_for_negative_ease()

        #################################################################
        # Torso measurements, wrap up.
        ##################################################################

        if self.is_drop_shoulder:
            self.back_cross_back_width = self.bust_width_back - (
                2 * MIN_ARMHOLE_WIDTH_DROP_SHOULDER
            )
        else:
            self.back_cross_back_width = self._compute_cross_back(
                grade, eases["cross_chest"], case_eases["upper_torso"]
            )

        # TODO: remove assert after testing.
        # Test that both front and back are either hourglass or straight
        assert self.waist_width_back is not None
        assert self.waist_width_back <= self.hip_width_back
        assert self.waist_width_back <= self.bust_width_back

        assert self.waist_width_front is not None
        assert self.waist_width_front <= self.hip_width_front
        assert self.waist_width_front <= self.bust_width_front

        # Test that the front and back pieces are of the right shapes:
        # both straight, both hourglass, or hourglass in the back and straight
        # in the front. That is, the only disallowed case is hourglass in front,
        # straight in back
        back_is_straight = all(
            [
                self.waist_width_back == self.hip_width_back,
                self.waist_width_back == self.bust_width_back,
            ]
        )
        front_is_straight = all(
            [
                self.waist_width_front == self.hip_width_front,
                self.waist_width_front == self.bust_width_front,
            ]
        )
        assert not all([back_is_straight, not front_is_straight])

    def compute_widths_common_logic(self, bust_darts, grade, eases, fit):

        if grade.upper_torso_circ is None:
            raise MissingMeasurement("upper_torso_circ")

        # Drop-shoulder special case
        if self.is_drop_shoulder and bust_darts:
            upper_torso_circ = grade.upper_torso_circ + eases["bust"]
            self.bust_width_back = upper_torso_circ / 2.0
            if (
                upper_torso_circ
                > grade.bust_circ + DROP_SHOULDER_FRONT_BUST_THRESHOLDS[fit]
            ):
                self.bust_width_front = upper_torso_circ / 2.0
            else:
                self.bust_width_front = (
                    grade.bust_circ
                    + DROP_SHOULDER_FRONT_BUST_THRESHOLDS[fit]
                    - self.bust_width_back
                )

        else:
            upper_torso_total = grade.upper_torso_circ + eases["upper_torso"]
            full_bust = grade.bust_circ + eases["bust"]
            if bust_darts:
                self.bust_width_back = upper_torso_total / 2
                self.bust_width_front = full_bust - self.bust_width_back
            else:
                if grade.bust_circ is None:
                    raise MissingMeasurement("bust_circ")
                self.bust_width_back = full_bust / 2
                self.bust_width_front = full_bust - self.bust_width_back

        if grade.waist_circ is None:
            raise MissingMeasurement("waist_circ")
        waist_circ = grade.waist_circ + eases["waist"]
        self.waist_width_back = min(waist_circ / 2, self.bust_width_back - 1)
        self.waist_width_front = waist_circ - self.waist_width_back

    def compute_widths_simple_case(self, bust_darts, grade, eases, hip_height, fit):
        self.compute_widths_common_logic(bust_darts, grade, eases, fit)

        body_hip_circ = self._get_hip_circ()
        hips_total = body_hip_circ + eases[hip_height]
        self.hip_width_back = max(
            (hips_total / 2), self.waist_width_back + FORCED_SHAPING_BACK_HIP
        )
        self.hip_width_front = max((hips_total / 2), self.waist_width_front)

        self.bust_width_front = max(self.bust_width_front, self.waist_width_front)

    def compute_widths_case_four(self, bust_darts, grade, eases, hip_height, fit):

        # The only thing we're going to keep from this next call
        # are the upper-torso measurements and back bust
        self.compute_widths_common_logic(bust_darts, grade, eases, fit)

        if grade.bust_circ is None:
            raise MissingMeasurement("bust_circ")
        if grade.waist_circ is None:
            raise MissingMeasurement("waist_circ")

        # First, set the bust and waist circumferences
        ideal_full_bust = self.bust_width_front + self.bust_width_back
        full_waist = grade.waist_circ + eases["waist"]

        if ideal_full_bust < full_waist:
            full_bust = full_waist
        else:
            full_bust = ideal_full_bust

        # Now, set the back waist

        bust_waist_delta = full_bust - full_waist
        logger.debug(bust_waist_delta)
        if bust_waist_delta >= 1:
            self.waist_width_back = self.bust_width_back - 1
        elif bust_waist_delta <= 0:
            self.waist_width_back = self.bust_width_back
        else:
            self.waist_width_back = self.bust_width_back - bust_waist_delta

        # waist- and bust-fronts
        self.waist_width_front = full_waist - self.waist_width_back
        self.bust_width_front = full_bust - self.bust_width_back

        # hips
        body_hip_circ = self._get_hip_circ()
        hips_total = body_hip_circ + eases[hip_height]
        self.hip_width_back = max(
            (hips_total / 2), self.waist_width_back + FORCED_SHAPING_BACK_HIP
        )
        self.hip_width_front = max((hips_total / 2), self.waist_width_front)

    def compute_widths_case_five_six(self, bust_darts, grade, eases, hip_height, fit):
        self.compute_widths_common_logic(bust_darts, grade, eases, fit)

        # Differences from simple-case start here
        body_hip_circ = self._get_hip_circ()
        hips_total = body_hip_circ + eases[hip_height]
        self.hip_width_back = max(
            (hips_total / 2), self.waist_width_back + FORCED_SHAPING_BACK_HIP
        )
        self.hip_width_front = max((hips_total / 2), self.waist_width_front)

        self.bust_width_front = max(self.bust_width_front, self.waist_width_front)

    def compute_widths_case_eight(self, bust_darts, grade, eases, hip_height, fit):
        self.compute_widths_common_logic(bust_darts, grade, eases, fit)

        assert eases[hip_height] >= 0
        self.hip_width_back = self.waist_width_back + eases[hip_height]
        self.hip_width_front = self.waist_width_front

        self.bust_width_front = max(self.bust_width_front, self.waist_width_front)

    def compute_widths_case_seven_and_nine(
        self, bust_darts, grade, eases, hip_height, fit
    ):
        self.compute_widths_common_logic(bust_darts, grade, eases, fit)

        self.waist_width_front = self.bust_width_front
        self.waist_width_back = self.bust_width_back

        if grade.waist_circ is None:
            raise MissingMeasurement("waist_circ")
        total_waist = grade.waist_circ + eases["waist"]
        total_hips = self._get_hip_circ() + eases[hip_height]
        max_hip_and_waist = max(total_hips, total_waist)
        self.hip_width_front = max(max_hip_and_waist / 2, self.waist_width_front)
        self.hip_width_back = max(
            max_hip_and_waist - self.hip_width_front, self.waist_width_back
        )

        # Now, move the waist-line up to bust, essentially
        self.waist_height_front = self.armpit_height - sum(
            [self.below_armhole_straight, ALINE_WAIST_TO_BUST]
        )
        self.waist_height_back = self.waist_height_front

    ############################################################################
    #
    # make() helpers
    #
    ############################################################################

    def _get_relevant_grade_attr(self, attr_dict, dc_value):
        grade = self.grade
        attr_name = attr_dict[dc_value]
        return_me = getattr(grade, attr_name)
        if return_me is None:
            raise MissingMeasurement(attr_name)
        else:
            return return_me

    def _get_relevant_hip_height_from_body(self):
        """
        Get the hip-height (in inches) relevant to this IGP by fetching
        the value from the Body associated with the hip-height of the
        PatternSpec. Will raise MissingMeasurement if the Body does not have
        a value at that hip-height
        """
        pattern_spec = self.get_spec_source()
        return self._get_relevant_grade_attr(
            self.hip_length_dict, pattern_spec.torso_length
        )

    def _get_relevant_sleeve_length_from_body(self):
        """
        Get the sleeve-length (in inches) relevant to this IGP by fetching
        the value from the Body associated with the sleeve-length of the
        PatternSpec. Will raise MissingMeasurement if the Body does not have
        a value at that sleeve-length
        """
        pattern_spec = self.get_spec_source()
        return self._get_relevant_grade_attr(
            self.sleeve_length_dict, pattern_spec.sleeve_length
        )

    def _get_relevant_arm_circ_from_body(self):
        """
        Get the arm-circ (in inches) relevant to this IGP by fetching
        the value from the Body associated with the sleeve-circ of the
        PatternSpec. Will raise MissingMeasurement if the Body does not have
        a value at that arm-circ
        """

        # Broken out into its own method so that it can be used in both
        # _get_relevant_sleeve_circ_from_body and sleeve_ease
        pattern_spec = self.get_spec_source()
        return self._get_relevant_grade_attr(
            self.arm_circ_dict, pattern_spec.sleeve_length
        )

    def _get_hip_circ(self):
        """
        Extracts the 'correct' cast-on circumference (in inches) from the underlying body.
        Note that this may not be the circumference at the cast-on length (high-hip,
        medium-hip, low-hip, or tunic). Instead, we look at the circumference of the cast-on
        length and all higher lengths. The circumference at the cast-on length is required,
        but all higher lengths are optional. We then return the largest circumference that
        we have. So if the pattern_spec is at low-hip, for example, it will be the largest
        non-None value of low, medium and high hip.
        """

        pattern_spec = self.get_spec_source()

        # Sanity check that we have at least the circ-value for this length
        # and raise MissingMeasurement if we do not
        _ = self._get_relevant_grade_attr(self.hip_circ_dict, pattern_spec.torso_length)

        all_circs = [
            self.grade.high_hip_circ,
            self.grade.med_hip_circ,
            self.grade.low_hip_circ,
            self.grade.tunic_circ,
        ]

        if pattern_spec.torso_length == SDC.HIGH_HIP_LENGTH:
            circs = all_circs[:1]
        elif pattern_spec.torso_length == SDC.MED_HIP_LENGTH:
            circs = all_circs[:2]
        elif pattern_spec.torso_length == SDC.LOW_HIP_LENGTH:
            circs = all_circs[:3]
        else:
            assert pattern_spec.torso_length == SDC.TUNIC_LENGTH
            circs = all_circs

        non_none_circs = [x for x in circs if x is not None]
        return max(non_none_circs)

    def _compute_cross_back(self, body, cross_chest_ease, upper_torso_ease):
        """
        Compute and return the cross-back-width based on the body and selected
        eases. Note that this has no side effects. In particular, it returns
        the cross-chest value instead of setting the cross_back_width attribute.
        """
        # Developer's note: why not replace the cross-chest ease and
        # upper-torso ease with the 'eases' dictionary we're carrying around
        # anyway? Because we use this method in two different places, and the
        # structure of the `ease` dictionary depends on which location we're in.
        # So it turns out to be clearer to force the client code to find the
        # ease values we want here for us.

        if body.cross_chest_distance is not None:
            return_me = self.grade.cross_chest_distance + cross_chest_ease
        else:
            if body.upper_torso_circ is not None:
                body_circ = body.upper_torso_circ
            else:
                if self.grade.bust_circ is None:
                    raise MissingMeasurement("bust_circ")
                body_circ = body.bust_circ
            upper_torso_total = body_circ + upper_torso_ease

            if body.body_type == Body.BODY_TYPE_ADULT_MAN:
                table = mens_cross_chest_table
            elif body.body_type == Body.BODY_TYPE_CHILD:
                table = childrens_cross_chest_table
            else:
                # UNSTATED body-types are to be treated like WOMAN body-types
                # for the purpose of cross-chests
                table = womens_cross_chest_table

            try:
                return_me = table[math.ceil(upper_torso_total)]
            except KeyError as ex:
                raise ValueError(
                    f"The upper torso total {upper_torso_total} is not in the cross-chest table"
                ) from ex

        necessary_armhole_width = 2 * (
            MIN_ARMHOLE_WIDTH_DROP_SHOULDER
            if self.is_drop_shoulder
            else MIN_ARMHOLE_WIDTH_SET_IN_SLEEVE
        )

        max_value = self.bust_width_back - necessary_armhole_width
        if return_me > max_value:
            return_me = max_value

        return return_me

    ############################################################################
    #
    # Shape helpers. Used in clean() both here and in schematics
    #
    ############################################################################

    def front_is_straight(self):
        if self.hip_width_front != self.bust_width_front:
            return False
        elif self.waist_width_front is not None:
            if any(
                [
                    self.waist_width_front != self.hip_width_front,
                    self.waist_width_front != self.bust_width_front,
                ]
            ):
                return False
        return True

    def back_is_straight(self):
        if self.hip_width_back != self.bust_width_back:
            return False
        elif self.waist_width_back is not None:
            if any(
                [
                    self.waist_width_back != self.hip_width_back,
                    self.waist_width_back != self.bust_width_back,
                ]
            ):
                return False
        return True

    def front_is_hourglass(self):
        return all([self.waist_width_front is not None, not self.front_is_straight()])

    def back_is_hourglass(self):
        return all([self.waist_width_back is not None, not self.back_is_straight()])

    def front_is_aline(self):
        return all(
            [
                self.waist_height_front is None,
                self.bust_width_front < self.hip_width_front,
            ]
        )

    def back_is_aline(self):
        return all(
            [self.waist_height_back is None, self.bust_width_back < self.hip_width_back]
        )

    def front_is_tapered(self):
        return all(
            [
                self.waist_height_front is None,
                self.bust_width_front > self.hip_width_front,
            ]
        )

    def back_is_tapered(self):
        return all(
            [
                self.waist_height_front is None,
                self.bust_width_back > self.hip_width_back,
            ]
        )

    def has_sleeves(self):
        spec_source = self.get_spec_source()
        return spec_source.has_sleeves()

    @property
    def construction(self):
        spec_source = self.get_spec_source()
        return spec_source.construction

    @property
    def is_set_in_sleeve(self):
        spec_source = self.get_spec_source()
        return spec_source.is_set_in_sleeve

    @property
    def is_drop_shoulder(self):
        spec_source = self.get_spec_source()
        return spec_source.is_drop_shoulder

    ############################################################################
    #
    # clean(), etc.
    #
    ############################################################################

    # Break out some helper methods to keep clean() itself relatively readable.
    def _clean_straight(self):
        errors = []
        if not self.back_is_straight():
            errors.append(
                ValidationError(
                    "Back piece must be straight, but is not. "
                    "All back widths must be the same; please adjust them "
                    "accordingly."
                )
            )
        if not self.front_is_straight():
            errors.append(
                ValidationError(
                    "Front piece must be straight, but is not. "
                    "All front widths must be the same; please adjust them "
                    "accordingly."
                )
            )
        return errors

    def _clean_hourglass_common(self):
        errors = []

        # Back must be straight or hourglass
        if not self.back_is_straight():
            # back must be hourglass
            if self.waist_width_back is None:
                errors.append(ValidationError("Back waist-width must not be blank"))
            if self.waist_height_back is None:
                errors.append(ValidationError("Back waist-height must not be blank"))
            if self.waist_width_back > self.hip_width_back:
                errors.append(
                    ValidationError("Back waist must not be larger than " "back hips")
                )
            if self.waist_width_back > self.bust_width_back:
                errors.append(
                    ValidationError("Back waist must not be larger than " "back bust")
                )

        # If back is straight, then front must be straight too.
        # (All other combinations are allowed.)

        if all([self.back_is_straight(), not self.front_is_straight()]):
            errors.append(
                ValidationError("Back cannot be straight unless " "front is as well.")
            )

        # Test that the neckline stays above the waist
        if self.waist_height_front is not None:
            if self.front_neck_depth >= sum(
                [self.armpit_height, self.armhole_depth - self.waist_height_front]
            ):
                errors.append(
                    ValidationError(
                        "Front-neck depth must not go below front-waist height"
                    )
                )

        return errors

    def _clean_half_hourglass(self):
        validation_errors = self._clean_hourglass_common()

        # If this is derived for a half-hourglass silhouette, then it
        # must be the case that all front-widths are the same.
        if not all(
            [
                self.waist_width_front == self.hip_width_front,
                self.hip_width_front == self.bust_width_front,
            ]
        ):
            validation_errors.append(
                ValidationError(
                    "This silhouette has shaping on the back only. Therefore, all "
                    "front widths (hip, waist, and bust) must be the same. "
                    "Please adjust them accordingly."
                )
            )

        return validation_errors

    def _clean_hourglass(self):
        errors = self._clean_hourglass_common()

        # Front must be straight or hourglass for an hourglass design.
        if not self.front_is_straight():
            # Front must be hourglass.
            if self.waist_width_front is None:
                errors.append(ValidationError("Front waist-width must not be blank"))
            if self.waist_height_front is None:
                errors.append(ValidationError("Front waist-height must not be blank"))
            if self.waist_width_front > self.hip_width_front:
                errors.append(
                    ValidationError("Front waist must not be larger than " "front hips")
                )
            if self.waist_width_front > self.bust_width_front:
                errors.append(
                    ValidationError("Front waist must not be larger than " "front bust")
                )

        return errors

    def _clean_aline(self):
        errors = []

        # Back and front must both be straight or both be a-line.
        if not all([self.front_is_straight(), self.back_is_straight()]):
            # Both must be a-line.

            # Test that front is A-line.
            if self.waist_width_front is not None:
                errors.append(
                    ValidationError("Front waist-width must be blank for A-line shapes")
                )
            if self.waist_height_front is not None:
                errors.append(
                    ValidationError(
                        "Front waist-height must be blank for A-line shapes"
                    )
                )

            if self.bust_width_front >= self.hip_width_front:
                errors.append(
                    ValidationError(
                        "Front bust-width must be less than front hip-width"
                    )
                )

            # Test that back is A-line.
            if self.waist_width_back is not None:
                errors.append(
                    ValidationError("Back waist-width must be blank for A-line shapes")
                )
            if self.waist_height_back is not None:
                errors.append(
                    ValidationError("Back waist-height must be blank for A-line shapes")
                )

            if self.bust_width_back >= self.hip_width_back:
                errors.append(
                    ValidationError("Back bust-width must be less than back hip-width")
                )

        return errors

    def _clean_tapered(self):
        errors = []

        if self.waist_width_front is not None:
            errors.append(
                ValidationError("Front waist-width must be blank for tapered shapes")
            )
        if self.waist_height_front is not None:
            errors.append(
                ValidationError("Front waist-height must be blank for tapered shapes")
            )
        if self.waist_width_back is not None:
            errors.append(
                ValidationError("Back waist-width must be blank for tapered shapes")
            )
        if self.waist_height_back is not None:
            errors.append(
                ValidationError("Back waist-height must be blank for tapered shapes")
            )

        # Neither back nor front can be aline, and front cannot be straight while back is tapered.
        if self.front_is_aline():
            errors.append(
                ValidationError("Front cannot be a-line for tapered garments")
            )
        if self.back_is_aline():
            errors.append(ValidationError("Back cannot be a-line for tapered garments"))

        if not (self.front_is_aline() or self.back_is_aline()):
            # Only bad combination is straight front and tapered back
            if self.front_is_straight() and self.back_is_tapered():
                errors.append(
                    ValidationError(
                        "Cannot have straight-front and tapered-back for tapered garments"
                    )
                )

        return errors

    def clean(self):

        super(_SweaterGarmentDimensions, self).clean()

        # Validate that the Body and PatternSpec are valid *together*.
        # This section should contain only tests that compare values from Body
        # to values from PatternSpec, and raise IncompatibleDesignInputs.
        # ----------------------------------------------------------------------
        grade = self.grade

        spec_source = self.get_spec_source()

        compatibility_errors = []

        # Make sure the hip length is sufficient to accommodate edging (seldom
        # a problem, but users could in theory ask for two feet of edging!)
        if self.waist_height_front:
            room_for_hip_edge = min([self.waist_height_front, self.waist_width_back])
        else:
            room_for_hip_edge = self.armpit_height

        if room_for_hip_edge < spec_source.hip_edging_height:
            room = length_fmt(room_for_hip_edge)
            edging = length_fmt(spec_source.hip_edging_height)
            error_msg = (
                "Sorry, but the hip edging is extending past "
                "the waist. Try a hip-edging height less than "
                "%s, or use a measurement set with a waist height "
                "greater than %s." % (room, edging)
            )
            compatibility_errors.append(error_msg)

        # Make sure that the neckline-depth is positive.
        if spec_source.neckline_depth_orientation == SDC.ABOVE_ARMPIT:
            eases = get_eases(
                spec_source.garment_fit,
                spec_source.silhouette,
                spec_source.construction,
            )
            armpit_ease = eases["armhole_depth"]

            if grade.armhole_depth is None:
                raise MissingMeasurement("armhole_depth")
            armpit_depth = grade.armhole_depth + armpit_ease
            if spec_source.neckline_depth > armpit_depth:
                error_msg = (
                    "Sorry, but those neckline settings actually put "
                    "the neckline above the shoulders. Did you really want your "
                    "neckline to start %s above the armhole?"
                    % length_fmt(spec_source.neckline_depth)
                )
                compatibility_errors.append(error_msg)

        if compatibility_errors:
            raise self.IncompatibleDesignInputs(*compatibility_errors)

        # Validate values generated during IGP make.
        # This section should test only aspects of IGP, and raise
        # ValidationErrors.
        # ----------------------------------------------------------------------

        validation_errors = []

        if spec_source.has_sleeves():

            if self.sleeve_to_armcap_start_height is None:
                validation_errors.append(ValidationError("Sleeve total-height needed"))

            if all(
                [
                    self.bicep_width is None,
                    spec_source.sleeve_length != SDC.SLEEVE_SHORT,
                    not spec_source.is_drop_shoulder,
                ]
            ):
                validation_errors.append(ValidationError("Bicep-width needed"))

            if self.sleeve_cast_on_width is None:
                validation_errors.append(ValidationError("Sleeve cast-on width needed"))

        if self.button_band_allowance is not None:
            if self.button_band_allowance > self.front_neck_opening_width:
                validation_errors.append(
                    ValidationError(
                        "Button-band allowance is bigger than " "front-neck wdith"
                    )
                )

        necessary_armhole_width = 2 * (
            MIN_ARMHOLE_WIDTH_DROP_SHOULDER
            if self.is_drop_shoulder
            else MIN_ARMHOLE_WIDTH_SET_IN_SLEEVE
        )
        actual_amrhole_widths = self.bust_width_back - self.back_cross_back_width
        if necessary_armhole_width > actual_amrhole_widths:
            validation_errors.append(
                ValidationError(
                    "Need to leave %s inches for armhole-shaping (currently leaving %s)"
                    % (necessary_armhole_width, actual_amrhole_widths)
                )
            )

        # Test that tweaking respected the silhouette of the spec_source.
        # ----------------------------------------------------------------------

        if spec_source.is_straight:
            silhouette_errors = self._clean_straight()

        elif spec_source.is_hourglass:
            silhouette_errors = self._clean_hourglass()

        elif spec_source.is_half_hourglass:
            silhouette_errors = self._clean_half_hourglass()

        elif spec_source.is_aline:
            silhouette_errors = self._clean_aline()

        else:
            assert spec_source.is_tapered
            silhouette_errors = self._clean_tapered()

        validation_errors += silhouette_errors

        if validation_errors:
            raise ValidationError(validation_errors)

    class Meta:
        abstract = True


# This next line contains a magic string created by Django-polymorphic to hold the
# pointer from the SweaterIndividualGarmentParameters table to the IndividualGarmentParameters
# table. This magic string can be manually overwritten (see the Django docs on multi-table
# inheritance) so don't do that.
@reversion.register(follow=["individualgarmentparameters_ptr"])
class SweaterIndividualGarmentParameters(
    IndividualGarmentParameters,
    _SweaterGarmentParametersTopLevel,
    _SweaterGarmentDimensions,
):

    @classmethod
    def missing_body_fields(cls, patternspec):
        return cls._inner_missing_body_fields(patternspec, patternspec.body)

    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        from ..models import SweaterPatternSpec

        assert isinstance(pattern_spec, SweaterPatternSpec)

        igp = cls()

        igp.pattern_spec = pattern_spec
        igp.redo = None
        igp.user = pattern_spec.user
        igp.set_garment_dimensions(pattern_spec, pattern_spec.body)

        igp.full_clean()
        igp.save()
        return igp

    @classmethod
    def make_from_redo(cls, user, redo):
        from ..models import SweaterRedo

        assert isinstance(redo, SweaterRedo)

        igp = cls()

        igp.pattern_spec = None
        igp.redo = redo
        igp.user = redo.user

        igp.set_garment_dimensions(redo, redo.body)

        igp.full_clean()
        igp.save()
        return igp

    @property
    def grade(self):
        spec_source = self.get_spec_source()
        body = spec_source.body
        return body

    @property
    def body(self):
        return self.grade

    def get_spec_source(self):
        assert (self.pattern_spec is not None) or (self.redo is not None)
        source = self.pattern_spec if self.pattern_spec else self.redo
        return source


@reversion.register(follow=["gradedgarmentparametersgrade_ptr"])
class SweaterGradedGarmentParametersGrade(
    GradedGarmentParametersGrade, _SweaterGarmentDimensions
):

    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)

    @classmethod
    def missing_body_fields(cls, patternspec, grade):
        return cls._inner_missing_body_fields(patternspec, grade)

    def get_spec_source(self):
        return self.graded_garment_parameters.get_spec_source()


@reversion.register(follow=["gradedgarmentparameters_ptr"])
class SweaterGradedGarmentParameters(
    GradedGarmentParameters, _SweaterGarmentParametersTopLevel
):

    @classmethod
    def missing_body_fields(cls, patternspec):

        missing_field_set = set()

        for grade in patternspec.all_grades():
            missing_fields = SweaterGradedGarmentParametersGrade.missing_body_fields(
                patternspec, grade
            )
            if missing_fields:
                missing_field_set.update(missing_fields)

        return missing_field_set

    def get_spec_source(self):
        return self.pattern_spec

    # required by superclass
    @classmethod
    def make_from_patternspec(cls, user, pattern_spec):
        from ..models import GradedSweaterPatternSpec

        assert isinstance(pattern_spec, GradedSweaterPatternSpec)

        gpg = cls()

        gpg.pattern_spec = pattern_spec
        gpg.user = pattern_spec.user
        gpg.full_clean()
        gpg.save()
        for grade in pattern_spec.all_grades():
            igp_grade = SweaterGradedGarmentParametersGrade()
            igp_grade.graded_garment_parameters = (
                gpg  # must come before set_garment_dimensions
            )
            igp_grade.grade = grade  # must come before set_garment_dimensions
            igp_grade.set_garment_dimensions(pattern_spec, grade)
            igp_grade.full_clean()
            igp_grade.save()
        return gpg

    def get_schematic_class(self):
        from .schematics import GradedSweaterSchematic

        return GradedSweaterSchematic
