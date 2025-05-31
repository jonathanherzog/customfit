import abc
import copy
import itertools
import logging
import os.path

import django.template
import django.utils

from customfit.helpers import row_parities as RP
from customfit.helpers.math_helpers import CompoundResult
from customfit.patterns.renderers import (
    Element,
    InstructionSection,
    PieceList,
    SubSection,
    make_template_path,
    render_template_path,
)

from .base import SWEATER_PIECE_TEMPLATES

logger = logging.getLogger(__name__)


# Places where a subsection can 'start'. See docstring on BodyPieceSubsection for details
# Note: the values of these constants are not important, but their *sort order* is.
_STARTS_BELOW_NECKLINE = 0
_STARTS_ON_SIDE1 = 1
_STARTS_ON_SIDE2 = 2
_END = 3
_possible_groups = [_STARTS_BELOW_NECKLINE, _STARTS_ON_SIDE1, _STARTS_ON_SIDE2, _END]


class BodyPieceSubsection(SubSection):
    # These subsections are a little complicated. They should be ordered in the following groups:
    #
    # * Things that start below the neckline,
    # * Armholes, if they start with the neckline,
    # * Neckline start,
    # * Things that start after the neckline on the RS,
    # * Things that start after the neckline on the WS
    # * Things that come at the end (like actuals)
    #
    # If things start at the same time as the neckline, the order should be: armholes, then neckline,
    # then anything else in any order. (We use _is_armholes and _is_neckline for this test.)
    #
    # And within a group, they should be ordered by start-row. When computing overlaps, however:
    #
    # * Things that start below the neckline can overlap with other things below the neckline and
    #   things that start above the neckline on both sides.
    # * Things that start above the neckline can only overlap with other things that start above
    #   the neckline on the same side.
    # * The only thing that can overlap with end-sections are other end-sections.

    def __init__(
        self,
        display_name,
        group,
        start_rows,
        end_rows,
        interrupts_others=True,
        warn_if_interrupted=True,
        is_neckline=False,
        is_armhole=False,
    ):
        super(BodyPieceSubsection, self).__init__()
        self.group = group
        self._display_name = display_name
        self._start_rows = start_rows
        self._end_rows = end_rows
        self._is_neckline = is_neckline
        self._is_armhole = is_armhole
        self._warn_if_interrupted = warn_if_interrupted
        self._interrupts_others = interrupts_others

    @property
    def display_name(self):
        return self._display_name

    @property
    def warn_if_interrupted(self):
        return self._warn_if_interrupted

    @property
    def interrupts_others(self):
        return self._interrupts_others

    @property
    def mallest_start_row(self):
        return min(self._start_rows)

    def _cmp(self, other):
        assert isinstance(other, BodyPieceSubsection)
        assert self.group in _possible_groups
        assert other.group in _possible_groups
        assert isinstance(self.start_rows, CompoundResult)
        assert isinstance(other.start_rows, CompoundResult)
        self_tuple = (self.group, self.smallest_start_row)
        other_tuple = (other.group, other.smallest_start_row)

        # See docstring for explaination
        if self_tuple < other_tuple:
            return -1
        elif self_tuple > other_tuple:
            return 1
        else:
            assert self_tuple == other_tuple
            # armhole comes first
            if self._is_armhole:
                return -1
            elif other._is_armhole:
                return 1
            # Now that we know neither is armhole, neckline comes before anything else:
            elif self._is_neckline:
                return -1
            elif other._is_neckline:
                return 1
            # Anything else can come in any order
            else:
                return 0

    def __eq__(self, other):
        return self._cmp(other) == 0

    def __lt__(self, other):
        return self._cmp(other) < 0

    def _gradewise_intersections(self, other):
        assert isinstance(other, BodyPieceSubsection)
        assert self.group in _possible_groups
        assert other.group in _possible_groups
        assert isinstance(self.start_rows, CompoundResult)
        assert isinstance(other.end_rows, CompoundResult)

        gradewise_intersections = [
            (o_s_r <= s_s_r) and (s_s_r <= o_e_r)
            for (s_s_r, o_s_r, o_e_r) in zip(
                self._start_rows, other._start_rows, other._end_rows
            )
        ]

        return gradewise_intersections

    def starts_during(self, other):
        """
        Return true iff self begins before other ends in any grades.
        """
        gradewise_intersections = self._gradewise_intersections(other)

        if (self.group == other.group) or (
            (other.group == _STARTS_BELOW_NECKLINE) and (self.group != _END)
        ):
            return any(gradewise_intersections)
        else:
            return False

    def starts_during_all_grades(self, other):
        """
        Return true iff self begins before other ends in any grades.
        """
        gradewise_intersections = self._gradewise_intersections(other)

        if (self.group == other.group) or (
            (other.group == _STARTS_BELOW_NECKLINE) and (self.group != _END)
        ):
            return all(gradewise_intersections)
        else:
            return False

    @property
    def start_rows(self):
        return self._start_rows

    @property
    def end_rows(self):
        return self._end_rows


class SecondNecklineSubSection(BodyPieceSubsection):

    def __init__(self, display_name, group, start_row, end_row):
        super(SecondNecklineSubSection, self).__init__(
            display_name, group, start_row, end_row, is_neckline=True, is_armhole=False
        )

    def starts_during(self, other):
        return False


BODY_PIECE_TEMPLATES = os.path.join(SWEATER_PIECE_TEMPLATES, "body_piece_templates")
ACTUALS = os.path.join(BODY_PIECE_TEMPLATES, "actuals")
ARMHOLE_AND_SHOULDERS = os.path.join(BODY_PIECE_TEMPLATES, "armhole_and_shoulders")
BODY_PIECE_CASTONS = os.path.join(BODY_PIECE_TEMPLATES, "cast_ons")
WAIST_AND_BUST = os.path.join(BODY_PIECE_TEMPLATES, "waist_and_bust")
WAISTS = os.path.join(WAIST_AND_BUST, "waists")
BUSTS = os.path.join(WAIST_AND_BUST, "busts")

NECKLINE_TEMPLATES = os.path.join(SWEATER_PIECE_TEMPLATES, "neckline_templates")


#########################################################################
#
# More complex abstract subclasses of PieceRenderers: body pieces
#
########################################################################


