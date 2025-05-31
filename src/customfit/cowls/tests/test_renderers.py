# -*- coding: utf-8 -*-

# Oy, these renderers I made. Horrible, unextensible, and untestable.
# Let's test what we can while we figure out how to re-factor them into
# something better.
import os.path
import re

from django.test import TestCase

from customfit.helpers.math_helpers import CM_PER_INCHES
from customfit.stitches.factories import StitchFactory, TemplateStitchFactory
from customfit.swatches.factories import SwatchFactory

from ..factories import (
    CowlDesignFactory,
    CowlPatternFactory,
    CowlPatternSpecFactory,
    GradedCowlPatternFactory,
    RedoneCowlPatternFactory,
    TemplatedDesignFactory,
)
from ..renderers import (
    CowlFinishingRenderer,
    CowlPatternRendererPdfAbridged,
    CowlPatternRendererPdfFull,
    CowlPatternRendererWebFull,
    CowlPieceRenderer,
    CowlSchematicRendererPrint,
    CowlSchematicRendererWeb,
    GradedCowlPatternRendererWebFull,
    PdfPreambleRenderer,
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


class PreambleRendererTestBase(object):
    #
    # Subclasses must implement:
    #
    # * self.renderer_class

    yardage_re = re.compile(
        "<li><strong>Materials:</strong>yarn_maker yarn_name \d+g, \d+ hanks, approximately \d+ yd/\d+ m</li>"
    )
    no_yardage_re = re.compile("Want a better estimate?")

    def render_preamble(self, pspec):
        p = CowlPatternFactory.from_pspec(pspec)
        wpr = self.renderer_class(p)
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
        pspec = CowlPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        html = self.normalize_html(html)
        match_obj = self.yardage_re.search(html)
        self.assertIsNotNone(match_obj)
        match_obj = self.no_yardage_re.search(html)
        self.assertIsNone(match_obj)

    def test_extra_notions(self):
        notion_text = "a little of this, a little of that"
        design = CowlDesignFactory(notions=notion_text)
        pspec1 = CowlPatternSpecFactory(design_origin=design)
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = "<li><strong>Notions:</strong> Darning needle, a little of this, a little of that</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_stitch_notions(self):
        notion_text = "a little more of this, a little more of that"
        stitch = StitchFactory(extra_notions_text=notion_text)
        pspec1 = CowlPatternSpecFactory(edging_stitch=stitch)
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = "<li><strong>Notions:</strong> Darning needle, a little more of this, a little more of that</li>"
        self.assertInHTML(goal_html, patterntext)

    def test_all_notions(self):
        stitch1 = StitchFactory(
            extra_notions_text="stitch1 extra notions, more stitch1 extra notions, foo"
        )
        stitch2 = StitchFactory(
            extra_notions_text="stitch2 extra notions, more stitch2 extra notions, foo"
        )
        design = CowlDesignFactory(
            notions="design extra notions, more design extra notions, foo"
        )
        pspec1 = CowlPatternSpecFactory(
            edging_stitch=stitch1,  # order matters
            main_stitch=stitch2,
            design_origin=design,
        )
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_html = """<li><strong>Notions:</strong> Darning needle, design extra notions,
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
        pspec1 = CowlPatternSpecFactory(swatch=swatch)
        pspec1.clean()
        patterntext = self.render_preamble(pspec1)
        goal_text = "<li><strong>Gauge:</strong>25.5 sts &amp; 20.25 rounds = 4&quot; / 25 sts &amp; 20 rounds = 10cm in"
        self.assertIn(goal_text, patterntext)

    def test_no_needle_text(self):
        swatch = SwatchFactory(needle_size=None)
        pspec = CowlPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        self.assertIn("<li><strong>Needles:</strong></li>", html)

    def test_redo(self):

        p = RedoneCowlPatternFactory()
        wpr = WebPreambleRenderer(p)
        html = wpr.render()
        html = self.normalize_html(html)

        orig_pspec = p.get_spec_source().get_original_patternspec()
        redo = p.get_spec_source()
        # sanity checks:
        self.assertNotEqual(orig_pspec.swatch, redo.swatch)
        self.assertNotEqual(orig_pspec.height, redo.height)
        self.assertNotEqual(orig_pspec.circumference, redo.circumference)

        # swatch
        self.assertIn(p.swatch.name, html)
        self.assertNotIn(orig_pspec.swatch.name, html)

        # height
        self.assertIn("<li>Height: Tall height (8½&quot;/22 cm)</li>", html)

        # circumference
        self.assertIn(
            "<li>Circumference: Large circumference (50½&quot;/128 cm)</li>", html
        )


class WebPreambleRendererTests(PreambleRendererTestBase, RendererTestCase):
    renderer_class = WebPreambleRenderer

    def test_imprecise_yardage_display(self):
        swatch = SwatchFactory(
            yarn_name="yarn_name",
            yarn_maker="yarn_maker",
            length_per_hank=None,
            weight_per_hank=None,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
            full_swatch_weight=19,
        )
        pspec = CowlPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        html = self.normalize_html(html)
        match_obj = self.yardage_re.search(html)
        self.assertIsNone(match_obj)
        match_obj = self.no_yardage_re.search(html)
        self.assertIsNotNone(match_obj)


class PdfPreambleRendererTests(PreambleRendererTestBase, RendererTestCase):
    renderer_class = PdfPreambleRenderer

    def test_imprecise_yardage_display(self):
        swatch = SwatchFactory(
            yarn_name="yarn_name",
            yarn_maker="yarn_maker",
            length_per_hank=None,
            weight_per_hank=None,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
            full_swatch_weight=19,
        )
        pspec = CowlPatternSpecFactory(swatch=swatch)
        html = self.render_preamble(pspec)
        html = self.normalize_html(html)
        match_obj = self.yardage_re.search(html)
        self.assertIsNone(match_obj)
        # 'Want a better estimate' is for the web only


class FinishingTests(RendererTestCase):

    def test_finishing_renderer(self):
        p = CowlPatternFactory()
        fr = CowlFinishingRenderer(p)
        html = fr.render()
        goal_html = """<div>
        <div><h2>Finishing Instructions</h2></div>
        <div><p>Wash cowl and lay flat to dry. Weave in ends.</p></div>
        </div>"""
        self.assertHTMLEqual(html, goal_html)


class SchematicTestsBase(object):
    maxDiff = None

    def render_schematic(self, pattern):
        sr = self.renderer(pattern)
        html = sr.render()
        return html

    def test_schematic_renderer(self):
        p = CowlPatternFactory(
            pieces__cowl__total_rows=84,
            pieces__cowl__cast_on_stitches=180,
            pieces__cowl__edging_height_in_rows=21,
        )
        # sanity checks
        cowl = p.pieces.cowl
        self.assertEqual(cowl.actual_height(), 12)
        self.assertEqual(cowl.actual_circumference(), 36)
        self.assertEqual(cowl.actual_edging_height(), 3)

        html = self.render_schematic(p)
        self.assertHTMLEqual(html, self.goal_html)


class SchematicWebTests(SchematicTestsBase, RendererTestCase):
    renderer = CowlSchematicRendererWeb
    goal_html = """
        <div class="schematic-section">
          <div><h2>Pattern Schematic</h2></div>
          <div>
            <!-- begin dimensions -->
            <div class="row">
            <div class="col-xs-12 col-sm-6 col-md-6">
              <img src="/static/img/Cowl_Schematic.png" class="schematic-image">
            </div>
            <div class="col-xs-12 col-sm-6 col-md-6 text-right text-centered-phone faux-table-hover margin-top-15">
              <div class="row">
                <div class="col-md-12 col-lg-10">
                  <strong>cowl dimensions</strong>
                </div>
              </div>
                  <div class="row">
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      actual height
                    </div>
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      12&quot;/30.5 cm
                    </div>
                  </div>
                  <div class="row">
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      actual circumference
                    </div>
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      36&quot;/91.5 cm
                    </div>
                  </div>
                  <div class="row">
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      actual edging height
                    </div>
                    <div class="col-xs-6 col-sm-6 col-lg-5">
                      3&quot;/7.5 cm
                    </div>
                  </div>
            </div>
            </div>
            <!-- end  dimensions -->              
              </div>
            </div>
    """


class SchematicPdfTests(SchematicTestsBase, RendererTestCase):
    renderer = CowlSchematicRendererPrint
    goal_html = """
    <div class="schematic-section">
      <div><h2>Pattern Schematic</h2></div>
      <div>
        <div class="div-schematic-piece-pair">
        <div class="div-schematic-image">
            <img src="/static/img/Cowl_Schematic.png" class="schematic-image" id="id-schematic-image-cowl">
        </div>
        <div class="div-schematic-measurements">
        <!-- begin dimensions -->
        <strong>cowl dimensions</strong>
        <ul>
                  <li>actual height: 12&quot;/30.5 cm</li>
                  <li>actual circumference: 36&quot;/91.5 cm</li>
                  <li>actual edging height: 3&quot;/7.5 cm</li>        
        </ul>
        <!-- end dimensions -->
        </div>
        </div>
        </div>
        </div>
    """


class CowlPieceRendererTests(RendererTestCase):
    maxDiff = None

    standard_first_part = """
                    <p>
                    CO 252 sts. Place marker and join for working in the
                    round, being careful not to twist.
                </p>
                <p>
                    Work in 1x1 Ribbing until cowl measures ¾&quot;/2 cm from CO edge (5 rounds total).
                </p>
                <p>
                  Switch to Stockinette.
                </p>
    """

    standard_second_part = """
                <p>
                    <strong>Next round:</strong> Work all sts in Stockinette around.
                </p>
                <p>
                    Continue even until cowl measures 7¾&quot;/19.5 cm from CO edge (54 rounds from beginning).
                
                </p>
                <p>
                  Switch to 1x1 Ribbing.
                </p>
    """

    standard_third_part = """
                <p>
                    Repeat edging as for CO section of cowl.
                </p>
                <p>
                    BO all sts in pattern.
                </p>
    """

    def make_goal_html(self, first_part=None, second_part=None, third_part=None):
        if first_part is None:
            first_part = self.standard_first_part
        if second_part is None:
            second_part = self.standard_second_part
        if third_part is None:
            third_part = self.standard_third_part

        goal_html = """
                <div>
                    <div><h2>Cowl</h2></div>
                    <div>

                        %s
                        
                        %s
                        
                        %s

                        <h4>Actual measurements:</h4>

                        <ul>
                          <li>Circumference: 50½&quot;/128 cm</li>
                          <li>Height: 8½&quot;/22 cm</li>
                        </ul>

                    </div>
                </div>
                """ % (
            first_part,
            second_part,
            third_part,
        )
        return goal_html

    def test_defaults(self):
        p = CowlPatternFactory()
        cowl = p.pieces.cowl
        renderer = CowlPieceRenderer(cowl)
        html = renderer.render()
        goal_html = self.make_goal_html()
        self.assertHTMLEqual(html, goal_html)

    def test_stitch_trumps_defaults(self):
        stitch = TemplateStitchFactory()
        pspec = CowlPatternSpecFactory(edging_stitch=stitch, main_stitch=stitch)
        pattern = CowlPatternFactory.from_pspec(pspec)
        cowl = pattern.pieces.cowl
        renderer = CowlPieceRenderer(cowl)
        html = renderer.render()
        goal_first_part = """
            <p>[default CowlCastonEdgeTemplateFactory template]<p>
            <p>252<p>
        """
        goal_second_part = """
            <p>[default CowlMainSectionTemplateFactory template]<p>
            <p>252<p>
        """
        goal_third_part = """
            <p>[default CowlCastoffEdgeTemplateFactory template]<p>
            <p>252<p>
        """
        goal_html = self.make_goal_html(
            first_part=goal_first_part,
            second_part=goal_second_part,
            third_part=goal_third_part,
        )
        self.assertHTMLEqual(html, goal_html)

    def test_design_trumps_stitch(self):
        stitch = TemplateStitchFactory()
        design = TemplatedDesignFactory()
        pspec = CowlPatternSpecFactory(
            edging_stitch=stitch, main_stitch=stitch, design_origin=design
        )
        pattern = CowlPatternFactory.from_pspec(pspec)
        cowl = pattern.pieces.cowl
        renderer = CowlPieceRenderer(cowl)
        html = renderer.render()
        goal_first_part = """
            <p>[default FirstEdgingTemplateFactory template]<p>
            <p>252<p>
        """
        goal_second_part = """
            <p>[default MainSectionTemplateFactory template]<p>
            <p>252<p>
        """
        goal_third_part = """
            <p>[default FinalEdgingTemplateFactory template]<p>
            <p>252<p>
        """
        goal_html = self.make_goal_html(
            first_part=goal_first_part,
            second_part=goal_second_part,
            third_part=goal_third_part,
        )
        self.assertHTMLEqual(html, goal_html)


class CowlPatternRendererTestsMixin(object):
    #
    # Subclasses must implement:
    #
    # * self.renderer_pattern(pattern)

    def render_pattern(self, pattern):
        wpr = self.renderer_class(pattern)
        html = wpr.render_pattern()
        return html

    def test_can_render(self):
        pattern = CowlPatternFactory()
        rendered_pattern = self.render_pattern(pattern)


class WebRendererFullTests(CowlPatternRendererTestsMixin, RendererTestCase):
    renderer_class = CowlPatternRendererWebFull


class PdfRendererFullTests(CowlPatternRendererTestsMixin, RendererTestCase):
    renderer_class = CowlPatternRendererPdfFull


class PdfRendererAbridgedTests(CowlPatternRendererTestsMixin, RendererTestCase):
    renderer_class = CowlPatternRendererPdfAbridged


class GradedCowlPatternRendererTests(TestCase):
    #
    # Subclasses must implement:
    #
    # * self.renderer_pattern(pattern)

    maxDiff = None

    def render_pattern(self, pattern):
        wpr = GradedCowlPatternRendererWebFull(pattern)
        html = wpr.render_pattern()
        return html

    def test_can_render(self):
        pattern = GradedCowlPatternFactory()
        rendered_pattern = self.render_pattern(pattern)
        goal_html = """
        <div>
          <div><h2>Cowl</h2></div>
          <div>
            <p>
                CO 100 (130, 210, 300) sts. Place marker and join for working in the
                round, being careful not to twist.
            </p>
            <p>
                Work in 1x1 Ribbing until cowl measures 1¼&quot;/3 cm
                from CO edge.
            </p>
            <p>
                Switch to Stockinette.
            </p>
            <p>
                <strong>Next round:</strong> Work all sts in Stockinette around.
            </p>
            <p>
                Continue even until cowl measures 8¾ (10½, 14½, 18½)&quot;/22 (27, 37, 47) cm from CO edge.
            </p>
            <p>
                Switch to 1x1 Ribbing.
            </p>
            <p>
                Repeat edging as for CO section of cowl.
            </p>
            <p>
                BO all sts in pattern.
            </p>
            <h4>Actual measurements:</h4>
            <ul>
              <li>Circumference: 20 (26, 42, 60)&quot;/51 (66, 106.5, 152.5) cm</li>
              <li>Height: 10 (12, 16, 20)&quot;/25.5 (30.5, 40.5, 51) cm</li>
            </ul>
          </div>
        </div>
        <div>
            <div><h2>Finishing Instructions</h2></div>
            <div>
            <p>Wash cowl and lay flat to dry. Weave in ends.</p>  
            </div>
        </div>"""
        self.assertHTMLEqual(rendered_pattern, goal_html)
