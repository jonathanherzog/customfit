import logging

from django.db import models

from customfit.fields import NonNegFloatField, StrictPositiveSmallIntegerField
from customfit.helpers.math_helpers import (
    ROUND_DOWN,
    ROUND_UP,
    _find_best_approximation,
    round,
)

from ...exceptions import ArmholeShapingError
from ...helpers.magic_constants import (
    BACKMARKERRATIO,
    HALF_INCH,
    MAX_ARMHOLE_SHAPING_HEIGHT_PERCENTAGE,
    ONEINCH,
)
from ..schematics import (
    GradedSweaterBackSchematic,
    GradedVestBackSchematic,
    SweaterBackSchematic,
    VestBackSchematic,
)
from .half_body_piece_mixin import GradedHalfBodyPieceMixin, HalfBodyPieceMixin
from .necklines import BackNeckline

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Developer's notes:
#
# 1. Errors: use asserts to assert things that should be guaranteed by
#    other models (such as Gauge or GarmentParameters) or by prior statements.
#    For other errors:
#    raise a ValidationError or ValueError as soon as possible for ease of
#    debugging. We may later want to keep make() from raising exceptions for
#    reasons yet to be determined, but for now, let's keep things pythonic.
#
# 2. Use TODO: in comments to flag unresolved issues or tasks.
#
# 3. The division of work into the _compute_* functions may seem somewhat
#    arbitrary, but was chosen to divide the code usable by SweaterFront
#    from the code not usable by SweaterFront. This may have been a mistake
#    in that that division turned out to be a moving target. But time will
#    tell. In the meantime: before changing any of those functions,
#    check in SweaterFront to see if the function is also used there.


# TODO: document the heck out of everything.


# Helper function, used in Backpiece and in the armcap-shaping calculator


def compute_armhole_circumference(
    gauge, armhole_x, armhole_y, armhole_z, armhole_depth
):
    """
    Returns Inches of armhole circumferences (front and back) in inches.
    """

    # armhole X and Y
    armhole_x_distance = float(armhole_x) / gauge.stitches

    armhole_y_distance = float(armhole_y) / gauge.stitches

    # armhole Z
    armhole_z_hyp = pow(
        pow(float(armhole_z) / gauge.stitches, 2)
        + pow(float(armhole_z * 2) / gauge.rows, 2),
        0.5,
    )

    # armhole even to shoulder

    if armhole_y:
        xy_rows = 2
    else:
        xy_rows = 1
    vert_dist = armhole_depth - (float(xy_rows + (2 * armhole_z)) / gauge.rows)

    return_me = sum([armhole_x_distance, armhole_y_distance, armhole_z_hyp, vert_dist])

    return return_me


