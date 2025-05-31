from datetime import date

from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Fieldset, Layout, Submit
from django.forms import ModelForm

from customfit.bodies.models import (
    ESSENTIAL_FIELDS,
    EXTRA_FIELDS,
    OPTIONAL_FIELDS,
    Body,
)
from customfit.helpers.form_helpers import add_help_circles_to_labels, wrap_with_units
from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    cm_to_inches,
    inches_to_cm,
    round,
)

HELP_TEXT = {
    "name": "",
    "upper_torso_circ": "Circumference (in {length}) around the body at upper torso",
    "bust_circ": "Circumference (in {length}) around the body at the bust",
    "waist_circ": "Circumference (in {length}) around the body at the natural waist",
    "high_hip_circ": "Circumference (in {length}) around the body at your short sweater hem height",
    "med_hip_circ": "Circumference (in {length}) around the body at your average-length sweater hem height",
    "low_hip_circ": "Circumference (in {length}) around the body at your long sweater hem height",
    "tunic_circ": "Circumference (in {length}) around the body at your tunic hem height",
    "armpit_to_high_hip": "Length (in {length}) from the armhole-shaping to your short sweater hem",
    "armpit_to_med_hip": "Length (in {length}) from the armhole-shaping to your average-length sweater hem",
    "armpit_to_low_hip": "Length (in {length}) from the armhole-shaping to your long sweater hem",
    "armpit_to_tunic": "Length (in {length}) from the armhole-shaping to your tunic hem",
    "armpit_to_waist": "In {length}, measured down the side, from armhole-shaping to your waist",
    "armhole_depth": "Vertical distance in {length}, up your back near your arm, "
    "from your armhole shaping marker to the top of your shoulder. "
    "Alternately, you can simply enter this value if you know it.",
    "inter_nipple_distance": "Distance between the nipples, in {length}",
    "cross_chest_distance": "Desired distance between the armhole edges of the top of your sweater, for an average fit.",
    "bicep_circ": "Circumference of the arm, in {length}, at the widest part of "
    "the bicep",
    "elbow_circ": "Circumference of the arm, in {length}, at the elbow",
    "forearm_circ": "Circumference of the arm, in {length}, at the widest part of "
    "the forearm",
    "wrist_circ": "Circumference of the arm, in {length}, at the wrist",
    "armpit_to_short_sleeve": "Distance, in {length}, from armhole shaping "
    "down the bottom of a short sleeve",
    "armpit_to_elbow_sleeve": "Distance, in {length}, from armhole shaping down "
    "to the bottom of an elbow sleeve",
    "armpit_to_three_quarter_sleeve": "Distance, in {length}, from armhole "
    "shaping down to the bottom of a three-quarter sleeve",
    "armpit_to_full_sleeve": "Distance, in {length}, from armhole shaping down "
    "to the bottom of a full sleeve",
}


