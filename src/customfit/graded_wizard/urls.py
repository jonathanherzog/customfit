from django.contrib.admin.views.decorators import staff_member_required
from django.urls import re_path

from . import views

# from django.views.generic.base import RedirectView
#
#
# from customfit.decorators import secure_required


app_name = "graded_wizard"
urlpatterns = [
    # Choose design type
    # --------------------------------------------------------------------------
    re_path(
        r"^$",
        staff_member_required(views.ListPatternsView.as_view()),
        name="list_patterns",
    ),
    re_path(
        r"^personalize/$",
        staff_member_required(views.ChooseDesignView.as_view()),
        name="choose_design",
    ),
    # # Note that the regex in the next line is from the django documentation
    # # as the regex for slugs:
    # # https://docs.djangoproject.com/en/1.9/ref/validators/#validate-slug
    re_path(
        r"^(?P<design_slug>[-a-zA-Z0-9_]+)/$",
        staff_member_required(views.personalize_graded_view),
        name="make_graded_pattern",
    ),
]