class CommonLogicMixin(InstructionSection, metaclass=abc.ABCMeta):
    """
    A mixin (abstract) class that contains logic common to both
    PulloverRenderer and CardiganRenderer.
    """

    @property
    @abc.abstractmethod
    def side_one_name(self):
        return None

    @property
    @abc.abstractmethod
    def side_two_name(self):
        return None

    @property
    @abc.abstractmethod
    def side_one_is_right_side(self):
        return None

    @property
    @abc.abstractmethod
    def marker_transition_template(self):
        """
        Basename only.
        """
        return None

    @property
    @abc.abstractmethod
    def actuals_template(self):
        """
        Basename only.
        """
        return None

    @abc.abstractmethod
    def _make_neckline_and_shoulder_elements(self, addl_context):
        return None

    def __init__(self, piece):
        super(CommonLogicMixin, self).__init__(piece)

        # Side 1 is the doesil (clockwise) side.
        side_one_inner_side = RP.RS
        side_one_outer_side = RP.reverse_parity(side_one_inner_side)
        side_one_pre_neckline_parity = side_one_outer_side
        side_one_pre_armhole_parity = side_one_inner_side
        side_one_pre_shoulder_parity = side_one_inner_side
        # common to both cardigans and pullovers
        self.side_one_dict = {
            "side_name": self.side_one_name,
            "is_right_side": self.side_one_is_right_side,
            "is_left_side": not self.side_one_is_right_side,
            "is_pullover": False,
            "outer_side": RP.to_string(side_one_outer_side),
            "inner_side": RP.to_string(side_one_inner_side),
            "decrease_text_triple_dart_standard_decrease": "K to first marker, sm, k2tog, k to end.",
            "decrease_text_triple_dart_double_decrease": "K to second marker, sm, k2tog, k to end.",
            "decrease_text_triple_dart_triple_decrease": "K to first marker, sm, k2tog, k to third marker, sm, k2tog, k to end",
            "decrease_text_double_dart_standard_decrease": "K to first marker, sm, k2tog, k to end.",
            "decrease_text_double_dart_double_dart_decrease": "K to second marker, sm, k2tog, k to end.",
            "decrease_text_single_dart": "K to marker, sm, k2tog, k to end.",
            "stitches_per_single_dart": "one stitch",
            "stitches_per_double_dart": "one stitch",
            "stitches_per_triple_dart": "two stitches",
            "increase_text_triple_dart_standard_dart": "K to first marker, sm, m1L, k to end.",
            "increase_text_triple_dart_double_dart": "K to second marker, sm, m1L, k to end.",
            "increase_text_triple_dart_triple_dart": "K to first marker, sm, m1L, k to third marker, sm, m1L, k to end.",
            "increase_text_double_dart_standard_dart": "K to first marker, sm, m1L, k to end.",
            "increase_text_double_dart_double_dart": "K to second marker, sm, m1L, k to end.",
            "increase_row_standard_dart": "Knit to marker, sm, m1L, k to end.",
            "reattach_side": "WS",
            "decrease_text_neckline_rs": "Knit 1, ssk, work to end.",
            "decrease_text_neckline_ws": "Work to last 3 sts, p2tog-tbl, p 1.",
            "stitches_per_neckline_decrease": "one stitch",
            "decrease_text_armhole_rs_onest": "Work to last 3 sts, k2tog, k 1.",
            "decrease_text_armhole_ws_onest": "Purl 1, p2tog, work to end.",
            "stitches_per_armhole_dec_one": "one stitch",
            "decrease_text_armhole_rs_twosts": "Knit 1, ssk, work to last 3 sts, k2tog, k 1.",
            "decrease_text_armhole_ws_twosts": "Purl 1, p2tog, work to last 3 sts, p2tog-tbl, p 1.",
            "stitches_per_armhole_dec_twosts": "two stitches",
            "pre_armhole_row_parity": RP.to_string(side_one_pre_armhole_parity),
            "pre_neckline_row_parity": RP.to_string(side_one_pre_neckline_parity),
            "neckline_row_parity": RP.to_string(
                RP.reverse_parity(side_one_pre_neckline_parity)
            ),
            "hem_to_armhole_in_rows": self.piece_list.hem_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
            "hem_to_shoulders_in_rows": self.piece_list.hem_to_shoulders_in_rows(
                side_one_pre_armhole_parity
            ),
            "last_increase_to_armhole_in_rows": self.piece_list.last_increase_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
            "last_decrease_to_armhole_in_rows": self.piece_list.last_decrease_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
            "armhole_to_shoulders_in_rows": self.piece_list.armhole_to_shoulders_in_rows(
                side_one_pre_armhole_parity, side_one_pre_shoulder_parity
            ),
            "last_armhole_to_shoulders_in_rows": self.piece_list.last_armhole_to_shoulders_in_rows(
                side_one_pre_armhole_parity, side_one_pre_shoulder_parity
            ),
            "hem_to_first_armhole_in_rows": self.piece_list.hem_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
            "last_increase_to_first_armhole_in_rows": self.piece_list.last_increase_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
            "last_decrease_to_first_armhole_in_rows": self.piece_list.last_decrease_to_armhole_in_rows(
                side_one_pre_armhole_parity
            ),
        }

        if not self.exemplar.neckline.empty():
            neckline_dict = {
                "neckline_to_armhole_in_rows": self.piece_list.neckline_to_armhole_in_rows(
                    side_one_pre_neckline_parity, side_one_pre_armhole_parity
                ),
                "armhole_to_neckline_in_rows": self.piece_list.armhole_to_neckline_in_rows(
                    side_one_pre_armhole_parity, side_one_pre_neckline_parity
                ),
                "last_armhole_to_neckline_in_rows": self.piece_list.last_armhole_to_neckline_in_rows(
                    side_one_pre_armhole_parity, side_one_pre_neckline_parity
                ),
                "hem_to_neckline_in_rows": self.piece_list.hem_to_neckline_in_rows(
                    side_one_pre_neckline_parity
                ),
                "last_increase_to_neckline_in_rows": self.piece_list.last_increase_to_neckline_in_rows(
                    side_one_pre_neckline_parity
                ),
                "last_decrease_to_neckline_in_rows": self.piece_list.last_decrease_to_neckline_in_rows(
                    side_one_pre_neckline_parity
                ),
                "neckline": self.piece_list.neckline,
            }

            self.side_one_dict.update(neckline_dict)

        # Side 2 is the widdershins (counterclockwise) side
        side_two_inner_side = RP.WS
        side_two_outer_side = RP.reverse_parity(side_two_inner_side)  # RS
        side_two_pre_neckline_parity = side_two_outer_side  # RS
        side_two_pre_armhole_parity = side_two_inner_side  # WS
        side_two_pre_shoulder_parity = side_two_inner_side  # WS
        self.side_two_dict = {
            "side_name": self.side_two_name,
            "is_right_side": not self.side_one_is_right_side,
            "is_left_side": self.side_one_is_right_side,
            "is_pullover": False,
            "outer_side": "RS",
            "inner_side": "WS",
            "decrease_text_triple_dart_standard_decrease": "K to 2 sts before third marker, ssk, sm, k to end.",
            "decrease_text_triple_dart_double_decrease": "K to 2 sts before second marker, ssk, sm, k to end.",
            "decrease_text_triple_dart_triple_decrease": "K to 2 sts before first marker, ssk, sm, k to third marker, ssk, sm, k to end.",
            "decrease_text_double_dart_standard_decrease": "K to 2 sts before second marker, ssk, sm, k to end.",
            "decrease_text_double_dart_double_dart_decrease": "K to 2 sts before first marker, ssk, sm, k to end.",
            "decrease_text_single_dart": "K to 2 sts before marker, SSK, sm, K to end.",
            "stitches_per_single_dart": "one stitch",
            "stitches_per_double_dart": "one stitch",
            "stitches_per_triple_dart": "two stitches",
            "increase_text_triple_dart_standard_dart": "K to third marker, m1R, sm, k to end.",
            "increase_text_triple_dart_double_dart": "K to second marker, m1R, sm, k to end.",
            "increase_text_triple_dart_triple_dart": "K to first marker, m1R, sm, k to last marker, m1R, sm, k to end.",
            "increase_text_double_dart_standard_dart": "K to second marker, m1R, sm, k to end.",
            "increase_text_double_dart_double_dart": "K to first marker, m1R, sm, k to end.",
            "increase_row_standard_dart": "Knit to marker, m1R, sm, k to end.",
            "reattach_side": "RS",
            "decrease_text_neckline_rs": "Work to last 3 sts, k2tog, k 1.",
            "decrease_text_neckline_ws": "P 1, p2tog, work to end.",
            "stitches_per_neckline_decrease": "one stitch",
            "decrease_text_armhole_rs_onest": "Knit 1, ssk, work to end.",
            "decrease_text_armhole_ws_onest": "Purl to last 3 sts, p2tog-tbl, p 1.",
            "stitches_per_armhole_dec_one": "one stitch",
            "decrease_text_armhole_rs_twosts": "Knit 1, ssk, work to last 3 sts, k2tog, k 1.",
            "decrease_text_armhole_ws_twosts": "Purl 1, p2tog, work to last 3 sts, p2tog-tbl, p 1.",
            "stitches_per_armhole_dec_twosts": "two stitches",
            "pre_armhole_row_parity": RP.to_string(side_two_pre_armhole_parity),
            "pre_neckline_row_parity": RP.to_string(side_two_pre_neckline_parity),
            "neckline_row_parity": RP.to_string(
                RP.reverse_parity(side_two_pre_neckline_parity)
            ),
            "hem_to_armhole_in_rows": self.piece_list.hem_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
            "hem_to_shoulders_in_rows": self.piece_list.hem_to_shoulders_in_rows(
                side_two_pre_armhole_parity
            ),
            "last_increase_to_armhole_in_rows": self.piece_list.last_increase_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
            "last_decrease_to_armhole_in_rows": self.piece_list.last_decrease_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
            "armhole_to_shoulders_in_rows": self.piece_list.armhole_to_shoulders_in_rows(
                side_two_pre_armhole_parity, side_two_pre_shoulder_parity
            ),
            "last_armhole_to_shoulders_in_rows": self.piece_list.last_armhole_to_shoulders_in_rows(
                side_two_pre_armhole_parity, side_two_pre_shoulder_parity
            ),
            "hem_to_first_armhole_in_rows": self.piece_list.hem_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
            "last_increase_to_first_armhole_in_rows": self.piece_list.last_increase_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
            "last_decrease_to_first_armhole_in_rows": self.piece_list.last_decrease_to_armhole_in_rows(
                side_two_pre_armhole_parity
            ),
        }

        if not self.exemplar.neckline.empty():
            neckline_dict = {
                "neckline_to_armhole_in_rows": self.piece_list.neckline_to_armhole_in_rows(
                    side_two_pre_neckline_parity, side_two_pre_armhole_parity
                ),
                "armhole_to_neckline_in_rows": self.piece_list.armhole_to_neckline_in_rows(
                    side_two_pre_armhole_parity, side_two_pre_neckline_parity
                ),
                "last_armhole_to_neckline_in_rows": self.piece_list.last_armhole_to_neckline_in_rows(
                    side_two_pre_armhole_parity, side_two_pre_neckline_parity
                ),
                "hem_to_neckline_in_rows": self.piece_list.hem_to_neckline_in_rows(
                    side_two_pre_neckline_parity
                ),
                "last_increase_to_neckline_in_rows": self.piece_list.last_increase_to_neckline_in_rows(
                    side_two_pre_neckline_parity
                ),
                "last_decrease_to_neckline_in_rows": self.piece_list.last_decrease_to_neckline_in_rows(
                    side_two_pre_neckline_parity
                ),
                "neckline": self.piece_list.neckline,
            }

            self.side_two_dict.update(neckline_dict)

        # Store these two attributes in case we need them in pullovers
        self.side_one_pre_shoulder_parity = side_one_pre_armhole_parity
        self.side_two_pre_shoulder_parity = side_two_pre_armhole_parity

    def _make_elements(self, additional_context):

        elements = sum(
            [
                self._make_cast_on_elements(additional_context),
                self._make_hourglass_elements(additional_context),
                self._make_neckline_and_shoulder_elements(additional_context),
                self._make_actuals_elements(additional_context),
                self._make_additional_elements(additional_context),
            ],
            [],
        )
        return elements

    def _make_cast_on_elements(self, additional_context):

        start_rows = CompoundResult(itertools.repeat(1, len(self.piece_list)))
        caston_subsection = BodyPieceSubsection(
            "Lower edging",
            _STARTS_BELOW_NECKLINE,
            start_rows,
            self.piece_list.waist_hem_height_in_rows,
        )

        spec_source = self.exemplar.get_spec_source()

        stitch_transition_text = self.make_stitch_transition_text(
            self.exemplar.hem_stitch, self.exemplar.allover_stitch
        )

        cast_on_context = additional_context.copy()

        cast_on_context["stitch_transition_text"] = stitch_transition_text

        cast_on_template = spec_source.get_waist_hem_template()
        caston_subsection.add_template_object(cast_on_template, cast_on_context)

        caston_element = Element("Lower edging", caston_subsection)
        return [caston_element]

    def _make_hourglass_elements(self, additional_context):
        if self.exemplar.is_hourglass:
            return self._make_hourglass_subsections_hourglass(additional_context)
        else:
            return self._make_hourglass_elements_non_hourglass(additional_context)

    def _make_hourglass_elements_non_hourglass(self, additional_context):

        if self.exemplar.is_straight:

            return []

        else:

            non_hourglass_context = copy.copy(additional_context)

            # Fill in starting/ending rows below

            if self.exemplar.is_aline:
                shaping_template = "a_line_silhouette"
                end_row = self.piece_list.last_decrease_row
                start_row = self.piece_list.begin_decreases_height_in_rows
                non_hourglass_context["any_ws_shaping_rows"] = (
                    self.piece_list.any_waist_decreases_on_ws.any()
                )

            else:
                assert self.exemplar.is_tapered
                shaping_template = "tapered_silhouette"
                end_row = self.piece_list.last_increase_row
                start_row = self.piece_list.begin_increases_height_in_rows
                non_hourglass_context["any_ws_shaping_rows"] = (
                    self.piece_list.any_bust_increases_on_ws.any()
                )

            shaping_subsection = BodyPieceSubsection(
                "Shaping", _STARTS_BELOW_NECKLINE, start_row, end_row
            )

            shaping_subsection.add_template_file(
                WAIST_AND_BUST, shaping_template, non_hourglass_context
            )

            shaping_element = Element("Shaping", shaping_subsection)
            return [shaping_element]

    def _make_hourglass_subsections_hourglass(self, additional_context):

        if self.exemplar.is_straight:
            return []
        else:

            waist_element = self._make_decreases_element(additional_context)

            bust_element = self._make_increases_element(additional_context)

            return [waist_element, bust_element]

    def _make_decreases_element(self, additional_context):

        # Fill in starting row below.
        has_decreases = self.piece_list.has_waist_decreases.any()
        start_row = (
            self.piece_list.begin_decreases_height_in_rows
            if has_decreases
            else self.piece_list.waist_hem_height_in_rows + 1
        )

        decreases_subsection = BodyPieceSubsection(
            "Waist shaping",
            _STARTS_BELOW_NECKLINE,
            start_row,
            self.piece_list.hem_to_waist_in_rows,
            interrupts_others=has_decreases,
            warn_if_interrupted=has_decreases,
        )

        if not has_decreases:

            decreases_subsection.add_template_file(
                WAISTS, "no_shaping", additional_context
            )

        else:

            decreases_subsection.add_template_file(
                WAISTS, "waist_start", additional_context
            )

            any_have_standard_decreases = (
                self.piece_list.num_waist_standard_decrease_rows.any(lambda x: x > 0)
            )
            any_have_double_darts = self.piece_list.num_waist_double_dart_rows.all(
                lambda x: x > 0
            )
            any_have_triple_darts = self.piece_list.num_waist_triple_dart_rows.all(
                lambda x: x > 0
            )

            shaping_context = copy.copy(additional_context)

            if all(
                [
                    any_have_standard_decreases,
                    not any_have_double_darts,
                    not any_have_triple_darts,
                ]
            ):

                shaping_context["waist_standard_decrease_repetitions"] = (
                    self.piece_list.num_waist_standard_decrease_repetitions.any(
                        lambda x: x > 0
                    )
                )

                decreases_subsection.add_template_file(
                    WAISTS, "standard_darts_only", shaping_context
                )

            elif all(
                [
                    any_have_standard_decreases,
                    any_have_double_darts,
                    not any_have_triple_darts,
                ]
            ):

                shaping_context["num_waist_non_double_dart_decrease_repetitions"] = (
                    self.piece_list.num_waist_non_double_dart_decrease_repetitions.any(
                        lambda x: x > 0
                    )
                )
                shaping_context[
                    "waist_non_double_dart_decrease_repetitions_minus_one"
                ] = self.piece_list.num_waist_non_double_dart_decrease_repetitions_minus_one.any(
                    lambda x: x > 0 if x is not None else False
                )
                shaping_context["num_waist_double_dart_decrease_repetitions"] = (
                    self.piece_list.num_waist_double_dart_decrease_repetitions.any(
                        lambda x: x > 0
                    )
                )

                decreases_subsection.add_template_file(
                    WAISTS, "standard_and_double_darts", shaping_context
                )

            elif all(
                [
                    any_have_standard_decreases,
                    any_have_double_darts,
                    any_have_triple_darts,
                ]
            ):

                shaping_context["num_waist_standard_decrease_repetitions"] = (
                    self.piece_list.num_waist_standard_decrease_repetitions.any(
                        lambda x: x > 0
                    )
                )
                shaping_context["num_waist_triple_dart_repetitions"] = (
                    self.piece_list.num_waist_triple_dart_repetitions.any(
                        lambda x: x > 0
                    )
                )

                decreases_subsection.add_template_file(
                    WAISTS, "standard_double_and_triple_darts", shaping_context
                )

            elif all([not any_have_standard_decreases, any_have_triple_darts]):

                shaping_context["num_waist_triple_dart_repetitions"] = (
                    self.piece_list.num_waist_triple_dart_repetitions.any(
                        lambda x: x > 0
                    )
                )
                shaping_context["num_waist_triple_dart_repetitions_minus_one"] = (
                    self.piece_list.num_waist_triple_dart_repetitions_minus_one.any(
                        lambda x: x > 0 if x is not None else False
                    )
                )

                decreases_subsection.add_template_file(
                    WAISTS, "double_and_triple_darts", shaping_context
                )
            else:
                raise RuntimeError("Should never happen")

        decreases_element = Element("Waist shaping", decreases_subsection)
        return decreases_element

    def _make_increases_element(self, additional_context):

        has_bust_increases = self.piece_list.has_bust_increases.any()
        end_row = (
            self.piece_list.last_increase_row
            if has_bust_increases
            else self.piece_list.hem_to_first_armhole_in_rows
        )
        increases_subsection = BodyPieceSubsection(
            "Bust shaping",
            _STARTS_BELOW_NECKLINE,
            self.piece_list.hem_to_waist_in_rows + 1,
            end_row,
            interrupts_others=has_bust_increases,
            warn_if_interrupted=has_bust_increases,
        )

        increases_subsection.add_template_file(WAISTS, "waist_end", additional_context)

        increases_subsection.add_template_file(
            WAIST_AND_BUST, self.marker_transition_template, additional_context
        )

        shaping_context = copy.copy(additional_context)

        if has_bust_increases:

            any_have_standard_increases = (
                self.piece_list.num_bust_standard_increase_rows.any(lambda x: x > 0)
            )
            any_have_double_increases = (
                self.piece_list.num_bust_double_dart_increase_rows.any(lambda x: x > 0)
            )
            any_have_triple_increases = self.piece_list.num_bust_triple_dart_rows.any(
                lambda x: x > 0
            )

            if all(
                [
                    any_have_standard_increases,
                    not any_have_double_increases,
                    not any_have_triple_increases,
                ]
            ):

                shaping_context["num_bust_standard_increase_repetitions"] = (
                    self.piece_list.num_bust_standard_increase_repetitions.any(
                        lambda x: x > 0
                    )
                )

                increases_subsection.add_template_file(
                    BUSTS, "standard_darts_only", shaping_context
                )

            elif all([any_have_double_increases, not any_have_triple_increases]):

                shaping_context["num_bust_non_double_dart_increase_repetitions"] = (
                    self.piece_list.num_bust_non_double_dart_increase_repetitions.any(
                        lambda x: x > 0
                    )
                )

                shaping_context[
                    "num_bust_non_double_dart_increase_repetitions_minus_one"
                ] = self.piece_list.num_bust_non_double_dart_increase_repetitions_minus_one.any(
                    lambda x: x > 0 if x is not None else False
                )

                shaping_context["num_bust_double_dart_increase_rows"] = (
                    self.piece_list.num_bust_double_dart_increase_rows.any(
                        lambda x: x > 1
                    )
                )

                increases_subsection.add_template_file(
                    BUSTS, "standard_and_double_darts", shaping_context
                )

            elif all([any_have_triple_increases, any_have_standard_increases]):

                shaping_context["num_bust_standard_increase_repetitions"] = (
                    self.piece_list.num_bust_standard_increase_repetitions.any(
                        lambda x: x > 0
                    )
                )

                shaping_context["num_bust_triple_dart_repetitions"] = (
                    self.piece_list.num_bust_triple_dart_repetitions.any(
                        lambda x: x > 0
                    )
                )

                increases_subsection.add_template_file(
                    BUSTS, "standard_double_and_triple_darts", shaping_context
                )

            elif all([any_have_triple_increases, not any_have_standard_increases]):

                shaping_context["num_bust_triple_dart_repetitions"] = (
                    self.piece_list.num_bust_triple_dart_repetitions.any(
                        lambda x: x > 0
                    )
                )

                shaping_context["multiple_num_bust_triple_dart_repetitions"] = (
                    self.piece_list.num_bust_triple_dart_repetitions.any(
                        lambda x: x > 1
                    )
                )

                increases_subsection.add_template_file(
                    BUSTS, "double_and_triple_darts", shaping_context
                )
            else:
                raise RuntimeError("Should never happen")

            increases_subsection.add_template_file(BUSTS, "bust_end", shaping_context)

        increases_element = Element("Bust increases", increases_subsection)
        return increases_element

    def _make_actuals_elements(self, additional_context):

        # Since we want the 'actuals' section to always come at the end, we express this
        # by saying that the actual section comes at row 'infinity'.
        start_end_rows = CompoundResult(
            itertools.repeat(float("inf"), len(self.piece_list))
        )
        actuals_subsection = BodyPieceSubsection(
            "Actuals", _END, start_end_rows, start_end_rows
        )

        additional_context = copy.copy(additional_context)
        additional_context["neckline"] = self.piece_list.neckline

        actuals_subsection.add_template_file(
            ACTUALS, self.actuals_template, additional_context
        )
        actuals_subsection.purely_informational = True

        actuals_element = Element("Actuals", actuals_subsection)
        return [actuals_element]

    # Not directly used in CommonLogicMixin, but will be used by
    # subclasses:
    def get_neckline_texts(self, sources, is_cardigan):
        """
        Builds and returns a dictionary of neckline-related patterntexts:
        either the ones necessary for pullover or the ones necessary for
        cardigan. This is determined by the `sources` argument, which should
        be a list of `(key, template_name, addl_context)` tuples. The
        dictionary returned will map `key` parameters to texts generated
        using the `template_name` and `addl_context` parameters.
        """

        neckline_start_template = make_template_path(
            NECKLINE_TEMPLATES, "neckline_start"
        )
        neckline = self.piece_list.neckline
        neckline_type = self.exemplar.neckline_content_type
        neckline_name = neckline_type.model

        neckline_texts = {}

        # context needed in neckline templates
        #
        # I hate to break the abstraction barrier here, but I don't see another way to do it
        neckline_specific_context = {"piece_is_graded": len(neckline) > 1}

        if neckline_name == "backneckline":
            rows_in_neckline = neckline.rows_in_neckline()
            at_least_five_rows = rows_in_neckline.map(lambda x: x >= 5)
            assert all(at_least_five_rows) or not any(at_least_five_rows)
            neckline_specific_context["any_over_five_rows"] = any(at_least_five_rows)
        elif neckline_name == "boatneck":
            neckline_specific_context["bottom_bindoffs"] = (
                neckline.bottom_bindoffs.any()
            )
            if is_cardigan:
                neckline_specific_context["bottom_bindoffs_cardigan"] = (
                    neckline.bottom_bindoffs_cardigan().any(lambda x: x > 0)
                )
        elif neckline_name == "crewneck":
            neckline_specific_context["rs_edge_decreases"] = (
                neckline.rs_edge_decreases.any()
            )
            neckline_specific_context["neck_edge_decreases"] = (
                neckline.neck_edge_decreases.any()
            )
            neckline_specific_context["no_rs_decreases_two_stitch_bindoffs"] = (
                neckline.no_rs_decreases_two_stitch_bindoffs().any()
            )
            neckline_specific_context["no_rs_decreases_one_stitch_bindoffs"] = (
                neckline.no_rs_decreases_one_stitch_bindoffs().any()
            )
            if is_cardigan:
                neckline_specific_context["center_bindoffs_cardigan"] = (
                    neckline.center_bindoffs_cardigan().any()
                )
        elif neckline_name == "scoopneck":
            neckline_specific_context["y_bindoffs"] = neckline.y_bindoffs.any()
            neckline_specific_context["z_bindoffs"] = neckline.z_bindoffs.any()
            neckline_specific_context["q_bindoffs"] = neckline.q_bindoffs.any()
            if is_cardigan:
                neckline_specific_context["initial_bindoffs_cardigan"] = (
                    neckline.initial_bindoffs_cardigan().any()
                )
        elif neckline_name == "turksandcaicosneck":
            neckline_specific_context["side_bindoffs"] = neckline.side_bindoffs.any()
        elif neckline_name == "veeneck":
            neckline_specific_context["decrease_rows"] = neckline.decrease_rows.any()
            neckline_specific_context["decrease_repeats"] = (
                neckline.decrease_repeats().any()
            )
            neckline_specific_context["some_ws_rows"] = (
                neckline.rows_per_decrease_odd().any()
            )
            neckline_specific_context["all_ws_rows"] = (
                neckline.rows_per_decrease_odd().all()
            )
            neckline_specific_context["extra_bindoffs"] = neckline.extra_bindoffs.any()
        else:
            # should never happen
            raise RuntimeError("Should never happen")

        for name, template_name, d in sources:

            neckline_specific_context["neckline_start"] = neckline_start_template
            neckline_specific_context.update(d)
            neckline_specific_context["bodypiece"] = self.piece_list
            neckline_specific_context["piece"] = neckline

            template_dir = os.path.join(NECKLINE_TEMPLATES, neckline_name)
            template_path = make_template_path(template_dir, template_name)
            html = render_template_path(template_path, neckline_specific_context)
            neckline_texts[name] = html

        return neckline_texts

    # Instantiates abstract method from InstructionSection

    def _get_start_rows_from_additonal_element(self, additional_element):
        gauge = self.exemplar.gauge
        # Because the additional element might be a 'full torso' element (and thus always
        # derived from the front meausurements) we need to provide both front and
        # back measurements each and every time we want to know the start row.
        pattern = self.exemplar.get_pattern()

        front_piece = PieceList(pattern.get_front_pieces())
        front_armhole_heights = front_piece.actual_hem_to_armhole
        front_shoulder_heights = front_piece.actual_hem_to_shoulder
        front_neckline_heights = front_piece.hem_to_neckline_shaping_start

        back_piece = PieceList(pattern.get_back_pieces())
        back_armhole_heights = back_piece.actual_hem_to_armhole
        back_shoulder_heights = back_piece.actual_hem_to_shoulder
        back_neckline_heights = back_piece.hem_to_neckline_shaping_start

        start_row = additional_element.start_rows(
            gauge,
            front_armhole_heights,
            front_neckline_heights,
            front_shoulder_heights,
            back_armhole_heights,
            back_neckline_heights,
            back_shoulder_heights,
        )
        return start_row

    def get_piece_final_rows(self, additional_context):
        mins = [
            min(x, y)
            for (x, y) in zip(
                self.piece_list.hem_to_shoulders_in_rows(RP.RS),
                self.piece_list.hem_to_shoulders_in_rows(RP.WS),
            )
        ]
        shoulder_row = CompoundResult(mins)
        final_row = shoulder_row + self.piece_list.rows_in_shoulder_shaping()
        return final_row


