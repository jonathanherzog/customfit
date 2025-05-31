import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, FormView, ListView
from django.views.generic.base import TemplateView

from customfit.bodies.models import Body
from customfit.patterns.models import IndividualPattern
from customfit.swatches.models import Swatch

from .forms import (
    BodyPictureUploadForm,
    IndividualPatternPictureUploadForm,
    SwatchPictureUploadForm,
)
from .models import AwesomePicture, BodyPicture, IndividualPatternPicture, SwatchPicture

logger = logging.getLogger(__name__)


class AwesomeView(TemplateView):
    template_name = "awesome.html"

    def get_context_data(self, **kwargs):
        context = super(AwesomeView, self).get_context_data(**kwargs)
        awesome = AwesomePicture.objects.all()
        context.update(
            {
                "awesome_list_basics": awesome.exclude(design=None)
                .filter(design__is_basic=True)
                .order_by("pk")
                .reverse()[:12],
                "awesome_list_designs": awesome.exclude(design=None)
                .filter(design__is_basic=False)
                .order_by("pk")
                .reverse()[:12],
                "awesome_list_custom": awesome.filter(design=None)
                .order_by("pk")
                .reverse()[:12],
            }
        )
        return context


class GenericPictureUploadView(FormView):
    template_name = "upload.html"

    def dispatch(self, *args, **kwargs):
        """
        Make sure the body/pattern/swatch we're uploading a picture for
        belongs to the user viewing the page.
        """
        try:
            object_in_the_picture = (
                self.form_class.Meta.model.object.get_queryset().get(
                    pk=self.kwargs["pk"]
                )
            )
            assert object_in_the_picture.user == self.request.user
            return super(GenericPictureUploadView, self).dispatch(*args, **kwargs)
        except AssertionError:
            raise PermissionDenied

    def get_context_data(self, **kwargs):
        """
        If they've already maxed out their quota of photos for this
        body/pattern/swatch, don't let them upload more.
        Note that Meta.model is BodyPicture (etc.) not Body (etc.), so we're
        counting BodyPictures (etc.) here, not bodies.
        """
        context = super(GenericPictureUploadView, self).get_context_data(**kwargs)
        object_picture_is_of = self.form_class.Meta.model.object.get_queryset().get(
            pk=self.kwargs["pk"]
        )
        context["object_pictured"] = object_picture_is_of
        if object_picture_is_of.pictures.count() >= settings.MAX_PICTURES:
            context["add_more"] = False
        else:
            context["add_more"] = True
        return context

    def get_form(self, form_class=None):
        """
        This exists solely to add the pk argument so we can track which body,
        pattern, swatch we're uploading content for.
        """
        pk = self.kwargs["pk"]
        if not form_class:
            form_class = self.get_form_class()
        return form_class(pk, **self.get_form_kwargs())

    def form_valid(self, form):
        """
        The ThingPicture classes have picture and object fields.
        We got ThingPicture.instance.picture from the upload.
        We derive ThingPicture.instance.object (the associated body, pattern,
        swatch) from the modelform class and the pk in the url,
        then actually save the ThingPicture object and communicate out.
        """
        try:
            self.associated_object = (
                self.form_class.Meta.model.object.get_queryset().get(
                    pk=self.kwargs["pk"]
                )
            )
        except IndividualPattern.DoesNotExist:
            # In case people try to upload pics for an unapproved pattern.
            IndividualPattern.even_unapproved.get(pk=self.kwargs["pk"])
        form.instance.object = self.associated_object
        form.instance.save()
        logger.info(
            "User %s uploaded a picture for %s with id %s"
            % (self.request.user.username, form.instance.object, form.instance.id)
        )
        messages.add_message(
            self.request,
            messages.INFO,
            "Hooray, photo uploaded " "for %s!" % form.instance.object,
        )
        return super(GenericPictureUploadView, self).form_valid(form)


class BodyPictureUploadView(GenericPictureUploadView):
    form_class = BodyPictureUploadForm

    def get_success_url(self):
        if self.request.user.profile.is_yarn_store:
            return reverse_lazy(
                "uploads:body_picture_edit", args=(self.associated_object.id,)
            )
        else:
            return reverse_lazy("bodies:body_list_view")


class SwatchPictureUploadView(GenericPictureUploadView):
    form_class = SwatchPictureUploadForm

    def get_success_url(self):
        return reverse_lazy("swatches:swatch_list_view")


