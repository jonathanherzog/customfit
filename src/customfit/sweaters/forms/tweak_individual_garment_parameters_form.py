from crispy_forms.bootstrap import AppendedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Button, Div, Fieldset, Layout, Submit
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from customfit.design_wizard.constants import REDIRECT_APPROVE, REDO_AND_APPROVE
from customfit.helpers.form_helpers import wrap_with_units
from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    convert_value_to_imperial,
    convert_value_to_metric,
    round,
)
from customfit.userauth.helpers import unitstring_for_user

from ..helpers.magic_constants import MAXBUSTTOARMPIT
from ..models import SweaterIndividualGarmentParameters

# Pulled out of the form because we need to import this field list elsewhere.
TWEAK_FIELDS_VEST = [
    # As-knit fields
    "bust_width_front",
    "bust_width_back",
    "waist_width_front",
    "waist_width_back",
    "hip_width_front",
    "hip_width_back",
    #'back_cross_back_width',
    "back_neck_opening_width",
    "armhole_depth",
    "below_armhole_straight",
    "front_neck_depth",
    # As-worn fields
    "armpit_height",
    "waist_height_back",
]

TWEAK_FIELDS_SLEEVE_ONLY = [
    # As-knit
    "bicep_width",
    "sleeve_cast_on_width",
    # As-worn
    "sleeve_to_armcap_start_height",
]


# We will remove the vest fields dynamically later if the garment doesn't have
# sleeves. It turns out to be easier to delete unused fields from vests than to
# add them to sleeves, because Meta does some magic in terms of setting up field
# types and labels, and that magic *isn't* performed if we add fields during
# __init__. We like letting Django do this magic for us, so let's let Django do
# magic to all the fields, and then toss the fields we don't use.
TWEAK_FIELDS = TWEAK_FIELDS_VEST + TWEAK_FIELDS_SLEEVE_ONLY


