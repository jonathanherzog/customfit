from django.contrib.auth.decorators import login_required
from django.urls import re_path

from customfit.swatches import views

app_name = "swatches"
urlpatterns = [
    re_path(
        r"^$", login_required(views.SwatchListView.as_view()), name="swatch_list_view"
    ),
    re_path(
        r"^new/$",
        login_required(views.SwatchCreateView.as_view()),
        name="swatch_create_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/$",
        login_required(views.SwatchDetailView.as_view()),
        name="swatch_detail_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/note/$",
        login_required(views.SwatchNoteUpdateView.as_view()),
        name="swatch_note_update_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/edit/$",
        login_required(views.SwatchUpdateView.as_view()),
        name="swatch_update_view",
    ),
    re_path(
        r"^(?P<pk>\d+)/delete/$",
        login_required(views.SwatchDeleteView.as_view()),
        name="swatch_delete_view",
    ),
]
