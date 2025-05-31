COWL_CIRC_EXTRA_SMALL = "cowl_circ_xsmall"
COWL_CIRC_SMALL = "cowl_circ_small"
COWL_CIRC_MEDIUM = "cowl_circ_medium"
COWL_CIRC_LARGE = "cowl_circ_large"

COWL_CIRC_CHOICES = [
    (COWL_CIRC_EXTRA_SMALL, "extra-small circumference"),
    (COWL_CIRC_SMALL, "small circumference"),
    (COWL_CIRC_MEDIUM, "medium circumference"),
    (COWL_CIRC_LARGE, "large circumference"),
]


circ_to_inches_dict = {
    COWL_CIRC_EXTRA_SMALL: 20,
    COWL_CIRC_SMALL: 26,
    COWL_CIRC_MEDIUM: 42,
    COWL_CIRC_LARGE: 60,
}

COWL_HEIGHT_SHORT = "cowl_height_short"
COWL_HEIGHT_AVERAGE = "cowl_height_avg"
COWL_HEIGHT_TALL = "cowl_height_tall"
COWL_HEIGHT_EXTRA_TALL = "cowl_height_xtall"

COWL_HEIGHT_CHOICES = [
    (COWL_HEIGHT_SHORT, "short height"),
    (COWL_HEIGHT_AVERAGE, "average height"),
    (COWL_HEIGHT_TALL, "tall height"),
    (COWL_HEIGHT_EXTRA_TALL, "extra tall height"),
]


height_to_inches_dict = {
    COWL_HEIGHT_SHORT: 10,
    COWL_HEIGHT_AVERAGE: 12,
    COWL_HEIGHT_TALL: 16,
    COWL_HEIGHT_EXTRA_TALL: 20,
}


def _decorate_choices(items, orig_choices, inches_dict):
    from customfit.patterns.templatetags.pattern_conventions import length_fmt

    orig_choice_dict = {k: v for (k, v) in orig_choices}
    new_choices = [("", "---------")]
    for item in items:
        inches = inches_dict[item]
        length_txt = length_fmt(inches)
        orig_text = orig_choice_dict[item]
        new_txt = "%s (%s)" % (orig_text, length_txt)
        new_choices.append((item, new_txt))
    return new_choices


def decorate_height_choices_for_form(height_choices):
    return _decorate_choices(height_choices, COWL_HEIGHT_CHOICES, height_to_inches_dict)


def decorate_circ_choices_for_form(height_choices):
    return _decorate_choices(height_choices, COWL_CIRC_CHOICES, circ_to_inches_dict)
