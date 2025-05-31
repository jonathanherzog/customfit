import logging
from datetime import date

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Fieldset, Layout, Submit
from django import forms

from customfit.design_wizard.constants import (
    REDIRECT_APPROVE,
    REDIRECT_TWEAK,
    REDO_AND_APPROVE,
    REDO_AND_TWEAK,
)
from customfit.design_wizard.forms import (
    _get_gauge_help_text,
    _IndividualQuerysetMixin,
    _make_create_link_layout,
)
from customfit.helpers.form_helpers import wrap_with_units
from customfit.helpers.math_helpers import (
    convert_value_to_imperial,
    convert_value_to_metric,
)
from customfit.patterns.models import GradedPattern, IndividualPattern
from customfit.stitches.models import Stitch
from customfit.swatches.models import Swatch

from .helpers import (
    COWL_CIRC_EXTRA_SMALL,
    COWL_CIRC_LARGE,
    COWL_CIRC_MEDIUM,
    COWL_CIRC_SMALL,
    COWL_HEIGHT_AVERAGE,
    COWL_HEIGHT_EXTRA_TALL,
    COWL_HEIGHT_SHORT,
    COWL_HEIGHT_TALL,
    decorate_circ_choices_for_form,
    decorate_height_choices_for_form,
)
from .models import (
    CowlIndividualGarmentParameters,
    CowlPatternSpec,
    CowlRedo,
    GradedCowlPatternSpec,
)

logger = logging.getLogger(__name__)

USER_FACING_HEIGHT_CHOICES = decorate_height_choices_for_form(
    [COWL_HEIGHT_SHORT, COWL_HEIGHT_AVERAGE, COWL_HEIGHT_TALL, COWL_HEIGHT_EXTRA_TALL]
)

USER_FACING_CIRC_CHOICES = decorate_circ_choices_for_form(
    [COWL_CIRC_EXTRA_SMALL, COWL_CIRC_SMALL, COWL_CIRC_MEDIUM, COWL_CIRC_LARGE]
)


class PersonalizeDesignForm(forms.ModelForm, _IndividualQuerysetMixin):

    class Meta:
        model = CowlPatternSpec
        fields = ("name", "swatch", "circumference", "height")

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
    # * _get_swatch_queryset()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")
        create_swatch_url = kwargs.pop("create_swatch_url")

        super(PersonalizeDesignForm, self).__init__(*args, **kwargs)

        # Set up available options in drop-down menus
        # ----------------------------------------------------------------------

        # Since we won't let them enter duplicate pattern names, let's
        # default to something unlikely to be a duplicate, if they already have
        # a pattern with the same name as the design.
        name = self.initial.get("name", None)
        if name:
            if IndividualPattern.live_patterns.filter(
                user=self.user, name=name
            ).exists():
                self.initial["name"] += " " + str(date.today())

        # Set label, menu & help-text for swatch
        self.fields["swatch"].label = "gauge"
        swatch_queryset = self._get_swatch_queryset()
        self.fields["swatch"].queryset = swatch_queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, create_swatch_url
        )

        # replace default height/circ choices with decorated ones
        self.fields["height"].choices = USER_FACING_HEIGHT_CHOICES
        self.fields["circumference"].choices = USER_FACING_CIRC_CHOICES

        # Lay out form
        # ----------------------------------------------------------------------

        create_swatch_layout = _make_create_link_layout(create_swatch_url)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "",
                "name",
                "swatch",
                # If swatch_queryset is empty, the create-swatch link is
                # already shown in 'swatch' helptext. So suppress
                # the following instance of it
                create_swatch_layout if swatch_queryset else None,
                "circumference",
                "height",
            )
        )

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
        if IndividualPattern.live_patterns.filter(user=self.user, name=name).exists():
            raise forms.ValidationError("You already have a pattern by that name.")
        return name