class _TweakSweaterIndividualGarmentParametersBase(forms.ModelForm):
    """
    This form is for people to tweak fit during the pop-the-hood step.
    When reading this form, bear in mind that there are two ways to think about
    the measurements of a garment: as knit, and as worn. The as-knit
    measurements reflect the dimensions the garment would have (after blocking
    and seaming) if you were to put in the table. The as-worn measurements
    reflect the dimensions it will have on the wearer's body. What's the
    difference? Negative ease. A garment has 'negative ease' at a partcular
    point if it is smaller in circumference than the wearer's body is at that
    point. This is possible? Yes, because knitted fabric stretches. When you
    stretch it in one direction though, it will actually shrink in the
    perpendicular direction. So when a garment has negative ease at, say, the
    bust (which is common) then the sweater will grow to match the wearer's bust
    circumference -- but get shorter due to the stretch. In general, *we* want
    to think about as-knit measurements. The IGP model, for example, holds
    as-knit measurements. And in general, and the user will want to think about
    as-worn measurements. But this particular form is an exception. In
    particular,

    * Knitters will want to think about circumferences in an as-knit fashion:
    broken out into front and back portions, and in terms of the as-knit
    measurements. This form will handle those in a straightforward way.

    * On the other hand, they will want to think about the lengths in as-worn
    terms. When the form gets initial values from the IGP instance, it will
    need to modify some of them from as-knit to as-worn. Likewise, when the form
    stores values in the IGP, it will need to ensure that they are translated
    from the as-worn values to the as-knit values. (Mostly, it uses logic
    already in the IGP.)

    """

    shoulder_width = forms.FloatField(min_value=0)

    class Meta:
        model = SweaterIndividualGarmentParameters

        fields = TWEAK_FIELDS

        labels = {
            "bust_width_front": "front bust/chest",
            "bust_width_back": "back bust/chest",
            #'back_cross_back_width': 'cross-chest',
            "front_neck_depth": "neck depth (from shoulder)",
            "waist_height_back": "hem to waist",
            "bicep_width": "bicep circumference",
            "sleeve_to_armcap_start_height": "sleeve to armhole",
            "sleeve_cast_on_width": "sleeve cast on",
            "armpit_height": "hem to armhole",
            "below_armhole_straight": "minimum distance worked straight before armhole",
        }

        help_texts = {
            #'back_cross_back_width': 'Measure across the chest',
            "shoulder_width": "your cross-chest is two shoulder widths (left "
            "and right) plus your neck opening width"
        }

    def _display_as_worn_parameters(self):
        """
        We store as-knit parameters, but we want to display as-worn parameters
        to the user; yarn is stretchy, and users' physical intuition for some
        parameters will reflect their understanding of how the garment looks
        when it is stretched out on a 3D body.
        """
        (readj_waist_height, _, readj_armpit_height, readj_sleeve_length) = (
            self.instance.unadjust_lengths_for_negative_ease()
        )

        self.initial["armpit_height"] = readj_armpit_height

        # Note: no need to set waist_height_front, since we're not
        # showing it to the user. We're only showing waist_height_back
        # under the name 'hem to waist'. That is, the form is only
        # showing *one* waist-height value and
        # we've chosen the back height as the one to show. When we save
        # this form (see save()) we will copy the back-waist height into
        # the waist_height_front value of the IGP, thus ensuring that
        # the IGP instance has valid values for both front and back heights,
        # that they are the same, and that they are the (adjusted) height
        # that the user selected.
        self.initial["waist_height_back"] = readj_waist_height

        if self.instance.has_sleeves():
            self.initial["sleeve_to_armcap_start_height"] = readj_sleeve_length
        else:
            del self.fields["bicep_width"]
            del self.fields["sleeve_to_armcap_start_height"]
            del self.fields["sleeve_cast_on_width"]

    def _convert_to_metric(self):
        for fieldkey in self._meta.fields:
            modelfield = SweaterIndividualGarmentParameters._meta.get_field(fieldkey)
            dimension = getattr(modelfield, "dimension", None)
            if dimension:
                orig_value = self.initial[fieldkey]
                self.initial[fieldkey] = convert_value_to_metric(orig_value, dimension)

    def _set_up_circs_and_eases(self, conversion, precision):
        circs_and_eases = {}
        circs_and_eases["bust"] = {}
        circs_and_eases["bust"]["circ"] = round(
            self.instance.bust_circ_total * conversion, ROUND_ANY_DIRECTION, precision
        )
        circs_and_eases["bust"]["ease"] = round(
            self.instance.bust_ease * conversion, ROUND_ANY_DIRECTION, precision
        )

        # Only hourglass/half-hourglass designs have waist parameters. Designs with waist parameters
        # should have waist ease logic; designs without waist parameters should not
        # present any to the user.
        if self.instance.waist_width_front:
            circs_and_eases["waist"] = {}
            circs_and_eases["waist"]["circ"] = round(
                self.instance.waist_circ_total * conversion,
                ROUND_ANY_DIRECTION,
                precision,
            )
            circs_and_eases["waist"]["ease"] = round(
                self.instance.waist_ease * conversion, ROUND_ANY_DIRECTION, precision
            )
        else:
            del self.fields["waist_width_front"]
            del self.fields["waist_width_back"]

        circs_and_eases["hip"] = {}
        circs_and_eases["hip"]["circ"] = round(
            self.instance.hip_circ_total * conversion, ROUND_ANY_DIRECTION, precision
        )
        circs_and_eases["hip"]["ease"] = round(
            self.instance.hip_ease * conversion, ROUND_ANY_DIRECTION, precision
        )

        if self.instance.has_sleeves():
            circs_and_eases["bicep"] = {}
            circs_and_eases["bicep"]["ease"] = round(
                self.instance.bicep_ease * conversion, ROUND_ANY_DIRECTION, precision
            )

            circs_and_eases["sleeve"] = {}
            circs_and_eases["sleeve"]["ease"] = round(
                self.instance.sleeve_ease * conversion, ROUND_ANY_DIRECTION, precision
            )

        circs_and_eases["cross_chest"] = round(
            self.instance.back_cross_back_width * conversion,
            ROUND_ANY_DIRECTION,
            precision,
        )
        return circs_and_eases

    def _initialize_crispy_form(self, circs_and_eases):
        """
        Set up fields required by all sweater types.
        """
        # The + / - icons after each field are applied in JS in the front end.
        # Just turned out to be easier that way.
        self.helper.layout = Layout(
            Fieldset(
                "DETAIL - CIRCUMFERENCES & EASE",
                Div(
                    HTML(
                        "<small>You can adjust the front and back widths separately for full bust/chest, waist, and hip. The eases and full circumferences will auto-update.</small>"
                    ),
                    css_class="clearfix text-center col-md-7 col-md-offset-1 col-xs-12 margin-bottom-20",
                ),
                Div(
                    Div(
                        HTML(
                            '<strong>Full bust/chest <span class="display_circ">%s</span> {{ units }} '
                            '/ <span class="display_ease">%s</span> {{ units }} ease</strong>'
                            % (
                                circs_and_eases["bust"]["circ"],
                                circs_and_eases["bust"]["ease"],
                            )
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "bust_width_front",
                    "bust_width_back",
                    css_class="clearfix margin-top-20 circ-group ease-group",
                ),
                Div(
                    Div(
                        HTML(
                            '<strong>Full hip cast-on <span class="display_circ">%s</span> {{ units }} '
                            '/ <span class="display_ease">%s</span> {{ units }} ease</strong>'
                            % (
                                circs_and_eases["hip"]["circ"],
                                circs_and_eases["hip"]["ease"],
                            )
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "hip_width_front",
                    "hip_width_back",
                    css_class="clearfix margin-top-20 circ-group ease-group",
                ),
                css_class="hide-help-text margin-bottom-20",
            ),
            Fieldset(
                "DETAIL - LENGTHS",
                Div(
                    Div(
                        HTML(
                            "<small>Your CustomFit pattern lengths directly correspond to the lengths in your body measurement set.</small>"
                        ),
                        css_class="clearfix text-center col-md-7 col-md-offset-1 col-xs-12 margin-bottom-20",
                    ),
                    css_class="row",
                ),
                Div(
                    "armhole_depth",
                    "front_neck_depth",
                    css_class="margin-top-40 clearfix",
                ),
                css_class="hide-help-text",
            ),
            Fieldset(
                "DETAIL - OTHER",
                Div(
                    Div(
                        HTML(
                            "<small>Optionally adjust the distance between the armhole edges on the front and back of your sweater.</small>"
                        ),
                        css_class="clearfix text-center col-md-7 col-md-offset-1 col-xs-12 margin-bottom-20",
                    ),
                    css_class="row",
                ),
                Div(
                    Div(
                        HTML(
                            '<strong>Cross-chest <span id="display_cross_chest">%s</span> {{ units }}</strong>'
                            % circs_and_eases["cross_chest"]
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "back_neck_opening_width",
                    "shoulder_width",
                    css_class="margin-top-40 clearfix",
                    css_id="cross_chest",
                ),
                css_class="hide-help-text",
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
                css_class="col-md-8 col-xs-12 margin-bottom-20",
            ),
        )

    def _add_sweater_length_parameters(self, circs_and_eases):
        """
        Hourglass/half-hourglass designs break sweater length into hem->waist and
        waist->armhole, and users may wish to independently adjust these.
        Other designs only have a single waist->armhole value.
        """
        if self.instance.waist_height_back:
            self.helper.layout[1].insert(
                1,
                Div(
                    Div(
                        Div(
                            HTML(
                                '<strong>Waist to armhole <span id="waist_to_armhole"></span> {{ units }}</strong>'
                            ),
                            css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                        ),
                        css_class="clearfix row margin-top-20",
                    ),
                    Div(
                        "waist_height_back",
                        "armpit_height",
                        css_class="margin-top-40 clearfix",
                    ),
                ),
            )

        else:
            self.helper.layout[1].insert(
                1,
                Div(
                    "armpit_height",
                    css_class="margin-top-40 clearfix",
                ),
            )

            del self.fields["waist_height_back"]

        # Also, non-straight sweaters should have a below-armhole-straight
        # parameter and explanation. Leave that section as-is.
        if self.instance.get_spec_source().is_straight:
            del self.fields["below_armhole_straight"]
        else:
            self.helper.layout[2] = Fieldset(
                "DETAIL - OTHER",
                Div(
                    Div(
                        HTML(
                            "<small>Optionally adjust the distance between the armhole edges on the front of your sweater, or the distance between the end of bust increases and the armhole shaping.</small>"
                        ),
                        css_class="clearfix text-center col-md-7 col-md-offset-1 col-xs-12 margin-bottom-20",
                    ),
                    css_class="row",
                ),
                Div(
                    Div(
                        HTML(
                            '<strong>Cross-chest <span id="display_cross_chest">%s</span> {{ units }}</strong>'
                            % circs_and_eases["cross_chest"]
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "shoulder_width",
                    "back_neck_opening_width",
                    css_class="margin-top-40 clearfix",
                    css_id="cross_chest",
                ),
                Div("below_armhole_straight", css_class="margin-top-40 clearfix"),
                css_class="hide-help-text",
            )

    def _add_sleeve_parameters(self, circs_and_eases):
        self.helper.layout[1][1].insert(1, "sleeve_to_armcap_start_height")
        self.helper.layout.insert(
            1,
            Div(
                Div(
                    Div(
                        HTML(
                            '<strong>bicep <span class="display_ease">%s</span> {{ units }} ease</strong>'
                            % (circs_and_eases["bicep"]["ease"])
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "bicep_width",
                    css_class="clearfix margin-top-20 ease-group",
                ),
                Div(
                    Div(
                        HTML(
                            '<strong>sleeve cast on <span class="display_ease">%s</span> {{ units }} ease</strong>'
                            % (circs_and_eases["sleeve"]["ease"])
                        ),
                        css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                    ),
                    "sleeve_cast_on_width",
                    css_class="clearfix margin-top-20 ease-group",
                ),
                css_class="hide-help-text",
            ),
        )

    def _add_waist_parameters(self, circs_and_eases):
        # It's important to _insert_ and not _extend_, because we need this to be
        # a separate div from the bust div, not contained within it - if they
        # are in the same circ-group div, then the JavaScript will update bust
        # and waist circs with the sum of ALL of them when any of them update.
        self.helper.layout[0].insert(
            2,
            Div(
                Div(
                    HTML(
                        '<strong>Full waist <span class="display_circ">%s</span> {{ units }} '
                        '/ <span class="display_ease">%s</span> {{ units }} ease</strong>'
                        % (
                            circs_and_eases["waist"]["circ"],
                            circs_and_eases["waist"]["ease"],
                        )
                    ),
                    css_class="text-right text-centered-phone col-xs-12 col-md-6 margin-bottom-5 faux-label",
                ),
                "waist_width_front",
                "waist_width_back",
                css_class="clearfix margin-top-20 circ-group ease-group",
            ),
        )

    def __init__(self, user, *args, **kwargs):

        super(_TweakSweaterIndividualGarmentParametersBase, self).__init__(
            *args, **kwargs
        )

        if self.instance is not None:
            self._display_as_worn_parameters()

        # We'll need these for calculating circumference and ease values
        # and displaying them to users in appropriate units.
        if user.profile.display_imperial:
            conversion = 1.0
            precision = 0.25

        else:
            conversion = 2.54
            precision = 0.5
            self._convert_to_metric()

        # This won't be caught by convert_to_metric since it doesn't have
        # a corresponding modelfield.
        total_shoulder_width = conversion * (
            self.instance.back_cross_back_width - self.instance.back_neck_opening_width
        )
        one_shoulder_width = round(
            0.5 * total_shoulder_width, ROUND_DOWN, precision
        )
        self.fields["shoulder_width"].initial = one_shoulder_width

        #
        # Crispy forms ahoy!
        # ---------------------------------------------------------------------

        self.helper = FormHelper()
        self.helper.form_class = "form-horizontal fix-firefox-fieldsets"
        self.helper.label_class = "col-md-3 col-xs-4"
        self.helper.field_class = "col-md-3 col-xs-6"

        circs_and_eases = self._set_up_circs_and_eases(conversion, precision)
        self._initialize_crispy_form(circs_and_eases)
        self._add_sweater_length_parameters(circs_and_eases)

        if self.instance.waist_width_front:
            self._add_waist_parameters(circs_and_eases)

        if self.instance.has_sleeves():
            self._add_sleeve_parameters(circs_and_eases)

        help_dict = {key: self.fields[key].help_text for key in self.fields}
        wrap_with_units(self, user, help_dict)

        # Because shoulder_width isn't on the model, it won't be caught by
        # the unit wrapping logic; we need to add this explicitly.
        units = unitstring_for_user("length", user)
        self.helper["shoulder_width"].wrap(AppendedText, units)

    def clean_below_armhole_straight(self):
        # Complain if the user asks for too much straight-height below the armhole.
        below_armhole_straight = self.cleaned_data["below_armhole_straight"]
        limit = MAXBUSTTOARMPIT
        if not self.instance.user.profile.display_imperial:
            limit = limit * 2.54
        if below_armhole_straight > limit:
            raise ValidationError("This must be less than 5 inches / 12.7 cm")

        return below_armhole_straight

    def clean_back_neck_opening_width(self):
        back_neck_opening_width = self.cleaned_data["back_neck_opening_width"]
        if not self.instance.user.profile.display_imperial:
            limit = 7.5
        else:
            limit = 3

        if back_neck_opening_width < limit:
            raise ValidationError("This must be at least 3 inches / 7.5 cm")

        return back_neck_opening_width

    def clean_shoulder_width(self):
        shoulder_width = self.cleaned_data["shoulder_width"]
        if not self.instance.user.profile.display_imperial:
            limit = 1.25
        else:
            limit = 0.5

        if shoulder_width < limit:
            raise ValidationError("This must be at least 0.5 inches / 1.25 cm")

        return shoulder_width

    def save(self, *args, **kwargs):
        instance = super(_TweakSweaterIndividualGarmentParametersBase, self).save(
            *args, **kwargs
        )

        # The back neck opening width has already been written to the instance
        # since it's a modelfield, but we need to write an appropriate
        # cross back width. Also we need to do this *before* we do metric
        # conversion, since the values in cleaned_data are in user units,
        # which may differ from model units.
        instance.back_cross_back_width = (
            2 * (self.cleaned_data["shoulder_width"])
            + self.cleaned_data["back_neck_opening_width"]
        )

        # If the user entered the values in metric, switch back to imperial.
        # *It is important to do this before adjusting the lengths because the
        # length adjustment function assumes inches.* If you let it adjust cm,
        # the adjusted lengths will grow without bound as users iterate, and
        # saving the field even once will result in a geometrically impossible
        # sweater.
        if not self.instance.user.profile.display_imperial:
            check_fields = self._meta.fields + ["back_cross_back_width"]

            for fieldkey in check_fields:
                modelfield = SweaterIndividualGarmentParameters._meta.get_field(
                    fieldkey
                )
                dimension = getattr(modelfield, "dimension", None)
                if dimension:
                    metric_value = getattr(instance, modelfield.name)
                    setattr(
                        instance,
                        fieldkey,
                        convert_value_to_imperial(metric_value, dimension),
                    )

        # Currently, front-waist and back-waist are always at the same height.
        # See comment in __init__(), above.
        instance.waist_height_front = instance.waist_height_back

        # Now adjust the as-worn measurements to as-knit
        instance.adjust_lengths_for_negative_ease()

        instance.save()
        return instance


class TweakSweaterIndividualGarmentParameters(
    _TweakSweaterIndividualGarmentParametersBase
):

    def _submit_button_name(self):
        return REDIRECT_APPROVE

    def _submit_button_value(self):
        return "proceed with these changes"


class TweakSweaterRedoIndividualGarmentParameters(
    _TweakSweaterIndividualGarmentParametersBase
):
    def _submit_button_name(self):
        return REDO_AND_APPROVE

    def _submit_button_value(self):
        return "redo with these changes"
