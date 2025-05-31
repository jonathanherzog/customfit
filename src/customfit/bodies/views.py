import copy
import logging
import os.path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from customfit.helpers.math_helpers import convert_to_imperial, round
from customfit.views import MakePdfMixin

from .forms import BodyCreateForm, BodyUpdateForm
from .models import ESSENTIAL_FIELDS, EXTRA_FIELDS, OPTIONAL_FIELDS, Body

BODY_SESSION_NAME = "current_selected_body"


def put_body_in_session(body, session):
    assert body.pk is not None
    session[BODY_SESSION_NAME] = body.pk


def get_body_from_session(session, user):
    body_pk = session[BODY_SESSION_NAME]
    body = Body.objects.get(pk=body_pk)
    assert user == body.user
    return body


def delete_body_from_session(session):
    if BODY_SESSION_NAME in session:
        del session[BODY_SESSION_NAME]


logger = logging.getLogger(__name__)


class BodyListView(ListView):
    """
    A class-based view for the Body-list page. Will retrieve and use only
    those bodies which are owned by the current user.
    """

    model = Body
    template_name = "abstract_list_view.html"

    def get_queryset(self):
        user = self.request.user
        queryset = self.model.objects.filter(user=user).order_by("-creation_date")
        return queryset

    def get_context_data(self, **kwargs):
        context = super(BodyListView, self).get_context_data(**kwargs)
        context["header_image_url"] = os.path.join(
            settings.STATIC_URL, "img/My_Measurements.png"
        )
        context[
            "header_text"
        ] = """<p class='margin-top-20'>You'll need a saved 
             measurement set to create a custom pattern. </p>
             <p>You can save up to 10 measurement sets in your
            account. Delete old ones when you don't need them any more.</p>"""
        context["label"] = "My measurements"
        context["empty_set"] = "You have no measurement sets yet."
        context["empty_set_action"] = "Start creating one now."
        context["create_url"] = reverse_lazy("bodies:body_create_view")
        context["listview_action_template"] = (
            "bodies/body_listview_action_template.html"
        )

        return context


class BodyDetailView(DetailView):
    """
    A class-based view for Body's detail page. Checks to ensure that the
    calling user is authorized to view the instance in question (i.e., is the
    instance's owner).
    """

    model = Body
    context_object_name = "body"

    def get_object(self, queryset=None):
        obj = super(BodyDetailView, self).get_object(queryset)
        if obj.user == self.request.user or self.request.user.is_staff:
            return obj
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        context = super(BodyDetailView, self).get_context_data(**kwargs)
        context["picture_upload_url"] = "uploads:body_picture_upload"
        context["manage_pictures_url"] = reverse_lazy(
            "uploads:body_picture_edit", args=(self.object.id,)
        )
        context["url_to_share"] = self.request.build_absolute_uri(reverse("about"))
        context["tweet_text"] = (
            "I just saved measurements for a #customfit - one step closer to happy sweater face!"
        )
        return context


class BodyDetailViewPdf(MakePdfMixin, BodyDetailView):
    template_name = "bodies/body_detail_pdf.html"

    def get_context_data(self, **kwargs):
        context = super(BodyDetailViewPdf, self).get_context_data(**kwargs)

        user = self.request.user
        body = self.object
        context["user_name"] = self.request.user.username
        return context

    def get_object_name(self):
        return self.object.name


class BodyCreateView(CreateView):
    model = Body
    form_class = BodyCreateForm
    template_name = "bodies/body_create_form.html"

    def get_request_next_url(self):
        return self.request.GET.get("next", None)

    def get_form_kwargs(self):
        kwargs = super(BodyCreateView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        kwargs["force_single_submit_button"] = bool(self.get_request_next_url())
        return kwargs

    def form_invalid(self, form):
        response = super(BodyCreateView, self).form_invalid(form)
        messages.error(self.request, "Please correct the errors below.")
        return response

    def _get_body_params_from_form(self, form):
        # We factor this out here because we'll want different handling in
        # the BodyCopyView.
        return convert_to_imperial(form.cleaned_data, Body, self.request.user)

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

        form.instance.user = self.request.user
        messages.add_message(
            self.request,
            messages.INFO,
            "Hooray! Measurement set saved; now you can make "
            "patterns for %s." % form.instance.name,
        )

        logger.info(
            "User %s created a new measurement set %s", self.request.user, form.instance
        )

        body_params = self._get_body_params_from_form(form)
        self.object = Body(**body_params)
        self.object.user = self.request.user
        self.object.save()

        put_body_in_session(self.object, self.request.session)

        return HttpResponseRedirect(self.get_success_url())

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


class BodyUpdateView(UpdateView):
    template_name = "bodies/body_update_form.html"
    form_class = BodyUpdateForm
    model = Body

    def get_object(self, queryset=None):
        obj = super(BodyUpdateView, self).get_object(queryset)
        if obj.user == self.request.user or self.request.user.is_staff:
            if obj.is_updateable:
                return obj
            else:
                raise PermissionDenied
        else:
            raise PermissionDenied

    def get_form_kwargs(self):
        kwargs = super(BodyUpdateView, self).get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        if (
            "submit_to_pattern" in self.request.POST
            or "submit_to_pattern" in self.request.POST
        ):
            success_url = reverse_lazy("design_wizard:choose_type")
        else:
            success_url = reverse_lazy(
                "bodies:body_detail_view", args=(self.kwargs["pk"],)
            )

        messages.add_message(
            self.request, messages.INFO, "Hooray! Measurement set updated."
        )

        logger.info(
            "User %s updated measurement set %s", self.request.user, self.kwargs["pk"]
        )

        return success_url

    def form_valid(self, form):

        # Set the body in the session
        put_body_in_session(self.object, self.request.session)
        return super(BodyUpdateView, self).form_valid(form)


class BodyCopyView(BodyCreateView):
    """
    Allow users to create
    new measurement sets by copying and tweaking existing ones.

    Useful for, e.g., those times that they're happy with their existing
    measurements except they just want to make their upper torso a half-inch
    smaller.
    """

    template_name = "bodies/body_copy_form.html"

    def get_initial(self):
        body = self._get_initial_object()
        body_dict = body.to_dict()

        # Let's be reasonably explicit about the fields we intend to
        # copy. In particular, we do want to copy measurements; we don't
        # want to copy featured pic, notes, archival status.
        copyable_fields = ESSENTIAL_FIELDS + EXTRA_FIELDS + OPTIONAL_FIELDS

        # They'll need a new name for the new body, and we have no
        # grounds for suggesting one, so let's not prepopulate this
        # field.
        copyable_fields.remove("name")

        initial = {}
        for field in copyable_fields:
            initial[field] = body_dict[field]

        if not self.request.user.profile.display_imperial:
            for field, value in list(initial.items()):
                if isinstance(value, int) or isinstance(value, float):
                    initial[field] = round(value * 2.54)

        return initial

    def _get_initial_object(self):
        pk = self.kwargs["pk"]
        try:
            body = Body.objects.get(pk=pk)
        except:
            raise Http404
        return body

    def _get_body_params_from_form(self, form):
        orig_posted_data = copy.copy(form.cleaned_data)
        base_params = convert_to_imperial(form.cleaned_data, Body, self.request.user)

        # If the users haven't changed the value, use the value
        # of the underlying body rather than reprocessing the
        # data. Multiple roundings (here and in form initialization)
        # can lead to significant measurement differences, particularly
        # for metric users. Users who are copying measurement sets into
        # new ones presumably meant for the underlying data to be
        # unchanged, when they did not make changes to the form.
        for k in form.initial:
            if form.initial[k] == orig_posted_data[k]:
                base_params[k] = getattr(self._get_initial_object(), k)

        return base_params

    def dispatch(self, request, *args, **kwargs):
        body = self._get_initial_object()
        if not body.user == request.user:
            raise PermissionDenied

        # This inherits all the view protections in the superclass. Yay!
        return super(BodyCopyView, self).dispatch(request, *args, **kwargs)


class BodyNoteUpdateView(UpdateView):
    model = Body
    template_name_suffix = "_note_update_form"
    form_class = modelform_factory(Body, fields=("notes",))

    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, "Your note has been updated.")
        return super(BodyNoteUpdateView, self).form_valid(form)


class BodyDeleteView(DeleteView):
    model = Body

    def form_valid(self, form):
        """
        This does some logging and ensures that the user owns the body
        to be deleted.

        The Body model delete() method checks to see whether the body
        should be actually deleted or merely archived.
        """
        obj = self.get_object()

        # Make these attributes of self here, because the object
        # doesn't exist as of get_success_url; we'll be unable to
        # fetch these properties to log if we don't retain them.
        obj_id = obj.id
        obj_name = obj.name
        obj_username = obj.user.username
        req_user = self.request.user
        req_username = req_user.username

        logger.info(
            "User %s is attempting to delete body with id %s", req_username, obj_id
        )

        # Ensure users can only delete their own bodies.
        if not obj.user == req_user:
            logger.warning(
                "User %s tried (unsuccessfully) to delete a body "
                "with id %s, which belongs to %s.",
                req_username,
                obj_id,
                obj_username,
            )
            raise PermissionDenied

        # If the body is in the session, remove it
        session = self.request.session
        try:
            body = get_body_from_session(session, req_user)
            if body == obj:
                delete_body_from_session(session)
        except KeyError:
            pass

        return_me = super().form_valid(form)

        logger.info("User %s deleted body with id %s", req_username, obj_id)
        messages.add_message(
            self.request,
            messages.INFO,
            "Your measurement " "set " + obj_name + " has been deleted.",
        )

        return return_me

    def get_success_url(self):
        return reverse_lazy("bodies:body_list_view")
