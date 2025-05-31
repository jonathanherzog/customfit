import logging
import os.path

from customfit.helpers.math_helpers import CompoundResult
from customfit.patterns.renderers.base import PieceList

from .base import BASE_TEMPLATE_DIR, Element, InstructionSection, SubSection
from .mock_pieces import (
    AboutDesignerRenderer,
    DesignerNotesRenderer,
    PdfPersonalNotesRenderer,
    StitchChartsRenderer,
    StitchesSectionRenderer,
    WebPersonalNotesRenderer,
)
from .pattern import PatternRendererBase

logger = logging.getLogger(__name__)


class TestPieceRenderer(InstructionSection):

    piece_name = "Test Piece"

    def _make_sole_element(self, additional_context):

        class TestSubsection(SubSection):
            def display_name(self):
                "Test subsection"

            def __eq__(self, other):
                return True

            def __lt__(self, other):
                return False

            def starts_during(self, other):
                """
                Return true iff self begins 'during' other (after other starts but before other ends).
                """
                return False

            def starts_during_all_grades(self, other):
                """
                Return true iff self begins 'during' other (after other starts but before other ends).
                """
                return False

            @property
            def start_rows(self):
                return CompoundResult([1])

            @property
            def end_rows(self):
                return CompoundResults([1])

            def interrupts_others(self):
                return False

            def warn_if_interrupted(self):
                return False

        subsection = TestSubsection()
        template_dir = os.path.join(BASE_TEMPLATE_DIR, "mock_pieces")
        subsection.add_template_file(template_dir, "test_piece", additional_context)

        sole_element = Element("Instructions", subsection)
        return sole_element

    def _make_elements(self, additional_context):

        return [self._make_sole_element(additional_context)]

    def _get_additional_elements_from_design(self, design):
        return []

    def _get_start_rows_from_additonal_element(self, additional_element):
        pass

    def _make_subsections_for_additonal_element(
        self,
        title,
        start_row,
        end_row,
        interrupts_others,
        warn_if_interrupted,
        additional_context,
    ):
        pass

    def get_piece_final_rows(self, additional_context):
        element = self._make_sole_element(additional_context)
        return element.end_rows()


class _BaseRenderer(PatternRendererBase):

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
        ]

    def _make_postamble_piece_list(self, pattern):
        return [
            (pattern, AboutDesignerRenderer),
        ]


class _IndividualBase(_BaseRenderer):

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.test_piece, TestPieceRenderer),
        ]


class _GradedBase(_BaseRenderer):

    def _make_instruction_piece_list(self, pattern):
        pieces = pattern.pieces.all_pieces
        piece_list = PieceList(pieces)
        return [
            (piece_list, TestPieceRenderer),
        ]


class _WebBaseMixin(object):

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, WebPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]


class _PdfBaseMixin(object):

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, PdfPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]


class _PdfBaseMixinAbridged(_PdfBaseMixin):
    pass


class _PdfBaseMixinFull(_PdfBaseMixin):
    def _make_preamble_piece_list(self, pattern):
        l = super()._make_preamble_piece_list(pattern)
        # Do this just to ensure that the full PDF has more than the abridged PDF, for testing
        # see customfit.patterns.tests.TestPatterntextPDFView.test_get_both_pdf
        l *= 3
        return l


# individual


class TestPatternRendererWebFull(_IndividualBase, _WebBaseMixin):

    pass


class TestPatternRendererPdfFull(_IndividualBase, _PdfBaseMixinFull):

    pass


class TestPatternRendererPdfAbridged(_IndividualBase, _PdfBaseMixinAbridged):

    pass


# graded


class GradedTestPatternRendererWebFull(_GradedBase, _WebBaseMixin):
    pass


class GradedTestPatternRendererPdfFull(_GradedBase, _PdfBaseMixinFull):
    pass


class GradedTestPatternRendererPdfAbridged(_GradedBase, _PdfBaseMixinAbridged):
    pass
