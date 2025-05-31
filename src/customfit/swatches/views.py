import logging
import os.path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms.models import model_to_dict, modelform_factory
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    convert_to_imperial,
    convert_value_to_metric,
    round,
)

from .forms import SwatchCreateFormIndividual, SwatchEditForm
from .models import Swatch

logger = logging.getLogger(__name__)

SWATCH_SESSION_NAME = "current_selected_swatch"


def put_swatch_in_session(swatch, session):
    assert swatch.pk is not None
    session[SWATCH_SESSION_NAME] = swatch.id


def get_swatch_from_session(session, user):
    swatch_id = session[SWATCH_SESSION_NAME]
    swatch = Swatch.objects.get(pk=swatch_id)
    assert swatch.user == user
    return swatch


def delete_swatch_from_session(session):
    if SWATCH_SESSION_NAME in session:
        del session[SWATCH_SESSION_NAME]


class SwatchListView(ListView):
    """
    A class-based view for the Swatch-list page. Will retrieve and use only
    those swatches which are owned by the current user.
    """

    model = Swatch
    template_name = "abstract_list_view.html"

    def get_queryset(self):
        user = self.request.user
        queryset = self.model.objects.filter(user=user).order_by("-creation_date")
        return queryset

    def get_context_data(self, **kwargs):
        context = super(SwatchListView, self).get_context_data(**kwargs)
        context["header_image_url"] = os.path.join(
            settings.STATIC_URL, "img/My_Gauge.png"
        )
        context["header_text"] = (
            "<p class='margin-top-20'>A saved gauge is required to create a "
            "custom pattern. Click the button to the left to create a new "
            "gauge.</p><p>You can save an unlimited amount of gauges. Be "
            "sure to check for typos! You cannot edit a gauge after you've "
            "used it to create a pattern.</p>"
        )
        context["label"] = "Your saved gauges"
        context["empty_set"] = "You have no swatches yet."
        context["empty_set_action"] = "Start creating one now."
        context["create_url"] = reverse_lazy("swatches:swatch_create_view")
        context["listview_action_template"] = (
            "swatches/swatch_listview_action_template.html"
        )
        return context


class SwatchDetailView(DetailView):
    """
    A class-based view for Swatch's detail page. Checks to ensure that the
    calling user is authorized to view the instance in question (i.e., is the
    instance's owner).
    """

    model = Swatch
    context_object_name = "swatch"

    def get_object(self, queryset=None):
        obj = super(SwatchDetailView, self).get_object(queryset)
        if obj.user == self.request.user or self.request.user.is_staff:
            return obj
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(SwatchDetailView, self).get_context_data(**kwargs)
        context["picture_upload_url"] = "uploads:swatch_picture_upload"
        context["manage_pictures_url"] = reverse_lazy(
            "uploads:swatch_picture_edit", args=(self.object.id,)
        )
        context["url_to_share"] = self.request.build_absolute_uri(reverse("about"))
        return context


class SwatchCreateView(CreateView):
    """
    Individual-user version of the swatch-create view. Expects that the user
    be logged in. Intended to be used in a GuardingHat view.
    """

    form_class = SwatchCreateFormIndividual
    template_name = "swatches/swatch_create_form.html"
    model = Swatch

    def form_valid(self, form, *args, **kwargs):

        messages.add_message(
            self.request,
            messages.INFO,
            "Hooray! Gauge saved; now you can make "
            "patterns with your beautiful yarn %s." % form.instance.name,
        )

        return super(SwatchCreateView, self).form_valid(form, *args, **kwargs)

    def get_success_url(self):
        if self.get_request_next_url():
            return self.get_request_next_url()
        elif (
            "submit_to_pattern" in self.request.POST
            or "submit_to_pattern" in self.request.POST
        ):
            return reverse_lazy("design_wizard:choose_type")
        else:
            return reverse_lazy("home_view")

    def get_request_next_url(self):
        return self.request.GET.get("next", None)

    def get_form_kwargs(self):
        kwargs = super(SwatchCreateView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        kwargs["force_single_submit_button"] = bool(self.get_request_next_url())
        return kwargs

    def form_valid(self, form, *args, **kwargs):
        """
        Convert entered data from metric to imperial if needed and then
        perform standard Django form_valid actions (save object and
        redirect to success_url).


        We override the default implementation rather than calling super here
        because Django's implementation (self.object = form.save()) saves
        the wrong values if the user entered metric data, and also does
        not have access to request.user (meaning that the save fails,
        because the foreign key to User is mandatory). Attempting to
        monkey with cleaned_data here and then call super does not
        provide the desired results since `user` is not among the
        form fields.
        """
        swatch_params = convert_to_imperial(
            form.cleaned_data, Swatch, self.request.user
        )
        self.object = Swatch(**swatch_params)
        self.object.user = self.request.user
        self.object.save()

        put_swatch_in_session(self.object, self.request.session)

        return HttpResponseRedirect(self.get_success_url())


class SwatchNoteUpdateView(UpdateView):
    model = Swatch
    template_name_suffix = "_note_update_form"
    form_class = modelform_factory(Swatch, fields=("notes",))

    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, "Your note has been updated.")
        return super(SwatchNoteUpdateView, self).form_valid(form)


