import logging

from django.urls import reverse

from customfit.design_wizard.views import CustomDesignCreateView
from customfit.helpers.math_helpers import convert_to_imperial

#
from ..forms import CustomCowlDesignForm
from ..models import CowlPatternSpec

#
#
logger = logging.getLogger(__name__)

#
# Views for creating custom designs
# -----------------------------------------------------------------------------


class CustomCowlDesignCreateView(CustomDesignCreateView):

    form_class = CustomCowlDesignForm
    template_name = "design_wizard/patternspec_create_form.html"

    model = CowlPatternSpec
    garment_name = "cowls"

    def get_form_kwargs(self):
        kwargs = super(CustomCowlDesignCreateView, self).get_form_kwargs()

        this_url_path = self._get_this_url_path(self.garment_name)
        create_swatch_url = (
            reverse("swatches:swatch_create_view") + "?next=" + this_url_path
        )

        update = {"user": self.request.user, "create_swatch_url": create_swatch_url}
        kwargs.update(update)

        return kwargs

    def form_valid(self, form):

        convert_to_imperial(form.cleaned_data, CowlPatternSpec, self.request.user)
        design_params = form.cleaned_data
        patternspec = CowlPatternSpec(**design_params)
        patternspec.user = self.request.user
        patternspec.full_clean()

        self.object = patternspec
        form.instance = patternspec
        return super(CustomCowlDesignCreateView, self).form_valid(form)
