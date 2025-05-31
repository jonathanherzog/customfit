"""
Created on Jun 23, 2012
"""

import collections
import logging

from django.core.exceptions import ValidationError
from django.db import models

from customfit.fields import (
    LengthField,
    NonNegFloatField,
    NonNegSmallIntegerField,
    StrictPositiveSmallIntegerField,
)
from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    _find_best_approximation,
    is_even,
    rectangle_area,
    round,
    trapezoid_area,
)
from customfit.helpers.row_parities import RS

from ...helpers import row_count_parities as RCP
from ...helpers.magic_constants import (
    ARMSCYE_C_RATIO,
    ARMSCYE_D_RATIO,
    DROP_SHOULDER_BICEP_TOLERANCE,
    MAX_ARMSCYE_Y,
    MAX_INCHES_BETWEEN_SLEEVE_SHAPING_ROWS,
    MINIMUM_WRIST_EDGING_HEIGHT,
)
from ...helpers.secret_sauce import (
    maximum_sleeve_straights_below_cap,
    minimum_sleeve_straights_below_cap,
)
from ..schematics import GradedSleeveSchematic, SleeveSchematic
from .base_piece import GradedSweaterPiece, SweaterPiece

# Get an instance of a logger
logger = logging.getLogger(__name__)

parities = RCP.parities["sleeve"]

# TODO: arm-top 'slack' (vert distance before shaping) should be .5 in for ball/tapered short/elbow sleeves, 2 in for everything else
# TODO: for tapered sleeves, check that there is enough vertical distance between arm-top slack and hem for 1 row per 2 stitches to reduce


#
#
# The arm-cap shaping logic appears at the top level so that it can be shared between Sleeve and
# the armcap-shaping calculator in knitting_calculators.
#
#


ArmcapShapingResult = collections.namedtuple(
    "ArmcapShapingResult",
    [
        "armscye_x",
        "armscye_y",
        "six_count_beads",
        "four_count_beads",
        "two_count_beads",
        "one_count_beads",
        "armscye_c",
        "armscye_d",
    ],
)


def _bead_game(
    gauge,
    bicep_stitches,
    original_armscye_x,
    original_armscye_y,
    original_armscye_d,
    armscye_c_targets,
    armscye_circumference_inches,
):

    armscye_x = original_armscye_x
    armscye_y = original_armscye_y
    armscye_d = original_armscye_d

    armscye_y_size_adjustment = 0

    solution_found = False

    while not solution_found:

        # This calculation of armscye_c is just an approximation. Actual
        # value is what remains after armscyeE is set
        armscye_c = (armscye_c_targets * gauge.stitches) - armscye_y_size_adjustment

        # There's a corner case where armscye_c is not big enough, and
        # there are not enough armscye_e_rows for all the
        # armscye_e_stitches. So, let's check and adjust if necessary

        armscye_c_big_enough = False
        while not armscye_c_big_enough:

            # might not be an integer.
            armscye_e_stitches = (
                bicep_stitches
                - sum([armscye_x * 2, armscye_y * 2, armscye_c, armscye_d * 4])
            ) / 2

            armscye_e_stitches = round(armscye_e_stitches, ROUND_UP)

            # Now we can set armscye_c to the remaining stitches
            armscye_c = bicep_stitches - sum(
                [armscye_x * 2, armscye_y * 2, armscye_e_stitches * 2, armscye_d * 4]
            )
            perimiter_so_far = (
                sum([armscye_x * 2, armscye_y * 2, armscye_c, armscye_d * 4])
                / gauge.stitches
            )
            armscye_e_hypetenuse_inches = (
                armscye_circumference_inches - perimiter_so_far
            ) / 2

            armscye_e_rows = (armscye_e_hypetenuse_inches**2) - (
                (armscye_e_stitches / float(gauge.stitches)) ** 2
            )

            armscye_e_rows = armscye_e_rows**0.5
            armscye_e_rows = armscye_e_rows * gauge.rows
            armscye_e_rows = round(armscye_e_rows, ROUND_DOWN, 2)

            if armscye_e_stitches <= armscye_e_rows:
                armscye_c_big_enough = True
            else:
                armscye_c += 2

        # Okay, now we play the bead game. We need to add armscye_e_stitches
        # stitches, over armscye_e_rows rows. (The number of rows should be
        # even.) Decreses to come in the following order:
        #
        # 1) zero or more 'decrease every 6 rows',
        # 2) zero or one 'decrease every 4th row',
        # 3) zero or more 'decrease every other row', and
        # 4) zero or more 'decrease every row'.
        #
        # Furthermore, she'd like as many 'every other row' as possible. To
        # find a solution, imagine every stitch-decrease is a bead on a
        # wire. At the beginning, they are all on the left, representing an
        # 'every row' decrease. We add up the number of rows this
        # represents. If this isn't enough, we move one bead from the 'every
        # row' slot into the 'every other row' slot. If that's still not
        # enough, we keep moving the beads, but we change it up a little. We
        # move one bead from the 'every other row' slot into the 'every 4th
        # row' slot . Still not enough? We move *the same bead* again to the
        # right, representing 'every 6th row'. Still not enough? Do it again
        # with the next bead. Keep going until you get enough rows, or move
        # all the beads over (which is an error).

        one_count_beads = armscye_e_stitches
        two_count_beads = 0
        four_count_beads = 0
        six_count_beads = 0

        while True:

            # Okay, have we found a solution?
            current_row_count = sum(
                [
                    one_count_beads,
                    two_count_beads * 2,
                    four_count_beads * 4,
                    six_count_beads * 6,
                ]
            )

            if current_row_count == armscye_e_rows:
                solution_found = True
                break  # inner while
            if not any(
                [one_count_beads > 0, two_count_beads > 0, four_count_beads == 1]
            ):
                break
            # There is a bead to move. Move it
            if one_count_beads > 0:
                one_count_beads -= 1
                two_count_beads += 1
            elif four_count_beads == 1:
                four_count_beads = 0
                six_count_beads += 1
            else:
                two_count_beads -= 1
                four_count_beads = 1

        # Okay, either we found a solution, or we didn't. IF we found
        # a solution, all is well. The outer while loop will terminate.
        # at the end of this loop.
        #
        # If we didn't find a solution, check armscye_y for slack. If
        # there is some there, use it and do another loop of the outer
        # while loop. Otherwise, give up

        if not solution_found:
            if (armscye_y < 2) and (armscye_y_size_adjustment / gauge.stitches > 2):
                break  # outer while
            else:
                if armscye_y >= 2:
                    armscye_y -= 2
                else:
                    armscye_y = original_armscye_y
                    armscye_y_size_adjustment += 2

    # end of outer while loop
    assert solution_found

    return_me = (
        armscye_c,
        armscye_y,
        one_count_beads,
        two_count_beads,
        four_count_beads,
        six_count_beads,
    )

    return return_me


