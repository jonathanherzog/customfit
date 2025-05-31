import logging

from customfit.patterns.renderers import (
    AboutDesignerRenderer,
    DesignerNotesRenderer,
    PatternRendererBase,
    PdfPersonalNotesRenderer,
    PieceList,
    StitchChartsRenderer,
    StitchesSectionRenderer,
    WebPersonalNotesRenderer,
)

from .body_pieces import (
    CardiganSleevedRenderer,
    CardiganVestRenderer,
    SweaterbackRenderer,
    SweaterfrontRenderer,
    VestbackRenderer,
    VestfrontRenderer,
)
from .finishing import FinishingRenderer
from .mock_pieces import (
    BustDartRenderer,
    GradedPreambleRenderer,
    PatternNotesRenderer,
    PdfPreambleRenderer,
    SchematicRendererPrint,
    SchematicRendererWeb,
    SeamlessRenderer,
    WebPreambleRenderer,
)
from .sleeve import SleeveRenderer

logger = logging.getLogger(__name__)


# And now a whole bunch of PatternRendererBase subclasses. Each one selects
# a seperate set of sections to include. General rules of thumb:
#
#  * The Abridged child (SweaterPatternRendererPdfAbridged) contains just those
#    sections that we expect most kntters to need on a day-to-day basis
#    and/or those that really should be part of every pattern (About Designer,
#    stitch charts, etc).
#
#  * The 'Full' classes (SweaterPatternRendererWebFull, SweaterPatternRendererPdfFull) hold
#    everything that even a beginner knitter might need (Pattern notes).
#
#  * PDF versions and HTML versions need slightly different renderers in some
#    parts (WebPreambleRenderer vs  PdfPreambleRenderer, specifically).
#
#  * There is no need for an Abridged Web version.
#
# Thus, we have a single Abridged version for PDF, and two Full versions:
# one for HTML and for PDF. They are very very similar, though, so we define
# a PatternRendererFullBase superclass to hold their common code.


class SweaterPatternRendererFullBase(PatternRendererBase):

    def _make_postamble_piece_list(self, pattern):
        return [
            (pattern, SeamlessRenderer),
            (pattern, BustDartRenderer),
            (pattern, AboutDesignerRenderer),
        ]


class SweaterPatternRendererPfdBase(PatternRendererBase):

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.sweater_back, SweaterbackRenderer),
            (pattern.pieces.vest_back, VestbackRenderer),
            (pattern.pieces.sweater_front, SweaterfrontRenderer),
            (pattern.pieces.vest_front, VestfrontRenderer),
            (pattern.pieces.cardigan_vest, CardiganVestRenderer),
            (pattern.pieces.cardigan_sleeved, CardiganSleevedRenderer),
            (pattern.pieces.sleeve, SleeveRenderer),
            (pattern, FinishingRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
            (pattern, SchematicRendererPrint),
        ]


class SweaterPatternRendererWebFull(SweaterPatternRendererFullBase):

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.sweater_back, SweaterbackRenderer),
            (pattern.pieces.vest_back, VestbackRenderer),
            (pattern.pieces.sweater_front, SweaterfrontRenderer),
            (pattern.pieces.vest_front, VestfrontRenderer),
            (pattern.pieces.cardigan_vest, CardiganVestRenderer),
            (pattern.pieces.cardigan_sleeved, CardiganSleevedRenderer),
            (pattern.pieces.sleeve, SleeveRenderer),
            (pattern, FinishingRenderer),
        ]

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, WebPreambleRenderer),
            (pattern, WebPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, PatternNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
            (pattern, SchematicRendererWeb),
        ]


class SweaterPatternRendererPdfFull(
    SweaterPatternRendererFullBase, SweaterPatternRendererPfdBase
):

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, PdfPreambleRenderer),
            (pattern, PdfPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, PatternNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]


class SweaterPatternRendererPdfAbridged(SweaterPatternRendererPfdBase):

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


class SweaterPatternCachePrefillRenderer(PatternRendererBase):
    # A 'mock' renderer that will compute all the section texts for caching

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, WebPreambleRenderer),
            (pattern, WebPersonalNotesRenderer),
            (pattern, PdfPreambleRenderer),
            (pattern, PdfPersonalNotesRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, PatternNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]

    def _make_instruction_piece_list(self, pattern):
        return [
            (pattern.pieces.sweater_back, SweaterbackRenderer),
            (pattern.pieces.vest_back, VestbackRenderer),
            (pattern.pieces.sweater_front, SweaterfrontRenderer),
            (pattern.pieces.vest_front, VestfrontRenderer),
            (pattern.pieces.cardigan_vest, CardiganVestRenderer),
            (pattern.pieces.cardigan_sleeved, CardiganSleevedRenderer),
            (pattern.pieces.sleeve, SleeveRenderer),
            (pattern, FinishingRenderer),
        ]

    def _make_postamble_piece_list(self, pattern):
        return [
            (pattern, SeamlessRenderer),
            (pattern, BustDartRenderer),
            (pattern, AboutDesignerRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
            (pattern, SchematicRendererPrint),
            (pattern, SchematicRendererWeb),
        ]


class GradedSweaterPatternRendererWebFull(PatternRendererBase):

    def _make_instruction_piece_list(self, pattern):
        maybe_piece_sections = [
            (pattern.pieces.sweater_backs, SweaterbackRenderer),
            (pattern.pieces.vest_backs, VestbackRenderer),
            (pattern.pieces.sweater_fronts, SweaterfrontRenderer),
            (pattern.pieces.vest_fronts, VestfrontRenderer),
            (pattern.pieces.cardigan_vests, CardiganVestRenderer),
            (pattern.pieces.cardigan_sleeveds, CardiganSleevedRenderer),
            (pattern.pieces.sleeves, SleeveRenderer),
        ]
        real_piece_sections = [
            (PieceList(pieces), renderer)
            for (pieces, renderer) in maybe_piece_sections
            if pieces
        ]
        return_me = real_piece_sections + [(PieceList([pattern]), FinishingRenderer)]
        return return_me

    def _make_preamble_piece_list(self, pattern):
        return [
            (pattern, GradedPreambleRenderer),
            (pattern, DesignerNotesRenderer),
            (pattern, StitchesSectionRenderer),
        ]

    def _make_chart_piece_list(self, pattern):
        return [
            (pattern, StitchChartsRenderer),
        ]

    def _make_postamble_piece_list(self, pattern):
        return []
