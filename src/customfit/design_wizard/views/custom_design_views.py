import logging

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import CreateView, UpdateView

from customfit.bodies.views import delete_body_from_session, get_body_from_session
from customfit.helpers.math_helpers import convert_to_imperial
from customfit.swatches.views import delete_swatch_from_session, get_swatch_from_session

from .garment_registry import app_name_to_view
from .helpers import _ErrorCheckerMixin, _return_post_design_redirect_url

logger = logging.getLogger(__name__)


def get_view(view_name):

    def view(request, *args, **kwargs):

        app_name = kwargs.pop("garment")
        inner_view = app_name_to_view(app_name, view_name)

        return inner_view(request, *args, **kwargs)

    return view


#
# Views for creating custom designs
# -----------------------------------------------------------------------------


class CustomDesignViewBaseMixin(object):
    # Requires subclasses to define:
    # * _get_this_url_path()

    def get_design(self):
        return self.get_myo_design()

    def form_invalid(self, form):
        # Add a message up top so they will know to scroll down to where they
        # can see form validation errors - otherwise it will not be obvious
        # to users why they have been returned to this page.
        logger.info(
            "User %s submitted an invalid custom design form".format(
                user=self.request.user
            )
        )
        messages.warning(self.request, "Please correct the errors below.")

        return super(CustomDesignViewBaseMixin, self).form_invalid(form)

    def get_form_kwargs(self):
        kwargs = super(CustomDesignViewBaseMixin, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super(CustomDesignViewBaseMixin, self).get_initial()
        user = self.request.user
        session = self.request.session
        try:
            body = get_body_from_session(session, user)
            if body.user == user:
                initial["body"] = body
            else:
                delete_body_from_session(session)
        except KeyError:
            pass
        try:
            swatch = get_swatch_from_session(session, user)
            if swatch.user == user:
                initial["swatch"] = swatch
            else:
                delete_swatch_from_session(session)

        except KeyError:
            pass
        return initial


class CustomDesignCreateView(CustomDesignViewBaseMixin, _ErrorCheckerMixin, CreateView):

    def dispatch(self, request, *args, **kwargs):
        logger.info(
            "User {user} is creating a custom design".format(user=self.request.user)
        )
        return super(CustomDesignCreateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # at this point, we should remove the body/swatch from the session
        # so that any form-error handling is based only on what was submitted
        # in the form
        session = self.request.session
        delete_body_from_session(session)
        delete_swatch_from_session(session)
        return super(CustomDesignCreateView, self).post(request, *args, **kwargs)

    def _get_this_url_path(self, garment_name):
        this_url_path = reverse(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": garment_name},
        )
        return this_url_path

    def get_success_url(self):
        return _return_post_design_redirect_url(self.request, self.object)


custom_design_create_view = get_view("custom_design_create_view")


class CustomDesignUpdateView(CustomDesignViewBaseMixin, _ErrorCheckerMixin, UpdateView):

    def dispatch(self, request, *args, **kwargs):
        patternspec = self.get_object()
        log_template = "User {user} is customizing an existing patternspec (ID #{spec}"
        logger.info(log_template.format(user=self.request.user, spec=patternspec.pk))
        return super(CustomDesignUpdateView, self).dispatch(request, *args, **kwargs)

    def _get_this_url_path(self, garment_name):
        pspec = self.get_object()
        this_url_path = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": garment_name},
        )
        return this_url_path

    def form_valid(self, form):

        patternspec = form.instance
        convert_to_imperial(form.cleaned_data, self.model, self.request.user)
        for field in list(form.cleaned_data.keys()):
            pspec_val = getattr(patternspec, field)
            if pspec_val != form.cleaned_data[field]:
                setattr(patternspec, field, form.cleaned_data[field])
        patternspec.full_clean()
        patternspec.save()

        redirect_url = _return_post_design_redirect_url(self.request, patternspec)
        return HttpResponseRedirect(redirect_url)

    def _check_consistency(self, request):
        patternspec = self.get_object()
        self._check_patternspec_consistency_base(request, patternspec)
        super(CustomDesignUpdateView, self)._check_consistency(request)


custom_design_update_view = get_view("custom_design_update_view")
