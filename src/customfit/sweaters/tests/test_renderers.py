# Oy, these renderers I made. Horrible, unextensible, and untestable.
# Let's test what we can while we figure out how to re-factor them into
# something better.
import os.path
import re

from django.test import TestCase

from customfit.bodies.factories import BodyFactory, get_csv_body
from customfit.helpers.math_helpers import CM_PER_INCHES
from customfit.patterns.renderers import PieceList
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory

from ..factories import (
    AdditionalBackElementFactory,
    AdditionalFrontElementFactory,
    AdditionalFullTorsoElementFactory,
    AdditionalSleeveElementFactory,
    GradedSweaterPatternFactory,
    GradedSweaterPatternSpecFactory,
    RedoneSweaterPatternFactory,
    SweaterDesignFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    VestPatternSpecFactory,
    create_cardigan_sleeved,
    create_sweater_back,
    make_cardigan_sleeved_from_pspec,
    make_cardigan_vest_from_pspec,
)
from ..helpers import sweater_design_choices as SDC
from ..models import (
    AdditionalBackElement,
    AdditionalFrontElement,
    AdditionalFullTorsoElement,
    AdditionalSleeveElement,
)
from ..renderers import (
    BustDartRenderer,
    CardiganSleevedRenderer,
    CardiganVestRenderer,
    FinishingRenderer,
    PatternNotesRenderer,
    SchematicRendererWeb,
    SeamlessRenderer,
    SleeveRenderer,
    SweaterbackRenderer,
    SweaterfrontRenderer,
    WebPreambleRenderer,
)


# Base class with useful methods
class RendererTestCase(TestCase):

    measurement_re = re.compile(
        "(\d+[\\u00BC\\u00BD\\u00BE]?|[\\u00BC\\u00BD\\u00BE])&quot;/\d+(\.5)? cm"
    )

    def normalize_html(self, html):
        # Remove non-semantic whitespace from HTML so it doesn't cause
        # regexp match errors.
        html = re.sub(r"\s+", " ", html)
        html = re.sub(r">\s+<", "><", html)
        html = re.sub(r"\s+<", "<", html)
        html = re.sub(r">\s+", ">", html)
        return html

    def get_goal_html_from_file(self, filename):
        currpath = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(currpath, "patterntext_fragments", filename)
        with open(path, "r") as f:
            return f.read()


class PreambleRendererTest(RendererTestCase):

    yardage_re = re.compile(
        "<li><strong>Materials:</strong>yarn_maker yarn_name \d+g, \d+ hanks, approximately \d+ yd/\d+ m</li>"
    )
    no_yardage_re = re.compile("Want a better estimate?")

    def render_preamble(self, pspec):
        p = SweaterPatternFactory.from_pspec(pspec)
        wpr = WebPreambleRenderer(p)
        html = wpr.render()
        return self.normalize_html(html)

    def test_precise_yardage_display(self):
        swatch = SwatchFactory(
            yarn_name="yarn_name",
            yarn_maker="yarn_maker",
            length_per_hank=220,
            weight_per_hank=100,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
            full_swatch_weight=19,
        )
        pspec = SweaterPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        html = self.normalize_html(html)
        match_obj = self.yardage_re.search(html)
        self.assertIsNotNone(match_obj)
        match_obj = self.no_yardage_re.search(html)
        self.assertIsNone(match_obj)

    def test_imprecise_yardage_display(self):
        swatch = SwatchFactory(
            yarn_name="yarn_name",
            yarn_maker="yarn_maker",
            length_per_hank=None,
            weight_per_hank=100,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
            full_swatch_weight=19,
        )
        pspec = SweaterPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        html = self.normalize_html(html)
        match_obj = self.yardage_re.search(html)
        self.assertIsNone(match_obj)
        match_obj = self.no_yardage_re.search(html)
        self.assertIsNotNone(match_obj)

    def test_zero_buttons(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)

        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_one_button(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=1,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)

        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle, 1 button, sewing thread, sewing needle</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_multiple_buttons(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=5,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)

        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle, 5 buttons, sewing thread, sewing needle</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_no_buttons(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)

        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_extra_notions(self):
        notion_text = "a little of this, a little of that"
        design = SweaterDesignFactory(notions=notion_text)
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            design_origin=design,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle, a little of this, a little of that</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_stitch_notions(self):
        notion_text = "a little more of this, a little more of that"
        stitch = StitchFactory(extra_notions_text=notion_text)
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            sleeve_allover_stitch=stitch,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = "<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle, a little more of this, a little more of that</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_all_notions(self):
        stitch1 = StitchFactory(
            extra_notions_text="stitch1 extra notions, more stitch1 extra notions, foo"
        )
        stitch2 = StitchFactory(
            extra_notions_text="stitch2 extra notions, more stitch2 extra notions, foo"
        )
        design = SweaterDesignFactory(
            notions="design extra notions, more design extra notions, foo"
        )
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            sleeve_allover_stitch=stitch1,
            front_allover_stitch=stitch2,
            design_origin=design,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = """<li><strong>Notions:</strong>Stitch markers, stitch holder, darning needle, design extra notions,
                       more design extra notions, foo, stitch2 extra notions, more stitch2 extra notions, foo,
                       stitch1 extra notions, more stitch1 extra notions, foo</li>"""
        self.assertInHTML(goal_html, patterntext)

    def test_gauge_display(self):

        ten_cm = 10 / CM_PER_INCHES
        swatch = SwatchFactory(
            rows_length=ten_cm,
            rows_number=20,
            stitches_length=ten_cm,
            stitches_number=25,
        )
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            swatch=swatch,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_text = "<li><strong>Gauge:</strong>25.5 sts &amp; 20.25 rows = 4&quot; / 25 sts &amp; 20 rows = 10cm in"
        self.assertIn(goal_text, patterntext)

    def test_no_needle_text(self):
        swatch = SwatchFactory(needle_size=None)
        pspec = SweaterPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        self.assertIn("<li><strong>Needles:</strong></li>", html)

    def test_redo(self):

        # Sanity tests
        pspec = SweaterPatternSpecFactory()
        html = self.render_preamble(pspec)
        self.assertIn("<li>Hourglass average fit</li>", html)
        self.assertIn("<li>Sleeves: Full-length tapered sleeve</li>", html)
        self.assertIn("<li>Length: Average</li>", html)
        self.assertIn("<li>Neck depth: 6&quot;/15 cm below shoulders</li>", html)

        p = RedoneSweaterPatternFactory()
        wpr = WebPreambleRenderer(p)
        html = wpr.render()
        html = self.normalize_html(html)

        orig_pspec = p.get_spec_source().get_original_patternspec()

        # body
        self.assertIn(p.body.name, html)
        self.assertNotIn(orig_pspec.body.name, html)

        # swatch
        self.assertIn(p.swatch.name, html)
        self.assertNotIn(orig_pspec.swatch.name, html)

        # torso_length
        self.assertIn(p.body.name, html)
        self.assertNotIn(orig_pspec.body.name, html)

        # fit
        self.assertIn("<li>Hourglass relaxed fit</li>", html)
        self.assertNotIn("<li>Hourglass average fit</li>", html)

        # neckline depth & orientation
        self.assertIn(
            "<li>Neck depth: 1&quot;/2.5 cm above armhole-shaping start</li>", html
        )
        self.assertNotIn("Below shoulders", html)
        self.assertNotIn("below shoulders", html)

        # sleeve length
        self.assertIn("<li>Sleeves: Three-quarter length sleeve</li>", html)
        self.assertNotIn("Full-length sleeve", html)
        self.assertNotIn("full-length sleeve", html)

        # torso length
        self.assertIn("<li>Length: Long</li>", html)
        self.assertNotIn("<li>Length: Average</li>", html)

    def test_addl_armhole_depth(self):

        # No addl armhole depth for set-in sleeve
        pspec = SweaterPatternSpecFactory(construction=SDC.CONSTRUCTION_SET_IN_SLEEVE)
        pspec.full_clean()
        self.assertFalse(pspec.is_drop_shoulder)
        html = self.render_preamble(pspec)
        self.assertNotIn("Drop-shoulder armhole: ", html)

        # No addl armhole depth for set-in sleeve
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            # currently 1.5 inches
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        self.assertTrue(pspec.is_drop_shoulder)
        html = self.render_preamble(pspec)
        self.assertIn(
            "<li>Drop-shoulder armhole: average length (additional 1\u00BD&quot;/4 cm)</li>",
            html,
        )


