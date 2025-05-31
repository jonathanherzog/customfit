from django.contrib.auth.decorators import login_required
from django.urls import re_path

from customfit.design_wizard import views

app_name = "design_wizard"
urlpatterns = [
    # Choose design type
    # --------------------------------------------------------------------------
    re_path(
        r"^$", login_required(views.ChooseDesignTypeView.as_view()), name="choose_type"
    ),
    # Note that the regex in the next line is from the django documentation
    # as the regex for slugs:
    # https://docs.djangoproject.com/en/1.9/ref/validators/#validate-slug
    re_path(
        r"^personalize/(?P<design_slug>[-a-zA-Z0-9_]+)/$",
        login_required(views.personalize_design_create_view),
        name="personalize",
    ),
    # These are used after we have added missing measurements in the midst of
    # a pattern creation process; we have an extra URL pk to maintain state
    # about the patternspec under development.
    re_path(
        r"^personalize/(?P<design_slug>[-a-zA-Z0-9_]+)/(?P<pk>[0-9]+)$",
        login_required(views.personalize_design_update_view),
        name="personalize_plus_missing",
    ),
    # Custom designs
    # --------------------------------------------------------------------------
    re_path(
        r"^custom/(?P<garment>[-a-zA-Z0-9_]+)/$",
        login_required(views.custom_design_create_view),
        name="custom_design_create_view_garment",
    ),
    re_path(
        r"^custom/(?P<garment>[-a-zA-Z0-9_]+)/(?P<pk>[0-9]+)$",
        login_required(views.custom_design_update_view),
        name="custom_design_plus_missing_garment",
    ),
    # Add missing measurements
    # --------------------------------------------------------------------------
    re_path(
        r"^missing/(?P<pk>[0-9]+)/$",
        login_required(views.add_missing_measurements_patternspec_view),
        name="missing",
    ),
    re_path(
        r"^missing/(?P<pk>[0-9]+)/(?P<action>\w+)/$",
        login_required(views.add_missing_measurements_patternspec_view),
        name="missing",
    ),
    # re_path(r'^missing/redo/(?P<pk>[0-9]+)/$',
    #     views.AddMissingMeasurementsToRedoView.as_view(),
    #     name='missing_redo'),
    re_path(
        r"^missing/redo/(?P<pk>[0-9]+)/(?P<action>\w+)/$",
        login_required(views.add_missing_measurements_redo_view),
        name="missing_redo",
    ),
    re_path(
        r"^tweak/(?P<pk>[0-9]+)/$",
        # Note: decorated by GuardingHat. See view declaration
        login_required(views.tweak_garment_view),
        name="tweak",
    ),
    # Approve a new design
    # --------------------------------------------------------------------------
    re_path(
        r"^summary/(?P<igp_id>\w+)/$",
        # Note: decorated by GuardingHat. See view declaration
        login_required(views.summary_and_approve_view),
        name="summary",
    ),
    # Redo existing patterns
    # --------------------------------------------------------------------------
    re_path(
        r"^redo/(?P<pk>\d+)/$",
        login_required(views.redo_create_view),
        name="redo_start",
    ),
    re_path(
        r"^redo/(?P<pk>[0-9]+)$",
        login_required(views.redo_update_view),
        name="redo_plus_missing",
    ),
    re_path(
        r"^redo/tweak/(?P<pk>\d+)/$",
        login_required(views.tweak_redo_view),
        name="redo_tweak",
    ),
    re_path(
        r"^redo/approve/(?P<igp_id>\d+)/$",
        login_required(views.redo_approve_view),
        name="redo_approve",
    ),
]
