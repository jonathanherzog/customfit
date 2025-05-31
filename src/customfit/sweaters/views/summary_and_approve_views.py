from customfit.design_wizard.views import RedoApproveView, SummaryAndApproveViewBase
from ..models.patternspec import MAKE_YOUR_OWN_SWEATER

from .helpers import _make_IPP_from_IPS, _make_IPS_from_IGP, _make_pattern_from_IPP


class SweaterApproveViewMixin(object):

    def get_context_data(self, **kwargs):
        context = super(SweaterApproveViewMixin, self).get_context_data(**kwargs)

        # Top-level lengths
        pattern = self.get_pattern()
        top_level_lengths = [("finished bust/chest", pattern.total_finished_bust())]
        if pattern.total_finished_waist():
            top_level_lengths += [("finished waist", pattern.total_finished_waist())]
        top_level_lengths += [("finished hip", pattern.total_finished_hip())]
        context["top_level_lengths"] = top_level_lengths

        # schematic image template
        context["schematic_template_name"] = (
            "sweaters/sweater_renderer_templates/mock_pieces/schematic_measurements_web.html"
        )

        return context

    def get_myo_design(self):
        return MAKE_YOUR_OWN_SWEATER


class SweaterSummaryAndApproveView(SweaterApproveViewMixin, SummaryAndApproveViewBase):

    def _make_pattern(self, request, igp):
        """
        Handle the nitty-gritty of actually making the pattern from the IGP. Broken out into its
        own method for historical reasons.
        """
        user = request.user
        ips = _make_IPS_from_IGP(user, igp)
        ipp = _make_IPP_from_IPS(ips)
        pattern = _make_pattern_from_IPP(user, ipp)
        return pattern


class SweaterRedoApproveView(SweaterApproveViewMixin, RedoApproveView):

    def _make_pattern(self, request, igp):
        ipp = self._make_new_pieces(request, igp)
        pattern = _make_pattern_from_IPP(request.user, ipp)
        return pattern
        # NOTE: DO NOT SAVE ANYTHING

    def _make_new_pieces(self, request, igp):
        user = request.user
        ips = _make_IPS_from_IGP(user, igp)
        ipp = _make_IPP_from_IPS(ips)
        return ipp

    def get_pattern(self):
        igp = self.get_object()
        pattern = self._make_pattern(self.request, igp)
        return pattern
