import copy
import itertools
import logging
import os.path

logger = logging.getLogger(__name__)

from customfit.helpers.math_helpers import CompoundResult
from customfit.patterns.renderers import Element, InstructionSection, SubSection

from .base import SWEATER_PIECE_TEMPLATES

SLEEVE_TEMPLATES = os.path.join(SWEATER_PIECE_TEMPLATES, "sleeve_templates")


class SleeveSubSection(SubSection):
    # These subsections are really easy-- they are sorted by starting row, and they overlap iff there's overlap
    # between beginning row and ending row.

    def __init__(
        self,
        display_name,
        start_rows,
        end_rows,
        interrupts_others=True,
        warn_when_interrupted=True,
    ):
        super(SleeveSubSection, self).__init__()
        self._display_name = display_name
        self._start_rows = start_rows
        self._end_rows = end_rows
        self._interrupts_others = interrupts_others
        self._warn_when_interrupted = warn_when_interrupted

    @property
    def display_name(self):
        return self._display_name

    @property
    def interrupts_others(self):
        return self._interrupts_others

    @property
    def warn_if_interrupted(self):
        return self._warn_when_interrupted

    def __eq__(self, other):
        return self.start_rows == other.start_rows

    def __lt__(self, other):
        assert isinstance(other, SleeveSubSection)
        return self.smallest_start_row < other.smallest_start_row

    def _find_starts_during_across_grades(self, other):
        # Sanity check
        assert isinstance(other, SleeveSubSection)
        assert isinstance(self.start_rows, CompoundResult)
        assert isinstance(other.end_rows, CompoundResult)
        gradewise_starts_during = [
            (o_s <= s_s) and (s_s <= o_e)
            for (s_s, o_s, o_e) in zip(
                self.start_rows, other.start_rows, other.end_rows
            )
        ]
        return gradewise_starts_during

    def starts_during(self, other):
        gradewise_starts_during = self._find_starts_during_across_grades(other)
        return_me = any(gradewise_starts_during)
        return return_me

    def starts_during_all_grades(self, other):
        gradewise_starts_during = self._find_starts_during_across_grades(other)
        return_me = all(gradewise_starts_during)
        return return_me

    @property
    def start_rows(self):
        return self._start_rows

    @property
    def end_rows(self):
        return self._end_rows