class SwatchUpdateView(UpdateView):
    model = Swatch
    template_name_suffix = "_edit_form"
    form_class = SwatchEditForm

    def dispatch(self, request, *args, **kwargs):
        swatch = self.get_object()
        if not self.request.user == swatch.user:
            logger.warning(
                "User %s tried to edit swatch id=%s, which belongs to " "user %s",
                self.request.user.username,
                swatch.id,
                swatch.user.username,
            )
            raise PermissionDenied

        # dispatch handles get and post; we only need to log this once
        if request.method == "GET":
            logger.info(
                "User %s is editing swatch id=%s . Current values are %s",
                self.request.user.username,
                swatch.id,
                model_to_dict(swatch),
            )
        return super(SwatchUpdateView, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        """
        Prepopulate form fields with existing swatch data, converting to metric
        if necessary.
        We will convert back to imperial as needed in form_valid.
        """
        initials = {}
        swatch = self.get_object()
        fieldkeys = self.get_form_class()._meta.fields
        for fieldkey in fieldkeys:
            val = getattr(swatch, fieldkey)
            modelfield = swatch._meta.get_field(fieldkey)
            dimension = getattr(modelfield, "dimension", None)
            if swatch.user.profile.display_imperial:
                # round the numbers we're about to display appropriately -- this
                # is especially necessary if they were originally entered in metric.
                # round lengths to 1/8 inch since for a swatch they're small and
                # precision might matter; round other values (long lengths, grams)
                # to tenths.
                if type(val) is float:
                    precision = {"length": 1.0 / 8}.get(dimension, 0.1)
                    val = round(val, ROUND_ANY_DIRECTION, precision)
            else:
                val = convert_value_to_metric(val, dimension)
                if type(val) is float:
                    val = round(val, ROUND_ANY_DIRECTION, 0.1)
            initials[fieldkey] = val
        return initials

    def get_context_data(self, **kwargs):
        context = super(SwatchUpdateView, self).get_context_data(**kwargs)
        swatch = self.get_object()

        # copy the non-editable fields from the same object used to render the
        # detail form
        non_editable_fields = []
        for field_key in ("stitches", "rows", "repeats"):
            non_editable_fields.extend(
                [x for x in swatch.details if x["field_key"] == field_key]
            )

        context["non_editable_fields"] = non_editable_fields
        context["max_pictures"] = settings.MAX_PICTURES
        return context

    def form_valid(self, form):
        swatch = self.get_object()
        swatch_params = convert_to_imperial(
            form.cleaned_data, Swatch, self.request.user
        )
        for key, value in list(swatch_params.items()):
            setattr(swatch, key, value)
        swatch.save()

        logger.info(
            "User %s has edited swatch id=%s . New values are %s",
            self.request.user.username,
            swatch.id,
            model_to_dict(swatch),
        )
        messages.add_message(
            self.request, messages.INFO, "Your swatch has been updated."
        )

        put_swatch_in_session(swatch, self.request.session)

        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        swatch_id = self.get_object().id
        return reverse_lazy("swatches:swatch_detail_view", args=(swatch_id,))


class SwatchDeleteView(DeleteView):
    model = Swatch

    def form_valid(self, form):
        """
        This does some logging and ensures that the user owns the swatch
        to be deleted.

        The Swatch model delete() method checks to see whether the swatch
        should be actually deleted or merely archived.
        """
        obj = self.get_object()

        obj_id = obj.id
        obj_name = obj.name
        obj_username = obj.user.username

        logger.info(
            "User %s is attempting to delete swatch with id %s",
            self.request.user.username,
            obj_id,
        )

        # Ensure users can only delete their own swatches.
        if obj.user != self.request.user:
            logger.warning(
                "User %s tried (unsuccessfully) to delete a swatch "
                "with id %s, which belongs to %s.",
                self.request.user.username,
                obj_id,
                obj_username,
            )
            raise PermissionDenied

        try:
            swatch = get_swatch_from_session(self.request.session, self.request.user)
            if swatch == obj:
                delete_swatch_from_session(self.request.session)
        except KeyError:
            pass

        return_me = super(SwatchDeleteView, self).form_valid(form)
        logger.info("User %s deleted swatch with id %s", obj_username, obj_id)
        messages.add_message(
            self.request,
            messages.INFO,
            "Your swatch " + obj_name + " has been deleted.",
        )
        return return_me

    def get_success_url(self):
        return reverse_lazy("swatches:swatch_list_view")
