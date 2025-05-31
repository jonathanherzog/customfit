from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.generic.base import RedirectView

from . import views

app_name = "patterns"
urlpatterns = [
    re_path(
        r"^$",
        login_required(views.MyPatternsView.as_view()),
        name="individualpattern_list_view",
    ),
    re_path(
        r"^archived/$",
        login_required(views.IndividualPatternArchivesListView.as_view()),
        name="individualpattern_archive_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/archive/$",
        login_required(views.IndividualPatternArchiveAction.as_view()),
        name="individualpattern_archive_action",
    ),
    re_path(
        r"^(?P<pk>\d+)/unarchive/$",
        login_required(views.IndividualPatternUnarchiveAction.as_view()),
        name="individualpattern_unarchive_action",
    ),
    re_path(
        r"^new/$",
        RedirectView.as_view(
            url=None, permanent=True
        ),  # url=None will trigger a 410 Gone response.
        name="individualpattern_create_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/$",
        login_required(views.IndividualPatternDetailView.as_view()),
        name="individualpattern_detail_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/note/$",
        login_required(views.IndividualPatternNoteUpdateView.as_view()),
        name="individualpattern_note_update_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/pdf/$",
        login_required(views.IndividualPatternPdfView.as_view()),
        name="individualpattern_pdf_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/pdf/abridged$",
        login_required(views.IndividualPatternShortPdfView.as_view()),
        name="individualpattern_shortpdf_view",
    ),
    re_path(
        r"^graded/(?P<pk>\d+)/$",
        login_required(views.GradedPatternDetailView.as_view()),
        name="gradedpattern_detail_view",
    ),
]
