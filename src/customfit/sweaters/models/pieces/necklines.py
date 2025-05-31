from django.db import models

from customfit.fields import (
    NonNegFloatField,
    NonNegSmallIntegerField,
    PositiveFloatField,
    StrictPositiveSmallIntegerField,
)
from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    hypotenuse,
    is_odd,
    rectangle_area,
    round,
    trapezoid_area,
    triangle_area,
)
from customfit.helpers.row_parities import RS, WS, reverse_parity

from ...helpers import sweater_design_choices as SDC
from .base_piece import SweaterPiece


def _trapezoid_area_stitches_and_rows(
    bottom_stitches, top_stitches, rows, row_gauge, stitch_gauge
):
    """
    Helper function to compute area of a trapezoid, when the dimensions are
    given in stitches and rows instead of inches
    """

    bottom_width = bottom_stitches / stitch_gauge
    top_width = top_stitches / stitch_gauge
    height = rows / row_gauge
    return trapezoid_area(bottom_width, top_width, height)


class Neckline(models.Model):

    row_gauge = PositiveFloatField(help_text=b"Rows per inch")

    stitch_gauge = PositiveFloatField(help_text=b"Stitches per inch")

    # Subclasses must implement all of the following methods.
    # I would love to use python's abc class to make this manditory, but
    # it turns out that Django's metclass magic conflicts with the abc
    # library's magic. Oh, well. I will provide exception-raising default
    # implementations so that the list of required methods is collected
    # in the abstract base class, at least, while making the failure to
    # override them into a run-time exception

    def total_depth(self):
        raise AttributeError("total_depth method not provided by Neckline")

    def depth_to_shaping_end(self):
        raise AttributeError("depth_to_shaping_end method not provided by Neckline")

    def rows_in_pullover_shaping(self):
        # Returns the number of rows between *and including* the first row
        # of neckline working (usually the initial bind-off row) and the the
        # last row of any bind-offs or decreases. Does not include any later
        # 'work even' rows that may be implied by the patterntext instructions.
        # Also, it is assumed that the last shaping row on the left side
        # of the neck will also be the last shaping row on the right side.
        raise AttributeError("method not provided by Neckline")

    def rows_in_cardigan_shaping(self, neckline_parity):
        # Returns the number of rows between *and including* the first row
        # of neckline working (usually the initial bind-off row) and the the
        # last row of any bind-offs or decreases. Does not include any later
        # 'work even' rows that may be implied by the patterntext instructions.
        # neckline_parity is the partity of the first row of the neckline
        raise AttributeError("method not provided by Neckline")

    def stitches_across_neckline(self):
        raise AttributeError("stitches_across_neckline method not provided by Neckline")

    def stitches_to_pick_up(self):
        raise AttributeError("stitches_to_pick_up method not provided by Neckline")

    @property
    def style_id(self):
        raise AttributeError("Neckline fails to define style_id")

    def area(self):
        """
        The area (in sq in) that the neckline *removes* from the piece,
        approximately.
        """
        raise AttributeError("Neckline fails to define area")

    def _width(self):
        """
        Often used in implementations of area()
        """
        return self.stitches_across_neckline() / self.stitch_gauge

    def empty(self):
        """
        If True, there is actually no neckline and the patterntext-renderer
        should skip the neckline instructions. (One example: the user selected a
        button-band allowance of 100% of the front neckline. In this case, the
        cardigan pieces should go right up to the shoulder seams, with no
        neckline shaping.)


        Defaults to False. Subclasses MAY override this if they would like.

        Note: originally implemented as the magic method __nonzero__ (as one
        might expect) but that interacts poorly with django's generic relation
        machinery, which we use for necklines.
        """
        return False

    # Regular methods

    def style(self):
        return self.style_id

    def __str__(self):
        return "%s %s" % (self.__class__.__name__, self.id)

    class Meta:
        abstract = True


