from factory import SelfAttribute, Sequence, SubFactory
from factory.django import DjangoModelFactory

from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from .models import GradedPatternSpec, PatternSpec


class BasePatternSpecFactory(DjangoModelFactory):
    name = Sequence(lambda n: "factory-made patternspec %s" % n)
    design_origin = None
    user = SubFactory(UserFactory)


class PatternSpecFactory(BasePatternSpecFactory):
    class Meta:
        model = PatternSpec

    swatch = SubFactory(SwatchFactory, user=SelfAttribute("..user"))


class GradedPatternSpecFactory(BasePatternSpecFactory):
    class Meta:
        model = GradedPatternSpec
