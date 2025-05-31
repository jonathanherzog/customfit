"""
Created on Jun 23, 2012
"""

import logging

from django.core.exceptions import ValidationError
from django.db import models

from customfit.helpers.math_helpers import ROUND_UP, _find_best_approximation, round

from ...helpers.magic_constants import FRONTMARKERRATIO
from ..patternspec import SweaterPatternSpec
from ..schematics import (
    CardiganSleevedSchematic,
    CardiganVestSchematic,
    GradedCardiganSleevedSchematic,
    GradedCardiganVestSchematic,
    GradedSweaterFrontSchematic,
    GradedVestFrontSchematic,
    SweaterFrontSchematic,
    VestFrontSchematic,
)
from .finishing import ButtonBand, VNeckButtonBand
from .half_body_piece_mixin import GradedHalfBodyPieceMixin, HalfBodyPieceMixin

# Get an instance of a logger
logger = logging.getLogger(__name__)


class BaseFrontPiece(models.Model):
    """
    Abstract base class containing fields and logic common to all front-
    pieces: sweaterfront, vestfront, and cardigan fronts. Note that
    cardgian fronts include second abstract base class (CardgianFront) which
    builds on this one.
    """

    class Meta:
        abstract = True

    def side_one_name(self):
        return "Right"

    def side_two_name(self):
        return "Left"

    def _inner_make(self, back_piece, rounding_directions, ease_tolerances, graded):
        sf_rounding_directions = rounding_directions["sweater_front"]
        self._compute_values(
            back_piece, sf_rounding_directions, ease_tolerances, graded
        )

    def _compute_values(self, back_piece, rounding_directions, ease_tolerances, graded):
        """
        Internal function used to calcuate all number of the piece from inputs.
        Simply calls other _compute_* functions to do the real work.
        """
        self._compute_set_up(rounding_directions, ease_tolerances)

        self._copy_values_from_backpiece(back_piece)

        self._compute_waist_and_bust_shaping(
            rounding_directions, ease_tolerances, graded
        )

        self._compute_marker_placement()

        self._add_cable_stitches()

        self._compute_neckline_and_shoulders(
            back_piece, rounding_directions, ease_tolerances
        )

    def _compute_set_up(self, rounding_directions, ease_tolerances):
        """
        Sets the ratio governing the location at which standard
        increase/decrease markers will be set.

        Not used by SweaterBack, as it uses a different ratio.
        """
        self.marker_ratio = FRONTMARKERRATIO

    def _copy_values_from_backpiece(self, backpiece):
        """
        Copy over those values from the back-piece which must
        absolutely, positively be the same in this piece.
        """
        attrs_to_copy = [
            "armhole_x",
            "armhole_y",
            "armhole_z",
            "first_shoulder_bindoff",
            "num_shoulder_stitches",
            "actual_armhole_circumference",
            "hem_to_armhole_shaping_start",
            "hem_to_shoulders",
            "_hourglass",
        ]
        for attr in attrs_to_copy:
            setattr(self, attr, getattr(backpiece, attr))

    def _compute_neckline_and_shoulders(self, sb, rounding_directions, ease_tolerances):
        """
        Compute fields for neckline and shoulders.
        """
        # Shoulders
        self.num_shoulder_stitches = sb.num_shoulder_stitches
        self.first_shoulder_bindoff = sb.first_shoulder_bindoff
        self.hem_to_shoulders = self.schematic.shoulder_height
        neck_depth_goal = self.hem_to_shoulders - self.schematic.neck_height

        neckline_stitches = (
            self._bust_stitches_internal_use
            - (2 * self.num_shoulder_stitches)
            - (2 * self.armhole_n)
        )

        neckline_style = self.schematic.neckline_style
        neckline_class = SweaterPatternSpec.get_neckline_class(neckline_style)

        self.neckline = neckline_class.make(
            neckline_stitches,
            neck_depth_goal,
            self.gauge,
            rounding_directions,
            ease_tolerances,
        )

    def _get_cable_extra_stitches(self):
        return self.get_spec_source().front_cable_extra_stitches

    @property
    def allover_stitch(self):
        return self.get_spec_source().front_allover_stitch

    def caston_repeats(self):
        """
        Return the caston repeat requirements for the waist caston.
        """
        return self.get_spec_source().front_repeats()

    @property
    def _cross_chest_stitches_internal_use(self):
        """
        Number of stitches after armhole shaping. Note: IS DEFINED EVEN IF
        NECKLINES GO LOWER THAN ARMHOLE.
        """
        return self._bust_stitches_internal_use - (2 * self.armhole_n)

    @property
    def cross_chest_stitches(self):
        """
        Number of stitches after bust increases. Note: is None if the
        neckline goes below the armhole
        """
        # Note: this is a field in back pieces but a model here. Why? It has to
        # do with the differences between the two models. For back pieces, we
        # don't need to worry about necklines going below armhole shaping, but
        # we do need to ensure that cross-chest stitches respect repeats. So for
        # back-pieces, it makes sense to compute the chest- stitches first and
        # let the armhole stitches be derived from that (and the bust stitches).
        # For front-pieces, however, those pesky necklines can go below
        # armholes-- and so cross-chest stitches might be None (which we want to
        # explicitly prohibit for back pieces) Also, front pieces must have the
        # same armhole shaping as back pieces, so it makes sense for front-
        # pieces to derive cross-chest stitches from the (predetermined) bust
        # stitches and the (predetermined) armhole shaping.
        if all(
            [
                self.hem_to_armhole_shaping_start is not None,
                self.hem_to_neckline_shaping_start is not None,
            ]
        ):
            if self.hem_to_neckline_shaping_start < self.hem_to_armhole_shaping_start:
                return None
        return self._cross_chest_stitches_internal_use


