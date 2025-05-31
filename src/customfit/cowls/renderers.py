import itertools
import logging
import os.path

import django.utils

from customfit.helpers.math_helpers import CompoundResult
from customfit.patterns.renderers import (
    AboutDesignerRenderer,
    DesignerNotesRenderer,
    Element,
    FinishingSubSection,
    InstructionSection,
    PatternRendererBase,
    PdfPersonalNotesRenderer,
    PieceList,
    PreambleRendererBase,
    SchematicRendererBase,
    StitchChartsRenderer,
    StitchesSectionRenderer,
    SubSection,
    WebPersonalNotesRenderer,
)

logger = logging.getLogger(__name__)


COWL_TEMPLATES = os.path.join("cowls", "patterntext_templates")
# COWL_FINISHING_TEMPLATE = os.path.join(COWL_TEMPLATES, "finishing")


class CowlPreambleRendererBase(PreambleRendererBase):

    template_dir = COWL_TEMPLATES

    _base_notions = "Darning needle"

    def _make_design_choices_text(self):
        spec_source = self.piece.get_spec_source()
        if spec_source.design_origin:
            origin = spec_source.design_origin

            patterntext = (
                "This pattern is a customized version of the design &quot;%s&quot;"
                % origin.name
            )

            designer = origin.designer
            if designer is not None:
                patterntext += " by %s" % designer.full_name
            patterntext += "."

            safe_patterntext = django.utils.safestring.mark_safe(patterntext)

            return safe_patterntext

        else:
            return None


class PdfPreambleRenderer(CowlPreambleRendererBase):
    template_name = "design_choices_pdf"


class WebPreambleRenderer(CowlPreambleRendererBase):
    template_name = "design_choices_web"


# Yes, this is to be formatted as a piece, not a mock-piece
class CowlFinishingRenderer(InstructionSection):

    piece_name = "Finishing Instructions"

    def _make_elements(self, additional_context=None):
        return [self._make_main_element(additional_context)]

    def _make_main_element(self, additional_context=None):
        subsection = FinishingSubSection()
        # The value 1 is arbitrary. The only consideration is how it compares to sort_order for
        # other subsections (of which there are none currently, I know, but there may be some in
        # the future).
        subsection.sort_order = 1

        if additional_context is None:
            additional_context = {}

        subsection.add_template_file(COWL_TEMPLATES, "finishing", additional_context)

        element = Element("Finishing", subsection)

        return element

    # Abstract methods from InstructionSection. They should never be called
    def _get_additional_elements_from_design(self, design):
        raise RuntimeError("Should never be called")

    def _get_start_rows_from_additonal_element(self, additional_element):
        raise RuntimeError("Should never be called")

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        raise RuntimeError("Should never be called")

    def get_piece_final_rows(self):
        raise RuntimeError("Should never be called")


class CowlSchematicRendererBase(SchematicRendererBase):

    def _get_template_dir(self):
        return COWL_TEMPLATES


class CowlSchematicRendererWeb(CowlSchematicRendererBase):

    def _get_template_name(self):
        return "schematic_measurements_web"


class CowlSchematicRendererPrint(CowlSchematicRendererBase):

    def _get_template_name(self):
        return "schematic_measurements_print"


class CowlPieceSubSection(SubSection):
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
        super(CowlPieceSubSection, self).__init__()
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
        assert isinstance(other, CowlPieceSubSection)
        assert isinstance(self.start_rows, CompoundResult)
        assert isinstance(other.start_rows, CompoundResult)
        return self.start_rows == other.start_rows

    def __lt__(self, other):
        assert isinstance(other, CowlPieceSubSection)
        return self.smallest_start_row < other.smallest_start_row

    def _find_starts_during_across_grades(self, other):
        # Sanity check
        assert isinstance(other, CowlPieceSubSection)
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


