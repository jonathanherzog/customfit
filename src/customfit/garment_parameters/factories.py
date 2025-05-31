from factory import CREATE_STRATEGY, SelfAttribute, SubFactory
from factory.django import DjangoModelFactory

from customfit.pattern_spec.factories import (
    GradedPatternSpecFactory,
    PatternSpecFactory,
)
from customfit.userauth.factories import UserFactory

from .models import (
    GradedGarmentParameters,
    GradedGarmentParametersGrade,
    IndividualGarmentParameters,
)


class BaseGarmentParametersFactory(DjangoModelFactory):
    user = SubFactory(UserFactory)


class IndividualGarmentParametersFactory(BaseGarmentParametersFactory):
    class Meta:
        model = IndividualGarmentParameters
        strategy = CREATE_STRATEGY

    pattern_spec = SubFactory(PatternSpecFactory, user=SelfAttribute("..user"))
    redo = None


class GradedGarmentParametersFactory(BaseGarmentParametersFactory):
    class Meta:
        model = GradedGarmentParameters
        strategy = CREATE_STRATEGY

    pattern_spec = SubFactory(GradedPatternSpecFactory, user=SelfAttribute("..user"))


class GradedGarmentParametersGradeFactory(DjangoModelFactory):
    class Meta:
        model = GradedGarmentParametersGrade

    graded_garment_parameters = SubFactory(GradedGarmentParametersFactory)
