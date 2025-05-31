import abc
import logging

from django.db import models

from customfit.helpers.magic_constants import FLOATING_POINT_NOISE
from customfit.helpers.math_helpers import (
    ROUND_DOWN,
    ROUND_UP,
    _down_to_odd,
    height_and_gauge_to_row_count,
    round,
)
from customfit.pieces.models import GradedPatternPiece, PatternPiece
from customfit.swatches.models import Swatch

from ...helpers.magic_constants import MAX_INCHES_BETWEEN_BODY_SHAPING_ROWS
from ..garment_parameters import SweaterGradedGarmentParametersGrade

logger = logging.getLogger(__name__)


class _BaseShapingResult(metaclass=abc.ABCMeta):
    """
    Base class for all shaping-result objects, which (in turn) should only be used
    by subclasses of SweaterPiece.  In addition to its methods (which are described
    by their own docstrings) these objects provide the following attributes:

    * shaping_vertical_play: the amount of vertical space, in inches, between
      the vertical distance allowed for the shaping (provided during generation)
      and the amount of vertical space actually consumed.

    * constraints_met: Will be False if the shaping calculation could not
      achieve the shaping required by its inputs.

    * best_larger_stitches: if constraints_met is False, this value will be the
      largest 'larger_stitches' value that could be achieved by starting with
      'smaller_stitches' and increasing according to shaping described by this
      object.

    * best_smaller_stitches: if constraints_met is False, this value will be the
      smallest 'smaller_stitches' value that could be achieved by starting with
      'larger_stitches' and decreasing according to the shaping described by
      this object.

    """

    def __init__(self):
        super(_BaseShapingResult, self).__init__()
        self.shaping_vertical_play = None
        self.constraints_met = False
        self.best_smaller_stitches = None
        self.best_larger_stitches = None

    @abc.abstractmethod
    def compute_vertical_play(self, gauge, max_vertical_height):
        pass

    def clean(self):
        "Check any constraints."
        if self.constraints_met:
            assert self.best_larger_stitches is None
            assert self.best_smaller_stitches is None
        else:
            assert self.best_larger_stitches is not None
            assert self.best_larger_stitches >= 0
            assert self.best_smaller_stitches is not None
            assert self.best_smaller_stitches >= 0


class _BaseEdgeShapingResult(_BaseShapingResult, metaclass=abc.ABCMeta):
    """
    * num_standard_shaping_rows: The number of shaping rows. (Name is a historical artifact)

    * rows_between_standard_shaping_rows: Does not include the two standard-
      shaping rows which book-end the rows between them.

    """

    def __init__(self):
        super(_BaseEdgeShapingResult, self).__init__()

        self.num_standard_shaping_rows = None
        self.rows_between_standard_shaping_rows = None

    def compute_vertical_play(self, gauge, max_vertical_height):

        shaping_height = self.num_total_rows() / gauge.rows

        self.shaping_vertical_play = max_vertical_height - shaping_height

        # Catch a rounding error that plauged us
        if all(
            [
                self.shaping_vertical_play < 0,
                self.shaping_vertical_play > (0 - FLOATING_POINT_NOISE),
            ]
        ):
            self.shaping_vertical_play = 0

        # This should be guaranteed
        assert self.shaping_vertical_play >= 0, "%f" % self.shaping_vertical_play

    @abc.abstractmethod
    def num_total_rows(self):
        pass

    @abc.abstractmethod
    def num_total_shaping_rows(self):
        pass


