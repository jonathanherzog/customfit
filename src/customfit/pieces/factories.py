from factory import SubFactory
from factory.django import DjangoModelFactory

from customfit.schematics.factories import (
    ConstructionSchematicFactory,
    GradedConstructionSchematicFactory,
)

from .models import (
    BasePatternPiece,
    GradedPatternPiece,
    GradedPatternPieces,
    PatternPiece,
    PatternPieces,
    _BasePatternPieces,
)


class _BasePatternPiecesFactory(DjangoModelFactory):
    class Meta:
        model = _BasePatternPieces
        abstract = True


class PatternPiecesFactory(_BasePatternPiecesFactory):
    class Meta:
        model = PatternPieces

    schematic = SubFactory(ConstructionSchematicFactory)


class GradedPatternPiecesFactory(_BasePatternPiecesFactory):
    class Meta:
        model = GradedPatternPieces
        abstract = True

    schematic = SubFactory(GradedConstructionSchematicFactory)


class BasePatternPieceFactory(DjangoModelFactory):
    class Meta:
        model = BasePatternPiece
        abstract = True


class PatternPieceFactory(BasePatternPieceFactory):
    class Meta:
        model = PatternPiece


class GradedPatternPieceFactory(BasePatternPieceFactory):
    class Meta:
        model = GradedPatternPiece
        abstract = True

    graded_pattern_pieces = SubFactory(GradedPatternPiecesFactory)
