import logging
from collections import defaultdict

from django.views.generic import DetailView, ListView

from .models import Stitch

logger = logging.getLogger(__name__)


class StitchDetailView(DetailView):

    model = Stitch
    context_object_name = "stitch"


class StitchListView(ListView):

    model = Stitch
    context_object_name = "stitch_list"
    template_name = "stitches/stitch_list.html"

    def get_context_data(self, **kwargs):
        context_data = super(StitchListView, self).get_context_data(**kwargs)

        # To optimize a slow view, we're going to pre-fetch Designs and match stitches to their designs
        # manually, rather than using stitch.get_public_designs()

        from customfit.designs.models import Design

        stitch_to_design_dict = defaultdict(set)
        for design in Design.listable.all():
            stitches = set(design.stitches_used())
            for stitch in stitches:
                stitch_to_design_dict[stitch].add(design)

        stitch_list = context_data["stitch_list"]

        stitches_with_designs = []
        for stitch in stitch_list:
            l = stitch_to_design_dict[stitch]
            l = sorted(l, key=lambda des: des.name)
            sl_tuple = (stitch, l)
            stitches_with_designs.append(sl_tuple)

        context_data["stitches_with_designs"] = stitches_with_designs

        return context_data
