from django.utils import timezone
from factory import LazyFunction, SubFactory
from factory.django import DjangoModelFactory

from customfit.garment_parameters.factories import (
    GradedGarmentParametersFactory,
    IndividualGarmentParametersFactory,
)

from .models import (
    ConstructionSchematic,
    GradedConstructionSchematic,
    GradedPieceSchematic,
    PieceSchematic,
    _BaseConstructionSchematic,
    _BasePieceSchematic,
)


class _BasePieceSchematicFactory(DjangoModelFactory):
    class Meta:
        model = _BasePieceSchematic
        abstract = True


class PieceSchematicFactory(_BasePieceSchematicFactory):
    class Meta:
        model = PieceSchematic
        abstract = True


class _BaseConstructionSchematicFactory(DjangoModelFactory):
    class Meta:
        model = _BaseConstructionSchematic
        abstract = True

    creation_date = LazyFunction(timezone.now)


class ConstructionSchematicFactory(_BaseConstructionSchematicFactory):
    class Meta:
        model = ConstructionSchematic

    customized = False
    individual_garment_parameters = SubFactory(IndividualGarmentParametersFactory)


class GradedConstructionSchematicFactory(_BaseConstructionSchematicFactory):
    class Meta:
        model = GradedConstructionSchematic
        abstract = True

    graded_garment_parameters = SubFactory(GradedGarmentParametersFactory)


class GradedPieceSchematicFactory(_BasePieceSchematicFactory):
    class Meta:
        model = GradedPieceSchematic
        abstract = True

    construction_schematic = SubFactory(GradedConstructionSchematicFactory)