class IndividualPatternPictureUploadView(GenericPictureUploadView):
    form_class = IndividualPatternPictureUploadForm

    def get_success_url(self):
        if self.request.user.profile.is_yarn_store:
            return reverse_lazy(
                "uploads:individual_pattern_picture_edit",
                args=(self.associated_object.id,),
            )
        else:
            return reverse_lazy("patterns:individualpattern_list_view")


# We need to avoid caching the picture list views, or they will appear to the user
# not to have changed after the user uploads or deletes photos. We've decorated
# with never_cache in urls.py but that's not sufficient; see
# http://stackoverflow.com/questions/2095520/fighting-client-side-caching-in-django .
def force_no_cache(request):
    request.META["Cache-Control"] = "no-cache, no-store, must-revalidate"
    request.META["Pragma"] = "no-cache"
    request.META["Expires"] = "0"


# The PictureEditViews allow users to delete pictures and select featured
# pictures.
class BodyPictureEditView(ListView):
    template_name = "abstract_picture_edit_view.html"

    def dispatch(self, request, *args, **kwargs):
        self.associated_object = Body.objects.get(pk=kwargs["pk"])
        if request.user != self.associated_object.user:
            raise PermissionDenied
        force_no_cache(request)
        return super(BodyPictureEditView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BodyPictureEditView, self).get_context_data(**kwargs)
        context["object"] = self.associated_object
        context["empty_set"] = "No pictures yet for %s." % self.associated_object.name
        context["empty_set_action"] = "Why not upload one?"
        context["empty_set_action_url"] = reverse(
            "uploads:body_picture_upload", args=(self.kwargs["pk"],)
        )
        context["object_delete_url"] = "uploads:body_picture_delete"
        context["feature_url"] = "uploads:body_picture_feature"
        context["upload_url"] = None
        if self.associated_object.pictures.count() < settings.MAX_PICTURES:
            context["upload_url"] = reverse(
                "uploads:body_picture_upload", args=(self.associated_object.id,)
            )
        return context

    def get_queryset(self):
        body_id = self.kwargs["pk"]
        return BodyPicture.objects.filter(object__id=body_id)


class SwatchPictureEditView(ListView):
    template_name = "abstract_picture_edit_view.html"

    def dispatch(self, request, *args, **kwargs):
        self.associated_object = Swatch.objects.get(pk=kwargs["pk"])
        if request.user != self.associated_object.user:
            raise PermissionDenied
        force_no_cache(request)
        return super(SwatchPictureEditView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SwatchPictureEditView, self).get_context_data(**kwargs)
        context["object"] = self.associated_object
        context["empty_set"] = "No pictures yet for %s." % self.associated_object.name
        context["empty_set_action"] = "Why not upload one?"
        context["empty_set_action_url"] = reverse(
            "uploads:swatch_picture_upload", args=(self.kwargs["pk"],)
        )
        context["object_delete_url"] = "uploads:swatch_picture_delete"
        context["feature_url"] = "uploads:swatch_picture_feature"
        context["upload_url"] = None
        if self.associated_object.pictures.count() < settings.MAX_PICTURES:
            context["upload_url"] = reverse(
                "uploads:swatch_picture_upload", args=(self.associated_object.id,)
            )
        return context

    def get_queryset(self):
        swatch_id = self.kwargs["pk"]
        return SwatchPicture.objects.filter(object__id=swatch_id)


class IndividualPatternPictureEditView(ListView):
    template_name = "abstract_picture_edit_view.html"

    def dispatch(self, request, *args, **kwargs):
        self.associated_object = IndividualPattern.even_unapproved.get(pk=kwargs["pk"])
        if request.user != self.associated_object.user:
            raise PermissionDenied
        force_no_cache(request)
        return super(IndividualPatternPictureEditView, self).dispatch(
            request, *args, **kwargs
        )

    def get_context_data(self, **kwargs):
        context = super(IndividualPatternPictureEditView, self).get_context_data(
            **kwargs
        )
        context["object"] = self.associated_object
        context["empty_set"] = "No pictures yet for %s." % self.associated_object.name
        context["empty_set_action"] = "Why not upload one?"
        context["empty_set_action_url"] = reverse(
            "uploads:individual_pattern_picture_upload", args=(self.kwargs["pk"],)
        )
        context["object_delete_url"] = "uploads:individual_pattern_picture_delete"
        context["feature_url"] = "uploads:individual_pattern_picture_feature"
        context["upload_url"] = None
        if self.associated_object.pictures.count() < settings.MAX_PICTURES:
            context["upload_url"] = reverse(
                "uploads:individual_pattern_picture_upload",
                args=(self.associated_object.id,),
            )
        return context

    def get_queryset(self):
        pattern_id = self.kwargs["pk"]
        return IndividualPatternPicture.objects.filter(object__id=pattern_id)


