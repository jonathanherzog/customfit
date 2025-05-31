import logging

from crispy_forms.bootstrap import Div, FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Layout, Submit
from django import forms

from customfit.design_wizard.constants import REDO_AND_APPROVE, REDO_AND_TWEAK
from customfit.design_wizard.forms import (
    _BodyOptionsMixin,
    _get_body_help_text,
    _get_gauge_help_text,
    _IndividualQuerysetMixin,
    _make_create_link_layout,
)
from customfit.helpers.form_helpers import add_help_circles_to_labels, wrap_with_units
from customfit.swatches.models import Swatch

from ..helpers import sweater_design_choices as SDC
from ..models import SweaterRedo

logger = logging.getLogger(__name__)


class SweaterRedoForm(forms.ModelForm, _BodyOptionsMixin, _IndividualQuerysetMixin):

    # Subclasses need to implement:
    # * _get_body_queryset
    # * _get_swatch_queryset

    class Meta:
        model = SweaterRedo
        fields = (
            "body",
            "swatch",
            "garment_fit",
            "torso_length",
            "sleeve_length",
            "neckline_depth",
            "neckline_depth_orientation",
        )

    HELP_TEXT = {}

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.pattern = kwargs.pop("pattern")

        create_body_url = kwargs.pop("create_body_url")
        create_swatch_url = kwargs.pop("create_swatch_url")

        self.user = self.pattern.user
        super(SweaterRedoForm, self).__init__(*args, **kwargs)

        # Set up fields
        body_queryset = self._get_body_queryset()
        self.fields["body"].queryset = body_queryset
        self.fields["body"].help_text = _get_body_help_text(
            body_queryset, create_body_url
        )

        self.fields["swatch"].label = "gauge"
        swatch_queryset = self._get_swatch_queryset()
        self.fields["swatch"].queryset = swatch_queryset
        self.fields["swatch"].help_text = _get_gauge_help_text(
            self.user, swatch_queryset, create_swatch_url
        )

        self.fields["torso_length"].label = "sweater length"

        # Make HTML for 'make new body/swatch'

        create_body_layout = _make_create_link_layout(create_body_url)
        create_swatch_layout = _make_create_link_layout(create_swatch_url)

        # Set the available fits according to the silhouette of the pattern
        self.fields["garment_fit"].choices = self.filter_compatible_fits

        layout_fields = [
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
            "garment_fit",
            "torso_length",
            "sleeve_length",
            Div(
                HTML(
                    '<label for="id_neckline_depth" class="control-label  requiredField">Necklne shaping starts:<span class="asteriskField">*</span> </label>'
                ),
                Div(
                    Div("neckline_depth", css_class="col-md-6"),
                    Div("neckline_depth_orientation", css_class="col-md-6"),
                    css_class="row",
                ),
            ),
            FormActions(
                Submit(
                    REDO_AND_TWEAK,
                    "customize fit specifics",
                    css_class="btn-customfit-outline",
                ),
                Submit(REDO_AND_APPROVE, "redo!", css_class="btn-customfit-action"),
            ),
        ]

        # Remove field-specific labels for neckline fields
        self.fields["neckline_depth"].label = False
        self.fields["neckline_depth_orientation"].label = False

        if self.pattern.has_sleeves():
            self.fields["sleeve_length"].required = True
        else:
            layout_fields.remove("sleeve_length")
            if "sleeve_length" in self.fields:
                del self.fields["sleeve_length"]

        # Lay out the form
        self.helper = FormHelper()
        self.helper.layout = Layout(*layout_fields)
        wrap_with_units(self, self.user, self.HELP_TEXT)
        add_help_circles_to_labels(self, self.HELP_TEXT)

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

    def filter_compatible_fits(self):
        pspec = self.pattern.get_spec_source()
        if pspec.is_hourglass or pspec.is_half_hourglass:
            return SDC.GARMENT_FIT_CHOICES_HOURGLASS
        else:
            return SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS
