import logging

logger = logging.getLogger(__name__)

# swatch weight must be measured in grams for accurate yardage; hence the
# 'grams' line in both
UNITS_IMPERIAL = {
    "length": "inches",
    "length_long": "yards",
    "weight": "ounces",
    "grams": "grams",
}

UNITS_METRIC = {
    "length": "cm",
    "length_long": "metres",
    "weight": "grams",
    "grams": "grams",
}


def unitstring_for_user(dimension, user):
    """
    Returns the appropriate unit string (inches, cm, yards, metres, etc) for the
    current user according to their unit system preference (metric or imperial).

    Params
    dimension: string 'length', 'length_long', 'weight', or 'grams'
    user: the user object

    """
    profile = user.profile
    if profile and profile.display_imperial:
        retval = UNITS_IMPERIAL[dimension]
    else:
        retval = UNITS_METRIC[dimension]
    return retval


def format_units_for_user(text, user):
    """
    Returns text with appropriate unit strings (inches, cm, yards, metres, etc)
    for the current user substituted into placeholders, according to the user's
    unit system preference (metric or imperial).

    Params
    text: a string with python format placeholders 'length', 'length_long',
        'weight', and/or 'grams'
    user: the user object

    """
    profile = user.profile
    if profile and profile.display_imperial:
        units = UNITS_IMPERIAL
    else:
        units = UNITS_METRIC
    return text.format(**units)
