"""
Created on Jun 22, 2012
"""

import logging
import math
import operator
from collections import UserList

import customfit.helpers.row_parities as row_parities
from customfit.helpers.magic_constants import (
    CM_PER_INCHES,
    FLOATING_POINT_NOISE,
    OUNCES_PER_GRAM,
    YARDS_PER_METRE,
)

# Get an instance of a logger
logger = logging.getLogger(__name__)


def inches_to_cm(inches):
    """
    @param inches: float
    @rtype : float
    """
    return inches * CM_PER_INCHES


def cm_to_inches(cm):
    """
    @param cm: float
    @rtype : float
    """
    return cm / CM_PER_INCHES


def metres_to_yards(m):
    """
    @param m: a float length to be converted from m to yd
    @rtype: float
    """
    return m * YARDS_PER_METRE


def yards_to_metres(yd):
    """
    @param yd: a float length to be converted from yd to m
    @rtype: float
    """
    return yd / YARDS_PER_METRE


def grams_to_ounces(g):
    """
    @param g: a float weight to be converted from g to oz
    @rtype: float
    """
    return g * OUNCES_PER_GRAM


def ounces_to_grams(oz):
    """
    @param oz: a float weight to be converted from oz to g
    @rtype: float
    """
    return oz / OUNCES_PER_GRAM


def convert_value_to_imperial(value, dimension):
    """
    @param value: a float to be converted from metric to imperial
    @param dimension: one of 'length', 'length_long', 'weight', or 'grams'
    @rtype: float
    """
    if value == None:
        return value
    # could get fancier by refactoring this as a call to a conversion function
    # looked up from a dict, but i think it would be less readable that way.
    if dimension == "length":
        retval = cm_to_inches(value)
    elif dimension == "length_long":
        retval = metres_to_yards(value)
    elif dimension == "weight":
        retval = grams_to_ounces(value)
    elif dimension == "grams":
        # fields declared as grams need precision, and are stored that way even
        # with imperial units
        retval = value
    elif dimension == None:
        # no conversion necessary for dimensionless values
        retval = value
    else:
        raise ValueError("Unknown dimension '%s'" % dimension)
    return retval


def convert_value_to_metric(value, dimension):
    """
    @param value: a float to be converted from imperial to metric
    @param dimension: one of 'length', 'length_long', 'weight', or 'grams'
    @rtype: float
    """
    if value == None:
        return value
    # could get fancier by refactoring this as a call to a conversion function
    # looked up from a dict, but i think it would be less readable that way.
    if dimension == "length":
        retval = inches_to_cm(value)
    elif dimension == "length_long":
        retval = yards_to_metres(value)
    elif dimension == "weight":
        retval = ounces_to_grams(value)
    elif dimension == "grams":
        # fields declared as grams need precision, and are stored that way even
        # with imperial units
        retval = value
    elif dimension == None:
        # no conversion necessary for dimensionless values
        retval = value
    else:
        raise ValueError("Unknown dimension '%s'" % dimension)
    return retval


def convert_to_imperial(parameters, modelClass, user):
    """
    Check each field in the parameter set and, if it is a length and in metric
    units, convert to imperial.
    """
    logger.info("Entering convert_to_imperial")
    if not user.profile.display_imperial:
        for field in modelClass._meta.fields:
            dimension = getattr(field, "dimension", None)
            if dimension:
                if field.name in parameters:
                    metric_value = parameters[field.name]
                    parameters[field.name] = convert_value_to_imperial(
                        metric_value, dimension
                    )
    return parameters


# Now, some helper functions for rounding things

ROUND_UP = "UP"
ROUND_DOWN = "DOWN"
ROUND_ANY_DIRECTION = "ANY"
ROUNDING_DIRECTIONS = [ROUND_UP, ROUND_DOWN, ROUND_ANY_DIRECTION]


