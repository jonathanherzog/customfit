# -*- coding: utf-8 -*-
import collections
import copy
import itertools
import logging
import urllib.parse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.safestring import mark_safe

from customfit.designs.models import (
    AdditionalDesignElement,
    Design,
    ExtraFinishingTemplate,
)
from customfit.fields import (
    LengthField,
    LengthOffsetField,
    NonNegFloatField,
    NonNegSmallIntegerField,
)
from customfit.helpers.math_helpers import CompoundResult, round
from customfit.stitches import models as stitches

from ..helpers import sweater_design_choices as SDC

logger = logging.getLogger(__name__)


class AdditionalSleeveElement(AdditionalDesignElement):
    # For sleeves, additional-element can start:
    # * X inches after cast-ons (non-negative) or
    # * X inches before the cap-shaping starts (non-negative)

    start_location_value = NonNegFloatField(help_text="Can be zero, but not negative.")

    START_AFTER_CASTON = "start_after_caston"
    START_BEFORE_CAP = "start_before_cap"
    START_TYPE_CHOICES = [
        (START_AFTER_CASTON, "inches after castons"),
        (START_BEFORE_CAP, "inches before cap-shaping start"),
    ]
    start_location_type = models.CharField(max_length=20, choices=START_TYPE_CHOICES)

    def start_rows(self, armcap_heights_in_inches, gauge):
        if self.start_location_type == self.START_AFTER_CASTON:
            start_heights = CompoundResult(
                itertools.repeat(
                    self.start_location_value, len(armcap_heights_in_inches)
                )
            )
        else:
            assert self.start_location_type == self.START_BEFORE_CAP
            start_heights = armcap_heights_in_inches - self.start_location_value

        def helper(start_height_val):
            # Additional elements should always start on RS row, so start row should be odd
            start_row_float = start_height_val * gauge.rows
            start_row = round(start_row_float, multiple=2, mod=1)

            # And if they end up being below the sleeve start, then (unlike body pieces)
            # we just shift them up to the start.
            if start_row < 1:
                return 1
            else:
                return int(start_row)

        row_vals = [helper(x) for x in start_heights]
        return CompoundResult(row_vals)


class AdditionalBodyPieceElement(AdditionalDesignElement):
    # Abstract base model for front, back, and full-torso (front and back, matching) elements

    start_location_value = models.FloatField(
        help_text="Must be non-negative for 'above cast-on' and 'below-shoulders' start locations"
    )

    START_AFTER_CASTON = "start_after_caston"
    START_BEFORE_ARMHOLE = "start_before_armhole"
    START_BEFORE_NECKLINE = "start_before_neckline"
    START_BEFORE_SHOULDERS = "start_before_shoulders"
    START_TYPE_CHOICES = [
        (START_AFTER_CASTON, "inches after cast-on"),
        (START_BEFORE_ARMHOLE, "inches before armhole-shaping"),
        (START_BEFORE_NECKLINE, "inches before neckline"),
        (START_BEFORE_SHOULDERS, "inches before shoulder-shaping"),
    ]
    start_location_type = models.CharField(max_length=25, choices=START_TYPE_CHOICES)

    Measurements = collections.namedtuple(
        "Measurements", ["armhole_heights", "neckline_heights", "shoulder_heights"]
    )

    class ElementBelowStartException(Exception):
        pass

    def start_rows(
        self,
        gauge,
        front_armhole_heights,
        front_neckline_heights,
        front_shoulder_heights,
        back_armhole_heights,
        back_neckline_heights,
        back_shoulder_heights,
    ):
        # Note: it is important that, when this is a method of AdditionalFullTorsoElement,
        # it returns the same value for both front pieces and back pieces. To that end, we
        # make this a thin wrapper around an abstract method that picks out the right arguments:
        fronts = self.Measurements(
            front_armhole_heights, front_neckline_heights, front_shoulder_heights
        )
        backs = self.Measurements(
            back_armhole_heights, back_neckline_heights, back_shoulder_heights
        )
        start_heights = self._get_start_heights(fronts, backs)

        # Additional elements should always start on RS row, so start row should be odd
        # Always round up. (In part, becuase this makes a 'start 0 inches after caston' int
        # 'start at row 1, which is right.)
        start_row_floats = start_heights * gauge.rows
        start_row = start_row_floats.map(lambda x: round(x, multiple=2, mod=1))

        # If they end up being below the start, then we throw an exception (unlike Sleeves)
        if start_row.any(lambda x: x < 1):
            raise self.ElementBelowStartException("Start row: %s" % start_row)
        else:
            return start_row.map(int)

    def _get_start_heights(self, fronts, backs):
        # This is an abstract method that needs to be shadowed by subclasses
        raise NotImplementedError

    def _inner_get_start_heights(self, measurements):
        # A helper function to be used in subclasses' definitions of _get_start_height
        heights = {
            self.START_AFTER_CASTON: CompoundResult(
                itertools.repeat(
                    self.start_location_value, len(measurements.armhole_heights)
                )
            ),
            self.START_BEFORE_ARMHOLE: measurements.armhole_heights
            - self.start_location_value,
            self.START_BEFORE_NECKLINE: measurements.neckline_heights
            - self.start_location_value,
            self.START_BEFORE_SHOULDERS: measurements.shoulder_heights
            - self.start_location_value,
        }
        return_me = heights[self.start_location_type]
        return return_me

    def clean(self):
        super(AdditionalBodyPieceElement, self).clean()
        # If the start is 'above caston' or 'below armhole' negative values are not allowed
        if self.start_location_value < 0:
            if self.start_location_type in [
                self.START_AFTER_CASTON,
                self.START_BEFORE_SHOULDERS,
            ]:
                if self.start_location_type == self.START_AFTER_CASTON:
                    error_msg = "'after caston' starts cannot be negative"
                else:
                    error_msg = "'before shoulder shaping' starts cannot be negative"
                raise ValidationError({"start_location_value": error_msg})

    class Meta:
        abstract = True


class AdditionalFrontElement(AdditionalBodyPieceElement):

    def _get_start_heights(self, fronts, backs):
        return self._inner_get_start_heights(fronts)


