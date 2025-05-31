import logging

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import FormView

from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.patterns.models import IndividualPattern

from ..forms import RedoApproveForm, SummaryAndApproveForm
from ..models import Transaction
from .caching import cache_pattern, uncache_pattern
from .garment_registry import model_to_view
from .helpers import _ErrorCheckerMixin, _get_featured_image_url

logger = logging.getLogger(__name__)


#
# Helper functions
# -----------------------------------------------------------------------------


def get_view_for_igp(view_name):

    def view(request, *args, **kwargs):

        pk = kwargs["igp_id"]
        igp = get_object_or_404(IndividualGarmentParameters, pk=pk)

        inner_view = model_to_view(igp, view_name)

        return inner_view(request, *args, **kwargs)

    return view


class SummaryAndApproveViewBase(_ErrorCheckerMixin, FormView):

    # Subclasses need to define:
    #
    # * template_name
    # * _make_pattern()

    form_class = SummaryAndApproveForm
    template_name = "design_wizard/summary_and_approve.html"

    def get_object(self):
        igp_id = self.kwargs["igp_id"]
        igp = IndividualGarmentParameters.objects.get(pk=igp_id)
        return igp

    def get_pattern(self):
        try:
            pattern = self._pattern
        except AttributeError:
            igp = self.get_object()
            try:
                pattern = IndividualPattern.even_unapproved.filter(
                    pieces__schematic__individual_garment_parameters=igp
                ).get()
            except IndividualPattern.DoesNotExist:
                request = self.request
                pattern = self.generate_pattern(request, igp)
                pattern.save()
                cache_pattern(pattern, self.request)
                self.request.session["pattern_id"] = pattern.id
                messages.add_message(
                    request,
                    messages.INFO,
                    "We've generated your final numbers - take a look!",
                )
            self._pattern = pattern

        return pattern

    def generate_pattern(self, request, igp):
        return self._make_pattern(request, igp)

    def _check_consistency(self, request):
        # pulled out into its own method to make it easier to subclass this class in the future
        igp = self.get_object()
        self._check_igp_consistency_base(request, igp)
        super(SummaryAndApproveViewBase, self)._check_consistency(request)

    def get_spec_source(self):
        igp = self.get_object()
        spec_source = igp.get_spec_source()
        return spec_source

    def get_design(self):
        spec_source = self.get_spec_source()
        if spec_source.design_origin:
            return spec_source.design_origin
        else:
            return self.get_myo_design()

    def get(self, request, *args, **kwargs):

        # First make the ConstructionSchematic and the pattern, then store the pattern
        # in the session for get_context() and other methods.
        # Although we only need schematic data to render the page,
        # we need to make the pattern here so that we won't end up
        # collecting money for patterns that throw exceptions.
        user = request.user

        pattern = self.get_pattern()
        # Check for some common problems
        assert (
            pattern.pieces.schematic.individual_garment_parameters == self.get_object()
        )

        if pattern.user != user:
            logger.warning(
                "User %s tried to approve pattern %s but does not " "own that pattern",
                user,
                pattern,
            )
            raise PermissionDenied

        # We used to test if the pattern was approved, but we took that out to simplify the code
        # when we moved that test to ErrorCheckerMixin

        else:
            return super(SummaryAndApproveViewBase, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SummaryAndApproveViewBase, self).get_context_data(**kwargs)

        igp = self.get_object()
        pattern = self.get_pattern()
        pattern_id = pattern.id

        context["pattern"] = pattern
        context["pattern_id"] = pattern_id
        context["igp_id"] = igp.id
        context["swatch"] = pattern.get_spec_source().swatch

        context["featured_image_url"] = _get_featured_image_url(igp)

        schematic_context = pattern.get_schematic_display_context()
        context.update(schematic_context)

        return context

    def _test_can_render_pattern(self, pattern):
        pattern.render_preamble()
        pattern.render_instructions()
        pattern.render_postamble()
        pattern.render_charts()
        pattern.render_pattern()

    def form_valid(self, form):

        # Assuming everything in the form is valid, make a Transaction for the pattern and redirect to the detail
        # view

        # Check the form
        user = self.request.user
        igp = self.get_object()
        design = self.get_design()

        # Before we save the transaction, let's make sure we can render the patterntext
        self._test_can_render_pattern(self.get_pattern())

        pattern = self.get_pattern()
        assert pattern.pieces.schematic.individual_garment_parameters == igp
        assert pattern.user == user

        reason = (
            Transaction.STAFF_USER if user.is_staff else Transaction.FRIENDS_AND_FAMILY
        )

        transaction = Transaction(
            user=pattern.user,
            pattern=pattern,
            amount=0.00,
            approved=True,
            why_free=reason,
        )
        transaction.save()

        return super(SummaryAndApproveViewBase, self).form_valid(form)

    def get_success_url(self):

        pattern = self.get_pattern()
        success_url = reverse(
            "patterns:individualpattern_detail_view", args=(pattern.id,)
        )
        return success_url


