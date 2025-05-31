import logging

from django import template
from django.template.defaultfilters import floatformat

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    inches_to_cm,
    round,
    yards_to_metres,
)

register = template.Library()
logger = logging.getLogger(__name__)


UNICODE_FRACTIONS = {
    0.125: "\u215B",
    0.25: "\u00BC",
    0.375: "\u215C",
    0.5: "\u00BD",
    0.625: "\u215D",
    0.75: "\u00BE",
    0.875: "\u215E",
}

# While the Right Thing to do is:
# INCHES_SYMBOL = u'\u2033'  # proper unicode double-prime inches symbol
# Our PDF font doesn't have that symbol. So:
INCHES_SYMBOL = '"'


NONBREAKING_SPACE = "\u00A0"  # proper unicode nonbreaking space


def _handle_maybe_lists(l, inner_f):
    try:
        # check if val is list-like
        raw_vals = [x for x in l]
    except TypeError:
        # Not a list!
        return inner_f(l)
    else:
        # Yes a list!
        return_me = [inner_f(v) for v in raw_vals]
        return return_me


def _handle_maybe_lists_and_format(l, inner_f):
    try:
        # check if val is list-like
        raw_vals = [x for x in l]
    except TypeError:
        # Not a list!
        return inner_f(l)
    else:
        # Yes a list!
        formatted_vals = [inner_f(v) for v in raw_vals]
        return_me = _format_list_for_pattern(formatted_vals)
        return return_me


def _simplify_if_same(l):
    # is it an iterable?
    try:
        l2 = [x for x in l]
        # OK. it is. Is it empty:
        if (
            len(l) == 0
        ):  # note: can't just say 'if l:' since we redefine __bool__ on CompoundResults
            return l
        # Not empty. All same?
        elif all(x == l[0] for x in l):
            return l[0]
        else:
            return l
    except TypeError:
        return l


def string_of_value(v, frac_formatting):
    """
    Returns a string representation of the value v, where the string
    representation is very humfrac_formattinged. If frac_formatting = true, then
    the string representation will use unicode characters for 1/4, 1/2 and 3/4.
    In either case, the value v is treated differently when in the range [0,1]
    than when it is above 1.
    """
    # Note: the code below was written when it was safe to assume that all
    # lengths would be positive, but that is no longer the case. But instead of
    # generalizing the code below, we just reduce to a solved problem!
    if v < 0:
        return "-" + string_of_value(-v, frac_formatting)

    fraction = v % 1
    wholepart = int(v - fraction)

    if frac_formatting:
        if fraction == 0:
            # example: 23.0 -> "23"
            return_me = str(wholepart)
        else:
            fracsym = UNICODE_FRACTIONS.get(fraction, None)
            if wholepart == 0:
                if fracsym:
                    # example: 0.25 -> unicode symbol for 1/4
                    return_me = fracsym
                else:
                    # example: 0.23 -> "0.23"
                    return_me = str(v)
            else:
                if fracsym:
                    # example: 23.25 -> "23" + unicode symbol for 1/4
                    return_me = "%0d%s" % (wholepart, fracsym)
                else:
                    # example: 23.23 -> "23.23"
                    return_me = str(v)
    else:
        if fraction == 0:
            # example: 23.0 -> "23"
            return_me = str(wholepart)
        else:
            # example: 23.25 -> "23.25"
            return_me = str(v)
    return return_me


def _format_list_for_pattern(l):
    if type(l) is not list:
        return l
    elif not l:
        # empty list
        return l
    elif len(l) == 1:
        # list with one element
        return l[0]
    else:
        # a non-trivial list
        starter = l[0]
        rest = [str(x) for x in l[1:]]
        in_parens = ", ".join(rest)
        return_me = "%s (%s)" % (starter, in_parens)
        return return_me


