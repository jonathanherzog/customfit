import logging
from collections import namedtuple

from django.urls import reverse_lazy
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

GarmentViewContainer = namedtuple(
    "GarmentViewContainer",
    [
        "personalize_create_view",
        "personalize_update_view",
        "custom_design_create_view",
        "custom_design_update_view",
        "redo_create_view",
        "redo_update_view",
        "add_missing_measurements_patternspec_view",
        "add_missing_measurements_redo_view",
        "tweak_patternspec_view",
        "tweak_redo_view",
        "approve_patternspec_view",
        "approve_redo_view",
    ],
)


view_dict = {
    "sweaters": GarmentViewContainer(
        personalize_create_view="customfit.sweaters.views.PersonalizeSweaterCreateView",
        personalize_update_view="customfit.sweaters.views.PersonalizeSweaterUpdateView",
        custom_design_create_view="customfit.sweaters.views.CustomSweaterDesignCreateView",
        custom_design_update_view="customfit.sweaters.views.CustomSweaterDesignUpdateView",
        redo_create_view="customfit.sweaters.views.SweaterRedoCreateView",
        redo_update_view="customfit.sweaters.views.SweaterRedoUpdateView",
        tweak_patternspec_view="customfit.sweaters.views.TweakSweaterView",
        tweak_redo_view="customfit.sweaters.views.TweakRedoSweaterView",
        add_missing_measurements_patternspec_view="customfit.sweaters.views.SweaterAddMissingMeasurementsView",
        add_missing_measurements_redo_view="customfit.sweaters.views.SweaterAddMissingMeasurementsToRedoView",
        approve_patternspec_view="customfit.sweaters.views.SweaterSummaryAndApproveView",
        approve_redo_view="customfit.sweaters.views.SweaterRedoApproveView",
    ),
    "cowls": GarmentViewContainer(
        personalize_create_view="customfit.cowls.views.PersonalizeCowlCreateView",
        personalize_update_view="customfit.cowls.views.PersonalizeCowlUpdateView",
        custom_design_create_view="customfit.cowls.views.CustomCowlDesignCreateView",
        custom_design_update_view=None,  # cowls don't depend on bodies
        redo_create_view="customfit.cowls.views.CowlRedoCreateView",
        redo_update_view=None,  # cowls don't depend on bodies
        tweak_patternspec_view="customfit.cowls.views.TweakCowlView",
        tweak_redo_view="customfit.cowls.views.TweakRedoCowlView",
        add_missing_measurements_patternspec_view=None,  # cowls don't depend on bodies
        add_missing_measurements_redo_view=None,  # cowls don't depend on bodies
        approve_patternspec_view="customfit.cowls.views.CowlSummaryAndApproveView",
        approve_redo_view="customfit.cowls.views.CowlRedoApproveView",
    ),
    "test_garment": GarmentViewContainer(  # needed for testing
        personalize_create_view="customfit.test_garment.views.TestPersonalizeCreateView",
        personalize_update_view="customfit.test_garment.views.TestPersonalizeUpdateView",
        custom_design_create_view="customfit.test_garment.views.CustomTestDesignCreateView",
        custom_design_update_view="customfit.test_garment.views.CustomTestDesignUpdateView",
        redo_create_view="customfit.test_garment.views.TestRedoCreateView",
        redo_update_view="customfit.test_garment.views.TestRedoUpdateView",
        tweak_patternspec_view="customfit.test_garment.views.TweakTestView",
        tweak_redo_view="customfit.test_garment.views.TweakRedoTestView",
        add_missing_measurements_patternspec_view="customfit.test_garment.views.TestAddMissingMeasurementsView",
        add_missing_measurements_redo_view="customfit.test_garment.views.TestAddMissingMeasurementsToRedoView",
        approve_patternspec_view="customfit.test_garment.views.TestSummaryAndApproveView",
        approve_redo_view="customfit.test_garment.views.TestRedoApproveView",
    ),
}


def model_to_view(model, view_name):

    logger.debug("view_name: %s", view_name)
    model_app_label = model._meta.app_label
    view_class_tuple = view_dict[model_app_label]
    view_class_name = getattr(view_class_tuple, view_name)
    view_class = import_string(view_class_name)
    return view_class.as_view()


def app_name_to_view(app_name, view_name):

    logger.debug("view_name: %s", view_name)
    view_class_tuple = view_dict[app_name]
    view_class_name = getattr(view_class_tuple, view_name)
    view_class = import_string(view_class_name)
    return view_class.as_view()


MYO_OPTIONS = [
    (
        "sweater",
        reverse_lazy(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": "sweaters"},
        ),
        "img/byo-sweater-image.png",
    ),
    (
        "cowl",
        reverse_lazy(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": "cowls"},
        ),
        "img/byo-cowl-image.png",
    ),
]