class BackNeckline(Neckline):
    """
    The class of necklines associated with back pieces. Not allowed to be
    empty/void.

    Many of the methods of this neckline involve the magic constant 5. Why? Because
    this neckline has more than 5 rows, then there is gradual shaping after the
    initial bind-offs. Otherwise, this neckline is perfectly square.
    """

    bindoff_stitches = StrictPositiveSmallIntegerField(
        help_text="Total number of stitches to bind off on first row."
    )

    neckline_depth = NonNegFloatField(help_text="Depth of the neckline, in inches")

    pickup_stitches = StrictPositiveSmallIntegerField(
        help_text="Number of stitches to pick up"
    )

    stitches_before_initial_bindoffs = StrictPositiveSmallIntegerField(
        help_text="Number of stitches to work from edge to initial bindoffs."
    )

    def total_depth(self):
        return self.neckline_depth

    def depth_to_shaping_end(self):
        if self.rows_in_neckline() >= 5:
            shaping_height = 4 / self.row_gauge
            return self.neckline_depth - shaping_height
        else:
            return self.total_depth()

    def stitches_across_neckline(self):
        if self.rows_in_neckline() >= 5:
            return self.bindoff_stitches + 4
        else:
            return self.bindoff_stitches

    def stitches_to_pick_up(self):
        return self.pickup_stitches

    def area(self):
        return rectangle_area(self.total_depth(), self._width())

    def rows_in_pullover_shaping(self):
        if self.rows_in_neckline() >= 5:
            return 5
        else:
            return 0

    def rows_in_cardigan_shaping(self, neckline_parity):
        # This makes no sense. There is no such thing as a cardigan in the back
        raise NotImplementedError

    style_id = SDC.NECK_BACK

    # Note: different arguments than front pieces.
    @classmethod
    def make(
        cls,
        stitches_goal,
        depth_goal,
        gauge,
        rounding,
        ease_tolerances,
        shoulder_stitches,
    ):
        """
        Make a BackNeckline instance. Typical usage:

          bn = BackNeckline.make(...)

        * stitches_goal: the number of stitches removed during the shaping of
          this neckline. Note: this argument is non-negotiable. If the neckline
          does not have this exact number of stitches, the pattern will be
          wrong.

        * depth_goal: The desired height (in inches) from the lowest row of
          neckline shaping to the shoulder bindoffs. Note: the neck might
          end up actually deeper than this, but should not be shallower.

        * gauge: the Gauge object to use.

        * rounding: A dict holding the rounding directions to be used.

        * ease_tolerances: Unused. Present only for historical reasons.

        * shoulder_stitches: number of stitches in the shoulder bindoffs.
          Sometimes needed to properly compute neckline-start instructions.
        """

        assert stitches_goal > 0

        neckline = cls()
        neckline.row_gauge = gauge.rows
        neckline.stitch_gauge = gauge.stitches

        rows_in_neckline = round(depth_goal * gauge.rows, ROUND_UP)
        neckline.neckline_depth = rows_in_neckline / gauge.rows

        if rows_in_neckline >= 5:
            neckline.bindoff_stitches = stitches_goal - 4
            neckline.stitches_before_initial_bindoffs = shoulder_stitches + 2

            neckline.pickup_stitches = round(
                neckline.bindoff_stitches
                + 4
                + (2 * neckline.neckline_depth * gauge.stitches),
                rounding["neckline_pickup_stitches"],
            )

        else:
            # super-chunky yarn
            assert rows_in_neckline >= 1

            neckline.bindoff_stitches = stitches_goal
            neckline.stitches_before_initial_bindoffs = shoulder_stitches

            neckline.pickup_stitches = round(
                neckline.bindoff_stitches
                + (2 * neckline.neckline_depth * gauge.stitches),
                rounding["neckline_pickup_stitches"],
            )

        return neckline

    def rows_in_neckline(self):
        rows = round(self.neckline_depth * self.row_gauge, ROUND_UP)
        return int(rows)


