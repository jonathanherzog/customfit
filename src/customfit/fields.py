from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class LowerLimitValidator(MinValueValidator):
    """Raises an exception if value is not larger than limit-value used to construct validator"""

    # Code stolen from django.core.validators.BaseValidator
    message = _("Ensure this value is greater than %(limit_value)s.")
    code = "min_value"
    compare = lambda self, a, b: a <= b


def _add_to_validators(kwargs, validator):
    if "validators" in kwargs:
        curr_validators = kwargs["validators"]
        if validator not in curr_validators:
            curr_validators.append(validator)
        kwargs["validators"] = curr_validators
    else:
        kwargs["validators"] = [validator]
    return kwargs


class _LengthMixin(object):
    dimension = "length"


class _NotBelowMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs = _add_to_validators(kwargs, MinValueValidator(self._lower_limit))
        super(_NotBelowMixin, self).__init__(*args, **kwargs)


class _StrictlyAboveMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs = _add_to_validators(kwargs, LowerLimitValidator(self._lower_limit))
        super(_StrictlyAboveMixin, self).__init__(*args, **kwargs)


class NonNegFloatField(_NotBelowMixin, models.FloatField):
    """A field that holds a float not less than zero"""

    _lower_limit = 0


class LengthOffsetField(_LengthMixin, models.FloatField):
    """A field that holds a length measurement that may be zero or negative (always stored in inches)."""

    pass


class PositiveFloatField(_StrictlyAboveMixin, models.FloatField):
    _lower_limit = 0


class PositiveLengthField(_LengthMixin, PositiveFloatField):
    """A field that holds a length measurement (req'd greater than zero, always stored in inches)."""

    pass


class LongLengthField(PositiveFloatField):
    """A field that holds a length measurement (req'd greater than zero, always stored in yards)."""

    dimension = "length_long"


class GramsField(PositiveFloatField):
    """A field that holds a precise weight measurement (always stored in grams)."""

    dimension = "grams"


class _IntegerRoundingErrorMixin(object):

    def to_python(self, value):
        """Based on the same function from django.db.models.fields,
        but redefined to throw an exception on floats (rather
        than to silently round)."""
        if value is None:
            return value
        try:
            i = int(value)
            f = float(value)
            if i == f:
                return i  # return the value as an integer!
            else:
                raise ValueError
        except (TypeError, ValueError):
            msg = "%s must be an integer" % str(value)
            raise ValidationError(msg)


class NonNegSmallIntegerField(
    _NotBelowMixin, _IntegerRoundingErrorMixin, models.SmallIntegerField
):
    """A field that holds an integer not less than zero"""

    _lower_limit = 0


# TODO: replace uses of the default PositiveSmallIntegerField with this one
class StrictPositiveSmallIntegerField(
    _StrictlyAboveMixin, _IntegerRoundingErrorMixin, models.SmallIntegerField
):
    """A field that holds a positive integer"""

    _lower_limit = 0


class LengthField(_LengthMixin, NonNegFloatField):
    """
    A field that holds a length measurement (non-negative, always stored in inches).

    LengthField and PositiveLengthField both exist for semi-arbitrary historical
    reasons about whether various lengths in Body and Swatch are allowed to be
    zero or not.  We have not taken the trouble to clean up and unify the
    validation rules.  The one hard rule is that it is not okay ever to tell
    someone with a severe disability or abnormality that their body was invalid;
    and so we decided to accept a measurement of zero at
    the body-measurements phase and deal with the engine error later as being
    preferable.
    """

    pass
