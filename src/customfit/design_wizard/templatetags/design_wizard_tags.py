import logging

from django import template

register = template.Library()
logger = logging.getLogger(__name__)


@register.filter
def value_for_key(dict, key):
    """
    Returns the value for a key in the dictionary
    """
    try:
        return dict[key]
    except KeyError:
        return ""
    # if there is no dict, the type error is "string indices must be integers, not str"
    except TypeError:
        return ""