class CowlPieceRenderer(InstructionSection):

    piece_name = "Cowl"

    def _make_caston_element(self, additional_context):
        start_rows = CompoundResult(itertools.repeat(1, len(self.piece_list)))
        cast_on_subsection = CowlPieceSubSection(
            "Cast on edge", start_rows, self.piece_list.edging_height_in_rows
        )

        stitch_transition_text = self.make_stitch_transition_text(
            self.exemplar.edging_stitch, self.exemplar.main_stitch
        )
        cast_on_context = additional_context.copy()
        cast_on_context["stitch_transition_text"] = stitch_transition_text

        spec_source = self.exemplar.get_spec_source()
        cast_on_template = spec_source.get_caston_edging_template()
        cast_on_subsection.add_template_object(cast_on_template, cast_on_context)
        cast_on_element = Element("Cast-ons", cast_on_subsection)

        return cast_on_element

    def _make_main_section_element(self, additional_context):
        main_subsection = CowlPieceSubSection(
            "Main section",
            self.piece_list.first_main_section_row,
            self.piece_list.last_main_section_row,
        )

        stitch_transition_text = self.make_stitch_transition_text(
            self.exemplar.main_stitch, self.exemplar.edging_stitch
        )
        main_section_context = additional_context.copy()
        main_section_context["stitch_transition_text"] = stitch_transition_text

        spec_source = self.exemplar.get_spec_source()
        main_section_template = spec_source.get_main_section_template()

        main_subsection.add_template_object(main_section_template, main_section_context)
        main_slement = Element("Main section", main_subsection)
        return main_slement

    def _make_final_edging_element(self, additional_context):
        cast_off_subsection = CowlPieceSubSection(
            "Cast off edge",
            self.piece_list.first_row_castoff_section,
            self.piece_list.total_rows,
        )

        cast_off_context = additional_context.copy()

        spec_source = self.exemplar.get_spec_source()
        cast_off_template = spec_source.get_castoff_edging_template()
        cast_off_subsection.add_template_object(cast_off_template, cast_off_context)
        cast_off_element = Element("Cast-offs", cast_off_subsection)

        return cast_off_element

    def _make_actuals_element(self, additional_context):
        # Since we want the 'actuals' section to always come at the end, we express this
        # by saying that the actual section comes at row 'infinity'
        start_rows = CompoundResult(
            itertools.repeat(float("inf"), len(self.piece_list))
        )
        end_rows = CompoundResult(itertools.repeat(float("inf"), len(self.piece_list)))

        actuals_subsection = CowlPieceSubSection(
            "Actuals",
            start_rows,
            end_rows,
            interrupts_others=False,
            warn_when_interrupted=False,
        )
        actuals_subsection.add_template_file(
            COWL_TEMPLATES, "cowl_actuals", additional_context
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
        # should never be called, but must be defined
        return []

    def _get_start_rows_from_additonal_element(self, additional_element):
        # should never be called, but must be defined
        raise NotImplemented()

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        # should never be called, but must be defined
        raise NotImplemented()

    def get_piece_final_rows(self, additional_context):
        piece = self.piece_list
        end_row = piece.total_rows
        return end_row

    def _make_elements(self, additional_context):

        elements = [
            self._make_caston_element(additional_context),
            self._make_main_section_element(additional_context),
            self._make_final_edging_element(additional_context),
            self._make_actuals_element(additional_context),
        ]
        return_me = [element for element in elements if element is not None]
        return return_me


class CowlPatternRendererFullBase(PatternRendererBase):

    def _make_postamble_piece_list(self, pattern):
        return [
            (pattern, AboutDesignerRenderer),
        ]


class CowlPatternRendererPfdBase(PatternRendererBase):

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.cowl, CowlPieceRenderer),
            (pattern, CowlFinishingRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
            (pattern, CowlSchematicRendererPrint),
        ]


class CowlPatternRendererWebFull(CowlPatternRendererFullBase):

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.cowl, CowlPieceRenderer),
            (pattern, CowlFinishingRenderer),
        ]

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, WebPreambleRenderer),
            (pattern, WebPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
            (pattern, CowlSchematicRendererWeb),
        ]


class CowlPatternRendererPdfFull(
    CowlPatternRendererFullBase, CowlPatternRendererPfdBase
):

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, PdfPreambleRenderer),
            (pattern, PdfPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]


class CowlPatternRendererPdfAbridged(CowlPatternRendererPfdBase):

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, PdfPreambleRenderer),
            (pattern, PdfPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]

    def _make_postamble_piece_list(self, pattern):
        return [
            (pattern, AboutDesignerRenderer),
        ]


#
# Graded
#


class GradedCowlPatternRendererWebFull(PatternRendererBase):

    def _make_instruction_piece_list(self, pattern):
        pieces = pattern.pieces.all_pieces
        piece_list = PieceList(pieces)
        return [
            (piece_list, CowlPieceRenderer),
            (pattern, CowlFinishingRenderer),
        ]

    def _make_preamble_piece_list(self, pattern):
        return [
            # (pattern, WebPreambleRenderer),
            # (pattern, WebPersonalNotesRenderer),
            # (pattern, DesignerNotesRenderer),
            # (pattern, StitchesSectionRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            # (pattern, StitchChartsRenderer),
            # (pattern, CowlSchematicRendererWeb),
        ]

    def _make_postamble_piece_list(self, pattern):
        return [
            # (pattern, AboutDesignerRenderer),
        ]