class FrontPiece(BaseFrontPiece, HalfBodyPieceMixin):
    pass


class GradedFrontPiece(BaseFrontPiece, GradedHalfBodyPieceMixin):
    class Meta:
        abstract = True


class BaseSweaterFrontMixin(object):

    @property
    def is_sweater_front(self):
        return True


class SweaterFront(BaseSweaterFrontMixin, FrontPiece):
    """
    Concrete model for pullover-sleeved fronts.
    """

    _pattern_field_name = "sweater_front"
    schematic = models.OneToOneField(SweaterFrontSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(sweaterback, swatch, schematic, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a SweaterFront instance. Note that returned
        object will not have been saved. It will, however, already have had
        full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.
        """
        p = SweaterFront()
        p.schematic = schematic
        p.swatch = swatch
        p._inner_make(sweaterback, rounding_directions, ease_tolerances, graded=False)
        return p


class GradedSweaterFront(BaseSweaterFrontMixin, GradedFrontPiece):

    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(
        GradedSweaterFrontSchematic, on_delete=models.CASCADE
    )

    @staticmethod
    def make(schematic, sweaterback, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a SweaterFront instance. Note that returned
        object will not have been saved. It will, however, already have had
        full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.
        """

        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ

        p = GradedSweaterFront()
        p.schematic = schematic
        p.graded_pattern_pieces = sweaterback.graded_pattern_pieces
        p._inner_make(sweaterback, rounding_directions, ease_tolerances, graded=True)
        return p


class BaseVestFrontMixin(object):

    @property
    def is_vest_front(self):
        return True


class VestFront(BaseVestFrontMixin, FrontPiece):
    """
    Concrete model for pullover-vest fronts.
    """

    _pattern_field_name = "vest_front"
    schematic = models.OneToOneField(VestFrontSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(vestback, swatch, schematic, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a VestFront instance. Note that returned
        object will not have been saved. It will, however, already have had
        full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.
        """
        p = VestFront()
        p.schematic = schematic
        p.swatch = swatch
        p._inner_make(vestback, rounding_directions, ease_tolerances, graded=False)
        return p


class GradedVestFront(BaseVestFrontMixin, GradedFrontPiece):

    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(GradedVestFrontSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(schematic, vestback, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a SweaterFront instance. Note that returned
        object will not have been saved. It will, however, already have had
        full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.
        """

        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ

        p = GradedVestFront()
        p.schematic = schematic
        p.graded_pattern_pieces = vestback.graded_pattern_pieces
        p._inner_make(vestback, rounding_directions, ease_tolerances, graded=True)
        return p


class BaseCardigan(models.Model):
    """
    Abstract base class for cardigan-fronts. Builds on the FrontPiece abstract
    base class, but:

    * Adds fields for the button-band, and

    * Interfaces between the schematic for a cardigan front (which describes
    only one side) and the front-piece shaping logic (which expects to be
    dealing with a pullover piece).
    """

    class Meta:
        abstract = True

    actual_button_band_stitches = models.SmallIntegerField(
        help_text="Negative means sides overlap"
    )

    def _get_cable_extra_stitches(self):
        # Note: this is the number of extra stitches we need to add to *each side*
        extra_stitches = self.get_spec_source().front_cable_extra_stitches
        return extra_stitches

    @property
    def actual_neck_opening_width(self):

        # Note: in Cardigans, this is different than the neckline's
        # stitches_across_neckline
        actual_neck_stitches = sum(
            [self.actual_button_band_stitches, self.neckline.stitches_across_neckline()]
        )
        # We need to remove cable stitches before converting to inches. But we
        # need to double it so that we get both cables -- one on each side.
        cable_stitches = self._get_cable_extra_stitches()
        effective_neck_stitches = actual_neck_stitches - (
            cable_stitches * 2 if cable_stitches else 0
        )
        return effective_neck_stitches / self.gauge.stitches

    def _cut_halfbody_piece_in_half(
        self, halfbody_piece, rounding_directions, ease_tolerances
    ):
        """
        Derive cardigan-piece values by cutting a half-body piece in half
        (minus the button-band)
        """
        gauge = halfbody_piece.gauge
        rounding_directions = rounding_directions["cardigan_front"]
        repeats = self.caston_repeats()

        # To cut sf in half, we need to figure out the band's width. The
        # tricky part is when the user wants repeats... Note that all of the
        # calls to halfbody_piece are to 'actual_*'. This is so that we don't
        # need to worry about whether the halfbody_piece has 'extra stitches'
        # for cables that might skew our computations.
        if self.schematic.button_band_allowance is not None:
            # Button-band expressed in absolute terms.

            goal_cast_on_width = (
                halfbody_piece.actual_hip - self.schematic.button_band_allowance
            ) / 2.0

            if repeats is not None:

                self.cast_ons = _find_best_approximation(
                    goal_cast_on_width,
                    gauge.stitches,
                    ROUND_UP,
                    ease_tolerances["waist"],
                    repeats.x_mod,
                    repeats.mod_y,
                )

            else:
                self.cast_ons = round(goal_cast_on_width * gauge.stitches, ROUND_UP)
        else:
            # Button-band allowance expressed as a percentage

            bb_length = (
                halfbody_piece.actual_neck_opening_width
                * self.schematic.button_band_allowance_percentage
                / 100.0
            )

            goal_cast_on_length = (halfbody_piece.actual_hip - bb_length) / 2
            goal_cast_ons = goal_cast_on_length * gauge.stitches

            if repeats is not None:
                self.cast_ons = round(
                    goal_cast_ons, ROUND_UP, repeats.mod_y, repeats.x_mod
                )
            else:
                self.cast_ons = round(goal_cast_ons, ROUND_UP)

        # Now, unfortunately, we need to consider the possibility that the
        # halfbody_piece.cast_ons value has 'extra' cable stitches include in
        # it. We need to subtract them out before we go further
        hbp_cable_extra_stitches = halfbody_piece._get_cable_extra_stitches()
        hbp_real_castons = halfbody_piece.cast_ons - (
            hbp_cable_extra_stitches if hbp_cable_extra_stitches else 0
        )

        self.actual_button_band_stitches = hbp_real_castons - (2 * self.cast_ons)

        # Now add extra stitches to cardigan, if there are extra stitches for a
        # cable.
        extra_stitches = self._get_cable_extra_stitches()
        self.cast_ons += extra_stitches if extra_stitches is not None else 0

        for attribute in self.unadjusted_attrs:
            setattr(self, attribute, getattr(halfbody_piece, attribute))

        # Re-compute necklines based on new stitch-counts.
        # Note: now that self.cast_ons have been adjusted, self.bust_stitches
        # is magically adjusted as well.
        neckline_stitches = (
            self._bust_stitches_internal_use
            - self.num_shoulder_stitches
            - halfbody_piece.armhole_n
        ) * 2

        neckline_style = self.schematic.neckline_style
        neckline_class = SweaterPatternSpec.get_neckline_class(neckline_style)
        depth_goal = self.schematic.shoulder_height - self.schematic.neck_height
        self.neckline = neckline_class.make(
            neckline_stitches,
            depth_goal,
            self.gauge,
            rounding_directions,
            ease_tolerances,
        )

    @property
    def inter_marker(self):
        """
        Return number of stitches between waist standard-dart marker and
        button-band edge. Will be None if standard-dart markers are not used.
        """
        if self.pre_marker is None:
            return None
        else:
            return self.cast_ons - self.pre_marker

    @property
    def bust_inter_standard_dart_markers(self):
        """
        Number of stitches (at waist) between standard-dart marker and
        button-band edge. Will be None if bust double-darts are not used.
        """
        if self.bust_pre_standard_dart_marker is None:
            return None
        else:
            return self.waist_stitches - self.bust_pre_standard_dart_marker

    @property
    def bust_inter_double_dart_markers(self):
        """
        Return number of stitches between waist double-dart marker and
        button-band edge. Will be None if bust double-dart markers are not used.
        """
        if self.bust_pre_double_dart_marker is None:
            return None
        else:
            return self.waist_stitches - self.bust_pre_double_dart_marker

    @property
    def bust_inter_triple_dart_markers(self):
        """
        Return number of stitches between waist triple-dart marker and
        button-band edge. Will be None if bust triple-dart markers are not used.
        """
        if self.bust_pre_triple_dart_marker is None:
            return None
        else:
            return self.waist_stitches - self.bust_pre_triple_dart_marker

    @property
    def waist_stitches(self):
        # This should only be defined for hourglass garments
        if not self.is_hourglass:
            return None
        else:
            return self.cast_ons - sum(
                [
                    self.num_waist_standard_decrease_rows,
                    self.num_waist_double_dart_rows,
                    2 * self.num_waist_triple_dart_rows,
                ]
            )

    @property
    def _bust_stitches_internal_use(self):
        return sum(
            [
                self.cast_ons,
                -self.num_waist_standard_decrease_rows,
                -self.num_waist_double_dart_rows,
                -2 * self.num_waist_triple_dart_rows,
                self.num_bust_standard_increase_rows,
                self.num_bust_double_dart_increase_rows,
                2 * self.num_bust_triple_dart_rows,
            ]
        )

    @property
    def _cross_chest_stitches_internal_use(self):
        # Note: this is used by cross_chest_stitches() in FrontPiece
        return self._bust_stitches_internal_use - self.armhole_n

    @property
    def actual_button_band_allowance(self):
        return self.actual_button_band_stitches / self.gauge.stitches

    @property
    def actual_button_band_height(self):
        band_to_fill_gap = self.get_spec_source().button_band_to_fill_allowance()
        if band_to_fill_gap:
            return self.actual_button_band_allowance
        else:
            return self.get_spec_source().button_band_edging_height

    # used to estimate yardage requirements of pattern
    def area(self):
        """
        Returns 'yardage' area of BOTH sides combined, in square inches.
        What is 'yardage' area? The area the piece would have if all the 'extra'
        cable stitches were width-producing.
        """
        # Break into two rectangles: below armholes and above armholes.

        # Note: Can't use self.actual_hip, self.actual_waist directly here.
        # If there are 'extra' stitches for the cable, we need to be sure to
        # add them to the area, and those two properties don't.

        cable_stitches = self._get_cable_extra_stitches()
        cable_stitches = 0 if cable_stitches is None else cable_stitches
        # Since _get_cable_extra_stitches() doubles the extra-stitch count
        # when computing the underlying hald-body piece, we need to halve it
        # here to get the per-side extra-stitch count.
        cable_stitches = cable_stitches / 2

        effective_hip_width = (self.cast_ons - cable_stitches) / self.gauge.stitches
        effective_bust_width = (
            self._bust_stitches_internal_use - cable_stitches
        ) / self.gauge.stitches

        rectangle1_height = self.actual_hem_to_armhole
        rectangle1_width = (effective_bust_width + effective_hip_width) / 2
        rectangle1_area = rectangle1_height * rectangle1_width

        rectangle2_height = self.actual_armhole_depth
        rectangle2_width_stitches = self._bust_stitches_internal_use - self.armhole_n
        rectangle2_width = rectangle2_width_stitches / self.gauge.stitches
        rectangle2_area = rectangle2_height * rectangle2_width

        return 2 * (rectangle1_area + rectangle2_area)

    def make_buttonband(self):
        pattern_spec = self.get_spec_source()
        if self.neckline.empty():
            length = self.hem_to_shoulders
        else:
            length = self.hem_to_neckline_shaping_start
        bb = ButtonBand(
            pattern_spec.button_band_edging_height,
            length,
            pattern_spec.button_band_edging_stitch,
            self.gauge,
            pattern_spec.number_of_buttons,
        )
        return bb

    def make_veeneck_buttonband(self, neckline_pickup_stitches):
        pattern_spec = self.get_spec_source()
        if self.neckline.empty():
            length = self.hem_to_shoulders
        else:
            length = self.hem_to_neckline_shaping_start
        bb = VNeckButtonBand(
            pattern_spec.button_band_edging_height,
            length,
            pattern_spec.button_band_edging_stitch,
            self.gauge,
            pattern_spec.number_of_buttons,
            neckline_pickup_stitches,
        )
        return bb

    @property
    def actual_hip(self):
        "Number of inches across cast-on."
        # Note: before computing, we need to remove the 'extra cable stitches'.
        extra_cable_stitches = self._get_cable_extra_stitches()
        extra_cable_stitches = extra_cable_stitches if extra_cable_stitches else 0
        effective_hip_stitches = self.cast_ons - extra_cable_stitches
        return effective_hip_stitches / self.gauge.stitches

    @property
    def actual_waist(self):
        "Number of inches across waist. Only defined for hourglass pieces"
        # Note: before computing, we need to remove the 'extra cable stitches'.
        if self.is_hourglass:
            extra_cable_stitches = self._get_cable_extra_stitches()
            extra_cable_stitches = extra_cable_stitches if extra_cable_stitches else 0
            effective_waist_stitches = self.waist_stitches - extra_cable_stitches
            return effective_waist_stitches / self.gauge.stitches
        else:
            return None

    @property
    def actual_bust(self):
        "Number of inches across bust."
        # Note: before computing, we need to remove the 'extra cable stitches'.
        extra_cable_stitches = self._get_cable_extra_stitches()
        extra_cable_stitches = extra_cable_stitches if extra_cable_stitches else 0
        effective_bust_stitches = (
            self._bust_stitches_internal_use - extra_cable_stitches
        )
        return effective_bust_stitches / self.gauge.stitches

    @property
    def total_front_finished_hip(self):
        """
        Returns the hip-width across the ENTIRE FRONT: both sides, plus
        button band.
        """
        pspec = self.get_spec_source()
        if pspec.number_of_buttons:
            x = pspec.button_band_edging_height
        else:
            # find actual button_band allowance
            x = self.actual_button_band_allowance
        return_me = sum([2 * self.actual_hip, x])
        return return_me

    @property
    def total_front_finished_waist(self):
        """
        Returns the waist-width across the ENTIRE FRONT: both sides, plus
        button band.
        """
        if self.actual_waist is None:
            return None
        pspec = self.get_spec_source()
        if pspec.number_of_buttons:
            x = pspec.button_band_edging_height
        else:
            # find actual button_band allowance
            x = self.actual_button_band_allowance
        return_me = sum([2 * self.actual_waist, x])
        return return_me

    @property
    def total_front_finished_bust(self):
        """
        Returns the bust-width across the ENTIRE FRONT: both sides, plus X where
            IF there are buttons in the design, X = trim height.
            IF there are NO buttons in the design, X = the allowance.
        """
        pspec = self.get_spec_source()
        if pspec.number_of_buttons:
            x = pspec.button_band_edging_height
        else:
            # find actual button_band allowance
            x = self.actual_button_band_allowance
        total_bust = self.actual_bust + self.actual_bust + x
        return total_bust

    @property
    def total_front_cast_ons(self):
        """
        Return the total number of cast-on stitches (across both pieces)
        required for seamless construction.
        """
        return 2 * self.cast_ons

    def total_neckline_stitches_to_pick_up(self):
        """
        Return the total number of neckline stitches, across both pieces.
        """
        return self.neckline.stitches_to_pick_up()

    def last_armhole_to_shoulders_in_rows(
        self, pre_armhole_parity, pre_shoulder_parity
    ):
        """
        Number of rows between last armhole decrease row and
        first neckline shaping. Will be either a positive integer or None.
        """
        if (
            self.armhole_to_shoulders_in_rows(pre_armhole_parity, pre_shoulder_parity)
            is None
        ):
            return None
        else:
            count = sum(
                [
                    self.armhole_to_shoulders_in_rows(
                        pre_shoulder_parity, pre_shoulder_parity
                    ),
                    -self.rows_in_armhole_shaping_cardigan(pre_armhole_parity),
                ]
            )
            if count >= 1:
                return count
            else:
                return None

    def rows_in_armhole_shaping_pullover(self, pre_armhole_parity):
        # Shadowing the HBPM method as it should not be called on cardigans
        raise NotImplementedError

    def last_armhole_to_neckline_in_rows(self, pre_armhole_parity, pre_neckline_parity):
        """
        Number of rows between *beginning of* last armhole decrease row and *beginning of*
        first neckline shaping. Will be either a positive integer or None.
        """
        if self.neckline.empty():
            return None
        elif (
            self.armhole_to_neckline_in_rows(pre_armhole_parity, pre_neckline_parity)
            is None
        ):
            return None
        else:
            count = sum(
                [
                    self.armhole_to_neckline_in_rows(
                        pre_armhole_parity, pre_neckline_parity
                    ),
                    -self.rows_in_armhole_shaping_cardigan(pre_armhole_parity),
                    1,  # just subtracted last shaping row, need to add it back in
                ]
            )

            return count if count >= 1 else None


class Cardigan(BaseCardigan, FrontPiece):
    # A number of attributes just get copied over:
    unadjusted_attrs = [
        "swatch",
        "_hourglass",
        "num_waist_standard_decrease_rows",
        "rows_between_waist_standard_decrease_rows",
        "num_waist_double_dart_rows",
        "num_waist_triple_dart_rows",
        "pre_marker",
        "waist_double_dart_marker",
        "waist_triple_dart_marker",
        "begin_decreases_height",
        "hem_to_waist",
        "num_bust_standard_increase_rows",
        "rows_between_bust_standard_increase_rows",
        "num_bust_double_dart_increase_rows",
        "num_bust_triple_dart_rows",
        "bust_pre_standard_dart_marker",
        "bust_pre_double_dart_marker",
        "bust_pre_triple_dart_marker",
        "hem_to_armhole_shaping_start",
        "armhole_x",
        "armhole_y",
        "armhole_z",
        "hem_to_shoulders",
        "first_shoulder_bindoff",
        "num_shoulder_stitches",
        "actual_armhole_circumference",
    ]


class GradedCardigan(BaseCardigan, GradedFrontPiece):

    # A number of attributes just get copied over:
    unadjusted_attrs = [
        "_hourglass",
        "num_waist_standard_decrease_rows",
        "rows_between_waist_standard_decrease_rows",
        "num_waist_double_dart_rows",
        "num_waist_triple_dart_rows",
        "pre_marker",
        "waist_double_dart_marker",
        "waist_triple_dart_marker",
        "begin_decreases_height",
        "hem_to_waist",
        "num_bust_standard_increase_rows",
        "rows_between_bust_standard_increase_rows",
        "num_bust_double_dart_increase_rows",
        "num_bust_triple_dart_rows",
        "bust_pre_standard_dart_marker",
        "bust_pre_double_dart_marker",
        "bust_pre_triple_dart_marker",
        "hem_to_armhole_shaping_start",
        "armhole_x",
        "armhole_y",
        "armhole_z",
        "hem_to_shoulders",
        "first_shoulder_bindoff",
        "num_shoulder_stitches",
        "actual_armhole_circumference",
    ]

    @property
    def finished_full_bust(self):
        return self.sort_kery


class BaseCardiganVest(models.Model):
    class Meta:
        abstract = True

    @property
    def is_cardigan_vest(self):
        return True


class CardiganVest(BaseCardiganVest, Cardigan):
    _pattern_field_name = "cardigan_vest"

    schematic = models.OneToOneField(CardiganVestSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(back_piece, swatch, schematic, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a VestFront instance based on high-level
        input. Note that returned object will not have been saved. It will,
        however, already have had full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.

        """
        # Note: the general approach here is to make a fake pullover schematic,
        # make a fake pullover piece from it, and then to cut the pullover
        # in half (minus button-band) to make a cardigan piece.

        pullover_schematic = schematic.double_into_pullover()
        sf = VestFront.make(
            back_piece, swatch, pullover_schematic, rounding_directions, ease_tolerances
        )

        p = CardiganVest()
        p.schematic = schematic
        p._cut_halfbody_piece_in_half(sf, rounding_directions, ease_tolerances)
        return p


class GradedCardiganVest(BaseCardiganVest, GradedCardigan):
    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(
        GradedCardiganVestSchematic, on_delete=models.CASCADE
    )

    @staticmethod
    def make(schematic, back_piece, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a VestFront instance based on high-level
        input. Note that returned object will not have been saved. It will,
        however, already have had full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.

        """
        # Note: the general approach here is to make a fake pullover schematic,
        # make a fake pullover piece from it, and then to cut the pullover
        # in half (minus button-band) to make a cardigan piece.

        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ

        pullover_schematic = schematic.double_into_pullover()
        sf = GradedVestFront.make(
            pullover_schematic, back_piece, rounding_directions, ease_tolerances
        )

        p = GradedCardiganVest()
        p.schematic = schematic
        p.graded_pattern_pieces = back_piece.graded_pattern_pieces
        p._cut_halfbody_piece_in_half(sf, rounding_directions, ease_tolerances)
        return p


class BaseCardiganSleeved(models.Model):

    class Meta:
        abstract = True

    @property
    def is_cardigan_sleeved(self):
        return True


class CardiganSleeved(BaseCardiganSleeved, Cardigan):
    _pattern_field_name = "cardigan_sleeved"

    schematic = models.OneToOneField(CardiganSleevedSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(sweaterback, swatch, schematic, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a VestFront instance based on high-level
        input. Note that returned object will not have been saved. It will,
        however, already have had full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.

        :type schematic: GarmentParameters
        """
        # Note: the general approach here is to make a fake pullover schematic,
        # make a fake pullover piece from it, and then to cut the pullover
        # in half (minus button-band) to make a cardigan piece.

        pullover_schematic = schematic.double_into_pullover()
        sf = SweaterFront.make(
            sweaterback,
            swatch,
            pullover_schematic,
            rounding_directions,
            ease_tolerances,
        )

        p = CardiganSleeved()
        p.schematic = schematic
        p._cut_halfbody_piece_in_half(sf, rounding_directions, ease_tolerances)
        return p


class GradedCardiganSleeved(BaseCardiganSleeved, GradedCardigan):
    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(
        GradedCardiganSleevedSchematic, on_delete=models.CASCADE
    )

    @staticmethod
    def make(schematic, sweaterback, rounding_directions, ease_tolerances):
        """
        Makes, validates and returns a VestFront instance based on high-level
        input. Note that returned object will not have been saved. It will,
        however, already have had full_clean called on it.

        Will raise ValidationError or ValueError if errors occur.

        :type schematic: GarmentParameters
        """
        # Note: the general approach here is to make a fake pullover schematic,
        # make a fake pullover piece from it, and then to cut the pullover
        # in half (minus button-band) to make a cardigan piece.

        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ

        pullover_schematic = schematic.double_into_pullover()
        sf = GradedSweaterFront.make(
            pullover_schematic, sweaterback, rounding_directions, ease_tolerances
        )

        p = GradedCardiganSleeved()
        p.schematic = schematic
        p.graded_pattern_pieces = sweaterback.graded_pattern_pieces
        p._cut_halfbody_piece_in_half(sf, rounding_directions, ease_tolerances)
        return p