class PulloverRenderer(CommonLogicMixin, metaclass=abc.ABCMeta):
    """
    A PieceRenderer specifically for rendering half-body pieces. The reason
    That this needs a class of its own is that the rendering of these pieces
    requires that the necklines already be rendered and added to the
    context.
    """

    @property
    @abc.abstractmethod
    def sleevedness(self):
        return None

    @property
    def marker_transition_template(self):
        return "waist_marker_transition_halfbody"

    @property
    def actuals_template(self):
        return "actuals_halfbody"

    def __init__(self, piece):

        super(PulloverRenderer, self).__init__(piece)

        # Yes, this has a strict subset of the side one / side two dictionaries.
        # We will sometimes need to merge this with a side one/two dictionary,
        # and don't want to overwrite the side one/two dict information
        # about the side.
        pullover_pre_neckline_parity = RP.WS
        pullover_pre_armhole_parity = RP.WS
        self.pullover_dict = {
            "is_right_side": False,
            "is_left_side": False,
            "is_pullover": True,
            "decrease_text_triple_dart_standard_decrease": "Work to 2 stitches before third marker (color A), ssk, sm, work to fourth marker (color A), sm, k2tog, work to end.",
            "decrease_text_triple_dart_double_decrease": "Work to 2 stitches before second marker (color B), ssk, sm, work to fifth marker (color B), sm, k2tog, work to end.",
            "decrease_text_triple_dart_triple_decrease": "Work to 2 stitches before first marker (color C), ssk, sm, work to 2 stitches before third marker (color A), ssk, sm, work to fourth marker (color A), sm, k2tog,  work to sixth marker (color C), sm, k2tog, work to end.",
            "decrease_text_double_dart_standard_decrease": "Work to 2 stitches before second marker (color A), ssk, sm, work to third marker (color A), sm, k2tog, work to end.",
            "decrease_text_double_dart_double_dart_decrease": "Work to 2 stitches before first marker (color B), ssk, sm, work to fourth marker (color B), sm, k2tog, work to end.",
            "decrease_text_single_dart": "Work to 2 stitches before first marker, ssk, sm, work to second marker, sm, k2tog, work to end.",
            "stitches_per_single_dart": "two stitches",
            "stitches_per_double_dart": "two stitches",
            "stitches_per_triple_dart": "four stitches",
            "increase_text_triple_dart_standard_dart": "Work to third marker (color A), m1R, sm, work to fourth marker (color A), sm, m1L, work to end.",
            "increase_text_triple_dart_double_dart": "Work to second marker (color B), m1R, sm, work to fifth marker (color B), sm, m1L, work to end.",
            "increase_text_triple_dart_triple_dart": "Work to first marker (color C), m1R, sm, work to third marker (color A), m1R, sm, work to fourth marker (color A), sm, m1L, work to sixth marker (color C), sm, m1L, work to end.",
            "increase_text_double_dart_standard_dart": "Work to second marker (color A), m1R, sm, work to third marker (color A), sm, m1L, work to end.",
            "increase_text_double_dart_double_dart": "Work to first marker (color B), m1R, sm, work to fourth marker (color B), sm, m1L, work to end.",
            "increase_row_standard_dart": "Work to first marker, m1R, sm, work to second marker, sm, m1L, work to end.",
            "pre_neckline_row_parity": RP.to_string(pullover_pre_neckline_parity),
            "neckline_row_parity": RP.to_string(
                RP.reverse_parity(pullover_pre_neckline_parity)
            ),
            "hem_to_first_armhole_in_rows": self.piece_list.hem_to_first_armhole_in_rows,
            "last_increase_to_first_armhole_in_rows": self.piece_list.last_increase_to_first_armhole_in_rows,
            "last_decrease_to_first_armhole_in_rows": self.piece_list.last_decrease_to_first_armhole_in_rows,
            "last_increase_to_neckline_in_rows": self.piece_list.last_increase_to_neckline_in_rows(
                pullover_pre_neckline_parity
            ),
            "last_decrease_to_neckline_in_rows": self.piece_list.last_decrease_to_neckline_in_rows(
                pullover_pre_neckline_parity
            ),
            "hem_to_neckline_in_rows": self.piece_list.hem_to_neckline_in_rows(
                pullover_pre_neckline_parity
            ),
        }

        # if the armholes start before or with the neckline, we want to override
        # the side-dicts to give unified instructions for armhole shaping
        if (
            self.exemplar.hem_to_first_armhole_in_rows
            <= self.exemplar.hem_to_neckline_in_rows(pullover_pre_neckline_parity)
        ):
            additional_items = {
                "pre_armhole_row_parity": RP.to_string(pullover_pre_armhole_parity),
                "hem_to_armhole_in_rows": self.piece_list.hem_to_first_armhole_in_rows,
                "armhole_to_neckline_in_rows": self.piece_list.first_armhole_to_neckline_in_rows(
                    pullover_pre_neckline_parity
                ),
                "last_armhole_to_neckline_in_rows": self.piece_list.last_armhole_to_neckline_in_rows(
                    pullover_pre_armhole_parity, pullover_pre_neckline_parity
                ),
                "neckline_to_armhole_in_rows": self.piece_list.neckline_to_armhole_in_rows(
                    pullover_pre_neckline_parity, pullover_pre_armhole_parity
                ),
            }
            self.pullover_dict.update(additional_items)

            # If armhole start before necklines, then both armhole start on the same row
            # and have the same pre-armhole parity. So we need to re-compute the
            # armhole-to-shoulders distances
            self.side_one_dict["last_armhole_to_shoulders_in_rows"] = (
                self.piece_list.last_armhole_to_shoulders_in_rows(
                    pullover_pre_armhole_parity, self.side_one_pre_shoulder_parity
                )
            )
            self.side_one_dict["armhole_to_shoulders_in_rows"] = (
                self.piece_list.armhole_to_shoulders_in_rows(
                    pullover_pre_armhole_parity, self.side_one_pre_shoulder_parity
                )
            )

            self.side_two_dict["last_armhole_to_shoulders_in_rows"] = (
                self.piece_list.last_armhole_to_shoulders_in_rows(
                    pullover_pre_armhole_parity, self.side_two_pre_shoulder_parity
                )
            )
            self.side_two_dict["armhole_to_shoulders_in_rows"] = (
                self.piece_list.armhole_to_shoulders_in_rows(
                    pullover_pre_armhole_parity, self.side_two_pre_shoulder_parity
                )
            )

            self._armholes_after_neckline = False
        else:
            self._armholes_after_neckline = True

        self.neckline_sources = [
            ("halfbody_start", "halfbody_start", self.pullover_dict),
            ("halfbody_side1", "halfbody_side", self.side_one_dict),
            ("halfbody_side2", "halfbody_side", self.side_two_dict),
        ]

    def _make_neckline_and_shoulder_elements(self, additional_context):

        elements = []

        # Empty necklines should not occur in pullovers, just cardigans
        assert not self.exemplar.neckline.empty()

        neckline_texts = self.get_neckline_texts(
            self.neckline_sources, is_cardigan=False
        )

        # WE're going to render side1 before side2, so the side-1
        # instructions need to inclue re-attachting side2
        # Note: render() will include self.pullover_dict
        # in additional_context()
        extended_side_one_dict = self.side_one_dict
        extended_side_one_dict.update(additional_context)
        extended_side_one_dict["reattatch_instructions_needed"] = True

        extended_side_two_dict = self.side_two_dict
        extended_side_two_dict.update(additional_context)
        extended_side_two_dict["reattatch_instructions_needed"] = False

        # Neckline
        neckline_element = Element("Neckline")

        neckline_start_row = self.pullover_dict["hem_to_neckline_in_rows"] + 1
        neckline_rows = self.piece_list.neckline.rows_in_pullover_shaping()
        neckline_end_row = neckline_start_row + neckline_rows - 1
        # rows_in_pullover_shaping includes first and last rows, so we need to subtract out
        # the start row so as to not double-count it.
        neckline1_subsection = BodyPieceSubsection(
            "Neckline",
            _STARTS_BELOW_NECKLINE,
            neckline_start_row,
            neckline_end_row,
            is_neckline=True,
        )
        neckline1_subsection._add_text_chunk(neckline_texts["halfbody_start"])

        neckline1_subsection._add_text_chunk(neckline_texts["halfbody_side1"])

        # Note the use of the special class here-- this one sub-section is a corner case.
        neckline2_subsection = SecondNecklineSubSection(
            "Neckline", _STARTS_ON_SIDE2, neckline_start_row + 1, neckline_end_row
        )  # yes, even though this side starts one up
        # Pullover necklines end at the same row on
        # both sides
        neckline2_subsection.add_template_file(
            NECKLINE_TEMPLATES, "reattach_instructions", extended_side_two_dict
        )
        neckline2_subsection._add_text_chunk(neckline_texts["halfbody_side2"])

        neckline_element.add_subsection(neckline1_subsection)
        neckline_element.add_subsection(neckline2_subsection)

        # Shoulders
        shoulder_element = Element("Shoulder shaping")

        shoulder1_start_row = extended_side_one_dict["hem_to_shoulders_in_rows"] + 1
        shoulder1_end_row = (
            shoulder1_start_row + self.piece_list.rows_in_shoulder_shaping() - 1
        )
        # rows_in_shoulder_shaping includes both first and last row, so we need to un-double-count
        # the first row
        shoulder1_subsection = BodyPieceSubsection(
            "Right shoulder shaping",
            _STARTS_ON_SIDE1,
            shoulder1_start_row,
            shoulder1_end_row,
        )
        shoulder1_subsection.add_template_file(
            ARMHOLE_AND_SHOULDERS, "shoulders", extended_side_one_dict
        )

        shoulder2_start_row = extended_side_two_dict["hem_to_shoulders_in_rows"] + 1
        shoulder2_end_row = (
            shoulder2_start_row + self.piece_list.rows_in_shoulder_shaping() - 1
        )
        # rows_in_shoulder_shaping includes both first and last row, so we need to un-double-count
        # the first row
        shoulder2_subsection = BodyPieceSubsection(
            "Left shoulder shaping",
            _STARTS_ON_SIDE2,
            shoulder2_start_row,
            shoulder2_end_row,
        )
        shoulder2_subsection.add_template_file(
            ARMHOLE_AND_SHOULDERS, "shoulders", extended_side_two_dict
        )

        shoulder_element.add_subsection(shoulder1_subsection)
        shoulder_element.add_subsection(shoulder2_subsection)

        elements.extend([neckline_element, shoulder_element])

        # Armholes and mop-up

        armhole_element = Element("Armhole shaping")

        # If armholes after the neckline, give 'separate' armhole instructions
        if self._armholes_after_neckline:

            armhole1_start_row = extended_side_one_dict["hem_to_armhole_in_rows"] + 1
            armhole1_prearmhole_parity = extended_side_one_dict[
                "pre_armhole_row_parity"
            ]
            # rows_in_armhole_shaping includes the start row, so we need to
            # subtract it out to keep it from being double-counted
            armhole1_end_row = (
                armhole1_start_row
                + self.piece_list.rows_in_armhole_shaping_cardigan(
                    armhole1_prearmhole_parity
                )
                - 1
            )
            armhole1_subsection = BodyPieceSubsection(
                "Armhole (%s) shaping" % extended_side_one_dict["outer_side"],
                _STARTS_ON_SIDE1,
                armhole1_start_row,
                armhole1_end_row,
                is_armhole=True,
            )
            armhole1_subsection.add_start_template_non_overlap(
                ARMHOLE_AND_SHOULDERS,
                "armhole_start_non_overlap",
                extended_side_one_dict,
            )
            armhole1_subsection.add_start_template_overlap(
                ARMHOLE_AND_SHOULDERS, "armhole_start_overlap", extended_side_one_dict
            )

            basename = "armhole_%s_cardigan" % self.sleevedness
            armhole1_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, basename, extended_side_one_dict
            )

            armhole1_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, "shaping_done", extended_side_one_dict
            )

            armhole2_start_row = extended_side_two_dict["hem_to_armhole_in_rows"] + 1
            armhole2_prearmhole_parity = extended_side_two_dict[
                "pre_armhole_row_parity"
            ]
            # rows_in_armhole_shaping includes the start row, so we need to
            # subtract it out to keep it from being double-counted
            armhole2_end_row = (
                armhole2_start_row
                + self.piece_list.rows_in_armhole_shaping_cardigan(
                    armhole2_prearmhole_parity
                )
                - 1
            )
            armhole2_subsection = BodyPieceSubsection(
                "Armhole (%s) shaping" % extended_side_two_dict["outer_side"],
                _STARTS_ON_SIDE2,
                armhole2_start_row,
                armhole2_end_row,
                is_armhole=True,
            )
            armhole2_subsection.add_start_template_non_overlap(
                ARMHOLE_AND_SHOULDERS,
                "armhole_start_non_overlap",
                extended_side_two_dict,
            )
            armhole2_subsection.add_start_template_overlap(
                ARMHOLE_AND_SHOULDERS, "armhole_start_overlap", extended_side_two_dict
            )
            armhole2_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, basename, extended_side_two_dict
            )

            armhole2_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, "shaping_done", extended_side_two_dict
            )

            armhole_element.add_subsection(armhole1_subsection)
            armhole_element.add_subsection(armhole2_subsection)

        else:
            # Armhole start before or with the neckline. Give 'joint' armhole instructions

            start_row = self.piece_list.hem_to_first_armhole_in_rows + 1
            pre_armhole_parity = RP.from_string(
                self.pullover_dict["pre_armhole_row_parity"]
            )
            shaping_rows = self.piece_list.rows_in_armhole_shaping_pullover(
                pre_armhole_parity
            )
            end_row = (
                start_row + shaping_rows - 1
            )  # shaping_rows includes intial row, which is already
            # represented in start_row. So we need to subtract it out.
            armhole_subsection = BodyPieceSubsection(
                "Armhole shaping",
                _STARTS_BELOW_NECKLINE,
                start_row,
                end_row,
                is_armhole=True,
            )
            basename = "armholes_%s_pullover" % self.sleevedness

            armhole_subsection.add_start_template_non_overlap(
                ARMHOLE_AND_SHOULDERS,
                "armhole_start_non_overlap",
                extended_side_two_dict,
            )
            armhole_subsection.add_start_template_overlap(
                ARMHOLE_AND_SHOULDERS, "armhole_start_overlap", extended_side_two_dict
            )

            armhole_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, basename, extended_side_one_dict
            )

            armhole_element.add_subsection(armhole_subsection)

            neckline1_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, "shaping_done", extended_side_one_dict
            )

            neckline2_subsection.add_template_file(
                ARMHOLE_AND_SHOULDERS, "shaping_done", extended_side_two_dict
            )

        elements.append(armhole_element)

        return elements

    # Instantiate abstract 'additional-element' method from InstructionSection.

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        # Sanity test: will this section start after the piece actually ends?

        shoulder_start = max(
            [
                self.piece_list.hem_to_shoulders_in_rows(RP.WS),
                self.piece_list.hem_to_shoulders_in_rows(RP.RS),
            ]
        )
        piece_end_row = self.piece_list.rows_in_shoulder_shaping() + shoulder_start
        if start_row > piece_end_row:
            msg = "Section %s starts on row %s when piece ends on row %s" % (
                title,
                start_row,
                piece_end_row,
            )
            raise self.SectionStartsAfterPieceEnds(msg)
        else:
            # Does the element start below (or with) the neckline? Use the same logic as in __init__
            pullover_pre_neckline_parity = RP.WS
            if start_row <= self.piece_list.hem_to_neckline_in_rows(
                pullover_pre_neckline_parity
            ):

                # Yes. Return one subsection in the below-neckline group.
                subsection = BodyPieceSubsection(
                    title,
                    _STARTS_BELOW_NECKLINE,
                    start_row,
                    end_row,
                    interrupts_others=interrupts_others,
                    warn_if_interrupted=warn_if_interrupted,
                    is_neckline=False,
                    is_armhole=False,
                )
                return [subsection]

            else:
                # No. Return two subsections-- one for each side
                side1 = BodyPieceSubsection(
                    title,
                    _STARTS_ON_SIDE1,
                    start_row,
                    end_row,
                    interrupts_others=interrupts_others,
                    warn_if_interrupted=warn_if_interrupted,
                    is_neckline=False,
                    is_armhole=False,
                )
                side2 = BodyPieceSubsection(
                    title,
                    _STARTS_ON_SIDE2,
                    start_row,
                    end_row,
                    interrupts_others=interrupts_others,
                    warn_if_interrupted=warn_if_interrupted,
                    is_neckline=False,
                    is_armhole=False,
                )
                return [side1, side2]

    # override the PieceRenderer template so that we can throw the
    # self.pullover_dict context in:
    def render(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        final_context = {}
        final_context.update(self.pullover_dict)
        final_context.update(additional_context)
        safe_html = super(PulloverRenderer, self).render(final_context)
        return safe_html


class CardiganRenderer(CommonLogicMixin, metaclass=abc.ABCMeta):
    """
    A PieceRenderer specifically for rendering half-body pieces. The reason
    That this needs a class of its own is that the rendering of these pieces
    requires that the necklines already be rendered and added to the
    context.
    """

    @property
    @abc.abstractmethod
    def sleevedness(self):
        return None

    @property
    def marker_transition_template(self):
        return "waist_marker_transition_cardigan"

    @property
    def actuals_template(self):
        return "actuals_cardigan"

    def _make_neckline_and_shoulder_elements(self, side_dict):

        return_me = []

        subsection_group = (
            _STARTS_ON_SIDE1 if side_dict["is_left_side"] else _STARTS_ON_SIDE2
        )

        # Armholes

        armhole_start_row = side_dict["hem_to_armhole_in_rows"] + 1
        armhole_parity = side_dict["pre_armhole_row_parity"]
        armhole_end_row = (
            armhole_start_row
            + self.piece_list.rows_in_armhole_shaping_cardigan(armhole_parity)
            - 1
        )
        # rows_in_shaping includes start row, so subtract it out so as not to double-count
        armhole_section = BodyPieceSubsection(
            "Armhole shaping",
            _STARTS_BELOW_NECKLINE,
            armhole_start_row,
            armhole_end_row,
            is_armhole=True,
        )
        basename = "armhole_%s_cardigan" % self.sleevedness
        armhole_section.add_start_template_non_overlap(
            ARMHOLE_AND_SHOULDERS, "armhole_start_non_overlap", side_dict
        )
        armhole_section.add_start_template_overlap(
            ARMHOLE_AND_SHOULDERS, "armhole_start_overlap", side_dict
        )
        armhole_section.add_template_file(ARMHOLE_AND_SHOULDERS, basename, side_dict)

        armhole_element = Element("Armhole shaping", armhole_section)

        # Shoulders

        shoulder_start_row = side_dict["hem_to_shoulders_in_rows"] + 1
        shoulder_end_row = shoulder_start_row + 2
        shoulder_subsection = BodyPieceSubsection(
            "Shoulder shaping", subsection_group, shoulder_start_row, shoulder_end_row
        )
        shoulder_subsection.add_template_file(
            ARMHOLE_AND_SHOULDERS, "shoulders", side_dict
        )
        shoulder_element = Element("Shoulder shaping", shoulder_subsection)

        return_me.extend([armhole_element, shoulder_element])

        # First, deal with a corner case-- neckline is empty (as would be the
        # case when e.g., the button-band allowance is at maximum width).

        if self.exemplar.neckline.empty():

            armhole_section.add_template_file(
                ARMHOLE_AND_SHOULDERS, "shaping_done", side_dict
            )

        else:

            # From this point on, we can assume necklines exist and so various
            # values (e.g., self.section_list.hem_to_neckline_shaping_start) are
            # not None

            neckline_sources = [
                ("cardigan_start", "cardigan_start", side_dict),
                ("cardigan_side", "cardigan_side", side_dict),
            ]
            neckline_texts = self.get_neckline_texts(neckline_sources, is_cardigan=True)
            necklines = self.piece_list.neckline

            neckline_start_row = side_dict["hem_to_neckline_in_rows"] + 1
            neckline_start_row_parity = RP.from_string(side_dict["neckline_row_parity"])
            # rows_in_shaping includes the start row, so remove to avoid double-counting
            neckline_end_row = (
                neckline_start_row
                + necklines.rows_in_cardigan_shaping(neckline_start_row_parity)
                - 1
            )
            neckline_subsection = BodyPieceSubsection(
                "Neckline",
                _STARTS_BELOW_NECKLINE,
                neckline_start_row,
                neckline_end_row,
                is_neckline=True,
            )
            neckline_subsection._add_text_chunk(neckline_texts["cardigan_start"])

            neckline_subsection._add_text_chunk(neckline_texts["cardigan_side"])

            if armhole_section <= neckline_subsection:
                neckline_subsection.add_template_file(
                    ARMHOLE_AND_SHOULDERS, "shaping_done", side_dict
                )
            else:
                armhole_section.add_template_file(
                    ARMHOLE_AND_SHOULDERS, "shaping_done", side_dict
                )

            neckline_element = Element("Neckline", neckline_subsection)

            return_me.append(neckline_element)

        return return_me

    # Instantiate abstract 'additional-element' method from InstructionSection.

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):

        # Sanity test: will this section start after the piece actually ends?
        # Note: 'additional_context' will be the side-dict
        pre_shoulder_parity = additional_context["pre_armhole_row_parity"]
        piece_end_row = (
            self.piece_list.rows_in_shoulder_shaping()
            + self.piece_list.hem_to_shoulders_in_rows(pre_shoulder_parity)
        )
        if start_row > piece_end_row:
            msg = "Section %s starts on row %s when piece ends on row %s" % (
                title,
                start_row,
                piece_end_row,
            )
            raise self.SectionStartsAfterPieceEnds(msg)
        else:
            # Because we're in a cardigan, we need only sort by start-row and can disregard group.
            # Therefore we take a shortcut and assign it to the below-neckline group always
            # (like we do for armholes in _make_neckline_and_shoulder_elements)

            subsection = BodyPieceSubsection(
                title,
                _STARTS_BELOW_NECKLINE,
                start_row,
                end_row,
                interrupts_others=interrupts_others,
                warn_if_interrupted=warn_if_interrupted,
                is_neckline=False,
                is_armhole=False,
            )
            return [subsection]

    def get_piece_final_rows(self, additional_context):
        pre_shoulder_parity = additional_context["pre_armhole_row_parity"]
        shoulder_row = self.piece_list.hem_to_shoulders_in_rows(pre_shoulder_parity)
        final_row = shoulder_row + self.piece_list.rows_in_shoulder_shaping()
        return final_row

    def render(self, additional_context=None):
        """
        Overrides the `render()` method from `PieceRenderer` so that
        we can render twice: once for the left side, once for the right side.
        """
        if additional_context is None:
            additional_context = {}

        # a quickie helper function
        def make_side_piece_name(side_dict):
            return "%s Front" % side_dict["side_name"]

        side_one_piece_name = make_side_piece_name(self.side_one_dict)
        side_one_context = {"piece_name": side_one_piece_name}
        side_one_context.update(self.side_one_dict)
        side_one_context.update(additional_context)
        side_one_html = super(CardiganRenderer, self).render(side_one_context)

        side_two_piece_name = make_side_piece_name(self.side_two_dict)
        side_two_context = {"piece_name": side_two_piece_name}
        side_two_context.update(self.side_two_dict)
        side_two_context.update(additional_context)
        side_two_html = super(CardiganRenderer, self).render(side_two_context)

        final_html = side_one_html + side_two_html
        safe_final_html = django.utils.safestring.mark_safe(final_html)
        return safe_final_html


