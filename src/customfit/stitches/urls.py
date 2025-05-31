from django.urls import re_path

from .views import StitchDetailView, StitchListView

# Do not have a urlpattern with "r'^featured" lest you conflict with the
# featured_stitches URLpattern. That app has been deprecated, but why
# borrow trouble, lest we resurrect it?

app_name = "stitch_models"
urlpatterns = [
    re_path(r"^$", StitchListView.as_view(), name="stitch_list_view"),
    re_path(r"^(?P<pk>\d+)$", StitchDetailView.as_view(), name="stitch_detail_view"),
]