class PulloverFrontTests(RendererTestCase):

    maxDiff = None

    def render_sweater_front(self, pspec):
        assert pspec.garment_type == SDC.PULLOVER_SLEEVED
        p = SweaterPatternFactory.from_pspec(pspec)
        sf = p.get_front_piece()
        sfr = SweaterfrontRenderer(sf)
        html = sfr.render()
        return self.normalize_html(html)

    def test_armhole_starts_neckline_above_armhole(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        # armhole shaping should only appear once:
        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 1)

        # shaping should start on RS row, meaning that shaping should end on the
        # WS row. Also, row-counts should be even from the beginning, and
        # should provide count since last increase.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning, \d+ rows from \(and including\) last increase row.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

    def test_armhole_starts_neckline_below_armhole(self):
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        patterntext = self.normalize_html(patterntext)

        # armhole shaping should appear twice:
        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 2)

        # one set of instructions should start on RS row, meaning that
        # shaping should end on the WS row. Also, row-counts should be even
        # from the beginning, and should provide count since neckline shaping.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning and \d+ rows from neckline.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

        # Other set of instructions should start on WS row, meaning that
        # shaping should end on the RS row. Also, row-counts should be odd
        # from the beginning, and should provide count since neckline shaping.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a RS row: (?P<row_count>\d+) rows from beginning and \d+ rows from neckline.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 1)

    def test_armhole_and_neck_start_together(self):
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=0,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)

        # armhole shaping should only appear once:
        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 1)

        # shaping should start on RS row, meaning that shaping should end on the
        # WS row. Also, row-counts should be even from the beginning, and
        # should provide count since last increase.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning, \d+ rows from \(and including\) last increase row.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

    def test_veeneck_patterntext(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        goal_patterntext = self.get_goal_html_from_file("pullover_front_veeneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_scoopneck_patterntext(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_SCOOP,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        goal_patterntext = self.get_goal_html_from_file("pullover_front_scoopneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_boatneck_patterntext(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_BOAT,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        goal_patterntext = self.get_goal_html_from_file("pullover_front_boatneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_crewneck_patterntext(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec1.clean()
        patterntext = self.render_sweater_front(pspec1)
        goal_patterntext = self.get_goal_html_from_file("pullover_front_crewneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_additional_front_element_below_neckline(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFrontElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_front(pspec)
        # Note: patterntext should be the same as in PulloverFrontTests.test_additional_back_element_below_neckline
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_front_element_above_neckline(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_BEFORE_NECKLINE,
            start_location_value=-1,
            height_type=AdditionalFrontElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_front(pspec)
        # Note that this patterntext should be the same as test_additional_full_torso_element_above_neckline, below
        goal_html1 = """
        <p>
        When piece measures 19&quot;/48.5 cm (133 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_full_torso_element_below_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_front(pspec)
        # Note: patterntext should be the same as in PulloverBackTests.test_additional_full_torso_element_below_neckline
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_full_torso_element_above_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=-1,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_front(pspec)
        # Note: patterntext should be the same as in PulloverBackTests.test_additional_full_torso_element_above_neckline
        # but here, it really is above the neckline. Hence, there will be two instances in the patterntext
        # instead of one.
        goal_html1 = """
        <p>
        When piece measures 19&quot;/48.5 cm (133 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_front_element_below_neckline_no_end(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFrontElement.HEIGHT_NO_END,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_front(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 151 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_element_error(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        with self.assertRaises(AdditionalFullTorsoElement.ElementBelowStartException):
            self.render_sweater_front(pspec)

    def test_additional_element_error2(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        with self.assertRaises(SweaterfrontRenderer.SectionStartsAfterPieceEnds):
            self.render_sweater_front(pspec)

    def test_no_overlap_when_no_bust_increases(self):
        pspec = SweaterPatternSpecFactory(
            swatch__stitches_length=4,
            swatch__stitches_number=17,
            swatch__rows_length=3,
            swatch__rows_number=20,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=2.0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
        )

        p = SweaterPatternFactory.from_pspec(pspec)
        sf = p.get_front_piece()
        sf.num_bust_standard_increase_rows = 0
        sf.rows_between_bust_standard_increase_rows = None
        sf.num_bust_double_dart_increase_rows = 0
        sf.num_bust_triple_dart_rows = 0
        sf.bust_pre_double_dart_marker = None
        sf.bust_pre_standard_dart_marker = None
        sf.bust_pre_triple_dart_marker = None

        sfr = SweaterfrontRenderer(sf)

        # Test the overlap behavior directly. Note-- this is heavily dependent on internal methods/implementation
        # of SweaterFrontRenderer
        elements = sfr._make_elements({})
        increases_element = [
            el for el in elements if el.display_name == "Bust increases"
        ][0]
        neckline_element = [el for el in elements if el.display_name == "Neckline"][0]

        self.assertFalse(increases_element.warn_of_overlap_with(neckline_element))

        # Test that overlap doesn't show up in the HTML. This is heavily dependent on the
        # template language for overlaps
        html = sfr.render()
        self.assertNotIn("Bust increases will overlap Neckline.", html)

    def test_no_overlap_when_no_waist_decreases(self):
        pspec = SweaterPatternSpecFactory(
            swatch__stitches_length=4,
            swatch__stitches_number=17,
            swatch__rows_length=3,
            swatch__rows_number=20,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=5.0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
        )

        p = SweaterPatternFactory.from_pspec(pspec)
        sf = p.get_front_piece()
        sf.num_waist_standard_decrease_rows = 0
        sf.rows_between_waist_standard_decrease_rows = None
        sf.num_waist_double_dart_rows = 0
        sf.num_waist_triple_dart_rows = 0
        sf.pre_marker = None
        sf.waist_double_dart_marker = None
        sf.waist_triple_dart_marker = None
        sf.begin_decreases_height = None

        sfr = SweaterfrontRenderer(sf)

        # Test the overlap behavior directly. Note-- this is heavily dependent on internal methods/implementation
        # of SweaterFrontRenderer
        elements = sfr._make_elements({})
        decreases_element = [
            el for el in elements if el.display_name == "Waist shaping"
        ][0]
        neckline_element = [el for el in elements if el.display_name == "Neckline"][0]

        self.assertFalse(decreases_element.warn_of_overlap_with(neckline_element))

        # Test that overlap doesn't show up in the HTML. This is heavily dependent on the
        # template language for overlaps
        html = sfr.render()
        self.assertNotIn("Waist shaping will overlap Neckline.", html)


class PulloverBackTests(RendererTestCase):

    maxDiff = None

    def render_sweater_back(self, pspec):
        assert pspec.garment_type in [SDC.PULLOVER_SLEEVED, SDC.PULLOVER_VEST]
        p = SweaterPatternFactory.from_pspec(pspec)
        sf = p.get_back_piece()
        sfr = SweaterbackRenderer(sf)
        html = sfr.render()
        return html

    def test_straight_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file("sweaterback_straight.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_aline_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file("sweaterback_aline.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_tapered_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file("sweaterback_tapered.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_bugfix_renderer(self):
        # Tickle a bug in the templates so we can fix it
        swatch = SwatchFactory(
            rows_number=4, rows_length=1, stitches_number=10, stitches_length=1
        )
        body = get_csv_body("Test 5")
        pspec = SweaterPatternSpecFactory(body=body, swatch=swatch)
        patterntext = self.render_sweater_back(pspec)
        waist_row_2_patterntext = """<p><em>Decrease Row Two (RS)</em>:
            Work to 2 stitches before second marker (color B), ssk, sm, work to fifth marker (color B), sm,
            k2tog, work to end. Two stitches decreased. Work one row even.</p>"""
        self.assertInHTML(waist_row_2_patterntext, patterntext)
        waist_row_3_patterntext = """<p><em>Decrease Row Three (RS)</em>:
            Work to 2 stitches before first marker (color C), ssk, sm, work to 2 stitches before third marker
            (color A), ssk, sm, work to fourth marker (color A), sm, k2tog,  work to sixth marker (color C),
            sm, k2tog, work to end. Four stitches decreased. Work 1 row even.</p>"""
        self.assertInHTML(waist_row_3_patterntext, patterntext)

    def test_render_single_darts(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=6,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=0,
            num_waist_triple_dart_rows=0,
            num_bust_standard_increase_rows=6,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=0,
            num_bust_triple_dart_rows=0,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_standard_darts.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_double_darts(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=6,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=4,
            num_waist_triple_dart_rows=0,
            num_bust_standard_increase_rows=6,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=4,
            num_bust_triple_dart_rows=0,
            pre_marker=20,
            waist_double_dart_marker=9,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_standard_and_double_darts.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_some_triple_darts(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=2,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=5,
            num_waist_triple_dart_rows=4,
            num_bust_standard_increase_rows=2,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=5,
            num_bust_triple_dart_rows=4,
            pre_marker=12,
            waist_double_dart_marker=9,
            waist_triple_dart_marker=5,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_standard_double_and_triple_darts.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_all_triple_darts(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=0,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=5,
            num_waist_triple_dart_rows=6,
            num_bust_standard_increase_rows=0,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=5,
            num_bust_triple_dart_rows=6,
            pre_marker=12,
            waist_double_dart_marker=9,
            waist_triple_dart_marker=5,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_double_and_triple_darts.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_one_triple_dart(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=0,
            rows_between_waist_standard_decrease_rows=3,
            num_waist_double_dart_rows=0,
            num_waist_triple_dart_rows=1,
            num_bust_standard_increase_rows=0,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=0,
            num_bust_triple_dart_rows=1,
            pre_marker=12,
            waist_double_dart_marker=9,
            waist_triple_dart_marker=5,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        print(patterntext)
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_one_triple_dart.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_duplicate_instruction_bug(self):
        sb = create_sweater_back(
            num_waist_standard_decrease_rows=0,
            rows_between_waist_standard_decrease_rows=None,
            num_waist_double_dart_rows=0,
            num_waist_triple_dart_rows=0,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        duplicated_text_instances = re.findall("52 rows from beginning", patterntext)
        self.assertEqual(len(duplicated_text_instances), 1)

    def test_double_and_triple_dart_bug(self):
        sb = create_sweater_back(
            cast_ons=112,
            num_waist_standard_decrease_rows=5,
            rows_between_waist_standard_decrease_rows=9,
            num_waist_double_dart_rows=0,
            num_waist_triple_dart_rows=0,
            num_bust_standard_increase_rows=0,
            rows_between_bust_standard_increase_rows=3,
            num_bust_double_dart_increase_rows=3,
            num_bust_triple_dart_rows=4,
        )
        sbr = SweaterbackRenderer(sb)
        patterntext = sbr.render()
        goal_html1 = """
          <p>
             <em>Increase Row Two (RS)</em>:
                Work to second marker (color B), m1R, sm, work to fifth marker (color B), sm, m1L, work to end.
                Two stitches increased.
                Work one row even.
          </p>"""
        self.assertInHTML(goal_html1, patterntext)

        goal_html2 = """
          <p>
            Work Increase Row One. Work one row even.
          </p>"""
        self.assertInHTML(goal_html2, patterntext)

        goal_html3 = """
          <p>
              Repeat the last four rows a total of
              3 times:
              7 total
              increase rows worked since waist.
          </p>
        """
        self.assertInHTML(goal_html3, patterntext)

    def test_additional_back_element_below_neckline(self):
        adl = AdditionalBackElementFactory(
            name="Stripe",
            start_location_type=AdditionalBackElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalBackElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        # Note: patterntext should be the same as in PulloverFrontTests.test_additional_back_element_below_neckline
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_back_element_above_neckline(self):
        adl = AdditionalBackElementFactory(
            name="Stripe",
            start_location_type=AdditionalBackElement.START_BEFORE_NECKLINE,
            start_location_value=-0.5,
            height_type=AdditionalBackElement.HEIGHT_IN_ROWS,
            height_value=2,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_html1 = """
        <p>
        When piece measures 23\u00BD&quot;/60 cm (165 rows from beginning) on RS row
        switch to secondary color. Continue as written for 2 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_full_torso_element_below_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        # Note: patterntext should be the same as in PulloverFrontTests.test_additional_full_torso_element_below_neckline
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_full_torso_element_above_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=-1,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        # Note that the full-torso section takes its heights from the *front*. Therefore,
        # the heights here will be different than that in test_additional_back_element_above_neckline.
        # And since it's lower, it's below the back neckline and there's only one instance of it in the
        # pattern
        goal_html1 = """
        <p>
        When piece measures 19&quot;/48.5 cm (133 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_back_element_below_neckline_no_end(self):
        adl = AdditionalBackElementFactory(
            name="Stripe",
            start_location_type=AdditionalBackElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalBackElement.HEIGHT_NO_END,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 151 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 98 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)

    def test_additional_additional_element_error(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        with self.assertRaises(AdditionalBackElement.ElementBelowStartException):
            patterntext = self.render_sweater_back(pspec)

    def test_additional_additional_element_error2(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        with self.assertRaises(SweaterbackRenderer.SectionStartsAfterPieceEnds):
            patterntext = self.render_sweater_back(pspec)

    def test_bugfix_renderer2(self):
        pspec = SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_SLEEVED)
        pspec.full_clean()
        p = SweaterPatternFactory.from_pspec(pspec)
        sb = p.get_back_piece()

        sb.num_waist_standard_decrease_rows = 5
        sb.rows_between_waist_standard_decrease_rows = 3
        sb.num_waist_double_dart_rows = 4
        sb.num_waist_triple_dart_rows = 0
        sb.save()
        sbr = SweaterbackRenderer(sb)
        # should not raise exception
        html = sbr.render()

    #############################################################################################
    #
    # Armhole combinations
    #
    #############################################################################################

    def test_setinsleeve_pullover_sleeved(self):
        # Make sure we cover all of the armhole template options
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            garment_type=SDC.PULLOVER_SLEEVED,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_setinsleeve_pullover_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_setinsleeve_pullover_vest(self):
        # Make sure we cover all of the armhole template options
        pspec = VestPatternSpecFactory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE, garment_type=SDC.PULLOVER_VEST
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_setinsleeve_pullover_vest.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_dropshoulder_pullover_sleeved(self):
        # Make sure we cover all of the armhole template options
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            garment_type=SDC.PULLOVER_SLEEVED,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_dropshoulder_pullover_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_dropshoulder_pullover_vest(self):
        # Make sure we cover all of the armhole template options
        pspec = VestPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            garment_type=SDC.PULLOVER_VEST,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "sweaterback_dropshoulder_pullover_vest.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    # Cardigan armhole are in  CardiganFrontTests

    #############################################################################################
    #
    # End armhole combinations
    #
    #############################################################################################


class CardiganFrontTests(RendererTestCase):

    maxDiff = None

    def make_cardigan_sleeved_from_pspec(self, pspec):
        assert pspec.garment_type == SDC.CARDIGAN_SLEEVED
        p = SweaterPatternFactory.from_pspec(pspec)
        cf = p.get_front_piece()
        return cf

    def render_cardigan_front(self, pspec):
        cf = self.make_cardigan_sleeved_from_pspec(pspec)
        cfr = CardiganSleevedRenderer(cf)
        html = cfr.render()
        return html

    def test_armhole_starts_neckline_above_armhole(self):

        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_cardigan_front(pspec1)
        patterntext = self.normalize_html(patterntext)

        # armhole shaping should only appear once:

        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 2)

        # One shaping should start on RS row, meaning that shaping should end on
        # the WS row. Also, row-counts should be even from the beginning, and
        # should provide count since last increase.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning, \d+ rows from \(and including\) last increase row.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

        # Other shaping should start on RS row, meaning that shaping should end
        # on the WS row. Also, row-counts should be even from the beginning,
        # and should provide count since last increase.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a RS row: (?P<row_count>\d+) rows from beginning, \d+ rows from \(and including\) last increase row.</p>"
        )

        # strip unneeded whitespace
        patterntext = self.normalize_html(patterntext)
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 1)

    def test_armhole_starts_neckline_below_armhole(self):
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_cardigan_front(pspec1)
        patterntext = self.normalize_html(patterntext)

        # armhole shaping should appear twice:
        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 2)

        # one set of instructions should start on RS row, meaning that
        # shaping should end on the WS row. Also, row-counts should be even
        # from the beginning, and should provide count since neckline shaping.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning and \d+ rows from neckline.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

        # Other set of instructions should start on WS row, meaning that
        # shaping should end on the RS row. Also, row-counts should be odd
        # from the beginning, and should provide count since neckline shaping.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a RS row: (?P<row_count>\d+) rows from beginning and \d+ rows from neckline.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 1)

    def test_armhole_starts_neckline_with_armhole(self):
        pspec1 = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec1.clean()
        patterntext = self.render_cardigan_front(pspec1)
        patterntext = self.normalize_html(patterntext)

        # armhole shaping should appear twice:
        armhole_shaping_start_matches = re.findall(
            "<strong>Shape Armhole:</strong>", patterntext
        )
        self.assertEqual(len(armhole_shaping_start_matches), 2)

        # one set of instructions should start on RS row, meaning that
        # shaping should end on the WS row. Also, row-counts should be even
        # from the beginning, and should provide count since last increase row.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a WS row: (?P<row_count>\d+) rows from beginning, \d+ rows from \(and including\) last increase row.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 0)

        # Other set of instructions should start on WS row, meaning that
        # shaping should end on the RS row. Also, row-counts should be odd
        # from the beginning, and should provide count since neckline shaping.
        goal_re = re.compile(
            "<p>Continue as established until piece measures "
            + self.measurement_re.pattern
            + ", ending with a RS row: (?P<row_count>\d+) rows from beginning and \d+ rows from neckline.</p><p><strong>Shape Armhole:</strong></p>"
        )
        match_obj = goal_re.search(patterntext)

        self.assertIsNotNone(match_obj)
        self.assertEqual(int(match_obj.group("row_count")) % 2, 1)

    def test_single_double_triple_dart(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
        )
        pspec.clean()

        cf = self.make_cardigan_sleeved_from_pspec(pspec)
        cf.num_bust_standard_increase_rows = 2
        cf.rows_between_bust_standard_increase_rows = 3

        cf.num_bust_double_dart_increase_rows = 3
        cf.num_bust_triple_dart_rows = 2

        cf.bust_pre_standard_dart_marker = 20
        cf.bust_pre_double_dart_marker = 13
        cf.bust_pre_triple_dart_marker = 6

        cfr = CardiganSleevedRenderer(cf)
        html = cfr.render()
        html = self.normalize_html(html)

        goal_re = re.compile(
            "<p>Repeat the following four rows \(Increase Rows One and Two\) 2 times:</p><p><em>Increase Row One \(RS\)</em>: K to third marker, m1R, sm, k to end. One stitch increased. Work one row even.</p><p><em>Increase Row Two \(RS\)</em>: K to second marker, m1R, sm, k to end. One stitch increased. Work one row even.</p><p>Then work the following two rows once.</p><p><em>Increase Row Three \(RS\)</em>: K to first marker, m1R, sm, k to last marker, m1R, sm, k to end. Two stitches increased. Work 1 row even.</p><p>Then, repeat Increase Rows Two and Three every RS row 1 additional time.</p><p>7 total increase rows worked since waist.</p>"
        )
        match_obj = goal_re.search(html)
        self.assertIsNotNone(match_obj)

    def test_straight_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_straight.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_aline_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_aline.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_tapered_silhouette(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_tapered.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_veeneck(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            neckline_style=SDC.NECK_VEE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_veeneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_boatneck(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            neckline_style=SDC.NECK_BOAT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_boatneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_scoopneck(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            neckline_style=SDC.NECK_SCOOP,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_scoopneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_crewneck(self):
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            neckline_style=SDC.NECK_CREW,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_patterntext = self.get_goal_html_from_file("cardigan_crewneck.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_single_darts(self):
        sb = create_cardigan_sleeved(
            num_waist_standard_decrease_rows=6,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=0,
            num_waist_triple_dart_rows=0,
            num_bust_standard_increase_rows=6,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=0,
            num_bust_triple_dart_rows=0,
        )
        sbr = CardiganSleevedRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file("cardigan_single_darts.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_double_darts(self):
        sb = create_cardigan_sleeved(
            num_waist_standard_decrease_rows=6,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=4,
            num_waist_triple_dart_rows=0,
            num_bust_standard_increase_rows=6,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=4,
            num_bust_triple_dart_rows=0,
            pre_marker=25,
            waist_double_dart_marker=10,
        )
        sbr = CardiganSleevedRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file("cardigan_double_darts.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_render_triple_darts(self):
        sb = create_cardigan_sleeved(
            num_waist_standard_decrease_rows=2,
            rows_between_waist_standard_decrease_rows=4,
            num_waist_double_dart_rows=5,
            num_waist_triple_dart_rows=4,
            num_bust_standard_increase_rows=2,
            rows_between_bust_standard_increase_rows=4,
            num_bust_double_dart_increase_rows=5,
            num_bust_triple_dart_rows=4,
            pre_marker=25,
            waist_double_dart_marker=10,
            waist_triple_dart_marker=5,
        )
        sbr = CardiganSleevedRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file("cardigan_triple_darts.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_additional_front_element_below_neckline(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFrontElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        # Note: patterntext should be the same as in PulloverFrontTests.test_additional_front_element_below_neckline
        # But there should be two-- one for each side
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 47 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_front_element_above_neckline(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_BEFORE_NECKLINE,
            start_location_value=-1,
            height_type=AdditionalFrontElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        # Note that this patterntext should be the same as test_additional_full_torso_element_above_neckline, below
        goal_html1 = """
        <p>
        When piece measures 19&quot;/48.5 cm (133 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 47 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_full_torso_element_below_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        # Note: patterntext should be the same as in PulloverBackTests.test_additional_full_torso_element_below_neckline
        # But there should be two-- one for each side
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 47 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_full_torso_element_above_neckline(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=-1,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        # Note: patterntext should be the same as in PulloverBackTests.test_additional_full_torso_element_above_neckline
        # But there should be two-- one for each side
        goal_html1 = """
        <p>
        When piece measures 19&quot;/48.5 cm (133 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=2)
        goal_html2 = """
             <p>Note: There were 47 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=2)

    def test_additional_front_element_below_neckline_no_end(self):
        adl = AdditionalFrontElementFactory(
            name="Stripe",
            start_location_type=AdditionalFrontElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalFrontElement.HEIGHT_NO_END,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        patterntext = self.render_cardigan_front(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 151 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 152 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)
        goal_html3 = """
             <p>Note: There were 47 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html3, patterntext, count=2)

    def test_additional_element_error(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_BEFORE_NECKLINE,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        with self.assertRaises(AdditionalFullTorsoElement.ElementBelowStartException):
            self.render_cardigan_front(pspec)

    def test_additional_element_error2(self):
        adl = AdditionalFullTorsoElementFactory(
            name="Stripe",
            start_location_type=AdditionalFullTorsoElement.START_AFTER_CASTON,
            start_location_value=40,
            height_type=AdditionalFullTorsoElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        with self.assertRaises(CardiganSleevedRenderer.SectionStartsAfterPieceEnds):
            self.render_cardigan_front(pspec)

    def test_no_overlap_when_no_bust_increases(self):
        pspec = SweaterPatternSpecFactory(
            swatch__stitches_length=4,
            swatch__stitches_number=17,
            swatch__rows_length=3,
            swatch__rows_number=20,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(),
            neckline_style=SDC.NECK_VEE,
            neckline_depth=2.0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            number_of_buttons=2,
        )
        cs = self.make_cardigan_sleeved_from_pspec(pspec)
        cs.num_bust_standard_increase_rows = 0
        cs.rows_between_bust_standard_increase_rows = None
        cs.num_bust_double_dart_increase_rows = 0
        cs.num_bust_triple_dart_rows = 0
        cs.bust_pre_double_dart_marker = None
        cs.bust_pre_standard_dart_marker = None
        cs.bust_pre_triple_dart_marker = None

        csr = CardiganSleevedRenderer(cs)

        # Test the overlap behavior directly. Note-- this is heavily dependent on internal methods/implementation
        # of CardiganSleevedRenderer
        increases_element = csr._make_increases_element({})
        neckline_element = csr._make_neckline_and_shoulder_elements(csr.side_one_dict)[
            2
        ]
        self.assertFalse(increases_element.warn_of_overlap_with(neckline_element))

        # Test that overlap doesn't show up in the HTML. This is heavily dependent on the
        # template language for overlaps
        html = csr.render()
        self.assertNotIn("Bust increases will overlap Neckline.", html)

    def test_no_overlap_when_no_waist_decreases(self):
        pspec = SweaterPatternSpecFactory(
            swatch__stitches_length=4,
            swatch__stitches_number=17,
            swatch__rows_length=3,
            swatch__rows_number=20,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(),
            neckline_style=SDC.NECK_VEE,
            neckline_depth=5.0,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            number_of_buttons=2,
        )
        cs = self.make_cardigan_sleeved_from_pspec(pspec)
        cs.num_waist_standard_decrease_rows = 0
        cs.rows_between_waist_standard_decrease_rows = None
        cs.num_waist_double_dart_rows = 0
        cs.num_waist_triple_dart_rows = 0
        cs.pre_marker = None
        cs.waist_double_dart_marker = None
        cs.waist_triple_dart_marker = None
        cs.begin_decreases_height = None

        csr = CardiganSleevedRenderer(cs)

        # Test the overlap behavior directly. Note-- this is heavily dependent on internal methods/implementation
        # of CardiganSleevedRenderer
        decreases_element = csr._make_decreases_element({})
        neckline_element = csr._make_neckline_and_shoulder_elements(csr.side_one_dict)[
            2
        ]
        self.assertFalse(decreases_element.warn_of_overlap_with(neckline_element))

        # Test that overlap doesn't show up in the HTML. This is heavily dependent on the
        # template language for overlaps
        html = csr.render()
        self.assertNotIn("Waist shaping will overlap Neckline.", html)

    #############################################################################################
    #
    # Armhole combinations
    #
    #############################################################################################

    def test_setinsleeve_cargigan_sleeved(self):
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=0,
            button_band_allowance=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        pspec.full_clean()
        sb = make_cardigan_sleeved_from_pspec(pspec)
        sbr = CardiganSleevedRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "cardigan_setinsleeve_cardigan_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_setinsleeve_cargigan_vest(self):
        pspec = VestPatternSpecFactory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_height=0,
            button_band_allowance=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        pspec.full_clean()
        sb = make_cardigan_vest_from_pspec(pspec)
        sbr = CardiganVestRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "cardigan_setinsleeve_cardigan_vest.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_dropshoulder_cargigan_sleeved(self):
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=0,
            button_band_allowance=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        sb = make_cardigan_sleeved_from_pspec(pspec)
        sbr = CardiganSleevedRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "cardigan_dropshoulder_cardigan_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_dropshoulder_cargigan_vest(self):
        pspec = VestPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_height=0,
            button_band_allowance=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        sb = make_cardigan_vest_from_pspec(pspec)
        sbr = CardiganVestRenderer(sb)
        patterntext = sbr.render()
        goal_patterntext = self.get_goal_html_from_file(
            "cardigan_dropshoulder_cardigan_vest.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    #
    # pullover armhole are in PulloverBackTests

    #############################################################################################
    #
    # End armhole combinations
    #
    #############################################################################################


class PatternNotesRendererTest(RendererTestCase):

    def test_hourglass_with_bust_darts(self):
        body = BodyFactory()
        pspec = SweaterPatternSpecFactory(body=body)
        p = SweaterPatternFactory.from_pspec(pspec)
        pnr = PatternNotesRenderer(p)
        html = self.normalize_html(pnr.render())
        goal_text = self.normalize_html(
            """The instructions in the main body
	        of this pattern are for a bottom-up, pieced sweater with vertical
	        darts for all shaping.
	        Instructions for working the sweater 
		    seamlessly, as well as adding horizontal bust darts, are given at
		    the end of the pattern."""
        )
        self.assertIn(goal_text, html)

    def test_hourglass_no_bust_darts(self):
        body = BodyFactory(inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(body=body)
        p = SweaterPatternFactory.from_pspec(pspec)
        pnr = PatternNotesRenderer(p)
        html = self.normalize_html(pnr.render())
        goal_text = self.normalize_html(
            """The instructions in the main body
	        of this pattern are for a bottom-up, pieced sweater with vertical
	        darts for all shaping.
	        Instructions for working the sweater seamlessly are given at
		    the end of the pattern."""
        )
        self.assertIn(goal_text, html)

    def test_straight(self):
        body = BodyFactory(inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            body=body,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
        )
        p = SweaterPatternFactory.from_pspec(pspec)
        pnr = PatternNotesRenderer(p)
        html = self.normalize_html(pnr.render())
        goal_text = self.normalize_html(
            """The instructions in the main body
	        of this pattern are for a bottom-up, pieced sweater.
	        Instructions for working the sweater seamlessly are given at
		    the end of the pattern."""
        )
        self.assertIn(goal_text, html)


class BustDartInstructionsTestCase(RendererTestCase):

    def test_missing_inter_nipple_distance(self):
        body = BodyFactory(inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(body=body)
        p = SweaterPatternFactory.from_pspec(pspec)
        bdi = BustDartRenderer(p)
        self.assertFalse(bdi)

    def test_non_hourglass_silhouetted(self):
        body = BodyFactory()
        for silhouette in [
            SDC.SILHOUETTE_ALINE,
            SDC.SILHOUETTE_STRAIGHT,
            SDC.SILHOUETTE_TAPERED,
        ]:
            pspec = SweaterPatternSpecFactory(
                silhouette=silhouette,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
                torso_length=SDC.MED_HIP_LENGTH,
                body=body,
            )
            p = SweaterPatternFactory.from_pspec(pspec)
            bdi = BustDartRenderer(p)
            self.assertFalse(bdi)

    def test_hourglass_silhouetted(self):
        body = BodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        p = SweaterPatternFactory.from_pspec(pspec)
        bdi = BustDartRenderer(p)
        self.assertTrue(bdi)
        patterntext = bdi.render()
        self.assertIn("<em>Dart row one (RS):</em>", patterntext)


class SleeveTests(RendererTestCase):

    maxDiff = None

    def render_sleeve(self, pspec):
        assert pspec.garment_type in [SDC.PULLOVER_SLEEVED, SDC.CARDIGAN_SLEEVED]
        p = SweaterPatternFactory.from_pspec(pspec)
        sl = p.get_sleeve()
        slr = SleeveRenderer(sl)
        html = slr.render()
        return html

    def test_sleeve_straight(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_STRAIGHT,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_patterntext = self.get_goal_html_from_file("sleeve_straight.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_sleeve_tapered(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_patterntext = self.get_goal_html_from_file("sleeve_tapered.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_sleeve_bell(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_BELL,
            bell_type=SDC.BELL_MODERATE,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_patterntext = self.get_goal_html_from_file("sleeve_bell.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_drop_shoulder(self):
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_patterntext = self.get_goal_html_from_file("sleeve_drop_shoulder.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_additional_element_caston_finite(self):
        adl = AdditionalSleeveElementFactory(
            name="Stripe",
            start_location_type=AdditionalSleeveElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalSleeveElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext)
        goal_html2 = """
             <p>Note: There were 45 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext)

    def test_additional_element_caston_no_end(self):
        adl = AdditionalSleeveElementFactory(
            name="Stripe",
            start_location_type=AdditionalSleeveElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalSleeveElement.HEIGHT_NO_END,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (21 rows from beginning) on RS row
            switch to secondary color. Continue as written for 147 rows, then
            switch back to primary color.
            </p>
        """
        self.assertInHTML(goal_html1, patterntext)
        goal_html2 = """
             <p>Note: There were 45 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext)

    def test_additional_element_cap_finite(self):
        adl = AdditionalSleeveElementFactory(
            name="Stripe",
            start_location_type=AdditionalSleeveElement.START_BEFORE_CAP,
            start_location_value=2.5,
            height_type=AdditionalSleeveElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_html1 = """
        <p>
        When piece measures 15&quot;/38 cm (105 rows from beginning) on RS row
        switch to secondary color. Continue as written for 10 rows, then
        switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext)
        goal_html2 = """
             <p>Note: There were 45 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext)

    def test_additional_element_cap_no_end(self):
        adl = AdditionalSleeveElementFactory(
            name="Stripe",
            start_location_type=AdditionalSleeveElement.START_BEFORE_CAP,
            start_location_value=2.5,
            height_type=AdditionalSleeveElement.HEIGHT_NO_END,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sleeve(pspec)
        goal_html1 = """
        <p>
        When piece measures 15&quot;/38 cm (105 rows from beginning) on RS row
        switch to secondary color. Continue as written for 63 rows, then
        switch back to primary color.
        </p>
        """
        self.assertInHTML(goal_html1, patterntext)
        goal_html2 = """
             <p>Note: There were 45 stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext)

    def test_additional_element_error(self):
        adl = AdditionalSleeveElementFactory(
            name="Stripe",
            start_location_type=AdditionalSleeveElement.START_AFTER_CASTON,
            start_location_value=40,
            height_type=AdditionalSleeveElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        with self.assertRaises(SleeveRenderer.SectionStartsAfterPieceEnds):
            patterntext = self.render_sleeve(pspec)

    #################################################################################################
    #
    # Graded sleeves
    #
    #################################################################################################

    def modify_and_render_graded_sleeve(self, pspec, modify_f):
        pspec = GradedSweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
        )
        pspec.full_clean()
        p = GradedSweaterPatternFactory.from_pspec(pspec)
        for sl in p.pieces.sleeves:
            modify_f(sl)

        sls = PieceList(p.pieces.sleeves)
        slr = SleeveRenderer(sls)
        html = slr.render()
        return html

    def test_graded_sleeve_no_compound(self):
        pspec = GradedSweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
        )

        def modify_f(sl):
            sl.num_sleeve_compound_increase_rows = None
            sl.save()

        html = self.modify_and_render_graded_sleeve(pspec, modify_f)
        goal_html = """
        <p>
        Work a shaping row every 7 (7, 8, 8, 9) rows 54 times.
        </p>
         """
        self.assertInHTML(goal_html, html)
        self.assertNotIn("For sizes", html)

    def test_graded_sleeve_all_compound(self):
        pspec = GradedSweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
        )

        def modify_f(sl):
            sl.num_sleeve_compound_increase_rows = sl.num_sleeve_increase_rows - 1
            sl.rows_after_compound_shaping_rows = sl.inter_sleeve_increase_rows + 1
            sl.save()

        html = self.modify_and_render_graded_sleeve(pspec, modify_f)
        goal_html = """
        <p>
        Work a shaping row every 7 (7, 8, 8, 9) rows 54 times,
        then every 8 (8, 9, 9, 10) rows 53 times.
        107 total shaping rows worked.
        </p>"""

        self.assertInHTML(goal_html, html)
        self.assertNotIn("For sizes", html)

    def test_graded_sleeve_some_compound(self):
        pspec = GradedSweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
        )

        def modify_f(sl):
            if (sl.finished_full_bust < 45) and (sl.finished_full_bust > 35):
                sl.num_sleeve_compound_increase_rows = None
                sl.rows_after_compound_shaping_rows = None
            else:
                sl.num_sleeve_compound_increase_rows = sl.num_sleeve_increase_rows - 1
                sl.rows_after_compound_shaping_rows = sl.inter_sleeve_increase_rows + 1
            sl.save()

        html = self.modify_and_render_graded_sleeve(pspec, modify_f)
        goal_html = """
        <div>
        <div>
            <p><em>
            For sizes 41 (42, 43, 44, -)&quot;/104 (107, 109.5, 112, -) cm only:
            </em></p>
        <p>
        Work a shaping row every
            7 (7, 8, 8, -) rows
        54 (54, 54, 54, -) times.
        </p>
        </div>
        <div>
            <p><em>
            For sizes - (-, -, -, 45)&quot;/- (-, -, -, 114.5) cm only:
            </em></p>
        <p>
        Work a shaping row every
            - (-, -, -, 9) rows
            - (-, -, -, 54) times,
        then every
            - (-, -, -, 10) rows
            - (-, -, -, 53) times.
            - (-, -, -, 107) total shaping rows worked.
        </p>
        </div>
        <p><em>
            All sizes:
        </em></p>
        """
        self.assertInHTML(goal_html, html)


class FinishingTests(RendererTestCase):

    maxDiff = None

    def render_finishing(self, pspec):
        p = SweaterPatternFactory.from_pspec(pspec)
        fr = FinishingRenderer(p)
        html = fr.render()
        return html

    def test_pullover_sleeved(self):
        pspec = SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_SLEEVED)
        pspec.full_clean()
        patterntext = self.render_finishing(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "finishing_pullover_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_pullover_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        pspec.full_clean()
        patterntext = self.render_finishing(pspec)
        goal_patterntext = self.get_goal_html_from_file("finishing_pullover_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_cardigan_sleeved_boatneck(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_BOAT,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=7,
        )
        pspec.full_clean()
        patterntext = self.render_finishing(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "finishing_cardigan_boatneck.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_cardigan_sleeved_veeneck(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=7,
        )
        pspec.full_clean()
        patterntext = self.render_finishing(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "finishing_cardigan_veeneck.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)


class SeamlessTests(RendererTestCase):

    maxDiff = None

    def render_seamless(self, pspec):
        p = SweaterPatternFactory.from_pspec(pspec)
        sr = SeamlessRenderer(p)
        html = sr.render()
        return html

    def test_pullover_sleeved(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED, name="Seamless Test Design"
        )
        pspec.full_clean()
        patterntext = self.render_seamless(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "seamless_pullover_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_pullover_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
            name="Seamless Test Design",
        )
        pspec.full_clean()
        patterntext = self.render_seamless(pspec)
        goal_patterntext = self.get_goal_html_from_file("seamless_pullover_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_cardigan_sleeved(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_BOAT,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=7,
            name="Seamless Test Design",
        )
        pspec.full_clean()
        patterntext = self.render_seamless(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "seamless_cardigan_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)


class SchematicWebTests(RendererTestCase):

    maxDiff = None

    def render_schematic(self, pspec):
        p = SweaterPatternFactory.from_pspec(pspec)
        sr = SchematicRendererWeb(p)
        html = sr.render()
        return html

    def test_pullover_sleeved(self):
        pspec = SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_SLEEVED)
        pspec.full_clean()
        patterntext = self.render_schematic(pspec)
        goal_patterntext = self.get_goal_html_from_file(
            "schematic_pullover_sleeved.html"
        )
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_cardigan_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_BOAT,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=7,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
            name="Seamless Test Design",
        )
        pspec.full_clean()
        patterntext = self.render_schematic(pspec)
        goal_patterntext = self.get_goal_html_from_file("schematic_cardigan_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_tapered_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        pspec.full_clean()
        patterntext = self.render_schematic(pspec)
        goal_patterntext = self.get_goal_html_from_file("schematic_tapered_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_aline_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        pspec.full_clean()
        patterntext = self.render_schematic(pspec)
        goal_patterntext = self.get_goal_html_from_file("schematic_aline_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)

    def test_straight_vest(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        pspec.full_clean()
        patterntext = self.render_schematic(pspec)
        goal_patterntext = self.get_goal_html_from_file("schematic_straight_vest.html")
        self.assertHTMLEqual(patterntext, goal_patterntext)


class GradedPulloverBackTests(RendererTestCase):

    maxDiff = None

    def render_sweater_back(self, pspec):
        assert pspec.garment_type == SDC.PULLOVER_SLEEVED
        p = GradedSweaterPatternFactory.from_pspec(pspec)
        sf = PieceList(p.pieces.sweater_backs)
        sfr = SweaterbackRenderer(sf)
        html = sfr.render()
        return html

    def test_additional_back_element_below_neckline(self):
        adl = AdditionalBackElementFactory(
            name="Stripe",
            start_location_type=AdditionalBackElement.START_AFTER_CASTON,
            start_location_value=3,
            height_type=AdditionalBackElement.HEIGHT_IN_ROWS,
            height_value=10,
        )
        pspec = GradedSweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            design_origin=adl.design,
        )
        pspec.full_clean()
        patterntext = self.render_sweater_back(pspec)
        goal_html1 = """
            <p>
            When piece measures 3&quot;/7.5 cm (75 rows from beginning) on RS row
            switch to secondary color. Continue as written for 10 rows, then
            switch back to primary color.            
            </p>
        """
        self.assertInHTML(goal_html1, patterntext, count=1)
        goal_html2 = """
             <p>Note: There were 500 (513, 525, 538, 550) stitches at cast-on.</p>
        """
        self.assertInHTML(goal_html2, patterntext, count=1)