class EdgeShapingResult(_BaseEdgeShapingResult):
    """
    Class for standard edge shaping (no double- or -triple darts, no compound shaping.)

    * max_distance_constraint_hit: True if the shaping result hit the max_rows_between_shaping_rows
      or max_distance_between_shaping_rows constraint. Not ver useful for compute_partial, but
      more useful for compute_full
    """

    def __init__(self):
        super(EdgeShapingResult, self).__init__()
        self.max_distance_constraint_hit = False

    def num_total_shaping_rows(self):
        return_me = self.num_standard_shaping_rows
        return return_me

    def num_total_rows(self):
        if self.num_standard_shaping_rows >= 2:
            total_rows_contained_in_shaping = sum(
                [
                    self.num_standard_shaping_rows,
                    self.rows_between_standard_shaping_rows
                    * (self.num_standard_shaping_rows - 1),
                ]
            )
        else:
            total_rows_contained_in_shaping = self.num_standard_shaping_rows

        return total_rows_contained_in_shaping

    def clean(self):
        super(EdgeShapingResult, self).clean()
        assert self.num_standard_shaping_rows is not None
        assert self.num_standard_shaping_rows >= 0
        if self.num_standard_shaping_rows in [0, 1]:
            assert self.rows_between_standard_shaping_rows is None
        else:
            assert self.rows_between_standard_shaping_rows is not None
            assert self.rows_between_standard_shaping_rows >= 0

    @classmethod
    def compute_shaping_partial(
        cls,
        larger_stitches,
        smaller_stitches,
        total_rows,
        even_spacing=False,
        max_rows_between_shaping_rows=None,
    ):
        """
        Computes the increase/decrease rate required for edge-shaping (sleeve
        and neckline), and returns it in the form of a ShapingResult. No markers
        can be used, but there is no need to leave rows between shaping rows.
        (Though see below about `even_spacing`.) Note that this code assumes
        that there are two opportunities to shape per row-- both edges of the
        sleeve, for example, or both sides of the neckline. If the shaping
        described by the inputs cannot be achieved, the resulting ShapingResult
        object will have constraints_met set to False, and best_larger_stitches
        & best_smaller_stitches will have the best possible stitch-values.

        If `even_spacing` is True, then it is guaranteed that all shaping
        rows will be of the same type: RS or WS. This is achieved by forcing
        `rows_between_standard_shaping_rows` of the returned ShapingResult to
        be odd.

        If `max_rows_between_shaping_rows` is not None, it will be used
        to limit the number of rows allowed to appear between consecutive
        shaping rows.

        Note: larger_stitches and smaller_stitches must have the same parity
        (odd or even).

        Does not add compound shaping. Does not compute vertical play.

        Exists for knitting calculators (which do not have access to gauge).
        """

        assert (larger_stitches % 2) == (smaller_stitches % 2), (
            larger_stitches,
            smaller_stitches,
        )
        assert total_rows >= 0
        assert larger_stitches >= smaller_stitches

        shaping_result = cls()

        num_shapings_needed = (larger_stitches - smaller_stitches) / 2
        # Catch corner case: max_rows_during_shaping less than 1
        if total_rows < 1:
            shaping_result.constraints_met = larger_stitches == smaller_stitches
            shaping_result.best_larger_stitches = smaller_stitches
            shaping_result.best_smaller_stitches = larger_stitches
            shaping_result.constraints_met = False
            shaping_result.num_standard_shaping_rows = 0
            return shaping_result

        # If < 1, go straight
        # If 1, single shaping row
        # Else, compute multiple shaping rows

        if num_shapings_needed < 1:
            # Go straight.
            shaping_result.num_standard_shaping_rows = 0
            shaping_result.constraints_met = True
        elif num_shapings_needed == 1:
            shaping_result.num_standard_shaping_rows = 1
            shaping_result.constraints_met = True
        else:
            # multiple decreases.

            #
            # Compute rows between standard shaping rows
            #
            shaping_result.rows_between_standard_shaping_rows = (
                (total_rows - 1) / float(num_shapings_needed - 1)
            ) - 1

            shaping_result.rows_between_standard_shaping_rows = round(
                shaping_result.rows_between_standard_shaping_rows, ROUND_DOWN
            )

            if max_rows_between_shaping_rows:
                if (
                    shaping_result.rows_between_standard_shaping_rows
                    > max_rows_between_shaping_rows
                ):
                    shaping_result.max_distance_constraint_hit = True
                    shaping_result.rows_between_standard_shaping_rows = (
                        max_rows_between_shaping_rows
                    )

            if even_spacing:
                shaping_result.rows_between_standard_shaping_rows = _down_to_odd(
                    shaping_result.rows_between_standard_shaping_rows
                )

            # Okay, now compute the rest
            if shaping_result.rows_between_standard_shaping_rows < 0:
                shaping_result.constraints_met = False

                if even_spacing:

                    shaping_result.rows_between_standard_shaping_rows = 1

                    shaping_result.num_standard_shaping_rows = (
                        round((total_rows - 1) / 2, ROUND_DOWN) + 1
                    )

                else:
                    shaping_result.rows_between_standard_shaping_rows = 0

                    shaping_result.num_standard_shaping_rows = round(
                        total_rows, ROUND_DOWN
                    )

                stitches_delta = 2 * shaping_result.num_standard_shaping_rows

                shaping_result.best_larger_stitches = smaller_stitches + stitches_delta
                shaping_result.best_smaller_stitches = larger_stitches - stitches_delta

            else:
                shaping_result.constraints_met = True
                shaping_result.num_standard_shaping_rows = num_shapings_needed

        shaping_result.clean()
        return shaping_result

    @classmethod
    def compute_shaping_full(
        cls,
        larger_stitches,
        smaller_stitches,
        max_vertical_height,
        gauge,
        even_spacing=False,
        max_distance_between_shaping_rows=None,
    ):
        """
        Computes the increase/decrease rate required for edge-shaping (sleeve
        and neckline), and returns it in the form of a ShapingResult. No markers
        can be used, but there is no need to leave rows between shaping rows.
        (Though see below about `even_spacing`.) Note that this code assumes
        that there are two opportunities to shape per row-- both edges of the
        sleeve, for example, or both sides of the neckline. If the shaping
        described by the inputs cannot be achieved, the resulting ShapingResult
        object will have constraints_met set to False, and best_larger_stitches
        & best_smaller_stitches will have the best possible stitch-values.

        If `even_spacing` is True, then it is guaranteed that all shaping
        rows will be of the same type: RS or WS. This is achieved by forcing
        `rows_between_standard_shaping_rows` of the returned ShapingResult to
        be odd.

        If `max_distance_between_shaping_rows` is not None, it will be used
        to limit how far apart shaping rows are allowed to be.

        Note: larger_stitches and smaller_stitches must have the same parity
        (odd or even).

        Adds vertical play.

        Used by pieces.
        """

        total_rows = max_vertical_height * gauge.rows
        if max_distance_between_shaping_rows:
            max_rows_between_shaping_rows = round(
                gauge.rows * max_distance_between_shaping_rows, ROUND_DOWN
            )
        else:
            max_rows_between_shaping_rows = None

        shaping_result = cls.compute_shaping_partial(
            larger_stitches,
            smaller_stitches,
            total_rows,
            even_spacing,
            max_rows_between_shaping_rows,
        )
        if shaping_result.constraints_met:
            shaping_result.compute_vertical_play(gauge, max_vertical_height)

        return shaping_result