@register.filter
def length_fmt(val, precision_imperial=1.0 / 4, precision_metric=0.5):
    """
    Formats a length (in inches) according to the convention of the knitting
    world and returns a string of the form:

      X"/Y cm

    where

    * X is the input value, rounded to the nearest quarter inch (and using the
      unicode values for 1/4, 1/2, 3/4) and

    * Y is the same value, converted to cm, and rounded to the nearest half cm.

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return the original input.
    """

    # simplify val if its a list:
    val = _simplify_if_same(val)

    if val is None:
        # This tag was throwing a lot of exceptions (via its call to round)
        # when people tried to personalize Featherweight, which has no
        # buttonband allowance. How about instead we don't try to format a
        # nonexistent length. 'None' will look reasonable in templates in
        # that case - it's actually a correct English description of the
        # situation.
        return None

    try:

        def _handle_inch_val(inch_val):
            if inch_val is None:
                return "-"
            rounded_inches = round(inch_val, ROUND_ANY_DIRECTION, precision_imperial)
            inches_str = string_of_value(rounded_inches, True)
            return inches_str

        def _handle_inch_val_to_cm(inch_val):
            if inch_val is None:
                return "-"
            cms = inches_to_cm(inch_val)
            rounded_cms = round(cms, ROUND_ANY_DIRECTION, precision_metric)
            cm_str = string_of_value(rounded_cms, False)
            return cm_str

        inches_str = _handle_maybe_lists_and_format(val, _handle_inch_val)
        cm_str = _handle_maybe_lists_and_format(val, _handle_inch_val_to_cm)

        # This used to include a nonbreaking space before the 'cm', but our
        # PDF renderer barfs on that with Nexa (an old font). Let's run the risk that the
        # space will occasionally break in exchange for having PDFs that
        # don't look gross.
        return_me = "%s%s/%s cm" % (inches_str, INCHES_SYMBOL, cm_str)
        return return_me
    except:
        logger.exception(
            "Exception. Returning original val. Parameters were "
            "val %s, precision_imperial %s , precision_metric %s",
            val,
            precision_imperial,
            precision_metric,
        )
        return val


@register.filter
def length_long_fmt(val):
    """
    Formats a length (in yards) and returns a string of the form:

      X yd/Y m

    where

    * X is the input value, rounded to the nearest whole yard, and

    * Y is the same value, converted to m and rounded to the nearest whole unit.

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return the original input.
    """

    # simplify val if its a list:
    val = _simplify_if_same(val)

    try:

        def _handle_yard_val(yard_val):
            rounded_yards = round(yard_val, ROUND_ANY_DIRECTION, 1)
            yards_str = string_of_value(rounded_yards, True)
            return yards_str

        def _handle_yard_val_to_meters(yard_val):
            val_m = yards_to_metres(yard_val)
            rounded_m = round(val_m, ROUND_ANY_DIRECTION, 1)
            m_str = string_of_value(rounded_m, False)
            return m_str

        yards_str = _handle_maybe_lists_and_format(val, _handle_yard_val)
        m_str = _handle_maybe_lists_and_format(val, _handle_yard_val_to_meters)

        return_me = "%s yd/%s m" % (yards_str, m_str)
        return return_me
    except:
        logger.exception("Exception. Returning original val of %s", val)
        return val


def _inner_count_fmt(val):
    # Why not just use the built-in floatformat tag? (1) to be able to log
    # errors, and (2) to give us the opportunity to extend this tag to include
    # more formatting, if desired
    if val is None:
        return "-"

    try:
        # Why all this rigamarole with int(float())? To properly process string
        # inputs like "2.0"
        if int(float(val)) == float(val):
            return int(float(val))
        else:
            # It's a number, but not a integer. Return as is (but let's not
            # clutter up the logs with any message.)
            return val
    except:
        # If there is any exception, log it and return the input unchanged.
        logger.exception("_inner_count_fmt called on %s, returning as-is", repr(val))
        return val


@register.filter
def count_fmt(val):
    """
    Formats a count-value (e.g., repeats, stitches, etc). If the input
    is a numeric value that has no float part (e.g., 1, "23", 2.0, "4.0") will
    return the number with no decimal places (1, 23, 2, 4). Otherwise, makes
    no change.

    Formats lists according to pattern convention (that is, [1,2,3,4]
    is rendered "1 (2, 3, 4)" but formats list-items as above.
    """
    # simplify val if its a list:
    val = _simplify_if_same(val)

    return _handle_maybe_lists_and_format(val, _inner_count_fmt)


def _percentage_round_helper(val, arg, mod, multiple):
    """
    Rounds (val * arg / 100) with rounding requirements specified by mod and
    multiple. Used as a helper function for percentage_match_parity and
    percentage_round_whole. Since those are template tags, we can't throw
    exceptions.  If anything goes wrong, we should return val unchanged.
    """

    try:
        assert int(val) == val
        assert int(arg) == arg
        assert int(mod) == mod
        assert int(multiple) == multiple
        assert arg >= 0
        assert arg <= 100

        exact_percentage = float(val) * float(arg) * 0.01
        rounded_percentage = round(
            exact_percentage, direction=ROUND_ANY_DIRECTION, multiple=multiple, mod=mod
        )

        return int(rounded_percentage)
    except:
        logger.exception("Exception. Returning original val of %s, arg of %s", val, arg)
        return val


@register.filter
def percentage_match_parity(val, arg):
    """
    If val is an integer, return (val * arg / 100), rounded to the nearest
    integer that is the same parity as val. This will be used to do some
    quick-and-dirty computation on stitch & row counts in templates.

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return val unchanged.
    """
    try:

        def inner_f(x):
            x_parity = x % 2
            return _percentage_round_helper(x, arg, x_parity, 2)

        return _handle_maybe_lists_and_format(val, inner_f)
    except:
        logger.exception("Exception. Returning original val of %s, arg of %s", val, arg)
        return val


