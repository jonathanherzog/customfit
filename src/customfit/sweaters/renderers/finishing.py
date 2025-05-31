import copy
import logging
import os.path

import django.template
import django.utils
from django.template import Template

from customfit.patterns.renderers import (
    Element,
    FinishingSubSection,
    InstructionSection,
    render_template,
)

from .base import SWEATER_PIECE_TEMPLATES

logger = logging.getLogger(__name__)


FINISHING = os.path.join(SWEATER_PIECE_TEMPLATES, "finishing")


# Yes, this is to be formatted as a piece, not a mock-piece
class FinishingRenderer(InstructionSection):

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

        additional_context["pspec"] = self.exemplar.get_spec_source()

        # sew together body pieces
        subsection.add_template_file(FINISHING, "start", additional_context)

        # Add sleeves to body pieces, if applicable.
        # If not, trim the armholes.
        if self.exemplar.has_sleeves():
            subsection.add_template_file(
                FINISHING, "second_chunk_sleeved", additional_context
            )
        else:
            subsection.add_template_file(
                FINISHING, "second_chunk_vest", additional_context
            )

            spec_source = self.exemplar.get_spec_source()

            armhole_template = spec_source.get_trim_armhole_template()
            subsection.add_template_object(armhole_template, additional_context)

        # Necklines: in v-neck cardigans, the button-band is the neckline too,
        # and so their necklines get pushed off to the button-band instructions.
        if not self.exemplar.is_veeneck_cardigan():
            is_veeneck = self.exemplar.vee_neck()
            neckline_context = {"veeneck_point_instructions": is_veeneck}
            neckline_context.update(additional_context)
            spec_source = self.exemplar.get_spec_source()
            neckline_template = spec_source.get_trim_neckline_template()
            subsection.add_template_object(neckline_template, neckline_context)

        # If the piece has button-band, get those instructions. There are
        # four cases: i-cord and not i-cord, vee-neck or not vee-neck.
        # However, it turned out to be easier to have one template for
        # both vee-neck icord and non-vee-neck i-cord
        if self.exemplar.has_button_band():

            buttonband = self.exemplar.get_buttonband()
            bb_context = {"button_band": buttonband}
            # Buttonband will be a single buttonband for individual patterns, piecelist for graded. So...
            try:
                bb_exemplar = buttonband.get_first()
            except AttributeError:
                bb_exemplar = buttonband

            bb_context["num_buttonholes"] = bb_exemplar.num_buttonholes
            bb_context["evenly_spaced_buttonholes"] = (
                bb_exemplar.evenly_spaced_buttonholes
            )
            bb_context.update(additional_context)
            spec_source = self.exemplar.get_spec_source()

            if self.exemplar.vee_neck():
                bb_template = spec_source.get_button_band_veeneck_template()
            else:
                bb_template = spec_source.get_button_band_template()

            subsection.add_template_object(bb_template, bb_context)

        # Wrap up with final instructions.
        end_context = copy.copy(additional_context)
        spec_source = self.exemplar.get_spec_source()
        finishes = [
            spec_source.hip_edging_stitch,
            spec_source.sleeve_edging_stitch,
            spec_source.neck_edging_stitch,
            spec_source.armhole_edging_stitch,
            spec_source.button_band_edging_stitch,
        ]

        extra_end_instructions = ""
        for stitch in finishes:
            if stitch is not None:
                if stitch.extra_finishing_instructions:
                    extra_end_instructions += stitch.extra_finishing_instructions

        if spec_source.get_extra_finishing_template():
            template = Template(spec_source.get_extra_finishing_template().content)
            html = render_template(template, end_context)
            extra_end_instructions += html

        end_context["extra_end_instructions"] = django.utils.safestring.mark_safe(
            extra_end_instructions
        )
        subsection.add_template_file(FINISHING, "end", end_context)

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
