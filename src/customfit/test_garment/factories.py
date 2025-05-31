from factory import RelatedFactory, SelfAttribute, SubFactory, post_generation
from factory.django import DjangoModelFactory

from customfit.bodies.factories import BodyFactory, GradeSetFactory
from customfit.designs.factories import (
    DesignFactory,
    _AdditionalDesignElementFactoryBase,
)
from customfit.garment_parameters.factories import (
    GradedGarmentParametersFactory,
    GradedGarmentParametersGradeFactory,
    IndividualGarmentParametersFactory,
)
from customfit.pattern_spec.factories import (
    GradedPatternSpecFactory,
    PatternSpecFactory,
)
from customfit.patterns.factories import (
    ApprovedPatternFactory,
    ArchivedPatternFactory,
    GradedPatternFactory,
    IndividualPatternFactory,
    RedoFactory,
)
from customfit.pieces.factories import (
    GradedPatternPieceFactory,
    GradedPatternPiecesFactory,
    PatternPieceFactory,
    PatternPiecesFactory,
)
from customfit.schematics.factories import (
    ConstructionSchematicFactory,
    GradedConstructionSchematicFactory,
    GradedPieceSchematicFactory,
    PieceSchematicFactory,
)
from customfit.stitches.factories import StitchFactory

from .models import (
    GradedTestGarmentParameters,
    GradedTestGarmentParametersGrade,
    GradedTestGarmentSchematic,
    GradedTestPattern,
    GradedTestPatternPiece,
    GradedTestPatternPieces,
    GradedTestPatternSpec,
    GradedTestPieceSchematic,
    TestAdditionalDesignElement,
    TestDesign,
    TestDesignWithBody,
    TestGarmentParameters,
    TestGarmentParametersWithBody,
    TestGarmentSchematic,
    TestIndividualPattern,
    TestPatternPiece,
    TestPatternPieces,
    TestPatternSpec,
    TestPatternSpecWithBody,
    TestPieceSchematic,
    TestRedo,
    TestRedoWithBody,
)

####################################################################################################################
#
# Designs
#
####################################################################################################################


class TestDesignFactory(DesignFactory):
    class Meta:
        model = TestDesign

    stitch1 = SubFactory(StitchFactory, name="1x1 Ribbing")
    test_length = 1.0


class TestDesignWithBodyFactory(TestDesignFactory):
    class Meta:
        model = TestDesignWithBody


####################################################################################################################
#
# PatternSpec
#
####################################################################################################################


class _BaseTestPatternSpecFactory(DjangoModelFactory):
    stitch1 = SubFactory(StitchFactory, name="1x1 Ribbing")
    test_length = 1.0

    class Meta:
        abstract = True


class TestPatternSpecFactory(PatternSpecFactory, _BaseTestPatternSpecFactory):
    class Meta:
        model = TestPatternSpec


class TestPatternSpecWithBodyFactory(TestPatternSpecFactory):
    class Meta:
        model = TestPatternSpecWithBody

    body = SubFactory(BodyFactory, user=SelfAttribute("..user"))


class GradedTestPatternSpecFactory(
    GradedPatternSpecFactory, _BaseTestPatternSpecFactory
):
    class Meta:
        model = GradedTestPatternSpec

    row_gauge = 16  # rows over 4 inches
    stitch_gauge = 12.5  # stitches over 4 inches
    grade_set = SubFactory(GradeSetFactory, user=SelfAttribute("..user"))


####################################################################################################################
#
# Garment Parameters
#
####################################################################################################################


class _TestBaseGarmentParamatersFactory(DjangoModelFactory):

    test_field = 2.0

    class Meta:
        abstract = True


class _TestBaseGarmentParametersBodyLevelFieldsFactory(DjangoModelFactory):

    test_field_from_body = 15

    class Meta:
        abstract = True


class TestIndividualGarmentParametersFactory(
    IndividualGarmentParametersFactory, _TestBaseGarmentParamatersFactory
):
    class Meta:
        model = TestGarmentParameters

    pattern_spec = SubFactory(TestPatternSpecFactory, user=SelfAttribute("..user"))


class TestIndividualGarmentParametersWithBodyFactory(
    TestIndividualGarmentParametersFactory,
    _TestBaseGarmentParametersBodyLevelFieldsFactory,
):
    class Meta:
        model = TestGarmentParametersWithBody

    pattern_spec = SubFactory(
        TestPatternSpecWithBodyFactory, user=SelfAttribute("..user")
    )


class GradedTestGarmentParametersGradeFactory(
    _TestBaseGarmentParametersBodyLevelFieldsFactory
):
    class Meta:
        model = GradedTestGarmentParametersGrade

    graded_garment_parameters = SubFactory(
        "customfit.test_garment.factories.GradedTestGarmentParametersFactory"
    )