def round(orig, direction=ROUND_ANY_DIRECTION, multiple=1, mod=0):
    assert direction in ROUNDING_DIRECTIONS

    # first, find 'lower': the largest value satisfying 'mod' mod 'multiple'
    # lower than or equal to orig.
    lower = (orig // multiple) * multiple
    if (lower + mod) <= orig:
        lower = lower + mod
    else:
        lower = lower - multiple + mod

    # now find 'upper': the smallest value satisying
    # 'mod' mod multiple larger than  or equal to orig

    upper = (orig // multiple) * multiple
    if upper < orig:
        upper = upper + multiple
    if (upper - multiple + mod) >= orig:
        upper = upper - multiple + mod
    else:
        upper = upper + mod

    # If orig is really close to either upper or lower-- within the
    # noise of floating-point representation error-- return that one.
    if abs(upper - orig) < FLOATING_POINT_NOISE:
        return upper
    if abs(orig - lower) < FLOATING_POINT_NOISE:
        return lower

    # Okay, neither of those matched. We're in a real rounding case.

    if direction == ROUND_UP:
        return upper
    elif direction == ROUND_DOWN:
        return lower
    else:
        # Captures  direction == ROUND_ANY_DIRECTION
        if (orig - lower) < (upper - orig):
            return lower
        else:
            return upper


def is_even(x):
    return (x % 2) == 0


def is_odd(x):
    return (x % 2) == 1


# TODO: write tests for this function
# TODO: Write docstring for this function
# TODO: Remove teh 'actual' return value. We should never use it.
def _find_best_approximation(
    target, rate, desired_rounding, tolerance, x_mod=0, mod_y=1
):
    """
    Converts lengths (hip, waist, etc) to stich counts in a way that respects
    rounding directions, minimum eases, etc.
    """

    first_attempt = round(target * rate, desired_rounding, mod_y, x_mod)

    actual = first_attempt / rate

    error = actual - target

    if error < tolerance:
        second_attempt = round(target * rate, ROUND_UP, mod_y, x_mod)

        return second_attempt
    else:
        return first_attempt


def _down_to_odd(x):
    """
    Helper funciton.

    :type x: int
    """
    if is_even(x):
        return x - 1
    else:
        return x


def hypotenuse(width, height):
    return math.sqrt(math.pow(width, 2) + math.pow(height, 2))


def height_and_gauge_to_row_count(height, row_gauge, parity):
    """
    Turn a height (in inches) and row-gauge (in rows per inch) into a row-count.
    Made slightly more complicated than one might expect by the need to round,
    and the need to take the row-parity (RS vs. WS) into account.
    """

    assert parity in [row_parities.RS, row_parities.WS, row_parities.ANY]

    rows_float = height * row_gauge
    if parity == row_parities.RS:
        parity = 1
        multiple = 2
    elif parity == row_parities.WS:
        parity = 0
        multiple = 2
    else:
        parity = 0
        multiple = 1
    rounded = round(rows_float, ROUND_ANY_DIRECTION, multiple, mod=parity)
    return int(rounded)


def rectangle_area(base, height):
    """
    Return area (in sq in) of rectangle with base and height of the given
    inputs (if measured in inches). Isn't this too trivial to make into a
    function? Perhaps, but it makes other bits of code much more readable
    (e.g., the area() methods of pieces and necklines).
    """
    return base * height


def triangle_area(base, height):
    """
    Return area (in sq in) of triangle with base and height of the given
    inputs (if measured in inches). Isn't this too trivial to make into a
    function? Perhaps, but it makes other bits of code much more readable
    (e.g., the area() methods of pieces and necklines).
    """
    return base * height / 2.0


def trapezoid_area(bottom_base, top_base, height):
    """
    Return area (in sq in) of rectangle with bases and height of the given
    inputs (if measured in inches). Isn't this too trivial to make into a
    function? Perhaps, but it makes other bits of code much more readable
    (e.g., the area() methods of pieces and necklines).
    """
    return (bottom_base + top_base) * height / 2.0


class _BaseCompoundResult(UserList):

    def __bool__(self):
        # sub-case: empty list:
        if not self.data:
            return False

        bool_sublist = [bool(d) for d in self.data]
        # They are all true or all false, right?
        assert all(bool_sublist) or (not any(bool_sublist)), self.data
        return bool_sublist[0]


class CompoundResult(_BaseCompoundResult):

    def _operator(self, other, op) -> "CompoundResult":
        if isinstance(other, CompoundResult):
            if len(other) != len(self.data):
                raise TypeError("CompoundResults of different lengths")
            else:
                new_list = [op(x, y) for (x, y) in zip(self.data, other)]
                return CompoundResult(new_list)
        else:
            new_list = [op(x, other) for x in self.data]
            return CompoundResult(new_list)

    def __mul__(self, other):
        return self._operator(other, operator.mul)

    def __truediv__(self, other):
        return self._operator(other, operator.truediv)

    def __add__(self, other):
        return self._operator(other, operator.add)

    def __sub__(self, other):
        return self._operator(other, operator.sub)

    def __str__(self):
        # IF they are all the same, pick one and return its string
        first = self.data[0]
        if all(x == first for x in self.data):
            return first.__str__()
        return super(CompoundResult, self).__str__()

    def any(self, f=None):
        if f is None:
            f = bool
        return any(f(x) for x in self.data)

    def all(self, f=None):
        if f is None:
            f = bool
        return all(f(x) for x in self.data)

    def displayable(self):
        if any(x is None for x in self.data):
            return False
        elif any(x < 0 for x in self.data):
            return False
        else:
            return any(x > 0 for x in self.data)

    def map(self, f):
        return CompoundResult(f(x) for x in self.data)


class CallableCompoundResult(_BaseCompoundResult):

    def __call__(self, *args, **kwargs):
        value_list = [x(*args, **kwargs) for x in self.data]
        return CompoundResult(value_list)
