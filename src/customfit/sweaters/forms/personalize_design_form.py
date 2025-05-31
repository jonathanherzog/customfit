import logging
from datetime import date
from urllib.parse import urljoin

from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Fieldset, Layout, Submit
from django import forms
from django.conf import settings

from customfit.design_wizard.constants import REDIRECT_APPROVE, REDIRECT_TWEAK
from customfit.design_wizard.forms import (
    _BodyOptionsMixin,
    _get_body_help_text,
    _get_gauge_help_text,
    _IndividualQuerysetMixin,
    _make_create_link_layout,
)
from customfit.helpers.form_helpers import add_help_circles_to_labels
from customfit.patterns.models import GradedPattern, IndividualPattern
from customfit.patterns.templatetags.pattern_conventions import length_fmt
from customfit.swatches.models import Swatch
from customfit.sweaters.helpers.magic_constants import (
    DROP_SHOULDER_ARMHOLE_DEPTH_INCHES,
)

from ..helpers import sweater_design_choices as SDC
from ..models import GradedSweaterPatternSpec, SweaterPatternSpec

logger = logging.getLogger(__name__)


class PersonalizeDesignForm(
    forms.ModelForm, _BodyOptionsMixin, _IndividualQuerysetMixin
):

    class Meta:
        model = SweaterPatternSpec
        fields = (
            "name",
            "body",
            "swatch",
            "garment_fit",
            "silhouette",
            "construction",
            "sleeve_length",
            "torso_length",
            "drop_shoulder_additional_armhole_depth",
        )

    # Helper methods for limiting bodies and swatches.
    # --------------------------------------------------------------------------
    @staticmethod
    def extract_compatible_swatches(swatches, design):
        return [swatch for swatch in swatches if design.compatible_swatch(swatch)]

    def filter_compatible_swatches(self, swatches):
        compatible_swatches = self.extract_compatible_swatches(swatches, self.instance)
        compatible_swatch_pks = [swatch.pk for swatch in compatible_swatches]
        return Swatch.objects.filter(pk__in=compatible_swatch_pks).order_by("name")

    # Limit drop-down choices to those compatible with the design.
    # --------------------------------------------------------------------------
    #
    # Subclasses must implement:
    # * _get_body_queryset()
    # * _get_swatch_queryset()

    def _get_optional_lengths_text(self):
        # Decide how to describe the user's length-changing options and return
        # that string for later use.
        if self.instance.has_sleeves():
            length_header = "Change hem/sleeve lengths (Optional)"
        else:
            length_header = "Change hem length (Optional)"

        length_html = (
            '<a class="accordion-toggle" data-toggle="collapse" '
            'data-parent="#accordion" href="#collapseLengths" role="button">'
            '<strong><b class="caret"></b> %s</strong></a>' % length_header
        )

        return length_html

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()

        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")
        create_body_url = kwargs.pop("create_body_url")
        create_swatch_url = kwargs.pop("create_swatch_url")

        super(PersonalizeDesignForm, self).__init__(*args, **kwargs)

        # Set up available options in drop-down menus
        # ----------------------------------------------------------------------

        # Since we won't let them enter duplicate pattern names, let's
        # default to something unlikely to be a duplicate, if they already have
        # a pattern with the same name as the design.
        name = self.initial.get("name", None)
        if name:
            if IndividualPattern.live_patterns.filter(user=self.user, name=name):
                self.initial["name"] += " " + str(date.today())

        # Set menu & help-text for body
        body_queryset = self._get_body_queryset()
        self.fields["body"].queryset = body_queryset
        self.fields["body"].help_text = _get_body_help_text(
            body_queryset, create_body_url
        )

        # Set label, menu & help-text for body
        self.fields["swatch"].label = "gauge"
        swatch_queryset = self._get_swatch_queryset()
        self.fields["swatch"].queryset = swatch_queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, create_swatch_url
        )

        # Set help-text
        help_text_dict = {
            "silhouette": "How the torso of your sweater should be shaped. ",
            "garment_fit": "How roomy you'd like your garment to be. ",
            "construction": "How the shoulders of your garment will be constructed. ",
            "torso_length": "How long your sweater should be below the armhole. ",
            "sleeve_length": "How long your sleeves should be. ",
            "drop_shoulder_additional_armhole_depth": "Drop shoulder armholes are deeper than set-in sleeve armholes. You can change the amount of additional depth here.",
        }
        for fieldname in help_text_dict:
            self.fields[fieldname].help_text = help_text_dict[fieldname]
        add_help_circles_to_labels(self, help_text_dict)

        # If the design has sleeves, set the choices. If not, remove the field.
        if self.design.has_sleeves():
            self.fields["sleeve_length"].choices = (
                self.design.supported_sleeve_length_choices()
            )
        else:
            del self.fields["sleeve_length"]

        length_html = self._get_optional_lengths_text()

        # Set the torso-length and silhouette choices available.
        self.fields["torso_length"].choices = (
            self.design.supported_torso_length_choices()
        )
        self.fields["silhouette"].choices = self.design.supported_silhouette_choices()
        self.fields["construction"].choices = (
            self.design.supported_construction_choices()
        )

        # Set the garment fit choices available.
        # Include the empty option because we have no grounds for suggesting
        # a default, and an empty default is consistent with the body and
        # swatch fields. If users select the empty default the form will
        # throw a ValidationError, so we don't need to worry about this
        # being passed on to the IGP.
        self.fields["garment_fit"].choices = [
            ("", "---------")
        ] + self.design.supported_fit_choices()

        # Add lengths to drop-shoulder choices
        drop_shoulder_choices = [
            (k, "%s (%s)" % (name, length_fmt(DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[k])))
            for (k, name) in SDC.DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES
        ]

        self.fields["drop_shoulder_additional_armhole_depth"].choices = [
            ("", "---------")
        ] + drop_shoulder_choices

        # Lay out form
        # ----------------------------------------------------------------------

        if "sleeve_length" in list(self.fields.keys()):
            sleeve = "sleeve_length"
        else:
            sleeve = None

        create_body_layout = _make_create_link_layout(create_body_url)
        create_swatch_layout = _make_create_link_layout(create_swatch_url)

        self.helper.layout = Layout(
            Fieldset(
                "",
                "name",
                "body",
                # If body_queryset is empty, the create-body link is
                # already shown in 'body' helptext. So suppress
                # the following instance of it
                create_body_layout if body_queryset else None,
                "swatch",
                # If swatch_queryset is empty, the create-swatch link is
                # already shown in 'swatch' helptext. So suppress
                # the following instance of it
                create_swatch_layout if swatch_queryset else None,
                "silhouette",
                "garment_fit",
                "construction",
                Div(
                    Div(
                        Div(
                            HTML(length_html),
                            css_class="accordion-heading",
                        ),
                        Div(
                            Div(
                                "torso_length",
                                sleeve,
                                "drop_shoulder_additional_armhole_depth",
                                css_class="accordion-inner",
                            ),
                            css_class="accordion-body collapse",
                            css_id="collapseLengths",
                        ),
                        css_class="accordion-group",
                    ),
                    css_class="accordion",
                    css_id="lengths-accordion",
                ),
                css_class="hide-help-text",
            )
        )

        # Update lengths div with sleeve length, if applicable.
        # if 'sleeve_length' in self.fields.keys():
        # I hate this line of code. And its children, and its pets. But
        # this is the API crispy-forms presents me with.
        # If you ever change the Layout() above, this will break, so you'll
        # need to update it accordingly.
        # self.helper.layout[0][4][0][1][0].fields.append('sleeve_length')

        self.helper.add_input(
            Submit(
                REDIRECT_TWEAK,
                "customize fit specifics",
                css_class="btn-customfit-outline",
            )
        )
        self.helper.add_input(
            Submit(
                REDIRECT_APPROVE,
                "Get this pattern!",
                css_class="btn-customfit-action",
            )
        )

    def clean_name(self):
        """
        Ensures that knitters don't have two sweater patterns with the same
        name.
        """
        name = self.cleaned_data["name"]
        if IndividualPattern.live_patterns.filter(user=self.user, name=name):
            raise forms.ValidationError("You already have a pattern by that name.")
        return name

    def clean(self):
        cleaned_data = super(PersonalizeDesignForm, self).clean()

        if "construction" in self.cleaned_data:
            if cleaned_data["construction"] != SDC.CONSTRUCTION_DROP_SHOULDER:
                # Ignore the drop-shoulder armhole-depth
                cleaned_data["drop_shoulder_additional_armhole_depth"] = None

        return cleaned_data


