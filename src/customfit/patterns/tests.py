# -*- coding: utf-8 -*-


import datetime
import itertools
import re
import unittest.mock as mock
import urllib.error
import urllib.parse
import urllib.request

import pytz
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import resolve, reverse

from customfit.designs.factories import DesignerFactory, DesignFactory
from customfit.helpers.math_helpers import CallableCompoundResult, CompoundResult
from customfit.pattern_spec.factories import PatternSpecFactory
from customfit.stitches.factories import StitchFactory
from customfit.swatches.factories import GaugeFactory
from customfit.test_garment.factories import (
    GradedTestPatternFactory,
    TestAdditionalElementFactory,
    TestApprovedIndividualPatternFactory,
    TestArchivedIndividualPatternFactory,
    TestIndividualPatternFactory,
    TestPatternSpecFactory,
    TestRedonePatternFactory,
)
from customfit.test_garment.models import (
    TestAdditionalDesignElement,
    TestIndividualPattern,
)
from customfit.userauth.factories import StaffFactory, UserFactory

from .models import IndividualPattern
from .renderers import (
    AboutDesignerRenderer,
    DesignerNotesRenderer,
    InformationSection,
    InstructionSection,
    PdfPersonalNotesRenderer,
    PieceList,
    StitchesSectionRenderer,
    SubSection,
    WebPersonalNotesRenderer,
)
from .templatetags.pattern_conventions import (
    count_fmt,
    divide_counts_by_gauge,
    length_fmt,
    length_long_fmt,
    percentage_match_parity,
    percentage_round_whole,
    pluralize_counts,
    round_counts_tag,
    round_lengths_tag,
    round_tag,
)


class PieceListTests(TestCase):

    def test_init(self):
        PieceList([1, 2, 3])

        with self.assertRaises(AssertionError):
            PieceList([])

    def test_dict_lookup(self):

        l = [{"a": 1, "b": 1}, {"a": 2, "b": 1}, {"a": 3, "b": 1}]
        p = PieceList(l)

        self.assertEqual(p["a"], [1, 2, 3])
        self.assertEqual(
            p["b"],
            [
                1,
                1,
                1,
            ],
        )
        self.assertIsInstance(p["a"], CompoundResult)

        with self.assertRaises(KeyError):
            p["c"]

    def test_dict_lookup_error1(self):
        class TestObject(object):
            def __init__(self, x):
                self.a = x

        l = [
            TestObject(1),
            TestObject(2),
            TestObject(3),
        ]
        p = PieceList(l)

        with self.assertRaises(TypeError):
            p["a"]

    def test_dict_lookup_error2(self):
        class TestObject(object):
            def __init__(self, x):
                self.a = x

        l = [{"a": 1}, TestObject(2), {"a": 3}]
        p = PieceList(l)

        with self.assertRaises(TypeError):
            p["a"]

    def test_dict_lookup_error3(self):

        l = [{"a": 1}, {"b": 2}, {"a": 3}]
        p = PieceList(l)

        with self.assertRaises(KeyError):
            p["a"]

    def test_dict_lookup_callable(self):

        l = [{"a": lambda: 1}, {"a": lambda: 2}, {"a": lambda: 3}]
        p = PieceList(l)

        self.assertIsInstance(p["a"], CallableCompoundResult)
        self.assertEqual(p["a"](), [1, 2, 3])

    def test_getattr(self):

        class TestObject(object):
            def __init__(self, x):
                self.a = x
                self.b = 1

        p = PieceList([TestObject(1), TestObject(2), TestObject(3)])

        self.assertEqual(p.a, [1, 2, 3])
        self.assertIsInstance(p.a, CompoundResult)
        self.assertEqual(p.b, [1, 1, 1])

    def test_getattr_callable(self):

        class TestObject(object):
            def __init__(self, x):
                self._a = x

            def a(self):
                return self._a

        p = PieceList([TestObject(1), TestObject(2), TestObject(3)])
        self.assertIsInstance(p.a, CallableCompoundResult)
        self.assertEqual(p.a(), [1, 2, 3])

    def test_callable_error(self):

        l = [{"a": 1}, {"a": lambda: 2}, {"a": 3}]
        p = PieceList(l)

        with self.assertRaises(RuntimeError):
            p["a"]

    def test_list_index(self):

        l = [[1, 4, 7, 1], [2, 5, 8, 1], [3, 6, 9, 1]]
        p = PieceList(l)
        self.assertEqual(p[0], [1, 2, 3])
        self.assertEqual(p[0:1], [[1], [2], [3]])
        self.assertEqual(p[0:2], [[1, 4], [2, 5], [3, 6]])
        self.assertEqual(p[3], [1, 1, 1])


# Base class with useful methods
class RendererTestCase(TestCase):

    measurement_re = re.compile(
        "(\\d+[\\u00BC\\u00BD\\u00BE]?|[\\u00BC\\u00BD\\u00BE])&quot;/\\d+(\\.5)? cm"
    )

    def normalize_html(self, html):
        # Remove non-semantic whitespace from HTML so it doesn't cause
        # regexp match errors.
        html = re.sub(r"\s+", " ", html)
        html = re.sub(r">\s+<", "><", html)
        html = re.sub(r"\s+<", "<", html)
        html = re.sub(r">\s+", ">", html)
        return html

    # def get_goal_html_from_file(self, filename):
    #     currpath = os.path.dirname(os.path.abspath(__file__))
    #     path = os.path.join(currpath, 'patterntext_fragments', filename)
    #     with open(path, 'r') as f:
    #         return f.read()


