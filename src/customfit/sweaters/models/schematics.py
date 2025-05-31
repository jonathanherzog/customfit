import logging

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from customfit.fields import LengthOffsetField, NonNegFloatField
from customfit.schematics.models import (
    ConstructionSchematic,
    GradedConstructionSchematic,
    GradedPieceSchematic,
    PieceSchematic,
)

from ..helpers import sweater_design_choices as SDC
from ..helpers.schematic_images import (
    get_back_schematic_url,
    get_front_schematic_url,
    get_sleeve_schematic_url,
)
from .garment_parameters import SweaterGradedGarmentParametersGrade

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Subclasses need to implement:
#
# * schematic_field_name
# * _get_values_from_gp
# * get_spec_source


class _IndividualSchematicMixin(object):
    def get_spec_source(self):
        sweater_schematic = self.sweaterschematic
        spec_source = sweater_schematic.get_spec_source()
        return spec_source


class _GradedSchematicMixin(models.Model):
    class Meta:
        abstract = True

    gp_grade = models.ForeignKey(
        SweaterGradedGarmentParametersGrade, on_delete=models.CASCADE
    )

    def get_spec_source(self):
        return self.construction_schematic.get_spec_source()

    def _get_values_from_gp_and_grade(self, _, gp_grade):
        self.gp_grade = gp_grade
        return self._get_values_from_gp(gp_grade)

    def get_grade(self):
        return self.gp_grade.grade


class _GradedCardiganMixin(object):
    def double_into_pullover(self):
        # Should only be used for cardigans
        return_me = super(_GradedCardiganMixin, self).double_into_pullover()
        return_me.gp_grade = self.gp_grade
        return return_me