class VeeNeck(Neckline):

    depth = PositiveFloatField(
        blank=True, null=True, help_text="Depth, in inches, of the entire neckline"
    )

    extra_bindoffs = NonNegSmallIntegerField(help_text="number of extra bindoffs")

    rows_per_decrease = NonNegSmallIntegerField(
        blank=True, null=True, help_text="number of rows per repeat"
    )

    decrease_rows = NonNegSmallIntegerField(help_text="total number of decrease rows")

    pickup_stitches = NonNegSmallIntegerField(help_text="Number of stitches to pick up")

    style_id = SDC.NECK_VEE

    # Required by the Neckline API
    def total_depth(self):
        return self.depth

    def depth_to_shaping_end(self):
        if not self.empty():
            return self.depth - (self.rows_in_pullover_shaping() / self.row_gauge)
        else:
            return None

    def stitches_across_neckline(self):
        return self.extra_bindoffs + (2 * self.decrease_rows)

    def stitches_to_pick_up(self):
        return self.pickup_stitches

    def area(self):
        # Break into two parts: the straight part and the triangular part

        # straight part
        area1 = rectangle_area(self._width(), self.depth_to_shaping_end())

        # triangular part
        area2_height = self.total_depth() - self.depth_to_shaping_end()
        # If there are no initial bindoffs, the first two shapign rows have
        # no area
        if not self.extra_bindoffs:
            area2_height -= 2 / self.row_gauge
        area2 = triangle_area(self._width(), area2_height)

        return sum([area1, area2])

    def empty(self):
        """
        Return True (indicating that this is a void neckline and should be
        skipped) if there are no decrease rows and no bindoff stitches
        """
        return not any([self.extra_bindoffs > 0, self.decrease_rows > 0])

    # Required by templates
    def rows_per_decrease_odd(self):
        if self.rows_per_decrease is None:
            return None
        else:
            return is_odd(self.rows_per_decrease)

    def decrease_repeats(self):
        if self.decrease_rows >= 1:
            return self.decrease_rows - 1
        else:
            return None

    def rows_in_pullover_shaping(self):
        return_me = 0

        if self.extra_bindoffs or self.decrease_rows:
            # Initial bindoff or marker row
            return_me += 1
        if self.decrease_rows:
            if self.decrease_repeats():
                return_me += 1  # skip row
                return_me += (self.rows_per_decrease * self.decrease_repeats()) + 1
            else:
                return_me += 1

        return return_me

    def rows_in_cardigan_shaping(self, neckline_parity):
        # neckline_parity is ignored
        return_me = 0
        if self.decrease_rows:
            if self.decrease_repeats():
                return_me += (self.rows_per_decrease * self.decrease_repeats()) + 1
            else:
                return_me += 1
        return return_me

    @classmethod
    def make(cls, stitches_goal, depth_goal, gauge, rounding, ease_tolerances):
        """
        Make a VeeNeck instance. Typical usage:

          bn = VeeNeck.make(...)

        * stitches_goal: the number of stitches removed during the shaping of
          this neckline. Note: in Cardgigans, may be different than the actual
          stitch-width of the neck opening. Also, this argument is
          non-negotiable. If the neckline does not have this exact number of
          stitches, the pattern will be wrong.

        * depth_goal: The desired height (in inches) from the lowest row of
          neckline shaping to the shoulder bindoffs. Note: the neck might
          end up actually deeper than this, but should not be shallower.

        * gauge: the Gauge object to use.

        * rounding: A dict holding the rounding directions to be used.

        * ease_tolerances: Unused. Present only for historical reasons.

        """

        assert stitches_goal >= 0

        neckline = cls()
        neckline.row_gauge = gauge.rows
        neckline.stitch_gauge = gauge.stitches

        if is_odd(stitches_goal):
            neckline.extra_bindoffs = 1
        else:
            neckline.extra_bindoffs = 0
        # Subtract two rows
        # The first is the initial-bindoff row. Even if there are no extra bindoffs,there is effectively shaping
        # in the initial-bindoff/marker row anyway due to the holding of stitches. The second is the initial
        # 'skip' row before the first decrease row
        shaping_depth = depth_goal - (2 / gauge.rows)

        # If the shaping required is especially steep, then the call
        # to compute_edge_shaping may fail. In that case, catch the
        # exception, increase the depth, and try again.

        shaping_achieved = False
        while not shaping_achieved:
            sr = SweaterPiece.compute_edge_shaping(
                stitches_goal, neckline.extra_bindoffs, shaping_depth, gauge
            )
            shaping_achieved = sr.constraints_met
            if not shaping_achieved:
                shaping_depth += 0.25
        assert sr.num_standard_shaping_rows >= 0

        neckline.decrease_rows = sr.num_standard_shaping_rows

        if not any([neckline.decrease_rows, neckline.extra_bindoffs]):
            # There are no shaping rows. Set values for a 'null' neckline
            neckline.depth = None
            neckline.rows_per_decrease = None
            neckline.pickup_stitches = 0

        else:

            neckline.depth = shaping_depth + (2 / gauge.rows)

            if sr.rows_between_standard_shaping_rows is not None:
                neckline.rows_per_decrease = sr.rows_between_standard_shaping_rows + 1
            else:
                neckline.rows_per_decrease = None

            # How many stitches to pick up in this neckline?
            neckline.stitches_gauge = gauge.stitches
            neckline.rows_gauge = gauge.rows
            rows_in_neck = round(neckline.depth * gauge.rows, ROUND_DOWN)

            shaping_rows = 1
            if neckline.rows_per_decrease:
                shaping_rows += (
                    neckline.decrease_rows - 1
                ) * neckline.rows_per_decrease

            straight_rows = rows_in_neck - shaping_rows

            width_of_slope = neckline.decrease_rows / gauge.stitches
            height_of_slope = shaping_rows / gauge.rows

            circumference_per_side = (straight_rows / gauge.rows) + hypotenuse(
                width_of_slope, height_of_slope
            )

            total_circumference = circumference_per_side * 2

            neckline.pickup_stitches = round(
                total_circumference * gauge.stitches,
                rounding["neckline_pickup_stitches"],
            )
            neckline.pickup_stitches += neckline.extra_bindoffs

        return neckline