def compute_armcap_shaping(
    gauge, armhole_x, armhole_y, armhole_circumference, bicep_stitches
):

    bicep_width = bicep_stitches / gauge.stitches
    armscye_c_targets = ARMSCYE_C_RATIO * bicep_width
    armscye_d_targets = ARMSCYE_D_RATIO * bicep_width

    armscye_d = round(armscye_d_targets * gauge.stitches, ROUND_DOWN)
    if armscye_d < 1:
        armscye_d = 1

    max_armscye_y_stitches = MAX_ARMSCYE_Y * gauge.stitches

    armscye_y = min([max_armscye_y_stitches, armhole_y])
    armscye_y = round(armscye_y, ROUND_DOWN)
    armscye_x = armhole_x

    (
        armscye_c,
        armscye_y,
        one_count_beads,
        two_count_beads,
        four_count_beads,
        six_count_beads,
    ) = _bead_game(
        gauge,
        bicep_stitches,
        armscye_x,
        armscye_y,
        armscye_d,
        armscye_c_targets,
        armhole_circumference,
    )

    result = ArmcapShapingResult(
        armscye_x,
        armscye_y,
        six_count_beads,
        four_count_beads,
        two_count_beads,
        one_count_beads,
        armscye_c,
        armscye_d,
    )

    return result


#
# And now the Sleeve class
#


