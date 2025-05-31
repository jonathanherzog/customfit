import logging
import os
import sys

import django.template.loader
import django.utils.text
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.forms.models import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, UpdateView, View

from customfit.views import MakePdfMixin

from .models import GradedPattern, IndividualPattern

logger = logging.getLogger(__name__)


class MyPatternsView(TemplateView):
    """
    A class-based view for the Pattern-list page. Will retrieve and use only
    those patterns which are owned by the current user. The special manager
    ensures that these patterns are also 1) approved, and 2) unarchived.
    """

    template_name = "patterns/my_patterns.html"

    def get_patterns(self):
        user = self.request.user
        queryset = IndividualPattern.live_patterns.filter(user=user).order_by(
            "-creation_date"
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super(MyPatternsView, self).get_context_data(**kwargs)
        context["pattern_list"] = self.get_patterns()
        return context


class IndividualPatternArchivesListView(ListView):
    """
    Just like MyPatternsView, except that it shows
    only archived patterns.

    Do not confuse with IndividualPatternArchiveAction, which performs the
    actual task of archiving specific patterns.
    """

    model = IndividualPattern
    template_name = "abstract_list_view.html"

    def get_queryset(self):
        user = self.request.user
        queryset = self.model.archived_patterns.filter(user=user).order_by(
            "-creation_date"
        )
        return queryset

    def get_context_data(self, **kwargs):
        context = super(IndividualPatternArchivesListView, self).get_context_data(
            **kwargs
        )
        context["header"] = "Archived Patterns"
        context["header_image_url"] = os.path.join(
            settings.STATIC_URL, "img/My_Patterns.png"
        )
        context["header_alt_text"] = "Generic photograph of sweaters"
        context["header_text"] = (
            "<p class='margin-top-20'>Create and store "
            "as many patterns as you like. Download as many PDFs as you'd "
            "like, forever. Archive patterns you won't use again to keep "
            "from seeing them in this view (you can unarchive them later "
            "if you like).</p>"
        )
        context["label"] = "Your Patterns"
        context["empty_set"] = "You have no patterns yet."
        context["empty_set_action"] = "Start creating one now."
        context["create_url"] = reverse_lazy("design_wizard:choose_type")
        context["listview_action_template"] = (
            "patterns/individualpattern_listview_action_template.html"
        )
        context["is_pattern_page"] = True

        url = reverse("patterns:individualpattern_list_view")
        context["extra_actions"] = '<a href="%s">View unarchived patterns</a>' % url
        return context


# There is no Create view, because pattern creation is handled by design_wizard.

# The Detail view for a pattern *is* very complicated. To make it simpler, we
# build a generic-view-like class to take a piece model-instance and render it
# in the appropriate 'patterntext.html' template.


class _BasePatternDetailView(DetailView):
    context_object_name = "pattern"

    def _valid_patterns_queryset(self):
        pass

    def get_object(self, queryset=None):
        # Note that we need to override the default queryset because the
        # default manager doesn't exclude unapproved patterns,
        # and to test ownership permissions.
        #
        # We are pretty sure that calling all() does not evaluate the queryset,
        # but if this view turns out to be slow, we should dig into this
        # question further.

        if queryset is None:
            queryset = self._valid_patterns_queryset()
        obj = super(_BasePatternDetailView, self).get_object(queryset)
        if obj.user == self.request.user or self.request.user.is_staff:
            return obj
        else:
            raise PermissionDenied

    def get_context_data(self, **kwargs):

        # Call the base implementation first to get a context.
        context = super(_BasePatternDetailView, self).get_context_data(**kwargs)

        # generate the pattern text
        pattern = self.object
        try:

            context["preamble_text"] = pattern.render_preamble(
                abridged=self.abridged_patterntext, for_pdf=self.for_pdf
            )
            context["instruction_text"] = pattern.render_instructions(
                abridged=self.abridged_patterntext, for_pdf=self.for_pdf
            )
            context["postamble_text"] = pattern.render_postamble(
                abridged=self.abridged_patterntext, for_pdf=self.for_pdf
            )
            context["chart_text"] = pattern.render_charts(
                abridged=self.abridged_patterntext, for_pdf=self.for_pdf
            )
            context["pattern_text"] = pattern.render_pattern(
                abridged=self.abridged_patterntext, for_pdf=self.for_pdf
            )

            # add the designer
            spec_source = pattern.get_spec_source()
            if spec_source.design_origin:
                designer = spec_source.design_origin.designer
            else:
                designer = None
            context["designer"] = designer
            return context

        except BaseException as e:
            (e_type, e_value, e_traceback) = sys.exc_info()

            username = pattern.user.username
            pattern_id = pattern.id

            error_msg = "Problem rendering pattern: user %s, pattern %s" % (
                username,
                pattern_id,
            )

            logger.error(error_msg)
            raise e_type(e_value).with_traceback(e_traceback)


class _BaseIndividualPatternDetailView(_BasePatternDetailView):
    model = IndividualPattern

    def _valid_patterns_queryset(self):
        return self.model.approved_patterns.all()


class IndividualPatternDetailView(_BaseIndividualPatternDetailView):
    template_name = "patterns/individualpattern_detail.html"

    # subclasses can change these attributes
    abridged_patterntext = False
    for_pdf = False

    def get_context_data(self, **kwargs):

        context = super(IndividualPatternDetailView, self).get_context_data(**kwargs)

        # generate the pattern text
        pattern = self.object
        spec_source = pattern.get_spec_source()

        context["picture_upload_url"] = "uploads:individual_pattern_picture_upload"
        context["manage_pictures_url"] = reverse_lazy(
            "uploads:individual_pattern_picture_edit", args=(self.object.id,)
        )

        return context


class IndividualPatternNoteUpdateView(UpdateView):
    model = IndividualPattern
    template_name = "patterns/individualpattern_note_update_form.html"
    form_class = modelform_factory(IndividualPattern, fields=("notes",))

    # Without this decorator, users may see the old value for the pattern note
    # when they are redirected to the pattern detail page, and become confused.
    # This decorator forces the transaction to conclude before we proceed.
    @transaction.atomic
    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, "Your note has been updated.")
        return super(IndividualPatternNoteUpdateView, self).form_valid(form)


