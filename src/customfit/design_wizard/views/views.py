import logging

from django.template.response import TemplateResponse
from django.views.generic.base import TemplateView

from customfit.designs.models import Collection, Design

from .garment_registry import MYO_OPTIONS

logger = logging.getLogger(__name__)


#
#
# Views for selecting and specifying design choices
# -----------------------------------------------------------------------------


class ChooseDesignTypeView(TemplateView):
    """
    This view allows users to choose a pre-canned design or to customize
    their own.

    Design options include:
        * All designs (displayed using featured designs)
        * All collections (displayed using the latest collection)
        * Entry to the full design wizard.
    """

    template_name = "choose_design.html"

    def dispatch(self, request, *args, **kwargs):
        # We have to put a logging statement somewhere we have access to
        # to request.user.
        logger.info("User %s is choosing a design", request.user)
        return super(ChooseDesignTypeView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ChooseDesignTypeView, self).get_context_data(**kwargs)

        displayables = Collection.displayable
        if displayables.exists():
            collection = displayables.latest()
            collection_designs = collection.visible_designs
            context["has_collections"] = True
        else:
            collection_designs = Design.basic.all()
            context["has_collections"] = False
        context["collection_designs"] = collection_designs

        if Design.featured.exists():
            designs = Design.featured.all()
        else:
            designs = Design.listable.all()[:5]
        context["designs"] = designs

        context["myo_options"] = MYO_OPTIONS

        return context


#
# Views for routing around historical technical debt
# -----------------------------------------------------------------------------


class TemplateResponse404(TemplateResponse):
    status_code = 404
