from crispy_forms.bootstrap import AppendedText, Div, Field
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Fieldset, Layout, Submit
from django.forms import ModelForm

from customfit.helpers.form_helpers import wrap_with_units
from customfit.swatches.models import Swatch

yardage_warning = " <em>Required for <em>swatch-based</em> yardage estimates</em>"


HELP_TEXT = {
    "name": "Give your gauge a name to remind yourself which one it is.",
    "stitches_length": "Precise length of the 'stitches' side of your gauge, "
    "in {length}",
    "rows_length": "Precise length of the 'rows' side of your gauge, in " "{length}",
    "length_per_hank": "How much yarn (in {length_long}) in a hank?",
    "full_swatch_height": "How long (in {length}) is the full swatch along "
    "the row edge?",
    "full_swatch_width": "How long (in {length}) is the full swatch along "
    "the stitch edge?",
}


class _SwatchCreateFormBase(ModelForm):
    # Subclasses should define save_and_go_to_not_pattern_text with the text that should be put on the
    # save button that is NOT save-and-go-to-pattern

    def _make_submit_buttons(self, single_submit_button, not_pattern_text, index):
        if single_submit_button:
            css_id = "submit-%d" % index
            return Div(
                Submit(
                    "submit", "Save", css_class="btn-customfit-action", css_id=css_id
                ),
                css_class="pull-right",
            )
        else:
            css_id1 = "submit-to-home-%d" % index
            css_id2 = "submit-to-pattern-%d" % index
            return Div(
                Submit(
                    "submit_to_home",
                    not_pattern_text,
                    css_class="btn-customfit-outline",
                    css_id=css_id1,
                ),
                Submit(
                    "submit_to_pattern",
                    "Save and make a pattern",
                    css_class="btn-customfit-action",
                    css_id=css_id2,
                ),
                css_class="pull-right",
            )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        single_submit_button = kwargs.pop("force_single_submit_button", False)
        super(_SwatchCreateFormBase, self).__init__(*args, **kwargs)

        # CRISPY FORMS
        self.helper = FormHelper()
        # self.helper.form_class = 'form-horizontal'
        self.helper.label_class = "col-xs-12 col-sm-4"
        self.helper.field_class = "col-xs-12 col-sm-8"
        self.helper.layout = Layout(
            Fieldset(
                "GAUGE INFO (required)",
                Div(
                    Field("name", placeholder="i.e. Rowan HKC for Eleanor sweater"),
                    css_class="form-horizontal",
                ),
                Div(
                    AppendedText("stitches_number", "sts", placeholder="stitches"),
                    Div(
                        HTML(" in "),
                    ),
                    Field("stitches_length"),
                    css_class="form-horizontal gauge-form-row-group",
                ),
                Div(
                    HTML(
                        "Are you sure? Unless you're knitting with "
                        "extremely fine yarn, most swatches have no "
                        "more than 10 stitches per inch/4 stitches "
                        "per cm."
                    ),
                    css_class="alert alert-block alert-error gauge-warning",
                    css_id="sts_warning_tiny",
                ),
                Div(
                    HTML(
                        "Are you sure? Unless you're knitting with "
                        "extremely bulky yarn, most swatches have at "
                        "least 2 stitches per inch/8 stitches over 10 cm."
                    ),
                    css_class="alert alert-block alert-error gauge-warning",
                    css_id="sts_warning_big",
                ),
                Div(
                    AppendedText("rows_number", "rows", placeholder="rows"),
                    Div(
                        HTML(" in "),
                    ),
                    Field("rows_length"),
                    css_class="form-horizontal gauge-form-row-group",
                ),
                Div(
                    HTML(
                        "Are you sure? Unless you're knitting with "
                        "extremely fine yarn, most swatches have no "
                        "more than 15 rows per inch/38 rows per cm."
                    ),
                    css_class="alert alert-block alert-error gauge-warning",
                    css_id="rows_warning_tiny",
                ),
                Div(
                    HTML(
                        "Are you sure? Unless you're knitting with "
                        "extremely bulky yarn, most swatches have at "
                        "least 3 rows per inch/12 rows over 10 cm."
                    ),
                    css_class="alert alert-block alert-error gauge-warning",
                    css_id="rows_warning_big",
                ),
                Div(
                    Field("needle_size", placeholder="i.e. US 6 Addi Turbo Circs"),
                    css_class="form-horizontal",
                ),
                self._make_submit_buttons(
                    single_submit_button, self.save_and_go_to_not_pattern_text, 1
                ),
                css_class="hide-help-text clearfix margin-top-20",
            ),
            Div(
                HTML(
                    '<legend><a role="button" aria-expanded="false" aria-controls="swatch-accordion-info" href="#swatch-accordion-info" data-toggle="collapse" data-parent="#swatch-accordion">SWATCH INFO (optional) <span class="glyphicon glyphicon-menu-down"></span></a></legend>'
                ),
                Div(
                    Div(
                        "yarn_maker",
                        "yarn_name",
                        "length_per_hank",
                        "weight_per_hank",
                        "full_swatch_width",
                        "full_swatch_height",
                        "full_swatch_weight",
                        "notes",
                    ),
                    Div(
                        Div(
                            "use_repeats",
                            css_class="col-xs-12 col-sm-8 col-sm-offset-4",
                            # We can't put data attributes here to control the
                            # accordion toggle, because they toggle when the
                            # *label* is clicked, not just when the box is
                            # checked; this can lead to the use repeats box
                            # being checked but the repeat info being
                            # inaccessible. Front-end JS will trigger the
                            # accordion when the box is checked.
                        ),
                        Div(
                            "stitches_per_repeat",
                            "additional_stitches",
                            css_class="form-horizontal panel-collapse collapse out hide-help-text",
                            css_id="repeat-accordion-info",
                        ),
                        css_id="repeat-accordion",
                    ),
                    css_class="form-horizontal panel-collapse collapse out hide-help-text",
                    css_id="swatch-accordion-info",
                ),
                css_class="margin-top-20",
                css_id="swatch-accordion",
            ),
            self._make_submit_buttons(
                single_submit_button, self.save_and_go_to_not_pattern_text, 2
            ),
        )

        wrap_with_units(self, user, HELP_TEXT)

    class Meta:
        model = Swatch
        fields = (
            "name",
            "stitches_number",
            "stitches_length",
            "rows_number",
            "rows_length",
            "needle_size",
            "yarn_maker",
            "yarn_name",
            "length_per_hank",
            "weight_per_hank",
            "full_swatch_width",
            "full_swatch_height",
            "full_swatch_weight",
            "notes",
            "use_repeats",
            "stitches_per_repeat",
            "additional_stitches",
        )


class SwatchCreateFormIndividual(_SwatchCreateFormBase):
    save_and_go_to_not_pattern_text = "Save and go to account home"


class SwatchEditForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super(SwatchEditForm, self).__init__(*args, **kwargs)
        user = self.instance.user

        # CRISPY FORMS
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "",
                "name",
                "needle_size",
                "yarn_maker",
                "yarn_name",
                "length_per_hank",
                "weight_per_hank",
                "full_swatch_weight",
                "full_swatch_height",
                "full_swatch_width",
            )
        )
        self.helper.add_input(
            Submit("submit", "Save my changes", css_class="btn-customfit-action")
        )

        wrap_with_units(self, user, HELP_TEXT)

    class Meta:
        model = Swatch
        fields = (
            "name",
            "needle_size",
            "yarn_maker",
            "yarn_name",
            "length_per_hank",
            "weight_per_hank",
            "full_swatch_weight",
            "full_swatch_height",
            "full_swatch_width",
        )