class BaseBodyPieceSchematic(models.Model):
    """
    An abstract base class for those schematics that represent body pieces:
    those which go on the torso such as sweater-back, vest-front and
    cardigan front.

    When a method lacks a docstring, see the same-named method in
    PieceSchematic.
    """

    class Meta:
        abstract = True

    hip_width = NonNegFloatField(help_text="Width of the hip cast-ons (in inches)")

    shoulder_height = NonNegFloatField(
        help_text="Length from hip cast-ons to top of shoulder bindoffs " "(in inches)"
    )

    armpit_height = NonNegFloatField(
        help_text="Length from hip cast-ons to beginning of armhole shaping "
        "(in inches)"
    )

    waist_height = NonNegFloatField(
        blank=True,
        null=True,  # Not used for non-hourglass garments
        help_text="Length from hip cast-ons to waist (in inches)",
    )

    bust_width = NonNegFloatField(
        help_text="Width of the sweater-back bust (in inches)"
    )

    # Waist width is undefined for non-hourglass garments (straight, a-line,
    # tapered)
    waist_width = NonNegFloatField(
        blank=True, null=True, help_text="Width of the sweater-back waist (in inches)"
    )

    neck_height = NonNegFloatField(
        help_text="Length from hip cast-ons to sweater-back neck bindoffs (in inches)"
    )

    @property
    def torso_hem_height(self):
        return self.get_spec_source().hip_edging_height

    @property
    def hem_stitch(self):
        return self.get_spec_source().hip_edging_stitch

    @property
    def is_straight(self):
        # Note: the following logic assumes that the model passes clean()
        if self.bust_width != self.hip_width:
            return False
        if self.waist_width is not None:
            if self.bust_width != self.waist_width:
                return False
            if self.hip_width != self.waist_width:
                return False
        return True

    @property
    def is_aline(self):
        # Note: the following logic assumes that the model passes clean()
        return all([self.waist_width is None, self.bust_width < self.hip_width])

    @property
    def is_tapered(self):
        # Note: the following logic assumes that the model passes clean()
        return all([self.waist_width is None, self.bust_width > self.hip_width])

    @property
    def is_hourglass(self):
        # Note: the following logic assumes that the model passes clean()
        return all([self.waist_width is not None, not self.is_straight])

    @property
    def armhole_depth(self):
        return self.shoulder_height - self.armpit_height

    @property
    def waist_to_armhole(self):
        if self.waist_height is None:
            return None
        else:
            return self.armpit_height - self.waist_height

    def _get_values_from_gp(self, gp):
        self.shoulder_height = gp.shoulder_height
        self.armpit_height = gp.armpit_height
        # Note: self.waist_height needs to be set in FrontPiece and BackPiece,
        # below

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

    def clean(self):

        errors = []

        try:
            super(BaseBodyPieceSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if self.shoulder_height <= self.armpit_height:
            errors.append(
                ValidationError("Shoulder-height must be larger than armhole-height")
            )

        if self.waist_height is not None:
            if self.armpit_height <= self.waist_height:
                errors.append(
                    ValidationError("Armhole-height must be larger than waist-height")
                )

            if self.waist_height < self.torso_hem_height:
                errors.append(
                    ValidationError(
                        "Waist-height must be larger than hip-edging height"
                    )
                )

        if (self.waist_height is None) != (self.waist_width is None):
            errors.append(
                ValidationError(
                    "Waist-height and waist-width must both be present or both blank"
                )
            )

        if self.waist_width is not None:
            if self.hip_width < self.waist_width:
                errors.append(
                    ValidationError("Hip-width must not be smaller than waist-width")
                )

            if self.bust_width < self.waist_width:
                errors.append(
                    ValidationError("Bust-width must not be smaller than waist-width")
                )

        if self.shoulder_height < self.neck_height:
            errors.append(
                ValidationError("Neck-height must be less than shoulder height")
            )

        if errors:
            raise ValidationError(errors)


class BaseBackPieceSchematic(BaseBodyPieceSchematic):
    """
    An abstract base class for those schematics that represent backs:
    currently just sweater-back and vest-back.

    When a method lacks a docstring, see the same-named method in
    PieceSchematic.
    """

    cross_back_width = NonNegFloatField(
        help_text="Width remaining between armholes after armhole shaping (sweater back; "
        "in inches)"
    )

    neck_opening_width = NonNegFloatField(
        help_text="Width of the neck opening (in inches)"
    )

    def _get_values_from_gp(self, gp):
        super(BaseBackPieceSchematic, self)._get_values_from_gp(gp)

        self.hip_width = gp.hip_width_back
        self.cross_back_width = gp.back_cross_back_width
        self.neck_opening_width = gp.back_neck_opening_width
        self.neck_height = gp.back_neck_height
        self.bust_width = gp.bust_width_back
        self.waist_width = gp.waist_width_back

        self.waist_height = gp.waist_height_back

    def get_schematic_image(self):
        construction = self.construction
        if self.is_straight:
            return get_back_schematic_url(SDC.SILHOUETTE_STRAIGHT, construction)
        elif self.is_hourglass:
            return get_back_schematic_url(SDC.SILHOUETTE_HOURGLASS, construction)
        elif self.is_aline:
            return get_back_schematic_url(SDC.SILHOUETTE_ALINE, construction)
        else:
            assert self.is_tapered
            return get_back_schematic_url(SDC.SILHOUETTE_TAPERED, construction)

    def clean(self):
        errors = []

        try:
            super(BaseBackPieceSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if self.bust_width < self.cross_back_width:
            errors.append(
                ValidationError(
                    "Bust width must not be smaller than " "cross-back width."
                )
            )

        if self.cross_back_width < self.neck_opening_width:
            errors.append(
                ValidationError(
                    "Neck-opening width must be less than " "cross-back width."
                )
            )

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class BaseSweaterBackSchematic(BaseBackPieceSchematic):
    """
    Schematic for a SweaterBack.
    """

    class Meta:
        abstract = True

    schematic_field_name = "sweater_back"
    piece_name = "Sweater Back"


class SweaterBackSchematic(
    BaseSweaterBackSchematic, _IndividualSchematicMixin, PieceSchematic
):
    pass


class GradedSweaterBackSchematic(
    BaseSweaterBackSchematic, _GradedSchematicMixin, GradedPieceSchematic
):
    pass


class BaseVestBackSchematic(BaseBackPieceSchematic):
    """
    Schematic for a SweaterBack.
    """

    class Meta:
        abstract = True

    schematic_field_name = "vest_back"
    piece_name = "Vest Back"


class VestBackSchematic(
    BaseVestBackSchematic, _IndividualSchematicMixin, PieceSchematic
):
    pass


class GradedVestBackSchematic(
    BaseVestBackSchematic, _GradedSchematicMixin, GradedPieceSchematic
):
    pass


class BaseFrontPieceSchematic(BaseBodyPieceSchematic):
    """
    An abstract base class for those schematics that represent front-pieces:
    pullover-fronts and cardigan-fronts, both sleeved and vest. Note that
    cardigan fronts have an additional abstract base class,
    CardiganFrontSchematic, which subclasses this one.

    When a method lacks a docstring, see the same-named method in
    PieceSchematic.
    """

    # TODO: is there special sauce for vertical bust darts?

    # Sweater-front measurements

    neckline_style = models.CharField(
        max_length=16,
        help_text="Style of the neckline. (Should be one of the members of "
        "design_choices.NECKLINE_STYLE_CHOICES.)",
    )

    below_armpit_straight = NonNegFloatField(
        # Note: this field was added late, and so the initial ~6K patterns
        # did not have it. Rather than allowing those schematics to have
        # None in this field, we gave them a default value of BUSTTOARMPIT
        # (1.5 inches). If you need to perform some sort of migration or
        # computation on schematics, be aware that a value of exactly 1.5 here
        # is likely to be bogus.
        help_text="Ideal amount of straight distance between end of "
        "bust shaping and beginning of armhole shaping. "
        "Engine will violate this parameter if it needs additional "
        "vertical distance for the desired shaping."
    )

    def _get_values_from_gp(self, gp):
        super(BaseFrontPieceSchematic, self)._get_values_from_gp(gp)

        self.hip_width = gp.hip_width_front
        self.waist_width = gp.waist_width_front
        self.neck_height = gp.front_neck_height
        self.bust_width = gp.bust_width_front
        self.neckline_style = gp.get_spec_source().neckline_style

        self.waist_height = gp.waist_height_front

        # Start with the default value-- users can tweak on tweak screen
        self.below_armpit_straight = gp.below_armhole_straight

    def get_schematic_image(self):
        spec_source = self.get_spec_source()
        neckline_style = spec_source.neckline_style
        construction = self.construction

        if self.is_straight:
            silhouette = SDC.SILHOUETTE_STRAIGHT
        elif self.is_hourglass:
            silhouette = SDC.SILHOUETTE_HOURGLASS
        elif self.is_aline:
            silhouette = SDC.SILHOUETTE_ALINE
        else:
            assert self.is_tapered
            silhouette = SDC.SILHOUETTE_TAPERED

        return get_front_schematic_url(
            silhouette, neckline_style, construction, cardigan=False
        )

    def get_spec_source(self):
        try:
            # Try getting the attribute created by double_into_pullover first
            return self.spec_source
        except AttributeError:
            return super(BaseFrontPieceSchematic, self).get_spec_source()

    def clean(self):
        errors = []

        try:
            super(BaseFrontPieceSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if self.waist_height is not None:
            waist_to_armpit = self.armpit_height - self.waist_height
            if self.below_armpit_straight > waist_to_armpit:
                errors.append(ValidationError("bust-shaping cannot end below waist."))

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class BaseSweaterFrontSchematic(BaseFrontPieceSchematic):
    """
    A schematic for pullover-sleeved fronts.
    """

    class Meta:
        abstract = True

    schematic_field_name = "sweater_front"
    piece_name = "Sweater Front"


class SweaterFrontSchematic(
    BaseSweaterFrontSchematic, _IndividualSchematicMixin, PieceSchematic
):
    pass


class GradedSweaterFrontSchematic(
    BaseSweaterFrontSchematic, _GradedSchematicMixin, GradedPieceSchematic
):
    pass


class BaseVestFrontSchematic(BaseFrontPieceSchematic):
    """
    A schematic for pullover-vest fronts.
    """

    class Meta:
        abstract = True

    schematic_field_name = "vest_front"
    piece_name = "Vest Front"


class VestFrontSchematic(
    BaseVestFrontSchematic, _IndividualSchematicMixin, PieceSchematic
):
    pass


class GradedVestFrontSchematic(
    BaseVestFrontSchematic, _GradedSchematicMixin, GradedPieceSchematic
):
    pass


class BaseCardiganFrontSchematic(BaseFrontPieceSchematic):
    """
    An abstract base class for those schematics that represent cardigan-fronts:
    sleeved-cardigan fronts and cardigan-vest fronts. Note that this
    abstract base class builds on the FrontPieceSchematic abstract base
    class.

    When a method lacks a docstring, see the same-named method in
    PieceSchematic.

    Note that this model contains two ways to represent a button-band allowance:

    * A measurement in inches, held in button_band_allowance, or
    * A proportion, held jointly in button_band_allowance_percentage and
    neck_opening_width.

    Note that exactly one of these representations must hold. That is, the
    following must evaluate to True:

        all([button_band_allowance is not None,
             button_band_allowance_percentage is None,
             neck_opening_width is None])
        or
        all([button_band_allowance is None,
             button_band_allowance_percentage is not None,
             neck_opening_width is not None])
    """

    # Cardigan measurements

    button_band_allowance = LengthOffsetField(
        null=True, blank=True, help_text="Gap left between cardigan pieces (in inches)."
    )

    button_band_allowance_percentage = models.FloatField(
        blank=True,
        null=True,
        validators=[MaxValueValidator(100)],
        help_text="Gap left between cardigan pieces (as a percentage of " "neck width.",
    )

    neck_opening_width = NonNegFloatField(
        blank=True, null=True, help_text="Width of the neck opening (in inches)."
    )

    button_band_edging_height = models.FloatField(
        null=True, blank=True, help_text="Width of button-band (in inches)"
    )

    # Constants

    piece_name = "Cardigan Front"

    # subclasses should override this. Used in double_into_pullover
    corresponding_pullover_class = BaseFrontPieceSchematic

    def _adjust_width(self, width):
        """
        Helper method to adjust pullover-front widths to cardigan-side widths.
        Subtracts button-band allowance, then divided by 2.
        """
        return (width - self.button_band_allowance_inches) / 2

    def _unadjust_width(self, width):
        """
        Helper method to adjust cardigan-front widths to pullover-side widths.
        Adds button-band allowance, then multiplies by 2.
        """
        return (width * 2) + self.button_band_allowance_inches

    @property
    def button_band_allowance_inches(self):
        """
        Guaranteed to return the button-band allowance in inches, no matter
        how it is defined (button_band_allowance or
        button_band_allowance_percentage.)
        """
        if self.button_band_allowance is not None:
            bb_inches = self.button_band_allowance
        else:
            bb_inches = (
                self.neck_opening_width * self.button_band_allowance_percentage / 100
            )
        return bb_inches

    def _get_values_from_gp(self, gp):

        super(BaseCardiganFrontSchematic, self)._get_values_from_gp(gp)

        if gp.button_band_allowance is not None:
            self.button_band_allowance = gp.button_band_allowance
        else:
            self.button_band_allowance_percentage = gp.button_band_allowance_percentage
            self.neck_opening_width = gp.front_neck_opening_width

        logger.debug("gp.button_band_allowance: %s", gp.button_band_allowance)
        logger.debug(
            "gp.button_band_allowance_percentage: %s",
            gp.button_band_allowance_percentage,
        )
        logger.debug("gp.front_neck_opening_width: %s", gp.front_neck_opening_width)
        logger.debug("self.button_band_allowance: %s", self.button_band_allowance)
        logger.debug(
            "self.button_band_allowance_percentage: %s",
            self.button_band_allowance_percentage,
        )
        logger.debug("self.neck_opening_width: %s", self.neck_opening_width)

        self.button_band_edging_height = gp.button_band_edging_height

        self.hip_width = self._adjust_width(self.hip_width)
        self.bust_width = self._adjust_width(self.bust_width)
        if self.waist_width is not None:
            self.waist_width = self._adjust_width(self.waist_width)

    def double_into_pullover(self):
        """
        Returns a pullover-front schematic of the right type (sleeved or vest)
        corresponding to what the finished cardigan front would be as a pullover
        (both sides plus button-band allowance). Used in front_pieces.py to
        express cardigan-making logic in terms of (existing) pullover-making
        logic.
        """

        correct_params = [
            "shoulder_height",
            "armpit_height",
            "waist_height",
            "neck_height",
            "neckline_style",
            "below_armpit_straight",
        ]
        adjusted_params = ["hip_width", "bust_width", "waist_width"]

        pullover_params = {}
        for attr in correct_params:
            pullover_params[attr] = getattr(self, attr)
        for attr in adjusted_params:
            if getattr(self, attr) is None:
                # Waist_wdith will be None for non-hourglass silhouettes
                pullover_params[attr] = None
            else:
                pullover_params[attr] = self._unadjust_width(getattr(self, attr))

        return_me = self.corresponding_pullover_class(**pullover_params)
        return_me.spec_source = self.get_spec_source()
        return return_me

    def get_schematic_image(self):
        """
        Return a schematic image which *may* be appropriate for this piece.
        The gotcha is that the image returned will always have a neckline.
        This may not be the case for the finished garment-- the piece might
        actually go straight from cast-on to shoulder seams. Unfortunately,
        there is no way to detect this situation from the schematic alone.
        So client code should always check against the actual piece of the
        relevant Pattern: if the neckline is empty(), then use
        get_front_schematic_url() with empty=True
        """
        spec_source = self.get_spec_source()
        neckline_style = spec_source.neckline_style
        construction = self.construction

        if self.is_straight:
            silhouette = SDC.SILHOUETTE_STRAIGHT
        elif self.is_hourglass:
            silhouette = SDC.SILHOUETTE_HOURGLASS
        elif self.is_aline:
            silhouette = SDC.SILHOUETTE_ALINE
        else:
            assert self.is_tapered
            silhouette = SDC.SILHOUETTE_TAPERED

        return get_front_schematic_url(
            silhouette, neckline_style, construction, cardigan=True
        )

    def clean(self):

        errors = []

        none_list = [
            self.button_band_allowance is None,
            self.button_band_allowance_percentage is None,
            self.neck_opening_width is None,
        ]

        acceptable_combinations = [[True, False, False], [False, True, True]]

        if none_list not in acceptable_combinations:
            errors.append(
                ValidationError(
                    "A button-band allowance must be provided, "
                    "either via button_band_allowance or both "
                    "button_band_allowance_percentage and "
                    "neck_front_width (but not all three)."
                )
            )

        try:
            super(BaseCardiganFrontSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True


class BaseCardiganVestSchematic(BaseCardiganFrontSchematic):
    """
    Schematic for cardigan-vest fronts.
    """

    class Meta:
        abstract = True

    schematic_field_name = "cardigan_vest"


class CardiganVestSchematic(
    BaseCardiganVestSchematic, _IndividualSchematicMixin, PieceSchematic
):
    corresponding_pullover_class = VestFrontSchematic


class GradedCardiganVestSchematic(
    _GradedCardiganMixin,
    BaseCardiganVestSchematic,
    _GradedSchematicMixin,
    GradedPieceSchematic,
):
    corresponding_pullover_class = GradedVestFrontSchematic


class BaseCardiganSleevedSchematic(BaseCardiganFrontSchematic):
    """
    Schematic for sleeved-cardgian fronts.
    """

    class Meta:
        abstract = True

    schematic_field_name = "cardigan_sleeved"
    corresponding_pullover_class = SweaterFrontSchematic


class CardiganSleevedSchematic(
    BaseCardiganSleevedSchematic, _IndividualSchematicMixin, PieceSchematic
):
    corresponding_pullover_class = SweaterFrontSchematic


class GradedCardiganSleevedSchematic(
    _GradedCardiganMixin,
    BaseCardiganSleevedSchematic,
    _GradedSchematicMixin,
    GradedPieceSchematic,
):
    corresponding_pullover_class = GradedSweaterFrontSchematic


class BaseSleeveSchematic(models.Model):
    """
    Schematic for sleeves.
    """

    class Meta:
        abstract = True

    # Sleeve measurements
    sleeve_to_armcap_start_height = NonNegFloatField(
        null=True,
        blank=True,
        help_text="Length from sleeve cast-ons to top of armscye (in inches)",
    )

    bicep_width = NonNegFloatField(
        null=True, blank=True, help_text="Width of the sleeve at the bicep (in inches)"
    )

    sleeve_cast_on_width = NonNegFloatField(
        null=True,
        blank=True,
        help_text="Width of the sleeve at cast-on  (wherever that falls on the arm; "
        "in inches)",
    )

    schematic_field_name = "sleeve"

    piece_name = "Sleeve"

    @property
    def sleeve_edging_height(self):
        return self.get_spec_source().sleeve_edging_height

    @property
    def sleeve_edging_stitch(self):
        return self.get_spec_source().sleeve_edging_stitch

    @property
    def sleeve_allover_stitch(self):
        return self.get_spec_source().sleeve_allover_stitch

    @property
    def sleeve_cable_stitch(self):
        return self.get_spec_source().sleeve_cable_stitch

    def _get_values_from_gp(self, gp):
        self.sleeve_to_armcap_start_height = gp.sleeve_to_armcap_start_height
        self.bicep_width = gp.bicep_width
        self.sleeve_cast_on_width = gp.sleeve_cast_on_width

    def get_schematic_image(self):
        spec_source = self.get_spec_source()
        construction = spec_source.construction
        sleeve_length = spec_source.sleeve_length
        return get_sleeve_schematic_url(sleeve_length, construction)

    # def get_spec_source(self):
    #     sweater_schematic = self.sweaterschematic
    #     spec_source = sweater_schematic.get_spec_source()
    #     return spec_source

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


class SleeveSchematic(BaseSleeveSchematic, _IndividualSchematicMixin, PieceSchematic):
    pass


class GradedSleeveSchematic(
    BaseSleeveSchematic, _GradedSchematicMixin, GradedPieceSchematic
):
    pass


class BaseSweaterSchematic(models.Model):
    class Meta:
        abstract = True

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


class SweaterSchematic(BaseSweaterSchematic, ConstructionSchematic):
    """
    A container model to hold all the piece-schematics of a garment.
    Note that methods like save(), full_clean(), delete(), will recurse down
    to all contained piece-schematics in the 'right' way.
    """

    sweater_back = models.OneToOneField(
        SweaterBackSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    sweater_front = models.OneToOneField(
        SweaterFrontSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    vest_back = models.OneToOneField(
        VestBackSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    vest_front = models.OneToOneField(
        VestFrontSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    sleeve = models.OneToOneField(
        SleeveSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    cardigan_vest = models.OneToOneField(
        CardiganVestSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    cardigan_sleeved = models.OneToOneField(
        CardiganSleevedSchematic, null=True, blank=True, on_delete=models.CASCADE
    )

    @property
    def front_piece(self):
        return self.get_front_piece()

    @property
    def back_piece(self):
        return self.get_back_piece()

    @property
    def sleeve_piece(self):
        return self.get_sleeve_piece()

    def get_back_piece(self):
        if self.sweater_back:
            return self.sweater_back
        else:
            return self.vest_back

    def get_front_piece(self):
        if self.sweater_front:
            return self.sweater_front
        elif self.vest_front:
            return self.vest_front
        elif self.cardigan_sleeved:
            return self.cardigan_sleeved
        else:
            return self.cardigan_vest

    def get_sleeve_piece(self):
        return self.sleeve

    @classmethod
    def make_from_garment_parameters(cls, user, gp):
        """
        Convert a IndividualGarmentParameters instance into a new
        IndividualPiecedSchematic instance. The new instance will have been
        neither cleaned nor saved.
        """
        attributes = {"individual_garment_parameters": gp, "customized": False}

        spec_source = gp.get_spec_source()

        piece_types = [
            (spec_source.has_sweater_back(), SweaterBackSchematic, "sweater_back"),
            (spec_source.has_sweater_front(), SweaterFrontSchematic, "sweater_front"),
            (spec_source.has_vest_back(), VestBackSchematic, "vest_back"),
            (spec_source.has_vest_front(), VestFrontSchematic, "vest_front"),
            (spec_source.has_sleeves(), SleeveSchematic, "sleeve"),
            (
                spec_source.has_cardigan_sleeved(),
                CardiganSleevedSchematic,
                "cardigan_sleeved",
            ),
            (spec_source.has_cardigan_vest(), CardiganVestSchematic, "cardigan_vest"),
        ]

        for piece_needed, piece_class, attr_name in piece_types:
            if piece_needed:
                attr_value = piece_class.make_from_gp_and_container(gp)
            else:
                attr_value = None
            attributes[attr_name] = attr_value

        return cls(**attributes)

    def sub_pieces(self):
        """
        Return those piece-schematics actually contained in this
        container class.
        """
        pre_sub_pieces = [
            self.sweater_back,
            self.sweater_front,
            self.vest_back,
            self.vest_front,
            self.sleeve,
            self.cardigan_vest,
            self.cardigan_sleeved,
        ]
        return [x for x in pre_sub_pieces if x is not None]

    def clean(self):
        errors = []

        for piece in self.sub_pieces():
            try:
                piece.clean()
            except ValidationError as ve:
                errors.append(ve)

        try:
            super(SweaterSchematic, self).clean()
        except ValidationError as ve:
            errors.append(ve)

        if (self.sweater_back is None) and (self.vest_back is None):
            errors.append(
                ValidationError(
                    "Schematic needs at least one of: sweaterback, vestback"
                )
            )

        if self.sweater_back is None:
            if self.sweater_front is not None:
                errors.append(
                    ValidationError("Cannot generate sweater-front without sweaterback")
                )
            if self.cardigan_sleeved is not None:
                errors.append(
                    ValidationError(
                        "Cannot generate sleeved-cardigan front without sweaterback"
                    )
                )

        if self.vest_back is None:
            if self.vest_front is not None:
                errors.append(
                    ValidationError("Cannot generate vest-front without vest back")
                )
            if self.cardigan_vest is not None:
                errors.append(
                    ValidationError(
                        "Cannot generate cardigan-vest pieces without vest back"
                    )
                )

        back_piece = self.back_piece
        igp = self.individual_garment_parameters

        if not all(
            [
                igp.back_is_straight() == back_piece.is_straight,
                igp.back_is_tapered() == back_piece.is_tapered,
                igp.back_is_aline() == back_piece.is_aline,
                igp.back_is_hourglass() == back_piece.is_hourglass,
            ]
        ):
            errors.append(
                ValidationError(
                    "IGP and this schematic have back-pieces of different shapes"
                )
            )

        front_piece = self.front_piece
        if not all(
            [
                igp.front_is_straight() == front_piece.is_straight,
                igp.front_is_tapered() == front_piece.is_tapered,
                igp.front_is_aline() == front_piece.is_aline,
                igp.front_is_hourglass() == front_piece.is_hourglass,
            ]
        ):
            errors.append(
                ValidationError(
                    "IGP and this schematic have front-pieces of different shapes"
                )
            )

        if errors:
            raise ValidationError(errors)


class GradedSweaterSchematic(BaseSweaterSchematic, GradedConstructionSchematic):

    # required by superclass
    @classmethod
    def make_from_garment_parameters(cls, gp):
        return_me = cls(graded_garment_parameters=gp)
        return_me.save()

        spec_source = gp.get_spec_source()

        piece_types = [
            (spec_source.has_sweater_back(), GradedSweaterBackSchematic),
            (spec_source.has_sweater_front(), GradedSweaterFrontSchematic),
            (spec_source.has_vest_back(), GradedVestBackSchematic),
            (spec_source.has_vest_front(), GradedVestFrontSchematic),
            (spec_source.has_sleeves(), GradedSleeveSchematic),
            (spec_source.has_cardigan_sleeved(), GradedCardiganSleevedSchematic),
            (spec_source.has_cardigan_vest(), GradedCardiganVestSchematic),
        ]

        for gp_grade in gp.all_grades:
            for piece_needed, piece_class in piece_types:
                if piece_needed:
                    piece_class.make_from_gp_grade_and_container(
                        gp, gp_grade, return_me
                    )

        return return_me

    @property
    def sweater_back_schematics(self):
        return GradedSweaterBackSchematic.objects.filter(
            construction_schematic=self
        ).all()

    @property
    def sweater_front_schematics(self):
        return GradedSweaterFrontSchematic.objects.filter(
            construction_schematic=self
        ).all()

    @property
    def sleeve_schematics(self):
        return GradedSleeveSchematic.objects.filter(construction_schematic=self).all()

    @property
    def cardigan_sleeved_schematics(self):
        return GradedCardiganSleevedSchematic.objects.filter(
            construction_schematic=self
        ).all()

    @property
    def vest_back_schematics(self):
        return GradedVestBackSchematic.objects.filter(construction_schematic=self).all()

    @property
    def vest_front_schematics(self):
        return GradedVestFrontSchematic.objects.filter(
            construction_schematic=self
        ).all()

    @property
    def cardigan_vest_schematics(self):
        return GradedCardiganVestSchematic.objects.filter(
            construction_schematic=self
        ).all()

    def get_pieces_class(self):
        from .pieces import GradedSweaterPatternPieces

        return GradedSweaterPatternPieces


# Constraint:
# SweaterBacks all have sleeve of same grade, either sweaterfront or cardgiansleeved (consistently) of same grade
# No sleeves, sweaterfronts, cardiganfronts without sweaterback of same grade
