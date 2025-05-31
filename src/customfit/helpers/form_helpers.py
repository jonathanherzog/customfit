from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout
from django.core.exceptions import FieldDoesNotExist
from django.utils.safestring import mark_safe

from customfit.userauth.helpers import format_units_for_user, unitstring_for_user


def wrap_with_units(form, user, help_text_dict=None):
    if not help_text_dict:
        help_text_dict = {}

    # This function assumes that we have a crispy forms layout to manipulate,
    # so let's make sure we do.
    if not hasattr(form, "helper"):
        form.helper = FormHelper()
        form.helper.layout = Layout()

        # Make sure our form fields are part of the layout - otherwise they
        # can't be governed by the layout manipulation below.
        for fieldname in list(form.fields.keys()):
            form.helper.layout.extend(Field(fieldname))

    assert isinstance(form.helper, FormHelper)

    # Wrap fields with appropriate units.
    for fieldname, _ in list(form.fields.items()):
        dimension = None
        try:
            modelfield = form._meta.model._meta.get_field(fieldname)
            dimension = getattr(modelfield, "dimension", None)
        except FieldDoesNotExist:
            pass
        if dimension:
            units = unitstring_for_user(dimension, user)
            form.helper[fieldname].wrap(AppendedText, units)

    # Override help text, fixing units for user.
    for fieldname in list(form.fields.keys()):
        if help_text_dict.get(fieldname):
            form.fields[fieldname].help_text = format_units_for_user(
                help_text_dict[fieldname], user
            )


def add_help_circles_to_labels(form, help_text):
    """
    Fields with help text get indicators that will appear onhover (this is taken
    care of by customfit_forms.css). Fields with no help text get a class added
    so that we can style them differently (again with customfit_forms.css)

    This will, for some reason, blow away any placeholders you've put in the
    fields, so wrap() them in after calling this function rather than applying
    them during initial layout.
    """
    for field in help_text:
        if help_text[field]:
            form.fields[field].label += ' <span class="help-callout-circle">?</span>'
            form.fields[field].label = mark_safe(form.fields[field].label)
        else:
            form.helper[field].wrap(Div, css_class="no-help-text")