class SleeveRenderer(InstructionSection):

    piece_name = "Sleeve"

    def _make_caston_element(self, additional_context):

        start_rows = CompoundResult(
            itertools.repeat(1, len(self.piece_list.wrist_hem_height_in_rows))
        )
        cast_on_subsection = SleeveSubSection(
            "Cast on edge", start_rows, self.piece_list.wrist_hem_height_in_rows
        )

        stitch_transition_text = self.make_stitch_transition_text(
            self.exemplar.hem_stitch, self.exemplar.allover_stitch
        )
        cast_on_context = additional_context.copy()
        cast_on_context["stitch_transition_text"] = stitch_transition_text

        spec_source = self.exemplar.get_spec_source()
        cast_on_template = spec_source.get_sleeve_hem_template()
        cast_on_subsection.add_template_object(cast_on_template, cast_on_context)
        cast_on_element = Element("Cast-ons", cast_on_subsection)

        return cast_on_element

    def _make_shaping_element(self, additional_context):

        if self.exemplar.is_straight:
            return None

        else:
            sleeve_context = copy.copy(additional_context)

            pl = self.piece_list

            more_context = {
                "multiple_shaping_rows": pl.num_shaping_rows().any(lambda x: x > 1),
                "sleeve_is_tapered": self.exemplar.is_tapered,
                "shaping_rows_on_ws": pl.shaping_row_on_ws.any(bool),
            }
            sleeve_context.update(more_context)

            if not pl.num_sleeve_compound_increase_rows.any():
                # all simple shaping
                compound_context = {
                    "show_simple_shaping_instructions": True,
                    "simple_shaping_grades": False,
                    "show_compound_shaping_instructions": False,
                    "compound_shaping_grades": False,
                    "simple": {
                        "inter_sleeve_increase_rows_plus_one": pl.inter_sleeve_increase_rows_plus_one,
                        "num_shaping_rows": pl.num_shaping_rows,
                        "shaping_rows_plural": (
                            pl.inter_sleeve_increase_rows_plus_one
                        ).any(lambda x: False if x is None else x >= 2),
                    },
                }
            elif pl.num_sleeve_compound_increase_rows.all():
                # all compound shaping
                compound_context = {
                    "show_simple_shaping_instructions": False,
                    "simple_shaping_grades": False,
                    "show_compound_shaping_instructions": True,
                    "compound_shaping_grades": False,
                    "compound_rows_plural": (pl.rows_after_compound_shaping_rows).any(
                        lambda x: False if x is None else x >= 1
                    ),
                    "compound": {
                        "inter_sleeve_increase_rows_plus_one_plural": (
                            pl.inter_sleeve_increase_rows_plus_one
                        ).any(lambda x: False if x is None else x >= 2),
                        "inter_sleeve_increase_rows_plus_one": pl.inter_sleeve_increase_rows_plus_one,
                        "num_sleeve_increase_rows_plural": pl.num_sleeve_increase_rows.any(
                            lambda x: False if x is None else x >= 2
                        ),
                        "num_sleeve_increase_rows": pl.num_sleeve_increase_rows,
                        "rows_after_compound_shaping_rows_plus_one_plural": pl.rows_after_compound_shaping_rows_plus_one.any(
                            lambda x: False if x is None else x >= 2
                        ),
                        "rows_after_compound_shaping_rows_plus_one": pl.rows_after_compound_shaping_rows_plus_one,
                        "num_sleeve_compound_increase_rows_plural": pl.num_sleeve_compound_increase_rows.any(
                            lambda x: False if x is None else x >= 2
                        ),
                        "num_sleeve_compound_increase_rows": pl.num_sleeve_compound_increase_rows,
                        "num_shaping_rows_plural": pl.num_shaping_rows().any(
                            lambda x: False if x is None else x >= 2
                        ),
                        "num_shaping_rows": pl.num_shaping_rows,
                    },
                }
            else:
                # Mixed

                def _simple_attrs(attr_name, call=False):
                    tuples = zip(
                        getattr(pl, attr_name), pl.num_sleeve_compound_increase_rows
                    )
                    if call:
                        return [None if comp else attr() for (attr, comp) in tuples]
                    else:
                        return [None if comp else attr for (attr, comp) in tuples]

                def _compound_attrs(attr_name, call=False):
                    tuples = zip(
                        getattr(pl, attr_name), pl.num_sleeve_compound_increase_rows
                    )
                    if call:
                        return [attr() if comp else None for (attr, comp) in tuples]
                    else:
                        return [attr if comp else None for (attr, comp) in tuples]

                def _compound_attrs_plural(attr_name, call=False):
                    compound_attrs = _compound_attrs(attr_name, call)
                    return any(False if x is None else x >= 2 for x in compound_attrs)

                compound_context = {
                    "show_simple_shaping_instructions": True,
                    "simple_shaping_grades": _simple_attrs("finished_full_bust"),
                    "simple": {
                        "inter_sleeve_increase_rows_plus_one": _simple_attrs(
                            "inter_sleeve_increase_rows_plus_one"
                        ),
                        "num_shaping_rows": _simple_attrs(
                            "num_shaping_rows", call=True
                        ),
                        "shaping_rows_plural": any(
                            False if x is None else x >= 2
                            for x in _simple_attrs(
                                "inter_sleeve_increase_rows_plus_one"
                            )
                        ),
                    },
                    "show_compound_shaping_instructions": True,
                    "compound_shaping_grades": _compound_attrs("finished_full_bust"),
                    "compound_rows_plural": (pl.rows_after_compound_shaping_rows).any(
                        lambda x: False if x is None else x >= 1
                    ),
                    "compound": {
                        "inter_sleeve_increase_rows_plus_one_plural": _compound_attrs_plural(
                            "inter_sleeve_increase_rows_plus_one"
                        ),
                        "inter_sleeve_increase_rows_plus_one": _compound_attrs(
                            "inter_sleeve_increase_rows_plus_one"
                        ),
                        "num_sleeve_increase_rows_plural": _compound_attrs_plural(
                            "num_sleeve_increase_rows"
                        ),
                        "num_sleeve_increase_rows": _compound_attrs(
                            "num_sleeve_increase_rows"
                        ),
                        "rows_after_compound_shaping_rows_plus_one_plural": _compound_attrs_plural(
                            "rows_after_compound_shaping_rows_plus_one"
                        ),
                        "rows_after_compound_shaping_rows_plus_one": _compound_attrs(
                            "rows_after_compound_shaping_rows_plus_one"
                        ),
                        "num_sleeve_compound_increase_rows_plural": _compound_attrs_plural(
                            "num_sleeve_compound_increase_rows"
                        ),
                        "num_sleeve_compound_increase_rows": _compound_attrs(
                            "num_sleeve_compound_increase_rows"
                        ),
                        "num_shaping_rows_plural": _compound_attrs_plural(
                            "num_shaping_rows", call=True
                        ),
                        "num_shaping_rows": _compound_attrs(
                            "num_shaping_rows", call=True
                        ),
                    },
                }

            sleeve_context.update(compound_context)

            shaping_subsection = SleeveSubSection(
                "Shaping",
                self.piece_list.first_shaping_height_in_rows,
                self.piece_list.last_shaping_height_in_rows,
            )

            shaping_subsection.add_template_file(
                SLEEVE_TEMPLATES, "sleeve_shaping_start", sleeve_context
            )
            shaping_subsection.add_template_file(
                SLEEVE_TEMPLATES, "sleeve_shaping_counts", sleeve_context
            )
            shaping_subsection.add_template_file(
                SLEEVE_TEMPLATES, "sleeve_shaping_instructions", sleeve_context
            )
            shaping_subsection.add_template_file(
                SLEEVE_TEMPLATES, "sleeve_shaping_end", sleeve_context
            )

            shaping_element = Element("Shaping", shaping_subsection)
            return shaping_element

    def _make_armcap_element(self, additional_context):
        sleeve_context = copy.copy(additional_context)
        sleeve_context["show_shaping"] = any(
            [
                self.piece_list.armscye_x.any(),
                self.piece_list.armscye_y.any(),
                self.piece_list.armscye_d.any(),
                self.piece_list.six_count_beads.any(),
                self.piece_list.four_count_beads.any(),
                self.piece_list.two_count_beads.any(),
                self.piece_list.one_count_beads.any(),
            ]
        )

        armcap_subsection = SleeveSubSection(
            "Sleeve-cap",
            self.piece_list.actual_wrist_to_cap_in_rows + 1,
            self.piece_list.actual_wrist_to_end_in_rows,
        )
        armcap_subsection.add_start_template_non_overlap(
            SLEEVE_TEMPLATES, "sleeve_cap_start_non_overlap", sleeve_context
        )
        armcap_subsection.add_start_template_overlap(
            SLEEVE_TEMPLATES, "sleeve_cap_start_overlap", sleeve_context
        )
        armcap_subsection.add_template_file(
            SLEEVE_TEMPLATES, "sleeve_cap", sleeve_context
        )

        armcap_element = Element("Sleeve cap", armcap_subsection)
        return armcap_element

    def _make_actuals_element(self, additional_context):
        # Since we want the 'actuals' section to always come at the end, we express this
        # by saying that the actual section comes at row 'infinity'
        start_rows = CompoundResult(
            itertools.repeat(float("inf"), len(self.piece_list))
        )

        actuals_subsection = SleeveSubSection(
            "Actuals",
            start_rows,
            start_rows,
            interrupts_others=False,
            warn_when_interrupted=False,
        )
        actuals_subsection.add_template_file(
            SLEEVE_TEMPLATES, "sleeve_actuals", additional_context
        )
        actuals_element = Element("Actuals", actuals_subsection)
        return actuals_element

    ################################################################################################
    #
    # Instantiate abstract methods for 'additional design elements'. See InstructionSection for
    # definitions and usage
    #
    #################################################################################################

    def _get_additional_elements_from_design(self, design):
        el_qs = design.additionalsleeveelement_set.all()
        el_list = list(el_qs)
        return el_list

    def _get_start_rows_from_additonal_element(self, additional_element):
        gauge = self.exemplar.gauge
        start_rows = additional_element.start_rows(
            self.piece_list.actual_wrist_to_cap, gauge
        )
        return start_rows

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        # Sanity test: will this section start after the sleeve actually ends?
        piece_end_row = self.piece_list.actual_wrist_to_cap_in_rows
        if start_row > piece_end_row:
            msg = "Section %s starts on row %s when piece ends on row %s" % (
                title,
                start_row,
                piece_end_row,
            )
            raise self.SectionStartsAfterPieceEnds(msg)
        else:
            single_subsection = SleeveSubSection(
                title,
                start_row,
                end_row,
                interrupts_others=interrupts_others,
                warn_when_interrupted=warn_if_interrupted,
            )
            return [single_subsection]

    def get_piece_final_rows(self, additional_context):
        end_row = self.piece_list.actual_wrist_to_end_in_rows
        return end_row

    def _make_elements(self, additional_context):

        elements = [
            self._make_caston_element(additional_context),
            self._make_shaping_element(additional_context),
            self._make_armcap_element(additional_context),
            self._make_actuals_element(additional_context),
        ]
        elements += self._make_additional_elements(additional_context)
        return_me = [element for element in elements if element is not None]
        return return_me