class EdgeCompoundShapingResult(_BaseEdgeShapingResult):
    """
    Class for compound-shaping. Adds:

    * num_alternate_shaping_rows
    * rows_after_alternate_shaping_rows.

    The sequence is
    * standard shaping row
    * rows_between_num_standard_shaping_rows straight
    * standard shaping row
    * rows_between_num_standard_shaping_rows straight
    * standard shaping row
    * rows_between_num_standard_shaping_rows straight
    ...
    * standard shaping row (for the num_standard_shaping_rows-th time)
    * rows_between_num_standard_shaping_rows straight
    * alternate shaping row
    * rows_between_num_standard_shaping_rows straight
    * alternate shaping row
    * rows_between_num_standard_shaping_rows straight
    * alternate shaping row
    * rows_between_num_standard_shaping_rows straight
    ...
    * alternate shaping row (for the num_alternate_shaping_rows-th time)

    Note:
    * num_standard_shaping_rows - num_alternate_shaping_rows will be either 0 or 1,
    * rows_between_num_standard_shaping_rows and rows_after_alternate_shaping_rows will be exactly 1 apart.
    """

    def __init__(self):
        super(EdgeCompoundShapingResult, self).__init__()

        self.num_alternate_shaping_rows = None
        self.rows_after_alternate_shaping_rows = None

    def num_total_shaping_rows(self):
        return_me = self.num_standard_shaping_rows + self.num_alternate_shaping_rows
        return return_me

    def num_total_rows(self):
        return self._num_total_rows(
            self.num_standard_shaping_rows,
            self.rows_between_standard_shaping_rows,
            self.num_alternate_shaping_rows,
            self.rows_after_alternate_shaping_rows,
        )

    @staticmethod
    def _num_total_rows(
        num_standard_shaping_rows,
        rows_between_standard_shaping_rows,
        num_alternate_shaping_rows,
        rows_after_alternate_shaping_rows,
    ):
        if num_standard_shaping_rows in [0, 1]:
            return num_standard_shaping_rows
        else:
            if num_alternate_shaping_rows == 0:
                return sum(
                    [
                        num_standard_shaping_rows,
                        rows_between_standard_shaping_rows
                        * (num_standard_shaping_rows - 1),
                    ]
                )
            else:
                return sum(
                    [
                        num_standard_shaping_rows,
                        rows_between_standard_shaping_rows * num_standard_shaping_rows,
                        num_alternate_shaping_rows,
                        rows_after_alternate_shaping_rows
                        * (num_alternate_shaping_rows - 1),
                    ]
                )

    @classmethod
    def compute_shaping(
        cls, larger_stitches, smaller_stitches, max_vertical_height, gauge
    ):

        total_rows = round(max_vertical_height * gauge.rows, ROUND_DOWN)

        assert (larger_stitches % 2) == (smaller_stitches % 2), (
            larger_stitches,
            smaller_stitches,
        )
        assert total_rows >= 0
        assert larger_stitches >= smaller_stitches

        shaping_result = cls()

        num_shapings_needed = (larger_stitches - smaller_stitches) / 2
        # Catch corner case: max_rows_during_shaping less than 1
        if total_rows < 1:
            shaping_result.constraints_met = larger_stitches == smaller_stitches
            shaping_result.best_larger_stitches = smaller_stitches
            shaping_result.best_smaller_stitches = larger_stitches
            shaping_result.constraints_met = False
            shaping_result.num_standard_shaping_rows = 0
            shaping_result.num_alternate_shaping_rows = 0
            return shaping_result

        # If < 1, go straight
        # If 1, single shaping row
        # Else, compute multiple shaping rows

        if num_shapings_needed < 1:
            # Go straight.
            shaping_result.num_standard_shaping_rows = 0
            shaping_result.num_alternate_shaping_rows = 0
            shaping_result.constraints_met = True
        elif num_shapings_needed == 1:
            shaping_result.num_standard_shaping_rows = 1
            shaping_result.num_alternate_shaping_rows = 0
            shaping_result.constraints_met = True
        else:
            # multiple decreases.

            # Compute the goal rows-per-shaping, then branch on whether it's
            # closer to an integer or halfway between integers

            float_rows_per_shaping = (float(total_rows) - 1) / float(
                num_shapings_needed - 1
            )
            rounded_rows_per_shaping = round(
                float_rows_per_shaping, ROUND_DOWN, multiple=0.5
            )

            if rounded_rows_per_shaping < 1:
                # Can't do the shaping-- not enough rows
                shaping_result.constraints_met = False
                shaping_result.num_standard_shaping_rows = total_rows
                shaping_result.rows_between_standard_shaping_rows = 0
                shaping_result.num_alternate_shaping_rows = 0
                shaping_result.rows_after_alternate_shaping_rows = None

                stitches_delta = 2 * shaping_result.num_standard_shaping_rows
                shaping_result.best_larger_stitches = smaller_stitches + stitches_delta
                shaping_result.best_smaller_stitches = larger_stitches - stitches_delta

            elif rounded_rows_per_shaping == int(rounded_rows_per_shaping):
                # compound shaping not needed-- use logic from standard shaping
                std_sr = EdgeShapingResult.compute_shaping_full(
                    larger_stitches, smaller_stitches, max_vertical_height, gauge
                )
                shaping_result.num_standard_shaping_rows = (
                    std_sr.num_standard_shaping_rows
                )
                shaping_result.rows_between_standard_shaping_rows = (
                    std_sr.rows_between_standard_shaping_rows
                )
                shaping_result.shaping_vertical_play = std_sr.shaping_vertical_play
                shaping_result.constraints_met = std_sr.constraints_met
                shaping_result.best_smaller_stitches = std_sr.best_smaller_stitches
                shaping_result.best_larger_stitches = std_sr.best_larger_stitches

                shaping_result.num_alternate_shaping_rows = 0
                shaping_result.rows_after_alternate_shaping_rows = None

            else:

                shaping_result.num_standard_shaping_rows = round(
                    num_shapings_needed / 2.0, ROUND_UP
                )
                shaping_result.num_alternate_shaping_rows = (
                    num_shapings_needed - shaping_result.num_standard_shaping_rows
                )

                inter_row_count1 = round(rounded_rows_per_shaping - 1, ROUND_UP)
                inter_row_count2 = round(rounded_rows_per_shaping - 1, ROUND_DOWN)

                total_row_count1 = shaping_result._num_total_rows(
                    shaping_result.num_standard_shaping_rows,
                    inter_row_count1,
                    shaping_result.num_alternate_shaping_rows,
                    inter_row_count2,
                )

                total_row_count2 = shaping_result._num_total_rows(
                    shaping_result.num_standard_shaping_rows,
                    inter_row_count2,
                    shaping_result.num_alternate_shaping_rows,
                    inter_row_count1,
                )

                if total_row_count1 <= total_rows:
                    if total_row_count2 <= total_rows:
                        if total_row_count1 > total_row_count2:
                            shaping_result.rows_between_standard_shaping_rows = (
                                inter_row_count1
                            )
                            shaping_result.rows_after_alternate_shaping_rows = (
                                inter_row_count2
                            )
                        else:
                            shaping_result.rows_between_standard_shaping_rows = (
                                inter_row_count2
                            )
                            shaping_result.rows_after_alternate_shaping_rows = (
                                inter_row_count1
                            )

                    else:
                        shaping_result.rows_between_standard_shaping_rows = (
                            inter_row_count1
                        )
                        shaping_result.rows_after_alternate_shaping_rows = (
                            inter_row_count2
                        )
                else:
                    assert total_row_count2 <= total_rows
                    shaping_result.rows_between_standard_shaping_rows = inter_row_count2
                    shaping_result.rows_after_alternate_shaping_rows = inter_row_count1

                shaping_result.constraints_met = True

        if shaping_result.constraints_met:
            shaping_result.compute_vertical_play(gauge, max_vertical_height)

        shaping_result.clean()

        return shaping_result

    def clean(self):

        super(EdgeCompoundShapingResult, self).clean()

        assert self.num_standard_shaping_rows is not None
        assert self.num_standard_shaping_rows >= 0
        assert self.num_alternate_shaping_rows is not None
        assert self.num_alternate_shaping_rows >= 0

        if self.num_standard_shaping_rows in [0, 1]:
            assert self.num_alternate_shaping_rows == 0
            assert self.rows_between_standard_shaping_rows is None
            assert self.rows_after_alternate_shaping_rows is None
        else:
            assert self.rows_between_standard_shaping_rows is not None
            assert self.rows_between_standard_shaping_rows >= 0
            if self.num_alternate_shaping_rows == 0:
                assert self.rows_after_alternate_shaping_rows is None
            else:
                assert self.num_alternate_shaping_rows is not None
                assert self.rows_after_alternate_shaping_rows is not None
                assert (
                    self.num_standard_shaping_rows - self.num_alternate_shaping_rows
                ) in [0, 1]
                assert (
                    self.rows_between_standard_shaping_rows
                    - self.rows_after_alternate_shaping_rows
                ) in [-1, 1]


