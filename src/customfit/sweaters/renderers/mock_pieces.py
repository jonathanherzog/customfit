import logging
import os.path

import django.utils

from customfit.patterns.renderers import (
    InformationSection,
    PreambleRendererBase,
    SchematicRendererBase,
)

from ..helpers import sweater_design_choices as DC
from .base import SWEATER_PIECE_TEMPLATES

logger = logging.getLogger(__name__)


MOCK_PIECES = os.path.join(SWEATER_PIECE_TEMPLATES, "mock_pieces")


class BustDartRenderer(InformationSection):

    piece_name = "Horizontal Bust Darts"

    def __bool__(self):
        """
        Returns True if the bust-dart section is appropriate for the pattern
        (e.g., the design is a hourglass) and we have the information we need
        to render it (e.g., the body has the inter-nipple distance filled in).
        This is a magic method that gets called in truth-testing.
        This will simplify higher-level code by allowing:

        bdr = BustDartRenderer(...)
        ...
        if bdr:
            bdr.render()

        Note that the default for a Python object is to evaluate to True,
        so this method need only be defined for renderers that might
        be empty (like this one).
        """
        return bool(self.piece.bust_dart_params())

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}
        self.add_template_file(MOCK_PIECES, "horizontal_bust_darts", additional_context)


class SweaterPreambleRendererBase(PreambleRendererBase):

    template_dir = MOCK_PIECES

    # Note: shadows superclass definition
    def _make_notion_text(self):
        """
        Figure out what to include under 'Notions' entry.
        """
        notions_text = ""
        spec_source = self.piece.get_spec_source()

        if self.piece.has_button_holes():
            num_buttons = spec_source.number_of_buttons
            if num_buttons == 1:
                notions_text += (
                    "Stitch markers, stitch holder, darning needle, "
                    "1 button, sewing thread, sewing needle"
                )
            else:
                notions_text += (
                    "Stitch markers, stitch holder, darning needle, "
                    "%s buttons, sewing thread, sewing needle" % num_buttons
                )
        else:
            notions_text += "Stitch markers, stitch holder, darning needle"

        if spec_source.notions:
            notions_text += ", "
            notions_text += spec_source.notions

        for stitch in spec_source.stitches_used():
            if stitch.extra_notions_text:
                notions_text += ", "
                notions_text += stitch.extra_notions_text

        return notions_text

    def _make_design_choices_text(self):
        spec_source = self.piece.get_spec_source()
        if spec_source.design_origin:
            origin = spec_source.design_origin
            # Get three pieces of text: the fit, the origin, and
            # the design name. Fit is a little tricky because of the a/an
            # convention of English
            if spec_source.garment_fit == DC.FIT_HOURGLASS_AVERAGE:
                fit_text = "a (women's) average-fit"
            elif spec_source.garment_fit == DC.FIT_HOURGLASS_RELAXED:
                fit_text = "a (women's) relaxed-fit"
            elif spec_source.garment_fit == DC.FIT_HOURGLASS_OVERSIZED:
                fit_text = "a (women's) oversized-fit"
            elif spec_source.garment_fit == DC.FIT_HOURGLASS_TIGHT:
                fit_text = "a (women's) close-fit"

            elif spec_source.garment_fit == DC.FIT_WOMENS_AVERAGE:
                fit_text = "a (women's) average-fit"
            elif spec_source.garment_fit == DC.FIT_WOMENS_RELAXED:
                fit_text = "a (women's) relaxed-fit"
            elif spec_source.garment_fit == DC.FIT_WOMENS_OVERSIZED:
                fit_text = "a (women's) oversized-fit"
            elif spec_source.garment_fit == DC.FIT_WOMENS_TIGHT:
                fit_text = "a (women's) close-fit"

            elif spec_source.garment_fit == DC.FIT_MENS_AVERAGE:
                fit_text = "a (men's) average-fit"
            elif spec_source.garment_fit == DC.FIT_MENS_RELAXED:
                fit_text = "a (men's) relaxed-fit"
            elif spec_source.garment_fit == DC.FIT_MENS_OVERSIZED:
                fit_text = "a (men's) oversized-fit"
            elif spec_source.garment_fit == DC.FIT_MENS_TIGHT:
                fit_text = "a (men's) close-fit"

            elif spec_source.garment_fit == DC.FIT_CHILDS_AVERAGE:
                fit_text = "a (childs's) average-fit"
            elif spec_source.garment_fit == DC.FIT_CHILDS_RELAXED:
                fit_text = "a (childs's) relaxed-fit"
            elif spec_source.garment_fit == DC.FIT_CHILDS_OVERSIZED:
                fit_text = "a (childs's) oversized-fit"
            else:
                assert spec_source.garment_fit == DC.FIT_CHILDS_TIGHT
                fit_text = "a (childs's) close-fit"

            if origin.is_basic:
                designer_text = "classic design"
            else:
                designer_text = "design"

            template = (
                "This pattern is %s customized version of " "the %s &quot;%s&quot;"
            )

            patterntext = template % (fit_text, designer_text, origin.name)

            designer = origin.designer
            if designer is not None:
                patterntext += " by %s" % designer.full_name
            patterntext += "."
            safe_patterntext = django.utils.safestring.mark_safe(patterntext)

            return safe_patterntext

        else:
            return None

    def _get_context(self, additional_context=None):

        from ..helpers.magic_constants import DROP_SHOULDER_ARMHOLE_DEPTH_INCHES

        context = super(SweaterPreambleRendererBase, self)._get_context(
            additional_context
        )

        spec_source = self.piece.get_spec_source()
        if spec_source.is_drop_shoulder:
            addl_length = DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[
                spec_source.drop_shoulder_additional_armhole_depth
            ]
            context["drop_shoulder_additional_length"] = addl_length

        return context


class PdfPreambleRenderer(SweaterPreambleRendererBase):
    template_name = "design_choices_pdf"


class WebPreambleRenderer(SweaterPreambleRendererBase):
    template_name = "design_choices_web"


class GradedPreambleRenderer(SweaterPreambleRendererBase):
    template_name = "design_choices_graded"


class SeamlessRenderer(InformationSection):

    piece_name = "Knitting Your Sweater Mostly Seamlessly"

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        self.add_template_file(MOCK_PIECES, "seamless", additional_context)


class PatternNotesRenderer(InformationSection):

    piece_name = "Pattern Notes"

    def _gather_text(self, additional_context=None):
        if additional_context is None:
            additional_context = {}

        self.add_template_file(MOCK_PIECES, "pattern_notes", additional_context)


class SweaterSchematicRendererBase(SchematicRendererBase):

    def _get_template_dir(self):
        return MOCK_PIECES


class SchematicRendererWeb(SweaterSchematicRendererBase):

    def _get_template_name(self):
        return "schematic_measurements_web"


class SchematicRendererPrint(SweaterSchematicRendererBase):

    def _get_template_name(self):
        return "schematic_measurements_print"