class AdditionalBackElement(AdditionalBodyPieceElement):

    def _get_start_heights(self, fronts, backs):
        return self._inner_get_start_heights(backs)


class AdditionalFullTorsoElement(AdditionalBodyPieceElement):

    def _get_start_heights(self, fronts, backs):
        return self._inner_get_start_heights(fronts)


###################################################################################
#
# Design-relevant fields
#
# (Factored out so they can be used in both PatternSpec and pattern.RedoRedo in a DRY
# fashion that keeps the models in sync)
#
###################################################################################


class TorsoLengthField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 15
        kwargs["choices"] = SDC.HIP_LENGTH_CHOICES
        super(TorsoLengthField, self).__init__(*args, **kwargs)


class SleeveLengthField(models.CharField):

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 20
        kwargs["choices"] = SDC.SLEEVE_LENGTH_CHOICES
        kwargs["null"] = True
        kwargs["blank"] = True
        super(SleeveLengthField, self).__init__(*args, **kwargs)


class NecklineDepthField(LengthField):
    pass


class NecklineDepthOrientationField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 15
        kwargs["choices"] = SDC.NECKLINE_DEPTH_ORIENTATION_CHOICES
        kwargs["default"] = SDC.BELOW_SHOULDERS
        super(NecklineDepthOrientationField, self).__init__(*args, **kwargs)