class CrewNeck(Neckline):

    depth = NonNegFloatField(
        blank=True, null=True, help_text="Depth, in inches, of the entire neckline"
    )

    marker_before_center_stitch = models.BooleanField(
        help_text="Whether the center marker should be before the center "
        "stitch (True), or between the center stitches (False)",
        default=False,
    )

    bindoffs_before_marker = NonNegSmallIntegerField(
        help_text="Bindoffs to work before center marker"
    )

    center_bindoffs = NonNegSmallIntegerField(help_text="Number of center bindoffs")

    neck_edge_decreases = NonNegSmallIntegerField(
        help_text="Number of neck-edge bindoffs on side of neck"
    )

    rs_edge_decreases = NonNegSmallIntegerField(
        help_text="Number of RS-edge bindoffs on side of neck"
    )

    pickup_stitches = NonNegSmallIntegerField(help_text="Number of stitches to pick up")

    style_id = SDC.NECK_CREW

    def total_depth(self):
        return self.depth

    def depth_to_shaping_end(self):
        if not self.empty():
            return self.total_depth() - self._shaping_height()
        else:
            return None

    def stitches_across_neckline(self):
        return self.center_bindoffs + (
            2 * (self.neck_edge_decreases + self.rs_edge_decreases)
        )

    def stitches_to_pick_up(self):
        return self.pickup_stitches

    def center_bindoffs_cardigan(self):
        assert self.center_bindoffs % 2 == 0
        return_me = self.center_bindoffs / 2.0
        return int(return_me)

    def rows_in_pullover_shaping(self):
        return_me = 0
        if self.center_bindoffs:
            return_me += 1  # initial bind-off row
        if self.rs_edge_decreases:
            if self.neck_edge_decreases:
                return_me += self.neck_edge_decreases
                if self.neck_edge_decreases % 2 == 0:
                    return_me += 1  # add one for the gap row between the neck_edge_decreases and rs_edge_decreases
                return_me += (
                    self.rs_edge_decreases * 2
                ) - 1  # subtract last 'work even' row
            else:
                return_me += (
                    self.rs_edge_decreases * 2
                )  #  Subtract last 'work even' row, but add skip row at the start
        else:
            if self.no_rs_decreases_two_stitch_bindoffs():
                if self.no_rs_decreases_one_stitch_bindoffs():
                    return_me += self.no_rs_decreases_two_stitch_bindoffs() * 2
                    return_me += self.no_rs_decreases_one_stitch_bindoffs()
                else:
                    return_me += (
                        self.no_rs_decreases_two_stitch_bindoffs() * 2
                    )  # count starts with an implicit 'work even' row
            else:
                if self.no_rs_decreases_one_stitch_bindoffs():
                    return_me += self.no_rs_decreases_one_stitch_bindoffs()

        return return_me

    def rows_in_cardigan_shaping(self, neckline_parity):
        return_me = 0
        if self.center_bindoffs:
            return_me += 1  # initial bind-off row
        if self.rs_edge_decreases:
            if self.neck_edge_decreases:
                return_me += self.neck_edge_decreases
            # Are we now on a RS row? If not, we need to add a skip row
            this_row_parity = (
                neckline_parity
                if (return_me % 2 == 0)
                else reverse_parity(neckline_parity)
            )
            if this_row_parity == WS:
                # Add the skip row
                return_me += 1

            return_me += (
                self.rs_edge_decreases * 2
            ) - 1  # subtract last 'work even' row
        else:
            if self.no_rs_decreases_two_stitch_bindoffs():
                if self.no_rs_decreases_one_stitch_bindoffs():
                    return_me += self.no_rs_decreases_two_stitch_bindoffs() * 2
                    return_me += self.no_rs_decreases_one_stitch_bindoffs()
                else:
                    return_me += (
                        self.no_rs_decreases_two_stitch_bindoffs() * 2
                    )  # count starts with an implicit 'work even' row
            else:
                if self.no_rs_decreases_one_stitch_bindoffs():
                    return_me += self.no_rs_decreases_one_stitch_bindoffs()

        return return_me

    def empty(self):
        return not any(
            [
                self.center_bindoffs > 0,
                self.neck_edge_decreases > 0,
                self.rs_edge_decreases > 0,
            ]
        )

    # These next two methods are a bit of a kludge, but seemed the best way to
    # accomodate a change. *Previously*, the field
    # rs_edge_decreases was required to be non-zero. *Now*, that field is
    # allowed to be made zero by compression, but we need to change the
    # template language when it is. The new language needs the value for
    #
    # * (neck_edge_decreases / 4), rounded to the nearest integer, and
    #
    # * Number of neck_edge_decreases, minus (2* above).
    #
    # Rather than to add these
    # through a migration, it seems better to compute them via methods.

    def no_rs_decreases_two_stitch_bindoffs(self):
        """
        Used by templates. Will be None unless all the decreases are neck-edge
        decreases.
        """
        if self.rs_edge_decreases:
            return None
        else:
            half_neck_edge_decreases_rounded_even = round(
                self.neck_edge_decreases / 2, ROUND_ANY_DIRECTION, 2
            )
            return int(half_neck_edge_decreases_rounded_even / 2)

    def no_rs_decreases_one_stitch_bindoffs(self):
        """
        Used by templates.
        """
        if self.rs_edge_decreases:
            return None
        else:
            return int(
                self.neck_edge_decreases
                - (2 * self.no_rs_decreases_two_stitch_bindoffs())
            )

    def _shaping_height(self):
        return self.rows_in_pullover_shaping() / self.row_gauge

    def area(self):

        return_me = 0

        # There are a number of possible trapezoids that may be present,
        # and then a straight rectangle at the end. To find the trapezoids,
        # we need to break into two cases

        if self.rs_edge_decreases:

            # Two trapzoids: one neck_edge decreases and one for
            # rs_edge_decreases

            neck_edge_top_stitches = sum(
                [self.center_bindoffs, 2 * self.neck_edge_decreases]
            )
            neck_edge_trapezoid_area = _trapezoid_area_stitches_and_rows(
                self.center_bindoffs,
                neck_edge_top_stitches,
                self.neck_edge_decreases,
                self.row_gauge,
                self.stitch_gauge,
            )
            return_me += neck_edge_trapezoid_area

            rs_edge_top_stitches = sum(
                [neck_edge_top_stitches, 2 * self.rs_edge_decreases]
            )
            rs_edge_height_rows = 2 * self.rs_edge_decreases
            rs_edge_area = _trapezoid_area_stitches_and_rows(
                neck_edge_top_stitches,
                rs_edge_top_stitches,
                rs_edge_height_rows,
                self.row_gauge,
                self.stitch_gauge,
            )
            return_me += rs_edge_area

        else:

            # Two trapezoids: one for  no_rs_decreases_two_stitch_bindoffs
            # and one for no_rs_decreases_one_stitch_bindoffs

            if self.no_rs_decreases_two_stitch_bindoffs() is None:
                no_rs_two_bindoffs = 0
            else:
                no_rs_two_bindoffs = self.no_rs_decreases_two_stitch_bindoffs()

            no_rs_two_top_stitches = sum([self.center_bindoffs, 4 * no_rs_two_bindoffs])
            no_rs_two_height_rows = 2 * no_rs_two_bindoffs
            no_rs_two_area = _trapezoid_area_stitches_and_rows(
                self.center_bindoffs,
                no_rs_two_top_stitches,
                no_rs_two_height_rows,
                self.row_gauge,
                self.stitch_gauge,
            )
            return_me += no_rs_two_area

            if self.no_rs_decreases_one_stitch_bindoffs() is None:
                no_rs_one_bindoffs = 0
            else:
                no_rs_one_bindoffs = self.no_rs_decreases_one_stitch_bindoffs()

            no_rs_one_top_stitches = sum(
                [no_rs_two_top_stitches, 2 * no_rs_one_bindoffs]
            )
            no_rs_one_area = _trapezoid_area_stitches_and_rows(
                no_rs_two_top_stitches,
                no_rs_one_top_stitches,
                no_rs_one_bindoffs,
                self.row_gauge,
                self.stitch_gauge,
            )
            return_me += no_rs_one_area

        # Straight portion
        return_me += rectangle_area(self._width(), self.depth_to_shaping_end())

        return return_me

    @classmethod
    def make(cls, stitches_goal, depth_goal, gauge, rounding, ease_tolerances):
        """
        Make a CrewNeck instance. Typical usage:

          bn = CrewNeck.make(...)

        * stitches_goal: the number of stitches removed during the shaping of
          this neckline. Note: in Cardgigans, may be different than the actual
          stitch-width of the neck opening. Also, this argument is
          non-negotiable. If the neckline does not have this exact number of
          stitches, the pattern will be wrong.

        * depth_goal: The desired height (in inches) from the lowest row of
          neckline shaping to the shoulder bindoffs. Note: the neck might
          end up actually deeper than this, but should not be shallower.

        * gauge: the Gauge object to use.

        * rounding: A dict holding the rounding directions to be used.

        * ease_tolerances: Unused. Present only for historical reasons.

        """

        neckline = CrewNeck()
        neckline.row_gauge = gauge.rows
        neckline.stitch_gauge = gauge.stitches

        # Number of stitches on either side of initial bindoffs must be the
        # same, so bind off enough stitches to make remaining stitches an
        # even number
        if is_odd(stitches_goal):
            neckline.marker_before_center_stitch = True
            neckline.center_bindoffs = round(
                stitches_goal / 2, direction=ROUND_DOWN, multiple=2, mod=1
            )
            if neckline.center_bindoffs < 1:
                neckline.center_bindoffs = 1
        else:
            neckline.marker_before_center_stitch = False
            neckline.center_bindoffs = round(
                stitches_goal / 2, direction=ROUND_DOWN, multiple=2, mod=0
            )
            if neckline.center_bindoffs < 0:
                neckline.center_bindoffs = 0

        neckline.bindoffs_before_marker = int(
            round(neckline.center_bindoffs / 2, ROUND_UP)
        )

        stitches_per_side = (stitches_goal - neckline.center_bindoffs) / 2

        neckline.neck_edge_decreases = round(stitches_per_side / 2, ROUND_UP)
        neckline.rs_edge_decreases = stitches_per_side - neckline.neck_edge_decreases

        # Try to compress the shaping to fit within the depth_goal
        while all(
            [neckline.rs_edge_decreases > 0, neckline._shaping_height() > depth_goal]
        ):
            neckline.rs_edge_decreases -= 1
            neckline.neck_edge_decreases += 1

        if neckline.empty():
            # neckline is empty/void:
            neckline.depth = None
            neckline.pickup_stitches = 0

        else:

            neckline.depth = max([depth_goal, neckline._shaping_height()])

            # How many stitches to pick up in this neckline?
            # Find distance around neckline for center bindoffs,
            # rs-decreases, neck=edge decreases, and straight working

            center_bindoffs_length = neckline.center_bindoffs / gauge.stitches

            rows_in_neck = round(neckline.depth * gauge.rows, ROUND_DOWN)

            neck_edge_decrease_rows = neckline.neck_edge_decreases
            rs_decreases_rows = neckline.rs_edge_decreases * 2
            straight_rows = rows_in_neck - neck_edge_decrease_rows - rs_decreases_rows

            # neck-edge working
            neck_edge_width = neckline.neck_edge_decreases / gauge.stitches
            neck_edge_height = neck_edge_decrease_rows / gauge.rows
            neck_edge_circ = hypotenuse(neck_edge_width, neck_edge_height)

            # rs-edge working
            rs_edge_width = neckline.rs_edge_decreases / gauge.stitches
            rs_edge_height = rs_decreases_rows / gauge.rows
            rs_edge_circ = hypotenuse(rs_edge_width, rs_edge_height)

            # striaght working
            straight_work_circ = straight_rows / gauge.rows

            total_circumference = sum(
                [
                    center_bindoffs_length,
                    2 * neck_edge_circ,
                    2 * rs_edge_circ,
                    2 * straight_work_circ,
                ]
            )

            neckline.pickup_stitches = int(
                round(
                    total_circumference * gauge.stitches,
                    rounding["neckline_pickup_stitches"],
                )
            )

        #        neckline.shaping_height = neck_edge_height + rs_edge_height

        return neckline


