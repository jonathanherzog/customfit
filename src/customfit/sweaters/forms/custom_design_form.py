import logging
import os
from urllib.parse import urljoin

from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Fieldset, Layout, Submit
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

from customfit.bodies.models import Body
from customfit.design_wizard.forms import (
    ImageInlineRadios,
    _get_body_help_text,
    _get_gauge_help_text,
    _make_create_link_layout,
)
from customfit.helpers.form_helpers import add_help_circles_to_labels, wrap_with_units
from customfit.patterns.models import IndividualPattern
from customfit.patterns.templatetags.pattern_conventions import length_fmt
from customfit.stitches.models import Stitch
from customfit.swatches.models import Swatch
from customfit.sweaters.helpers.magic_constants import (
    DROP_SHOULDER_ARMHOLE_DEPTH_INCHES,
)

from ..helpers import sweater_design_choices as SDC
from ..models import SweaterPatternSpec

# Override default help text to fix all unit references so they're in the user's
# preferred system.
# TODO: our help text handling is pretty incoherent at this point;
# wrap_with_units could be handling the unit conversions, and since Django 1.6
# there has been help text access through form.Meta. We've never taken a unified
# architectual approach to our help text handling, and yes, it shows.
HELP_TEXT = {
    "button_band_allowance": "How far apart you'd like the fronts of your cardigan to be, "
    "not including any edging. A value of 0 will result in cardigan "
    "fronts that meet in the middle before trim. A value of 2 will "
    "result in cardigan fronts that are 2 {length} apart before adding trim. "
    "A value of -1.5 will result in cardigan fronts that overlap by 1.5 {length} "
    "before adding trim.",  # note {length} renders as "inches" or "cm"
    "neckline_depth": mark_safe(
        "How deep would you like your neckline? Normally measured as a "
        "length below the shoulders, but if you "
        '<a id="showNecklineOptionsHelp" href="#">reveal</a> and change the '
        "option below for neckline depth orientation, you can also measure it "
        "above the armhole shaping or below the armhole shaping.<br />"
        "<img src='"
        + os.path.join(settings.STATIC_URL, "img/neck-depth-help.png")
        + "' width='150px'>"
    ),
}

LABELS = {
    # button band
    "button_band_allowance": "allowance",
    "button_band_edging_height": "edge height",
    "number_of_buttons": "# of buttons",
    "button_band_edging_stitch": "edge stitch",
    # neckline
    "neckline_depth": "depth",
    "neck_edging_height": "edge height",
    "neck_edging_stitch": "edge stitch",
    # sleeve
    "sleeve_edging_height": "edge height",
    "sleeve_edging_stitch": "edge stitch",
    "armhole_edging_stitch": "edge stitch",
    "armhole_edging_height": "edge height",
    # hem
    "hip_edging_stitch": "edge stitch",
    "hip_edging_height": "edge height",
}

CARDIGAN = "cardigan"
PULLOVER = "pullover"
SLEEVED = "sleeved"
VEST = "vest"

GARMENT_TYPE_CHOICES = [(CARDIGAN, CARDIGAN), (PULLOVER, PULLOVER)]
GARMENT_SLEEVE_CHOICES = [(SLEEVED, SLEEVED), (VEST, VEST)]


