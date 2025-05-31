from django.contrib.auth.decorators import login_required
from django.urls import re_path

from customfit.bodies import views

from .decorators import can_make_body

app_name = "bodies"
urlpatterns = [
    re_path(r"^$", login_required(views.BodyListView.as_view()), name="body_list_view"),
    re_path(
        r"^new/$",
        can_make_body(login_required(views.BodyCreateView.as_view())),
        name="body_create_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/pdf/$",
        login_required(views.BodyDetailViewPdf.as_view()),
        name="body_detail_view_pdf",
    ),
    re_path(
        r"^(?P<pk>\d+)/$",
        login_required(views.BodyDetailView.as_view()),
        name="body_detail_view",
    ),
    re_path(
        r"^update/(?P<pk>\d+)/$",
        login_required(views.BodyUpdateView.as_view()),
        name="body_update_view",
    ),
    re_path(
        r"^copy/(?P<pk>\d+)/$",
        can_make_body(login_required(views.BodyCopyView.as_view())),
        name="body_copy_view",
    ),
    re_path(
        r"^note/(?P<pk>\d+)/$",
        login_required(views.BodyNoteUpdateView.as_view()),
        name="body_note_update_view",
    ),
    re_path(
        r"^delete/(?P<pk>\d+)/$",
        login_required(views.BodyDeleteView.as_view()),
        name="body_delete_view",
    ),
]