class GradedTestGarmentParametersFactory(
    GradedGarmentParametersFactory, _TestBaseGarmentParamatersFactory
):
    class Meta:
        model = GradedTestGarmentParameters

    pattern_spec = SubFactory(
        GradedTestPatternSpecFactory, user=SelfAttribute("..user")
    )

    # Note the random order-- used to test sorting
    piece2 = RelatedFactory(
        GradedTestGarmentParametersGradeFactory,
        "graded_garment_parameters",
        test_field_from_body=11,
    )
    piece4 = RelatedFactory(
        GradedTestGarmentParametersGradeFactory,
        "graded_garment_parameters",
        test_field_from_body=13,
    )
    piece1 = RelatedFactory(
        GradedTestGarmentParametersGradeFactory,
        "graded_garment_parameters",
        test_field_from_body=10,
    )
    piece3 = RelatedFactory(
        GradedTestGarmentParametersGradeFactory,
        "graded_garment_parameters",
        test_field_from_body=12,
    )
    piece5 = RelatedFactory(
        GradedTestGarmentParametersGradeFactory,
        "graded_garment_parameters",
        test_field_from_body=14,
    )


####################################################################################################################
#
# Schematics
#
####################################################################################################################


class _BaseTestPieceSchematicFactory(DjangoModelFactory):

    test_field = 2.0

    class Meta:
        abstract = True


class TestPieceSchematicFactory(PieceSchematicFactory, _BaseTestPieceSchematicFactory):
    class Meta:
        model = TestPieceSchematic


class GradedTestPieceSchematicFactory(
    GradedPieceSchematicFactory, _BaseTestPieceSchematicFactory
):
    class Meta:
        model = GradedTestPieceSchematic

    test_field_from_body = 15
    construction_schematic = SubFactory(
        "customfit.test_garment.factories.GradedTestGarmentSchematicFactory"
    )


class TestGarmentSchematicFactory(ConstructionSchematicFactory):
    class Meta:
        model = TestGarmentSchematic

    test_piece = SubFactory(TestPieceSchematicFactory)
    individual_garment_parameters = SubFactory(TestIndividualGarmentParametersFactory)


class TestGarmentSchematicWithBodyFactory(TestGarmentSchematicFactory):
    individual_garment_parameters = SubFactory(
        TestIndividualGarmentParametersWithBodyFactory
    )


class GradedTestGarmentSchematicFactory(GradedConstructionSchematicFactory):
    class Meta:
        model = GradedTestGarmentSchematic

    graded_garment_parameters = SubFactory(GradedTestGarmentParametersFactory)

    # Note the random order-- used to test sorting
    piece5 = RelatedFactory(
        GradedTestPieceSchematicFactory,
        "construction_schematic",
        test_field_from_body=14,
    )
    piece1 = RelatedFactory(
        GradedTestPieceSchematicFactory,
        "construction_schematic",
        test_field_from_body=10,
    )
    piece4 = RelatedFactory(
        GradedTestPieceSchematicFactory,
        "construction_schematic",
        test_field_from_body=13,
    )
    piece3 = RelatedFactory(
        GradedTestPieceSchematicFactory,
        "construction_schematic",
        test_field_from_body=12,
    )
    piece2 = RelatedFactory(
        GradedTestPieceSchematicFactory,
        "construction_schematic",
        test_field_from_body=11,
    )


####################################################################################################################
#
# Pieces
#
####################################################################################################################


class _BaseTestPatternPieceFactory(DjangoModelFactory):
    test_field = 2.0

    class Meta:
        abstract = True


class TestPatternPieceFactory(PatternPieceFactory, _BaseTestPatternPieceFactory):
    class Meta:
        model = TestPatternPiece


class _BaseTestPatternPiecesFactory(DjangoModelFactory):

    class Meta:
        abstract = True


class TestPatternPiecesFactory(PatternPiecesFactory, _BaseTestPatternPiecesFactory):
    class Meta:
        model = TestPatternPieces

    test_piece = SubFactory(TestPatternPieceFactory)
    schematic = SubFactory(TestGarmentSchematicFactory)


class TestPatternPiecesWithBodyFactory(TestPatternPiecesFactory):
    schematic = SubFactory(TestGarmentSchematicWithBodyFactory)


class GradedTestPatternPieceFactory(
    GradedPatternPieceFactory, _BaseTestPatternPieceFactory
):
    class Meta:
        model = GradedTestPatternPiece

    graded_pattern_pieces = SubFactory(
        "customfit.test_garment.factories.GradedTestPatternPiecesFactory"
    )
    sort_key = SelfAttribute("test_field")


class GradedTestPatternPiecesFactory(
    GradedPatternPiecesFactory, _BaseTestPatternPiecesFactory
):
    class Meta:
        model = GradedTestPatternPieces

    schematic = SubFactory(GradedTestGarmentSchematicFactory)

    # Note the random order-- used to test sorting
    piece5 = RelatedFactory(
        GradedTestPatternPieceFactory, "graded_pattern_pieces", test_field=14
    )
    piece2 = RelatedFactory(
        GradedTestPatternPieceFactory, "graded_pattern_pieces", test_field=11
    )
    piece3 = RelatedFactory(
        GradedTestPatternPieceFactory, "graded_pattern_pieces", test_field=12
    )
    piece1 = RelatedFactory(
        GradedTestPatternPieceFactory, "graded_pattern_pieces", test_field=10
    )
    piece4 = RelatedFactory(
        GradedTestPatternPieceFactory, "graded_pattern_pieces", test_field=13
    )