class _BodyCreateFormBase(ModelForm):

    # Subclasses should define save_and_go_to_not_pattern_text with the text that should be put on the
    # save button that is NOT save-and-go-to-pattern

    def _fix_labels(self):
        self.fields["cross_chest_distance"].label = "cross chest distance (expert mode)"

        # Set likely default
        self.fields["body_type"].initial = Body.BODY_TYPE_ADULT_WOMAN

    def _make_submit_buttons(
        self, force_single_submit_button, go_to_not_pattern_text, index
    ):
        if force_single_submit_button:
            css_id = "submit_%d" % index
            return Div(
                Submit(
                    "submit",
                    "submit",
                    css_class="btn-customfit-outline",
                    css_id=css_id,
                ),
                css_class="col-xs-12 hide-help-text text-right pad-right",
            )

        else:
            css_id1 = "submit_to_home_%d" % index
            css_id2 = "submit_to_pattern_%d" % index
            return Div(
                Submit(
                    "submit_to_home",
                    go_to_not_pattern_text,
                    css_class="btn-customfit-outline",
                    css_id=css_id1,
                ),
                Submit(
                    "submit_to_pattern",
                    "save and make a pattern",
                    css_class="btn-customfit-action",
                    css_id=css_id2,
                ),
                css_class="col-xs-12 hide-help-text text-right pad-right",
            )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        single_submit_button = kwargs.pop("force_single_submit_button", False)
        super(_BodyCreateFormBase, self).__init__(*args, **kwargs)
        self.instance.user = user

        # CRISPY FORMS
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal fix-firefox-fieldsets"
        self.helper.label_class = "col-sm-6 col-xs-12"
        self.helper.field_class = "col-sm-6 col-xs-12"

        # This form anticipates being placed inside a col-xs-12 col-sm-6 in the
        # template.
        # If you change the order of fields in this form, please also change the
        # order of ESSENTIAL_FIELDS, etc., in bodies/models.py to match;
        # this isn't functionally important, but it allows us to present
        # measurements to users in the same order on the measurement entry
        # and measurement detail pages.

        self.helper.layout = Layout(
            Fieldset(
                "Essentials",
                # Measurement set name
                Div(
                    Div(
                        Field("name", placeholder="i.e. Me (September 2015)"),
                        css_class="col-xs-12",
                    ),
                    Div(
                        HTML(
                            """
                            <div class="help-callout">
                              <span class="help-callout-circle">?</span>
                                <small>click a measurement name for more info</small>            
                            </div>"""
                        ),
                        css_class="col-xs-12 col-sm-8 col-sm-offset-4",
                    ),
                    css_class="row",
                    css_id="form_header",
                ),
                # Essential measurement fields
                Div(
                    Div(
                        "bust_circ",
                        Div(
                            HTML(
                                "Customfit won't build sweaters for wee ones just yet. "
                                "Please enter a bust/chest circumference that is at least "
                                "23''/59cm."
                            ),
                            css_class="alert alert-block alert-error inline-javascript-warning",
                            css_id="bust_circ_warning",
                        ),
                        "waist_circ",
                        "med_hip_circ",
                        "armhole_depth",
                        "armpit_to_med_hip",
                        "armpit_to_full_sleeve",
                        "wrist_circ",
                        "bicep_circ",
                        "body_type",
                        css_class="col-xs-12 hide-help-text margin-top-20",
                    ),
                    css_class="row",
                ),
                # Submit buttons
                Div(
                    self._make_submit_buttons(
                        single_submit_button, self.save_and_go_to_not_pattern_text, 1
                    ),
                    css_class="row",
                ),
                # Fieldset attributes
                css_class="clearfix",
            ),
            Fieldset(
                "",
                HTML(
                    '<legend><a role="button" aria-expanded="false" aria-controls="extras-accordion-fields" href="#extras-accordion-fields" data-toggle="collapse" data-parent="#extras-accordion" id="extras-accordion-control">Extras <span class="glyphicon glyphicon-menu-down"></span></a></legend>'
                ),
                Div(
                    # Optional measurement fields
                    Div(
                        Div(
                            Div(
                                HTML(
                                    "Your waist-to-armhole length is only part of your hem-to-armhole "
                                    "length. It should typically at least 3'' (7.5 cm) shorter than your short sweater "
                                    "hem-to-armhole length. (See 'Extras' pictures.)"
                                ),
                                css_class="alert alert-block alert-error inline-javascript-warning",
                                css_id="armpit_to_waist_warning",
                            ),
                            "upper_torso_circ",
                            "elbow_circ",
                            "forearm_circ",
                            "armpit_to_short_sleeve",
                            "armpit_to_elbow_sleeve",
                            "armpit_to_three_quarter_sleeve",
                            "armpit_to_waist",
                            "armpit_to_high_hip",
                            "high_hip_circ",
                            "armpit_to_low_hip",
                            "low_hip_circ",
                            "armpit_to_tunic",
                            "tunic_circ",
                            css_class="col-xs-12 hide-help-text margin-top-20",
                        ),
                        css_class="row",
                    ),
                    # Submit buttons
                    Div(
                        self._make_submit_buttons(
                            single_submit_button,
                            self.save_and_go_to_not_pattern_text,
                            2,
                        ),
                        css_class="row",
                    ),
                    css_class="panel-collapse collapse out",
                    css_id="extras-accordion-fields",
                ),
                # Fieldset attributes
                css_class="clearfix",
                css_id="extras-accordion",
            ),
            Fieldset(
                "",
                HTML(
                    '<legend><a role="button" aria-expanded="false" aria-controls="optional-accordion-fields" href="#optional-accordion-fields" data-toggle="collapse" data-parent="#optional-accordion" id="optional-accordion-control">Optional <span class="glyphicon glyphicon-menu-down"></span></a></legend>'
                ),
                Div(
                    Div(
                        Div(
                            "cross_chest_distance",
                            Div(
                                HTML(
                                    "Your cross-chest measurement for sweaters should be taken on "
                                    "your front rather than your back, and is the distance between "
                                    "the sides of your sweater's armholes. It's "
                                    "usually between 12''/30.5 cm and 16''/40.5 cm, and must be "
                                    "at least 2.5'' (6.5 cm) narrower than half of your upper torso."
                                ),
                                css_class="alert alert-block alert-error inline-javascript-warning",
                                css_id="cross_chest_warning",
                            ),
                            "inter_nipple_distance",
                            css_class="col-xs-12 hide-help-text margin-top-20",
                        ),
                        Div(
                            # Help content can go here
                            css_class="col-xs-12",
                        ),
                        css_class="row",
                    ),
                    # Submit buttons
                    Div(
                        self._make_submit_buttons(
                            single_submit_button,
                            self.save_and_go_to_not_pattern_text,
                            3,
                        ),
                        css_class="row",
                    ),
                    css_class="panel-collapse collapse out",
                    css_id="optional-accordion-fields",
                ),
                # Fieldset attributes
                css_class="clearfix",
                css_id="optional-accordion",
            ),
        )

        self._fix_labels()
        wrap_with_units(self, user, HELP_TEXT)
        add_help_circles_to_labels(self, HELP_TEXT)
        placeholder = "i.e. Me! (%s)" % date.today().strftime("%B %Y")
        self.helper["name"].wrap(Field, placeholder=placeholder)

    class Meta:
        model = Body
        fields = ESSENTIAL_FIELDS + EXTRA_FIELDS + OPTIONAL_FIELDS