class PictureDeleteView(DeleteView):
    """
    An abstract delete view which works for body, swatch, or pattern pictures.
    """

    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()

        # Figure out whether we're dealing with a body, swatch, or pattern pic.
        self.object_type_name = obj._meta.verbose_name

        """
        After we delete the object we'll no longer be able to fetch these
        properties; let's store them here so we'll be able to do descriptive
        log & success messages in get_success_url().
        """
        self.id = obj.id
        self.associated_object = obj.object

        # If this is the featured pic for something, we'll have to make sure to
        # un-feature it later.
        self.featured = False
        if self.associated_object.featured_pic == obj:
            self.featured = True

        logger.info(
            "User %s is attempting to delete %s with id %s"
            % (self.request.user.username, self.object_type_name, self.id)
        )
        # Users can only delete their own pictures.
        if not self.associated_object.user == self.request.user:
            logger.warning(
                "User %s tried (unsuccessfully) to delete a %s "
                "with id %s, which belongs to %s."
                % (
                    self.request.user.username,
                    self.object_type_name,
                    self.id,
                    obj.username,
                )
            )
            raise PermissionDenied
        return super(PictureDeleteView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        if self.featured:
            self.associated_object.featured_pic = None
            self.associated_object.save()
        logger.info(
            "User %s deleted %s with id %s"
            % (self.request.user.username, self.object_type_name, self.id)
        )
        messages.add_message(
            self.request,
            messages.INFO,
            "Your picture " "for " + self.associated_object.name + " has been deleted.",
        )
        url = "uploads:%s_edit" % self.object_type_name.replace(" ", "_")
        return reverse_lazy(url, args=(self.associated_object.id,))


class BodyPictureDeleteView(PictureDeleteView):
    model = BodyPicture


class SwatchPictureDeleteView(PictureDeleteView):
    model = SwatchPicture


class IndividualPatternPictureDeleteView(PictureDeleteView):
    model = IndividualPatternPicture


class PictureFeatureView(TemplateView):
    template_name = "feature_pic.html"

    def post(self, request, *args, **kwargs):
        self.picture.object.featured_pic = self.picture
        self.picture.object.save()
        logger.info(
            "User %s featured pic %s for %s %s"
            % (
                self.request.user,
                self.picture.id,
                self.picture.object._meta.verbose_name,
                self.picture.object,
            )
        )
        messages.add_message(request, messages.INFO, "Featured picture updated!")
        return HttpResponseRedirect(self.finish_url)

    def get_context_data(self, **kwargs):
        context = super(PictureFeatureView, self).get_context_data(**kwargs)
        context["picture"] = self.picture
        context["cancel_url"] = self.finish_url
        return context


class BodyPictureFeatureView(PictureFeatureView):
    def dispatch(self, request, *args, **kwargs):
        self.picture = BodyPicture.objects.get(pk=kwargs["pk"])
        if request.user.profile.is_yarn_store:
            self.finish_url = reverse(
                "uploads:body_picture_edit", args=(self.picture.object.id,)
            )
        else:
            self.finish_url = reverse("bodies:body_list_view")
        return super(BodyPictureFeatureView, self).dispatch(request, *args, **kwargs)


class SwatchPictureFeatureView(PictureFeatureView):
    def dispatch(self, request, *args, **kwargs):
        self.picture = SwatchPicture.objects.get(pk=kwargs["pk"])
        if request.user.profile.is_yarn_store:
            self.finish_url = reverse(
                "uploads:swatch_picture_edit", args=(self.picture.object.id,)
            )
        else:
            self.finish_url = reverse("swatches:swatch_list_view")
        return super(SwatchPictureFeatureView, self).dispatch(request, *args, **kwargs)


class IndividualPatternPictureFeatureView(PictureFeatureView):
    def dispatch(self, request, *args, **kwargs):
        self.picture = IndividualPatternPicture.objects.get(pk=kwargs["pk"])
        if request.user.profile.is_yarn_store:
            self.finish_url = reverse(
                "uploads:individual_pattern_picture_edit",
                args=(self.picture.object.id,),
            )
        else:
            self.finish_url = reverse("patterns:individualpattern_list_view")
        return super(IndividualPatternPictureFeatureView, self).dispatch(
            request, *args, **kwargs
        )