class _BaseSleeve(models.Model):
    class Meta:
        abstract = True

    cast_ons = StrictPositiveSmallIntegerField()

    num_sleeve_increase_rows = StrictPositiveSmallIntegerField(
        help_text="Not needed for straight sleeves.", null=True, blank=True
    )

    inter_sleeve_increase_rows = NonNegSmallIntegerField(
        help_text="Not needed for straight sleeves.", null=True, blank=True
    )

    num_sleeve_compound_increase_rows = NonNegSmallIntegerField(
        help_text="Not needed for straight sleeves.", null=True, blank=True
    )

    rows_after_compound_shaping_rows = NonNegSmallIntegerField(
        help_text="Not needed for straight sleeves.", null=True, blank=True
    )

    bicep_stitches = StrictPositiveSmallIntegerField()

    armscye_x = NonNegSmallIntegerField()

    armscye_y = NonNegSmallIntegerField()

    six_count_beads = NonNegSmallIntegerField()

    four_count_beads = NonNegSmallIntegerField()

    two_count_beads = NonNegSmallIntegerField()

    one_count_beads = NonNegSmallIntegerField()

    armscye_d = NonNegSmallIntegerField()

    armscye_c = NonNegSmallIntegerField()

    wrist_hem_height = NonNegFloatField()

    #
    # Actuals
    #

    actual_wrist_to_cap = LengthField()

    actual_armcap_heights = LengthField()

    @property
    def is_straight(self):
        # Note: clean() ensures that if the following is true, then
        # rows_after_compound_shaping_rows must be None as well.
        return self.num_sleeve_increase_rows in [None, 0]

    @property
    def is_tapered(self):
        return self.cast_ons < self.bicep_stitches

    @property
    def is_bell(self):
        return self.cast_ons > self.bicep_stitches

    # Required by templates
    @property
    def actual_total_height(self):
        return self.actual_wrist_to_cap + self.actual_armcap_heights

    @property
    def num_sleeve_increase_repetitions(self):
        """
        Will be None if there is no sleeve shaping or if sleeve uses compound shaping.
        """
        if self.is_straight or self.num_sleeve_compound_increase_rows:
            return None
        else:
            return self.num_sleeve_increase_rows - 1

    @property
    def actual_wrist(self):
        # We have to be sure to subtract out the extra cable-stitches, since the whole
        # point of those stitches is that they don't extend the width of the piece
        cable_stitches = self.get_spec_source().sleeve_cable_extra_stitches
        effective_cast_ons = self.cast_ons - (cable_stitches if cable_stitches else 0)
        return effective_cast_ons / self.gauge.stitches

    @property
    def actual_bicep(self):
        # We have to be sure to subtract out the extra cable-stitches, since the whole
        # point of those stitches is that they don't extend the width of the piece
        cable_stitches = self.get_spec_source().sleeve_cable_extra_stitches
        if self.get_spec_source().sleeve_cable_extra_stitches_caston_only:
            cable_stitches = 0
        effective_bicep_stitches = self.bicep_stitches - (
            cable_stitches if cable_stitches else 0
        )
        return effective_bicep_stitches / self.gauge.stitches

    @property
    def is_set_in_sleeve(self):
        return self.schematic.is_set_in_sleeve

    @property
    def is_drop_shoulder(self):
        return self.schematic.is_drop_shoulder

    @property
    def pre_bead_game_stitch_count(self):
        return self.bicep_stitches - (2 * sum([self.armscye_x, self.armscye_y]))

    @property
    def post_bead_game_stitch_count(self):
        return self.pre_bead_game_stitch_count - (
            2
            * sum(
                [
                    self.one_count_beads,
                    self.two_count_beads,
                    self.four_count_beads,
                    self.six_count_beads,
                ]
            )
        )

    @property
    def hem_stitch(self):
        return self.schematic.sleeve_edging_stitch

    @property
    def allover_stitch(self):
        return self.schematic.sleeve_allover_stitch

    @property
    def cable_stitch(self):
        return self.schematic.sleeve_cable_stitch

    def hem_stitch_patterntext(self):
        """
        Returns the patterntext-appropriate name for the hem-stitch.
        """
        if self.hem_stitch:
            return self.hem_stitch.patterntext
        else:
            return None

    @property
    def wrist_hem_height_in_rows(self):
        return self._height_to_row_count(self.wrist_hem_height, parities["wrist_hem"])

    @property
    def actual_wrist_to_cap_in_rows(self):
        return self._height_to_row_count(
            self.actual_wrist_to_cap, parities["wrist_to_cap_start"]
        )

    @property
    def rows_in_cap(self):
        # two rows per two-count bead
        # four rows per four-count bead
        # six rows per six-count bead
        bead_rows = sum(
            [
                self.one_count_beads,
                self.two_count_beads * 2,
                self.four_count_beads * 4,
                self.six_count_beads * 6,
            ]
        )

        rows = bead_rows

        if self.armscye_x:
            rows += 1

        if self.armscye_y:
            rows += 2

        if self.armscye_d:
            rows += 4

        if not self.is_drop_shoulder:
            rows += 2

        return rows

    @property
    def actual_wrist_to_end_in_rows(self):
        return sum([self.actual_wrist_to_cap_in_rows, self.rows_in_cap])

    @property
    def inter_sleeve_increase_rows_plus_one(self):
        "Will be None if straight"
        if self.is_straight or self.inter_sleeve_increase_rows is None:
            return None
        else:
            return self.inter_sleeve_increase_rows + 1

    @property
    def rows_after_compound_shaping_rows_plus_one(self):
        "Will be None if straight or doesn't use compound shaping"
        if self.is_straight or (not self.num_sleeve_compound_increase_rows):
            return None
        else:
            return self.rows_after_compound_shaping_rows + 1

    @property
    def shaping_row_on_ws(self):
        """
        If true, then all sleeve shaping rows will be of mixed chirality
        (some RS rows, some WS rows)

        Will be None if straight.
        """
        if self.is_straight:
            return None
        elif self.num_sleeve_increase_rows == 1:
            # corner case
            # clean() ensures that num_compound_rows is 0 or None and
            # inter_sleeve_increase_rows is None
            return False
        else:
            # There are multiple increase rows. Check if
            # inter_sleeve_increase_rows is even. If so, ws rows.
            # If not, check for compound rows.
            if is_even(self.inter_sleeve_increase_rows):
                return True
            else:
                # Check if compound shaping puts shaping rows on the ws
                if self.rows_after_compound_shaping_rows is None:
                    return False
                elif is_even(self.rows_after_compound_shaping_rows):
                    return True
                else:
                    return False

    def num_shaping_rows(self):
        total = 0
        if self.num_sleeve_increase_rows is not None:
            total += self.num_sleeve_increase_rows
        if self.num_sleeve_compound_increase_rows is not None:
            total += self.num_sleeve_compound_increase_rows
        return total

    def num_shaping_rows_minus_one(self):
        if self.num_shaping_rows() < 1:
            return None
        else:
            return self.num_shaping_rows() - 1

    def _rows_in_shaping(self):
        """
        Note: includes both first and last shaping rows.
        """
        assert not self.is_straight

        if self.num_sleeve_compound_increase_rows:

            rows = sum(
                [
                    self.num_sleeve_increase_rows
                    * (self.inter_sleeve_increase_rows + 1),
                    self.num_sleeve_compound_increase_rows
                    * (self.rows_after_compound_shaping_rows + 1),
                ]
            )

            # We've counted too much-- either an extra inter_sleeve_increase_rows or an
            # extra rows_after_compound_shaping_rows, depending on which kind is last

            if self.num_sleeve_compound_increase_rows >= self.num_sleeve_increase_rows:
                # compound rows were last
                rows -= self.rows_after_compound_shaping_rows
            else:
                rows -= self.inter_sleeve_increase_rows

        else:
            # Simpler case

            rows = 1
            repetitions = self.num_sleeve_increase_rows - 1
            assert repetitions >= 0
            if repetitions >= 1:
                rows += repetitions * (self.inter_sleeve_increase_rows + 1)

        return int(rows)

    @property
    def last_shaping_to_cap_in_rows(self):
        # REturn the number of rows between beginning of first armcap row and *beginning* of
        # last shaping row. Will be None if there is no shaping
        if self.last_shaping_height_in_rows is None:
            return None
        else:
            return sum(
                [
                    self.actual_wrist_to_cap_in_rows,
                    -self.last_shaping_height_in_rows,
                    1,  # self.last_shaping_height_in_rows includes last shaping row, so we need to add it back in
                ]
            )

    # Used to estimate yardage of a pattern
    def area(self):
        """
        Note: returns 'yardage' area of BOTH sleeves, in square inches.
        What is 'yardage' area? The area we should use to compute yardage. That is,
        the area this piece would have if all the stitches were in the all-over stitch.
        This may be different from the 'actual' area, since the extra stitches in the
        cable produce no area (but should be used to compute yardage).
        """

        # Break into four pieces:
        #
        # 1. Straight before shaping
        # 2. Shaping
        # 3. Straight after shaping
        # 4. Cap

        # Note: we can't use self.actual_wrist and self.actual_bicep for these
        # since we remove the cable stitches before computing them. So,
        # compute 'yardage' versions of them. Complication: we don't count the
        # cable-stitches if they are cast-on only

        cast_on_stitches = self.cast_ons
        if self.get_spec_source().sleeve_cable_extra_stitches:
            if self.get_spec_source().sleeve_cable_extra_stitches_caston_only:
                cast_on_stitches -= self.get_spec_source().sleeve_cable_extra_stitches
        yardage_wrist_width = cast_on_stitches / self.gauge.stitches
        yardage_bicep_width = self.bicep_stitches / self.gauge.stitches

        # But first, deal with corner case: straight
        if self.is_straight:
            area1 = rectangle_area(self.actual_wrist_to_cap, yardage_wrist_width)
            area2 = 0
            area3 = 0
        else:
            area1 = rectangle_area(yardage_wrist_width, self.first_shaping_height)

            area2_height = self._rows_in_shaping() / self.gauge.rows
            area2 = trapezoid_area(
                yardage_wrist_width, yardage_bicep_width, area2_height
            )

            area3_rows = (
                self.last_shaping_to_cap_in_rows - 1
            )  # Don't double-count the last shaping row
            area3_height = area3_rows / self.gauge.rows
            area3 = rectangle_area(area3_height, yardage_bicep_width)

        area4_height = self.actual_armcap_heights
        armcap_top_width = self.armscye_c / self.gauge.stitches
        armcap_bottom_width = yardage_bicep_width
        area4 = trapezoid_area(armcap_bottom_width, armcap_top_width, area4_height)

        return 2 * sum([area1, area2, area3, area4])

    def _compute_values(self, roundings, ease_tolerances, sweater_back, spec_source):

        # General structure of this function:
        #
        # 1. Figure out the cast-on and edging
        # 2. Figure out the arm-cap
        # 3. With these, can interpolate from edging to arm-cap (for bell or
        #    tapered sleeves)

        gauge = self.gauge
        caston_repeats = self.caston_repeats()

        # Cast-on and edging

        if caston_repeats:
            self.cast_ons = _find_best_approximation(
                self.schematic.sleeve_cast_on_width,
                gauge.stitches,
                roundings["cast_ons"],
                ease_tolerances[spec_source.sleeve_length],
                caston_repeats.x_mod,
                caston_repeats.mod_y,
            )

            self.bicep_stitches = _find_best_approximation(
                self.schematic.bicep_width,
                gauge.stitches,
                roundings["bicep"],
                ease_tolerances["bicep"],
                caston_repeats.x_mod,
                caston_repeats.mod_y,
            )

            # We need to check for a corner case: drop-shoulder sweaters where the bicep is 'too far' from the
            # goal due to repeats.
            bicep_length = self.bicep_stitches / self.gauge.stitches
            bicep_too_far_from_goal = (
                abs(bicep_length - self.schematic.bicep_width)
                > DROP_SHOULDER_BICEP_TOLERANCE
            )

            if not (self.is_drop_shoulder and bicep_too_far_from_goal):

                bicep_parity = self.bicep_stitches % 2
                if (self.cast_ons % 2) != bicep_parity:
                    # The intuition here is that if both cast-ons and bicep_stitches
                    # respect the x mod y of the repeats *and* are of different
                    # partities, then it must be the case that y is odd. In that
                    # case, we can adjust cast_ons to both respect x mod y and
                    # have the same partiy as bicep_stitches by either adding or
                    # subtracting y. Which? Adding y.
                    self.cast_ons += caston_repeats.mod_y

            else:
                # We're in a special casee: a drop-shoulder sweater where biceps are 'too large' or 'too small'
                # compared to the armholes. In that case, we need to adjust the bicep by ignoring repeats.
                # And while we're at it, we might as well match the cast-on parity, too. So replace the repeats
                # of the cast_ons with the repeats x mod 2, where x is the parity of the cast-ons
                x_mod = self.cast_ons % 2
                self.bicep_stitches = _find_best_approximation(
                    self.schematic.bicep_width,
                    gauge.stitches,
                    ROUND_ANY_DIRECTION,
                    ease_tolerances["bicep"],
                    x_mod=x_mod,
                    mod_y=2,
                )

            assert (self.bicep_stitches % 2) == (self.cast_ons % 2)
        else:
            self.cast_ons = _find_best_approximation(
                self.schematic.sleeve_cast_on_width,
                gauge.stitches,
                roundings["cast_ons"],
                ease_tolerances[spec_source.sleeve_length],
            )

            cast_on_parity = self.cast_ons % 2

            self.bicep_stitches = _find_best_approximation(
                self.schematic.bicep_width,
                gauge.stitches,
                roundings["bicep"],
                ease_tolerances["bicep"],
                cast_on_parity,
                2,
            )

        assert (self.cast_ons % 2) == (self.bicep_stitches % 2)

        armscye_circumference_inches = sweater_back.actual_armhole_circumference * 2
        # double, to account for sweaterfront too

        if not self.is_drop_shoulder:

            armcap_shaping = compute_armcap_shaping(
                self.gauge,
                sweater_back.armhole_x,
                sweater_back.armhole_y,
                armscye_circumference_inches,
                self.bicep_stitches,
            )

            self.armscye_x = armcap_shaping.armscye_x
            self.armscye_y = armcap_shaping.armscye_y
            self.armscye_c = armcap_shaping.armscye_c
            self.armscye_d = armcap_shaping.armscye_d
            self.six_count_beads = armcap_shaping.six_count_beads
            self.four_count_beads = armcap_shaping.four_count_beads
            self.two_count_beads = armcap_shaping.two_count_beads
            self.one_count_beads = armcap_shaping.one_count_beads

            actual_armcap_rows = self.rows_in_cap

            self.actual_armcap_heights = actual_armcap_rows / gauge.rows

        else:
            # drop shoulder
            self.armscye_x = 0
            self.armscye_y = 0
            self.armscye_c = self.bicep_stitches
            self.armscye_d = 0
            self.six_count_beads = 0
            self.four_count_beads = 0
            self.two_count_beads = 0
            self.one_count_beads = 0

            self.actual_armcap_heights = 0

        # Interpolate edging to cap

        # First, see if we need to adjust the cast-ons due to lack of
        # increase/decrease vertical distance. This is only necessary
        # if the sleeve is not already straight.
        if self.cast_ons != self.bicep_stitches:

            two_rows_height = self._two_rows_height()
            increase_vertical_distance = (
                self.schematic.sleeve_to_armcap_start_height
                - minimum_sleeve_straights_below_cap[spec_source.construction][
                    spec_source.sleeve_length
                ]
                - self.schematic.sleeve_edging_height
                - two_rows_height
            )

            # Do we have any room to do the shaping?
            if increase_vertical_distance <= 0:

                # Nope. Go straight.
                self.cast_ons = self.bicep_stitches

            else:

                (self.cast_ons, sr) = self._compute_shaping(
                    self.cast_ons,
                    self.bicep_stitches,
                    increase_vertical_distance,
                    gauge,
                    spec_source,
                )

            self.num_sleeve_increase_rows = sr.num_standard_shaping_rows
            self.inter_sleeve_increase_rows = sr.rows_between_standard_shaping_rows
            try:
                self.num_sleeve_compound_increase_rows = sr.num_alternate_shaping_rows
            except AttributeError:
                self.num_sleeve_compound_increase_rows = None

            try:
                self.rows_after_compound_shaping_rows = (
                    sr.rows_after_alternate_shaping_rows
                )
            except AttributeError:
                self.rows_after_compound_shaping_rows = None

        # end if self.style != SLEEVE_STRAIGHT

        self.actual_wrist_to_cap = self.schematic.sleeve_to_armcap_start_height

        desired_wrist_edging_height = self.schematic.sleeve_edging_height
        if desired_wrist_edging_height > self.actual_wrist_to_cap:
            self.wrist_hem_height = MINIMUM_WRIST_EDGING_HEIGHT
        else:
            self.wrist_hem_height = desired_wrist_edging_height

        # Last step: Add in the extra stitches for the sleeve cable
        cable_stitches = self.get_spec_source().sleeve_cable_extra_stitches
        if cable_stitches:
            self.cast_ons += cable_stitches
            assert self.cast_ons > 0

            if not self.get_spec_source().sleeve_cable_extra_stitches_caston_only:
                self.bicep_stitches += cable_stitches
                assert self.bicep_stitches > 0

                self.armscye_c += cable_stitches
                assert self.armscye_c > 0

    def _two_rows_height(self):
        """
        Helper function to compute the height of the two work-even rows
        after the hem is done.
        """
        return 2.0 / self.gauge.rows

    def _compute_shaping(
        self,
        start_castons,
        bicep_stitches,
        increase_vertical_distance,
        gauge,
        spec_source,
    ):
        two_rows_height = self._two_rows_height()
        caston_repeats = self.caston_repeats()

        bell_sleeve = start_castons > bicep_stitches
        tapered_sleeve = start_castons < bicep_stitches
        assert bell_sleeve or tapered_sleeve

        if bell_sleeve:
            larger_stiches = start_castons
            smaller_stitches = bicep_stitches
        else:
            larger_stiches = bicep_stitches
            smaller_stitches = start_castons

        # Compute edge shaping

        sr1 = self.compute_edge_shaping(
            larger_stiches,
            smaller_stitches,
            increase_vertical_distance,
            gauge,
            even_spacing=False,
        )

        if sr1.constraints_met:

            max_vertical_above_shaping = maximum_sleeve_straights_below_cap[
                spec_source.construction
            ][spec_source.sleeve_length]
            actual_vertical_above_shaping = sr1.shaping_vertical_play + two_rows_height

            if actual_vertical_above_shaping <= max_vertical_above_shaping:
                if spec_source.is_set_in_sleeve and not sr1.max_distance_constraint_hit:
                    sr2 = self.compute_edge_shaping(
                        larger_stiches,
                        smaller_stitches,
                        increase_vertical_distance,
                        gauge,
                        even_spacing=False,
                        max_distance_between_shaping_rows=MAX_INCHES_BETWEEN_SLEEVE_SHAPING_ROWS,
                    )
                    if sr2.constraints_met:
                        return (start_castons, sr2)
                    else:
                        return (start_castons, sr1)
                else:
                    return (start_castons, sr1)

            else:
                # Vertrical-play constraint not met
                sr3 = self.compute_compound_edge_shaping(
                    larger_stiches, smaller_stitches, increase_vertical_distance, gauge
                )
                if sr3.constraints_met:
                    return (start_castons, sr3)
                else:
                    return (start_castons, sr3)
        else:

            # We could not achieve the shaping. Adjust the cast-ons.

            if bell_sleeve:
                best_castons = sr1.best_larger_stitches
                rounding_direction = ROUND_DOWN
            else:
                best_castons = sr1.best_smaller_stitches
                rounding_direction = ROUND_UP

            # If we're not using repeats, we can just take the values
            # from the ShapingResult:
            if not caston_repeats:

                return (best_castons, sr1)

            else:
                # We *are* using repeats. We need to take the
                # ShapingResults' best guess, round it in the right directions to the right
                # modularity and parity, and then re-compute the shaping.

                new_castons = round(
                    best_castons,
                    rounding_direction,
                    caston_repeats.mod_y,
                    caston_repeats.x_mod,
                )
                bicep_parity = bicep_stitches % 2
                if (new_castons % 2) != bicep_parity:
                    # At this point, what do we know? For bell sleeves, we know that
                    # best_castons (i.e., sr.best_larger_stitches) must be as large or
                    # larger than bicep_stitches, and so when we
                    # round it down, above, to a number of the same
                    # x mod y as bicep_stitches, we will get something
                    # as large or larger than bicep_stitches. If it
                    # is of the opposite parity as bicep_stitches,
                    # further, it must not be equal to bicep_stitches
                    # and therefore must be larger than bicep_stitches
                    # by at least y. If we subtract y, then,
                    # we will get another number as large or larger
                    # than bicep_stitches, of the same parity as
                    # bicep_stitches, and respecting the same x mod y.
                    # (And the same logic follows for tapered sleeves, except we
                    # rounded up and so need to add y.)
                    if bell_sleeve:
                        new_castons -= caston_repeats.mod_y
                    else:
                        new_castons += caston_repeats.mod_y

                assert (
                    bicep_stitches - caston_repeats.x_mod
                ) % caston_repeats.mod_y == 0
                assert (new_castons - caston_repeats.x_mod) % caston_repeats.mod_y == 0
                assert (new_castons % 2) == (bicep_stitches % 2)
                if bell_sleeve:
                    assert new_castons >= bicep_stitches
                else:
                    assert new_castons <= bicep_stitches

                if bell_sleeve:
                    new_larger_stitches = new_castons
                    new_smaller_stitches = bicep_stitches
                else:
                    new_larger_stitches = bicep_stitches
                    new_smaller_stitches = new_castons

                sr4 = SweaterPiece.compute_edge_shaping(
                    new_larger_stitches,
                    new_smaller_stitches,
                    increase_vertical_distance,
                    gauge,
                )

                assert sr4.constraints_met
                return (new_castons, sr4)

    @property
    def first_shaping_height(self):
        """
        Height, in inches, of the first shaping row. Will be None if
        there is no shaping.
        """
        if self.is_straight:
            return None
        else:
            return self._row_count_to_height(self.first_shaping_height_in_rows)

    @property
    def row_before_first_shaping_row_height(self):
        if self.is_straight:
            return None
        else:
            return self._row_count_to_height(self.row_before_first_shaping_row)

    @property
    def first_shaping_height_in_rows(self):
        """
        Height, in rows, of the first shaping row. Will be None if
        there is no shaping.
        """
        if self.is_straight:
            return None
        else:
            return self.wrist_hem_height_in_rows + 3

    # This next one is useful for templates
    @property
    def row_before_first_shaping_row(self):
        if self.first_shaping_height_in_rows is None:
            return None
        else:
            return self.first_shaping_height_in_rows - 1

    @property
    def last_shaping_height_in_rows(self):
        """
        Height, in rows, of the last shaping row. Will be None if
        there is no shaping.
        """
        if self.is_straight:
            return None
        else:
            return self.first_shaping_height_in_rows + self._rows_in_shaping() - 1

    def get_design(self):
        """
        Gets the original patternspec from the start of this pattern. Present only
        to maintain backwards compatibility with templates in the database.
        """
        spec_source = self.get_spec_source()
        pspec = spec_source.get_original_patternspec()
        return pspec

    def caston_repeats(self):
        """
        Return the caston repeat requirements for the sleeve caston.
        """
        return self.get_spec_source().sleeve_repeats()

    def clean(self):

        if self.num_sleeve_increase_rows is None:
            if self.inter_sleeve_increase_rows is not None:
                raise ValidationError(
                    "Cannot have inter_sleeve_increase_rows without num_sleeve_increase_rows"
                )
            if self.num_sleeve_compound_increase_rows is not None:
                raise ValidationError(
                    "Cannot have num_sleeve_compound_increase_rows without num_sleeve_increase_rows"
                )
        elif self.num_sleeve_increase_rows == 0:
            if self.inter_sleeve_increase_rows is not None:
                raise ValidationError(
                    "Cannot have inter_sleeve_increase_rows without num_sleeve_increase_rows"
                )
            if self.num_sleeve_compound_increase_rows not in [None, 0]:
                raise ValidationError(
                    "Cannot have num_sleeve_compound_increase_rows without num_sleeve_increase_rows"
                )
        elif self.num_sleeve_increase_rows == 1:
            if self.num_sleeve_compound_increase_rows not in [None, 0]:
                raise ValidationError(
                    "Cannot have num_sleeve_compound_increase_rows without num_sleeve_increase_rows"
                )
            if self.inter_sleeve_increase_rows is not None:
                raise ValidationError(
                    "Cannot have inter_sleeve_increase_rows without 2 or more num_sleeve_increase_rows"
                )
        else:
            assert self.num_sleeve_increase_rows >= 2
            if self.num_sleeve_compound_increase_rows not in [
                None,
                0,
                self.num_sleeve_increase_rows,
                self.num_sleeve_increase_rows - 1,
            ]:
                raise ValidationError(
                    "Invalid value for num_sleeve_compound_increase_rows"
                )
            if self.inter_sleeve_increase_rows is None:
                raise ValidationError(
                    "Must have inter_sleeve_increase_rows with 2 or more num_sleeve_increase_rows"
                )

        if self.num_sleeve_compound_increase_rows in [None, 0]:
            if self.rows_after_compound_shaping_rows is not None:
                raise ValidationError(
                    "Cannot have rows_after_compound_shaping_rows without num_sleeve_compound_increase_rows"
                )
        else:
            if self.num_sleeve_increase_rows in [None, 1]:
                raise ValidationError(
                    "Cannot have num_sleeve_compound_increase_rows without multiple num_sleeve_increase_rows"
                )
            if self.rows_after_compound_shaping_rows is None:
                raise ValidationError(
                    "Must have rows_after_compound_shaping_rows with num_sleeve_compound_increase_rows"
                )
            if self.rows_after_compound_shaping_rows == self.inter_sleeve_increase_rows:
                raise ValidationError(
                    "Compound shaping must use two different shaping rates"
                )

        return super(_BaseSleeve, self).clean()


