from customfit.design_wizard.views import RedoApproveView, SummaryAndApproveViewBase

from ..models import CowlGarmentSchematic, CowlPattern, CowlPatternPieces


def make_IPS_from_IGP(igp):
    ips = CowlGarmentSchematic.make_from_garment_parameters(igp)
    ips.clean()
    ips.save()
    return ips


def make_IPP_from_IPS(ips):
    ipp = CowlPatternPieces.make_from_individual_pieced_schematic(ips)
    ipp.clean()
    ipp.save()
    return ipp


def make_pattern_from_IPP(user, ipp):
    pattern = CowlPattern.make_from_individual_pattern_pieces(user, ipp)
    pattern.clean()
    pattern.save()
    return pattern


class CowlApproveViewMixin(object):

    def get_context_data(self, **kwargs):
        context = super(CowlApproveViewMixin, self).get_context_data(**kwargs)

        # Top-level lengths
        pattern = self.get_pattern()
        top_level_lengths = [
            ("height", pattern.actual_height()),
            ("circumference", pattern.actual_circumference()),
        ]
        context["top_level_lengths"] = top_level_lengths

        # No detailed schematics
        context["schematic_template_name"] = None

        return context

    def _make_pattern(self, request, igp):
        """
        Handle the nitty-gritty of actually making the pattern from the IGP. Broken out into its
        own method for historical reasons.
        """
        user = request.user
        ips = make_IPS_from_IGP(igp)
        ipp = make_IPP_from_IPS(ips)
        pattern = make_pattern_from_IPP(user, ipp)
        return pattern


class CowlSummaryAndApproveView(CowlApproveViewMixin, SummaryAndApproveViewBase):

    pass


class CowlRedoApproveView(CowlApproveViewMixin, RedoApproveView):

    def _make_new_pieces(self, request, igp):
        ips = make_IPS_from_IGP(igp)
        ipp = make_IPP_from_IPS(ips)
        return ipp

    def get_pattern(self):
        igp = self.get_object()
        pattern = self._make_pattern(self.request, igp)
        return pattern
