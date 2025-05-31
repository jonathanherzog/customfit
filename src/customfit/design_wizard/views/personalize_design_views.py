import logging

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, FormView, UpdateView, View

from customfit.bodies.views import delete_body_from_session, get_body_from_session
from customfit.designs.models import Design
from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.helpers.math_helpers import convert_to_imperial
from customfit.patterns.models import IndividualPattern, Redo
from customfit.swatches.views import delete_swatch_from_session, get_swatch_from_session

from .garment_registry import model_to_view
from .helpers import _ErrorCheckerMixin, _return_post_design_redirect_url

logger = logging.getLogger(__name__)


def get_view_personalize(view_name):

    def view(request, *args, **kwargs):

        design_slug = kwargs["design_slug"]
        design = get_object_or_404(Design, slug=design_slug)

        inner_view = model_to_view(design, view_name)

        return inner_view(request, *args, **kwargs)

    return view


# Helper Mixins to keep things DRY


class SessionClearingMixin(object):
    def post(self, request, *args, **kwargs):
        # at this point, we should remove the body/swatch from the session
        # so that any form-error handling is based only on what was submitted
        # in the form
        session = self.request.session
        delete_body_from_session(session)
        delete_swatch_from_session(session)

        return super(SessionClearingMixin, self).post(request, *args, **kwargs)


class GetInitialFromSessionMixin(object):

    def get_initial(self):
        initial = super(GetInitialFromSessionMixin, self).get_initial()
        user = self.request.user
        session = self.request.session
        try:
            body = get_body_from_session(session, user)
            if body.user == user:
                initial["body"] = body
            else:
                delete_body_from_session()
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


class AddBodyCreateURLMixin(object):

    def get_form_kwargs(self):
        kwargs = super(AddBodyCreateURLMixin, self).get_form_kwargs()
        this_url_path = self.request.path
        create_body_url = reverse("bodies:body_create_view") + "?next=" + this_url_path
        kwargs["create_body_url"] = create_body_url
        return kwargs


class AddSwatchCreateURLMixin(object):

    def get_form_kwargs(self):
        kwargs = super(AddSwatchCreateURLMixin, self).get_form_kwargs()
        this_url_path = self.request.path
        create_swatch_url = (
            reverse("swatches:swatch_create_view") + "?next=" + this_url_path
        )
        kwargs["create_swatch_url"] = create_swatch_url
        return kwargs


class AddCreateURLsMixin(AddBodyCreateURLMixin, AddSwatchCreateURLMixin):
    pass


##############################################################################################################
#
# Abstracted personalize views
#
##############################################################################################################


class _PersonalizeDesignViewBase(SessionClearingMixin):

    template_name = "design_wizard/personalize_design.html"

    def get_form_kwargs(self):
        kwargs = super(_PersonalizeDesignViewBase, self).get_form_kwargs()
        design = self.get_design()
        kwargs["design"] = design
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        """
        This gets the context shared by get() and post().
        """
        context = super(_PersonalizeDesignViewBase, self).get_context_data(**kwargs)
        design = self.get_design()
        path = self._get_design_url_path()
        share_url = self.request.build_absolute_uri(path)

        more_context = {
            "login_url": settings.LOGIN_URL,
            "design": design,
            "url_to_share": share_url,
        }
        context.update(more_context)

        return context

    def get_design(self):
        design_slug = self.kwargs["design_slug"]
        design = get_object_or_404(Design, slug=design_slug)
        return design

    def _get_design_url_path(self):
        design = self.get_design()
        path = design.get_absolute_url()
        return path

    def dispatch(self, request, *args, **kwargs):

        # Can't use get_design() since self.kwargs have not been set yet
        design_slug = kwargs.get("design_slug", None)
        design = get_object_or_404(Design, slug=design_slug)

        logger.info(
            "User {user} is personalizing design {design}".format(
                user=request.user, design=design_slug
            )
        )

        # Note: this next method-call works even for anonymous users.
        if not design.is_visible_to_user(request.user):
            # Some designs are created as byproducts of the pattern generation
            # process and are for internal use only.
            logger.info(
                "User %s tried to view disallowed design %s", request.user, design.id
            )
            raise PermissionDenied

        return super(_PersonalizeDesignViewBase, self).dispatch(
            request, *args, **kwargs
        )

    def get_success_url(self):
        redirect_url = _return_post_design_redirect_url(self.request, self.object)
        return redirect_url