class IndividualPatternPdfViewBase(MakePdfMixin, _BaseIndividualPatternDetailView):
    """
    Produces a PDF version of a IndividualPatternDetailView,
    and returns it as a HttpResponse. Operates by embedding the same
    HTML content as the IndividualPatternDetailView in a different
    top-level template, and then sending the whole thing through
    the xhtml2pdf engine.

    See:
      https://github.com/chrisglass/xhtml2pdf/blob/master/doc/usage.rst

    """

    template_name = "patterns/individualpattern_pdf.html"
    for_pdf = True

    def get_cover_sheet(self):
        cover_sheet = self.object.get_spec_source().get_cover_sheet()
        return cover_sheet


class IndividualPatternPdfView(IndividualPatternPdfViewBase):

    abridged_patterntext = False

    def make_file_name(self):
        pattern_name = self.object.name
        slug = django.utils.text.slugify(pattern_name)
        filename = slug + "-expanded.pdf"
        return filename

    def get_context_data(self, **kwargs):
        context = super(IndividualPatternPdfView, self).get_context_data(**kwargs)
        context["pattern_title"] = self.object.name + " (expanded)"
        return context


class IndividualPatternShortPdfView(IndividualPatternPdfViewBase):

    abridged_patterntext = True

    def make_file_name(self):
        pattern_name = self.object.name
        slug = django.utils.text.slugify(pattern_name)
        filename = slug + ".pdf"
        return filename

    def get_context_data(self, **kwargs):
        context = super(IndividualPatternShortPdfView, self).get_context_data(**kwargs)
        context["pattern_title"] = self.object.name
        return context


class GradedPatternDetailView(_BasePatternDetailView):
    model = GradedPattern
    template_name = "patterns/gradedpattern_detail.html"
    abridged_patterntext = True
    for_pdf = False

    def _valid_patterns_queryset(self):
        return self.model.objects.all()


class IndividualPatternAction(View):
    """
    Superclass for functionality shared by ArchiveAction and UnarchiveAction.
    Is not intended to be exposed to the user.

    Subclasses are required to define an attribute 'should_be_archived',
    which indicates whether the pattern should have archived = True or
    not when the (un)archiving action is complete.
    """

    def __init__(self, **kwargs):
        super(IndividualPatternAction, self).__init__(**kwargs)
        if not hasattr(self, "should_be_archived"):
            raise NotImplementedError

        # This specifies the English string we should use in logging
        # and messaging to describe the action we are performing.
        if self.should_be_archived:
            self.action_string = "archive"
        else:
            self.action_string = "unarchive"

    def dispatch(self, request, *args, **kwargs):
        logger.info(
            "User %s is attempting to %s a pattern", request.user, self.action_string
        )

        # Make sure it's a valid pattern.
        try:
            pk = kwargs["pk"]
            pattern = IndividualPattern.approved_patterns.get(pk=pk)
        except IndividualPattern.DoesNotExist:
            logger.exception(
                "Pattern to %s does not exist or is not approved", self.action_string
            )
            raise Http404
        except KeyError:
            logger.exception(
                "No primary key provided for pattern to %s", self.action_string
            )
            raise Http404

        # Make the user owns this pattern.
        if not pattern.user == request.user:
            logger.error(
                "User %s attempted to %s pattern %s but does not own it",
                request.user,
                self.action_string,
                pattern,
            )
            raise PermissionDenied

        # If it's already in the desired state, we don't need to do anything
        # (except tell the user we hear them).
        if pattern.archived == self.should_be_archived:
            return self._return_pattern(request, pattern)
        else:
            return super(IndividualPatternAction, self).dispatch(
                request, *args, **kwargs
            )

    def get(self, request, *args, **kwargs):
        # This is guaranteed by dispatch() to be safe: we can only hit the
        # get() method if the pattern exists, is not yet in the desired state
        # vis-a-vis archiving, and belongs to the user.
        pk = kwargs["pk"]
        pattern = IndividualPattern.approved_patterns.get(pk=pk)
        pattern.archived = self.should_be_archived
        pattern.save()
        logger.info("Pattern %s has been %sd", pattern, self.action_string)
        return self._return_pattern(request, pattern)

    def _return_pattern(self, request, pattern):
        messages.add_message(
            request, messages.INFO, "This pattern has been %sd." % self.action_string
        )
        pattern_url = pattern.get_absolute_url()
        return HttpResponseRedirect(pattern_url)


class IndividualPatternArchiveAction(IndividualPatternAction):
    """
    Archives patterns.
    """

    should_be_archived = True


class IndividualPatternUnarchiveAction(IndividualPatternAction):
    """
    Unarchives patterns.
    """

    should_be_archived = False
