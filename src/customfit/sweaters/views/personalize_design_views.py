# -*- coding: utf-8 -*-

import logging

import customfit.design_wizard.views as dwviews
from customfit.graded_wizard.views import PersonalizeGradedDesignView
from customfit.helpers.math_helpers import cm_to_inches

from ..forms import (
    PersonalizeDesignForm,
    PersonalizeGradedSweaterDesignForm,
    SweaterRedoForm,
)
from ..helpers import sweater_design_choices as SDC
from ..models import (
    GradedSweaterPatternSpec,
    SweaterDesignBase,
    SweaterPatternSpec,
    SweaterRedo,
)

logger = logging.getLogger(__name__)

# Create your views here.


class _PersonalizeSweaterDesignViewBase(dwviews.AddCreateURLsMixin):

    model = SweaterPatternSpec

    def get_context_data(self, **kwargs):
        context = super(_PersonalizeSweaterDesignViewBase, self).get_context_data(
            **kwargs
        )
        design = self.get_design()
        context["silhouette_text"] = design.supported_silhouette_choices()
        if "form" in context:
            form = context["form"]
            # form may be None
            if form is not None:
                context["body_options"] = form.get_body_options()
        return context


class PersonalizeSweaterCreateView(
    _PersonalizeSweaterDesignViewBase, dwviews.PersonalizeDesignCreateView
):
    template_name = "sweaters/personalize_design.html"
    form_class = PersonalizeDesignForm

    def get_form_kwargs(self):
        kwargs = super(PersonalizeSweaterCreateView, self).get_form_kwargs()
        design = self.get_design()
        # add missing fields to an instance and pass that in.
        instance = self.model()
        for field in SweaterDesignBase._meta.get_fields():
            setattr(instance, field.name, getattr(design, field.name))
        instance.design_origin = design
        instance.user = self.request.user
        kwargs["instance"] = instance
        return kwargs

    def get_initial(self):
        initial = super(PersonalizeSweaterCreateView, self).get_initial()
        design = self.get_design()
        initial["name"] = design.name
        initial["silhouette"] = design.primary_silhouette

        initial["construction"] = design.primary_construction
        if design.construction_drop_shoulder_allowed:
            initial["drop_shoulder_additional_armhole_depth"] = (
                design.drop_shoulder_additional_armhole_depth
            )

        return initial


class PersonalizeSweaterUpdateView(
    dwviews.PersonalizeDesignUpdateView, _PersonalizeSweaterDesignViewBase
):
    pass


class PersonalizeGradedSweaterView(PersonalizeGradedDesignView):
    # Probably different enough from above views to make common superclasses
    # not worth it
    form_class = PersonalizeGradedSweaterDesignForm
    model = GradedSweaterPatternSpec

    def get_form_kwargs(self):
        kwargs = super(PersonalizeGradedSweaterView, self).get_form_kwargs()
        design = self.get_design()
        # add missing fields to an instance and pass that in.
        instance = self.model()
        for field in SweaterDesignBase._meta.get_fields():
            setattr(instance, field.name, getattr(design, field.name))
        instance.design_origin = design
        instance.user = self.request.user
        kwargs["instance"] = instance
        return kwargs

    def get_initial(self):
        initial = super(PersonalizeGradedSweaterView, self).get_initial()
        design = self.get_design()
        initial["name"] = design.name
        initial["silhouette"] = design.primary_silhouette
        initial["construction"] = design.primary_construction
        if design.construction_drop_shoulder_allowed and (
            design.primary_construction == SDC.CONSTRUCTION_DROP_SHOULDER
        ):
            initial["drop_shoulder_additional_armhole_depth"] = (
                design.drop_shoulder_additional_armhole_depth
            )
        else:
            initial["drop_shoulder_additional_armhole_depth"] = None

        return initial


##############################################################################################################
#
# Redo views
#
##############################################################################################################


class _SweaterRedoViewBase(dwviews.AddBodyCreateURLMixin):
    template_name = "sweaters/redo_pattern_select_changes.html"
    model = SweaterRedo
    form_class = SweaterRedoForm

    def get_context_data(self, **kwargs):
        context = super(_SweaterRedoViewBase, self).get_context_data(**kwargs)
        form = context["form"]
        if form:
            context["body_options"] = form.get_body_options()

        pattern = self._get_pattern()
        pattern_spec = pattern.get_spec_source()
        context["silhouette"] = pattern_spec.silhouette
        return context


class SweaterRedoCreateView(_SweaterRedoViewBase, dwviews.RedoCreateView):

    def get_form_kwargs(self):
        kwargs = super(SweaterRedoCreateView, self).get_form_kwargs()

        pattern = self._get_pattern()
        instance = self.model()
        orig_patternspec = pattern.get_spec_source()

        instance.body = orig_patternspec.body
        instance.swatch = orig_patternspec.swatch
        instance.garment_fit = orig_patternspec.garment_fit
        instance.torso_length = orig_patternspec.torso_length
        instance.sleeve_length = orig_patternspec.sleeve_length
        instance.neckline_depth = orig_patternspec.neckline_depth
        instance.neckline_depth_orientation = (
            orig_patternspec.neckline_depth_orientation
        )
        instance.pattern = pattern

        kwargs["instance"] = instance

        return kwargs


class SweaterRedoUpdateView(_SweaterRedoViewBase, dwviews.RedoUpdateView):

    def form_valid(self, form):

        if not self.request.user.profile.display_imperial:
            self.object.neckline_depth = cm_to_inches(self.object.neckline_depth)
            self.object.save()

        return super(SweaterRedoUpdateView, self).form_valid(form)