class ScoopNeck(Neckline):

    marker_before_center_stitch = models.BooleanField(
        help_text="Whether center marker should go before center stitch "
        "(True) or between center stitches.",
        default=False,
    )

    bindoff_stitches_before_marker = NonNegSmallIntegerField(
        help_text="Number of stitches before center marker at which to start "
        "binding off."
    )

    y_bindoffs = NonNegSmallIntegerField(
        help_text="First bindoffs on the side of the neck"
    )

    z_bindoffs = NonNegSmallIntegerField(
        help_text="Second bindoffs on the side of the neck"
    )

    q_bindoffs = NonNegSmallIntegerField(
        help_text="final bindoffs on the side of the neck"
    )

    _total_depth = NonNegFloatField(
        blank=True, null=True, help_text="Depth of the neckline, in inches"
    )

    #    shaping_height = NonNegFloatField(
    #        help_text = "Vertical distance between start and shaping end")

    pickup_stitches = NonNegSmallIntegerField(
        blank=True, null=True, help_text="Number of stitches to pick up"
    )

    style_id = SDC.NECK_SCOOP

    def area(self):
        # Break into four areas:
        # The (bottom) trapezoid of the 'y' bindoffs
        # The trapezoid of the 'z' bindoffs
        # The trapezoid of the 'q' bindoffs
        # The (top) rectangle

        return_me = 0

        # y bindoffs

        y_top_stitches = sum([self.initial_bindoffs, 2 * self.y_bindoffs])
        y_height_rows = self.y_bindoffs
        y_area = _trapezoid_area_stitches_and_rows(
            self.initial_bindoffs,
            y_top_stitches,
            y_height_rows,
            self.row_gauge,
            self.stitch_gauge,
        )

        # Z bindoffs
        z_top_stitches = sum([y_top_stitches, 2 * self.z_bindoffs])
        z_height_rows = 2 * self.z_bindoffs
        z_area = _trapezoid_area_stitches_and_rows(
            y_top_stitches,
            z_top_stitches,
            z_height_rows,
            self.row_gauge,
            self.stitch_gauge,
        )

        # Q bindoffs
        q_height_rows = 4 * self.q_bindoffs
        q_area = _trapezoid_area_stitches_and_rows(
            z_top_stitches,
            self.stitches_across_neckline(),
            q_height_rows,
            self.row_gauge,
            self.stitch_gauge,
        )

        # Rectangle
        straight_height = self.depth_to_shaping_end()
        # If there are q_bindoffs, then we've already counted 3 straight rows above.
        # We need to take them out:
        if self.q_bindoffs:
            straight_height -= 3 / self.row_gauge
        straight_area = rectangle_area(straight_height, self._width())

        return sum([y_area, z_area, q_area, straight_area])

    def empty(self):
        return not any(
            [
                self.y_bindoffs > 0,
                self.z_bindoffs > 0,
                self.q_bindoffs > 0,
                self.bindoff_stitches_before_marker > 0,
            ]
        )

    @property
    def initial_bindoffs(self):
        return_me = 2 * self.bindoff_stitches_before_marker
        if self.marker_before_center_stitch:
            # take out the extra stitch
            return_me -= 1
        return return_me

    def total_depth(self):
        return self._total_depth

    def depth_to_shaping_end(self):
        if not self.empty():
            return self.total_depth() - self._shaping_height
        else:
            return None

    def stitches_across_neckline(self):
        return sum(
            [
                self.initial_bindoffs,
                2 * self.y_bindoffs,
                2 * self.z_bindoffs,
                2 * self.q_bindoffs,
            ]
        )

    def stitches_to_pick_up(self):
        return self.pickup_stitches

    def rows_in_pullover_shaping(self):

        return_me = 0

        if any(
            [self.initial_bindoffs, self.y_bindoffs, self.z_bindoffs, self.q_bindoffs]
        ):
            return_me += 1  # initial row.

        if self.y_bindoffs:
            return_me += self.y_bindoffs
            if self.z_bindoffs or self.q_bindoffs:
                # there may be a 'skip' row between y decreases and next decreases
                if (self.y_bindoffs % 2) == 0:
                    return_me += 1
        else:
            if self.z_bindoffs or self.q_bindoffs:
                return_me += 1  # for skip row before first z/q decrease

        if self.z_bindoffs:
            return_me += self.z_bindoffs * 2
            if not self.q_bindoffs:
                # We need to subtract off the last 'work even' row
                return_me -= 1

        if self.q_bindoffs:
            # We need to subtract off the last three 'work even' rows
            return_me += (self.q_bindoffs * 4) - 3

        return return_me

    def rows_in_cardigan_shaping(self, neckline_parity):

        return_me = 0

        if any(
            [self.initial_bindoffs, self.y_bindoffs, self.z_bindoffs, self.q_bindoffs]
        ):
            return_me += 1  # initial row.

        if self.y_bindoffs:
            return_me += self.y_bindoffs

        if self.z_bindoffs:
            # Are we on a RS row? If so, add a skip row
            this_row_parity = (
                neckline_parity
                if (return_me % 2 == 0)
                else reverse_parity(neckline_parity)
            )
            if this_row_parity == WS:
                return_me += 1

            return_me += self.z_bindoffs * 2
            if not self.q_bindoffs:
                # We need to subtract off the last 'work even' row
                return_me -= 1

        if self.q_bindoffs:
            # We need to subtract off the last three 'work even' rows
            return_me += (self.q_bindoffs * 4) - 3

        return return_me

    @property
    def _shaping_height(self):
        return self.rows_in_pullover_shaping() / self.row_gauge

    def initial_bindoffs_cardigan(self):
        assert (self.initial_bindoffs % 2) == 0
        return int(self.initial_bindoffs / 2)

    @classmethod
    def make(cls, stitches_goal, depth_goal, gauge, rounding, ease_tolerances):
        """
        Make a ScoopNeck instance. Typical usage:

          bn = ScoopNeck.make(...)

        * stitches_goal: the number of stitches removed during the shaping of
          this neckline. Note: in Cardgigans, may be different than the actual
          stitch-width of the neck opening. Also, this argument is
          non-negotiable. If the neckline does not have this exact number of
          stitches, the pattern will be wrong.

        * depth_goal: The desired height (in inches) from the lowest row of
          neckline shaping to the shoulder bindoffs. Note: the neck might
          end up actually deeper than this, but should not be shallower.

        * gauge: the Gauge object to use.

        * rounding: A dict holding the rounding directions to be used.

        * ease_tolerances: Unused. Present only for historical reasons.

        """

        neckline = ScoopNeck()
        neckline.row_gauge = gauge.rows
        neckline.stitch_gauge = gauge.stitches

        XGOAL = 0.4
        YGOAL = 0.4
        ZGOAL = 0.5

        if is_odd(stitches_goal):
            neckline.marker_before_center_stitch = True
        else:
            neckline.marker_before_center_stitch = False

        goal_parity = stitches_goal % 2
        x = round(stitches_goal * XGOAL, ROUND_DOWN, 2, goal_parity)
        # Need to keep x from dropping below 0. Actually, if goal_partiy is 1,
        # needs to be at least 1. If goal_partiy is 0, x can be 0
        if x < goal_parity:
            x = goal_parity
        b = (stitches_goal - x) / 2
        y = round(YGOAL * b, ROUND_UP)
        c = b - y
        z = round(c * ZGOAL, ROUND_UP)
        q = b - y - z

        neckline.bindoff_stitches_before_marker = round(x / 2, ROUND_UP)
        neckline.y_bindoffs = y
        neckline.z_bindoffs = z
        neckline.q_bindoffs = q

        # Can now determine if the neckline is empty/void:

        if neckline.empty():
            neckline._total_depth = None

        else:
            # If the shaping is higher than the depth_goal, then the depth of the
            # neckline needs to increase to accomodate. Otherwise, we can just set
            # it to the depth goal.
            neckline._total_depth = max([depth_goal, neckline._shaping_height])

        #
        # And now, the crazy computations for the pickup-stitches
        #

        circumference = 0

        # initial bindoffs
        circumference += neckline.initial_bindoffs / gauge.stitches

        # y decreases
        y_width = neckline.y_bindoffs / gauge.stitches
        y_height = neckline.y_bindoffs / gauge.rows
        y_hyp = hypotenuse(y_width, y_height)
        circumference += 2 * y_hyp

        # z decreases
        z_width = neckline.z_bindoffs / gauge.stitches
        z_height = (2 * neckline.z_bindoffs) / gauge.rows
        z_hyp = hypotenuse(z_width, z_height)
        circumference += 2 * z_hyp

        # q decreases
        q_width = neckline.q_bindoffs / gauge.stitches
        q_height = (4 * neckline.q_bindoffs) / gauge.rows
        q_hyp = hypotenuse(q_width, q_height)
        circumference += 2 * q_hyp

        # work-straight
        if neckline.total_depth() is not None:
            straight_dist = neckline.depth_to_shaping_end()
            # Note: we already counted 3 rows of straight in the q-stitches above,
            # so we need to substract them here.
            if neckline.q_bindoffs:
                straight_dist -= 3 / neckline.row_gauge

            circumference += 2 * straight_dist

        neckline.pickup_stitches = round(circumference * gauge.stitches)

        return neckline