class SweaterDesignBase(models.Model):
    """
    Base-class for design-like models.
    """

    # Currently, the list of design-like models (subclasses of DesignBase) is
    # just designs.Design and patternspec.PatternSpec. The idea is that
    # Design represents the work of a designer, while PatternSpec is the set
    # of values specifying one particular pattern to be created by the
    # engine. PatternSpec instances can be made directly (through the
    # custom-design form) or they can be derived from a source Design. And in
    #  the latter case, many *but not all* common fields will be copied from
    # the Design into the PatternSpec. Why? Why copy fields into PatternSpec
    # instead of use using the values in the original Design? Two reasons:
    #
    # 1) The user may want to change some of the values in the Design (e.g.,
    # torso length, sleeve length) when they 'personalize' the design, and
    #
    # 2) The designer or an admin may change values in the Design, and it may
    #  be that the change should not propagate to all derived patterns.
    # Therefore, the PatternSpec will have its own copy of that field which
    # is not changed just because the corresponding value changed in the
    # Design.
    #
    # So where should a particular field go? It depends:
    #
    # * Does it only make sense for Designs and not Patterns? (Example:
    # WooCommerce URL.) Then it does in Design.
    #
    # * Does it only make sense for PatternSpecs and not Designs? (Example:
    # body.) Then it goes in PatternSpec.
    #
    # * It makes sense for both models, but the user may want to change it
    # when personalizing? (Example: name.) Then it goes in DesignBase.
    #
    # * It makes sense for both models and the user won't want to change it.
    # But suppose that we change that value in the Design instance. Should
    # that change propagate out to all Patterns derived from that design?
    #
    #   * Yes? (Example: templates, in that we sometimes need to debug or
    #     extend them.) It goes in Design.
    #
    #   * No? (Example: edging heights.) It goes in DesignBase.
    #

    garment_type = models.CharField(max_length=20, choices=SDC.GARMENT_TYPE_CHOICES)

    sleeve_length = SleeveLengthField()

    sleeve_shape = models.CharField(
        max_length=16, choices=SDC.SLEEVE_SHAPE_CHOICES, null=True, blank=True
    )

    bell_type = models.CharField(
        max_length=15,
        choices=SDC.BELL_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="A slight bell is slightly wider at cast-on; "
        'a moderate bell is an "average" bell shape; '
        "an extreme bell is substantially wider at cast on. "
        "Extreme bells should only be used with three-quarter "
        "and long sleeves.",
    )

    drop_shoulder_additional_armhole_depth = models.CharField(
        blank=True,
        null=True,
        max_length=15,
        choices=SDC.DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES,  # Note-- excludes 'none' depth
        help_text="Amount to extend armhole_depth when the construction is drop-shoulder.",
    )

    neckline_style = models.CharField(max_length=16, choices=SDC.NECKLINE_STYLE_CHOICES)

    torso_length = TorsoLengthField()

    neckline_width = models.CharField(
        max_length=16,
        choices=SDC.NECKLINE_WIDTH_CHOICES,
        help_text=mark_safe(
            "How wide your neckline will be, <b>not including "
            "any edging</b>. Narrow necklines will be close "
            "to your neck; average necklines are suitable for "
            "most cases; wide necklines will be further out "
            "on your shoulders. Since CustomFit is producing "
            "your sweater pattern based on your body, "
            "even wide necklines will never fall off your "
            "shoulders. "
        ),
    )

    neckline_other_val_percentage = models.FloatField(
        help_text="Should be between 0 and 100",
        null=True,
        blank=True,
        validators=[MaxValueValidator(100), MinValueValidator(0)],
    )

    neckline_depth = NecklineDepthField(
        help_text=mark_safe(
            "How deep would you like your neckline? You'll have "
            "3 choices for orienting this depth: below the shoulders, "
            "above the armhole shaping, and below the armhole shaping.<br />"
            "<img src='"
            + urllib.parse.urljoin(settings.STATIC_URL, "img/neck-depth-help.png")
            + "' width='150px'>"
            "<br /> Customfit will make this measurement deeper if it can't fit "
            "the decreases needed to make the selected neckline shape and width."
        )
    )

    neckline_depth_orientation = NecklineDepthOrientationField(
        help_text=mark_safe(
            "Typically, it's easier to input shallower "
            "necklines in terms of the distance from neck shaping "
            "start to shoulders. For deeper necklines, either "
            "inputting the distance above the armhole shaping, or "
            "even below the armhole shaping, often makes more sense. "
            '<a href="'
            + urllib.parse.urljoin(settings.STATIC_URL, "img/neck-depth-help.png")
            + '" target="_blank">See this picture for help!</a>'
        )
    )

    #
    # all-over stitches
    #

    back_allover_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_allover_stitch": True},
        related_name="%(app_label)s_back_allover_stitch_%(class)s",
        help_text="All-over stitch for back piece",
        on_delete=models.CASCADE,
    )

    front_allover_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_allover_stitch": True},
        related_name="%(app_label)s_front_allover_stitch_designs_%(class)s",
        on_delete=models.CASCADE,
        help_text="All-over stitch for front piece or pieces",
    )

    sleeve_allover_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_allover_stitch": True},
        related_name="%(app_label)s_sleeve_allover_stitch_designs_%(class)s",
        help_text="All-over stitch for sleeve. (Ignored for vests.)",
        on_delete=models.CASCADE,
    )

    #
    # edging fields
    #

    hip_edging_stitch = models.ForeignKey(
        stitches.Stitch,
        related_name="%(app_label)s_hip_edging_stitch_designs_%(class)s",
        limit_choices_to={"is_waist_hem_stitch": True},
        help_text="What stitch you'd like to trim the hem of your sweater.",
        on_delete=models.CASCADE,
    )

    hip_edging_height = LengthField(
        help_text="How high you'd like the trim stitch pattern to be. "
        "Typically, waist shaping will not overlap this trim."
    )

    sleeve_edging_stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        related_name="%(app_label)s_sleeve_edging_stitch_designs_%(class)s",
        limit_choices_to={"is_sleeve_hem_stitch": True},
        help_text="The stitch pattern you'd like trimming the cast on edge of your sleeve.",
        on_delete=models.CASCADE,
    )

    sleeve_edging_height = LengthField(
        null=True,
        blank=True,
        help_text="How high you'd like the trim stitch pattern to be. "
        "For short sleeves, be careful not to add an edging height "
        "higher than your sleeve is long!",
    )

    neck_edging_stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        limit_choices_to={"is_neckline_hem_stitch": True},
        related_name="%(app_label)s_neck_edging_stitch_designs_%(class)s",
        help_text="What stitch you'd like to trim the neck of your sweater. "
        "Necklines are trimmed during finishing. ",
        on_delete=models.CASCADE,
    )

    neck_edging_height = LengthField(
        null=True,
        blank=True,
        help_text="How high you'd like that trim stitch pattern to be.",
    )

    armhole_edging_stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        limit_choices_to={"is_armhole_hem_stitch": True},
        related_name="%(app_label)s_armhole_edging_stitch_designs_%(class)s",
        help_text="What stitch you'd like edging your armholes. This will be applied after finishing.",
        on_delete=models.CASCADE,
    )

    armhole_edging_height = LengthField(
        null=True,
        blank=True,
        help_text="How wide you'd like your armhole edging stitch to be. Values greater "
        "than 1&Prime; / 2.5&nbsp;cm may extend beyond the shoulders and bunch up under the arms.",
    )

    button_band_edging_stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        limit_choices_to={"is_buttonband_hem_stitch": True},
        related_name="%(app_label)s_button_band_edging_stitch_designs_%(class)s",
        help_text="What stitch you'd like to trim the front edges of your cardigan. "
        "Will be applied during finishing.",
        on_delete=models.CASCADE,
    )

    button_band_edging_height = LengthField(
        null=True, blank=True, help_text="How wide you'd like that trim stitch to be. "
    )

    button_band_allowance = LengthOffsetField(
        "button-band allowance",
        blank=True,
        null=True,
        help_text="How far apart you'd like the fronts of your cardigan to be, "
        "not including any edging. A value of 0 will result in cardigan "
        "fronts that meet in the middle before trim. A value of 1 will "
        'result in cardigan fronts that are 1" apart before adding trim. '
        'A value of -1 will result in cardigan fronts that overlap by 1" '
        "before adding trim. ",
    )

    button_band_allowance_percentage = models.FloatField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(100)],
        help_text="Alternate way to express button-band allowance: as "
        "percentage of neck width. This should be visible to "
        "designers only. It is illegal to provide a value for "
        "both this *and* button_band_allowance.",
    )

    number_of_buttons = NonNegSmallIntegerField(
        blank=True,
        null=True,
        help_text="How many buttons you'd like to use in your cardigan. "
        "Fewer than 5 buttons will be placed at the waist. "
        "(Yes, you can put 0.)",
    )

    #
    # Cable fields
    #

    # Developer's notes: These stitches will not be used by the engine directly.
    # They will be included in the 'stitches used' lists, and their charts will be
    # included in the set of stitch charts. But the engine will not automatically
    # add instructions to switch to these stitches or cast them on. Instead, they
    # need to be mentioned in custom templates.
    #
    # Also, the 'panel stitch' really is orthoginal to the cable stitches. It's a
    # 'free slot' into which designers can put stitches for things that are not cables,
    # like the Turks and Caicos neckline, or a special stitch for a yoke.

    panel_stitch = models.ForeignKey(
        stitches.Stitch,
        null=True,
        blank=True,
        related_name="%(app_label)s_panel_stitch_designs_%(class)s",
        limit_choices_to={"is_panel_stitch": True},
        on_delete=models.CASCADE,
    )

    back_cable_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_panel_stitch": True},
        related_name="%(app_label)s_back_cable_stitch_%(class)s",
        help_text="Cable stitch for back piece",
        on_delete=models.CASCADE,
    )

    back_cable_extra_stitches = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of extra stitches for back cable. (Can be zero or negative.)",
    )

    front_cable_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_panel_stitch": True},
        related_name="%(app_label)s_front_cable_stitch_%(class)s",
        help_text="Cable stitch for front piece",
        on_delete=models.CASCADE,
    )

    front_cable_extra_stitches = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of extra stitches for front cable. "
        "(Can be zero or negative. If cardigan, applied separately to each side.)",
    )

    sleeve_cable_stitch = models.ForeignKey(
        stitches.Stitch,
        blank=True,
        null=True,
        limit_choices_to={"is_panel_stitch": True},
        related_name="%(app_label)s_sleeve_cable_stitch_%(class)s",
        help_text="Cable stitch for sleeve",
        on_delete=models.CASCADE,
    )

    sleeve_cable_extra_stitches = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of extra stitches for sleeve cable. (Can be zero or negative.)",
    )

    sleeve_cable_extra_stitches_caston_only = models.BooleanField(
        default=False,
        help_text="If true, cable sitches will be applied to cast-on counts only",
    )

    pattern_credits = models.CharField(
        max_length=100,
        blank=True,
        help_text="For any non-authorship and non-photography credits. "
        "Example: 'Technical editing: Jane Doe.'",
    )

    def has_sweater_back(self):
        """
        Will return True iff resulting pattern should have a sweater-back piece
        in it.
        """
        return self.garment_type in [
            SDC.PULLOVER_SLEEVED,
            SDC.CARDIGAN_SLEEVED,
            SDC.ALL_PIECES,
        ]

    def has_sweater_front(self):
        """
        Will return True iff resulting pattern should have a sweater-front piece
        in it.
        """
        return self.garment_type in [SDC.PULLOVER_SLEEVED, SDC.ALL_PIECES]

    def has_vest_back(self):
        """
        Will return True iff resulting pattern should have a vest-back piece in
        it.
        """
        return self.garment_type in [
            SDC.PULLOVER_VEST,
            SDC.CARDIGAN_VEST,
            SDC.ALL_PIECES,
        ]

    def has_vest_front(self):
        """
        Will return True iff resulting pattern should have a vest-front piece in
        it.
        """
        return self.garment_type in [SDC.PULLOVER_VEST, SDC.ALL_PIECES]

    def has_cardigan_sleeved(self):
        """
        Will return True iff resulting pattern should have cardigan-sleeved
        pieces in it.
        """
        return self.garment_type in [SDC.CARDIGAN_SLEEVED, SDC.ALL_PIECES]

    def has_cardigan_vest(self):
        """
        Will return True iff resulting pattern should have cardigan-vest pieces
        in it.
        """
        return self.garment_type in [SDC.CARDIGAN_VEST, SDC.ALL_PIECES]

    def is_cardigan(self):
        return self.garment_type in [
            SDC.CARDIGAN_SLEEVED,
            SDC.CARDIGAN_VEST,
            SDC.ALL_PIECES,
        ]

    def has_sleeves(self):
        """
        Will return True iff resulting pattern should have a sleeve piece in it.
        """
        return self.garment_type in [
            SDC.PULLOVER_SLEEVED,
            SDC.CARDIGAN_SLEEVED,
            SDC.ALL_PIECES,
        ]

    def is_vest(self):
        """
        Will return True iff resulting pattern is a vest (has no sleeves).
        This is needed in our clean() method.
        """
        return self.garment_type in [SDC.PULLOVER_VEST, SDC.CARDIGAN_VEST]

    def supported_sleeve_length_choices(self):
        """
        Return the set of sleeve-length choices that are compatible
        with this Design. (Used in PersonalizeClassicDesign view.)

        (Note: we used to only be able to support short sleeves when
        the design was a short-sleeve design. That is no longer the case.)
        """
        if not self.has_sleeves():
            return []
        else:
            # We need to be sure to return a copy of the list
            # from design_choices. Lists are malleable and we don't know
            # what's going to happen to it down stream.
            return copy.copy(SDC.SLEEVE_LENGTH_CHOICES)

    def supported_torso_length_choices(self):
        """
        Return the set of torso-length choices that are compatible
        with this Design. (Used in PersonalizeClassicDesign view.)
        """
        return copy.copy(SDC.HIP_LENGTH_CHOICES)

    def sleeve_is_bell(self):
        return self.sleeve_shape == SDC.SLEEVE_BELL

    # Used in CardiganFront to compute the acutal button-band height
    def button_band_to_fill_allowance(self):
        """
        Returns True if the user's intent is that the button-band should
        actually fill the gap between the pieces.
        """

        # The logic here is that if the button-band allowance and height
        # are the same in the design, then the user intended the button
        # band to actually fill the gap between the pieces. Then the actual
        # button band should be as high as the allowance. If not, then
        # the user intended the button band to be decorative and so it should
        # not be adjusted to fill the allowance.
        #
        # Update: now that we allow the designer to express button-band
        # allowances as a percentage of neckline, this gets a little more
        # complicated. But not much: if they express the allowance as a
        # percentage, then we skip the logic and assume that they didn't
        # want the buttonband to exactly fill the allowance.
        if self.button_band_allowance is not None:
            assert self.button_band_edging_height is not None
            return self.button_band_allowance == self.button_band_edging_height
        else:
            return False

    #
    # Methods/properties for templates
    #

    def is_veeneck(self):
        return self.neckline_style == SDC.NECK_VEE

    def _is_veeneck_cardigan(self):
        return all([self.is_cardigan(), self.is_veeneck()])

    def neck_edging_stitch_patterntext(self):
        if self._is_veeneck_cardigan():
            return None
        else:
            if self.neck_edging_stitch:
                return self.neck_edging_stitch.patterntext
            else:
                return None

    def neckline_style_patterntext(self):
        if self.neckline_width == SDC.NECK_OTHERWIDTH:
            if self.neckline_other_val_percentage == 0:
                return "No neck"
            elif self.neckline_other_val_percentage == 100:
                return "No neck shaping"

        shape_text = SDC.NECKLINE_STYLE_CUSTOM_FORM[self.neckline_style]
        width_text = SDC.NECKLINE_WIDTHS_SHORT_FORMS[self.neckline_width]
        return_me = "%s %s neck" % (width_text, shape_text)
        return return_me.lower().capitalize()

    def neckline_depth_orientation_patterntext(self):
        # Note: get_neckline_depth_orientation_display() created
        # automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_neckline_depth_orientation_display()

    def neckline_width_patterntext_short_form(self):
        return SDC.NECKLINE_WIDTHS_SHORT_FORMS[self.neckline_width]

    def torso_length_patterntext(self):
        # Note: get_torso_length_isplay() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_torso_length_display()

    def hip_edging_stitch_patterntext(self):
        return self.hip_edging_stitch.patterntext

    def sleeve_length_patterntext(self):
        if not self.has_sleeves():
            return None
        else:
            length_text = SDC.SLEEVE_LENGTH_SHORT_FORMS[self.sleeve_length]
            if self.sleeve_length == SDC.SLEEVE_SHORT:
                return_me = "%s sleeve" % length_text
            else:
                shape_text = SDC.SLEEVE_SHAPE_SHORT_FORMS[self.sleeve_shape]
                if self.sleeve_shape == SDC.SLEEVE_BELL:
                    bell_shape_text = SDC.BELL_TYPE_SHORT_FORMS[self.bell_type]
                    return_me = "%s %s %s sleeve" % (
                        length_text,
                        bell_shape_text,
                        shape_text,
                    )
                else:
                    return_me = "%s %s sleeve" % (length_text, shape_text)
            return return_me.lower().capitalize()

    def sleeve_length_patterntext_short_form(self):
        if not self.has_sleeves():
            return None
        else:
            return SDC.SLEEVE_LENGTH_SHORT_FORMS[self.sleeve_length]

    def sleeve_edging_stitch_patterntext(self):
        if not self.has_sleeves():
            return None
        else:
            if self.sleeve_edging_stitch:
                return self.sleeve_edging_stitch.patterntext
            else:
                return None

    def armhole_edging_stitch_patterntext(self):
        if self.has_sleeves():
            return None
        else:
            if self.armhole_edging_stitch:
                return self.armhole_edging_stitch.patterntext
            else:
                return None

    def button_band_edging_stitch_patterntext(self):
        if not self.is_cardigan():
            return None
        else:
            if self.button_band_edging_stitch:
                return self.button_band_edging_stitch.patterntext
            else:
                return None

    def stitches_used(self):
        """
        Returns a list of all stitches used in this design, in an arbitrary
        but consistent/reproducible order and with no repeats.
        """
        # Note: It would be pythonic to do this with sets rather than lists,
        # except that we would like to enforce a consistent order in the
        # return-list.

        stitch_list = []

        # add stitches

        stitch_list.append(self.hip_edging_stitch)
        stitch_list.append(self.front_allover_stitch)
        stitch_list.append(self.back_allover_stitch)
        stitch_list.append(self.panel_stitch)
        stitch_list += self.get_additional_element_stitches()

        if self.has_sleeves():
            stitch_list.append(self.sleeve_edging_stitch)
            stitch_list.append(self.sleeve_allover_stitch)
        else:
            stitch_list.append(self.armhole_edging_stitch)

        if self.is_cardigan():
            stitch_list.append(self.button_band_edging_stitch)
            if not self.is_veeneck():
                stitch_list.append(self.neck_edging_stitch)
        else:
            stitch_list.append(self.neck_edging_stitch)

        stitch_list.append(self.back_cable_stitch)
        stitch_list.append(self.front_cable_stitch)
        stitch_list.append(self.sleeve_cable_stitch)

        # This list may have duplicates, and may contain None (e.g., the
        # neckline stitch is allowed to be None when the neckline hem height
        # is 0). Remove both.

        return_me = []
        for stitch in stitch_list:
            if all([stitch is not None, stitch not in return_me]):
                return_me.append(stitch)
        return return_me

    def get_additional_element_stitches(self):
        # sub-classes must implement this
        raise NotImplementedError()

    def compatible_swatch(self, swatch):
        """
        Return True iff the swatch is compatible with this design. At the
        moment, this means only that the repeats of the swatch's allover
        stitch is compatible with the allover stitches of this design.
        """
        swatch_stitch = swatch.get_stitch()
        allover_stitches = [
            self.front_allover_stitch,
            self.back_allover_stitch,
            self.sleeve_allover_stitch,
        ]
        return all(swatch_stitch.is_compatible(x) for x in allover_stitches)

    # There is not a compatible_body method here; see instead
    # missing_body_entries() in garment_parameters.py.

    def clean(self):

        errors = []

        try:
            super(SweaterDesignBase, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        # Test 1: Make sure requisite sleeve (or armhole) values are present

        if self.has_sleeves():
            self.armhole_edging_stitch = None
            self.armhole_edging_height = None

            if self.sleeve_length is None:
                errors.append(ValidationError("Please select a sleeve length"))

            if self.sleeve_edging_height is None:
                errors.append(
                    ValidationError("Please provide a value for sleeve-edging height")
                )

            # Do they want sleeve-edging?
            if (self.sleeve_edging_height or 0) > 0:
                # Looks like they do. Check that we have the rest of the
                # values we need
                if self.sleeve_edging_stitch is None:
                    errors.append(
                        ValidationError("Please select a sleeve edging stitch")
                    )

            if self.sleeve_shape is None:
                errors.append(ValidationError("Please select a sleeve shape"))
            else:
                # Sub-test: Is is a bell sleeve? If so, make sure that a
                # bell-type has been chosen
                if self.sleeve_shape == SDC.SLEEVE_BELL:
                    if self.bell_type is None:
                        errors.append(ValidationError("Please select a bell type"))

        elif self.is_vest():

            # if the customer has changed her choice of garment_type to a vest,
            # that should override any previous choices for sleeves.
            self.sleeve_length = None
            self.sleeve_shape = None
            self.bell_type = None
            self.sleeve_edging_height = None
            self.sleeve_edging_stitch = None
            self.sleeve_cable_stitch = None
            self.sleeve_cable_extra_stitches = None

            if self.armhole_edging_height is None:
                errors.append(
                    ValidationError("Please provide a value for armhole-edging height")
                )

            # Do they want armhole edging?
            if (self.armhole_edging_height or 0) > 0:
                # They do. Check that we have the values we need.
                if self.armhole_edging_stitch is None:
                    errors.append(
                        ValidationError("Please select an armhole-edging stitch")
                    )

        else:  # it is not a vest and has no sleeves
            errors.append(
                ValidationError("The garment must either have sleeves or be a vest.")
            )

        # Test 2: If the other-width option is selected for neckine, make sure it is provided
        if self.neckline_width == SDC.NECK_OTHERWIDTH:
            if self.neckline_other_val_percentage is None:
                errors.append(
                    ValidationError(
                        "A percentage must be provided for the neckline width"
                    )
                )

        # Test 3: Some fields are required for cardigans but not pullovers
        if self.is_cardigan():

            if all(
                [
                    self.button_band_allowance is None,
                    self.button_band_allowance_percentage is None,
                ]
            ):
                errors.append(
                    ValidationError("Please enter a value for button-band allowance")
                )
            if all([self.button_band_allowance, self.button_band_allowance_percentage]):
                errors.append(
                    ValidationError(
                        "Cannot provide both inches and "
                        "percentage for button-band allowance. "
                        "Please pick only one."
                    )
                )

            if self.button_band_edging_height is None:
                errors.append(
                    ValidationError(
                        "Please enter a value for button-band edging height"
                    )
                )
            # They may not want a button band. Do they?
            elif self.button_band_edging_height > 0:
                # They do. Check that we have the rest of the values we need
                if self.button_band_edging_stitch is None:
                    errors.append(
                        ValidationError("Please select a button-band edging stitch")
                    )
                if self.number_of_buttons is None:
                    errors.append(
                        ValidationError(
                            "Please enter a value for 'Number of buttons' (Note: zero is allowed)"
                        )
                    )

        # Test 4: neckline-edging fields are required for everything but
        # v-neck cardigans
        if not all(
            [
                self.garment_type in [SDC.CARDIGAN_SLEEVED, SDC.CARDIGAN_VEST],
                self.neckline_style == SDC.NECK_VEE,
            ]
        ):
            if self.neck_edging_height is None:
                errors.append(
                    ValidationError("Please provide a value for neckline-edging height")
                )
            # DO they want neck-edging?
            elif self.neck_edging_height > 0:
                # Looks like they do. Do we have all the values we need?
                if self.neck_edging_stitch is None:
                    errors.append(
                        ValidationError("Please select a neckline-edging stitch")
                    )

        # Note: we used to test that the edging-stitches were compatible
        # with the relevant allover stitches, I'm told that this
        # is unnecessary.

        # Test 5: Test that we have consistent orders with regard to cables:

        if self.sleeve_cable_stitch is not None:
            if self.sleeve_cable_extra_stitches is None:
                errors.append(
                    ValidationError(
                        "Please provide a number of extra stitches to add for the sleeve cable. "
                        "(0 is a valid value.)"
                    )
                )
        if self.back_cable_stitch is not None:
            if self.back_cable_extra_stitches is None:
                errors.append(
                    ValidationError(
                        "Please provide a number of extra stitches to add for the back cable. "
                        "(0 is a valid value.)"
                    )
                )
        if self.front_cable_stitch is not None:
            if self.front_cable_extra_stitches is None:
                errors.append(
                    ValidationError(
                        "Please provide a number of extra stitches to add for the front cable. "
                        "(0 is a valid value.)"
                    )
                )

        if self.sleeve_cable_extra_stitches is not None:
            if self.sleeve_cable_stitch is None:
                errors.append(
                    ValidationError(
                        "Please pick a stitch for the sleeve cable "
                        "(or void out the extra-cable count)"
                    )
                )

        if self.back_cable_extra_stitches is not None:
            if self.back_cable_stitch is None:
                errors.append(
                    ValidationError(
                        "Please pick a stitch for the back cable "
                        "(or void out the extra-cable count)"
                    )
                )

        if self.front_cable_extra_stitches is not None:
            if self.front_cable_stitch is None:
                errors.append(
                    ValidationError(
                        "Please pick a stitch for the front cable "
                        "(or void out the extra-cable count)"
                    )
                )
        # Note: some necklines are incompatible with front cables
        if self.front_cable_stitch is not None:
            if self.neckline_style in [SDC.NECK_VEE, SDC.NECK_TURKS_AND_CAICOS]:
                errors.append(
                    ValidationError(
                        "Please choose a neckline-style that can "
                        "handle a front cable."
                    )
                )

        if errors:
            raise ValidationError(errors)

        # end clean()

    class Meta:
        abstract = True


class SweaterDesign(Design, SweaterDesignBase):

    primary_silhouette = models.CharField(
        max_length=25,
        choices=SDC.SILHOUETTE_CHOICES,
    )

    silhouette_hourglass_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in hourglass silhouette",
    )

    silhouette_straight_allowed = models.BooleanField(
        default=True,
        help_text="Set to True if this design can be made in straight silhouette",
    )

    silhouette_aline_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in a-line silhouette",
    )

    silhouette_tapered_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in tapered silhouette",
    )

    silhouette_half_hourglass_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in half-hourglass silhouette",
    )

    primary_construction = models.CharField(
        max_length=15, choices=SDC.SUPPORTED_CONSTRUCTIONS
    )

    construction_set_in_sleeve_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in set-in-sleeve construction",
    )

    construction_drop_shoulder_allowed = models.BooleanField(
        default=False,
        help_text="Set to True if this design can be made in drop-shoulder construction",
    )

    waist_hem_template = models.ForeignKey(
        stitches.WaistHemTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the waist cast-on. "
        "Replaces the 'waist_hem.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %} and will be given a "
        "body-piece under the name 'piece', but this may be "
        "a SweaterBack, VestBack, CardiganFront, etc. "
        "If omitted, the stitch-default will be used.",
        on_delete=models.CASCADE,
    )

    sleeve_hem_template = models.ForeignKey(
        stitches.SleeveHemTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the sleeve cast-on. "
        "Replaces the 'sleeve_hem.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %} and will be given a "
        "Sleeve under the name 'piece'."
        "If omitted, the stitch-default will be used.",
        on_delete=models.CASCADE,
    )

    trim_armhole_template = models.ForeignKey(
        stitches.TrimArmholeTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the armhole trim. "
        "Replaces the 'trim_armhole.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %}, and "
        "{% with design=piece.get_spec_source %} is useful too. "
        "Will be given a "
        "Pattern object under the name 'piece'."
        "If omitted, the stitch-default will be used.",
        on_delete=models.CASCADE,
    )

    trim_neckline_template = models.ForeignKey(
        stitches.TrimNecklineTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the neck trim. "
        "Replaces the 'trim_neckline.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %}, and "
        "{% with design=piece.get_spec_source %} is useful too. "
        "Will be given a "
        "Pattern object under the name 'piece'."
        "If omitted, the stitch-default will be used.",
        on_delete=models.CASCADE,
    )

    button_band_template = models.ForeignKey(
        stitches.ButtonBandTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the button band trim. "
        "Replaces the 'button_band.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %}. "
        "Will be given a "
        "ButtonBand object under the name 'button_band'."
        "If omitted, the stitch-default will be used. "
        "Does not apply to v-necks-- "
        "button_band_veeneck_template is used instead.",
        on_delete=models.CASCADE,
    )

    button_band_veeneck_template = models.ForeignKey(
        stitches.ButtonBandVeeneckTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for the button band trim. "
        "Replaces the 'button_band_veeneck.html' template. "
        "Note: Template should start with "
        "{% load pattern_conventions %}. "
        "Will be given a "
        "ButtonBand object under the name 'button_band'."
        "If omitted, the stitch-default will be used. "
        "Does not apply to necks other than v-necks-- "
        "button_band_template is used instead.",
        on_delete=models.CASCADE,
    )

    extra_finishing_template = models.ForeignKey(
        ExtraFinishingTemplate,
        null=True,
        blank=True,
        related_name="+",  # We don't need a backwards relation
        help_text="Design-specific template for *extra* finishing "
        "instructions.  "
        "Gets added by the FinishingRenderer as a last "
        "addition. Note: Template should start with "
        "{% load pattern_conventions %} and be 'complete' "
        "HTML (include liminal p or h3 tags).",
        on_delete=models.CASCADE,
    )

    def supported_fit_choices(self):
        """
        Return the set of garment fit choices that are compatible
        with this Design.  Hourglass designs must have hourglass fits;
        non-hourglass designs must have non-hourglass fits.

        (Used in _PersonalizeDesignForm)
        """
        choices = []
        if self.silhouette_hourglass_allowed or self.silhouette_half_hourglass_allowed:
            choices += SDC.GARMENT_FIT_CHOICES_HOURGLASS

        # note: not elif
        if any(
            [
                self.silhouette_aline_allowed,
                self.silhouette_straight_allowed,
                self.silhouette_tapered_allowed,
            ]
        ):
            choices += SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS

        # remove duplicates
        return_me = []
        for choice in choices:
            if choice not in return_me:
                return_me.append(choice)

        return return_me

    def supported_silhouette_choices(self):
        """
        Return the set of silhouette choices that are compatible
        with this Design.

        (Used in _PersonalizeDesignForm)
        """
        choices = []
        for const, display in SDC.SILHOUETTE_CHOICES:
            if any(
                [
                    const == SDC.SILHOUETTE_ALINE and self.silhouette_aline_allowed,
                    const == SDC.SILHOUETTE_HALF_HOURGLASS
                    and self.silhouette_half_hourglass_allowed,
                    const == SDC.SILHOUETTE_HOURGLASS
                    and self.silhouette_hourglass_allowed,
                    const == SDC.SILHOUETTE_STRAIGHT
                    and self.silhouette_straight_allowed,
                    const == SDC.SILHOUETTE_TAPERED and self.silhouette_tapered_allowed,
                ]
            ):
                choices += [(const, display)]

        return choices

    def supported_silhouettes_patterntext(self):
        ALINE_WORD = "a-line"
        HOURGLASS_WORD = "hourglass"
        HALF_HOURGLASS_WORD = "half-hourglass"
        STRAIGHT_WORD = "straight"
        TAPERED_WORD = "tapered"

        words = []
        if self.primary_silhouette == SDC.SILHOUETTE_ALINE:
            primary = ALINE_WORD
            if self.silhouette_hourglass_allowed:
                words += [HOURGLASS_WORD]
            if self.silhouette_half_hourglass_allowed:
                words += [HALF_HOURGLASS_WORD]
            if self.silhouette_straight_allowed:
                words += [STRAIGHT_WORD]
            if self.silhouette_tapered_allowed:
                words += [TAPERED_WORD]
        elif self.primary_silhouette == SDC.SILHOUETTE_HOURGLASS:
            primary = HOURGLASS_WORD
            if self.silhouette_half_hourglass_allowed:
                words += [HALF_HOURGLASS_WORD]
            if self.silhouette_aline_allowed:
                words += [ALINE_WORD]
            if self.silhouette_straight_allowed:
                words += [STRAIGHT_WORD]
            if self.silhouette_tapered_allowed:
                words += [TAPERED_WORD]
        elif self.primary_silhouette == SDC.SILHOUETTE_HALF_HOURGLASS:
            primary = HALF_HOURGLASS_WORD
            if self.silhouette_aline_allowed:
                words += [ALINE_WORD]
            if self.silhouette_hourglass_allowed:
                words += [HOURGLASS_WORD]
            if self.silhouette_straight_allowed:
                words += [STRAIGHT_WORD]
            if self.silhouette_tapered_allowed:
                words += [TAPERED_WORD]
        elif self.primary_silhouette == SDC.SILHOUETTE_STRAIGHT:
            primary = STRAIGHT_WORD
            if self.silhouette_aline_allowed:
                words += [ALINE_WORD]
            if self.silhouette_hourglass_allowed:
                words += [HOURGLASS_WORD]
            if self.silhouette_half_hourglass_allowed:
                words += [HALF_HOURGLASS_WORD]
            if self.silhouette_tapered_allowed:
                words += [TAPERED_WORD]
        else:
            assert self.primary_silhouette == SDC.SILHOUETTE_TAPERED
            primary = TAPERED_WORD
            if self.silhouette_aline_allowed:
                words += [ALINE_WORD]
            if self.silhouette_hourglass_allowed:
                words += [HOURGLASS_WORD]
            if self.silhouette_half_hourglass_allowed:
                words += [HALF_HOURGLASS_WORD]
            if self.silhouette_straight_allowed:
                words += [STRAIGHT_WORD]

        return_me = "Pictured in %s silhouette." % primary

        if not words:
            pass
        elif len(words) == 1:
            return_me += " Also available in %s silhouette." % words[0]
        elif len(words) == 2:
            return_me += " Also available in %s and %s silhouettes." % (
                words[0],
                words[1],
            )
        elif len(words) == 3:
            return_me += " Also available in %s, %s, and %s silhouettes." % (
                words[0],
                words[1],
                words[2],
            )
        else:
            assert len(words) == 4
            return_me += " Also available in %s, %s, %s, and %s silhouettes." % (
                words[0],
                words[1],
                words[2],
                words[3],
            )

        return return_me

    def supported_construction_choices(self):
        """
        Return the set of construction choices that are compatible
        with this Design.
        """
        choices = []
        for const, display in SDC.SUPPORTED_CONSTRUCTIONS:
            if any(
                [
                    const == SDC.CONSTRUCTION_SET_IN_SLEEVE
                    and self.construction_set_in_sleeve_allowed,
                    const == SDC.CONSTRUCTION_DROP_SHOULDER
                    and self.construction_drop_shoulder_allowed,
                ]
            ):
                choices += [(const, display)]
        return choices

    def isotope_classes(self):

        return_me = []

        silhouettes = self.supported_silhouette_choices()
        silhouette_classes = [
            SDC.SILHOUETTE_TO_SHORT_NAME[sil_const] for (sil_const, _) in silhouettes
        ]
        return_me += silhouette_classes

        constructions = self.supported_construction_choices()
        construction_classes = [
            SDC.CONSTRUCTION_TO_SHORT_NAME[con_const]
            for (con_const, _) in constructions
        ]
        return_me += construction_classes

        return " ".join(return_me)

    def get_additional_element_stitches(self):

        # Return a list of Stitches used in *relevant* additional elements.
        # For example, return the Stitch used in an AdditionalSleeveElement iff
        # the design is not a vest.

        def _append_stitches(element_list, output_list):
            for el in element_list:
                stitch = el.stitch
                if stitch is not None:
                    output_list.append(stitch)

        return_me = []

        # The order of the following matters: back, then front, then sleeve

        back_els = AdditionalBackElement.objects.filter(design=self).all()
        _append_stitches(back_els, return_me)

        full_els = AdditionalFullTorsoElement.objects.filter(design=self).all()
        _append_stitches(full_els, return_me)

        front_els = AdditionalFrontElement.objects.filter(design=self).all()
        _append_stitches(front_els, return_me)

        if self.has_sleeves():
            sleeve_els = AdditionalSleeveElement.objects.filter(design=self).all()
            _append_stitches(sleeve_els, return_me)

        return return_me

    def uses_stitch(self, stitch):
        # Returns True if the Design uses the Stitch in any way. Declared in Design.
        # Note: must be implemented here instead of SweaterDesignBase due to how SweaterDesign
        # Inherits from Design before SweaterDesignBase. If we define it in SweaterDesignBase,
        # it would be shadowed by the method in Design
        return stitch in self.stitches_used()

    def clean(self):

        errors = []

        try:
            super(Design, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        # The flag for the primary silhouette must be set:
        if any(
            [
                (self.primary_silhouette == SDC.SILHOUETTE_ALINE)
                and not self.silhouette_aline_allowed,
                (self.primary_silhouette == SDC.SILHOUETTE_HOURGLASS)
                and not self.silhouette_hourglass_allowed,
                (self.primary_silhouette == SDC.SILHOUETTE_HALF_HOURGLASS)
                and not self.silhouette_half_hourglass_allowed,
                (self.primary_silhouette == SDC.SILHOUETTE_STRAIGHT)
                and not self.silhouette_straight_allowed,
                (self.primary_silhouette == SDC.SILHOUETTE_TAPERED)
                and not self.silhouette_tapered_allowed,
            ]
        ):
            errors.append(ValidationError("Primary silhouette must be allowed."))

        # Technically redundant with above + the fact that primary_silhouette cannot be blank, but let's
        # put it in to future-proof our code
        if not any(
            [
                self.silhouette_aline_allowed,
                self.silhouette_hourglass_allowed,
                self.silhouette_half_hourglass_allowed,
                self.silhouette_straight_allowed,
                self.silhouette_tapered_allowed,
            ]
        ):
            errors.append(ValidationError("Please allow at least one silhouette"))

        # The flag for the primary construction must be set:
        if any(
            [
                (self.primary_construction == SDC.CONSTRUCTION_SET_IN_SLEEVE)
                and not self.construction_set_in_sleeve_allowed,
                (self.primary_construction == SDC.CONSTRUCTION_DROP_SHOULDER)
                and not self.construction_drop_shoulder_allowed,
            ]
        ):
            errors.append(ValidationError("Primary construction must be allowed."))

        # Technically redundant with above + the fact that primary_construction cannot be blank, but let's
        # put it in to future-proof our code
        if not any(
            [
                self.construction_set_in_sleeve_allowed,
                self.construction_drop_shoulder_allowed,
            ]
        ):
            errors.append(ValidationError("Please allow at least one construction"))

        # If drop-shoulder is allowed, then must set default depth
        if self.construction_drop_shoulder_allowed:
            if self.drop_shoulder_additional_armhole_depth is None:
                errors.append(
                    ValidationError(
                        {
                            "drop_shoulder_additional_armhole_depth": "Must set default drop-shoulder armhole depth when drop-shoulder construction is allowed"
                        }
                    )
                )

        # If default_depth must be blank if drop-shoulder not allowed
        if not self.construction_drop_shoulder_allowed:
            if self.drop_shoulder_additional_armhole_depth is not None:
                errors.append(
                    ValidationError(
                        {
                            "drop_shoulder_additional_armhole_depth": "Must not set drop-shoulder armhole depth when drop-shoulder not allowed."
                        }
                    )
                )

        if errors:
            raise ValidationError(errors)

        # end clean()
