"""
Created: April 13 2013
"""

import logging

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from customfit.fields import (
    NonNegFloatField,
    NonNegSmallIntegerField,
    StrictPositiveSmallIntegerField,
)
from customfit.helpers.math_helpers import (
    ROUND_DOWN,
    ROUND_UP,
    _find_best_approximation,
    is_even,
    rectangle_area,
    round,
    trapezoid_area,
)
from customfit.helpers.row_parities import RS, WS, reverse_parity

from ...helpers.magic_constants import (
    BUSTTOARMPIT,
    HALFWAISTEVEN,
    MINIMUM_WAIST_STRAIGHT,
    POST_HEM_MARGIN,
)
from ...helpers.row_count_parities import parities
from .base_piece import GradedSweaterPiece, SweaterPiece

# Get an instance of a logger
logger = logging.getLogger(__name__)

parities = parities["pullover"]


class BaseHalfBodyPieceMixin(models.Model):
    """
    This model contains the fields and validation logic common to all
    half-body pieces: SweaterBack, SweaterFront, VestBack and VestFront.
    (Unclear if CardiganFront also applies.) It is intended to be an abstract
    mixin class for those models. This model does not contain the logic
    for *computing* those values, but just the fields themselves and some
    global validation logic.

    To understand this model in detail, it helps to know some of its history.
    The customfit engine was originally written exclusively to generate
    hourglass garments: garments that decrease from the hem in to the waist
    and then increase from the waist back out to the bust. One could end up
    with corner cases where garment did no decrease from hem to waist,
    or increase from waist to bust, and thus even end up with a corner case
    where the garment want straight from hem to bust! But these were
    considered corner cases that one might encounter accidentally, and not
    explicitly called out with their own representation.

    Later, we extended the engine to include garments intentionally designed
    to be:

    * A-line, meaning the garment decreases from a (larger) hem to a (smaller)
    bust at a constant rate,

    * Tapered, meaning that the garment increases from a (smaller) hem to a
    larger bust at a constant rate of increase, and

    * Straight, which means that the hem and bust are the same size and the
    garment neither decreases nor increases between.

    In making this extensions, we decided *neither* to break out these new cases
    into new classes *nor* to try to silently represent them as degenerate
    corner cases of hourglass garments. Both were possible, but with
    unacceptable costs in terms of complexity. Instead, we decided to extend
    this model with an explicit flag as to its interpretation: _hourglass or not.
    This flag would indicate which fields were to be regarded as meaningful
    and how the meaningful ones were to be interpreted. Specifically:

    * If the garment is marked with _hourglass = True, then this model has its
    original meaning. The garment can have both, one of, or neither of
    decreases from hem to waist and increases from waist to bust. Neither
    shaping is required, but any shaping that does occur will be implemented
    via 'darts'. A longer explanation is below, but the general idea is that
    stitches are added or removed via a special knitting technique in the
    middle of the fabric, and the exact location(s) of these
    increase/decreases are indicated by one, two, or three markers.

    * If the garment is marked with _hourglass = False, then it will be
    interpreted as being a 'constant rate' garment: A-line or tapered. (What
    about straight? See below.) In these garments, the adding or subtracting
    of stitches will happen on the edge of the garment, and hence the
    'marker' and 'dart' fields will be regarded as meaningless. The only
    increase/decrease field that will be regarded as meaningful will be those
    which describe either the 'standard increase' rows (for tapered) or
    'standard decrease' rows (for A-line).

    * What about straight garments? We will actually need to handle both
    kinds of representation. Since we might already have straight garments in
    the database as a corner case of hourglass, we need to continue to
    process and render those garments correctly. Thus, there is no harm in
    allowing the engine to continue to generate those corner-cases when it
    would otherwise anyway. However, we must guarantee a straight garment
    when the user explicitly requests that silhouette, and so we will go the
    easy route in those cases and represent them as 'non-hourglass' garments
    where the hem and bust have exactly the same number of stitches.

    Note that a number of this model's fields are used in both cases and
    interpreted the same way: armhole fields, for example, and the shoulders.
    For those fields that do depend on the _hourglass flag, the name and
    help_text of the field are written for the hourglass case. We will
    provide the non-hourglass interpretation in comments.



    (A short explanation of darts, for those who are interested. As
    mentioned above, the hourglass silhouette uses a special technique to
    add or remove a stitch in the middle of the fabric. It leaves a tiny
    hole, though, and it is thought most pleasing to the eye to line them up
    vertically. They pull on the fabric around them, however, and so they
    can't be placed too close to each other. So what we do depends on how
    many stitches we need to increase of decrease, and over how many rows.

    First, we try 'single darts': one vertical line of increase/decreases
    where the actual increase/decreases are placed no closer than four rows
    apart. (When we say 'one vertical line', we actually mean 'one on the
    left side and one on the right side of the piece. In all this
    explanation, we will speak in terms of only one side, but be aware that
    the described scenario is happening on both the left and the right
    symmetrically.)

    If we need to increase or decrease more than mere single darts would
    allow, we move on to 'double darts: *two* vertical lines of increases or
    decreases, where the vertical lines are interleaved. First, an increase
    or decrease in one line. Two rows later, an increase or decrease in the
    other vertical line. Then two rows later, an increase or decrease back in
    the first vertical line. And so on.

    If we need even more increases or decreases, we try our last effort:
    'triple darts'. Three vertical lines, and we have increases in decreases
    in the first and the third lines simultaneously (i.e., on the same rows).

    Note that these cases combine in some interesting ways. First we 'fill
    up' the available vertical space with single darts. Then, if we need to,
    we add double darts between the single dart rows. When doing so, we start
    adding them from the bottom, and we don't add more than we need. So yes,
    you can end up in a situation where you have double-darts between the
    bottom portion of the single-dart rows but not between the top portion.
    And if we fill up all the inter-single-dart rows with double darts and we
    still need more shaping then we start adding triple-darts to the
    single-dart rows-- again, starting at the bottom and working up to the
    top. And again, we don't add more than we need to. So, what are the valid
    combinations:

    * Single-dart rows only

    * Single-dart rows with double-darts between them at the bottom but not
    at the top.

    * Single-dart rows completely filled with double-dart rows.

    * A sequence of triple-dart rows (i.e., rows with both single and
    triple-dart shapings) followed by a sequence of single-dart rows,
    with double-dart rows between every pair, and

    * A sequence of triple-dart rows with double-darts between each
    consecutive pair.

    Pray you never need to change any of this logic.)
    """

    class Meta:
        abstract = True

    # See docstring for a longer explanation but: if this flag is true,
    # then this instance was computed for an hourglass shape. It may have ended
    # up straight, but all of the hourglass fields have been filled in with
    # legal values and it is safe to render as if it were an hourglass.
    # If this flag is False, then it should be interpreted as a constant-rate
    # garment. If there are 'bust increases', then it is a tapered garment. If
    # there are 'waist-decreases', then it is A-line. And if there are niether,
    # then it is straight.
    #
    # Note that the rest of the world should use the is_hourglass, is_straight,
    # etc. methods to determine this garment's shape.
    _hourglass = models.BooleanField(
        default=True,
        help_text="If true, the piece is to be interpreted as representing "
        "an hourglass silhouette. If not, an A-line or tapered "
        "piece. (Straight pieces can be represented either way.)",
    )

    ############################################################################
    #
    # Cast-ons
    #
    ############################################################################

    cast_ons = StrictPositiveSmallIntegerField(
        help_text="Number of stitches to cast on at the hip."
    )

    ############################################################################
    #
    # Waist decreases
    #
    ############################################################################

    # If _hourglass = False, will also represent the total number of decrease
    # rows between hem and bust for A-line garments. Will be 0 for straight
    # garments.
    num_waist_standard_decrease_rows = NonNegSmallIntegerField(
        help_text="Number of standard decrease rows needed during waist "
        "decreases that are *NOT* triple-dart rows"
    )

    # If _hourglass = False, will also represent the number of rows between
    # shaping rows for A-line garments. Will be None for straight garments.
    rows_between_waist_standard_decrease_rows = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of rows *between* two standard/triple-dart "
        "waist-decrease rows (not including the decrease rows "
        "themselves). Will be None is there are no waist-decrease "
        "repeats",
    )

    # If _hourglass is False, unused.
    num_waist_double_dart_rows = NonNegSmallIntegerField(
        help_text="Number of rows containing waist double-darts."
    )

    # If _hourglass is False, unused.
    num_waist_triple_dart_rows = NonNegSmallIntegerField(
        help_text="Number of waist decrease rows with triple darts."
    )

    # If _hourglass is False, unused.
    pre_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of cast-on stitches before the marker for standard "
        "increases and increases. Will be None if there are"
        "no waist decreases.",
    )

    # If _hourglass is False, unused.
    waist_double_dart_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of stitches (at cast-on) before first waist "
        "double-dart marker. Will be None if waist double-darts "
        "are not used.",
    )

    # If _hourglass is False, unused.
    waist_triple_dart_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of stitches (at cast-on) before first waist "
        "triple-dart marker. Will be None if waist triple-darts "
        "are not used.",
    )

    # If _hourglass is false, this is the height to begin the
    # tapered-increases or A-line decreases, whichever applies. Will be None
    # for straight garments.
    begin_decreases_height = NonNegFloatField(
        null=True,
        blank=True,
        help_text="Number of inches at which to begin the waist decreases. "
        "(Note: will be accurate even when double- or triple-darts "
        "are used.)",
    )

    # If _hourglass is false, unused.
    hem_to_waist = NonNegFloatField(
        blank=True,
        null=True,
        help_text="Number of inches from cast-on to *top* of waist, where "
        "bust shaping can begin.",
    )

    ############################################################################
    #
    # Bust increases
    #
    ############################################################################

    # If _hourglass = False, will also represent the total number of decrease
    # rows between hem and bust for A-line garments. Will be 0 for straight
    # garments.
    num_bust_standard_increase_rows = NonNegSmallIntegerField(
        help_text="Number of standard increase rows needed during bust "
        "increases. Note: does not include triple-dart rows"
    )

    # If _hourglass = False, will also represent the total number of decrease
    # rows between hem and bust for A-line garments. Will be None for
    # straight garments.
    rows_between_bust_standard_increase_rows = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of rows *between* two standard/triple-dart "
        "bust-increase rows (not including the increase rows "
        "themselves). Will be None is there are no bust-increase "
        "repeats",
    )

    # If _hourglass is False, unused.
    num_bust_double_dart_increase_rows = NonNegSmallIntegerField(
        help_text="Number of rows containing bust double-darts"
    )

    # If _hourglass is False, unused.
    num_bust_triple_dart_rows = NonNegSmallIntegerField(
        help_text="Number of times the double-dart/triple-dart combinations "
        "are repeated. Will be None if bust double-darts are not "
        "used."
    )

    # If _hourglass is False, unused.
    bust_pre_standard_dart_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of stitches (at waist) before first standard-dart "
        "marker.  Will be None if bust double-darts are not used.",
    )

    # If _hourglass is False, unused.
    bust_pre_double_dart_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of stitches (at waist) before first double-dart "
        "marker.  Will be None if bust double-darts are not used.",
    )

    # If _hourglass is False, unused.
    bust_pre_triple_dart_marker = StrictPositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Number of stitches (at waist) before first bust "
        "triple-dart marker. Will be None if bust triple-darts "
        "are not used.",
    )

    ############################################################################
    #
    # Armhole shaping
    #
    ############################################################################

    hem_to_armhole_shaping_start = NonNegFloatField(
        help_text="Number of inches from cast-on to beginning of armhole " "shaping"
    )

    armhole_x = StrictPositiveSmallIntegerField(
        help_text="Number of stitches to bind off at bottom layer of " "armhole."
    )

    armhole_y = NonNegSmallIntegerField(
        help_text="Number of stitches to bind off at second-to-bottom layer "
        "of armhole."
    )

    armhole_z = NonNegSmallIntegerField(
        help_text="Number of stitches to bind off during slope portion of " "armhole."
    )

    ############################################################################
    #
    # Necklines
    #
    ############################################################################

    # The following three fields are *jointly* needed for a generic relation to necklines
    neckline_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    neckline_object_id = models.PositiveIntegerField()
    neckline = GenericForeignKey("neckline_content_type", "neckline_object_id")

    ############################################################################
    #
    # Shoulder bind-offs
    #
    # Calculated in SweaterBack
    ############################################################################

    hem_to_shoulders = NonNegFloatField(
        help_text="Number of inches from cast-on to end of shoulders."
    )

    first_shoulder_bindoff = StrictPositiveSmallIntegerField(
        help_text="Number of stitches to bind off on the bottom layer "
        "of the two-layer shoulder bindoff."
    )

    num_shoulder_stitches = StrictPositiveSmallIntegerField(
        help_text="Number of stitches in one shoulder (between neckline " "and armhole)"
    )

    ############################################################################
    #
    # Actuals
    #
    ############################################################################

    actual_armhole_circumference = NonNegFloatField(
        help_text="Number of inches in this piece's portion of the armhole "
        "(used by Sleeve)."
    )

    ############################################################################
    #
    # End fields
    #
    ############################################################################

    def _compute_waist_and_bust_shaping(
        self, rounding_directions, ease_tolerances, graded
    ):
        if self.schematic.is_hourglass:

            return self._compute_waist_and_bust_shaping_hourglass(
                rounding_directions, ease_tolerances, graded
            )

        else:
            return self._compute_waist_and_bust_shaping_non_hourglass(
                rounding_directions, ease_tolerances
            )

    def _compute_waist_and_bust_shaping_non_hourglass(
        self, rounding_directions, ease_tolerances
    ):

        # First, clear the air by dispatching a bunch of easy-to-set fields
        self._hourglass = False
        self.num_waist_double_dart_rows = 0
        self.num_waist_triple_dart_rows = 0
        self.pre_marker = None
        self.waist_double_dart_marker = None
        self.waist_triple_dart_marker = None
        self.hem_to_waist = None
        self.num_bust_double_dart_increase_rows = 0
        self.num_bust_triple_dart_rows = 0
        self.bust_pre_standard_dart_marker = None
        self.bust_pre_double_dart_marker = None
        self.bust_pre_triple_dart_marker = None

        # So what's left?
        #
        # * cast_ons
        # * num_waist_standard_decrease_rows
        # * rows_between_waist_standard_decrease_rows
        # * begin_decreases_height
        # * num_bust_standard_increase_rows
        # * rows_between_bust_standard_increase_rows
        #
        # So, break into cases: straight, A-line, tapered. In all three cases,
        # start by computing cast-ons

        hip_width = self.schematic.hip_width
        bust_width = self.schematic.bust_width
        gauge = self.gauge
        caston_repeats = self.caston_repeats()
        if caston_repeats:
            hip_stitches = _find_best_approximation(
                hip_width,
                gauge.stitches,
                rounding_directions["cast_ons"],
                ease_tolerances["hips"],
                caston_repeats.x_mod,
                caston_repeats.mod_y,
            )

        else:
            hip_stitches = _find_best_approximation(
                hip_width,
                gauge.stitches,
                rounding_directions["cast_ons"],
                ease_tolerances["hips"],
            )

        self.parity = hip_stitches % 2

        # Now, the three cases.
        if hip_width == bust_width:
            # Straight garment. We're done.
            self.num_waist_standard_decrease_rows = 0
            self.rows_between_waist_standard_decrease_rows = None
            self.num_bust_standard_increase_rows = 0
            self.rows_between_bust_standard_increase_rows = None
            self.begin_decreases_height = None
            self.cast_ons = hip_stitches

        else:
            # Either A-line or tapered. In either case, we need to know the
            # bust-stitches-- and they must match the parity of the hip-stitches
            # and how much vertical distance we have to do our shaping

            bust_stitches = _find_best_approximation(
                bust_width,
                gauge.stitches,
                rounding_directions["bust"],
                ease_tolerances["bust"],
                self.parity,
                2,
            )
            shaping_start_height = sum(
                [self.schematic.torso_hem_height, POST_HEM_MARGIN]
            )

            # Get the user's ideal/goal length for staight-below-armhole
            # distance. This is only an attribute of the FrontPiece template, so
            # we use a default value for back pieces.
            try:
                below_armpit_straight = max(
                    [self.schematic.below_armpit_straight, BUSTTOARMPIT]
                )
            except AttributeError:
                # Piece-schematic doesn't have below_armpit_straight. Must
                # be a back piece, so use the default value from the magic
                # constants.
                below_armpit_straight = BUSTTOARMPIT

            shaping_end_height = sum(
                [self.schematic.armpit_height, -below_armpit_straight]
            )

            shaping_vertical_dist = shaping_end_height - shaping_start_height

            if hip_width > bust_width:
                # A-line
                sr = self.compute_edge_shaping(
                    hip_stitches,
                    bust_stitches,
                    shaping_vertical_dist,
                    gauge,
                    even_spacing=False,
                )

                self.num_bust_standard_increase_rows = 0
                self.rows_between_bust_standard_increase_rows = None
                self.cast_ons = hip_stitches

                self.begin_decreases_height = sum(
                    [shaping_start_height, sr.shaping_vertical_play]
                )

                self.num_waist_standard_decrease_rows = sr.num_standard_shaping_rows

                self.rows_between_waist_standard_decrease_rows = (
                    sr.rows_between_standard_shaping_rows
                )

            else:
                # Should be in tapered.
                assert bust_width > hip_width
                sr = self.compute_edge_shaping(
                    bust_stitches,
                    hip_stitches,
                    shaping_vertical_dist,
                    gauge,
                    even_spacing=False,
                )

                self.num_waist_standard_decrease_rows = 0
                self.rows_between_waist_standard_decrease_rows = None
                self.cast_ons = hip_stitches

                self.num_bust_standard_increase_rows = sr.num_standard_shaping_rows

                self.rows_between_bust_standard_increase_rows = (
                    sr.rows_between_standard_shaping_rows
                )

                self.begin_decreases_height = sum(
                    [shaping_start_height, sr.shaping_vertical_play]
                )

    def _compute_waist_and_bust_shaping_hourglass(
        self, rounding_directions, ease_tolerances, graded
    ):
        """
        Computes and sets the values associated with the waist-shaping and the
        bust-shaping. Note: these two shapings are interconnected because if
        either one cannot be achieved to the schematic's specifications, then
        the waist needs to be expanded to take up the slack. So there is some
        logic to first figure out what the waist must be, and then we compute
        the actual shaping values.
        """

        self._hourglass = True

        ###################################################################
        # First, compute the naive/ideal stitch-count for hips, bust, and waist.
        # Note: If the number of waist stitches is not larger than the number of
        # hip stitches (by at least two) then the cast-on stitches should come
        # from the waist, not the hips.
        ################################################################

        gauge = self.gauge
        hip_width = self.schematic.hip_width
        waist_width = self.schematic.waist_width
        bust_width = self.schematic.bust_width

        allow_double_darts = not graded
        allow_triple_darts = not graded

        caston_repeats = self.caston_repeats()
        if caston_repeats:
            hip_stitches = _find_best_approximation(
                hip_width,
                gauge.stitches,
                rounding_directions["cast_ons"],
                ease_tolerances["hips"],
                caston_repeats.x_mod,
                caston_repeats.mod_y,
            )

        else:
            hip_stitches = _find_best_approximation(
                hip_width,
                gauge.stitches,
                rounding_directions["cast_ons"],
                ease_tolerances["hips"],
            )

        # 0 if cast-ons are eve, 1 in off. All other stitch-counts need
        # to respect this parity
        parity = hip_stitches % 2

        # First, check for the case where the waist & hip widths are exactly
        # the same. This will occur in the front when the design specifies
        # back_waist_shaping_only
        if waist_width == hip_width:
            waist_stitches = hip_stitches
        else:
            waist_stitches = _find_best_approximation(
                waist_width,
                gauge.stitches,
                rounding_directions["waist"],
                ease_tolerances["waist"],
                parity,
                2,
            )

        if waist_stitches <= hip_stitches:
            # We can use the hip_stitch count for cast-ons
            cast_ons = hip_stitches
        else:
            # We can't have waist-stitches larger than hip stitches.
            # The default is that we expand the hip stitches to be the same
            # as the waist stitches. But there is a corner case: we're using
            # repeats. In this case, we need to make sure that the waist
            # stiches respect the repeat-requirements. So, re-compute the
            # ideal_waist_stitches to respect the repeats. This *may* jsut
            # solve the problem, so check that first (and that
            # the cast-ons and the now waist stitches have the same parity).
            # If not, set cast_ons
            # to waist stitches.

            if caston_repeats:

                waist_stitches = _find_best_approximation(
                    waist_width,
                    gauge.stitches,
                    rounding_directions["waist"],
                    ease_tolerances["waist"],
                    caston_repeats.x_mod,
                    caston_repeats.mod_y,
                )

                if (waist_stitches < hip_stitches) and (waist_stitches % 2) == (
                    hip_stitches % 2
                ):

                    cast_ons = hip_stitches

                else:
                    cast_ons = waist_stitches
            else:
                cast_ons = waist_stitches

        # And now we test again for equal widths. If the design specified
        # back_waist_shaping_only, then bust_width will be the same as
        # waist_width, and we should just use the same number of stitches
        if bust_width == waist_width:
            bust_stitches = waist_stitches
        else:
            bust_stitches = _find_best_approximation(
                bust_width,
                gauge.stitches,
                rounding_directions["bust"],
                ease_tolerances["bust"],
                parity,
                2,
            )

        ######################################################################
        # Compute the heights needed to compute shapings.
        ######################################################################

        # This next bit is confusing. The core idea is that there is an
        # ideal height for waist-decreases to start and end, and an ideal
        # place for bust-increases to end. But there are limits to how
        # quickly the piece can increase or decrease. If we can't increase
        # or decrease enough in the vertical distance allowed, then the
        # ShapingResult objects we get back will have constraints_met
        # set to False. So then we need to expand the vertical distance allowed
        # either above or below the waist. If we run out of vertical space
        # then we need to let the waist expand to the best we can actually do
        # in the vertical space we have.

        waist_height = self.schematic.waist_height
        armpit_height = self.schematic.armpit_height

        # Setting this here, so that I can call self.hem_to_waist_in_rows later
        self.hem_to_waist = waist_height + HALFWAISTEVEN

        waist_hem_height = self.schematic.torso_hem_height

        # waist-decreasing heights, in decreasing order of desirability:
        waist_shaping_vert_possibilities = [
            (waist_hem_height + POST_HEM_MARGIN, waist_height - HALFWAISTEVEN),
            (waist_hem_height, waist_height - HALFWAISTEVEN),
            (waist_hem_height, waist_height),
        ]

        if waist_hem_height > MINIMUM_WAIST_STRAIGHT:
            waist_shaping_vert_possibilities.append(
                (MINIMUM_WAIST_STRAIGHT, waist_height)
            )

        # Top-borders for bust-increase heights, in decreasing order of
        # desirability
        #
        # First, we get the user's ideal/goal length for staight-below-armhole
        # distance. This is only an attribute of the FrontPiece template, so
        # we use a default value for back pieces.
        #
        # Then, we *start* with that value but eat away at it if we can't
        # achieve the necessary bust-shaping. Specifically, we will
        # pre-compute all the possible values, starting at the goal-distance
        # and subtracting a half-inch each time. This results in the list
        # bust_shaping_vert_dists, which give all the valid vertical-distances
        # for bust-shapings in order of preference.

        try:
            below_armpit_straight = max(
                [self.schematic.below_armpit_straight, BUSTTOARMPIT]
            )
        except AttributeError:
            # Piece-schematic doesn't have below_armpit_straight. Must
            # be a back piece, so use the default value from the magic
            # constants.
            below_armpit_straight = BUSTTOARMPIT

        bust_shaping_vert_dists = []
        while below_armpit_straight >= 0:
            vert_dist = sum(
                [
                    armpit_height,
                    -(self.hem_to_waist_in_rows / self.gauge.rows),
                    -below_armpit_straight,
                    # Add in the height of one row, since
                    # the last increase row is actually included
                    # in the below_armpit_straight value
                    1 / self.gauge.rows,
                    # Why add in the next line? We were getting one of
                    # those 'length changes during the schematic loop
                    # even though the user doesn't change it' errors
                    # for below_armpit_straight, and we eventually
                    # tracked it down to here. The source of the
                    # problem is that this computation doesn't take in
                    # to account the fact that armpit_height, above, is
                    # *approximate* and will be refined to a specific
                    # row by hem_to_armhole_in_rows() once
                    # self.hem_to_armhole_shaping_start is set in
                    # Backpiece. However, that hasn't happened yet, and
                    # so we add in another two rows to account for the
                    # fact that rounding armpit_height to an integer
                    # number of rows might cause two rows's worth of
                    # rounding error here-- and thus cause the
                    # below_waist_straight to creep up during the
                    # schematic loop
                    2 / self.gauge.rows,
                ]
            )

            below_armpit_straight -= 0.5
            bust_shaping_vert_dists.append(vert_dist)

        # Now that we have the possibilities, find the best viable one (if it
        # exists). Specifically, loop until we find settings that work or
        # we run out of options
        waist_shaping = None
        bust_shaping = None
        while (
            (waist_shaping is None)
            or (bust_shaping is None)
            or (
                (not waist_shaping.constraints_met) and waist_shaping_vert_possibilities
            )
            or ((not bust_shaping.constraints_met) and bust_shaping_vert_dists)
        ):

            # First, get a new shaping result for the waist, if
            # we need it
            if (waist_shaping is None) or (
                (not waist_shaping.constraints_met) and waist_shaping_vert_possibilities
            ):

                (begin_decreases_height, top_height) = (
                    waist_shaping_vert_possibilities.pop(0)
                )

                max_waist_shaping_distance = top_height - begin_decreases_height
                if max_waist_shaping_distance < 0:
                    continue

                waist_shaping = self.compute_marker_shaping(
                    cast_ons,
                    waist_stitches,
                    max_waist_shaping_distance,
                    gauge,
                    allow_double_darts=allow_double_darts,
                    allow_triple_darts=allow_triple_darts,
                )

            else:
                # Waists must be fine, so let's move on to the bust

                max_bust_shaping_distance = bust_shaping_vert_dists.pop(0)

                bust_shaping = self.compute_marker_shaping(
                    bust_stitches,
                    waist_stitches,
                    max_bust_shaping_distance,
                    gauge,
                    allow_double_darts=allow_double_darts,
                    allow_triple_darts=allow_triple_darts,
                )

            # endif
        # endwhile

        # Now we need to check whether or not we acutally met the constraints
        # or just ran out of options. If the later, we need to let the waist
        # out to what can actually be achieved. But the wrinkle here is that
        # this is larger than either cast-ons or busts, we need to expand those
        # as well. And we need to expand those not just to match waist-stitches
        # but if the gauge uses repeats, we need to expand cast-ons to the
        # next highest repeat as well.

        if (not waist_shaping.constraints_met) or (not bust_shaping.constraints_met):

            best_waist_from_waist_shaping = (
                waist_stitches
                if waist_shaping.constraints_met
                else waist_shaping.best_smaller_stitches
            )
            best_waist_from_bust_shaping = (
                waist_stitches
                if bust_shaping.constraints_met
                else bust_shaping.best_smaller_stitches
            )

            waist_stitches = max(
                [best_waist_from_waist_shaping, best_waist_from_bust_shaping]
            )

            if waist_stitches > cast_ons:

                cast_ons = waist_stitches

                if caston_repeats:
                    cast_ons = round(
                        cast_ons, ROUND_UP, caston_repeats.mod_y, caston_repeats.x_mod
                    )

                    cast_on_parity = cast_ons % 2

                    if waist_stitches % 2 != cast_on_parity:
                        waist_stitches = round(
                            waist_stitches, ROUND_UP, 2, cast_on_parity
                        )

            if waist_stitches > bust_stitches:
                bust_stitches = waist_stitches

            waist_shaping = self.compute_marker_shaping(
                cast_ons,
                waist_stitches,
                max_waist_shaping_distance,
                gauge,
                allow_double_darts=allow_double_darts,
                allow_triple_darts=allow_triple_darts,
            )

            bust_shaping = self.compute_marker_shaping(
                bust_stitches,
                waist_stitches,
                max_bust_shaping_distance,
                gauge,
                allow_double_darts=allow_double_darts,
                allow_triple_darts=allow_triple_darts,
            )

        assert waist_shaping.constraints_met
        assert bust_shaping.constraints_met

        #####################################################################
        # Okay. Set all the values we have.
        #####################################################################

        # hem through waist
        self.cast_ons = cast_ons

        self.parity = parity

        self.begin_decreases_height = begin_decreases_height

        self.num_waist_standard_decrease_rows = waist_shaping.num_standard_shaping_rows

        self.rows_between_waist_standard_decrease_rows = (
            waist_shaping.rows_between_standard_shaping_rows
        )

        self.num_waist_double_dart_rows = waist_shaping.num_double_dart_shaping_rows

        self.num_waist_triple_dart_rows = waist_shaping.num_triple_dart_shaping_rows

        if self.num_waist_decrease_rows_knitter_instructions == 0:
            # Go straight.
            self.begin_decreases_height = None
        elif self.num_waist_decrease_rows_knitter_instructions == 1:
            # Only one decrease row. Put it at the top-- .5 below waist
            self.begin_decreases_height = waist_height - HALFWAISTEVEN
        else:
            self.begin_decreases_height = sum(
                [begin_decreases_height, waist_shaping.shaping_vertical_play]
            )

        # busts

        self.num_bust_standard_increase_rows = bust_shaping.num_standard_shaping_rows
        assert self.num_bust_standard_increase_rows is not None

        self.rows_between_bust_standard_increase_rows = (
            bust_shaping.rows_between_standard_shaping_rows
        )

        self.num_bust_double_dart_increase_rows = (
            bust_shaping.num_double_dart_shaping_rows
        )

        self.num_bust_triple_dart_rows = bust_shaping.num_triple_dart_shaping_rows

    def _compute_marker_placement(self):
        """
        Once we have shaping from cast-on through bust (inclusive)
        compute which markers are necessary, when they should be added, and
        where they should go.
        """

        # The default is that markers are not needed
        self.pre_marker = None
        self.waist_double_dart_marker = None
        self.waist_triple_dart_marker = None
        self.bust_pre_standard_dart_marker = None
        self.bust_pre_double_dart_marker = None
        self.bust_pre_triple_dart_marker = None

        # If this is not an hourglass garment, then there's nothing more to
        # do-- markers are only used in hourglass garments
        if not self._hourglass:
            return

        #######################################################################
        # Now, let's compute 'ideal' placement for all three markers at cast-on
        # and see where they end up at the waist. Note: not setting any self.*
        # values yet.
        ######################################################################

        # 'ideal' cast-on placement
        pre_marker = round(self.cast_ons * self.marker_ratio)
        waist_double_dart_marker = round(pre_marker / 2.0, ROUND_DOWN)
        waist_triple_dart_marker = round(waist_double_dart_marker / 2, ROUND_DOWN)

        # resulting waist-placements
        bust_pre_triple_dart_marker = (
            waist_triple_dart_marker - self.num_waist_triple_dart_rows
        )

        bust_pre_double_dart_marker = waist_double_dart_marker - sum(
            [self.num_waist_triple_dart_rows, self.num_waist_double_dart_rows]
        )

        bust_pre_standard_dart_marker = pre_marker - sum(
            [
                self.num_waist_triple_dart_rows,
                self.num_waist_double_dart_rows,
                self.num_waist_standard_decrease_rows,
            ]
        )

        # Now, we error-check and adjust at the waist from the inside out:

        if self.has_waist_decreases or self.has_bust_increases:
            # We need to ensure that the standard-dart marker has at least
            # two stitches when it reaches the waist.

            if bust_pre_standard_dart_marker < 2:

                bust_pre_standard_dart_marker = 2

            # Now, we check the double-darts:
            if self.waist_double_darts or self.bust_double_darts:
                # we need a double-dart. Do we need to move it in?
                if bust_pre_double_dart_marker < 2:
                    bust_pre_double_dart_marker = 2

                # Do we need to move in the standard-dart marker to make
                # room for the double-dart marker
                if (bust_pre_standard_dart_marker - bust_pre_double_dart_marker) < 2:
                    bust_pre_standard_dart_marker = bust_pre_double_dart_marker + 2

                # And now, on to the triple-dart marker:
                if self.waist_triple_darts or self.bust_triple_darts:
                    # We need a triple-dart. Do we need to move it in?
                    if bust_pre_triple_dart_marker < 2:
                        bust_pre_triple_dart_marker = 2

                    # Do we need to move in the double-dart marker to make
                    # room?
                    if (bust_pre_double_dart_marker - bust_pre_triple_dart_marker) < 2:
                        bust_pre_double_dart_marker = bust_pre_triple_dart_marker + 2

                    # And again, o we need to move in the standard-dart marker
                    # to make room for the double-dart marker?
                    if (
                        bust_pre_standard_dart_marker - bust_pre_double_dart_marker
                    ) < 2:
                        bust_pre_standard_dart_marker = bust_pre_double_dart_marker + 2

        # Okay, now let's compute any hem-cast ons that we need, and
        # set any values we need

        if self.bust_triple_darts:
            self.bust_pre_triple_dart_marker = bust_pre_triple_dart_marker

        if self.waist_triple_darts:
            self.waist_triple_dart_marker = sum(
                [bust_pre_triple_dart_marker, self.num_waist_triple_dart_rows]
            )

        if self.bust_double_darts:
            self.bust_pre_double_dart_marker = bust_pre_double_dart_marker

        if self.waist_double_darts:
            self.waist_double_dart_marker = sum(
                [
                    bust_pre_double_dart_marker,
                    self.num_waist_triple_dart_rows,
                    self.num_waist_double_dart_rows,
                ]
            )

        if self.has_bust_increases:
            self.bust_pre_standard_dart_marker = bust_pre_standard_dart_marker

        if self.has_waist_decreases:
            self.pre_marker = sum(
                [
                    bust_pre_standard_dart_marker,
                    self.num_waist_triple_dart_rows,
                    self.num_waist_double_dart_rows,
                    self.num_waist_standard_decrease_rows,
                ]
            )

        #
        # Assertions left over from old code
        #
        if self.pre_marker is not None:
            if self.pre_marker < 4:
                raise ValueError("Cast-on count too small: %d" % self.pre_marker)

        if self.waist_double_dart_marker is not None:
            assert self.waist_double_dart_marker != 0

        if all(
            [(self.pre_marker is not None), (self.waist_double_dart_marker is not None)]
        ):
            assert self.pre_marker > self.waist_double_dart_marker

        if self.waist_triple_dart_marker is not None:
            assert self.waist_triple_dart_marker != 0

        if all(
            [
                self.waist_double_dart_marker is not None,
                self.waist_triple_dart_marker is not None,
            ]
        ):
            assert self.waist_double_dart_marker > self.waist_triple_dart_marker

    def _add_cable_stitches(self):
        # adjust stitch counts to include the 'extra cable stitches'
        # To be implemented by sub-classes

        cable_extra_stitches = self._get_cable_extra_stitches()
        if cable_extra_stitches:
            self.cast_ons += cable_extra_stitches
            assert self.cast_ons > 0

    def _get_cable_extra_stitches(self):
        # Get the relevant 'extra cable' stitch count for this piece (front or back)
        # To be implemented by subclasses
        raise NotImplementedError

    # TODO: Finish writing this when more awake
    def clean(self):
        """
        This will check for consistency of the fields. Other errors dynamically
        encountered during the making of this object will be raised via
        ValueError or ValidationError exceptions.
        """
        errors = []

        #
        # Test consistency of each field, in order of definition above
        #

        # cast_ons: no tests

        # waist_hem_height: no tests

        # num_waist_standard_decrease_rows: no tests

        # rows_between_waist_standard_decrease_rows
        if (
            sum(
                [self.num_waist_standard_decrease_rows, self.num_waist_triple_dart_rows]
            )
            > 1
        ):
            x = self.rows_between_waist_standard_decrease_rows
            if not x:
                errors.append(
                    ValidationError(
                        "Invalid value for "
                        "rows_between_waist_standard_decrease_rows: %s" % x
                    )
                )

        # num_waist_double_dart_rows:
        x = self.num_waist_triple_dart_rows
        y = sum(
            [self.num_waist_standard_decrease_rows, self.num_waist_triple_dart_rows]
        )
        if (x > 0) and (y > 1):
            if self.num_waist_double_dart_rows == 0:
                errors.append(ValidationError("Missing double-darts at waist."))

        # num_waist_triple_dart_rows: no tests

        # pre_marker:
        if any(
            [
                (self.num_waist_standard_decrease_rows > 0 and self._hourglass),
                self.num_waist_double_dart_rows > 0,
                self.num_waist_triple_dart_rows > 0,
            ]
        ):
            if self.pre_marker is None:
                errors.append(ValidationError("pre_marker value missing"))

        # waist_double_dart_marker:
        if any(
            [self.num_waist_double_dart_rows > 0, self.num_waist_triple_dart_rows > 0]
        ):
            if self.waist_double_dart_marker is None:
                errors.append(ValidationError("waist_double_dart_marker value missing"))

        # waist_triple_dart_marker:
        if self.num_waist_triple_dart_rows > 0:
            if self.waist_triple_dart_marker is None:
                errors.append(ValidationError("waist_triple_dart_marker value missing"))

        # begin_decreases_height
        if any(
            [
                self.num_waist_standard_decrease_rows > 0,
                self.num_waist_double_dart_rows > 0,
                self.num_waist_triple_dart_rows > 0,
            ]
        ):
            if self.begin_decreases_height is None:
                errors.append(ValidationError("begin_decreases_height value missing"))

        # hem_to_waist: no tests

        # num_bust_standard_increase_rows: no tests

        # rows_between_bust_standard_increase_rows
        if (
            sum([self.num_bust_standard_increase_rows, self.num_bust_triple_dart_rows])
            > 1
        ):
            x = self.rows_between_bust_standard_increase_rows
            if not x:
                errors.append(
                    ValidationError(
                        "Invalid value for "
                        "rows_between_bust_standard_increase_rows: %s" % x
                    )
                )

        # num_bust_double_dart_increase_rows:
        x = self.num_bust_triple_dart_rows
        y = sum([self.num_bust_standard_increase_rows, self.num_bust_triple_dart_rows])
        if (x > 0) and (y > 1):
            if self.num_bust_double_dart_increase_rows == 0:
                errors.append(ValidationError("Missing double-darts at bust."))

        # num_bust_triple_dart_rows: no tests

        # bust_pre_standard_dart_marker
        if (
            sum(
                [
                    self.num_bust_standard_increase_rows,
                    self.num_bust_double_dart_increase_rows,
                    self.num_bust_triple_dart_rows,
                ]
            )
            > 0
        ):
            if self.pre_marker is not None:
                if self.bust_pre_standard_dart_marker is None:
                    errors.append(
                        ValidationError("Missing value: bust_pre_standard_dart_marker")
                    )

        # bust_pre_double_dart_marker
        if (
            sum(
                [
                    self.num_bust_double_dart_increase_rows,
                    self.num_bust_triple_dart_rows,
                ]
            )
            > 0
        ):
            if self.waist_double_dart_marker is not None:
                if self.bust_pre_double_dart_marker is None:
                    errors.append(
                        ValidationError("Missing value: bust_pre_double_dart_marker")
                    )

        # bust_pre_triple_dart_marker
        if self.num_bust_triple_dart_rows > 0:
            if self.waist_triple_dart_marker is not None:
                if self.bust_pre_triple_dart_marker is None:
                    errors.append(
                        ValidationError("Missing value: bust_pre_triple_dart_marker")
                    )

        # Done

        if errors:
            raise ValidationError(errors)
        else:
            self.neckline.clean()

    def clean_fields(self, exclude=None):
        if exclude is None:
            exclude_set = set()
        else:
            exclude_set = exclude

        exclude_set.add("neckline_object_id")
        self.neckline.clean_fields()
        super(BaseHalfBodyPieceMixin, self).clean_fields(exclude_set)

    def full_clean(self, *args, **kwargs):
        errors = []

        try:
            super(BaseHalfBodyPieceMixin, self).full_clean(*args, **kwargs)
        except ValidationError as ve:
            errors.append(ve)

        try:
            self.neckline.full_clean(*args, **kwargs)
        except ValidationError as ve2:
            errors.append(ve2)

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        # ensure that the generic relation to neckline is in a good state
        neckline = self.neckline
        neckline.save()
        self.neckline = neckline
        super(BaseHalfBodyPieceMixin, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.neckline.delete(*args, **kwargs)
        super(BaseHalfBodyPieceMixin, self).delete(*args, **kwargs)

    # The six properties following are to make template-logic easier.
    # Child classes should override the appropriate one.
    @property
    def is_sweater_back(self):
        return False

    @property
    def is_vest_back(self):
        return False

    @property
    def is_sweater_front(self):
        return False

    @property
    def is_vest_front(self):
        return False

    @property
    def is_cardigan_vest(self):
        return False

    @property
    def is_cardigan_sleeved(self):
        return False

    @property
    def is_straight(self):
        return not (self.has_waist_decreases or self.has_bust_increases)

    @property
    def is_hourglass(self):
        return self._hourglass and not self.is_straight

    @property
    def is_aline(self):
        return (not self._hourglass) and self.has_waist_decreases

    @property
    def is_tapered(self):
        return (not self._hourglass) and self.has_bust_increases

    @property
    def actual_hem_to_waist(self):
        return self.hem_to_waist

    @property
    def actual_hem_to_armhole(self):
        return self.hem_to_armhole_shaping_start

    @property
    def actual_hem_to_shoulder(self):
        return self.hem_to_shoulders

    @property
    def bust_use_standard_markers(self):
        return self.has_bust_increases

    @property
    def actual_waist_to_armhole(self):
        return self.actual_hem_to_armhole - self.actual_hem_to_waist

    @property
    def waist_hem_height(self):
        return self.schematic.torso_hem_height

    @property
    def post_marker(self):
        """
        Number of cast-on stitches AFTER the last marker for standard
        increases and increases
        """
        return self.pre_marker

    @property
    def inter_marker(self):
        """
        Number of stitches (at cast-on) between the two markers for standard
        increases and increases.
        """
        return self.cast_ons - self.pre_marker - self.post_marker

    @property
    def num_waist_triple_dart_repetitions(self):
        """
        Number of times the double-dart/triple-dart combinations are repeated.
        Will be None if waist triple-darts are not used.
        """
        if self.num_waist_triple_dart_rows > 0:
            return self.num_waist_triple_dart_rows - 1
        else:
            return None

    @property
    def num_waist_triple_dart_repetitions_minus_one(self):
        """
        Will be None if there are no waist triple darts, or only one
        triple-dart row.
        """
        x = self.num_waist_triple_dart_repetitions
        if x is None:
            return None
        elif x == 0:
            return None
        else:
            return x - 1

    @property
    def waist_triple_darts(self):
        """
        Will be True if waist-decreases use triple darts.
        """
        return self.num_waist_triple_dart_rows > 0

    @property
    def waist_inter_triple_marker(self):
        """
        "Number of stitches (at cast-on) between waist triple-dart marker
        and double-dart marker. Will be None if waist triple-darts are not
        used.
        """
        if self.waist_triple_dart_marker is None:
            return None
        else:
            return self.waist_double_dart_marker - self.waist_triple_dart_marker

    @property
    def waist_double_darts(self):
        """
        Will be true if waist-decreases use double darts.
        """
        return (self.num_waist_double_dart_rows > 0) or (
            self.num_waist_triple_dart_rows > 0
        )

    @property
    def num_waist_double_dart_decrease_repetitions(self):
        """
        Number of rows containing waist double-darts, minus one. Note:
        might be as many as num_waist_standard_decrease_repetitions. Will be
        None if waist double-darts are not used.
        """
        if self.num_waist_double_dart_rows > 0:
            return self.num_waist_double_dart_rows - 1
        else:
            return None

    @property
    def num_waist_non_double_dart_decrease_repetitions(self):
        """
        Number of standard decrease repetitions *without*
        double-dart rows enclosed. Will be None if waist
        double-darts are not used.
        """
        if self.num_waist_double_dart_rows == 0:
            return None
        else:
            return (
                (
                    self.num_waist_standard_decrease_rows
                    + self.num_waist_triple_dart_rows
                )
                - self.num_waist_double_dart_rows
                - 1
            )

    @property
    def num_waist_non_double_dart_decrease_repetitions_minus_one(self):
        """
        num_waist_non_double_dart_decrease_repetitions - 1. Used in the
        template. Returns None instead of a negative number/zero, or if waist
        double-darts are not used.
        """
        x = self.num_waist_non_double_dart_decrease_repetitions
        if x is None:
            return None
        if x == 0:
            return None
        return x - 1

    @property
    def waist_inter_double_marker(self):
        """
        Number of stitches (at cast-on) between double-dart marker and
        standard marker. Will return None if there are no double-darts in
        the waist decreases.
        """
        if self.waist_double_dart_marker is None:
            return None
        else:
            return self.pre_marker - self.waist_double_dart_marker

    @property
    def num_waist_decrease_rows_knitter_instructions(self):
        """
        Number of waist-decrease rows containing a standard decrease, a double-
        dart decrease, or a triple-dart decrease.
        """
        return sum(
            [
                self.num_waist_standard_decrease_rows,
                self.num_waist_double_dart_rows,
                self.num_waist_triple_dart_rows,
            ]
        )

    @property
    def num_waist_standard_decrease_repetitions(self):
        """
        Number of times a standard waist decrease-row is repeated (and so does
        not include the first such row). Will be None if there are no waist
        decreases at all.
        """
        if self.num_waist_standard_decrease_rows > 0:
            return self.num_waist_standard_decrease_rows - 1
        else:
            return None

    @property
    def rows_between_standard_waist_decrease_rows_plus_one(self):
        x = self.rows_between_waist_standard_decrease_rows
        if x is None:
            return None
        else:
            return x + 1

    @property
    def has_waist_decreases(self):
        """
        True if there are any waist decreases of any kind.
        """
        return any(
            [
                self.num_waist_standard_decrease_rows > 0,
                self.num_waist_double_dart_rows > 0,
                self.num_waist_triple_dart_rows > 0,
            ]
        )

    @property
    def any_waist_decreases_on_ws(self):
        if not self.has_waist_decreases:
            return False
        else:
            # If there are double darts, then both single/triple-dart rows and double-dart rows
            # are on RS, with a single WS row betweeen
            if self.num_waist_double_dart_rows > 0:
                return False
            else:
                # No double-dart rows, so it comes down to whether there are an even number of rows between
                # single-dart rows-- if there is more than one
                if self.num_waist_standard_decrease_repetitions == 1:
                    return False
                else:
                    return is_even(self.rows_between_waist_standard_decrease_rows)

    @property
    def bust_triple_darts(self):
        """
        Will be True if bust-increases use triple darts.
        """
        return self.num_bust_triple_dart_rows > 0

    @property
    def num_bust_triple_dart_repetitions(self):
        """
        Number of times the double-dart/triple-dart combinations are repeated.
        Will be None if bust double-darts are not used.
        """
        if self.num_bust_triple_dart_rows == 0:
            return None
        else:
            return self.num_bust_triple_dart_rows - 1

    @property
    def bust_inter_triple_dart_markers(self):
        """
        Number of stitches (at waist) between bust triple-dart markers.
        Will be None if bust triple-darts are not used.
        """
        if self.bust_pre_triple_dart_marker is None:
            return None
        else:
            return self.waist_stitches - (2 * self.bust_pre_triple_dart_marker)

    @property
    def bust_inter_double_and_triple_dart_markers(self):
        """
        Number of stitches (at waist) between bust triple-dart and double-dart
        markers. Will be None if bust triple-darts are not used.
        """
        if (self.bust_pre_double_dart_marker is None) or (
            self.bust_pre_triple_dart_marker is None
        ):
            return None
        else:
            return self.bust_pre_double_dart_marker - self.bust_pre_triple_dart_marker

    @property
    def bust_double_darts(self):
        """
        Will return true if bust-increases use double darts.
        """
        return (self.num_bust_double_dart_increase_rows > 0) or (
            self.num_bust_triple_dart_rows > 0
        )

    @property
    def bust_inter_double_dart_markers(self):
        """
        Number of stitches (at waist) between double-dart markers.  Will be None
        if bust double-darts are not used.
        """
        if self.bust_pre_double_dart_marker is None:
            return None
        else:
            return self.waist_stitches - (2 * self.bust_pre_double_dart_marker)

    @property
    def bust_inter_standard_dart_markers(self):
        """
        Number of stitches (at waist) between standard-dart markers. Will be
        None if bust double-darts are not used.
        """
        if self.bust_pre_standard_dart_marker is None:
            return None
        else:
            return self.waist_stitches - (2 * self.bust_pre_standard_dart_marker)

    @property
    def bust_inter_double_and_standard_dart_markers(self):
        """
        Number of stitches (at waist) between double-dart and standard-dart
        markers.  Will be None if bust double-darts are not used.
        """
        if (self.bust_pre_standard_dart_marker is None) or (
            self.bust_pre_double_dart_marker is None
        ):
            return None
        else:
            return self.bust_pre_standard_dart_marker - self.bust_pre_double_dart_marker

    @property
    def num_bust_non_double_dart_increase_repetitions(self):
        """
        Number of standard increase repetitions *without*
        double-dart rows enclosed. Will be None if bust
        double-darts are not used.
        """
        if self.num_bust_double_dart_increase_rows == 0:
            return None
        else:
            return (
                (self.num_bust_standard_increase_rows + self.num_bust_triple_dart_rows)
                - self.num_bust_double_dart_increase_rows
                - 1
            )

    @property
    def num_bust_non_double_dart_increase_repetitions_minus_one(self):
        """
        num_bust_non_double_dart_increase_repetitions. Used in the template.
        Will be None if bust double-darts are not used.
        """
        x = self.num_bust_non_double_dart_increase_repetitions
        if (x is None) or (x == 0):
            return None
        else:
            return x - 1

    @property
    def has_bust_increases(self):
        """
        True if there are any bust_increases of any kind.
        """
        return any(
            [
                self.num_bust_standard_increase_rows > 0,
                self.num_bust_double_dart_increase_rows > 0,
                self.num_bust_triple_dart_rows > 0,
            ]
        )

    @property
    def any_bust_increases_on_ws(self):
        if not self.has_bust_increases:
            return False
        else:
            # If there are double darts, then both single/triple-dart rows and double-dart rows
            # are on RS, with a single WS row betweeen
            if self.num_bust_double_dart_increase_rows > 0:
                return False
            else:
                # No double-dart rows, so it comes down to whether there are an even number of rows between
                # single-dart rows-- if there is more than one
                if self.num_bust_standard_increase_rows == 1:
                    return False
                else:
                    return is_even(self.rows_between_bust_standard_increase_rows)

    @property
    def num_bust_increase_rows_knitter_instructions(self):
        """
        Number of bust-increase rows containing a standard increase,
        a double-dart increase, or a triple-dart increase.
        """
        return sum(
            [
                self.num_bust_standard_increase_rows,
                self.num_bust_double_dart_increase_rows,
                self.num_bust_triple_dart_rows,
            ]
        )

    @property
    def num_bust_standard_increase_repetitions(self):
        """
        Number of times a standard bust increase-row is repeated (and so does
        not include the first such row). Will be None if there are no bust
        increases at all.")
        """
        x = self.num_bust_standard_increase_rows
        if x is None:
            return None
        if x == 0:
            return None
        return x - 1

    @property
    def rows_between_bust_standard_increase_rows_plus_one(self):
        x = self.rows_between_bust_standard_increase_rows
        if x is None:
            return None
        else:
            return x + 1

    @property
    def second_shoulder_bindoff(self):
        """
        Number of stitches to bind off on the top layer or the two-layer
        shoulder bindoff.
        """
        return self.num_shoulder_stitches - self.first_shoulder_bindoff

    @property
    def actual_armhole_depth(self):
        return self.hem_to_shoulders - self.hem_to_armhole_shaping_start

    @property
    def actual_hip(self):
        "Number of inches across cast-on."
        # Note: before computing, we need to remove the 'extra cable stitches'
        extra_cable_stitches = self._get_cable_extra_stitches()
        effective_hip_stitches = self.cast_ons - (
            extra_cable_stitches if extra_cable_stitches else 0
        )
        return effective_hip_stitches / self.gauge.stitches

    @property
    def waist_stitches(self):
        "Number of stitches at the waist."
        return self.cast_ons - sum(
            [
                2 * self.num_waist_standard_decrease_rows,
                2 * self.num_waist_double_dart_rows,
                4 * self.num_waist_triple_dart_rows,
            ]
        )

    @property
    def actual_waist(self):
        """
        Will be None for non-hourglass garments (straight, tapered, a-line)
        """
        if self.is_hourglass:
            # Note: before computing, we need to remove the 'extra cable stitches'
            extra_cable_stitches = self._get_cable_extra_stitches()
            effective_waist_stitches = self.waist_stitches - (
                extra_cable_stitches if extra_cable_stitches else 0
            )
            return effective_waist_stitches / self.gauge.stitches
        else:
            return None

    @property
    def hem_to_bust_increase_end(self):
        """
        Inches from hem to last bust-increase row (inclusive). Will be None
        if there are no bust increases or the garment is not hourglass.
        """
        if self.is_hourglass and self.has_bust_increases:
            increase_repetitions = (
                self.num_bust_standard_increase_rows
                + self.num_bust_triple_dart_rows
                - 1
            )

            increase_rows = 1
            rows_between = self.rows_between_bust_standard_increase_rows
            if rows_between is not None:
                increase_rows += (rows_between + 1) * increase_repetitions
            increase_height = increase_rows / self.gauge.rows
            return increase_height + self.hem_to_waist
        else:
            return None

    @property
    def hem_to_last_torso_shaping_row(self):
        """
        Inches from cast-on to the last torso shaping row. Which row is this?
        Depends on the silhouette:

        * Straight: undefined, so this method returns None.

        * Hourglass: the last bust-increase row, if there is one, or the last
        waist-decrease row otherwise.

        * A-line: the last decrease row.

        * Tapered: the last increasr row.

        Why do we need this? To tell if necklines go down below it and
        (for example) whether the bust-stitch count is well-defined for the
        patterntext.
        """

        if self.is_straight:
            return None
        elif self.is_hourglass:
            if self.has_bust_increases:
                return self.hem_to_bust_increase_end
            else:
                # Must be waist decreases, else we would be in the 'straight'
                # branch
                return self.last_decrease_row / self.gauge.rows
        elif self.is_aline:
            return self.last_decrease_row / self.gauge.rows
        else:
            assert self.is_tapered
            return self.last_increase_row / self.gauge.rows

    @property
    def actual_shoulder_stitch_width(self):
        """
        Number of inches across a shoulder (between armhole and neckline).
        Use this when you need to display shoulder_width.
        """
        return self.num_shoulder_stitches / self.gauge.stitches

    @property
    def hem_to_neckline_shaping_start(self):
        "Number of inches from cast-on to beginning of neckline shaping."
        if self.neckline.total_depth() is not None:
            return self.hem_to_shoulders - self.neckline.total_depth()
        else:
            return None

    @property
    def hem_to_neckline_shaping_end(self):
        "Number of inches from cast-on to end of neckline shaping."
        if self.neckline.depth_to_shaping_end() is not None:
            return self.hem_to_shoulders - self.neckline.depth_to_shaping_end()
        else:
            return None

    def rows_in_armhole_shaping_pullover(self, pre_armhole_parity):
        # Rows in shaping for 'pullover' instructions (pullover garment, armholes start below
        # neckline). Note: includes initial shaping/bindoff row, last shaping/bindoff row, and all
        # rows in between. But does not include any following 'work even' rows.

        return_me = 0

        # Vest-armholes are shaped differently than sleeved-garment armholes, so we break this into
        # two cases.
        if self.is_vest_front or self.is_vest_back:

            return_me += 2  # initial bindoff rows
            return_me += self.armhole_y if self.armhole_y else 0

            # Did we just finish a RS row? if so, and there are armhole_z rows,
            # we need to skip a WS row before first armhole_z (RS) row
            if self.armhole_z:
                if return_me % 2 == 0:
                    row_just_finished_parity = pre_armhole_parity
                else:
                    row_just_finished_parity = reverse_parity(pre_armhole_parity)

                if row_just_finished_parity == RS:
                    return_me += 1  # skip WS row before armhole z

                return_me += (
                    self.armhole_z * 2
                ) - 1  # subtract off last 'work even' row

        else:
            return_me += 2  # initial bindoff rows
            return_me += 2 if self.armhole_y else 0  # second bindoff rows
            # Did we just finish a RS row? If so, and there are armhole_z rows,
            # we need to skip a WS for before the first RS armhole_z row.
            if self.armhole_z:
                if (return_me % 2) == 0:
                    row_just_finished_parity = pre_armhole_parity
                else:
                    row_just_finished_parity = reverse_parity(pre_armhole_parity)

                if row_just_finished_parity == RS:
                    return_me += 1  # skip a WS row to get first armhole_z (RS) row

                return_me += (self.armhole_z * 2) - 1  # skip last 'work even' row

        return return_me

    def rows_in_armhole_shaping_cardigan(self, pre_armhole_parity):
        # Rows in shaping for 'cardigan' instructions (cardigan garment OR pullover garment where
        # armholes start above neckline). Note: includes initial shaping/bindoff row,
        # last shaping/bindoff row, and all rows in between. But does not include any
        # following 'work even' rows. Note: unlike rows_in_armhole_shaping_pullover, this
        # method can be called for both cardigans and pullovers (where the armhole starts
        # after the neckline)

        return_me = 0

        # Vest-armholes are shaped differently than sleeved-garment armholes, so we break this into
        # two cases.
        if self.is_vest_front or self.is_vest_back or self.is_cardigan_vest:

            return_me += 1  # initial bindoff rows
            if self.armhole_y:
                return_me += self.armhole_y
                # Did we just finish a RS row? if so, and there are armhole_z rows,
                # we need to skip a WS row before first armhole_z (RS) row
                if return_me % 2 == 0:
                    row_just_finished_parity = pre_armhole_parity
                else:
                    row_just_finished_parity = reverse_parity(pre_armhole_parity)

                if (row_just_finished_parity == RS) and self.armhole_z:
                    return_me += 1  # skip WS row before armhole z

                if self.armhole_z:
                    return_me += (
                        self.armhole_z * 2
                    ) - 1  # subtract off last 'work even' row

        else:
            return_me += 1  # initial bindoff row
            if self.armhole_y or self.armhole_z:
                return_me += 1  # 'work even row

            if self.armhole_y:
                return_me += 1  # second bind-off row

            # Did we just finish a RS row? If so, and there are armhole_z rows,
            # we need to skip a WS row before first armhole_z (RS) row
            if return_me % 2 == 0:
                row_just_finished_parity = pre_armhole_parity
            else:
                row_just_finished_parity = reverse_parity(pre_armhole_parity)

            if (row_just_finished_parity == RS) and self.armhole_z:
                return_me += 1  # skip WS row before armhole z

            if self.armhole_z:
                return_me += (self.armhole_z * 2) - 1

        return return_me

    def rows_in_shoulder_shaping(self):
        # Note: this really is a constant given how the template is written
        return 3

    @property
    def _bust_stitches_internal_use(self):
        """
        Number of stitches after bust increases. Note: IS DEFINED EVEN IF
        NECKLINES GO LOWER THAN BUST STITCHES.
        """
        increase_stitches = sum(
            [
                2 * self.num_bust_standard_increase_rows,
                2 * self.num_bust_double_dart_increase_rows,
                4 * self.num_bust_triple_dart_rows,
            ]
        )
        return self.waist_stitches + increase_stitches

    @property
    def bust_stitches(self):
        """
        Number of stitches after bust increases or non-hourglass shaping.
        """
        if all(
            [
                self.hem_to_neckline_shaping_start is not None,
                self.hem_to_last_torso_shaping_row is not None,
            ]
        ):
            if self.hem_to_neckline_shaping_start < self.hem_to_last_torso_shaping_row:
                return None
        return self._bust_stitches_internal_use

    @property
    def actual_bust(self):
        """
        Number of inches across bustline.
        """
        # Note: before computing, we need to remove the 'extra cable stitches'
        extra_cable_stitches = self._get_cable_extra_stitches()
        effective_bust_stitches = self._bust_stitches_internal_use - (
            extra_cable_stitches if extra_cable_stitches else 0
        )
        return effective_bust_stitches / self.gauge.stitches

    @property
    def armhole_n(self):
        return sum([self.armhole_x, self.armhole_y, self.armhole_z])

    @property
    def hem_stitch(self):
        return self.schematic.hem_stitch

    def hem_stitch_patterntext(self):
        """
        REturns the patterntext-appropriate name for the hem-stitch.
        """
        return self.hem_stitch.patterntext

    ####################################################################
    #
    # Row-counts for heights
    #
    # We will often want templates to process the logic "If it makes sense
    # to display this count, display it. Otherwise, don't." In this context
    # 'makes sense' means 'is defined and is not negative.' To keep templates
    # simple, we will make these methods return an int if they make sense to
    # display and None otherwise. Then templates can be kept simple:
    #
    #  {% if piece.row_count_method %}
    #      Blah blah blah {{ piece.row_count_method }}.
    #  {% endif %}

    @property
    def waist_hem_height_in_rows(self):
        """
        Returns row-count of last WS row in waist hem. Always defined and
        well-formed for display.
        """
        return self._height_to_row_count(
            self.waist_hem_height, parities["waist_hem_height"]
        )

    @property
    def begin_decreases_height_in_rows(self):
        """
        Returns row-count of WS row before first decrease row. Returns None
        if no decrease rows.
        """
        if self.has_waist_decreases:
            return self._height_to_row_count(
                self.begin_decreases_height, parities["begin_decreases_height"]
            )
        else:
            return None

    @property
    def decrease_marker_placement_height_in_rows(self):
        """
        Returns row-count of RS row before decrease marker-placement row (which is also the row
        before the first waist decrease row). Returns None if no decrease rows.
        """
        if self.begin_decreases_height_in_rows is not None:
            return self.begin_decreases_height_in_rows - 1
        else:
            return None

    @property
    def begin_increases_height_in_rows(self):
        """
        Returns row-count of row before first decrease row. Returns None
        if no decrease rows.
        """
        if self._first_increase_row is None:
            return None
        else:
            return self._first_increase_row - 1

    @property
    def hem_to_waist_in_rows(self):
        """
        Returns row-count of last WS row at the top of the waist-straight.
        That is, the last WS row before the first bust-shaping row, if there
        is bust-shaping. Will be None for A-line and tapered. Will not be none
        for hourglass. May be none for straight (depending on whether it was
        meant to be hourglass or not.)
        """

        if self._hourglass:
            return self._height_to_row_count(
                self.hem_to_waist, parities["hem_to_waist"]
            )
        else:
            return None

    ###################################################
    # Helper functions for later *_in_rows properties

    @property
    def _first_decrease_row(self):
        """
        Note: row-count of the first decrease row itself. Will be None if
        there are no decrease rows
        """
        if self.has_waist_decreases:
            return self.begin_decreases_height_in_rows + 1
        else:
            return None

    def _rows_in_decreases(self):
        """
        Note: includes both first *and* last decrease. Will be zero if there
        are no decreases.
        """
        if not self.has_waist_decreases:
            return 0
        else:
            decrease_repetitions = (
                sum(
                    [
                        self.num_waist_standard_decrease_rows,
                        self.num_waist_triple_dart_rows,
                    ]
                )
                - 1
            )

            assert decrease_repetitions >= 0
            if self.rows_between_waist_standard_decrease_rows:
                rows_in_decrease = 1 + (
                    decrease_repetitions
                    * (self.rows_between_waist_standard_decrease_rows + 1)
                )
            else:
                rows_in_decrease = 1

            return int(rows_in_decrease)

    @property
    def last_decrease_row(self):
        """
        Note: row-count of last decrease-row itself. Will be None if there
        are no decrease, and will be the same as _first_decrease_row if
        there is only one increase.
        """
        if self.has_waist_decreases:
            return self._first_decrease_row + self._rows_in_decreases() - 1
        else:
            return None

    @property
    def _first_increase_row(self):
        """
        Note: row-count of the first increase_row itself. Will be None if
        there are no bust increases.
        """
        if self.has_bust_increases:
            if self.is_hourglass:
                return self.hem_to_waist_in_rows + 1
            else:
                assert self.is_tapered
                return self._height_to_row_count(
                    self.begin_decreases_height, parities["begin_decreases_height"]
                )
        else:
            return None

    def _rows_in_increases(self):
        """
        Note: includes both first and last increase row. Will be zero
        if there are no bust increases.
        """
        if not self.has_bust_increases:
            return 0
        else:
            repetitions = (
                sum(
                    [
                        self.num_bust_standard_increase_rows,
                        self.num_bust_triple_dart_rows,
                    ]
                )
                - 1
            )

            assert repetitions >= 0
            if self.rows_between_bust_standard_increase_rows:
                rows = 1 + (
                    repetitions * (self.rows_between_bust_standard_increase_rows + 1)
                )
            else:
                rows = 1
            return int(rows)

    @property
    def last_increase_row(self):
        """
        Note: Will be none if there are no increase, and will be the same
        as _first_increase_row if there is only once increase.
        """
        if self.has_bust_increases:
            return self._first_increase_row + self._rows_in_increases() - 1
        else:
            return None

    def _find_first_row_count(self, sided_row_count_method):
        """
        Helper function to find the 'first' row-count: the smaller of the
        RS row-count and the WS-row count. If either side has a row-count
        of None, will return None.
        """
        rs_side = sided_row_count_method(RS)
        ws_side = sided_row_count_method(WS)

        if None in [rs_side, ws_side]:
            return None
        else:
            return min(rs_side, ws_side)

    #################################
    # More 'real' properties. These properties, however, depend on the parity
    # of one or more rows.

    @property
    def last_decrease_to_waist_in_rows(self):
        """
        Includes the rows between last decrease and first increase,
        including the first but not the second. Will be None if there are no
        waist-decreases or the garment is not hourglass
        """
        if self.is_hourglass and self.has_waist_decreases:
            return self.hem_to_waist_in_rows - self.last_decrease_row + 1
        else:
            return None

    def hem_to_neckline_in_rows(self, pre_neckline_row_parity):
        """
        Returns the row-count of the row BEFORE the first neckline-row given
        that it has the given parity. Always defined.
        """
        return self._height_to_row_count(
            self.hem_to_neckline_shaping_start, pre_neckline_row_parity
        )

    def last_increase_to_neckline_in_rows(self, pre_neckline_row_parity):
        """
        Returns the number of rows between the last increase row and the first
        row of actual neckline shaping, including the first but not the second.
        Will be positive integer or None.
        """
        if self.has_bust_increases:
            val = (
                self.hem_to_neckline_in_rows(pre_neckline_row_parity)
                - self.last_increase_row
                + 1
            )
            if val >= 1:
                return val
            else:
                return None
        else:
            return None

    def last_decrease_to_neckline_in_rows(self, pre_neckline_row_parity):
        """
        Returns the number of rows between the last decrease row and the first
        row of actual neckline shaping, including the first but not the second.
        Will be None if no decreases or neckline is below last decrease
        """
        if self.has_waist_decreases:
            count = (
                self.hem_to_neckline_in_rows(pre_neckline_row_parity)
                - self.last_decrease_row
                + 1
            )
            if count < 1:
                return None
            else:
                return count
        else:
            return None

    def hem_to_armhole_in_rows(self, pre_armhole_parity):
        """
        Returns the row-count of the row just before the armhole-shaping.
        Always defined.
        """
        ### For pullovers, if armholes are below necklines, then armhol
        ### bindoffs should start on a RS row. So, we need to make sure
        ### that this method orders the sides in the right way.
        ### It will affect cardigans, too, but that's okay and it's better
        ### to just keep things simple.
        assert pre_armhole_parity in [RS, WS]
        if pre_armhole_parity == RS:
            return self.hem_to_armhole_in_rows(WS) + 1
        else:
            return self._height_to_row_count(
                self.hem_to_armhole_shaping_start, pre_armhole_parity
            )

    @property
    def hem_to_first_armhole_in_rows(self):
        """
        Returns the row-count of the row just before the *first* armhole
        shaping. Always defined.
        """
        return self._find_first_row_count(self.hem_to_armhole_in_rows)

    def last_increase_to_armhole_in_rows(self, pre_armhole_parity):
        """
        Number of rows between last increase row and armhole bindoff-row
        including the first but not the second. Will be None if no increases.
        """
        if self.last_increase_row:
            return (
                self.hem_to_armhole_in_rows(pre_armhole_parity)
                - self.last_increase_row
                + 1
            )
        else:
            return None

    @property
    def last_increase_to_first_armhole_in_rows(self):
        """
        Number of rows between last increase row and first
        armhole bind-off row, excluding both of those rows. Will be None
        if there are no increases.
        """
        return self._find_first_row_count(self.last_increase_to_armhole_in_rows)

    def last_decrease_to_armhole_in_rows(self, pre_armhole_parity):
        """
        Number of rows between last decrease row and armhole bindoff-row
        including the first but not the second. Will be None if no decreases.
        """
        if self.last_decrease_row:
            return (
                self.hem_to_armhole_in_rows(pre_armhole_parity)
                - self.last_decrease_row
                + 1
            )
        else:
            return None

    @property
    def last_decrease_to_first_armhole_in_rows(self):
        """
        Number of rows between last decrease and first armhole bind-off
        row, incuding the first but not the second. Will be None if there
        are no decreases.
        """
        return self._find_first_row_count(self.last_decrease_to_armhole_in_rows)

    def hem_to_shoulders_in_rows(self, pre_shoulder_parity):
        """
        Row-count of row *before* first shoulder bindoffs.
        """
        return self._height_to_row_count(self.hem_to_shoulders, pre_shoulder_parity)

    ###########################################
    # Great. And now more 'real' methods.

    def neckline_to_armhole_in_rows(self, pre_neckline_parity, pre_armhole_parity):
        """
        Number of rows between first neckline shaping row and first
        armhole bindoff row on the given side, including the first.
        but not the secondWill be either a positive
        integer or None.
        """
        count = self.hem_to_armhole_in_rows(
            pre_armhole_parity
        ) - self.hem_to_neckline_in_rows(pre_neckline_parity)
        if count >= 1:
            return count
        else:
            return None

    def armhole_to_neckline_in_rows(self, pre_armhole_parity, pre_neckline_parity):
        """
        Number of rows between beginning of FIRST armhole bindoff row on the given side and
        beginning of first neckline shaping. Will be either a positive integer or None.
        """
        count = self.hem_to_neckline_in_rows(
            pre_neckline_parity
        ) - self.hem_to_armhole_in_rows(pre_armhole_parity)
        if count >= 1:
            return count
        else:
            return None

    def last_armhole_to_neckline_in_rows(self, pre_armhole_parity, pre_neckline_parity):
        """
        Number of rows between *beginning of* LAST armhole decrease row and *beginning of*
        first neckline shaping. Should be the case that this is the same on both sides.
        Will be either a positive integer or None.
        """
        if (
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
                    -self.rows_in_armhole_shaping_pullover(pre_armhole_parity),
                    1,  # just subtracted last shaping row, need to add it back in
                ]
            )

            return count if count > 1 else None

    def first_armhole_to_neckline_in_rows(self, pre_neckline_parity):
        """
        Number of rows between first armhole bindoff on either side and
        first neckline shaping, including first but not second.
        Will be either a positive integer, or None.
        """
        neckline = self.hem_to_neckline_in_rows(pre_neckline_parity)
        armhole = self.hem_to_first_armhole_in_rows
        count = neckline - armhole
        if count >= 1:
            return count
        else:
            return None

    def armhole_to_shoulders_in_rows(self, pre_armhole_parity, pre_shoulder_parity):
        """
        Number of rows between first armhole bindoff row on the given side and
        first neckline shaping. Will be either a positive integer or None.
        """
        count = self.hem_to_shoulders_in_rows(
            pre_shoulder_parity
        ) - self.hem_to_armhole_in_rows(pre_armhole_parity)
        if count >= 1:
            return count
        else:
            return None

    def last_armhole_to_shoulders_in_rows(
        self, pre_armhole_parity, pre_shoulder_parity
    ):
        """
        Number of rows between last armhole decrease row on the given side and
        first neckline shaping. Will be either a positive integer or None.
        """
        if (
            self.armhole_to_shoulders_in_rows(pre_armhole_parity, pre_shoulder_parity)
            is None
        ):
            return None
        else:
            # If neckline starts below armholes, use cardigan row-count computation
            if self.hem_to_neckline_shaping_start < self.hem_to_armhole_shaping_start:

                count = sum(
                    [
                        self.armhole_to_shoulders_in_rows(
                            pre_armhole_parity, pre_shoulder_parity
                        ),
                        -self.rows_in_armhole_shaping_cardigan(pre_armhole_parity),
                    ]
                )
            else:
                # neckline starts above armholes in a non-cardigan piece. Use pullover counts
                count = sum(
                    [
                        self.armhole_to_shoulders_in_rows(
                            pre_armhole_parity, pre_shoulder_parity
                        ),
                        -self.rows_in_armhole_shaping_pullover(pre_armhole_parity),
                    ]
                )
            if count >= 1:
                return count
            else:
                return None

    def caston_repeats(self):
        """
        Return the repeat requirements for the waist castons. Note:
        should be overriden by subclasses.
        """
        raise NotImplementedError

    # Used to compute yardage requirements of a pattern
    def area(self):
        """
        Returns 'yardage' area of body piece (roughly) in square inches. What do we
        mean by 'yardage' area? the area computation relevant to yardage estimation:
        the area that the piece would have if the cable-stitches were knit
        the same way as every other stitch. This will be different than the actual
        area of the piece as the cable stitches don't actually change the real area of the
        piece, but we can't ignore those stitches in our yardage estimator.

        Note: this method can slightly
        underestimate the area: it ignores any waist-shaping and pretends
        that the garment goes from cast-on to bust-width via a constant rate
        of shaping. But given that this method is only used (currently) for
        estimating yardage, this approach has been deemed acceptable. First,
        the error is probably negligible. Second, the error is in the 'safe'
        direction. By *overestimating* the area of the piece, the error could
        cause knitters to buy too much yarn and not too little. (And knitters
        would rather end up with an extra hank of yarn than buy too few hanks
        and need to try to scramble for one more hank in the same dye-lot.)
        """

        # Note: we can't simply use self.actual_hip or self.actual_bust, since those
        # ignore cable stiches. We need to re-compute them with the stitches taken
        # into account
        stitch_gauge = self.gauge.stitches
        yardage_hip_width = self.cast_ons / stitch_gauge
        yardage_bust_width = self._bust_stitches_internal_use / stitch_gauge

        # Break into two rectangles: below armholes and above armholes.

        below_armhole_area = trapezoid_area(
            yardage_hip_width, yardage_bust_width, self.actual_hem_to_armhole
        )

        # Above armhole-- first compute area ignoring neckline,
        # then subtract neckline
        above_armhole_width_stitches = self._bust_stitches_internal_use - (
            2 * self.armhole_n
        )
        above_armhole_width = above_armhole_width_stitches / self.gauge.stitches
        above_armhole_area = rectangle_area(
            above_armhole_width, self.actual_armhole_depth
        )

        above_armhole_area -= self.neckline.area()

        return sum([below_armhole_area, above_armhole_area])

    @property
    def actual_last_increase_to_first_armhole(self):
        """
        Number of inches between last increase and first armhole bind-off
        row, including the first but not the second. Will be None if there
        are no decreases. Used in the schematic loop to set a
        FrontPieceSchematic's below_armpit_straight.
        """

        if self.last_increase_to_first_armhole_in_rows:
            return self.last_increase_to_first_armhole_in_rows / self.gauge.rows
        else:
            return None

    @property
    def actual_neck_opening_width(self):

        # Note: in Cardigans, this is different than the neckline's
        # stitches_across_neckline

        actual_neck_stitches = sum(
            [
                self._bust_stitches_internal_use,
                -2 * self.armhole_n,
                -2 * self.num_shoulder_stitches,
            ]
        )
        # need to remove cable stitches before converting to inches
        cable_stitches = self._get_cable_extra_stitches()
        effective_neck_stitches = actual_neck_stitches - (
            cable_stitches if cable_stitches else 0
        )

        return effective_neck_stitches / self.gauge.stitches

    def get_spec_source(self):
        return self.schematic.get_spec_source()

    def get_design(self):
        """
        Do Not Use. Returns the original patternspec for this pattern. Present only
        to maintain backwards compatibility with templates in the database.
        """
        spec_source = self.get_spec_source()
        original_patternspec = spec_source.get_original_patternspec()
        return original_patternspec


class HalfBodyPieceMixin(BaseHalfBodyPieceMixin, SweaterPiece):
    pass


class GradedHalfBodyPieceMixin(BaseHalfBodyPieceMixin, GradedSweaterPiece):
    class Meta:
        abstract = True

    @property
    def finished_full_bust(self):
        return self.sort_key
