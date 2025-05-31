# Le sigh. A special-snowflake test suite for a special-snowflake
# model. The Turks and Caicos neck should only be used in the Turks
# and Caicos design: pullover, with neckline starting 0.5 in above the
# armhole start. Test to make sure it works.
import re
from unittest import skip

from django.test import TestCase

from ..factories import SweaterPatternFactory, SweaterPatternSpecFactory
from ..helpers import sweater_design_choices as SDC
from ..renderers import SweaterfrontRenderer


@skip
class TurksAndCaicosPatterntextTest(TestCase):

    measurement_re = re.compile(
        "(\d+[\\u00BC\\u00BD\\u00BE]?|[\\u00BC\\u00BD\\u00BE])&quot;/\d+(\.5)? cm"
    )

    def normalize_html(self, html):
        # To make the tests below sane, we normalize the form of the HTML
        # First, remove all line breaks and carriage returns
        html = html.replace("\n", "").replace("\r", "")
        # Then, we replace tabs with spaces
        html = html.replace("\t", " ")
        # Then, we collapse down all multi-space sequences into single spaces
        html = re.sub(r" +", " ", html)
        # Then, we remove all spaces just before or after tags
        html = re.sub(r" <", "<", html)
        html = re.sub(r"> ", ">", html)
        return html

    def render_sweater_front(self, pspec):
        from ..models import SweaterFront

        assert pspec.garment_type == SDC.PULLOVER_SLEEVED
        p = SweaterPatternFactory.from_pspec(pspec)
        sf = p.get_front_piece()
        assert isinstance(sf, SweaterFront)
        sfr = SweaterfrontRenderer(sf)
        html = sfr.render()
        return self.normalize_html(html)

    def test_turks_and_caicos_patterntext(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_TURKS_AND_CAICOS,
            neckline_depth=0.5,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
