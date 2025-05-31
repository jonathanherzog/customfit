"""
Created on Jun 23, 2012
"""

import logging

LOGGER = logging.getLogger(__name__)


from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    height_and_gauge_to_row_count,
    round,
)
from customfit.helpers.row_parities import ANY, RS, WS

from ...helpers.magic_constants import BUTTONHOLE_MARGIN_GOAL, BUTTONHOLE_MARGIN_MIN


class ButtonBand(object):
    """
    Class for button-bands. Not a model, but included in the models directory
    for consistency. Dynamically created by a Cardigan front piece for
    for rendering the finishing instructions. As you read this, remember that
    the button band is knit *sideways* to all the other pieces. That is, they
    are knit from one side of the body to the other, not up to the
    shoulders.
    """

    STITCHES_IN_BUTTONHOLE = 2

    def __init__(self, height, length, stitch_pattern, gauge, num_buttonholes):
        assert height > 0
        assert length > 0
        self.height = height
        self.stitch_pattern = stitch_pattern
        self.gauge = gauge

        self.stitches = int(round(length * self.gauge.stitches, ROUND_ANY_DIRECTION))
        self.num_buttonholes = num_buttonholes

        if self.num_buttonholes < 5:
            self.evenly_spaced_buttonholes = False
            self.margin_stitches = None
            self.inter_buttonhole_stitches = None
        else:
            self.evenly_spaced_buttonholes = True

            (margin_stitches, stitches_per_interval) = (
                self._estimate_buttonhole_spacing(ROUND_UP)
            )

            margin_height = margin_stitches / self.gauge.stitches

            if margin_height < BUTTONHOLE_MARGIN_MIN:
                (margin_stitches, stitches_per_interval) = (
                    self._estimate_buttonhole_spacing(ROUND_DOWN)
                )

            self.margin_stitches = int(margin_stitches)
            self.inter_buttonhole_stitches = int(stitches_per_interval)

    def _estimate_buttonhole_spacing(self, rounding_direction):
        # Note: we reproduce much of this logic in the the buttonband-spacer calculator,
        # but the use-cases for button-spacing turns out to be different enough (between
        # that calculator and here) that we decided not to try to unify the code.

        ideal_margin_stitches = self.gauge.stitches * BUTTONHOLE_MARGIN_GOAL

        stitches_for_buttonholes = self.stitches - (2 * ideal_margin_stitches)

        stitches_for_between_buttonholes = stitches_for_buttonholes - (
            self.STITCHES_IN_BUTTONHOLE * self.num_buttonholes
        )

        num_intervals = self.num_buttonholes - 1

        stitches_per_interval = round(
            stitches_for_between_buttonholes / num_intervals, rounding_direction
        )

        actual_margin_stitches = (
            self.stitches
            - sum(
                [
                    self.STITCHES_IN_BUTTONHOLE * self.num_buttonholes,
                    num_intervals * stitches_per_interval,
                ]
            )
        ) / 2

        return (actual_margin_stitches, stitches_per_interval)

    def half_height(self):
        """
        Height (in inches) from cast-on to buttonhole row.
        """
        return self.height / 2

    def half_height_in_rows(self):
        """
        Height (in inches) from cast-on to buttonhole row, placing no
        assumptions on the parity of the row
        """
        height = self.half_height()
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, ANY)

    def half_height_in_rows_ws(self):
        """
        Height (in inches) from cast-on to buttonhole row, assuming that
        the row is a WS row.
        """
        height = self.half_height()
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, WS)

    def half_height_in_rows_rs(self):
        """
        Height (in inches) from cast-on to buttonhole row, assuming that
        the row is a RS row.
        """
        height = self.half_height()
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, RS)

    def height_in_rows(self):
        """
        Height (in inches) from cast-on to the bindoff row, placing no
        assumptions on the parity of the row
        """
        height = self.height
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, ANY)

    def height_in_rows_ws(self):
        """
        Height (in inches) from cast-on to bindoff row, assuming that
        the row is a WS row.
        """
        height = self.height
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, WS)

    def height_in_rows_rs(self):
        """
        Height (in inches) from cast-on to bindoff row, assuming that
        the row is a RS row.
        """
        height = self.height
        row_gauge = self.gauge.rows
        return height_and_gauge_to_row_count(height, row_gauge, RS)

    def edging_stitch_patterntext(self):
        """
        Return patterntext-appropriate name of the stitch pattern used
        for the button band.
        """
        return self.stitch_pattern.patterntext

    def stitches_before_first_buttonhole(self):
        """
        If providing evenly-spaced buttonholes, the number of stitches before
        the first buttonhole starts.
        """
        if self.margin_stitches:
            return int(round(self.margin_stitches, ROUND_DOWN))
        else:
            return None

    def num_interior_buttonholes(self):
        """
        If providing evenly-spaced buttonholes, the number of buttonholes
        provided *minus* the top and bottom ones.
        """
        if self.evenly_spaced_buttonholes:
            return self.num_buttonholes - 2
        else:
            return None

    def area(self):
        """
        Total area (in sq in) for both buttonband pieces-- one for each side
        of the body.
        """
        width = float(self.stitches) / float(self.gauge.stitches)
        return 2 * self.height * width


class VNeckButtonBand(ButtonBand):
    """
    Class for V-neck button-bandsm which include the neck edging as well.
    """

    def __init__(
        self,
        height,
        length,
        stitch_pattern,
        gauge,
        num_buttonholes,
        neckline_pickup_stitches,
    ):
        # First, do the straightforward init, as if stitch-repeats were not
        # a concern
        super(VNeckButtonBand, self).__init__(
            height, length, stitch_pattern, gauge, num_buttonholes
        )
        self.neckline_pickup_stitches = neckline_pickup_stitches

        # Now, see if we need to adjust the pickup-countss to accommodate
        # the edging-stitch requirements
        repeats = stitch_pattern.get_repeats_spec()
        if repeats:
            x_mod = repeats.x_mod
            mod_y = repeats.mod_y
        else:
            x_mod = 0
            mod_y = 1
        current_sum = sum([self.neckline_pickup_stitches, 2 * self.stitches])
        ideal_sum = round(current_sum, ROUND_ANY_DIRECTION, mod_y, x_mod)
        difference = ideal_sum - current_sum

        if (difference // 3) != 0:
            self.stitches += difference // 3
            self.neckline_pickup_stitches += difference // 3
        if (difference % 3) == 2:
            self.stitches += 1
        if (difference % 3) == 1:
            self.neckline_pickup_stitches += 1

    def total_veeneck_cardigan_stitches(self):
        return sum([self.neckline_pickup_stitches, 2 * self.stitches])

    def area(self):
        """
        Total area (in sq in) for buttonband: up one side, around neck,
        back down the other side
        """
        width = float(self.total_veeneck_cardigan_stitches()) / float(
            self.gauge.stitches
        )
        return self.height * width
