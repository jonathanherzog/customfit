from django.urls import re_path
from django.views.generic.base import RedirectView

app_name = "sweaters"
urlpatterns = [
    # Yes, this first URL is very close to /design/X for the design_wizard app
    # (once you include the /designs/ prefix applied in the top-level urls.py),
    # but actual users expressed a preference for it.
    re_path(
        r"^$",
        RedirectView.as_view(pattern_name="designs:all_designs", permanent=True),
        name="all_designs",
    ),
    re_path(
        r"^(?P<silhouette>[-\w]+)/$",
        RedirectView.as_view(pattern_name="designs:all_designs", permanent=True),
        name="all_designs_by_silhouette",
    ),
]
