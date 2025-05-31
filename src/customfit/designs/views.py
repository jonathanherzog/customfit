from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView

from .forms import CreateCollectionForm
from .models import Collection, Design


class AllCollectionsView(TemplateView):
    """
    Displays the complete list of collections available in CustomFit.
    """

    template_name = "designs/all_collections.html"

    def get_context_data(self, **kwargs):
        context = super(AllCollectionsView, self).get_context_data(**kwargs)

        context["collections"] = Collection.displayable.all().order_by("-creation_date")

        return context


class CreateCollectionView(CreateView):
    template_name = "create_collection.html"
    model = Collection
    form_class = CreateCollectionForm
    success_url = reverse_lazy("staff")

    def form_valid(self, form):
        # We must save the instance before we can create an FK relationship to
        # to it from Design.
        form.instance.save()
        for design in form.cleaned_data["designs"]:
            design.collection = form.instance
            design.save()
        messages.add_message(
            self.request, messages.INFO, "Collection %s created." % form.instance.name
        )
        return super(CreateCollectionView, self).form_valid(form)


class AllDesignsView(TemplateView):

    template_name = "designs/all_designs.html"

    def _get_displayable_designs(self):
        listable_designs = Design.listable.all()
        return listable_designs.order_by("name")

    def get_context_data(self, **kwargs):
        context = super(AllDesignsView, self).get_context_data(**kwargs)
        context["designs"] = self._get_displayable_designs()

        # Knitters should see the build-your-own options at the bottom
        # of the all-designs page, too
        from customfit.design_wizard.views.garment_registry import MYO_OPTIONS

        context["myo_options"] = MYO_OPTIONS

        return context