class PersonalizeGradedSweaterDesignForm(forms.ModelForm):
    # Probably different enough from the other Personalize forms to
    # make common-superclasses not worth it

    class Meta:
        model = GradedSweaterPatternSpec
        fields = [
            "name",
            "silhouette",
            "construction",
            "sleeve_length",
            "torso_length",
            "garment_fit",
            "stitch_gauge",
            "row_gauge",
            "drop_shoulder_additional_armhole_depth",
            "gradeset",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")

        super(PersonalizeGradedSweaterDesignForm, self).__init__(*args, **kwargs)

        # If the design has sleeves, set the choices. If not, remove the field.
        if self.design.has_sleeves():
            self.fields["sleeve_length"].choices = (
                self.design.supported_sleeve_length_choices()
            )
        else:
            del self.fields["sleeve_length"]

        # Set the torso-length and silhouette choices available.
        self.fields["torso_length"].choices = (
            self.design.supported_torso_length_choices()
        )
        self.fields["silhouette"].choices = self.design.supported_silhouette_choices()
        self.fields["construction"].choices = (
            self.design.supported_construction_choices()
        )
        self.fields["garment_fit"].choices = self.design.supported_fit_choices()

        # Add lengths to drop-shoulder choices
        drop_shoulder_choices = [
            (k, "%s (%s)" % (name, length_fmt(DROP_SHOULDER_ARMHOLE_DEPTH_INCHES[k])))
            for (k, name) in SDC.DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES
        ]
        self.fields["drop_shoulder_additional_armhole_depth"].choices = [
            ("", "---------")
        ] + drop_shoulder_choices

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))

    def clean_name(self):
        """
        Ensures that knitters don't have two sweater patterns with the same
        name.
        """
        name = self.cleaned_data["name"]
        name_used = False
        if IndividualPattern.live_patterns.filter(user=self.user, name=name).exists():
            name_used = True
        for gp in GradedPattern.objects.filter(name=name).all():
            if gp.user == self.user:
                name_used = True
        if name_used:
            raise forms.ValidationError("You already have a pattern by that name.")
        return name