class TorsoShapingResult(_BaseShapingResult):

    def __init__(self):
        super(TorsoShapingResult, self).__init__()

        self.num_standard_shaping_rows = None
        self.rows_between_standard_shaping_rows = None
        self.num_double_dart_shaping_rows = None
        self.num_triple_dart_shaping_rows = None

    def num_total_shaping_rows(self):

        return_me = self.num_standard_shaping_rows
        return_me += self.num_double_dart_shaping_rows
        return_me += self.num_triple_dart_shaping_rows
        return return_me

    def use_double_darts(self):
        return self.num_double_dart_shaping_rows > 0

    def use_triple_darts(self):
        return self.num_triple_dart_shaping_rows > 0

    def compute_vertical_play(self, gauge, max_vertical_height):

        if (self.num_standard_shaping_rows + self.num_triple_dart_shaping_rows) >= 2:

            total_rows_contained_in_shaping = (
                (self.rows_between_standard_shaping_rows + 1)
                * (
                    self.num_standard_shaping_rows
                    + self.num_triple_dart_shaping_rows
                    - 1
                )
            ) + 1
        else:
            total_rows_contained_in_shaping = (
                self.num_standard_shaping_rows + self.num_triple_dart_shaping_rows
            )

        shaping_height = total_rows_contained_in_shaping / gauge.rows

        self.shaping_vertical_play = max_vertical_height - shaping_height

        # Catch a rounding error that plauged us
        if all(
            [
                self.shaping_vertical_play < 0,
                self.shaping_vertical_play > (0 - FLOATING_POINT_NOISE),
            ]
        ):
            self.shaping_vertical_play = 0

        # This should be guaranteed
        assert self.shaping_vertical_play >= 0, "%f" % self.shaping_vertical_play

    # def clean(self):
    #     super(TorsoShapingResult, self).clean()
    #     if self.constraints_met:
    #         assert self.num_standard_shaping_rows is not None
    #         assert self.rows_between_standard_shaping_rows is not None
    #         assert self.num_double_dart_shaping_rows is not None
    #         assert self.num_triple_dart_shaping_rows is not None
    #         assert self.num_standard_shaping_rows >= 0
    #         assert self.rows_between_standard_shaping_rows >= 0
    #         assert self.num_double_dart_shaping_rows >= 0
    #         assert self.num_triple_dart_shaping_rows >= 0
    #
    #     else:
    #         assert self.num_standard_shaping_rows is None
    #         assert self.rows_between_standard_shaping_rows is None
    #         assert self.num_double_dart_shaping_rows is None
    #         assert self.num_triple_dart_shaping_rows is None

    @classmethod
    def compute_shaping(
        cls,
        larger_stitches,
        smaller_stitches,
        max_vertical_height,
        gauge,
        max_distance_between_shaping_rows=MAX_INCHES_BETWEEN_BODY_SHAPING_ROWS,
        allow_double_darts=True,
        allow_triple_darts=True,
    ):
        """
        Computes the increase/decrease rate required for marker-shaping (waist
        and bust), and returns it in the form of a ShapingResult. There must
        be 3 rows between decreases at a given marker, but double-dart and
        triple-dart markers can be used.
        """

        assert (larger_stitches % 2) == (smaller_stitches % 2)
        assert max_vertical_height >= 0
        assert larger_stitches >= smaller_stitches
        assert (
            allow_double_darts if allow_triple_darts else True
        )  # if triple-darts are allowed, then double-darts must be too

        shaping_result = cls()
        num_shapings_needed = (larger_stitches - smaller_stitches) / 2

        # first, let's catch a corner-case: max_vertical_height is less than
        # one row. in that case, return a no-op ShapingResult
        max_rows_during_shaping = max_vertical_height * gauge.rows

        if max_rows_during_shaping < 1:
            shaping_result.constraints_met = larger_stitches == smaller_stitches
            shaping_result.best_larger_stitches = smaller_stitches
            shaping_result.best_smaller_stitches = larger_stitches
            shaping_result.constraints_met = False
            shaping_result.num_standard_shaping_rows = 0
            shaping_result.num_double_dart_shaping_rows = 0
            shaping_result.num_triple_dart_shaping_rows = 0
            return shaping_result

        # Great. For the rest of this method, then, we can assume that
        # max_vertical_distance is positive
        # If < 1, go straight
        # If 1, single shaping row
        # Else, compute multiple shaping rows

        if num_shapings_needed < 1:
            # Go straight.
            shaping_result.num_standard_shaping_rows = 0
            shaping_result.num_double_dart_shaping_rows = 0
            shaping_result.num_triple_dart_shaping_rows = 0
            shaping_result.constraints_met = True
        elif num_shapings_needed == 1:
            shaping_result.num_standard_shaping_rows = 1
            shaping_result.num_double_dart_shaping_rows = 0
            shaping_result.num_triple_dart_shaping_rows = 0
            shaping_result.constraints_met = True
        else:

            ###################################################################
            # Okay, now we compute for multiple decreases.
            # Find max decrease-rate that best fills
            # this height. If this rate is shallow enough (4 rows per decrease)
            # then good. Otherwise, we need to use double- or
            # even triple-darts.
            ###################################################################

            #
            # Compute rows between standard shaping rows
            #
            shaping_result.rows_between_standard_shaping_rows = (
                (max_rows_during_shaping - 1) / float(num_shapings_needed - 1)
            ) - 1

            if max_distance_between_shaping_rows:
                max_rows_between_shaping_rows = (
                    gauge.rows * max_distance_between_shaping_rows
                )
                if (
                    shaping_result.rows_between_standard_shaping_rows
                    > max_rows_between_shaping_rows
                ):
                    shaping_result.rows_between_standard_shaping_rows = (
                        max_rows_between_shaping_rows
                    )

            shaping_result.rows_between_standard_shaping_rows = round(
                shaping_result.rows_between_standard_shaping_rows, ROUND_DOWN
            )

            shaping_result.rows_between_standard_shaping_rows = _down_to_odd(
                shaping_result.rows_between_standard_shaping_rows
            )

            # Okay, now compute the rest

            # TODO: factor out these magic constants
            if shaping_result.rows_between_standard_shaping_rows >= 3:
                ##################################################
                # This is the expected case. The decrease-rate is
                # shallow enough that we do not need to use double-
                # or triple-darts.
                #
                # Spread the standard shaping rows as much as possible
                # ######################################################

                shaping_result.num_standard_shaping_rows = num_shapings_needed

                shaping_result.num_double_dart_shaping_rows = 0
                shaping_result.num_triple_dart_shaping_rows = 0
                shaping_result.constraints_met = True

            else:
                ###############################################
                # It looks like we need double or even triple
                # darts. Can we use them?
                ###############################################
                shaping_result.rows_between_standard_shaping_rows = 3
                assert max_rows_during_shaping >= 1
                shaping_result.num_standard_shaping_rows = (
                    round((max_rows_during_shaping - 1) / 4, ROUND_DOWN) + 1
                )

                if not allow_double_darts:
                    # Nope. No double darts, and hence no triple darts

                    shaping_result.constraints_met = False
                    shaping_result.num_triple_dart_shaping_rows = 0
                    shaping_result.num_double_dart_shaping_rows = 0
                    stitches_delta = shaping_result.num_standard_shaping_rows * 2
                    shaping_result.best_larger_stitches = (
                        smaller_stitches + stitches_delta
                    )
                    shaping_result.best_smaller_stitches = (
                        larger_stitches - stitches_delta
                    )

                else:
                    ###############################################
                    #
                    # Double darts: First, we will figure out how many
                    # double-dart shaping rows there
                    # can possibly be. The 'standard' shaping rows will have
                    # three other rows between them, and the double-dart
                    # shaping rows will be staggered halfway between them.
                    # Plus, we might be able to put an extra one at the top.
                    # If we don't need all the possible double-dart rows, great.
                    #
                    # If we need even more decrease rows, though, we need
                    # triple darts. First, see if we need all of them.
                    # Triple-dart shapings happen in the same rows as the
                    # standard shapings, so we get exactly the same amount.
                    # If we don't need them all, great.
                    # If we need even more decreases... well,
                    # throw an error.
                    #
                    ################################################

                    # This should be true by prior statements in this else: clause.
                    rows_in_standard_decreases = (
                        4 * (shaping_result.num_standard_shaping_rows - 1)
                    ) + 1
                    assert rows_in_standard_decreases <= max_rows_during_shaping

                    # Now, compute how many double-dart decrease we might
                    # be able to use. There is at least one between each
                    # standard shaping row.

                    num_double_dart_shaping_rows_possible = max(
                        shaping_result.num_standard_shaping_rows - 1, 0
                    )

                    # Now, do we need that many? If not, set it to the number
                    # we actually need and be done. If we need more, move on
                    # to triple darts

                    double_dart_shapings_needed = (
                        num_shapings_needed - shaping_result.num_standard_shaping_rows
                    )

                    if (
                        double_dart_shapings_needed
                        <= num_double_dart_shaping_rows_possible
                    ):

                        # Yay! We're done
                        shaping_result.num_double_dart_shaping_rows = (
                            double_dart_shapings_needed
                        )

                        shaping_result.num_triple_dart_shaping_rows = 0
                        shaping_result.constraints_met = True

                    else:

                        if not allow_triple_darts:
                            # No triple darts allowed. return what we can

                            shaping_result.constraints_met = False

                            shaping_result.num_triple_dart_shaping_rows = 0
                            shaping_result.num_double_dart_shaping_rows = (
                                num_double_dart_shaping_rows_possible
                            )
                            stitches_delta = (
                                sum(
                                    [
                                        shaping_result.num_standard_shaping_rows,
                                        shaping_result.num_double_dart_shaping_rows,
                                    ]
                                )
                                * 2
                            )
                            shaping_result.best_larger_stitches = (
                                smaller_stitches + stitches_delta
                            )
                            shaping_result.best_smaller_stitches = (
                                larger_stitches - stitches_delta
                            )

                        else:

                            shaping_result.num_double_dart_shaping_rows = (
                                num_double_dart_shaping_rows_possible
                            )

                            ####################################################
                            # We need yet more decreases. WE've maxed out
                            # double-darts, so we go on to triple darts
                            #################################################

                            # Now, we can turn each standard decrease row into
                            # a triple-dart row.
                            # Now, do we need that many? If not, set it to the number
                            # we actually need and be done. If we need more...
                            # throw an error

                            triple_dart_shapings_needed = (
                                num_shapings_needed
                                - shaping_result.num_standard_shaping_rows
                                - shaping_result.num_double_dart_shaping_rows
                            )

                            triple_dart_rows_possible = (
                                shaping_result.num_standard_shaping_rows
                            )

                            if triple_dart_shapings_needed <= triple_dart_rows_possible:

                                shaping_result.num_triple_dart_shaping_rows = (
                                    triple_dart_shapings_needed
                                )
                                shaping_result.num_standard_shaping_rows -= (
                                    shaping_result.num_triple_dart_shaping_rows
                                )

                                shaping_result.constraints_met = True

                            else:

                                shaping_result.constraints_met = False

                                shaping_result.num_triple_dart_shaping_rows = (
                                    shaping_result.num_standard_shaping_rows
                                )

                                shaping_result.num_standard_shaping_rows -= (
                                    shaping_result.num_triple_dart_shaping_rows
                                )

                                stitches_delta = (
                                    sum(
                                        [
                                            shaping_result.num_standard_shaping_rows,
                                            shaping_result.num_double_dart_shaping_rows,
                                            2
                                            * shaping_result.num_triple_dart_shaping_rows,
                                        ]
                                    )
                                    * 2
                                )

                                shaping_result.best_larger_stitches = (
                                    smaller_stitches + stitches_delta
                                )

                                shaping_result.best_smaller_stitches = (
                                    larger_stitches - stitches_delta
                                )

                    # End double/triple dart case

        ###########################################################
        # Now, figure out how much vertical play there is (vertical
        # distance available for shaping not used during shaping
        ###########################################################

        shaping_result.compute_vertical_play(gauge, max_vertical_height)

        # This should be guaranteed by prior statements
        assert shaping_result.shaping_vertical_play >= 0, (
            "%f" % shaping_result.shaping_vertical_play
        )

        if shaping_result.constraints_met:
            shaping_result.clean()
        return shaping_result


