import logging

from crispy_forms.bootstrap import Div, InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django import forms

from customfit.bodies.models import Body
from customfit.swatches.models import Swatch

logger = logging.getLogger(__name__)

# TODO: how many things in this file are actually used anywhere?


#
# Helper functions
# -----------------------------------------------------------------------------
def _get_body_help_text(body_queryset, create_body_url):

    if body_queryset.exists():
        # The help text is unnecessary and clutters the screen if the
        # drop-down is populated.
        help_text = None
    else:
        help_text = """
        You need to <a href="{url}">add at least one measurement set</a>
        before you can proceed.""".format(
            url=create_body_url
        )
    return help_text


def _get_gauge_help_text(user, swatch_queryset, create_swatch_url):
    if swatch_queryset.exists():
        # The help text is unnecessary and clutters the screen if the
        # drop-down is populated.
        help_text = None
    elif user.swatches.count():
        help_text = """
        None of your gauges' repeats match the stitch-pattern used in this design.
        Please <a href="{url}">add a gauge</a> for this stitch pattern to make this
        design.""".format(
            url=create_swatch_url
        )
    else:
        help_text = """
        You need to <a href="{url}">add at least one gauge</a>
        before you can proceed.""".format(
            url=create_swatch_url
        )
    return help_text


def _make_create_link_layout(url):
    create_url_template = '<em><a href="%s">(or create a new one)</a></em>'
    raw_html = create_url_template % url
    return Div(HTML(raw_html), css_class="small text-right")


#
# Form mixins
# -----------------------------------------------------------------------------


class _BodyOptionsMixin(object):

    def get_body_options(self):
        """
        Creates a dict indicating whether a body has a gender attached to it.
        This will be used by front-end JS to dynamically show/hide fits.
        """
        options = {}

        for body in self.fields["body"].queryset:
            options[body.pk] = {}
            if body.is_woman:
                options[body.pk]["type"] = "woman"
            elif body.is_man:
                options[body.pk]["type"] = "man"
            elif body.is_child:
                options[body.pk]["type"] = "child"
            else:
                assert body.is_unstated_type
                options[body.pk]["type"] = "unstated"

        return options


class _IndividualQuerysetMixin(object):

    def _get_body_queryset(self):
        # Limit drop-down choices to those belonging to the user and without customer linkages.
        all_bodies = Body.objects.filter(user=self.user)
        return all_bodies

    def _get_swatch_queryset(self):
        # Limit drop-down choices to those belonging to the user, without customer linkages,
        # and compatible with the design.
        all_swatches = Swatch.objects.filter(user=self.user)
        return self.filter_compatible_swatches(all_swatches)


class ImageInlineRadios(InlineRadios):
    """
    A helper class for rendering radio buttons with picture labels
    (like sleeve length choices).
    """

    def __init__(self, *args, **kwargs):
        self.span_class = kwargs.pop("span_class", 2)
        super(ImageInlineRadios, self).__init__(*args, **kwargs)

    template = "custom/radio_buttons.html"

    def render(self, form, context, template_pack="bootstrap", **kwargs):
        context.update(
            {"inline_class": "inline", "images": "none", "span_class": self.span_class}
        )
        return super(ImageInlineRadios, self).render(
            form, context, template_pack=template_pack, **kwargs
        )


class SummaryAndApproveForm(forms.Form):

    def __init__(self, *args, **kwargs):

        super(SummaryAndApproveForm, self).__init__(*args, **kwargs)
        # Lay out the form

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Submit("get_pattern", "get pattern!", css_class="btn-customfit-action")
        )


class RedoApproveForm(forms.Form):
    # A no-op form that exists just so we can Do The Right Thing on the RedoApproveView

    APPROVE_BUTTON = "redo_approved"

    def __init__(self, *args, **kwargs):

        super(RedoApproveForm, self).__init__(*args, **kwargs)
        # Lay out the form

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Submit(
                self.APPROVE_BUTTON,
                "replace the old pattern with this one!",
                css_class="btn-customfit-action",
            )
        )