class BaseBackPiece(models.Model):

    # Note: for FrontPieces, cross_chest_stitches is a *property* not a field.
    # Why? It has to do with the differences between the two models. For
    # back pieces, we don't need to worry about necklines going below armhole
    # shaping, but we do need to ensure that cross-chest stitches respect
    # repeats. So for back-pieces, it makes sense to compute the chest-
    # stitches first and let the armhole stitches be derived from that
    # (and the bust stitches). For front-pieces, however, those pesky
    # necklines can go below armholes-- and so cross-chest stitches
    # might be None (which we want to explicitly prohibit for back pieces)
    # Also, front pieces must have the same armhole shaping as back pieces,
    # so it makes sense for front-pieces to derive cross-chest stitches from
    # the (predetermined) bust stitches and the (predetermined) armhole shaping.

    class Meta:
        abstract = True

    cross_chest_stitches = StrictPositiveSmallIntegerField(
        help_text="Number of stitches left after armhole shaping."
    )

    actual_neck_opening = NonNegFloatField(
        help_text="Number of inches across neck opening"
    )

    def side_one_name(self):
        return "Left"

    def side_two_name(self):
        return "Right"

    def _inner_make(self, rounding_directions, ease_tolerances, graded=False):
        """
        Helper function to do the real work of make, but to contain code
        that can be re-used in VestBack.
        """
        sb_rounding_directions = rounding_directions["sweater_back"]
        self._compute_values(sb_rounding_directions, ease_tolerances, graded=graded)

    def _compute_values(self, rounding_directions, ease_tolerances, graded):
        """
        Internal function used to calcuate all number of the piece from inputs.
        Simply calls other _compute_* functions to do the real work.
        """
        self._compute_set_up(rounding_directions, ease_tolerances)
        self._compute_waist_and_bust_shaping(
            rounding_directions, ease_tolerances, graded
        )
        self._compute_marker_placement()
        self._compute_bust_through_armhole(rounding_directions, ease_tolerances)
        self._add_cable_stitches()
        self._compute_neckline_and_shoulders(rounding_directions, ease_tolerances)

    def _compute_set_up(self, rounding_directions, ease_tolerances):
        """
        Sets the ratio governing the location at which standard
        increase/decrease markers will be set.

        Not used by SweaterBack, as it uses a different ratio.
        """
        self.marker_ratio = BACKMARKERRATIO

    def _compute_bust_through_armhole(self, rounding_directions, ease_tolerances):
        """
        Compute fields above bust through armhole shaping.
        """

        # =======================================================================
        # Okay, go even to the armholes. Then compute the cross-chest stitches,
        # which tells you how many stitches to remove in the armholes. Then
        # finish by shaping the armholes using a helper function.
        # =======================================================================

        # Even until the underarm decreases
        self.hem_to_underarms = self.schematic.armpit_height
        self.hem_to_shoulders = self.schematic.shoulder_height
        gauge = self.gauge

        # Note: this next step only applies when
        # the neckline does not begin until after armhole
        # shaping is done. This is currently true for back pieces,
        # but will need to be revisited if we allow deep back-necks.

        # First, take care of the simple case:
        self.hem_to_armhole_shaping_start = self.schematic.armpit_height
        if self.is_drop_shoulder:

            # armhole_x gets a half-inch of stitches, everything else gets 0
            self.armhole_x = round(gauge.stitches * HALF_INCH, ROUND_UP)
            self.armhole_y = 0
            self.armhole_z = 0
            self.cross_chest_stitches = self._bust_stitches_internal_use - (
                2 * self.armhole_x
            )

        else:

            assert self.is_set_in_sleeve
            # cross chests
            self.cross_chest_stitches = _find_best_approximation(
                self.schematic.cross_back_width,
                gauge.stitches,
                rounding_directions["cross_chest"],
                ease_tolerances["cross_chest"],
                self.parity,
                2,
            )

            # figure out armhole shaping via a helper function

            armhole_n = (
                self._bust_stitches_internal_use - self.cross_chest_stitches
            ) / 2
            (self.armhole_x, self.armhole_y, self.armhole_z) = (
                self._calculate_armhole_shaping(armhole_n, self.actual_armhole_depth)
            )

        self.actual_armhole_circumference = self._compute_armhole_circumference()

    def _compute_neckline_and_shoulders(self, rounding_directions, ease_tolerances):
        """
        Compute fields for neckline and shoulders.
        """

        gauge = self.gauge

        # necklines! Note that this is the back, and so uses
        # a standard, fixed neckline shape.

        # We start by finding the stitch-count of the neckline using an approximation of its width
        # We need to be a little careful here when selecting the parity of the following
        # approximation. If there are no extra 'cable' stitches, then we need to use the
        # parity of the cross-chest stitches. But if there are extra cable stitches, then we need
        # to use a parity such that (the approximation + the extra stitches) has the same
        # parity as the cross-chest stitches. In other words, the parity of the approximation must be
        # the parity of (cross-chest stitches - cable stitches)

        cable_extra_stitches = self._get_cable_extra_stitches()
        if cable_extra_stitches is None:
            cable_extra_stitches = 0

        approx_parity = (self.cross_chest_stitches - cable_extra_stitches) % 2
        neckline_stitches_goal = _find_best_approximation(
            self.schematic.neck_opening_width,
            gauge.stitches,
            rounding_directions["neck_width"],
            ease_tolerances["neck_width"],
            approx_parity,
            2,
        )

        # Be sure to include the cable stitches
        neckline_stitches_goal += cable_extra_stitches
        assert (neckline_stitches_goal % 2) == (self.cross_chest_stitches % 2)

        # Shoulders
        self.num_shoulder_stitches = (
            self.cross_chest_stitches - neckline_stitches_goal
        ) / 2
        self.first_shoulder_bindoff = round(self.num_shoulder_stitches / 2)

        self.hem_to_shoulders = self.schematic.shoulder_height
        neckline_depth_goal = self.hem_to_shoulders - self.schematic.neck_height
        # Note: BeckNeckline.make() has a different signature than fronts.
        self.neckline = BackNeckline.make(
            neckline_stitches_goal,
            neckline_depth_goal,
            self.gauge,
            rounding_directions,
            ease_tolerances,
            self.num_shoulder_stitches,
        )

        effective_stitches_across_neckline = (
            self.neckline.stitches_across_neckline() - cable_extra_stitches
        )

        self.actual_neck_opening = effective_stitches_across_neckline / gauge.stitches

    def _compute_armhole_circumference(self):
        """
        Returns Inches of armhole circumferences (front and back) in inches.
        Helper function.
        """
        return compute_armhole_circumference(
            self.gauge,
            self.armhole_x,
            self.armhole_y,
            self.armhole_z,
            self.actual_armhole_depth,
        )

    def _calculate_armhole_shaping(self, armhole_n, armhole_depth):
        # Try to catch/prevent infintite-loop problem that briefly appeared
        # during testing/review but then proved unreproducable
        assert armhole_depth > 0

        gauge = self.gauge

        # Armhole shaping is only allowed to be so high
        max_armhole_shaping_height = (
            armhole_depth * MAX_ARMHOLE_SHAPING_HEIGHT_PERCENTAGE
        )

        # start looking for satisfactory armhole shaping

        # initial parameters
        armholeSolutionFound = False
        x = round(ONEINCH * gauge.stitches, ROUND_DOWN, 2)

        # Do we have enough stitches to shape? We need x + 1 (the extra is so that z is not zero)
        if armhole_n < x + 1:
            raise ArmholeShapingError("Not enough stitches in armhole")

        # Helper function to test if we found a solution
        def is_solution(x, y, z):
            # figure out height of this armhole shaping
            # 2 rows for X bindoff
            # 2 rows for the Y bindoff , if present
            # 2 rows for each BO in Z
            # divided by rows per inch
            armhole_shaping_rows = sum([2 if x > 0 else 0, 2 if y > 0 else 0, 2 * z])
            armhole_shaping_height = float(armhole_shaping_rows) / float(gauge.rows)
            return armhole_shaping_height < max_armhole_shaping_height

        # Now iterate through possible solutions
        while not armholeSolutionFound:

            y_plus_z = armhole_n - x

            # Deal with degenerate cases
            if y_plus_z == 0:
                raise ArmholeShapingError(
                    "Not enough height in armhole to compute shaping."
                )

            elif y_plus_z <= 3:
                if y_plus_z == 1:
                    y = 0
                    z = 1
                elif y_plus_z == 2:
                    y = 0
                    z = 2
                else:  # y_plus_z == 3
                    y = 2
                    z = 1
                armholeSolutionFound = is_solution(x, y, z)

            else:
                # do the usual search
                y = 2
                z = armhole_n - x - y

                while (y < x) and (z >= 1) and (not armholeSolutionFound):

                    if is_solution(x, y, z):
                        armholeSolutionFound = True
                        break

                    # Soluton not found. Increment y
                    y += 1
                    z = armhole_n - x - y

                # end inner while

            # If solution found in inner while, break out of this one too
            if armholeSolutionFound:
                break

            # No solution found? increment x
            x += 1

        # end outer while

        # These should (?) be guaranteed by prior statements
        if (not armholeSolutionFound) or (x <= 0) or (y < 0) or (z <= 0):
            raise ArmholeShapingError("Cannot find valid shaping for armhole")

        return (x, y, z)

    # end calculateArmholeShaping

    #    def clean(self):
    #        """
    #        This will check for consistency of the fields. Other errors dynamically
    #        encountered during the making of this object will be raised via
    #        ValueError or ValidationError exceptions.
    #        """
    #        super(SweaterBack, self).clean(self)

    def _add_cable_stitches(self):
        super(BaseBackPiece, self)._add_cable_stitches()
        cable_stitches = self._get_cable_extra_stitches()
        self.cross_chest_stitches += cable_stitches if cable_stitches else 0

    def _get_cable_extra_stitches(self):
        return self.get_spec_source().back_cable_extra_stitches

    @property
    def actual_cross_chest(self):
        "Number of inches across chest (after armhole shaping)"
        # Note: we need to remove the extra 'cable' stitches, if present,
        # before converting to inches
        cable_stitches = self._get_cable_extra_stitches()
        effective_stitches = self.cross_chest_stitches - (
            cable_stitches if cable_stitches else 0
        )
        return effective_stitches / self.gauge.stitches

    @property
    def allover_stitch(self):
        return self.get_spec_source().back_allover_stitch

    def caston_repeats(self):
        """
        Return the caston repeat requirements for the waist caston.
        """
        return self.get_spec_source().back_repeats()


