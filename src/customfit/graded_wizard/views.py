import logging

from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.module_loading import import_string
from django.views.generic import CreateView, ListView

from customfit.designs.models import Design
from customfit.patterns.models import GradedPattern

logger = logging.getLogger(__name__)


############################################################################################################
#
# Show patterns
#
############################################################################################################


class ListPatternsView(ListView):

    model = GradedPattern
    template_name = "graded_wizard/list_patterns.html"

    def get_queryset(self):
        qs = super(ListPatternsView, self).get_queryset()
        qs = qs.filter(
            pieces__schematic__graded_garment_parameters__pattern_spec__user=self.request.user
        ).order_by("-creation_date")
        return qs


############################################################################################################
#
# Choose design
#
############################################################################################################


class ChooseDesignView(ListView):

    model = Design
    template_name = "graded_wizard/all_designs.html"


############################################################################################################
#
# Personalize design
#
############################################################################################################


# Logic for making the pattern:


def _make_pattern_return_url(request, graded_pattern_spec):

    graded_pattern_spec.full_clean()
    igp_class = graded_pattern_spec.get_igp_class()
    missing_fields = igp_class.missing_body_fields(graded_pattern_spec)
    if missing_fields:
        field_list = ", ".join(missing_fields)
        msg = "Missing measurements: %s" % field_list
        raise RuntimeError(msg)
    else:

        logger.info(
            "User {user} has appropriate measurements for graded patternspec "
            "#{pspec}; making IGP".format(
                user=request.user, pspec=graded_pattern_spec.pk
            )
        )
        # We can make the IGP; let's see if it's also valid.

        igp = igp_class.make_from_patternspec(request.user, graded_pattern_spec)
        igp.full_clean()

        logger.info(
            "Successfully made graded IGP #{igp} for user {user}. "
            "Continuing to tweak or approval.".format(igp=igp.id, user=request.user)
        )

        schematic_class = igp.get_schematic_class()
        schematic = schematic_class.make_from_garment_parameters(igp)
        schematic.full_clean()

        logger.info(
            "Successfully made graded GarmentSchematic #{sch} for user {user}. "
            "Continuing to tweak or approval.".format(
                sch=schematic.id, user=request.user
            )
        )

        pieces_class = schematic.get_pieces_class()
        pieces = pieces_class.make_from_schematic(schematic)
        pieces.full_clean()

        logger.info(
            "Successfully made graded PatternPieces #{pieces} for user {user}. "
            "Continuing to tweak or approval.".format(
                pieces=pieces.id, user=request.user
            )
        )

        pattern_class = pieces.get_pattern_class()
        pattern = pattern_class.make_from_graded_pattern_pieces(pieces)
        pattern.full_clean()
        pattern.save()

        logger.info(
            "Successfully made graded Pattern #{p} for user {user}. "
            "Continuing to tweak or approval.".format(p=pattern.id, user=request.user)
        )

        success_url = reverse("patterns:gradedpattern_detail_view", args=(pattern.id,))
        return success_url


# And now, the actual class


class PersonalizeGradedDesignView(CreateView):

    template_name = "graded_wizard/personalize_graded_design.html"

    def get_design(self):
        design_slug = self.kwargs["design_slug"]
        design = get_object_or_404(Design, slug=design_slug)
        return design

    def get_context_data(self, **kwargs):
        """
        This gets the context shared by get() and post().
        """
        context = super(PersonalizeGradedDesignView, self).get_context_data(**kwargs)
        context["design"] = self.get_design()
        return context

    def get_form_kwargs(self):
        kwargs = super(PersonalizeGradedDesignView, self).get_form_kwargs()
        design = self.get_design()
        kwargs["design"] = design
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted a valid personalize-graded form for design %s",
            self.request.user,
            design.name,
        )
        return super(PersonalizeGradedDesignView, self).form_valid(form)

    def form_invalid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted an invalid  personalize-graded form for design %s",
            self.request.user,
            design.name,
        )
        logger.debug("Form errors: %s", form.errors)
        return super(PersonalizeGradedDesignView, self).form_invalid(form)

    def get_success_url(self):
        redirect_url = _make_pattern_return_url(self.request, self.object)
        return redirect_url


# Magic garment registry


view_dict = {
    "cowls": "customfit.cowls.views.PersonalizeGradedCowlView",
    "sweaters": "customfit.sweaters.views.PersonalizeGradedSweaterView",
    # needed for testing
    "test_garment": "customfit.test_garment.views.PersonalizeGradedView",
}


# Actual view exposed to outside world


def personalize_graded_view(request, *args, **kwargs):
    design_slug = kwargs["design_slug"]
    design = get_object_or_404(Design, slug=design_slug)
    model_app_label = design._meta.app_label
    logger.debug("model: %s", model_app_label)
    view_class_name = view_dict[model_app_label]
    view_class = import_string(view_class_name)
    view_fun = view_class.as_view()
    return view_fun(request, *args, **kwargs)