class PatternSpecForm(forms.ModelForm):
    garment_type_body = forms.ChoiceField(choices=GARMENT_TYPE_CHOICES, required=True)
    garment_type_sleeves = forms.ChoiceField(
        choices=GARMENT_SLEEVE_CHOICES, required=True
    )

    class Meta:
        model = SweaterPatternSpec
        fields = [
            "name",
            "body",
            "swatch",
            "garment_fit",
            "silhouette",
            "construction",
            "button_band_edging_stitch",
            "button_band_edging_height",
            "button_band_allowance",
            "number_of_buttons",
            "neckline_style",
            "neckline_width",
            "neckline_depth",
            "neckline_depth_orientation",
            "neck_edging_stitch",
            "neck_edging_height",
            "armhole_edging_stitch",
            "armhole_edging_height",
            "drop_shoulder_additional_armhole_depth",
            "sleeve_length",
            "sleeve_shape",
            "bell_type",
            "sleeve_edging_stitch",
            "sleeve_edging_height",
            "torso_length",
            "hip_edging_stitch",
            "hip_edging_height",
            "garment_type_body",
            "garment_type_sleeves",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.create_body_url = kwargs.pop("create_body_url")
        self.create_swatch_url = kwargs.pop("create_swatch_url")

        super(PatternSpecForm, self).__init__(*args, **kwargs)

        self.instance.user = self.user

        self._limit_querysets()
        self._lay_out_form()
        self._remove_non_user_visible_necklines()
        self._amend_labels()

        help_texts = {
            "silhouette": "How the torso of your sweater should be shaped. ",
            "garment_fit": "How roomy you'd like your garment to be. ",
            "construction": "How the shoulders of your garment will be constructed. ",
            "drop_shoulder_additional_armhole_depth": "Drop shoulder armholes are deeper than set-in sleeve armholes. You can change the amount of additional depth here.",
        }

        # These fields should have help available onclick.
        help_text_fields = [
            "neckline_depth",
            "neck_edging_stitch",
            "neck_edging_height",
            "neckline_depth_orientation",
            "button_band_allowance",
            "button_band_edging_height",
            "button_band_edging_stitch",
            "number_of_buttons",
            "sleeve_edging_stitch",
            "sleeve_edging_height",
            "armhole_edging_stitch",
            "armhole_edging_height",
            "hip_edging_height",
            "hip_edging_stitch",
        ]

        # These fields should not have help available on click, and should
        # be styled so as not to indicate help availability.
        blank_help_text = ["name", "body", "swatch"]

        # Remaining fields don't have help onclick and also should not
        # be touched by add_help_circles_to_labels, as they have their
        # own styling requirements.

        for field in self.fields:
            if field in help_text_fields:
                help_texts[field] = self.fields[field].help_text
            elif field in blank_help_text:
                help_texts[field] = None

        for fieldname in help_texts:
            self.fields[fieldname].help_text = help_texts[fieldname]

        add_help_circles_to_labels(self, help_texts)
        self.helper["name"].wrap(Field, placeholder="i.e. cardi for Eleanor")

        # After all that, handle a special case-- empty menus for body or swatch
        body_queryset = self.fields["body"].queryset
        self.fields["body"].help_text = _get_body_help_text(
            body_queryset, self.create_body_url
        )
        swatch_queryset = self.fields["swatch"].queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, self.create_swatch_url
        )

        # Add lengths to drop-shoulder choices
        drop_shoulder_choices = [
            (k, "%s (%s)" % (name, length_fmt(DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[k])))
            for (k, name) in SDC.DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES
        ]

        self.fields["drop_shoulder_additional_armhole_depth"].choices = [
            ("", "---------")
        ] + drop_shoulder_choices

        wrap_with_units(self, self.user, {})

    def _lay_out_form(self):
        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-sm-4 col-xs-12"
        self.helper.field_class = "col-sm-8 col-xs-12"
        create_link_class = "col-sm-12 col-xs-12 form-group"

        create_body_layout = _make_create_link_layout(self.create_body_url)
        create_swatch_layout = _make_create_link_layout(self.create_swatch_url)

        self.helper.layout = Layout(
            Fieldset(
                "",
                # Basic details
                Div(
                    Div(
                        HTML(
                            '<img src="{{ STATIC_URL }}img/custom/BYO_Default_Icon_Straight.png" class="img-customfit">'
                        ),
                        css_class="col-xs-12 col-sm-4",
                    ),
                    Div(
                        "name",
                        "body",
                        # If body_queryset is empty, the create-body link is
                        # already shown in 'body' helptext. So suppress
                        # the following instance of it
                        (
                            Div(create_body_layout, css_class=create_link_class)
                            if self.fields["body"].queryset.exists()
                            else None
                        ),
                        "swatch",
                        # If body_queryset is empty, the create-body link is
                        # already shown in 'body' helptext. So suppress
                        # the following instance of it
                        (
                            Div(create_swatch_layout, css_class=create_link_class)
                            if self.fields["swatch"].queryset.exists()
                            else None
                        ),
                        "silhouette",
                        "garment_fit",
                        "construction",
                        css_class="col-xs-12 col-sm-8 hide-help-text margin-top-20",
                    ),
                    css_class="row",
                ),
                css_class="clearfix",
            ),
            Fieldset(
                "Body construction",
                Div(
                    Div(
                        Field(
                            "garment_type_body", template="custom/button_groups.html"
                        ),
                        Field(
                            "garment_type_sleeves", template="custom/button_groups.html"
                        ),
                        css_class="col-xs-12 col-sm-6 btn-form-group-lg btn-group-justified-2",
                    ),
                    Div(
                        HTML(
                            '<p class="text-right text-centered-phone"><span class="visible-xs margin-top-20"></span><strong>button band</strong></p>'
                        ),
                        "button_band_allowance",
                        "number_of_buttons",
                        "button_band_edging_height",
                        "button_band_edging_stitch",
                        css_class="col-xs-12 col-sm-6 hide-help-text",
                        css_id="button_band_options",
                    ),
                ),
            ),
            Fieldset(
                "Neckline",
                Div(
                    ImageInlineRadios("neckline_style"),
                    css_class="col-xs-12 col-sm-6 clearfix",
                ),
                Div(
                    HTML(
                        '<p class="text-right text-centered-phone"><span class="visible-xs margin-top-20"></span><strong>neckline details</strong></p>'
                    ),
                    Field("neckline_width", template="custom/button_groups.html"),
                    "neckline_depth",
                    "neckline_depth_orientation",
                    "neck_edging_height",
                    "neck_edging_stitch",
                    css_class="col-xs-12 col-sm-6 hide-help-text btn-right",
                ),
            ),
            Fieldset(
                '<span class="sleeve_header">Sleeves</span><span class="armhole_header">Armholes</span>',
                Div(
                    ImageInlineRadios("sleeve_length"),
                    css_class="col-xs-12 col-sm-6 clearfix",
                    css_id="sleeve_length_options",
                ),
                # Only one of the sleeve_shape/bell_type/sleeve_edging_stitch/height
                # options, or the armhole_edging_stitch/height options, is shown,
                # depending on whether garment_type has sleeves or not.  This is
                # controlled by the showDependent logic in static/js/customfit.js,
                # and changes dynamically depending on user input about garment
                # parameters.
                Div(
                    HTML(
                        '<p class="text-right text-centered-phone"><span class="visible-xs margin-top-20"></span><strong><span class="sleeve_header">sleeve</span><span class="armhole_header">armhole</span> details</strong></p>'
                    ),
                    Div(
                        Field(
                            "sleeve_shape",
                            template="custom/button_groups.html",
                            css_id="sleeve_shape_options",
                        ),
                        Field("bell_type", template="custom/button_groups.html"),
                        "sleeve_edging_height",
                        "sleeve_edging_stitch",
                        css_id="sleeve_details",
                    ),
                    Div(
                        "armhole_edging_height",
                        "armhole_edging_stitch",
                        css_id="armhole_details",
                    ),
                    Div(
                        "drop_shoulder_additional_armhole_depth",
                        css_id="drop_shoulder_armhole_depth",
                    ),
                    css_class="col-xs-12 col-sm-6 hide-help-text btn-right",
                ),
            ),
            Fieldset(
                "Hem",
                Div(
                    ImageInlineRadios("torso_length"),
                    css_class="col-xs-12 col-sm-6 clearfix",
                ),
                Div(
                    HTML(
                        '<p class="text-right text-centered-phone"><span class="visible-xs margin-top-20"></span><strong>hem details</strong></p>'
                    ),
                    "hip_edging_height",
                    "hip_edging_stitch",
                    css_class="col-xs-12 col-sm-6 hide-help-text",
                ),
            ),
        )

        self.helper.add_input(
            Submit(
                "redirect_tweak",
                "customize fit specifics",
                css_class="btn-customfit-outline btn-customfit-lg",
            )
        )
        self.helper.add_input(
            Submit(
                "redirect_approve",
                "Get this pattern!",
                css_class="btn-customfit-action btn-customfit-lg",
            )
        )

    def body_options(self):
        """
        Creates a dict indicating whether a body has hourglass
        measurements. This will be used by front-end JS to dynamically show/hide
        relevant design options.

        We don't check to see if bodies have all of the extra measurements,
        because users are allowed to create patterns for bodies that are missing
        some; they'll be prompted for additional measurements in a subsequent
        AddMissingMeasurementsView if needed.
        """
        options = {}

        for body in self.fields["body"].queryset:
            body_opts = {}

            if body.is_woman:
                body_opts["type"] = "woman"
            elif body.is_man:
                body_opts["type"] = "man"
            elif body.is_child:
                body_opts["type"] = "child"
            else:
                assert body.is_unstated_type
                body_opts["type"] = "unstated"

            options[body.pk] = body_opts

        return options

    def _limit_querysets(self):
        # Limit swatch and body to only those belonging to the user.
        self.fields["body"].queryset = self._get_bodies()
        self.fields["swatch"].queryset = self._get_swatches()

        self.fields["button_band_edging_stitch"].queryset = (
            Stitch.public_buttonband_hem_stitches.all()
        )
        self.fields["neck_edging_stitch"].queryset = (
            Stitch.public_neckline_hem_stitches.all()
        )
        self.fields["sleeve_edging_stitch"].queryset = (
            Stitch.public_sleeve_hem_stitches.all()
        )
        self.fields["armhole_edging_stitch"].queryset = (
            Stitch.public_armhole_hem_stitches.all()
        )
        self.fields["hip_edging_stitch"].queryset = (
            Stitch.public_waist_hem_stitches.all()
        )

        self.fields["silhouette"].choices = [
            ("", "---------")
        ] + SDC.SUPPORTED_SILHOUETTES

    def _remove_non_user_visible_necklines(self):
        try:
            # Field-level remove
            choices = dict(self.fields["neckline_width"].choices)
            choices.pop("NECK_OTHERWIDTH")
            self.fields["neckline_width"].choices = list(choices.items())
        except ValueError:
            pass

        try:
            # We used to do this by converting our neckline style choices to
            # a dict, examining its keys, and converting back, but this option
            # gives us no control over the ordering of the choices in the form,
            # and the powers that be wanted to control the order.
            user_visible_choices = []
            user_visible_necks = list(
                dict(SDC.USER_VISIBLE_NECKLINE_STYLE_CHOICES).keys()
            )
            for neck_style in self.fields["neckline_style"].choices:
                if neck_style[0] in user_visible_necks:
                    user_visible_choices.append(neck_style)
            self.fields["neckline_style"].choices = user_visible_choices
        except ValueError:
            pass

    def _amend_labels(self):
        for field in self.fields:
            if field in LABELS:
                self.fields[field].label = LABELS[field]

        def _swap_out_labels(field_name, design_options):
            new_choices = []

            for choice in self.fields[field_name].choices:
                option_id = choice[0]
                if option_id in design_options:
                    label = design_options[option_id]
                    new_choices.append((option_id, label))

            self.fields[field_name].choices = new_choices

        _swap_out_labels("neckline_style", SDC.NECKLINE_STYLE_CUSTOM_FORM)
        _swap_out_labels("sleeve_length", SDC.SLEEVE_LENGTH_CUSTOM_FORM)

        # The term 'swatch' is historical. Even though we're asking for a Swatch instance, the user
        # facing name is 'gauge'
        self.fields["swatch"].label = "gauge"

    def _set_garment_type(self, data):
        """
        Sets garment type on the instance, so that we will be able to feed it
        into design_params in the view.
        """
        if data["garment_type_body"] == PULLOVER:
            if data["garment_type_sleeves"] == VEST:
                self.instance.garment_type = SDC.PULLOVER_VEST
            elif data["garment_type_sleeves"] == SLEEVED:
                self.instance.garment_type = SDC.PULLOVER_SLEEVED
            else:
                raise ValidationError("Cannot determine garment type")
        elif data["garment_type_body"] == CARDIGAN:
            if data["garment_type_sleeves"] == VEST:
                self.instance.garment_type = SDC.CARDIGAN_VEST
            elif data["garment_type_sleeves"] == SLEEVED:
                self.instance.garment_type = SDC.CARDIGAN_SLEEVED
            else:
                raise ValidationError("Cannot determine garment type")
        else:
            raise ValidationError("Cannot determine garment type")

        data.pop("garment_type_sleeves")
        data.pop("garment_type_body")

    def clean_name(self):
        name = self.cleaned_data["name"]
        if IndividualPattern.live_patterns.filter(user=self.user, name=name):
            raise forms.ValidationError("You already have a pattern by that name.")
        return name

    def clean(self):
        cleaned_data = super(PatternSpecForm, self).clean()
        if "garment_type_body" not in list(cleaned_data.keys()):
            raise ValidationError("Please choose a cardigan or pullover.")
        if "garment_type_sleeves" not in list(cleaned_data.keys()):
            raise ValidationError("Please choose sleeves or a vest.")

        if cleaned_data["garment_type_body"] == CARDIGAN:
            if "neckline_style" not in list(cleaned_data.keys()):
                raise ValidationError("Please a neckline style.")
            elif cleaned_data["neckline_style"] == SDC.NECK_VEE:
                # Neck edging is not defined for v-neck cardigans; it is the
                # continuation of the buttonband. If users have somehow entered
                # values here (e.g. while switching their sweater types around
                # in the custom design form), we should not use them.
                # Because these fields were not visible on form submit, setting
                # their values to None should fit with user expectations.
                cleaned_data["neck_edging_stitch"] = None
                cleaned_data["neck_edging_height"] = None

        if "construction" in self.cleaned_data:
            if cleaned_data["construction"] != SDC.CONSTRUCTION_DROP_SHOULDER:
                # Ignore the drop-shoulder armhole-depth
                cleaned_data["drop_shoulder_additional_armhole_depth"] = None

        # This must go *after* the vneck cardi if condition or cleaned_data
        # will no longer have the needed keys.
        self._set_garment_type(cleaned_data)

        return cleaned_data

    def _get_bodies(self):
        # All bodies of this user
        return Body.objects.filter(user=self.user)

    def _get_swatches(self):
        # All swatches of this user
        return Swatch.objects.filter(user=self.user)