####################################################################################################################
#
# Patterns
#
####################################################################################################################


class TestAdditionalElementFactory(_AdditionalDesignElementFactoryBase):
    class Meta:
        model = TestAdditionalDesignElement

    # Shadow the declaration in _AdditionalDesignElementFactoryBase to enforce the design is a sweater
    design = SubFactory(DesignFactory)
    start_location_value = 3.0
    start_location_type = TestAdditionalDesignElement.START_AFTER_CASTON


class _BaseTestPatternFactory(DjangoModelFactory):

    class Meta:
        abstract = True


class TestIndividualPatternFactory(IndividualPatternFactory):
    class Meta:
        model = TestIndividualPattern

    pieces = SubFactory(
        TestPatternPiecesFactory,
        schematic__individual_garment_parameters__user=SelfAttribute("....user"),
    )

    @classmethod
    def for_user(cls, user):
        return cls(user=user)

    @classmethod
    def from_pspec(cls, pspec):
        return cls(
            user=pspec.user,
            pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
        )

    @classmethod
    def from_us(cls, user=None, swatch=None):
        kwargs = {}

        if user:
            kwargs["user"] = user

        if swatch:
            kwargs[
                "pieces__schematic__individual_garment_parameters__pattern_spec__swatch"
            ] = swatch

        return cls(**kwargs)


class TestApprovedIndividualPatternFactory(
    TestIndividualPatternFactory, ApprovedPatternFactory
):
    pass


class TestArchivedIndividualPatternFactory(
    TestApprovedIndividualPatternFactory,
    ArchivedPatternFactory,
    _BaseTestPatternFactory,
):

    archived = True


class TestIndividualPatternWithBodyFactory(TestIndividualPatternFactory):
    pieces = SubFactory(
        TestPatternPiecesWithBodyFactory,
        schematic__individual_garment_parameters__user=SelfAttribute("....user"),
    )

    @classmethod
    def from_ubs(cls, user=None, body=None, swatch=None):
        kwargs = {}

        if user:
            kwargs["user"] = user

        if body:
            kwargs[
                "pieces__schematic__individual_garment_parameters__pattern_spec__body"
            ] = body

        if swatch:
            kwargs[
                "pieces__schematic__individual_garment_parameters__pattern_spec__swatch"
            ] = swatch

        return cls(**kwargs)


class TestApprovedIndividualPatternWithBodyFactory(
    TestIndividualPatternWithBodyFactory, ApprovedPatternFactory
):
    pass


class TestArchivedIndividualPatternWithBodyFactory(
    TestIndividualPatternWithBodyFactory, ArchivedPatternFactory
):
    pass


class GradedTestPatternFactory(GradedPatternFactory, _BaseTestPatternFactory):
    class Meta:
        model = GradedTestPattern

    pieces = SubFactory(GradedTestPatternPiecesFactory)


####################################################################################################################
#
# Redos
#
####################################################################################################################


class TestRedoFactory(RedoFactory):
    class Meta:
        model = TestRedo

    test_length = 1.0
    pattern = SubFactory(TestApprovedIndividualPatternFactory)


class TestRedoWithBodyFactory(TestRedoFactory):
    class Meta:
        model = TestRedoWithBody

    pattern = SubFactory(TestApprovedIndividualPatternWithBodyFactory)
    body = SubFactory(BodyFactory, user=SelfAttribute("..pattern.user"))


class TestRedonePatternFactory(TestApprovedIndividualPatternFactory):

    @post_generation
    def redo(self, create, extracted, **kwargs):
        ## Create a Redo object, then redo the pattern
        assert "pattern" not in kwargs
        kwargs["pattern"] = self
        new_redo_object = TestRedoFactory(**kwargs)
        new_igp = TestIndividualGarmentParametersFactory(
            pattern_spec=None, redo=new_redo_object, user=new_redo_object.pattern.user
        )
        new_pieces = TestPatternPiecesFactory(
            schematic__individual_garment_parameters=new_igp
        )
        self.update_with_new_pieces(new_pieces)
        self.save()
        return self


def pattern_from_pspec_and_redo_kwargs(pspec, **kwargs):
    redo = TestRedoFactory.from_original_pspec(pspec, **kwargs)
    pattern = redo.pattern
    new_igp = TestIndividualGarmentParametersFactory(pattern_spec=None, redo=redo)
    new_pieces = TestPatternPiecesFactory(
        schematic__individual_garment_parameters=new_igp
    )
    pattern.update_with_new_pieces(new_pieces)
    pattern.save()
    return pattern


def pattern_with_body_from_pspec_and_redo_kwargs(pspec, **kwargs):
    redo = TestRedoWithBodyFactory.from_original_pspec(pspec, **kwargs)
    pattern = redo.pattern
    new_igp = TestIndividualGarmentParametersFactory(pattern_spec=None, redo=redo)
    new_pieces = TestPatternPiecesFactory(
        schematic__individual_garment_parameters=new_igp
    )
    pattern.update_with_new_pieces(new_pieces)
    pattern.save()
    return pattern