class BoatNeck(Neckline):

    bottom_bindoffs = NonNegSmallIntegerField(
        help_text="Total number of stitches to bind off on first row."
    )

    side_bindoffs = NonNegSmallIntegerField(
        help_text="Total number of stitches to decrease on sides of neck."
    )

    neckline_depth = NonNegFloatField(
        null=True, blank=True, help_text="Depth of the neckline, in inches"
    )

    pickup_stitches = NonNegSmallIntegerField(help_text="Number of stitches to pick up")

    # Methods for the template
    def marker_before_center_stitch(self):
        return is_odd(self.bottom_bindoffs)

    def bindoff_stitches_before_marker(self):
        return int(round(self.bottom_bindoffs / 2, ROUND_DOWN))

    def bottom_bindoffs_cardigan(self):
        assert self.bottom_bindoffs % 2 == 0
        return_me = self.bottom_bindoffs / 2.0
        return int(return_me)

    # Neckline API

    def total_depth(self):
        return self.neckline_depth

    def depth_to_shaping_end(self):
        if not self.empty():
            return self.total_depth() - self._shaping_height()
        else:
            return None

    def stitches_across_neckline(self):
        return self.bottom_bindoffs + (2 * self.side_bindoffs)

    def stitches_to_pick_up(self):
        return self.pickup_stitches

    def area(self):
        return rectangle_area(self._width(), self.total_depth())

    def empty(self):
        return not any([self.bottom_bindoffs > 0, self.side_bindoffs > 0])

    style_id = SDC.NECK_BOAT

    def rows_in_pullover_shaping(self):
        return_me = 0
        if self.bottom_bindoffs:
            return_me += 1  # initial bind-off row
        if self.side_bindoffs:
            return_me += (self.side_bindoffs * 2) - 1  # subtract final 'work even' row
        return return_me

    def rows_in_cardigan_shaping(self, neckline_parity):
        return_me = 0
        if self.bottom_bindoffs:
            return_me += 1  # initial bind-off row
        if self.side_bindoffs:
            if neckline_parity == RS:
                return_me += 1  # one for the skip row before the side bindoffs
            return_me += (self.side_bindoffs * 2) - 1  # subtract final 'work even' row
        return return_me

    def _shaping_height(self):
        return self.rows_in_pullover_shaping() / self.row_gauge

    @classmethod
    def make(cls, stitches_goal, depth_goal, gauge, rounding, ease_tolerances):
        """
        Make a BoatNeck instance. Typical usage:

          bn = BoatNeck.make(...)

        * stitches_goal: the number of stitches removed during the shaping of
          this neckline. Note: in Cardgigans, may be different than the actual
          stitch-width of the neck opening. Also, this argument is
          non-negotiable. If the neckline does not have this exact number of
          stitches, the pattern will be wrong.

        * depth_goal: The desired height (in inches) from the lowest row of
          neckline shaping to the shoulder bindoffs. Note: the neck might
          end up actually deeper than this, but should not be shallower.

        * gauge: the Gauge object to use.

        * rounding: A dict holding the rounding directions to be used.

        * ease_tolerances: Unused. Present only for historical reasons.

        """

        neckline = cls()
        neckline.row_gauge = gauge.rows
        neckline.stitch_gauge = gauge.stitches

        SIDE_BINDOFF_RATIO = 0.1

        neckline.side_bindoffs = int(
            max([round(stitches_goal * SIDE_BINDOFF_RATIO, ROUND_DOWN), 0])
        )
        neckline.bottom_bindoffs = int(stitches_goal - (2 * neckline.side_bindoffs))

        # Can now determine if neckline is empty/void:

        if not neckline.empty():

            neckline.neckline_depth = max([depth_goal, neckline._shaping_height()])
        else:
            neckline.neckline_depth = None

        # Pickup-stitch computation: quick and dirty (and accurate enough)
        pickup_stitches_float = sum(
            [neckline.bottom_bindoffs, 2 * neckline.side_bindoffs]
        )
        if neckline.total_depth() is not None:
            pickup_stitches_float += 2 * neckline.total_depth() * neckline.stitch_gauge

        neckline.pickup_stitches = round(pickup_stitches_float)

        return neckline