class BodyCreateForm(_BodyCreateFormBase):
    save_and_go_to_not_pattern_text = "save and go to account home"


class BodyUpdateForm(_BodyCreateFormBase):
    """
    Nearly identical to BodyCreateForm in styling and validation, but with
    form fields for existing values (except name) disabled as they cannot
    be updated; accordions expanded, as users will want to edit them;
    and submit button actions slightly amended.
    """

    save_and_go_to_not_pattern_text = "save and review"

    def __init__(self, *args, **kwargs):
        super(BodyUpdateForm, self).__init__(*args, **kwargs)

        # Display in metric to metric users.
        if not self.instance.user.profile.display_imperial:
            for field, value in list(self.initial.items()):
                if isinstance(value, int) or isinstance(value, float):
                    self.initial[field] = round(
                        inches_to_cm(value), ROUND_ANY_DIRECTION, 0.5
                    )

        # Disable fields that already have values (except for name);
        # users should not be editing these.
        editable_fields = []
        for field in self.fields:
            if getattr(self.instance, field) and field != "name":
                self.fields[field].widget.attrs["readonly"] = True
            else:
                editable_fields.append(field)

        self.editable_fields = editable_fields

        # Start accordions in expanded state, since users will be wanting to
        # edit data in one or both of them.
        self.helper.layout[1][1].css_class = "panel-collapse collapse in"
        self.helper.layout[2][1].css_class = "panel-collapse collapse in"
        self.helper.layout[1][0] = HTML(
            '<legend><a role="button" aria-expanded="false" aria-controls="extras-accordion-fields" href="#extras-accordion-fields" data-toggle="collapse" data-parent="#extras-accordion">Extras<span class="glyphicon glyphicon-menu-down"></span></a></legend>'
        )
        self.helper.layout[2][0] = HTML(
            '<legend><a role="button" aria-expanded="false" aria-controls="optional-accordion-fields" href="#optional-accordion-fields" data-toggle="collapse" data-parent="#optional-accordion">Optional<span class="glyphicon glyphicon-menu-down"></span></a></legend>'
        )

        self.helper.layout[0].pop(2)

    def save(self):
        """
        Making fields readonly should have ensured that users did not change
        existing data (except possibly 'name'), but let's make super sure,
        since HTML form attributes don't protect against backdoor POST
        sneakiness.
        """
        instance = super(BodyUpdateForm, self).save(commit=False)

        # Display in metric to metric users.
        if not self.instance.user.profile.display_imperial:
            for field in self.editable_fields:
                value = getattr(self.instance, field)
                if isinstance(value, int) or isinstance(value, float):
                    setattr(self.instance, field, cm_to_inches(value))

        instance.save(update_fields=self.editable_fields)
        return instance


class BodyNoteUpdateForm(ModelForm):
    class Meta:
        model = Body
        fields = ("notes",)