class Sleeve(_BaseSleeve, SweaterPiece):

    _pattern_field_name = "sleeve"

    schematic = models.OneToOneField(SleeveSchematic, on_delete=models.CASCADE)

    def get_spec_source(self):
        return self.schematic.get_spec_source()

    @staticmethod
    def make(swatch, schematic, roundings, ease_tolerances, sweater_back, spec_source):
        """
        Makes, validates, and returns a Sleeve instance based on high-level input.

        :type sweater_back: SweaterBack
        :type gauge: Gauge
        :type schematic: GarmentParameters
        """
        p = Sleeve()
        sl_roundings = roundings["sleeve"]
        p.swatch = swatch
        p.schematic = schematic

        p._compute_values(sl_roundings, ease_tolerances, sweater_back, spec_source)
        p.full_clean()
        return p


class GradedSleeve(_BaseSleeve, GradedSweaterPiece):
    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(GradedSleeveSchematic, on_delete=models.CASCADE)

    @classmethod
    def make(
        cls, sleeve_schematic, sweater_back, roundings, ease_tolerances, spec_source
    ):
        p = GradedSleeve()
        sl_roundings = roundings["sleeve"]
        p.schematic = sleeve_schematic
        p.graded_pattern_pieces = sweater_back.graded_pattern_pieces
        p.sort_key = sweater_back.sort_key

        p._compute_values(sl_roundings, ease_tolerances, sweater_back, spec_source)
        p.full_clean()
        return p

    def get_spec_source(self):
        return self.graded_pattern_pieces.get_spec_source()

    @property
    def finished_full_bust(self):
        return self.sort_key


#   Graded Sleeve constraints
#
#
# * all straight, all tapered, or all bell.
