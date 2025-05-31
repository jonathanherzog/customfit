import logging

import customfit.design_wizard.views as dwviews
from customfit.design_wizard.views.helpers import _return_post_design_redirect_url
from customfit.graded_wizard.views import PersonalizeGradedDesignView

from ..forms import CowlRedoForm, PersonalizeDesignForm, PersonalizeGradedDesignForm
from ..models import CowlDesignBase, CowlPatternSpec, CowlRedo, GradedCowlPatternSpec

logger = logging.getLogger(__name__)


class PersonalizeCowlCreateView(
    dwviews.AddSwatchCreateURLMixin, dwviews.PersonalizeDesignCreateView
):

    model = CowlPatternSpec
    template_name = "cowls/personalize_design.html"
    form_class = PersonalizeDesignForm

    # TODO: can this be factored out to design_wizard?
    def get_form_kwargs(self):
        kwargs = super(PersonalizeCowlCreateView, self).get_form_kwargs()
        design = self.get_design()
        # add missing fields to an instance and pass that in.
        instance = self.model()
        for field in CowlDesignBase._meta.get_fields():
            setattr(instance, field.name, getattr(design, field.name))
        instance.design_origin = design
        instance.user = self.request.user
        kwargs["instance"] = instance
        return kwargs

    def get_initial(self):
        initial = super(PersonalizeCowlCreateView, self).get_initial()
        design = self.get_design()
        initial["name"] = design.name
        initial["height"] = design.height
        initial["circumference"] = design.circumference
        return initial

    def get_success_url(self):
        redirect_url = _return_post_design_redirect_url(self.request, self.object)
        return redirect_url


class PersonalizeGradedCowlView(PersonalizeGradedDesignView):
    # Probably different enough from above views to make common superclasses
    # not worth it
    form_class = PersonalizeGradedDesignForm
    model = GradedCowlPatternSpec

    def get_form_kwargs(self):
        kwargs = super(PersonalizeGradedCowlView, self).get_form_kwargs()
        design = self.get_design()
        # add missing fields to an instance and pass that in.
        instance = self.model()
        for field in CowlDesignBase._meta.get_fields():
            setattr(instance, field.name, getattr(design, field.name))
        instance.design_origin = design
        instance.user = self.request.user
        kwargs["instance"] = instance
        return kwargs


##############################################################################################################
#
# Redo views
#
##############################################################################################################


class CowlRedoCreateView(dwviews.RedoCreateView):

    template_name = "cowls/redo_pattern_select_changes.html"
    model = CowlRedo
    form_class = CowlRedoForm

    def get_form_kwargs(self):
        kwargs = super(CowlRedoCreateView, self).get_form_kwargs()

        pattern = self._get_pattern()
        instance = self.model()
        orig_patternspec = pattern.get_spec_source()
        instance.circumference = orig_patternspec.circumference
        instance.height = orig_patternspec.height
        instance.swatch = orig_patternspec.swatch
        instance.pattern = pattern

        kwargs["instance"] = instance

        return kwargs