@register.filter
def percentage_round_whole(val, arg):
    """
    If val is an integer, return (val * arg / 100), rounded to the nearest
    integer. This will be used to do some quick-and-dirty computation on stitch
    & row counts in templates. (Note that round_match_parity matches the parity
    of the input. This does not.)

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return val unchanged.

    Note: this is now redundant with the more general {% round %} tag, below,
    but is remaining in the code base for historical reasons.
    """

    def inner_f(x):
        return _percentage_round_helper(x, arg, 0, 1)

    return _handle_maybe_lists_and_format(val, inner_f)


@register.filter
def multiply_gauge_by_inches(gauge, inches):
    """
    If gauge and inches are both numbers, return the integer closest to
    gauge * inches. This sill be used in templates to do some quick and
    dirty computation along the lines of "3 inches of stitches".

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return gauge unchanged.

    Note: this is now redundant with the more general {% round %} tag, below,
    but is remaining in the code base for historical reasons.
    """

    try:
        assert float(gauge) == gauge
        assert float(inches) == inches
        assert gauge > 0
        assert inches >= 0

        answer = round(gauge * inches, ROUND_ANY_DIRECTION)
        return int(answer)
    except:
        logger.exception(
            "Exception. Returning original val of %s, arg of %s", gauge, inches
        )
        return gauge


@register.filter
def divide_counts_by_gauge(counts, gauge):
    """
    If counts and gauge are both numbers, return the float equal
    to counts/gauge. This will be used in templates to do some quick and
    dirty computation in templates (particularly design-specific templates).

    Note: 'counts' is generic because it can be either stitch-count or
    row-count.

    This is a template tag, and so cannot throw an exception. If anything
    goes wrong, we should return inches unchanged.
    """

    def inner_f(count):

        try:
            assert float(gauge) == gauge
            assert float(count) == count
            assert gauge > 0
            assert count >= 0

            return float(count) / float(gauge)
        except:
            logger.exception(
                "Exception. Returning original val of %s, arg of %s", count, gauge
            )
            return count

    return _handle_maybe_lists(counts, inner_f)


@register.simple_tag(name="round")
def round_tag(factor1, factor2=1, direction=ROUND_ANY_DIRECTION, multiple=1, mod=0):
    """
    Provides direct access to the `round` function,
    which is the general-purpose rounding function used throughout the engine.

    Usage:

    {% round v %}: rounds v to the nearest whole number.

    {% round v1 v2 %}: rounds (v1 * v2) to the nearest whole number.

    {% round v1 v2 dir %}: rounds (v1 * v2) to the nearest whole number in the
    direction dir. dir can be any of ROUND_ANY_DIRECTION, 'UP', 'DOWN'.

    {% round v1 v2 dir mult %} rounds (v1 * v2) in the direction dir to the
    nearest whole number which is a multiple of mult.

    {% round v1 v2 dir mult rem %} rounds (v1 * v2) in the direction dir to the
    nearest whole number which is congruent to (rem mod multple).

    In all cases, v1, v2, dir, mult and rem can be hard-coded values OR
    context variables.


    Examples:

    {% round 2.9 %}              ---> "3"
    {% round 2.9 2 %}            ---> "6"
    {% round 2.9 2 'DOWN' %}     ---> "5"
    {% round 2.9 2 ROUND_ANY_DIRECTION 4 %}    ---> "4"
    {% round 2.9 2 'UP' 2 1 %}   ---> "7"

    """

    def inner_f(x):
        product = x * factor2
        result = round(product, direction, multiple, mod)
        return int(result)

    return _handle_maybe_lists(factor1, inner_f)


@register.simple_tag(name="round_counts")
def round_counts_tag(
    factor1, factor2=1, direction=ROUND_ANY_DIRECTION, multiple=1, mod=0
):
    return count_fmt(round_tag(factor1, factor2, direction, multiple, mod))


@register.simple_tag(name="round_lengths")
def round_lengths_tag(
    factor1, factor2=1, direction=ROUND_ANY_DIRECTION, multiple=1, mod=0
):
    return length_fmt(round_tag(factor1, factor2, direction, multiple, mod))


@register.filter()
def pluralize_counts(value, arg="s"):
    """
    Return a plural suffix if the value does not have a string representation of "1" or "1.0"
    """
    if "," not in arg:
        arg = "," + arg
    bits = arg.split(",")
    if len(bits) > 2:
        return ""
    singular_suffix, plural_suffix = bits[:2]

    try:
        return singular_suffix if str(value) in ["1", "1.0"] else plural_suffix
    except:  # Invalid string that's not a number.
        pass
    return ""