class AbstractClassesTestCase(RendererTestCase):

    maxDiff = None
    gauge = GaugeFactory()

    # First, define a simple mock-piece object to hold elements
    class MockPiece(object):
        FINAL_ROW = 100

        def __init__(self, *elements):
            super(AbstractClassesTestCase.MockPiece, self).__init__()
            self.individualpattern = self
            self.individualpatternpieces = self
            self.get_spec_source = lambda: self
            self.design_origin = self
            self.elements = list(elements)
            self.gauge = AbstractClassesTestCase.gauge
            self.final_row = self.FINAL_ROW

        def get_pattern(self):
            return self.individualpattern

        @property
        def design(self):
            return self

    # First, let's define two simple concrete subclasses of the abstract classes

    class SimpleSubsection(SubSection):

        def __init__(
            self,
            title,
            start_rows,
            end_rows,
            interrupts_others,
            warn_if_interrupted,
            additional_context,
        ):
            super(AbstractClassesTestCase.SimpleSubsection, self).__init__()
            self._name = title
            self._start_rows = start_rows
            self._end_rows = end_rows
            self._warn_if_interrupted = warn_if_interrupted
            self._interrupts_others = interrupts_others

        def display_name(self):
            return self._display_name

        def __eq__(self, other):
            return min(self.start_rows) == min(other.start_rows)

        def __lt__(self, other):
            return min(self.start_rows) < min(other.start_rows)

        def starts_during(self, other):
            return (other.start_rows[0] <= self.start_rows[0]) and (
                self.start_rows[0] <= other.end_rows[0]
            )

        def starts_during_all_grades(self, other):
            return (other.start_rows[0] <= self.start_rows[0]) and (
                self.start_rows[0] <= other.end_rows[0]
            )

        @property
        def start_rows(self):
            return self._start_rows

        @property
        def end_rows(self):
            return self._end_rows

        @property
        def warn_if_interrupted(self):
            return self._warn_if_interrupted

        @property
        def interrupts_others(self):
            return self._interrupts_others

    class SimpleInstructionSection(InstructionSection):

        START_HEIGHT = 10

        @property
        def piece_name(self):
            return "Mock Section"

        def _make_elements(self, additional_context):
            return self._make_additional_elements(additional_context)

        def _get_additional_elements_from_design(self, design):
            # Note that this only works when we initialize this class with a MockPiece
            return design.elements

        def _get_start_rows_from_additonal_element(self, additional_element):
            el_val = additional_element.start_row(
                self.START_HEIGHT, AbstractClassesTestCase.gauge
            )
            return CompoundResult([el_val])

        def _make_subsections_for_additonal_element(
            self,
            title,
            start_rows,
            end_rows,
            interrupts_others,
            warn_if_interrupted,
            additional_context,
        ):
            return [
                AbstractClassesTestCase.SimpleSubsection(
                    title,
                    start_rows,
                    end_rows,
                    interrupts_others,
                    warn_if_interrupted,
                    additional_context,
                )
            ]

        def get_piece_final_rows(self, additional_context):
            return self.piece_list.final_row

    class SimpleInformationSection(InformationSection):

        def _gather_text(self, additional_context):
            pass

        def piece_name(self):
            pass

    # And now, the tests!

    def test_element_methods(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=5,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 1 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        elements = sis._make_elements({})
        el = elements[0]
        self.assertEqual(el.start_rows(), CompoundResult([7]))

    def test_simple_information(self):
        mock_piece = AbstractClassesTestCase.MockPiece()
        mock_piece.id = 101
        sis = AbstractClassesTestCase.SimpleInformationSection(mock_piece)

    def test_simple_instruction(self):
        element = TestAdditionalElementFactory(
            name="Element 1", template__content="<p>Element 1 content.</p>"
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element)
        mock_piece.id = 101
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div><p>Element 1 content.</p></div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_simple_instruction_graded(self):
        element = TestAdditionalElementFactory(
            name="Element 1", template__content="<p>Element 1 content.</p>"
        )
        mock_piece1 = AbstractClassesTestCase.MockPiece(element)
        mock_piece1.id = 101
        mock_piece2 = AbstractClassesTestCase.MockPiece(element)
        mock_piece2.id = 102
        piece_list = PieceList([mock_piece1, mock_piece2])
        sis = AbstractClassesTestCase.SimpleInstructionSection(piece_list)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div><p>Element 1 content.</p></div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_no_overlaps(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=1,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=3,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=1,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_instructional_instructional(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>
                <strong><em>Before you begin,</em></strong> please note that some instructions will overlap.
                In particular,
                Element 1 will overlap Element 2. Element 1 begins on row 7 and ends on row 20.
                Element 2 begins on row 15 and ends on row 28. Please read ahead.
            </p>
            <p>Element 1 content.</p>
            <p><strong><em>At the same time:</em></strong></p><p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_instructional_startonly(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>
                <strong><em>Before you begin,</em></strong> please note that some instructions will overlap.
                In particular,
                Element 1 will overlap Element 2. Element 1 begins on row 7 and ends on row 20.
                Element 2 begins on row 15 and ends on row 28. Please read ahead.
            </p>
            <p>Element 1 content.</p>
            <p><strong><em>At the same time:</em></strong></p><p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_instructional_informational(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_informational_instructional(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_informational_startonly(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_informational_informational(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_startonly_instructional(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_startonly_startonly(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_overlaps_startonly_informational(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_START_ONLY,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p>Element 1 content.</p>
            <p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)

    def test_multiple_overlaps(self):
        element1 = TestAdditionalElementFactory(
            name="Element 1",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=5,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 1 content.</p>",
        )
        element2 = TestAdditionalElementFactory(
            name="Element 2",
            start_location_value=2,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 2 content.</p>",
        )
        element3 = TestAdditionalElementFactory(
            name="Element 3",
            start_location_value=1,
            start_location_type=TestAdditionalDesignElement.START_AFTER_CASTON,
            height_value=2,
            height_type=TestAdditionalDesignElement.HEIGHT_IN_INCHES,
            overlap_behavior=TestAdditionalDesignElement.OVERLAP_INSTRUCTIONS,
            template__content="<p>Element 2 content.</p>",
        )
        mock_piece = AbstractClassesTestCase.MockPiece(element1, element2, element3)
        sis = AbstractClassesTestCase.SimpleInstructionSection(mock_piece)
        text = sis.render()
        goal_html = """
        <div>
        <div><h2>Mock Section</h2></div>
        <div>
            <p><strong><em>Before you begin,</em></strong> please note that some instructions will overlap:</p>
            <ul>
                <li>
                    Element 1 will overlap Element 3. Element 1 begins on row 7 and ends on row 42.
                    Element 3 begins on row 7 and ends on row 20.
                </li>
                <li>
                    Element 1 will overlap Element 2.
                    Element 1 begins on row 7 and ends on row 42.
                    Element 2 begins on row 15 and ends on row 28.
                </li>
                <li>
                    Element 3 will overlap Element 2.
                    Element 3 begins on row 7 and ends on row 20.
                    Element 2 begins on row 15 and ends on row 28.
                </li>
            </ul>
            <p>Please read ahead.</p>
            <p>Element 1 content.</p>
            <p><strong><em>At the same time:</em></strong></p><p>Element 2 content.</p>
            <p><strong><em>At the same time:</em></strong></p><p>Element 2 content.</p>
        </div>
        </div>"""
        self.assertHTMLEqual(text, goal_html)


class AboutDesignerTest(RendererTestCase):

    def _renderer_from_design(self, designer=None, is_basic=False):
        if designer is None:
            designer = DesignerFactory()
        des = DesignFactory(designer=designer, is_basic=is_basic)
        p = TestIndividualPatternFactory(
            pieces__schematic__individual_garment_parameters__pattern_spec__design_origin=des
        )
        renderer = AboutDesignerRenderer(p)
        return renderer

    def test_plain_design(self):
        r = self._renderer_from_design()
        self.assertTrue(r)

    def test_basic(self):
        r = self._renderer_from_design(is_basic=True)
        self.assertTrue(r)

    def test_designer_no_long_no_short(self):
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_long=None,
            about_designer_short=None,
        )
        r = self._renderer_from_design(designer=designer)
        self.assertFalse(r)

    def test_designer_yes_long_no_short(self):
        about_designer_long = """
This is paragraph 1.

This is paragraph 2.
"""
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_short=None,
            about_designer_long=about_designer_long,
        )
        r = self._renderer_from_design(designer=designer)
        self.assertTrue(r)
        html = r.render()
        html = self.normalize_html(html)

        goal_html = "<div><div><h2>About test designer</h2></div><div><p>This is paragraph 1.</p><p>This is paragraph 2.</p></div></div>"

        self.assertEqual(goal_html, html)

    def test_designer_yes_long_yes_short(self):
        about_designer_long = """
This is paragraph 1.

This is paragraph 2.
"""
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_short="Text!",
            about_designer_long=about_designer_long,
        )
        r = self._renderer_from_design(designer=designer)
        self.assertTrue(r)
        html = r.render()
        html = self.normalize_html(html)

        goal_html = "<div><div><h2>About test designer</h2></div><div><p>This is paragraph 1.</p><p>This is paragraph 2.</p></div></div>"

        self.assertEqual(goal_html, html)

    def test_designer_no_long_yes_short(self):
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_short="Text!",
            about_designer_long=None,
        )
        r = self._renderer_from_design(designer=designer)
        self.assertTrue(r)
        html = r.render()
        html = self.normalize_html(html)

        goal_html = (
            "<div><div><h2>About test designer</h2></div><div><p>Text!</p></div></div>"
        )

        self.assertEqual(goal_html, html)


class PersonalNotesRendererTest(RendererTestCase):

    def test_empty_notes(self):
        pattern = TestIndividualPatternFactory(notes="")  # explicitly test default

        # On the web, people should get the option to add notes if they don't
        # have any.
        pnr = WebPersonalNotesRenderer(pattern)
        html = self.normalize_html(pnr.render())
        url = reverse("patterns:individualpattern_note_update_view", args=(pattern.pk,))
        goal_text = self.normalize_html(
            """
            <a href="{url}"
            class='btn btn-customfit-outline'>
              add notes
            </a>""".format(
                url=url
            )
        )
        self.assertIn(goal_text, html)

        # The pdf should omit empty notes to save space/printing.
        pnr = PdfPersonalNotesRenderer(pattern)
        self.assertFalse(pnr)

    def test_nonempty_notes(self):
        pattern = TestIndividualPatternFactory(notes="I can has notes")

        # On the web, people should see their note and get an editing option.
        pnr = WebPersonalNotesRenderer(pattern)
        html = self.normalize_html(pnr.render())
        url = reverse("patterns:individualpattern_note_update_view", args=(pattern.pk,))
        goal_text = self.normalize_html(
            """
              <p>
                I can has notes
              </p>
              <a href="{url}" class='btn btn-customfit-outline'>
                Edit notes
              </a>""".format(
                url=url
            )
        )
        self.assertIn(goal_text, html)

        # The pdf should display the notes, but not the option to edit notes
        # (as it is unusable in this context).
        pnr = PdfPersonalNotesRenderer(pattern)
        html = self.normalize_html(pnr.render())
        goal_text = self.normalize_html(
            """
              <p>
                I can has notes
              </p>"""
        )
        self.assertIn(goal_text, html)


class DesignerNotesTests(RendererTestCase):

    maxDiff = None

    def _make_renderer(self, pspec):
        p = TestIndividualPatternFactory(
            pieces__schematic__individual_garment_parameters__pattern_spec=pspec
        )
        r = DesignerNotesRenderer(p)
        return r

    def _render_designer_notes(self, pspec):
        r = self._make_renderer(pspec)
        html = r.render()
        return html

    def test_notes_and_credits(self):
        des = DesignFactory(description="Design description")
        pspec = PatternSpecFactory(design_origin=des, pattern_credits="Design credits")

        r = self._make_renderer(pspec)
        self.assertTrue(r)

        html = self._render_designer_notes(pspec)
        self.assertHTMLEqual(
            html,
            """<div><div><h2>Design Notes</h2></div><div><p>Design description</p>
                             <p>Design credits</p></div></div>""",
        )

    def test_notes_no_credits(self):
        des = DesignFactory(description="Design description", pattern_credits="")
        pspec = PatternSpecFactory(design_origin=des, pattern_credits="")

        r = self._make_renderer(pspec)
        self.assertTrue(r)

        html = self._render_designer_notes(pspec)
        self.assertHTMLEqual(
            html,
            """<div><div><h2>Design Notes</h2></div><div><p>Design description</p>
                             </div></div>""",
        )

    def test_credits_no_notes(self):
        des = DesignFactory(description="")
        pspec = PatternSpecFactory(design_origin=des, pattern_credits="Design credits")

        r = self._make_renderer(pspec)
        self.assertTrue(r)

        html = self._render_designer_notes(pspec)
        self.assertHTMLEqual(
            html,
            """<div><div><h2>Design Notes</h2></div><div><p></p>
                             <p>Design credits</p></div></div>""",
        )

    def test_no_notes_no_credits(self):
        des = DesignFactory(description="", pattern_credits="")
        pspec = PatternSpecFactory(design_origin=des, pattern_credits="")

        r = self._make_renderer(pspec)
        self.assertFalse(r)


class PatternTests(TestCase):

    def test_cache_fill_and_flush(self):
        p = TestIndividualPatternFactory()
        piece = p.pieces.test_piece
        cache_key = "patterntext:TestPieceRenderer:TestPatternPiece:%d" % piece.id

        p.prefill_patterntext_cache()
        self.assertIsNotNone(cache.get(cache_key), msg=cache_key)

        p.flush_patterntext_cache()
        self.assertIsNone(cache.get(cache_key), msg=cache_key)

    def test_redo_deadline(self):

        _tz = pytz.timezone(settings.TIME_ZONE)
        # patterns made before the deadline-start should still get 90 days since deadline-start

        long_ago = datetime.datetime(2017, 1, 1, 0, 0, 0, 0, _tz)
        p1 = TestIndividualPatternFactory(creation_date=long_ago)
        self.assertEqual(
            p1.redo_deadline(), datetime.datetime(2018, 6, 18, 0, 0, 0, 0, _tz)
        )

        just_before = datetime.datetime(2018, 3, 18, 12, 13, 14, 0, _tz)
        p1 = TestIndividualPatternFactory(creation_date=just_before)
        self.assertEqual(
            p1.redo_deadline(), datetime.datetime(2018, 6, 18, 0, 0, 0, 0, _tz)
        )

        # A pattern made after deadline-start shoudl get 90 days since creation
        just_after = datetime.datetime(2018, 3, 25, 1, 1, 1, 1, _tz)
        p1 = TestIndividualPatternFactory(creation_date=just_after)
        self.assertEqual(
            p1.redo_deadline(), datetime.datetime(2018, 6, 23, 1, 1, 1, 1, _tz)
        )

        far_future = datetime.datetime(2020, 12, 31, 0, 0, 0, 0, _tz)
        p1 = TestIndividualPatternFactory(creation_date=far_future)
        self.assertEqual(
            p1.redo_deadline(), datetime.datetime(2021, 3, 31, 0, 0, 0, 0, _tz)
        )

    def test_redo_days_left(self):

        _tz = pytz.timezone(settings.TIME_ZONE)
        long_ago = datetime.datetime(2017, 1, 1, 0, 0, 0, 0, _tz)
        p1 = TestIndividualPatternFactory(creation_date=long_ago)

        # sanity check
        self.assertEqual(
            p1.redo_deadline(), datetime.datetime(2018, 6, 18, 0, 0, 0, 0, _tz)
        )

        testdate = datetime.datetime(2018, 6, 10, 0, 0, 0, 0, _tz)
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            self.assertEqual(p1.redo_days_left(), 8)

        testdate = datetime.datetime(2018, 6, 10, 0, 0, 0, 1, _tz)
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            self.assertEqual(p1.redo_days_left(), 7)

        testdate = datetime.datetime(2018, 6, 17, 0, 0, 0, 1, _tz)
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            self.assertEqual(p1.redo_days_left(), 0)

        testdate = datetime.datetime(2018, 6, 17, 23, 59, 59, 1, _tz)
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            self.assertEqual(p1.redo_days_left(), 0)

        testdate = datetime.datetime(2018, 6, 18, 0, 0, 0, 1, _tz)
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            self.assertIsNone(p1.redo_days_left())

    def test_redo_possible(self):

        #
        # previously-redone/not-redone
        #

        # It should be possible to redo a (new) pattern that has not been redone
        p = TestIndividualPatternFactory()
        # sanity check
        self.assertIsNone(p.original_pieces)
        # real test
        self.assertTrue(p.redo_possible())

        # It should not be possible to redo a (new) pattern that has already been redone
        p2 = TestIndividualPatternFactory()
        ipp = p2.pieces
        p.original_pieces = ipp
        self.assertFalse(p.redo_possible())

        #
        # Deadlines
        #

        # Patterns made before the deadline-start should be possible 90 days after deadline start, but not later
        _tz = pytz.timezone(settings.TIME_ZONE)
        before_nintey_days = datetime.datetime(2018, 6, 17, 23, 59, 59, 0, _tz)
        after_nintey_days = datetime.datetime(2018, 7, 18, 0, 0, 0, 1, _tz)

        long_ago = datetime.datetime(2017, 1, 1, 0, 0, 0, 0, _tz)
        p1 = TestIndividualPatternFactory(creation_date=long_ago)
        with mock.patch(
            "customfit.patterns.models.timezone",
            **{"now.return_value": before_nintey_days}
        ):
            self.assertTrue(p1.redo_possible())
        with mock.patch(
            "customfit.patterns.models.timezone",
            **{"now.return_value": after_nintey_days}
        ):
            self.assertFalse(p1.redo_possible())

        # Patterns made after the deadline-start should be possible 90 days after creation, but not later
        after_deadline = datetime.datetime(2020, 12, 31, 0, 0, 0, 0, _tz)
        before_nintey_days = datetime.datetime(2021, 3, 30, 23, 59, 59, 0, _tz)
        after_nintey_days = datetime.datetime(2021, 3, 31, 0, 0, 0, 1, _tz)
        p2 = TestIndividualPatternFactory(creation_date=after_deadline)
        with mock.patch(
            "customfit.patterns.models.timezone",
            **{"now.return_value": before_nintey_days}
        ):
            self.assertTrue(p2.redo_possible())
        with mock.patch(
            "customfit.patterns.models.timezone",
            **{"now.return_value": after_nintey_days}
        ):
            self.assertFalse(p2.redo_possible())

    def test_model_managers(self):
        """
        Verifies that the model managers return the expected types of patterns.
        """
        p_unapproved = TestIndividualPatternFactory()

        p_approved = TestApprovedIndividualPatternFactory()

        p_archived = TestApprovedIndividualPatternFactory(archived=True)

        self.assertIn(p_unapproved, TestIndividualPattern.objects.all())
        self.assertIn(p_approved, TestIndividualPattern.objects.all())
        self.assertIn(p_archived, TestIndividualPattern.objects.all())

        self.assertNotIn(p_unapproved, TestIndividualPattern.live_patterns.all())
        self.assertIn(p_approved, TestIndividualPattern.live_patterns.all())
        self.assertNotIn(p_archived, TestIndividualPattern.live_patterns.all())

        self.assertNotIn(p_unapproved, TestIndividualPattern.archived_patterns.all())
        self.assertNotIn(p_approved, TestIndividualPattern.archived_patterns.all())
        self.assertIn(p_archived, TestIndividualPattern.archived_patterns.all())

        self.assertNotIn(p_unapproved, TestIndividualPattern.approved_patterns.all())
        self.assertIn(p_approved, TestIndividualPattern.approved_patterns.all())
        self.assertIn(p_archived, TestIndividualPattern.approved_patterns.all())

        self.assertIn(p_unapproved, TestIndividualPattern.even_unapproved.all())
        self.assertIn(p_approved, TestIndividualPattern.even_unapproved.all())
        self.assertIn(p_archived, TestIndividualPattern.even_unapproved.all())


class GradedPatternTests(TestCase):

    def test_user(self):
        user = UserFactory()
        p = GradedTestPatternFactory(
            pieces__schematic__graded_garment_parameters__pattern_spec__user=user
        )
        self.assertEqual(p.user, user)


class PatternRendererTests(RendererTestCase):

    maxDiff = None

    def _render_pattern(self, **kwargs):
        des = DesignFactory(**kwargs)
        p = TestIndividualPatternFactory(
            pieces__schematic__individual_garment_parameters__pattern_spec__design_origin=des
        )
        html = p.render_pattern()
        html = self.normalize_html(html)
        return (html, p)

    def test_about_designer(self):

        designer = DesignerFactory(
            short_name="test designer",
            about_designer_long="long description",
            about_designer_short="short description",
        )
        (html, _) = self._render_pattern(designer=designer)
        goal_html = "<div><div><h2>About test designer</h2></div><div><p>long description</p></div></div>"
        self.assertIn(goal_html, html)

    def test_patterntext(self):
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_long="long description",
            about_designer_short="short description",
        )
        (html, p) = self._render_pattern(designer=designer)
        goal_html = (
            """
        <div>
        <div><h2>Your Notes</h2></div>
        <div><a href="/pattern/%s/note/" class='btn btn-customfit-outline'>add notes</a></div>
        </div>

        <div>
        <div><h2>Test Piece</h2></div>
        <div><p>Knit 2 over 2&quot;/5 cm.</p></div>
        </div>
        
        <div>
        <div><h2>About test designer</h2></div>
        <div><p>long description</p></div>
        </div>
        """
            % p.id
        )
        self.assertHTMLEqual(html, goal_html)


class GradedPatternRendererTests(RendererTestCase):

    maxDiff = None

    def _render_pattern(self, **kwargs):
        des = DesignFactory(**kwargs)
        p = GradedTestPatternFactory(
            pieces__schematic__graded_garment_parameters__pattern_spec__design_origin=des
        )
        html = p.render_pattern()
        html = self.normalize_html(html)
        return (html, p)

    def test_patterntext(self):
        designer = DesignerFactory(
            short_name="test designer",
            about_designer_long="long description",
            about_designer_short="short description",
        )
        (html, p) = self._render_pattern(designer=designer)
        goal_html = (
            """
        <div>
        <div><h2>Your Notes</h2></div>
        <div><a href="/pattern/%s/note/" class='btn btn-customfit-outline'>add notes</a></div>
        </div>

        <div>
        <div><h2>Test Piece</h2></div>
        <div><p>Knit 10 (11, 12, 13, 14) over 10 (11, 12, 13, 14)&quot;/25.5 (28, 30.5, 33, 35.5) cm.</p></div>
        </div>

        <div>
        <div><h2>About test designer</h2></div>
        <div><p>long description</p></div>
        </div>
        """
            % p.id
        )
        self.assertHTMLEqual(html, goal_html)


class StitchSectionTests(RendererTestCase):

    maxDiff = None

    def _make_renderer(self, stitch_list):

        # Need a Mock m such that m.get_spec_source().stitches_used() returns stitch_list
        inner_mock = mock.Mock(**{"stitches_used.return_value": stitch_list})
        outer_mock = mock.Mock(**{"get_spec_source.return_value": inner_mock})

        r = StitchesSectionRenderer(outer_mock)
        return r

    def _render_stitch_notes(self, stitch_list):
        r = self._make_renderer(stitch_list)
        html = r.render()
        return html

    def test_no_notes(self):
        no_note_stitch = StitchFactory(notes=None)
        stitch_list = [no_note_stitch]
        r = self._make_renderer(stitch_list)
        self.assertFalse(r)

    def test_with_notes(self):
        stitch1 = StitchFactory(name="front stitch", notes="front stitch notes")
        stitch2 = StitchFactory(name="back stitch", notes="back stitch notes")
        stitch3 = StitchFactory(notes=None)
        stitch_list = [stitch1, stitch2, stitch3]
        r = self._make_renderer(stitch_list)

        self.assertTrue(r)

        patterntext = self._render_stitch_notes(stitch_list)
        goal_patterntext = """<div><div><h2>Stitches</h2></div><div><p>front stitch notes</p>
                            <p>back stitch notes</p></div></div>"""
        self.assertHTMLEqual(patterntext, goal_patterntext)


class TestPatterntextViewCorrectness(TestCase):

    def setUp(self):
        super(TestPatterntextViewCorrectness, self).setUp()

        self.alice = UserFactory()
        self.alice.save()

        self.client = Client(HTTP_HOST="example.com")
        self.client.force_login(self.alice)

    # def tearDown(self):
    #     self.client.logout()
    #     # This will also delete objects FKed off of her in a cascade.
    #     self.alice.delete()
    #     super(TestPatterntextViewCorrectness, self).tearDown()

    def _make_pattern_from_pspec(self, pspec):
        return TestApprovedIndividualPatternFactory.from_pspec(pspec)

    def _view_pattern(self, **kwargs):
        des = DesignFactory(**kwargs)
        pspec = TestPatternSpecFactory(design_origin=des, user=self.alice)
        p = self._make_pattern_from_pspec(pspec)
        url = p.get_absolute_url()
        response = self.client.get(url)
        return response

    def test_designer_byline(self):

        # designer
        designer = DesignerFactory(
            full_name="test designer",
            about_designer_long="long description",
            about_designer_short="short description",
        )
        designer.save()
        with self.settings(ALLOWED_HOSTS=['example.com']):
            response = self._view_pattern(designer=designer)
        self.assertEqual(response.status_code, 200)
        goal_response = "<small>Design by test designer</small>"

        self.assertContains(response, goal_response, html=True)
        designer.delete()


class TestPatterntextPDFView(TestCase):

    maxDiff = None

    def setUp(self):
        super(TestPatterntextPDFView, self).setUp()

        # Elf is a CF staff member
        self.elf = StaffFactory()

        self.client = Client()
        self.client.force_login(self.elf)

    def tearDown(self):
        self.client.logout()
        # This will also delete objects FKed off of her in a cascade.
        self.elf.delete()
        super(TestPatterntextPDFView, self).tearDown()

    def _make_pattern_from_patternspec(self, pspec):
        return TestApprovedIndividualPatternFactory.from_pspec(pspec)

    def test_get_long_pdf(self):
        user = UserFactory()
        pspec = TestPatternSpecFactory(name="Pattern name")
        p = self._make_pattern_from_patternspec(pspec)

        pdf_url = reverse("patterns:individualpattern_pdf_view", args=(p.pk,))

        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="pattern-name-expanded.pdf"',
        )

        p.delete()
        pspec.delete()
        user.delete()

    def test_get_short_pdf(self):
        user = UserFactory()
        pspec = TestPatternSpecFactory(name="Pattern name")
        p = self._make_pattern_from_patternspec(pspec)

        short_pdf_url = reverse(
            "patterns:individualpattern_shortpdf_view", args=(p.pk,)
        )

        response = self.client.get(short_pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="pattern-name.pdf"'
        )

        p.delete()
        pspec.delete()
        user.delete()

    def test_get_both_pdf(self):
        user = UserFactory()
        five_hundred_foos = " ".join(itertools.repeat("foo", 500))
        pspec = TestPatternSpecFactory(
            name="Pattern Name", stitch1__notes=five_hundred_foos
        )
        p = self._make_pattern_from_patternspec(pspec)

        # Long PDF
        pdf_url = reverse("patterns:individualpattern_pdf_view", args=(p.pk,))
        long_pdf = self.client.get(pdf_url)
        self.assertEqual(long_pdf.status_code, 200)
        self.assertEqual(
            long_pdf["Content-Disposition"],
            'attachment; filename="pattern-name-expanded.pdf"',
        )

        # short PDF
        pdf_url = reverse("patterns:individualpattern_shortpdf_view", args=(p.pk,))
        short_pdf = self.client.get(pdf_url)
        self.assertEqual(short_pdf.status_code, 200)
        self.assertEqual(
            short_pdf["Content-Disposition"], 'attachment; filename="pattern-name.pdf"'
        )

        length_diff = len(long_pdf.content) - len(short_pdf.content)

        # Unfortunately, long_pdf will be longer than short_pdf even if they
        # have exactly the same patterntext: the long-pdf has a longer string
        # for the title. But their differences should be significant.
        # The full PDF should have three copies of the stitch section (see
        # customfit.patterns.renderers.test_renderers._PDFBaseMixinFull), and so should be at least
        # 500 * 2 bytes bigger. (By not len("foo") * 500 * 2? Because PDFs will assign a glyph to the string 'foo',
        # I think. In any case, it's a little over 1000 bytes bigger even when I look at the PDFs to confirm
        # the big PDF has three Stitch sections and the little one has one.)
        self.assertGreater(length_diff, 1000)

        p.delete()
        pspec.delete()
        user.delete()

    def test_missing_image(self):
        # Sanity check: make sure the dummy image does not really exist
        image_url = "http://example.com/nonesuch.jpg"
        with self.assertRaises(urllib.error.URLError):
            urllib.request.urlopen(image_url)

        # Test that the PDF renderer can survive a missing image
        # One easy way to test this is to make a design with an <img> tag
        # in the notes, then make a pattern with this stitch.
        img_tag = '<img src="http://example.com/nonesuch.jpg"/>'

        user = UserFactory()
        pspec = TestPatternSpecFactory(
            name="Pattern name", design_origin=DesignFactory(description=img_tag)
        )
        pspec.save()
        p = self._make_pattern_from_patternspec(pspec)

        # Double-check: the image-tag shows up in the patterntext, right?
        pattern_url = p.get_absolute_url()
        response = self.client.get(pattern_url)
        self.assertContains(response, img_tag)

        pdf_url = reverse("patterns:individualpattern_pdf_view", args=(p.pk,))

        # And now to test that the PDF rendering will not break
        response = self.client.get(pdf_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="pattern-name-expanded.pdf"',
        )

        p.delete()
        pspec.delete()

        user.delete()


class TestPatternArchives(TestCase):
    """Verifies that pattern archiving works."""

    def setUp(self):
        super(TestPatternArchives, self).setUp()

        # Elf is a logged-in CF user
        self.elf = StaffFactory()

        self.client = Client()
        self.client.force_login(self.elf)

        # Elf has a live and an archived pattern, both approved
        self.live_pattern = TestApprovedIndividualPatternFactory.for_user(user=self.elf)
        self.archived_pattern = TestArchivedIndividualPatternFactory.for_user(
            user=self.elf
        )

        self.archive_list_url = reverse("patterns:individualpattern_archive_view")
        self.archive_action_url = reverse(
            "patterns:individualpattern_archive_action", args=(self.live_pattern.pk,)
        )

    def tearDown(self):
        super(TestPatternArchives, self).tearDown()
        self.live_pattern.delete()
        self.archived_pattern.delete()
        self.elf.delete()

    def _get_live_pattern_archive(self):
        """
        This hits the archive URL for the live pattern (simulating the user's
        action to archive it). We use it a lot in this test, so it's factored
        out here.

        FUN FACT: when you create database objects in setUp(), it caches them,
        and you get the cached state even if your test does something to change
        it. Therefore if you just test for self.live_pattern.archived in the
        naive way, you will always get False, and all your tests of the
        archive functionality are subtly misleading! Good times.

        So you have to force-get an updated object, thusly.
        """
        _ = self.client.get(self.archive_action_url, follow=True)
        updated_pattern = IndividualPattern.approved_patterns.get(
            pk=self.live_pattern.pk
        )
        return updated_pattern

    def test_archives_list_renders(self):
        """
        User goes to the front page and it is rendered with
        IndividualPatternArchivesListView
        """
        found = resolve(self.archive_list_url)
        self.assertEqual(found.view_name, "patterns:individualpattern_archive_view")

    def test_archives_single_pattern_renders(self):
        """
        User goes to the detail page for the archived pattern and it renders
        as expected. That is, it should still be visible as normal
        because they have paid for it; we just don't display it in the main
        pattern list.
        """
        url = reverse(
            "patterns:individualpattern_detail_view", args=(self.archived_pattern.pk,)
        )
        response = self.client.get(url)
        self.assertContains(response, self.archived_pattern.name)

    def test_cannot_archive_nonexistent_pattern(self):
        """
        If we try to archive a pattern that doesn't exist, we 404.
        """
        not_a_pk = IndividualPattern.even_unapproved.all().order_by("-pk")[0].pk + 1
        url = reverse("patterns:individualpattern_archive_action", args=(not_a_pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_cannot_archive_unowned_pattern(self):
        """
        If we try to archive a pattern that belongs to someone else, we fail.
        """
        not_elf = UserFactory()

        self.client.logout()
        self.client.force_login(not_elf)

        response = self.client.get(self.archive_action_url)
        self.assertEqual(response.status_code, 403)

        updated_pattern = self._get_live_pattern_archive()

        self.assertFalse(updated_pattern.archived)

    def test_anons_cannot_archive(self):
        """
        If the anonymous user hits a pattern archive URL, the pattern is not
        archived.
        """
        self.client.logout()
        updated_pattern = self._get_live_pattern_archive()
        self.assertFalse(updated_pattern.archived)

    def test_archive_action_works(self):
        """
        Getting the archive action results in archiving the pattern.
        (Note that this assumes you're logged in and it's your pattern, as
        established in setUp() and tested for above.)
        """
        updated_pattern = self._get_live_pattern_archive()
        self.assertTrue(updated_pattern.archived)

    def test_archive_action_works_on_archived(self):
        """
        Getting the archive action on an archived pattern doesn't unarchive it.
        """
        archive_action_url = reverse(
            "patterns:individualpattern_archive_action",
            args=(self.archived_pattern.pk,),
        )
        self.client.get(archive_action_url)
        updated_pattern = IndividualPattern.approved_patterns.get(
            pk=self.archived_pattern.pk
        )
        self.assertTrue(updated_pattern.archived)

    def test_repeated_archiving_works(self):
        """
        Previously archived patterns can be unarchived and vice versa.
        """
        # Archive it
        updated_pattern = self._get_live_pattern_archive()

        # Unarchive it; make sure it's unarchived
        unarchive_action_url = reverse(
            "patterns:individualpattern_unarchive_action", args=(updated_pattern.pk,)
        )
        _ = self.client.get(unarchive_action_url, follow=True)
        updated_pattern = IndividualPattern.approved_patterns.get(pk=updated_pattern.pk)
        self.assertFalse(updated_pattern.archived)

        # Re-archive it; make sure it's archived
        archive_action_url = reverse(
            "patterns:individualpattern_archive_action", args=(updated_pattern.pk,)
        )
        _ = self.client.get(archive_action_url, follow=True)
        updated_pattern = IndividualPattern.approved_patterns.get(pk=updated_pattern.pk)
        self.assertTrue(updated_pattern.archived)

    def test_archived_patterns_not_in_pattern_list(self):
        """
        Verifies that archived patterns don't show up in the pattern list view.
        """
        self.archived_pattern.name = "Briet's Antelope"
        self.archived_pattern.save()

        url = reverse("patterns:individualpattern_list_view")
        response = self.client.get(url)
        self.assertNotContains(response, "Antelope")

    def test_archived_patterns_in_archives_list(self):
        """
        Verifies that archived patterns do show up in the archives list view.
        """
        self.archived_pattern.name = "Happy Fun Sweater Pattern"
        self.archived_pattern.save()

        response = self.client.get(self.archive_list_url)
        goal_html = "Happy Fun Sweater Pattern"
        self.assertContains(response, goal_html)


class TestPatternUnarchives(TestCase):
    """Verifies that pattern unarchiving works."""

    def setUp(self):
        super(TestPatternUnarchives, self).setUp()

        # Alice is a logged-in CF user
        self.alice = UserFactory()

        self.client = Client()
        self.client.force_login(self.alice)

        # Elf has a live and an archived pattern, both approved
        self.live_pattern = TestApprovedIndividualPatternFactory.for_user(
            user=self.alice
        )
        self.archived_pattern = TestArchivedIndividualPatternFactory.for_user(
            user=self.alice
        )
        assert self.archived_pattern.archived  # sanity check

        self.archive_list_url = reverse("patterns:individualpattern_archive_view")
        self.unarchive_action_url = reverse(
            "patterns:individualpattern_unarchive_action",
            args=(self.archived_pattern.pk,),
        )

    def _get_archived_pattern_unarchive(self):
        """
        See comment above on _get_live_pattern_archive.
        """
        _ = self.client.get(self.unarchive_action_url, follow=True)
        updated_pattern = IndividualPattern.approved_patterns.get(
            pk=self.archived_pattern.pk
        )
        return updated_pattern

    def test_cannot_unarchive_nonexistent_pattern(self):
        """
        If we try to unarchive a pattern that doesn't exist, we 404.
        """
        not_a_pk = IndividualPattern.objects.all().order_by("-pk")[0].pk + 1
        url = reverse("patterns:individualpattern_unarchive_action", args=(not_a_pk,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_cannot_unarchive_unowned_pattern(self):
        """
        If we try to unarchive a pattern that belongs to someone else, we fail.
        """
        not_alice = UserFactory()

        self.client.logout()
        self.client.force_login(not_alice)

        self.assertTrue(self.archived_pattern.archived)  # sanity check

        response = self.client.get(self.unarchive_action_url)
        self.assertEqual(response.status_code, 403)

        updated_pattern = self._get_archived_pattern_unarchive()

        self.assertTrue(updated_pattern.archived)

    def test_anons_cannot_unarchive(self):
        """
        If the anonymous user hits a pattern unarchive URL, the pattern is not
        unarchived.
        """
        self.client.logout()
        self.assertTrue(self.archived_pattern.archived)  # sanity check
        self.assertTrue(
            IndividualPattern.approved_patterns.filter(
                pk=self.archived_pattern.pk
            ).exists()
        )
        updated_pattern = self._get_archived_pattern_unarchive()
        self.assertTrue(updated_pattern.archived)

    def test_unarchive_action_works(self):
        """
        Getting the unarchive action results in unarchiving the pattern.
        (Note that this assumes you're logged in and it's your pattern, as
        established in setUp() and tested for above.)
        """
        updated_pattern = self._get_archived_pattern_unarchive()
        self.assertFalse(updated_pattern.archived)

    def test_unarchive_action_works_on_unarchived(self):
        """
        Getting the unarchive action on an unarchived pattern doesn't archive it.
        """
        self.assertFalse(self.live_pattern.archived)  # sanity check

        unarchive_action_url = reverse(
            "patterns:individualpattern_unarchive_action", args=(self.live_pattern.pk,)
        )
        self.client.get(unarchive_action_url)
        self.live_pattern.refresh_from_db()
        self.assertFalse(self.live_pattern.archived)

    def test_unarchived_patterns_not_in_archives_list(self):
        """
        Verifies that unarchived patterns don't show up in the pattern archive view.
        """
        self.live_pattern.name = "Briet's Antelope"
        self.live_pattern.save()

        url = reverse("patterns:individualpattern_archive_view")
        response = self.client.get(url)
        self.assertNotContains(response, "Briet's Antelope")


class IndividualPatternDetailViewTest(TestCase):

    def setUp(self):
        super(IndividualPatternDetailViewTest, self).setUp()
        self.user = UserFactory()
        self.approved_pattern = TestApprovedIndividualPatternFactory.for_user(
            user=self.user
        )
        self.approved_url = reverse(
            "patterns:individualpattern_detail_view", args=(self.approved_pattern.pk,)
        )
        self.unapproved_pattern = TestIndividualPatternFactory.for_user(user=self.user)
        # sanity check
        self.assertFalse(
            IndividualPattern.approved_patterns.filter(
                id=self.unapproved_pattern.id
            ).exists()
        )
        self.unapproved_url = reverse(
            "patterns:individualpattern_detail_view", args=(self.unapproved_pattern.pk,)
        )

    def tearDown(self):
        self.approved_pattern.delete()
        self.unapproved_pattern.delete()
        self.user.delete()
        super(IndividualPatternDetailViewTest, self).tearDown()

    def login(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 302)

    def test_expected_case(self):
        self.login()
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.approved_pattern.name)

    def test_archived(self):
        self.approved_pattern.archived = True
        self.approved_pattern.save()
        self.login()
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.approved_pattern.name)

    def test_unapproved(self):
        self.login()
        resp = self.client.get(self.unapproved_url)
        self.assertEqual(resp.status_code, 404)

    def test_unapproved_archived(self):
        self.unapproved_pattern.archived = True
        self.unapproved_pattern.save()
        self.login()
        resp = self.client.get(self.unapproved_url)
        self.assertEqual(resp.status_code, 404)

    def test_see_redo_button(self):
        # For this test, it's useful to fix exactly when the pattern was created
        _tz = pytz.timezone(settings.TIME_ZONE)
        creation_date = datetime.datetime(2020, 3, 3, 0, 0, 0, 0, _tz)
        self.approved_pattern.creation_date = creation_date
        self.approved_pattern.save()

        self.login()
        resp = self.client.get(self.approved_url)
        goal_url = reverse("design_wizard:redo_start", args=(self.approved_pattern.pk,))

        # 12 hours after creation
        twelve_hours = datetime.timedelta(0, 12 * 60 * 60)
        testdate = creation_date + twelve_hours
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            resp = self.client.get(self.approved_url)
        goal_html = (
            """<a href="%s" class="btn-customfit-outline btn-block">Redo this pattern <br/> <i>(89 days left)</i></a>"""
            % goal_url
        )
        self.assertContains(resp, goal_html, html=True)

        # 36 hours before expiry
        ninety_days = datetime.timedelta(90)
        testdate = (
            self.approved_pattern.creation_date + ninety_days - (3 * twelve_hours)
        )
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            resp = self.client.get(self.approved_url)
        goal_html = (
            """<a href="%s" class="btn-customfit-outline btn-block">Redo this pattern <br/> <i>(1 day left)</i></a>"""
            % goal_url
        )
        self.assertContains(resp, goal_html, html=True)

        # 12 hours before expiry
        testdate = self.approved_pattern.creation_date + ninety_days - twelve_hours
        with mock.patch(
            "customfit.patterns.models.timezone", **{"now.return_value": testdate}
        ):
            resp = self.client.get(self.approved_url)
        goal_html = (
            """<a href="%s" class="btn-customfit-outline btn-block">Redo this pattern <br/> <i>(last day!)</i></a>"""
            % goal_url
        )
        self.assertContains(resp, goal_html, html=True)

    def test_dont_see_redo_button(self):
        p = TestRedonePatternFactory.for_user(self.user)
        self.login()
        pattern_url = reverse("patterns:individualpattern_detail_view", args=(p.pk,))
        resp = self.client.get(pattern_url)
        goal_url = reverse("design_wizard:redo_start", args=(p.pk,))
        goal_html = (
            """<a href="%s" class="btn-customfit-outline btn-block">Redo this pattern</a>"""
            % goal_url
        )
        self.assertNotContains(resp, goal_html, html=True)


class IndividualPatternPDFViewTest(TestCase):

    def setUp(self):
        super(IndividualPatternPDFViewTest, self).setUp()
        self.user = UserFactory()
        self.approved_pattern = TestApprovedIndividualPatternFactory.for_user(
            user=self.user
        )
        self.approved_url = reverse(
            "patterns:individualpattern_pdf_view", args=(self.approved_pattern.pk,)
        )
        self.unapproved_pattern = TestIndividualPatternFactory.for_user(user=self.user)
        # sanity check
        self.assertFalse(
            IndividualPattern.approved_patterns.filter(
                id=self.unapproved_pattern.id
            ).exists()
        )
        self.unapproved_url = reverse(
            "patterns:individualpattern_pdf_view", args=(self.unapproved_pattern.pk,)
        )

    def tearDown(self):
        self.approved_pattern.delete()
        self.unapproved_pattern.delete()
        self.user.delete()
        super(IndividualPatternPDFViewTest, self).tearDown()

    def login(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 302)

    def test_expected_case(self):
        self.login()
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        goal_name = "%s-expanded.pdf" % (self.approved_pattern.name.replace(" ", "-"))
        self.assertEqual(
            resp["Content-Disposition"], 'attachment; filename="%s"' % goal_name
        )

    def test_archived(self):
        self.approved_pattern.archived = True
        self.approved_pattern.save()
        self.login()
        resp = self.client.get(self.approved_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        goal_name = "%s-expanded.pdf" % (self.approved_pattern.name.replace(" ", "-"))
        self.assertEqual(
            resp["Content-Disposition"], 'attachment; filename="%s"' % goal_name
        )

    def test_unapproved(self):
        self.login()
        resp = self.client.get(self.unapproved_url)
        self.assertEqual(resp.status_code, 404)

    def test_unapproved_archived(self):
        self.unapproved_pattern.archived = True
        self.unapproved_pattern.save()
        self.login()
        resp = self.client.get(self.unapproved_url)
        self.assertEqual(resp.status_code, 404)


class MyPatternsViewTest(TestCase):

    def setUp(self):
        super(MyPatternsViewTest, self).setUp()
        self.user = UserFactory()
        self.approved_pattern = TestApprovedIndividualPatternFactory.for_user(
            user=self.user
        )

        self.unapproved_pattern = TestIndividualPatternFactory.for_user(user=self.user)

        self.url = reverse("patterns:individualpattern_list_view")

        # sanity checks
        self.assertFalse(
            IndividualPattern.approved_patterns.filter(
                id=self.unapproved_pattern.id
            ).exists()
        )
        self.assertNotEqual(self.approved_pattern.name, self.unapproved_pattern.name)

    def login(self):
        self.client.force_login(self.user)

    def test_login_required(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    def test_expected_case(self):
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.approved_pattern.name)

    def test_archived(self):
        self.approved_pattern.archived = True
        self.approved_pattern.save()
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.approved_pattern.name)

    def test_unapproved(self):
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.unapproved_pattern.name)

    def test_unapproved_archived(self):
        self.unapproved_pattern.archived = True
        self.unapproved_pattern.save()
        self.login()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, self.unapproved_pattern.name)


class IndividualPatternNoteUpdateViewTests(TestCase):

    def setUp(self):
        super(IndividualPatternNoteUpdateViewTests, self).setUp()
        self.user = UserFactory()
        self.approved_pattern = TestApprovedIndividualPatternFactory.for_user(
            user=self.user
        )

        self.url = reverse(
            "patterns:individualpattern_note_update_view",
            kwargs={"pk": self.approved_pattern.pk},
        )

    def test_get(self):
        self.client.force_login(self.user)

        response = self.client.get(self.url)
        goal_html = "<h2>Edit note for %s</h2>" % self.approved_pattern.name
        self.assertContains(response, goal_html, html=True)

    def test_post(self):
        # sanity check
        self.client.force_login(self.user)
        self.approved_pattern.notes = "No note yet"
        self.approved_pattern.save()

        response = self.client.post(self.url, {"notes": "Let there be notes!"})
        self.assertRedirects(
            response,
            reverse(
                "patterns:individualpattern_detail_view",
                kwargs={"pk": self.approved_pattern.pk},
            ),
            fetch_redirect_response=False,
        )

        self.approved_pattern.refresh_from_db()
        self.assertEqual(self.approved_pattern.notes, "Let there be notes!")


class TemplateFilterTests(TestCase):

    def test_count_fmt(self):

        self.assertEqual(count_fmt(2), 2)
        self.assertEqual(count_fmt(2.0), 2)
        self.assertEqual(count_fmt([]), [])
        self.assertEqual(count_fmt([1]), 1)
        self.assertEqual(count_fmt([1, 2, 3, 4, 5, 6]), "1 (2, 3, 4, 5, 6)")
        self.assertEqual(count_fmt(CompoundResult([1])), 1)
        self.assertEqual(
            count_fmt(CompoundResult([1, 2, 3, 4, 5, 6])), "1 (2, 3, 4, 5, 6)"
        )
        self.assertEqual(
            count_fmt(
                CompoundResult(
                    [
                        1,
                        1,
                        1,
                        1,
                        1,
                        1,
                    ]
                )
            ),
            1,
        )
        self.assertEqual(count_fmt(CompoundResult([1.1, 1.1])), 1.1)
        self.assertEqual(count_fmt(CompoundResult([1])), 1)
        self.assertEqual(count_fmt(None), "-")
        self.assertEqual(count_fmt(CompoundResult([None])), "-")
        self.assertEqual(count_fmt(CompoundResult([None, None, None])), "-")
        self.assertEqual(count_fmt([1, None, 3, None, 5, 6]), "1 (-, 3, -, 5, 6)")
        self.assertEqual(
            count_fmt(CompoundResult([1, None, 3, None, 5, 6])), "1 (-, 3, -, 5, 6)"
        )
        self.assertEqual(
            count_fmt(
                CompoundResult(
                    [
                        1,
                        None,
                        1,
                        1,
                        None,
                        1,
                    ]
                )
            ),
            "1 (-, 1, 1, -, 1)",
        )

    def test_length_fmt(self):
        self.assertEqual(length_fmt(2), '2"/5 cm')
        self.assertEqual(length_fmt(2.0), '2"/5 cm')
        self.assertEqual(
            length_fmt([]), '[]"/[] cm'
        )  # weird, but we'll live with it for now
        self.assertEqual(length_fmt([2]), '2"/5 cm')
        self.assertEqual(
            length_fmt([1, 2, 3, 4, 5, 6]),
            '1 (2, 3, 4, 5, 6)"/2.5 (5, 7.5, 10, 12.5, 15) cm',
        )
        self.assertEqual(length_fmt(CompoundResult([2])), '2"/5 cm')
        self.assertEqual(
            length_fmt(CompoundResult([1, 2, 3, 4, 5, 6])),
            '1 (2, 3, 4, 5, 6)"/2.5 (5, 7.5, 10, 12.5, 15) cm',
        )
        self.assertEqual(
            length_fmt(
                CompoundResult(
                    [
                        1,
                        1,
                        1,
                        1,
                        1,
                        1,
                    ]
                )
            ),
            '1"/2.5 cm',
        )
        self.assertEqual(length_fmt(None), None)
        self.assertEqual(length_fmt(CompoundResult([None])), None)
        self.assertEqual(length_fmt(CompoundResult([None, None, None])), None)
        self.assertEqual(
            length_fmt([1, None, 3, None, 5, 6]),
            '1 (-, 3, -, 5, 6)"/2.5 (-, 7.5, -, 12.5, 15) cm',
        )
        self.assertEqual(
            length_fmt(CompoundResult([1, None, 3, None, 5, 6])),
            '1 (-, 3, -, 5, 6)"/2.5 (-, 7.5, -, 12.5, 15) cm',
        )
        self.assertEqual(
            length_fmt(
                CompoundResult(
                    [
                        1,
                        None,
                        1,
                        None,
                        1,
                        1,
                    ]
                )
            ),
            '1 (-, 1, -, 1, 1)"/2.5 (-, 2.5, -, 2.5, 2.5) cm',
        )

    def test_long_length_fmt(self):
        # write me
        self.assertEqual(length_long_fmt(2), "2 yd/2 m")
        self.assertEqual(length_long_fmt(2.0), "2 yd/2 m")
        self.assertEqual(
            length_long_fmt([]), "[] yd/[] m"
        )  # weird, but we'll live with it for now
        self.assertEqual(length_long_fmt([2]), "2 yd/2 m")
        self.assertEqual(
            length_long_fmt([1, 2, 3, 4, 5, 6]),
            "1 (2, 3, 4, 5, 6) yd/1 (2, 3, 4, 5, 5) m",
        )
        self.assertEqual(length_long_fmt(CompoundResult([2])), "2 yd/2 m")
        self.assertEqual(
            length_long_fmt(CompoundResult([1, 2, 3, 4, 5, 6])),
            "1 (2, 3, 4, 5, 6) yd/1 (2, 3, 4, 5, 5) m",
        )
        self.assertEqual(
            length_long_fmt(
                CompoundResult(
                    [
                        1,
                        1,
                        1,
                        1,
                        1,
                        1,
                    ]
                )
            ),
            "1 yd/1 m",
        )

    def test_percentage_match_parity(self):
        self.assertEqual(percentage_match_parity(100, 24), 24)
        self.assertEqual(percentage_match_parity(100, 25), 26)
        self.assertEqual(percentage_match_parity([], 25), [])
        self.assertEqual(percentage_match_parity([100], 25), 26)
        self.assertEqual(
            percentage_match_parity([100, 200, 300, 400, 500], 10),
            "10 (20, 30, 40, 50)",
        )
        self.assertEqual(percentage_match_parity(CompoundResult([100]), 25), 26)
        self.assertEqual(
            percentage_match_parity(CompoundResult([100, 200, 300, 400, 500]), 10),
            "10 (20, 30, 40, 50)",
        )

    def test_percentage_round_whole(self):
        self.assertEqual(percentage_round_whole(100, 10), 10)
        self.assertEqual(percentage_round_whole(99, 10), 10)
        self.assertEqual(percentage_round_whole([], 10), [])
        self.assertEqual(percentage_round_whole([100], 10), 10)
        self.assertEqual(
            percentage_round_whole([99, 201, 301, 401, 501], 10), "10 (20, 30, 40, 50)"
        )
        self.assertEqual(percentage_round_whole(CompoundResult([100]), 10), 10)
        self.assertEqual(
            percentage_round_whole(CompoundResult([99, 201, 301, 401, 501]), 10),
            "10 (20, 30, 40, 50)",
        )

    def test_divide_counts_by_gauge(self):
        self.assertEqual(divide_counts_by_gauge(100, 10), 10)
        self.assertEqual(divide_counts_by_gauge(99, 10), 9.9)
        self.assertEqual(divide_counts_by_gauge([], 10), [])
        self.assertEqual(divide_counts_by_gauge([100], 10), [10])
        self.assertEqual(
            divide_counts_by_gauge([100, 200, 300, 400, 501], 10),
            [10, 20, 30, 40, 50.1],
        )
        self.assertEqual(divide_counts_by_gauge(CompoundResult([100]), 10), [10])
        self.assertEqual(
            divide_counts_by_gauge(CompoundResult([99, 201, 301, 401, 500]), 10),
            [9.9, 20.1, 30.1, 40.1, 50],
        )

    def test_round_tag(self):
        self.assertEqual(round_tag(10, 10), 100)
        self.assertEqual(round_tag(9.9, 10), 99)
        self.assertEqual(round_tag([], 10), [])
        self.assertEqual(round_tag([9.9], 10), [99])
        self.assertEqual(round_tag([1.9, 2.9, 3.9, 4.9, 5.9], 10), [19, 29, 39, 49, 59])
        self.assertEqual(round_tag(CompoundResult([9.9]), 10), [99])
        self.assertEqual(
            round_tag(CompoundResult([1.9, 2.9, 3.9, 4.9, 5.9]), 10),
            [19, 29, 39, 49, 59],
        )

    def test_round_counts_tag(self):
        self.assertEqual(round_counts_tag(10, 10), 100)
        self.assertEqual(round_counts_tag(9.9, 10), 99)
        self.assertEqual(round_counts_tag([], 10), [])
        self.assertEqual(round_counts_tag([9.9], 10), 99)
        self.assertEqual(
            round_counts_tag([1.9, 2.9, 3.9, 4.9, 5.9], 10), "19 (29, 39, 49, 59)"
        )
        self.assertEqual(round_counts_tag(CompoundResult([9.9]), 10), 99)
        self.assertEqual(
            round_counts_tag(CompoundResult([1.9, 2.9, 3.9, 4.9, 5.9]), 10),
            "19 (29, 39, 49, 59)",
        )

    def test_round_lengths_tag(self):
        self.assertEqual(round_lengths_tag(10, 10), '100"/254 cm')
        self.assertEqual(round_lengths_tag(9.9, 10), '99"/251.5 cm')
        self.assertEqual(round_lengths_tag([], 10), '[]"/[] cm')
        self.assertEqual(round_lengths_tag([9.9], 10), '99"/251.5 cm')
        self.assertEqual(
            round_lengths_tag([1.9, 2.9, 3.9, 4.9, 5.9], 10),
            '19 (29, 39, 49, 59)"/48.5 (73.5, 99, 124.5, 150) cm',
        )
        self.assertEqual(round_lengths_tag(CompoundResult([9.9]), 10), '99"/251.5 cm')
        self.assertEqual(
            round_lengths_tag(CompoundResult([1.9, 2.9, 3.9, 4.9, 5.9]), 10),
            '19 (29, 39, 49, 59)"/48.5 (73.5, 99, 124.5, 150) cm',
        )

    def test_pluralize_counts(self):
        self.assertEqual(pluralize_counts(1), "")
        self.assertEqual(pluralize_counts(1.0), "")
        self.assertEqual(pluralize_counts("1"), "")
        self.assertEqual(pluralize_counts(CompoundResult([1, 1, 1])), "")
        self.assertEqual(pluralize_counts(CompoundResult([1, 1.0, 1])), "")

        self.assertEqual(pluralize_counts(1, "x,y"), "x")
        self.assertEqual(pluralize_counts(1.0, "x,y"), "x")
        self.assertEqual(pluralize_counts("1", "x,y"), "x")
        self.assertEqual(pluralize_counts(CompoundResult([1, 1, 1]), "x,y"), "x")
        self.assertEqual(pluralize_counts(CompoundResult([1, 1.0, 1]), "x,y"), "x")

        self.assertEqual(pluralize_counts(2), "s")
        self.assertEqual(pluralize_counts(2.0), "s")
        self.assertEqual(pluralize_counts("2"), "s")
        self.assertEqual(pluralize_counts(CompoundResult([1, 2, 1])), "s")

        self.assertEqual(pluralize_counts(2, "x,y"), "y")
        self.assertEqual(pluralize_counts(2.0, "x,y"), "y")
        self.assertEqual(pluralize_counts("2", "x,y"), "y")
        self.assertEqual(pluralize_counts(CompoundResult([1, 1, 2]), "x,y"), "y")