class BackPiece(BaseBackPiece, HalfBodyPieceMixin):
    pass


class GradedBackPiece(BaseBackPiece, GradedHalfBodyPieceMixin):
    class Meta:
        abstract = True


class BaseSweaterBackMixin(object):
    @property
    def is_sweater_back(self):
        return True


class SweaterBack(BaseSweaterBackMixin, BackPiece):

    _pattern_field_name = "sweater_back"

    schematic = models.OneToOneField(SweaterBackSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(swatch, back_piece_schematic, rounding_directions, ease_tolerances):
        p = SweaterBack()
        p.schematic = back_piece_schematic
        p.swatch = swatch
        p._inner_make(rounding_directions, ease_tolerances, graded=False)
        return p


class GradedSweaterBack(BaseSweaterBackMixin, GradedBackPiece):

    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(
        GradedSweaterBackSchematic, on_delete=models.CASCADE
    )

    @staticmethod
    def make(
        graded_pattern_pieces,
        graded_back_piece_schematic,
        rounding_directions,
        ease_tolerances,
    ):
        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ
        p = GradedSweaterBack()
        p.graded_pattern_pieces = graded_pattern_pieces
        p.schematic = graded_back_piece_schematic
        p._inner_make(rounding_directions, ease_tolerances, graded=True)
        return p


class BaseVestBackMixin(object):
    @property
    def is_vest_back(self):
        return True


class VestBack(BaseVestBackMixin, BackPiece):

    _pattern_field_name = "vest_back"

    schematic = models.OneToOneField(VestBackSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(swatch, back_piece_schematic, rounding_directions, ease_tolerances):
        p = VestBack()
        p.schematic = back_piece_schematic
        p.swatch = swatch
        p._inner_make(rounding_directions, ease_tolerances, graded=False)
        return p


class GradedVestBack(BaseVestBackMixin, GradedBackPiece):

    class Meta:
        ordering = ["sort_key"]

    schematic = models.OneToOneField(GradedVestBackSchematic, on_delete=models.CASCADE)

    @staticmethod
    def make(
        graded_pattern_pieces,
        back_piece_schematic,
        rounding_directions,
        ease_tolerances,
    ):
        # Don't save or set sort_key here. That will be done in GradedSweaterPatternPieces so
        # that the sort key can be the finsihed bust circ
        p = GradedVestBack()
        p.graded_pattern_pieces = graded_pattern_pieces
        p.schematic = back_piece_schematic
        p._inner_make(rounding_directions, ease_tolerances, graded=True)
        return p


# Graded back Piece constraings
#
# All necklines empty or none
# hem_to_first_armhole_in_rows <= hem_to_neckline_in_rows(pullover_pre_neckline_parity) always or never (PulloverRenderer.__init__)
# All hourglass, all straight, or all tapered
# All have waist decreases or none
# all have_bust_increases or none