summary_and_approve_view = get_view_for_igp("approve_patternspec_view")


class RedoApproveView(_ErrorCheckerMixin, FormView):

    # Subclasses must implement:
    #
    # * _make_pattern(self, request, igp)
    # * _make_new_pieces(self, request, igp)

    #
    # Copied from _SummaryAndApproveViewBase
    #

    template_name = "design_wizard/approve_redo.html"

    def get_object(self):
        igp_id = self.kwargs["igp_id"]
        igp = IndividualGarmentParameters.objects.get(pk=igp_id)
        return igp

    def _check_consistency(self, request):
        igp = self.get_object()
        self._check_igp_consistency_base(request, igp)
        super(RedoApproveView, self)._check_consistency(request)

    def _test_can_render_pattern(self, pattern):
        pattern.render_preamble()
        pattern.render_instructions()
        pattern.render_postamble()
        pattern.render_charts()
        pattern.render_pattern()

    #
    # New for _RedoApproveViewBase
    #

    form_class = RedoApproveForm

    def _get_pattern_from_igp(self, igp):
        return igp.redo.pattern

    def get_context_data(self, **kwargs):
        context = super(RedoApproveView, self).get_context_data(**kwargs)

        igp = self.get_object()

        context["featured_image_url"] = _get_featured_image_url(igp)
        context["swatch"] = igp.get_spec_source().swatch
        context["igp_id"] = igp.id

        pattern = self._make_pattern(self.request, igp)
        context["pattern"] = pattern
        schematic_context = pattern.get_schematic_display_context()
        context.update(schematic_context)

        return context

    def get(self, request, *args, **kwargs):
        # Make the pattern and ensure that we can render it before showing it to the
        # user for approval.
        igp = self.get_object()
        pattern = self._make_pattern(self.request, igp)
        self._test_can_render_pattern(pattern)
        messages.add_message(
            request, messages.INFO, "We've generated your new numbers - take a look!"
        )
        return super(RedoApproveView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        # Make the new IPP (again), update the pattern, and then let the superclass handle the rest.
        igp = self.get_object()
        user = self.request.user
        new_pieces = self._make_new_pieces(self.request, igp)
        pattern = self._get_pattern_from_igp(igp)
        uncache_pattern(pattern)
        pattern.update_with_new_pieces(new_pieces)
        cache_pattern(pattern, self.request)
        return super(RedoApproveView, self).form_valid(form)

    # TODO: extend ErrorCheckerMixin to check that pattern has not already been redone

    def get_success_url(self):
        # re-direct the user back to the detail page for the pattern
        igp = self.get_object()
        pattern = self._get_pattern_from_igp(igp)
        messages.add_message(
            self.request, messages.INFO, "We've redone the pattern-- take a look!"
        )
        return reverse(
            "patterns:individualpattern_detail_view", kwargs={"pk": pattern.pk}
        )


redo_approve_view = get_view_for_igp("approve_redo_view")