class SleevedMixin(object):
    @property
    def sleevedness(self):
        return "sleeved"


class VestMixin(object):
    @property
    def sleevedness(self):
        return "vest"


class FrontMixin(object):
    @property
    def side_one_name(self):
        return "Right"

    @property
    def side_two_name(self):
        return "Left"

    @property
    def side_one_is_right_side(self):
        return True

    # Instantiate abstract 'additional element' methods from InstructionSection. See there for
    # definitions and usage.

    def _get_additional_elements_from_design(self, design):
        front_qs = design.additionalfrontelement_set.all()
        front_list = list(front_qs)
        full_qs = design.additionalfulltorsoelement_set.all()
        full_list = list(full_qs)
        return front_list + full_list


class BackMixin(object):
    @property
    def side_one_name(self):
        return "Left"

    @property
    def side_two_name(self):
        return "Right"

    @property
    def side_one_is_right_side(self):
        return False

    # Instantiate abstract 'additional element' methods from InstructionSection. See there for
    # definitions and usage.

    def _get_additional_elements_from_design(self, design):
        back_els = design.additionalbackelement_set.all()
        back_list = list(back_els)
        full_qs = design.additionalfulltorsoelement_set.all()
        full_list = list(full_qs)
        return back_list + full_list


#####################################################################
# actual renderers
#####################################################################


class SweaterbackRenderer(SleevedMixin, BackMixin, PulloverRenderer):
    piece_name = "Sweater Back"


class SweaterfrontRenderer(SleevedMixin, FrontMixin, PulloverRenderer):
    piece_name = "Sweater Front"


class VestbackRenderer(VestMixin, BackMixin, PulloverRenderer):
    piece_name = "Vest Back"


class VestfrontRenderer(VestMixin, FrontMixin, PulloverRenderer):
    piece_name = "Vest Front"


class CardiganSleevedRenderer(SleevedMixin, FrontMixin, CardiganRenderer):
    piece_name = "Cardigan"


class CardiganVestRenderer(VestMixin, FrontMixin, CardiganRenderer):
    piece_name = "Cardigan"
