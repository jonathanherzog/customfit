import logging

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms

from customfit.bodies.models import GradeSet
from customfit.design_wizard.constants import REDIRECT_APPROVE, REDO_AND_APPROVE
from customfit.design_wizard.forms import _BodyOptionsMixin, _IndividualQuerysetMixin

from .models import (
    GradedTestGarmentParameters,
    GradedTestPatternSpec,
    TestGarmentParameters,
    TestPatternSpec,
    TestRedo,
)

logger = logging.getLogger(__name__)


######################################################################################################
#
# Personalize forms
#
######################################################################################################


class PersonalizeDesignFormIndividual(
    forms.ModelForm, _BodyOptionsMixin, _IndividualQuerysetMixin
):

    class Meta:
        model = TestPatternSpec
        fields = ("name", "swatch", "stitch1")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")

        super(PersonalizeDesignFormIndividual, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.pattern_credits = self.design.pattern_credits
        self.instance.user = self.user
        self.instance.test_length = self.design.test_length
        return super(PersonalizeDesignFormIndividual, self).save(commit)


######################################################################################################
#
# Custom design forms
#
######################################################################################################


class TestPatternSpecFormIndividual(forms.ModelForm):

    class Meta:
        model = TestPatternSpec
        fields = [
            "name",
            "swatch",
            "stitch1",
            "test_length",
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(TestPatternSpecFormIndividual, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        self.instance.user = self.user
        return super(TestPatternSpecFormIndividual, self).save(commit)


######################################################################################################
#
# Tweak forms
#
######################################################################################################


class _TweakTestIndividualGarmentParametersBase(forms.ModelForm):

    class Meta:
        model = TestGarmentParameters
        fields = ["test_field"]

    def __init__(self, *args, **kwargs):

        self.user = kwargs.pop("user")
        super(_TweakTestIndividualGarmentParametersBase, self).__init__(*args, **kwargs)


class TweakTestIndividualGarmentParameters(_TweakTestIndividualGarmentParametersBase):

    def _submit_button_name(self):
        return REDIRECT_APPROVE

    def _submit_button_value(self):
        return "proceed with these changes"


class TweakTestRedoIndividualGarmentParameters(
    _TweakTestIndividualGarmentParametersBase
):
    def _submit_button_name(self):
        return REDO_AND_APPROVE

    def _submit_button_value(self):
        return "redo with these changes"


######################################################################################################
#
# Redo forms
#
######################################################################################################


class TestRedoFormIndividual(
    forms.ModelForm, _BodyOptionsMixin, _IndividualQuerysetMixin
):

    class Meta:
        model = TestRedo
        fields = ("swatch", "test_length")

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.pattern = kwargs.pop("pattern")

        create_swatch_url = kwargs.pop("create_swatch_url")

        super(TestRedoFormIndividual, self).__init__(*args, **kwargs)


######################################################################################################
#
# Personalize GRADED forms
#
######################################################################################################


class PersonalizeDesignFormGraded(forms.ModelForm):
    class Meta:
        model = GradedTestPatternSpec
        fields = (
            "name",
            "grade_set",
            "row_gauge",
            "stitch_gauge",
            "stitch1",
        )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.design = kwargs.pop("design")
        super(PersonalizeDesignFormGraded, self).__init__(*args, **kwargs)

        user_grade_sets = GradeSet.objects.filter(user=self.user).all()
        self.fields["grade_set"].query_set = user_grade_sets

        self.helper = FormHelper()
        self.helper.add_input(Submit("submit", "Submit"))

    def clean(self):
        # Check that the grade-set has all of the body-fields needed
        missing = GradedTestGarmentParameters.missing_body_fields(self.instance)
        if missing:
            field_list = ", ".join(missing)
            msg = "Grade-set is missing the following fields: %s" % field_list
            raise forms.ValidationError(msg)
        else:
            return super(PersonalizeDesignFormGraded, self).clean()

    def save(self, commit=True):
        self.instance.user = self.user
        self.instance.test_length = self.design.test_length
        return super(PersonalizeDesignFormGraded, self).save(commit)
