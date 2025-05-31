"""
Created on Jul 3, 2012
"""

# import test_common
import django.test
from django.template import Context, Template
from django.test import TestCase

from customfit.helpers.math_helpers import CallableCompoundResult, CompoundResult

from ..math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    _find_best_approximation,
    cm_to_inches,
    grams_to_ounces,
    inches_to_cm,
    is_even,
    ounces_to_grams,
    round,
)


class MathHelpersTestCase(django.test.TestCase):

    def test_metric_1(self):
        i = inches_to_cm(1)
        self.assertEqual(i, 2.54)

    def test_metric_2(self):
        i = cm_to_inches(1)
        self.assertAlmostEqual(i, 0.393700787)

    def test_metric_3(self):
        i = cm_to_inches(inches_to_cm(1))
        self.assertAlmostEqual(i, 1)

    def test_metric_4(self):
        i = inches_to_cm(cm_to_inches(1))
        self.assertAlmostEqual(i, 1)

    def test_is_even(self):
        self.assertTrue(is_even(2))
        self.assertTrue(is_even(0))
        self.assertTrue(is_even(-2))
        self.assertFalse(is_even(-1))
        self.assertFalse(is_even(1))
        self.assertFalse(is_even(0.5))
        self.assertFalse(is_even(-0.5))

    def test_round(self):
        self.assertEqual(round(0.75), 1)
        self.assertEqual(round(0.25), 0)
        self.assertEqual(round(0), 0)
        self.assertEqual(round(1), 1)
        self.assertEqual(round(0.75, ROUND_DOWN), 0)
        self.assertEqual(round(0.25, ROUND_DOWN), 0)
        self.assertEqual(round(0, ROUND_DOWN), 0)
        self.assertEqual(round(1, ROUND_DOWN), 1)
        self.assertEqual(round(0.75, ROUND_UP), 1)
        self.assertEqual(round(0.25, ROUND_UP), 1)
        self.assertEqual(round(0, ROUND_UP), 0)
        self.assertEqual(round(1, ROUND_UP), 1)

        self.assertEqual(round(2.1, multiple=3), 3)
        self.assertEqual(round(2.1, direction=ROUND_ANY_DIRECTION, multiple=3), 3)
        self.assertEqual(round(2.1, direction=ROUND_UP, multiple=3), 3)
        self.assertEqual(round(2.1, direction=ROUND_DOWN, multiple=3), 0)

        self.assertEqual(round(2.1, multiple=5, mod=2), 2)
        self.assertEqual(
            round(2.1, direction=ROUND_ANY_DIRECTION, multiple=5, mod=2), 2
        )
        self.assertEqual(round(2.1, direction=ROUND_UP, multiple=5, mod=2), 7)
        self.assertEqual(round(2.1, direction=ROUND_DOWN, multiple=5, mod=2), 2)

        self.assertEqual(round(6.1, multiple=5, mod=2), 7)
        self.assertEqual(
            round(6.1, direction=ROUND_ANY_DIRECTION, multiple=5, mod=2), 7
        )
        self.assertEqual(round(6.1, direction=ROUND_UP, multiple=5, mod=2), 7)
        self.assertEqual(round(6.1, direction=ROUND_DOWN, multiple=5, mod=2), 2)

    def test_integers_1(self):
        for orig in [-1, 0, 1]:
            for d in [ROUND_UP, ROUND_ANY_DIRECTION, ROUND_DOWN]:
                result = round(orig, d)
                msg = (
                    "apparently round("
                    + str(orig)
                    + ", "
                    + str(d)
                    + ") is "
                    + str(result)
                )
                self.assertEqual(result, orig, msg)

    def test_integers_2(self):
        for orig in [-1, 0, 1]:
            result = round(orig)
            msg = "apparently round_helper(" + str(orig) + ") is " + str(result)
            self.assertEqual(result, orig, msg)

    def test_floats1(self):
        self.assertEqual(round(1.1), 1)
        self.assertEqual(round(0.1), 0)
        self.assertEqual(round(1.9), 2)
        self.assertEqual(round(0.9), 1)
        self.assertEqual(round(-1.9), -2)
        self.assertEqual(round(-0.01), 0)

    def test_floats_up(self):
        self.assertEqual(round(0.1, ROUND_UP), 1)
        self.assertEqual(round(0.9, ROUND_UP), 1)
        self.assertEqual(round(1.1, ROUND_UP), 2)
        self.assertEqual(round(-0.1, ROUND_UP), 0)
        self.assertEqual(round(-1.9, ROUND_UP), -1)

    def test_floats_down(self):
        self.assertEqual(round(0.1, ROUND_DOWN), 0)
        self.assertEqual(round(0.9, ROUND_DOWN), 0)
        self.assertEqual(round(1.1, ROUND_DOWN), 1)
        self.assertEqual(round(-0.1, ROUND_DOWN), -1)
        self.assertEqual(round(-1.9, ROUND_DOWN), -2)

    def test_floats_any(self):
        self.assertEqual(round(0.1, ROUND_ANY_DIRECTION), 0)
        self.assertEqual(round(0.9, ROUND_ANY_DIRECTION), 1)
        self.assertEqual(round(1.1, ROUND_ANY_DIRECTION), 1)
        self.assertEqual(round(-0.1, ROUND_ANY_DIRECTION), 0)
        self.assertEqual(round(-1.9, ROUND_ANY_DIRECTION), -2)

        # Note: the following asymmetrires are OK
        self.assertEqual(round(0.5, ROUND_ANY_DIRECTION), 1)
        self.assertEqual(round(-0.5, ROUND_ANY_DIRECTION), 0)

    def test_mult(self):
        self.assertEqual(round(-5, multiple=5), -5)
        self.assertEqual(round(-4, multiple=5), -5)
        self.assertEqual(round(-3, multiple=5), -5)
        self.assertEqual(round(-2, multiple=5), 0)
        self.assertEqual(round(-1, multiple=5), 0)
        self.assertEqual(round(0, multiple=5), 0)
        self.assertEqual(round(1, multiple=5), 0)
        self.assertEqual(round(2, multiple=5), 0)
        self.assertEqual(round(3, multiple=5), 5)
        self.assertEqual(round(4, multiple=5), 5)
        self.assertEqual(round(5, multiple=5), 5)
        self.assertEqual(round(6, multiple=5), 5)
        self.assertEqual(round(7, multiple=5), 5)
        self.assertEqual(round(8, multiple=5), 10)
        self.assertEqual(round(9, multiple=5), 10)
        self.assertEqual(round(10, multiple=5), 10)

    def test_mult_any(self):
        self.assertEqual(round(-5, ROUND_ANY_DIRECTION, 5), -5)
        self.assertEqual(round(-4, ROUND_ANY_DIRECTION, 5), -5)
        self.assertEqual(round(-3, ROUND_ANY_DIRECTION, multiple=5), -5)
        self.assertEqual(round(-2, ROUND_ANY_DIRECTION, multiple=5), 0)
        self.assertEqual(round(-1, ROUND_ANY_DIRECTION, multiple=5), 0)
        self.assertEqual(round(0, ROUND_ANY_DIRECTION, multiple=5), 0)
        self.assertEqual(round(1, ROUND_ANY_DIRECTION, multiple=5), 0)
        self.assertEqual(round(2, ROUND_ANY_DIRECTION, multiple=5), 0)
        self.assertEqual(round(3, ROUND_ANY_DIRECTION, multiple=5), 5)
        self.assertEqual(round(4, ROUND_ANY_DIRECTION, multiple=5), 5)
        self.assertEqual(round(5, ROUND_ANY_DIRECTION, multiple=5), 5)
        self.assertEqual(round(6, ROUND_ANY_DIRECTION, multiple=5), 5)
        self.assertEqual(round(7, ROUND_ANY_DIRECTION, multiple=5), 5)
        self.assertEqual(round(8, ROUND_ANY_DIRECTION, multiple=5), 10)
        self.assertEqual(round(9, ROUND_ANY_DIRECTION, multiple=5), 10)
        self.assertEqual(round(10, ROUND_ANY_DIRECTION, multiple=5), 10)

    def test_mult_up(self):
        self.assertEqual(round(-5, ROUND_UP, 5), -5)
        self.assertEqual(round(-4, ROUND_UP, 5), 0)
        self.assertEqual(round(-3, ROUND_UP, multiple=5), 0)
        self.assertEqual(round(-2, ROUND_UP, multiple=5), 0)
        self.assertEqual(round(-1, ROUND_UP, multiple=5), 0)
        self.assertEqual(round(0, ROUND_UP, multiple=5), 0)
        self.assertEqual(round(1, ROUND_UP, multiple=5), 5)
        self.assertEqual(round(2, ROUND_UP, multiple=5), 5)
        self.assertEqual(round(3, ROUND_UP, multiple=5), 5)
        self.assertEqual(round(4, ROUND_UP, multiple=5), 5)
        self.assertEqual(round(5, ROUND_UP, multiple=5), 5)
        self.assertEqual(round(6, ROUND_UP, multiple=5), 10)
        self.assertEqual(round(7, ROUND_UP, multiple=5), 10)
        self.assertEqual(round(8, ROUND_UP, multiple=5), 10)
        self.assertEqual(round(9, ROUND_UP, multiple=5), 10)
        self.assertEqual(round(10, ROUND_UP, multiple=5), 10)

    def test_mult_down(self):
        self.assertEqual(round(-5, ROUND_DOWN, 5), -5)
        self.assertEqual(round(-4, ROUND_DOWN, 5), -5)
        self.assertEqual(round(-3, ROUND_DOWN, multiple=5), -5)
        self.assertEqual(round(-2, ROUND_DOWN, multiple=5), -5)
        self.assertEqual(round(-1, ROUND_DOWN, multiple=5), -5)
        self.assertEqual(round(0, ROUND_DOWN, multiple=5), 0)
        self.assertEqual(round(1, ROUND_DOWN, multiple=5), 0)
        self.assertEqual(round(2, ROUND_DOWN, multiple=5), 0)
        self.assertEqual(round(3, ROUND_DOWN, multiple=5), 0)
        self.assertEqual(round(4, ROUND_DOWN, multiple=5), 0)
        self.assertEqual(round(5, ROUND_DOWN, multiple=5), 5)
        self.assertEqual(round(6, ROUND_DOWN, multiple=5), 5)
        self.assertEqual(round(7, ROUND_DOWN, multiple=5), 5)
        self.assertEqual(round(8, ROUND_DOWN, multiple=5), 5)
        self.assertEqual(round(9, ROUND_DOWN, multiple=5), 5)
        self.assertEqual(round(10, ROUND_DOWN, multiple=5), 10)

    def test_mult_mod(self):
        self.assertEqual(round(-5, multiple=5, mod=3), -7)
        self.assertEqual(round(-4, multiple=5, mod=3), -2)
        self.assertEqual(round(-3, multiple=5, mod=3), -2)
        self.assertEqual(round(-2, multiple=5, mod=3), -2)
        self.assertEqual(round(-1, multiple=5, mod=3), -2)
        self.assertEqual(round(0, multiple=5, mod=3), -2)
        self.assertEqual(round(1, multiple=5, mod=3), 3)
        self.assertEqual(round(2, multiple=5, mod=3), 3)
        self.assertEqual(round(3, multiple=5, mod=3), 3)
        self.assertEqual(round(4, multiple=5, mod=3), 3)
        self.assertEqual(round(5, multiple=5, mod=3), 3)
        self.assertEqual(round(6, multiple=5, mod=3), 8)
        self.assertEqual(round(7, multiple=5, mod=3), 8)
        self.assertEqual(round(8, multiple=5, mod=3), 8)
        self.assertEqual(round(9, multiple=5, mod=3), 8)
        self.assertEqual(round(10, multiple=5, mod=3), 8)

    def test_mult_mod_any(self):
        self.assertEqual(round(-5, ROUND_ANY_DIRECTION, multiple=5, mod=3), -7)
        self.assertEqual(round(-4, ROUND_ANY_DIRECTION, multiple=5, mod=3), -2)
        self.assertEqual(round(-3, ROUND_ANY_DIRECTION, multiple=5, mod=3), -2)
        self.assertEqual(round(-2, ROUND_ANY_DIRECTION, multiple=5, mod=3), -2)
        self.assertEqual(round(-1, ROUND_ANY_DIRECTION, multiple=5, mod=3), -2)
        self.assertEqual(round(0, ROUND_ANY_DIRECTION, multiple=5, mod=3), -2)
        self.assertEqual(round(1, ROUND_ANY_DIRECTION, multiple=5, mod=3), 3)
        self.assertEqual(round(2, ROUND_ANY_DIRECTION, multiple=5, mod=3), 3)
        self.assertEqual(round(3, ROUND_ANY_DIRECTION, multiple=5, mod=3), 3)
        self.assertEqual(round(4, ROUND_ANY_DIRECTION, multiple=5, mod=3), 3)
        self.assertEqual(round(5, ROUND_ANY_DIRECTION, multiple=5, mod=3), 3)
        self.assertEqual(round(6, ROUND_ANY_DIRECTION, multiple=5, mod=3), 8)
        self.assertEqual(round(7, ROUND_ANY_DIRECTION, multiple=5, mod=3), 8)
        self.assertEqual(round(8, ROUND_ANY_DIRECTION, multiple=5, mod=3), 8)
        self.assertEqual(round(9, ROUND_ANY_DIRECTION, multiple=5, mod=3), 8)
        self.assertEqual(round(10, ROUND_ANY_DIRECTION, multiple=5, mod=3), 8)

    def test_mult_mod_up(self):
        self.assertEqual(round(-5, ROUND_UP, multiple=5, mod=3), -2)
        self.assertEqual(round(-4, ROUND_UP, multiple=5, mod=3), -2)
        self.assertEqual(round(-3, ROUND_UP, multiple=5, mod=3), -2)
        self.assertEqual(round(-2, ROUND_UP, multiple=5, mod=3), -2)
        self.assertEqual(round(-1, ROUND_UP, multiple=5, mod=3), 3)
        self.assertEqual(round(0, ROUND_UP, multiple=5, mod=3), 3)
        self.assertEqual(round(1, ROUND_UP, multiple=5, mod=3), 3)
        self.assertEqual(round(2, ROUND_UP, multiple=5, mod=3), 3)
        self.assertEqual(round(3, ROUND_UP, multiple=5, mod=3), 3)
        self.assertEqual(round(4, ROUND_UP, multiple=5, mod=3), 8)
        self.assertEqual(round(5, ROUND_UP, multiple=5, mod=3), 8)
        self.assertEqual(round(6, ROUND_UP, multiple=5, mod=3), 8)
        self.assertEqual(round(7, ROUND_UP, multiple=5, mod=3), 8)
        self.assertEqual(round(8, ROUND_UP, multiple=5, mod=3), 8)
        self.assertEqual(round(9, ROUND_UP, multiple=5, mod=3), 13)
        self.assertEqual(round(10, ROUND_UP, multiple=5, mod=3), 13)

    def test_mult_mod_down(self):
        self.assertEqual(round(-5, ROUND_DOWN, multiple=5, mod=3), -7)
        self.assertEqual(round(-4, ROUND_DOWN, multiple=5, mod=3), -7)
        self.assertEqual(round(-3, ROUND_DOWN, multiple=5, mod=3), -7)
        self.assertEqual(round(-2, ROUND_DOWN, multiple=5, mod=3), -2)
        self.assertEqual(round(-1, ROUND_DOWN, multiple=5, mod=3), -2)
        self.assertEqual(round(0, ROUND_DOWN, multiple=5, mod=3), -2)
        self.assertEqual(round(1, ROUND_DOWN, multiple=5, mod=3), -2)
        self.assertEqual(round(2, ROUND_DOWN, multiple=5, mod=3), -2)
        self.assertEqual(round(3, ROUND_DOWN, multiple=5, mod=3), 3)
        self.assertEqual(round(4, ROUND_DOWN, multiple=5, mod=3), 3)
        self.assertEqual(round(5, ROUND_DOWN, multiple=5, mod=3), 3)
        self.assertEqual(round(6, ROUND_DOWN, multiple=5, mod=3), 3)
        self.assertEqual(round(7, ROUND_DOWN, multiple=5, mod=3), 3)
        self.assertEqual(round(8, ROUND_DOWN, multiple=5, mod=3), 8)
        self.assertEqual(round(9, ROUND_DOWN, multiple=5, mod=3), 8)
        self.assertEqual(round(10, ROUND_DOWN, multiple=5, mod=3), 8)

    def test_mult_mod2(self):
        self.assertEqual(round(-5, multiple=4, mod=2), -6)
        self.assertEqual(round(-4, multiple=4, mod=2), -2)
        self.assertEqual(round(-3, multiple=4, mod=2), -2)
        self.assertEqual(round(-2, multiple=4, mod=2), -2)
        self.assertEqual(round(-1, multiple=4, mod=2), -2)
        self.assertEqual(round(0, multiple=4, mod=2), 2)
        self.assertEqual(round(1, multiple=4, mod=2), 2)
        self.assertEqual(round(2, multiple=4, mod=2), 2)
        self.assertEqual(round(3, multiple=4, mod=2), 2)
        self.assertEqual(round(4, multiple=4, mod=2), 6)
        self.assertEqual(round(5, multiple=4, mod=2), 6)
        self.assertEqual(round(6, multiple=4, mod=2), 6)
        self.assertEqual(round(7, multiple=4, mod=2), 6)
        self.assertEqual(round(8, multiple=4, mod=2), 10)
        self.assertEqual(round(9, multiple=4, mod=2), 10)
        self.assertEqual(round(10, multiple=4, mod=2), 10)

    def test_floats_2(self):
        self.assertEqual(round(-2, multiple=2.5, mod=0.25), -2.25)
        self.assertEqual(round(-1.66, multiple=2.5, mod=0.25), -2.25)
        self.assertEqual(round(-1.33, multiple=2.5, mod=0.25), -2.25)
        self.assertEqual(round(-1, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(-0.66, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(-0.33, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(0, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(0.33, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(0.66, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(1, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(1.33, multiple=2.5, mod=0.25), 0.25)
        self.assertEqual(round(1.66, multiple=2.5, mod=0.25), 2.75)
        self.assertEqual(round(2, multiple=2.5, mod=0.25), 2.75)
        self.assertEqual(round(2.33, multiple=2.5, mod=0.25), 2.75)
        self.assertEqual(round(2.66, multiple=2.5, mod=0.25), 2.75)
        self.assertEqual(round(3, multiple=2.5, mod=0.25), 2.75)

    def test_floats_3(self):
        self.assertEqual(round(-2, multiple=0.5), -2)
        self.assertEqual(round(-1.66, multiple=0.5), -1.5)
        self.assertEqual(round(-1.33, multiple=0.5), -1.5)
        self.assertEqual(round(-1, multiple=0.5), -1)
        self.assertEqual(round(-1.1, multiple=0.5), -1)
        self.assertEqual(round(-0.66, multiple=0.5), -0.5)
        self.assertEqual(round(-0.33, multiple=0.5), -0.5)
        self.assertEqual(round(0, multiple=0.5), 0)
        self.assertEqual(round(0.33, multiple=0.5), 0.5)
        self.assertEqual(round(0.66, multiple=0.5), 0.5)
        self.assertEqual(round(1.1, multiple=0.5), 1)
        self.assertEqual(round(1.33, multiple=0.5), 1.5)
        self.assertEqual(round(1.66, multiple=0.5), 1.5)
        self.assertEqual(round(2, multiple=0.5), 2)
        self.assertEqual(round(2.33, multiple=0.5), 2.5)
        self.assertEqual(round(2.66, multiple=0.5), 2.5)
        self.assertEqual(round(3, multiple=0.5), 3)

    def test_best_approx_1(self):
        r = _find_best_approximation(1, 4, ROUND_ANY_DIRECTION, -1)
        self.assertEqual(r, 4)

    def test_best_approx_2(self):
        r = _find_best_approximation(0.8, 4, ROUND_ANY_DIRECTION, -1)
        self.assertEqual(r, 3)

    def test_best_approx_3(self):
        r = _find_best_approximation(0.8, 2, ROUND_DOWN, -1)
        self.assertEqual(r, 1)

    def test_best_approx_4(self):
        r = _find_best_approximation(0.8, 2, ROUND_DOWN, -0.25)
        self.assertEqual(r, 2)

    def test_best_approx_5(self):
        r = _find_best_approximation(10, 3, ROUND_DOWN, -1, 0, 4)
        self.assertEqual(r, 28)

    def test_best_approx_6(self):
        r = _find_best_approximation(10, 3, ROUND_DOWN, -0.5, 0, 4)
        self.assertEqual(r, 32)

    def test_best_approx_7(self):
        r = _find_best_approximation(10, 3, ROUND_UP, -0.5, 1, 4)
        self.assertEqual(r, 33)

    def test_best_approx(self):
        self.longMessage = True
        self.maxDiff = None
        error_cases = []
        for x_mod in range(0, 10):
            for mod_y in range(1, 10):
                r = _find_best_approximation(
                    10, 3, ROUND_ANY_DIRECTION, 0, x_mod, mod_y
                )
                if (r - x_mod) % mod_y != 0:
                    error_cases += [(x_mod, mod_y, r)]

        self.assertEqual(error_cases, [])

    def test_oz_and_grams(self):
        oz = 7
        g = ounces_to_grams(oz)
        self.assertAlmostEqual(g, 198.447, 3)

        oz = 7.5
        g = ounces_to_grams(oz)
        self.assertAlmostEqual(g, 212.621, 3)

        oz = 0
        g = ounces_to_grams(oz)
        self.assertEqual(g, 0)

        g = 7
        oz = grams_to_ounces(g)
        self.assertAlmostEqual(oz, 0.246918, 6)

        g = 7.5
        oz = grams_to_ounces(g)
        self.assertAlmostEqual(oz, 0.264555, 6)

        g = 0
        oz = grams_to_ounces(g)
        self.assertEqual(oz, 0)


class CompoundResultTests(TestCase):

    def test_bool(self):
        cr = CompoundResult(range(1, 5))
        self.assertTrue(cr)

        cr = CompoundResult([False, False, False])
        self.assertFalse(cr)

        cr = CompoundResult([True, True, True])
        self.assertTrue(cr)

        cr = CompoundResult([True, False, True])
        with self.assertRaises(AssertionError):
            bool(cr)

        cr = CompoundResult(range(5))  # contains 0
        with self.assertRaises(AssertionError):
            bool(cr)

        cr = CompoundResult([])
        self.assertFalse(cr)

    def test_list(self):
        cr = CompoundResult([1, 2, 3])
        l = [x for x in cr]
        self.assertEqual(l, [1, 2, 3])

    # The whole point is to be dropped in as a value in a template context. So let's test them.
    # Note: length_fmt, count_fmt, etc. are tested in TemplateFilterTests, below

    def test_template_var(self):
        template_str = "{{ l }}"
        context_dict = {"l": CompoundResult([1, 2, 3])}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "[1, 2, 3]")

    def test_template_if(self):
        template_str = "{% if l %}foo{% else %}bar{% endif %}"
        context_dict = {"l": CompoundResult([True, [1], 1])}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "foo")

        template_str = "{% if l %}foo{% else %}bar{% endif %}"
        context_dict = {"l": CompoundResult([False, 0, []])}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "bar")

    def test_template_for(self):
        # Just to establish that it acts like a list here
        template_str = "{% for x in l %}{{x}} {% endfor %}"
        context_dict = {"l": CompoundResult([1, 2, 3])}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "1 2 3 ")

    def test_operators(self):
        cr1 = CompoundResult([1, 2, 3])
        cr2 = CompoundResult([2, 4, 6])

        self.assertEqual(cr1 + cr2, CompoundResult([3, 6, 9]))
        self.assertEqual(cr1 + 5, CompoundResult([6, 7, 8]))

        self.assertEqual(cr2 - cr1, CompoundResult([1, 2, 3]))
        self.assertEqual(cr2 - 1, CompoundResult([1, 3, 5]))

        self.assertEqual(cr2 * cr1, CompoundResult([2, 8, 18]))
        self.assertEqual(cr2 * 3, CompoundResult([6, 12, 18]))

        self.assertEqual(cr2 / cr1, CompoundResult([2, 2, 2]))
        self.assertEqual(cr2 / 2, CompoundResult([1, 2, 3]))

    def test_not_callable(self):
        cr = CompoundResult([1, 2, 3])
        self.assertFalse(callable(cr))
        with self.assertRaises(TypeError):
            cr()

    def test_str(self):
        test_vectors = [
            ([1], "1"),
            ([1, 1, 1], "1"),
            ([1, 2, 3], "[1, 2, 3]"),
            ([1, 1.0, 1], "1"),
        ]
        for l, goal_s in test_vectors:
            with self.subTest(l=l, goal_s=goal_s):
                s = str(CompoundResult(l))
                self.assertEqual(s, goal_s)

    def test_displayable(self):
        test_vectors = [
            ([1, 2, 3], True),
            ([0, 2, 3], True),
            ([0, 0, 0], False),
            ([-1, 2, 3], False),
            ([None, 2, 3], False),
            (
                [
                    1,
                ],
                True,
            ),
            ([0], False),
            ([-1], False),
            ([None], False),
        ]
        for l, goal in test_vectors:
            with self.subTest(l=l, goal_s=goal):
                s = CompoundResult(l).displayable()
                self.assertEqual(s, goal)

    def test_eq(self):
        cr1 = CompoundResult([1, 2, 3, 4, 5])
        cr2 = CompoundResult([1, 2, 3, 4, 5])
        self.assertEqual(cr1, cr2)

        cr3 = CompoundResult([1, 2, 3, 4])
        cr4 = CompoundResult([2, 3, 4, 5, 6])

        for cr in [cr3, cr4]:
            self.assertNotEqual(cr1, cr)


class CallableCompoundListTests(TestCase):

    def test_bool(self):
        f = lambda: 1
        self.assertTrue(callable(f))  # sanity check
        self.assertEqual(f(), 1)  # sanity check

        cr = CallableCompoundResult([f, f, f])
        self.assertTrue(cr)

        cr = CallableCompoundResult([])
        self.assertFalse(cr)

    def test_list(self):
        f = lambda: 1
        cr = CallableCompoundResult([f, f, f])
        l = [x() for x in cr]
        self.assertEqual(l, [1, 1, 1])

    # The whole point is to be dropped in as a value in a template context. So let's test them.
    # Note: length_fmt, count_fmt, etc. are tested in TemplateFilterTests, below

    def test_template_var(self):
        f = lambda: 1
        cr = CallableCompoundResult([f, f, f])
        template_str = "{{ l }}"
        context_dict = {"l": cr}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "1")  # due to the __str__ in CompoundResult

    def test_template_var2(self):
        f1 = lambda: 1
        f2 = lambda: 2
        f3 = lambda: 3
        cr = CallableCompoundResult([f1, f2, f3])
        template_str = "{{ l }}"
        context_dict = {"l": cr}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "[1, 2, 3]")  # due to the __str__ in CompoundResult

    def test_template_if(self):
        f = lambda: 1
        cr = CallableCompoundResult([f, f, f])
        template_str = "{% if l %}foo{% else %}bar{% endif %}"
        context_dict = {"l": cr}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "foo")

        f = lambda: False
        cr = CallableCompoundResult([f, f, f])
        template_str = "{% if l %}foo{% else %}bar{% endif %}"
        context_dict = {"l": cr}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "bar")

    def test_template_for(self):
        # Just to establish that it acts like a list here
        f = lambda: 1
        cr = CallableCompoundResult([f, f, f])
        template_str = "{% for x in l %}{{x}} {% endfor %}"
        context_dict = {"l": cr}

        template = Template(template_str)
        context = Context(context_dict)
        output = template.render(context)

        self.assertEqual(output, "1 1 1 ")

    def test_callable1(self):
        f = lambda: 1
        self.assertTrue(callable(f))  # sanity check
        self.assertEqual(f(), 1)  # sanity check

        cr = CallableCompoundResult([f, f, f])
        self.assertTrue(callable(cr))
        self.assertIsInstance(cr(), CompoundResult)
        self.assertEqual(cr(), [1, 1, 1])

    def test_callable2(self):
        f = lambda x: x + 1
        self.assertTrue(callable(f))  # sanity check
        self.assertEqual(f(1), 2)  # sanity check

        cr = CallableCompoundResult([f, f, f])
        self.assertTrue(callable(cr))
        self.assertIsInstance(cr(1), CompoundResult)
        self.assertEqual(cr(1), [2, 2, 2])

    def test_callable2(self):
        def f(x, y, z=3):
            return (x * y) + z

        self.assertTrue(callable(f))  # sanity check
        self.assertEqual(f(1, 2), 5)  # sanity check
        self.assertEqual(f(1, 2, 4), 6)  # sanity check
        self.assertEqual(f(1, 2, z=4), 6)  # sanity check

        cr = CallableCompoundResult([f, f, f])
        self.assertTrue(callable(cr))

        self.assertIsInstance(cr(1, 2), CompoundResult)
        self.assertEqual(cr(1, 2), [5, 5, 5])

        self.assertIsInstance(cr(1, 2, 4), CompoundResult)
        self.assertEqual(cr(1, 2, 4), [6, 6, 6])

        self.assertIsInstance(cr(1, 2, z=4), CompoundResult)
        self.assertEqual(cr(1, 2, z=4), [6, 6, 6])