class TurksAndCaicosNeck(BoatNeck):
    """
    Neckline for the Turks and Caicos pattern. Essentially a BoatNeck of
    depth 2.5, but with a rectangular lace panel centered below it.
    Note: DO NOT USE IN ANY PATTERN BUT TURKS AND CAICOS. This model
    has a lot of implicit assumptions built in to it, such as:

    * The garment is a pullover,
    * The neckline-depth is at least 6 inches, and
    * The stitch-width is at least 15 stitches.

    (Violations of the last two will produce AssertionErrors. The first will
    not, unfortunately.)

    Why is this even a model? Why not define the Turks and Caicos neckline
    to use a boatneck and use design-specific templates to do the rest?
    Unfortunately, this won't work. To get the lace-pattern instructions to
    start at the right time, the 'depth' of this neckline has to be the
    bottom of the lace panel. But if use a BoatNeck of that depth, the number
    of pickup-stitches is all wrong. We *could* play even more tricks in the
    neck-trim template to adjust, but the words of PEP 20 haunt me: "explicit
    is better than implicit." If we need to put this complexity somewhere, let
    it be explicit in the source-base rather than implicit & hidden away in
    the database.
    """

    style_id = SDC.NECK_TURKS_AND_CAICOS

    lace_stitches = NonNegSmallIntegerField(
        help_text="Total number of stitches across lace element"
    )

    boat_portion_depth = 2.5
    minimum_depth = 5.5
    minimum_stitches = 15

    @classmethod
    def make(cls, stitches_goal, depth_goal, gauge, rounding, ease_tolerances):

        assert depth_goal >= cls.minimum_depth
        assert stitches_goal >= cls.minimum_stitches
        tcn = super(TurksAndCaicosNeck, cls).make(
            stitches_goal, cls.boat_portion_depth, gauge, rounding, ease_tolerances
        )
        tcn.neckline_depth = depth_goal
        tcn.lace_stitches = int(
            round(tcn.stitches_across_neckline() * 0.80, ROUND_DOWN, multiple=12, mod=0)
        )
        return tcn

    def depth_to_shaping_end(self):
        return self.boat_portion_depth - self._shaping_height()

    def lace_height_in_inches(self):
        return self.total_depth() - self.boat_portion_depth

    def lace_height_in_rows(self):
        return int(
            round(
                self.lace_height_in_inches() * self.row_gauge,
                ROUND_DOWN,
                multiple=2,
                mod=1,
            )
        )

    def area(self):
        # Remember, this returns the area *removed* from the piece.
        return rectangle_area(self._width(), self.boat_portion_depth)
