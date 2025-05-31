from factory import Faker, RelatedFactory, SelfAttribute, SubFactory
from factory.django import DjangoModelFactory

from customfit.pieces.factories import GradedPatternPiecesFactory, PatternPiecesFactory
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from .models import GradedPattern, IndividualPattern, Redo, _BasePattern


class BasePatternFactory(DjangoModelFactory):
    class Meta:
        model = _BasePattern
        abstract = True

    id = Faker("random_int", min=1, max=100000000)
    name = SelfAttribute("pieces.schematic.name")
    notes = ""
    archived = False
    featured_pic = None


#
# IndividualPattern factories
#


class IndividualPatternFactory(BasePatternFactory):
    class Meta:
        model = IndividualPattern

    user = SubFactory(UserFactory)
    pieces = SubFactory(
        PatternPiecesFactory,
        schematic__individual_garment_parameters__user=SelfAttribute("....user"),
    )
    original_pieces = None


class ApprovedPatternFactory(IndividualPatternFactory):

    transaction = RelatedFactory(
        "customfit.design_wizard.factories.TransactionFactory", "pattern"
    )

    @classmethod
    def for_user(cls, user):
        return cls(user=user)


class ArchivedPatternFactory(ApprovedPatternFactory):

    archived = True


#
# Graded Patterns
#


class GradedPatternFactory(BasePatternFactory):
    class Meta:
        model = GradedPattern
        abstract = True

    pieces = SubFactory(
        GradedPatternPiecesFactory,
        schematic__graded_garment_parameters__user=SelfAttribute("....user"),
    )


#
# Redo
#


class RedoFactory(DjangoModelFactory):
    class Meta:
        model = Redo

    pattern = SubFactory(ApprovedPatternFactory)
    swatch = SubFactory(SwatchFactory, user=SelfAttribute("..pattern.user"))

    @classmethod
    def from_original_pspec(cls, pspec, **kwargs):
        return cls(
            pattern__user=pspec.user,
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
            **kwargs
        )
