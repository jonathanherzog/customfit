from customfit.patterns.templatetags.pattern_conventions import length_fmt


def _fix_length_formatting(length):
    """
    When Django renders templates, it does stuff with encodings that we
    don't do inside the length_fmt tag. (It also does stuff with HTML
    escaping that we don't do here, but it seems like the test runner does
    not do that.) We're going to need to deal with encodings (but not
    escaping) in order to check the text of rendered templates for lengths.
    """
    length_formatted = length_fmt(length)
    length_encoded = (
        length_formatted.replace("\xa0", " ").replace('"', "&quot;").encode("utf-8")
    )
    return length_encoded
