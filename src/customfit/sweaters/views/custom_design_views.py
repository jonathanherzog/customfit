import logging

from django.urls import reverse

from customfit.design_wizard.views import CustomDesignCreateView, CustomDesignUpdateView
from customfit.helpers.math_helpers import convert_to_imperial, convert_value_to_metric

from ..forms import CARDIGAN, PULLOVER, SLEEVED, VEST, PatternSpecForm
from ..helpers import sweater_design_choices as SDC
from ..models import SweaterPatternSpec
from ..models.patternspec import MAKE_YOUR_OWN_SWEATER
logger = logging.getLogger(__name__)

#
# Views for creating custom designs
# -----------------------------------------------------------------------------


class CustomSweaterDesignViewMixin(object):

    model = SweaterPatternSpec
    garment_name = "sweaters"
    form_class = PatternSpecForm
    template_name = "sweaters/patternspec_create_form.html"

    def get_myo_design(self):
        return MAKE_YOUR_OWN_SWEATER

    def get_context_data(self, **kwargs):
        context = super(CustomSweaterDesignViewMixin, self).get_context_data(**kwargs)
        context["help_text"] = SDC.HELP_TEXT
        context["scripts"] = ["js/design_wizard.js"]
        return context

    def get_form_kwargs(self):
        kwargs = super(CustomSweaterDesignViewMixin, self).get_form_kwargs()

        this_url_path = self._get_this_url_path(self.garment_name)
        create_body_url = reverse("bodies:body_create_view") + "?next=" + this_url_path
        create_swatch_url = (
            reverse("swatches:swatch_create_view") + "?next=" + this_url_path
        )

        update = {
            "user": self.request.user,
            "create_body_url": create_body_url,
            "create_swatch_url": create_swatch_url,
        }
        kwargs.update(update)

        return kwargs

    def form_invalid(self, form):

        if "__all__" in list(form._errors.keys()):
            # We're putting our own error messages around garment type in the
            # form validation; since we split apart cardigan/pullover and
            # sleeves/vest we provide specific validation messages for each,
            # and we don't want to inherit the overall model validation error.
            remove_me = "The garment must either have sleeves or be a vest."
            new_list = [x for x in form._errors["__all__"] if x != remove_me]
            form._errors["__all__"] = new_list
        return super(CustomSweaterDesignViewMixin, self).form_invalid(form)


class CustomSweaterDesignCreateView(
    CustomSweaterDesignViewMixin, CustomDesignCreateView
):

    def form_valid(self, form):

        convert_to_imperial(form.cleaned_data, SweaterPatternSpec, self.request.user)
        design_params = form.cleaned_data
        design_params["garment_type"] = form.instance.garment_type
        patternspec = SweaterPatternSpec(**design_params)
        patternspec.user = self.request.user
        patternspec.full_clean()

        self.object = patternspec
        form.instance = patternspec
        return super(CustomSweaterDesignCreateView, self).form_valid(form)


class CustomSweaterDesignUpdateView(
    CustomSweaterDesignViewMixin, CustomDesignUpdateView
):

    def get_initial(self):
        initial = super(CustomSweaterDesignUpdateView, self).get_initial()

        patternspec = self.get_object()
        # The form handles cardigan/pullover and sleeved/vest differently
        # than the model, so we need to populate those fields manually.
        if patternspec.is_cardigan():
            initial["garment_type_body"] = CARDIGAN
        else:
            initial["garment_type_body"] = PULLOVER

        if patternspec.has_sleeves():
            initial["garment_type_sleeves"] = SLEEVED
        else:
            initial["garment_type_sleeves"] = VEST

        # Convert values to metric if appropriate
        if not self.request.user.profile.display_imperial:
            for field in patternspec.__class__._meta.fields:
                dimension = getattr(field, "dimension", None)
                if dimension:
                    orig_value = getattr(patternspec, field.name)
                    initial[field.name] = convert_value_to_metric(orig_value, dimension)

        return initial