class PersonalizeDesignCreateView(
    GetInitialFromSessionMixin, _PersonalizeDesignViewBase, CreateView
):

    def form_valid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted a valid (create) design personalization form for design %s",
            self.request.user,
            design.name,
        )
        return super(PersonalizeDesignCreateView, self).form_valid(form)

    def form_invalid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted an invalid (create) design personalization form for design %s",
            self.request.user,
            design.name,
        )
        logger.debug("Form errors: %s", form.errors)
        return super(PersonalizeDesignCreateView, self).form_invalid(form)


class PersonalizeDesignUpdateView(
    GetInitialFromSessionMixin, _PersonalizeDesignViewBase, UpdateView
):

    def _check_for_existing_pattern(self, patternspec):
        # If an approved pattern has already been made from this spec,
        # don't let them make another, in case there's some assumption
        # we made that gets violated.
        if IndividualPattern.objects.filter(
            pieces__schematic__individual_garment_parameters__pattern_spec=patternspec
        ):
            logger.warning(
                "User {user} tried to personalize design "
                "with patternspec {spec}, but there is already a "
                "pattern from that spec.".format(
                    user=self.request.user, spec=patternspec.id
                )
            )
            raise PermissionDenied

    def get_object(self, queryset=None):
        object = super(PersonalizeDesignUpdateView, self).get_object(queryset)

        design = self.get_design()
        assert object.design_origin == design

        if object.user != self.request.user:
            raise PermissionDenied

        self._check_for_existing_pattern(object)

        return object

    def form_valid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted a valid (update) design personalization form for design %s",
            self.request.user,
            design.name,
        )
        return super(PersonalizeDesignUpdateView, self).form_valid(form)

    def form_invalid(self, form):
        design = self.get_design()
        logger.info(
            "User %s has posted an invalid (update) design personalization form for design %s",
            self.request.user,
            design.name,
        )
        return super(PersonalizeDesignUpdateView, self).form_invalid(form)


personalize_design_create_view = get_view_personalize("personalize_create_view")
personalize_design_update_view = get_view_personalize("personalize_update_view")


##############################################################################################################
#
# Redo views
#
##############################################################################################################


def get_view_redo(view_name, klass):

    def view(request, *args, **kwargs):

        pattern_id = kwargs["pk"]
        pattern = get_object_or_404(klass, id=pattern_id)

        inner_view = model_to_view(pattern, view_name)

        return inner_view(request, *args, **kwargs)

    return view


class _RedoViewBase(_ErrorCheckerMixin, AddSwatchCreateURLMixin):

    def _get_pattern(self):
        pattern_pk = self.kwargs["pk"]
        pattern = get_object_or_404(IndividualPattern, pk=pattern_pk)
        return pattern

    def _check_consistency(self, request):
        # Check-- is it possible to redo this pattern? If not,
        # return permission denied.
        if not self._get_pattern().redo_possible():
            raise PermissionDenied()
        return super(_RedoViewBase, self)._check_consistency(request)

    def get_success_url(self):
        # WE might be going to tweak, summary, or add-missing measurements. Let's
        # use the existing state machine to figure out which.
        redirect_url = _return_post_design_redirect_url(self.request, self.object)
        return redirect_url


class RedoCreateView(
    GetInitialFromSessionMixin, _RedoViewBase, SessionClearingMixin, CreateView
):

    def _check_consistency(self, request):
        pattern = self._get_pattern()
        self._check_pattern_consistency_base(request, pattern)
        return super(RedoCreateView, self)._check_consistency(request)

    def get_form_kwargs(self):
        kwargs = super(RedoCreateView, self).get_form_kwargs()
        pattern = self._get_pattern()
        kwargs["pattern"] = pattern
        kwargs["user"] = self.request.user

        return kwargs

    def form_valid(self, form):
        redo_params = convert_to_imperial(
            form.cleaned_data, self.model, self.request.user
        )
        self.object = self.model(**redo_params)
        self.object.pattern = self._get_pattern()
        self.object.full_clean()
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


class RedoUpdateView(_RedoViewBase, UpdateView):

    def _check_consistency(self, request):
        redo = self.get_object()
        self._check_redo_consistency_base(request, redo)
        return super(RedoUpdateView, self)._check_consistency(request)

    def _get_pattern(self):
        return self.get_object().pattern

    def get_form_kwargs(self):
        kwargs = super(RedoUpdateView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["pattern"] = self._get_pattern()
        return kwargs

    def form_valid(self, form):
        super(RedoUpdateView, self).form_valid(form)

        # Delete any old IGPs that are based on this redo
        IndividualGarmentParameters.objects.filter(redo=self.object).delete()

        return HttpResponseRedirect(self.get_success_url())


redo_create_view = get_view_redo("redo_create_view", IndividualPattern)
redo_update_view = get_view_redo("redo_update_view", Redo)