class PersonalizeGradedDesignForm(forms.ModelForm):
    # Probably different enough from the other Personalize forms to
    # make common-superclasses not worth it

    class Meta:
        model = GradedCowlPatternSpec
        fields = ["name", "row_gauge", "stitch_gauge"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")

        super(PersonalizeGradedDesignForm, self).__init__(*args, **kwargs)

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


class CustomCowlDesignForm(forms.ModelForm):

    class Meta:
        model = CowlPatternSpec
        fields = [
            "name",
            "swatch",
            "circumference",
            "height",
            "main_stitch",
            "edging_stitch",
            "edging_stitch_height",
            "cast_on_x_mod",
            "cast_on_mod_y",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.create_swatch_url = kwargs.pop("create_swatch_url")

        super(CustomCowlDesignForm, self).__init__(*args, **kwargs)

        self.instance.user = self.user

        self._limit_querysets()
        self._lay_out_form()
        self._set_help_texts_and_labels()

        wrap_with_units(self, self.user, {})

    def _get_swatches(self):
        # All swatches of this user that *don't* have a customer linkage
        return Swatch.objects.filter(user=self.user)

    def _lay_out_form(self):

        create_swatch_layout = _make_create_link_layout(self.create_swatch_url)
        swatch_queryset = self.fields["swatch"].queryset

        self.helper = FormHelper()

        self.helper.label_class = "col-sm-4 col-xs-12"
        self.helper.field_class = "col-sm-8 col-xs-12"

        self.helper.layout = Layout(
            Fieldset(
                "",
                "name",
                "swatch",
                # If swatch_queryset is empty, the create-swatch link is
                # already shown in 'swatch' helptext. So suppress
                # the following instance of it
                create_swatch_layout if swatch_queryset else None,
                "circumference",
                "height",
                "main_stitch",
                "edging_stitch",
                "edging_stitch_height",
                Fieldset(
                    "Stitch count multiples",
                    HTML(
                        "<p>If you'd like to force your stitch counts to be a multiple of x plus y stitches in order to accommodate a stitch pattern, please enter both x and y below. (If you don't want to adjust stitch counts, leave these fields as-is.)</p>"
                    ),
                    "cast_on_mod_y",
                    "cast_on_x_mod",
                ),
            )
        )

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

    def _limit_querysets(self):
        # Limit swatch and body to only those belonging to the user.
        self.fields["swatch"].queryset = self._get_swatches()

        # Limit stitches as below"
        #
        self.fields["edging_stitch"].queryset = (
            Stitch.public_accessory_edge_stitches.all()
        )
        self.fields["main_stitch"].queryset = (
            Stitch.public_accessory_main_stitches.all()
        )

    def _set_help_texts_and_labels(self):
        swatch_queryset = self.fields["swatch"].queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, self.create_swatch_url
        )

        # The term 'swatch' is historical. Even though we're asking for a Swatch instance, the user
        # facing name is 'gauge'
        self.fields["swatch"].label = "gauge"

        self.fields["edging_stitch_height"].help_text = (
            "How high you'd like the edging stitch pattern to be. Note: will be applied twice-- once at cast on and once at cast off."
        )

        self.fields["cast_on_x_mod"].label = "plus"

        self.fields["cast_on_mod_y"].label = "multiple of:"

        # replace default height/circ choices with decorated ones
        self.fields["height"].choices = USER_FACING_HEIGHT_CHOICES
        self.fields["circumference"].choices = USER_FACING_CIRC_CHOICES

    # TODO: copied from sweater custom-design form. Factor out?
    def clean_name(self):
        name = self.cleaned_data["name"]
        if IndividualPattern.live_patterns.filter(user=self.user, name=name):
            raise forms.ValidationError("You already have a pattern by that name.")
        return name


class TweakCowlIndividualGarmentParametersBase(forms.ModelForm):
    class Meta:
        model = CowlIndividualGarmentParameters
        fields = ["height", "circumference", "edging_height"]

    def __init__(self, user, *args, **kwargs):

        super(TweakCowlIndividualGarmentParametersBase, self).__init__(*args, **kwargs)

        if not user.profile.display_imperial:
            self._convert_to_metric()

        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal fix-firefox-fieldsets"
        self.helper.label_class = "col-md-3 col-xs-4"
        self.helper.field_class = "col-md-3 col-xs-6"
        self.helper.layout = Layout(
            Div(
                "height",
                "circumference",
                "edging_height",
                css_class="clearfix hide-help-text",
            ),
            Div(
                Div(
                    Button(
                        "restore",
                        "Restore original values",
                        css_class="btn-customfit-outline",
                    ),
                    Submit(
                        self._submit_button_name(),
                        self._submit_button_value(),
                        css_class="btn-customfit-action",
                    ),
                    css_class="text-center",
                ),
                css_class="clearfix col-md-8 col-xs-12 margin-bottom-20",
            ),
        )

        help_dict = {key: self.fields[key].help_text for key in self.fields}
        wrap_with_units(self, user, help_dict)

    # TODO: copied from sweaters.tweak_igp_form.py. Factor out somewhere?
    def _convert_to_metric(self):
        for fieldkey in self._meta.fields:
            modelfield = CowlIndividualGarmentParameters._meta.get_field(fieldkey)
            dimension = getattr(modelfield, "dimension", None)
            if dimension:
                orig_value = self.initial[fieldkey]
                self.initial[fieldkey] = convert_value_to_metric(orig_value, dimension)

    # TODO: heavily duplicates sweaters.tweak_igp_form.py. Factor out somewhere?
    def save(self, *args, **kwargs):
        instance = super(TweakCowlIndividualGarmentParametersBase, self).save(
            *args, **kwargs
        )

        # If the user entered the values in metric, switch back to imperial.
        if not self.instance.user.profile.display_imperial:
            for fieldkey in self._meta.fields:
                modelfield = CowlIndividualGarmentParameters._meta.get_field(fieldkey)
                dimension = getattr(modelfield, "dimension", None)
                if dimension:
                    metric_value = getattr(instance, modelfield.name)
                    setattr(
                        instance,
                        fieldkey,
                        convert_value_to_imperial(metric_value, dimension),
                    )

            instance.save()

        return instance


class TweakCowlIndividualGarmentParameters(TweakCowlIndividualGarmentParametersBase):

    def _submit_button_name(self):
        return REDIRECT_APPROVE

    def _submit_button_value(self):
        return "proceed with these changes"


class TweakCowlRedoIndividualGarmentParameters(
    TweakCowlIndividualGarmentParametersBase
):
    def _submit_button_name(self):
        return REDO_AND_APPROVE

    def _submit_button_value(self):
        return "redo with these changes"


class CowlRedoForm(forms.ModelForm, _IndividualQuerysetMixin):

    class Meta:
        model = CowlRedo
        fields = ("swatch", "height", "circumference")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.pattern = kwargs.pop("pattern")

        create_swatch_url = kwargs.pop("create_swatch_url")

        super(CowlRedoForm, self).__init__(*args, **kwargs)

        # Set up fields
        self.fields["swatch"].label = "gauge"
        swatch_queryset = self._get_swatch_queryset()
        self.fields["swatch"].queryset = swatch_queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, create_swatch_url
        )

        # Make HTML for 'make new swatch'

        create_swatch_layout = _make_create_link_layout(create_swatch_url)

        layout_fields = [
            "swatch",
            # If swatch_queryset is empty, the create-swatch link is
            # already shown in 'swatch' helptext. So suppress
            # the following instance of it
            create_swatch_layout if swatch_queryset else None,
            "height",
            "circumference",
            FormActions(
                Submit(
                    REDO_AND_TWEAK,
                    "customize fit specifics",
                    css_class="btn-customfit-outline",
                ),
                Submit(REDO_AND_APPROVE, "redo!", css_class="btn-customfit-action"),
            ),
        ]
        # Lay out the form
        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_fields)

    # Note: not copied from elsewhere. Cannot copy from either _PersonalizeDesignForm or
    # _PatternSpecFormBase since (here) we need to handle both the case where the pattern
    # came from a design and the case where it did not.
    def filter_compatible_swatches(self, swatch_queryset):
        design = self.pattern.get_design()
        compatible_swatches = (
            [s for s in swatch_queryset if design.compatible_swatch(s)]
            if design
            else swatch_queryset
        )
        compatible_swatch_pks = [swatch.pk for swatch in compatible_swatches]
        # Note: we need to return a queryset
        return Swatch.objects.filter(pk__in=compatible_swatch_pks).order_by("name")
