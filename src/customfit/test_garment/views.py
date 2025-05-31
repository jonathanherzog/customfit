# -*- coding: utf-8 -*-


from customfit.design_wizard.views import (
    AddMissingMeasurementsViewBase,
    AddMissingMeasurementsViewPatternspecMixin,
    AddMissingMeasurementsViewRedoMixin,
    BaseRedoTweakView,
    BaseTweakGarmentView,
    CustomDesignCreateView,
    CustomDesignUpdateView,
    GetInitialFromSessionMixin,
    PersonalizeDesignCreateView,
    PersonalizeDesignUpdateView,
    RedoApproveView,
    RedoCreateView,
    RedoUpdateView,
    SummaryAndApproveViewBase,
)
from customfit.graded_wizard.views import PersonalizeGradedDesignView

from .forms import (
    PersonalizeDesignFormGraded,
    PersonalizeDesignFormIndividual,
    TestPatternSpecFormIndividual,
    TestRedoFormIndividual,
    TweakTestIndividualGarmentParameters,
    TweakTestRedoIndividualGarmentParameters,
)
from .models import (
    GradedTestPatternSpec,
    TestGarmentParameters,
    TestGarmentParametersWithBody,
    TestGarmentSchematic,
    TestIndividualPattern,
    TestPatternPieces,
    TestPatternSpec,
    TestRedo,
)

MAKE_YOUR_OWN_TEST_GARMENT = "make_your_own_test_garm"


#################################################################################################################
#
# Personalize views
#
#################################################################################################################


class _PersonalizeTestDesignViewMixin(GetInitialFromSessionMixin):
    model = TestPatternSpec
    template_name = "test_garment/personalize_design.html"
    form_class = PersonalizeDesignFormIndividual


class TestPersonalizeCreateView(
    _PersonalizeTestDesignViewMixin, PersonalizeDesignCreateView
):
    pass


class TestPersonalizeUpdateView(
    _PersonalizeTestDesignViewMixin,
    PersonalizeDesignUpdateView,
):
    pass


#################################################################################################################
#
# Custom-design views
#
#################################################################################################################


class _CustomDesignMixin(object):
    model = TestPatternSpec
    form_class = TestPatternSpecFormIndividual
    template_name = "test_garment/patternspec_create_form.html"

    def get_myo_design(self):
        return MAKE_YOUR_OWN_TEST_GARMENT


class CustomTestDesignCreateView(_CustomDesignMixin, CustomDesignCreateView):
    pass


class CustomTestDesignUpdateView(_CustomDesignMixin, CustomDesignUpdateView):
    pass


#################################################################################################################
#
# Add-missing views
#
#################################################################################################################


class TestAddMissingMeasurementsMixin(object):

    def get_igp_class(self):
        return TestGarmentParametersWithBody

    def get_myo_design(self):
        return MAKE_YOUR_OWN_TEST_GARMENT


class TestAddMissingMeasurementsView(  # warning: order matters
    TestAddMissingMeasurementsMixin,
    AddMissingMeasurementsViewPatternspecMixin,
    AddMissingMeasurementsViewBase,
):
    pass


class TestAddMissingMeasurementsToRedoView(
    TestAddMissingMeasurementsMixin,
    AddMissingMeasurementsViewRedoMixin,
    AddMissingMeasurementsViewBase,
):

    pass


#################################################################################################################
#
# Tweak views
#
#################################################################################################################


class _TweakTestViewBase(object):

    model = TestGarmentParameters

    def get_tweak_fields(self):
        return ["test_field"]


class TweakTestView(_TweakTestViewBase, BaseTweakGarmentView):
    template_name = "test_garment/tweak_page.html"
    form_class = TweakTestIndividualGarmentParameters

    def get_myo_design(self):
        return MAKE_YOUR_OWN_TEST_GARMENT


class TweakRedoTestView(_TweakTestViewBase, BaseRedoTweakView):
    template_name = "test_garment/tweak_redo.html"
    form_class = TweakTestRedoIndividualGarmentParameters


#################################################################################################################
#
# Redo create/update
#
#################################################################################################################


class _TestRedoViewBase(object):
    template_name = "test_garment/redo_pattern_select_changes.html"
    model = TestRedo
    form_class = TestRedoFormIndividual


class TestRedoCreateView(_TestRedoViewBase, RedoCreateView):
    pass


class TestRedoUpdateView(_TestRedoViewBase, RedoUpdateView):
    pass


#################################################################################################################
#
# Redo tweak
#
#################################################################################################################


#################################################################################################################
#
# Redo summary & approve
#
#################################################################################################################


class TestApproveViewMixin(object):

    def _make_pattern(self, request, igp):
        """
        Handle the nitty-gritty of actually making the pattern from the IGP. Broken out into its
        own method for historical reasons.
        """
        user = request.user
        ips = TestGarmentSchematic.make_from_garment_parameters(igp)
        ips.clean()
        ips.save()
        ipp = TestPatternPieces.make_from_schematic(ips)
        ipp.clean()
        ipp.save()
        pattern = TestIndividualPattern.make_from_individual_pattern_pieces(user, ipp)
        pattern.clean()
        pattern.save()
        return pattern

    def get_context_data(self, **kwargs):
        context = super(TestApproveViewMixin, self).get_context_data(**kwargs)

        # schematic image template
        context["schematic_template_name"] = (
            "test_garment/schematic_measurements_web.html"
        )

        return context

    def get_myo_design(self):
        return MAKE_YOUR_OWN_TEST_GARMENT


class TestSummaryAndApproveView(TestApproveViewMixin, SummaryAndApproveViewBase):

    pass


class TestRedoApproveView(TestApproveViewMixin, RedoApproveView):

    def _make_new_pieces(self, request, igp):
        ips = TestGarmentSchematic.make_from_garment_parameters(igp)
        ips.clean()
        ips.save()
        ipp = TestPatternPieces.make_from_schematic(ips)
        ipp.clean()
        ipp.save()
        return ipp

    def _make_pattern(self, request, igp):
        """
        Handle the nitty-gritty of actually making the pattern from the IGP. Broken out into its
        own method for historical reasons.
        """
        user = request.user
        ipp = self._make_new_pieces(request, igp)
        pattern = TestIndividualPattern.make_from_individual_pattern_pieces(user, ipp)
        pattern.clean()
        pattern.save()
        return pattern

    def get_pattern(self):
        igp = self.get_object()
        pattern = self._make_pattern(self.request, igp)
        return pattern


#################################################################################################################
#
# Personalize GRADED views
#
#################################################################################################################


class PersonalizeGradedView(PersonalizeGradedDesignView):
    form_class = PersonalizeDesignFormGraded
    model = GradedTestPatternSpec