class _BaseSweaterPiece(models.Model):
    class Meta:
        abstract = True

    @property
    def is_drop_shoulder(self):
        return self.schematic.is_drop_shoulder

    @property
    def is_set_in_sleeve(self):
        return self.schematic.is_set_in_sleeve

    def _height_to_row_count(self, height, parity):
        # Note: mostly moved to helpers.math_helpers to be
        # accessible to non-pieces, like buttonbands.
        return height_and_gauge_to_row_count(height, self.gauge.rows, parity)

    def _row_count_to_height(self, row_count):
        return row_count / self.gauge.rows

    @staticmethod
    def compute_edge_shaping(
        larger_stitches,
        smaller_stitches,
        max_vertical_height,
        gauge,
        even_spacing=False,
        max_distance_between_shaping_rows=None,
    ):
        """
        Computes the increase/decrease rate required for edge-shaping (sleeve
        and neckline), and returns it in the form of a ShapingResult. No markers
        can be used, but there is no need to leave rows between shaping rows.
        (Though see below about `even_spacing`.) Note that this code assumes
        that there are two opportunities to shape per row-- both edges of the
        sleeve, for example, or both sides of the neckline. If the shaping
        described by the inputs cannot be achieved, the resulting ShapingResult
        object will have constraints_met set to False, and best_larger_stitches
        & best_smaller_stitches will have the best possible stitch-values.

        If `even_spacing` is True, then it is guaranteed that all shaping
        rows will be of the same type: RS or WS. This is achieved by forcing
        `rows_between_standard_shaping_rows` of the returned ShapingResult to
        be odd.

        If `max_distance_between_shaping_rows` is not None, it will be used
        to limit how far apart shaping rows are allowed to be.

        Note: larger_stitches and smaller_stitches must have the same parity
        (odd or even).

        """
        return EdgeShapingResult.compute_shaping_full(
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            gauge,
            even_spacing,
            max_distance_between_shaping_rows,
        )

    @staticmethod
    def compute_marker_shaping(
        larger_stitches,
        smaller_stitches,
        max_vertical_height,
        gauge,
        max_distance_between_shaping_rows=MAX_INCHES_BETWEEN_BODY_SHAPING_ROWS,
        allow_double_darts=True,
        allow_triple_darts=True,
    ):
        """
        Computes the increase/decrease rate required for marker-shaping (waist
        and bust), and returns it in the form of a ShapingResult. There must
        be 3 rows between decreases at a given marker, but double-dart and
        triple-dart markers can be used.
        """

        return TorsoShapingResult.compute_shaping(
            larger_stitches,
            smaller_stitches,
            max_vertical_height,
            gauge,
            max_distance_between_shaping_rows,
            allow_double_darts,
            allow_triple_darts,
        )

    @staticmethod
    def compute_compound_edge_shaping(
        larger_stitches, smaller_stitches, max_vertical_height, gauge
    ):
        return EdgeCompoundShapingResult.compute_shaping(
            larger_stitches, smaller_stitches, max_vertical_height, gauge
        )


class SweaterPiece(_BaseSweaterPiece, PatternPiece):

    swatch = models.ForeignKey(
        Swatch,
        help_text="Swatch from which this piece is computed",
        on_delete=models.CASCADE,
    )

    def get_pattern(self):
        # TODO: handle the cases where there is no sweaterpatternpieces or indivdiualpattern
        return self.sweaterpatternpieces.individualpattern


class GradedSweaterPiece(_BaseSweaterPiece, GradedPatternPiece):
    # Must define:
    # * schematic: ForeignKey to piece schematic

    # setting inheritence to keep the 'ordering' attribute from GradedPieces.Meta
    class Meta(GradedPatternPiece.Meta):
        abstract = True

    def get_pattern(self):
        return self.graded_pattern_pieces.gradedpattern
