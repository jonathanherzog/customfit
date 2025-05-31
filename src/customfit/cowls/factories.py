import copy

import factory

from customfit.designs.factories import DesignFactory
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

from . import helpers as CDC
from .models import (
    AdditionalStitch,
    CowlDesign,
    CowlGarmentSchematic,
    CowlGradedGarmentParametersGrade,
    CowlIndividualGarmentParameters,
    CowlPattern,
    CowlPatternPieces,
    CowlPatternSpec,
    CowlPiece,
    CowlPieceSchematic,
    CowlRedo,
    FinalEdgingTemplate,
    FirstEdgingTemplate,
    GradedCowlGarmentParameters,
    GradedCowlGarmentSchematic,
    GradedCowlPattern,
    GradedCowlPatternPieces,
    GradedCowlPatternSpec,
    GradedCowlPiece,
    GradedCowlPieceSchematic,
    MainSectionTemplate,
)


class CowlIndividualBaseFactory(factory.django.DjangoModelFactory):
    circumference = CDC.COWL_CIRC_MEDIUM
    height = CDC.COWL_HEIGHT_AVERAGE


class CowlDesignBaseFactory(factory.django.DjangoModelFactory):
    edging_stitch_height = 1
    cast_on_x_mod = 0
    cast_on_mod_y = 1
    edging_stitch = factory.SubFactory(StitchFactory, name="1x1 Ribbing")
    main_stitch = factory.SubFactory(StitchFactory, name="Stockinette")
    panel_stitch = None
    cable_stitch = None
    extra_cable_stitches = 0
    extra_cable_stitches_are_main_pattern_only = False
    horizontal_panel_rounds = 0


class FirstEdgingTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = FirstEdgingTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
    {% load pattern_conventions %}
    <p>[default FirstEdgingTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


class MainSectionTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = MainSectionTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
    {% load pattern_conventions %}
    <p>[default MainSectionTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


class FinalEdgingTemplateFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = FinalEdgingTemplate
        strategy = factory.CREATE_STRATEGY

    content = """
        {% load pattern_conventions %}
    <p>[default FinalEdgingTemplateFactory template]<p>
    <p>{{ piece.cast_on_stitches | count_fmt }}<p>
    """


class CowlDesignFactory(
    DesignFactory, CowlIndividualBaseFactory, CowlDesignBaseFactory
):
    class Meta:
        model = CowlDesign

    first_edging_template = None
    final_edging_template = None
    main_section_template = None


class TemplatedDesignFactory(CowlDesignFactory):
    first_edging_template = factory.SubFactory(FirstEdgingTemplateFactory)
    main_section_template = factory.SubFactory(MainSectionTemplateFactory)
    final_edging_template = factory.SubFactory(FinalEdgingTemplateFactory)


class AdditionalStitchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AdditionalStitch

    design = factory.SubFactory(CowlDesignFactory)
    stitch = factory.SubFactory(StitchFactory)


class CowlPatternSpecFactory(
    PatternSpecFactory, CowlDesignBaseFactory, CowlIndividualBaseFactory
):
    class Meta:
        model = CowlPatternSpec


class GradedCowlPatternSpecFactory(GradedPatternSpecFactory, CowlDesignBaseFactory):
    class Meta:
        model = GradedCowlPatternSpec

    row_gauge = 17
    stitch_gauge = 20


################################################################################################################
#
# GarmentParameters
#
################################################################################################################


class CowlGarmentDimensionsFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    height = 12
    circumference = 42


class CowlGarmentParametersTopLevelFieldsFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    edging_height = 1


class CowlIndividualGarmentParametersFactory(
    IndividualGarmentParametersFactory,
    CowlGarmentDimensionsFactory,
    CowlGarmentParametersTopLevelFieldsFactory,
):
    class Meta:
        model = CowlIndividualGarmentParameters

    pattern_spec = factory.SubFactory(
        CowlPatternSpecFactory, user=factory.SelfAttribute("..user")
    )


class CowlGradedGarmentParametersGradeFactory(
    GradedGarmentParametersGradeFactory, CowlGarmentDimensionsFactory
):
    class Meta:
        model = CowlGradedGarmentParametersGrade


class GradedCowlGarmentParametersFactory(
    GradedGarmentParametersFactory, CowlGarmentParametersTopLevelFieldsFactory
):
    class Meta:
        model = GradedCowlGarmentParameters

    pattern_spec = factory.SubFactory(
        GradedCowlPatternSpecFactory, user=factory.SelfAttribute("..user")
    )

    grade1 = factory.RelatedFactory(
        CowlGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        height=10,
        circumference=20,
    )
    grade2 = factory.RelatedFactory(
        CowlGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        height=12,
        circumference=26,
    )
    grade3 = factory.RelatedFactory(
        CowlGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        height=16,
        circumference=42,
    )
    grade4 = factory.RelatedFactory(
        CowlGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        height=20,
        circumference=60,
    )


################################################################################################################
#
# Schematics
#
################################################################################################################


class _BaseCowlPieceSchematicFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    height = 12
    circumference = 36
    edging_height = 1


class CowlPieceSchematicFactory(PieceSchematicFactory, _BaseCowlPieceSchematicFactory):
    class Meta:
        model = CowlPieceSchematic


class GradedCowlPieceSchematicFactory(
    GradedPieceSchematicFactory, _BaseCowlPieceSchematicFactory
):
    class Meta:
        model = GradedCowlPieceSchematic

    construction_schematic = factory.SubFactory(
        "customfit.cowls.factories.GradedCowlGarmentSchematicFactory"
    )


class CowlGarmentSchematicFactory(ConstructionSchematicFactory):
    class Meta:
        model = CowlGarmentSchematic

    cowl_piece = factory.SubFactory(
        CowlPieceSchematicFactory,
    )
    individual_garment_parameters = factory.SubFactory(
        CowlIndividualGarmentParametersFactory
    )


class GradedCowlGarmentSchematicFactory(GradedConstructionSchematicFactory):
    class Meta:
        model = GradedCowlGarmentSchematic

    graded_garment_parameters = factory.SubFactory(GradedCowlGarmentParametersFactory)

    grade1 = factory.RelatedFactory(
        GradedCowlPieceSchematicFactory,
        "construction_schematic",
        height=10,
        circumference=20,
        edging_height=1,
    )
    grade2 = factory.RelatedFactory(
        GradedCowlPieceSchematicFactory,
        "construction_schematic",
        height=12,
        circumference=26,
        edging_height=1,
    )
    grade3 = factory.RelatedFactory(
        GradedCowlPieceSchematicFactory,
        "construction_schematic",
        height=16,
        circumference=42,
        edging_height=1,
    )
    grade4 = factory.RelatedFactory(
        GradedCowlPieceSchematicFactory,
        "construction_schematic",
        height=20,
        circumference=60,
        edging_height=1,
    )


################################################################################################################
#
# Pieces
#
################################################################################################################


class _BaseCowlPieceFactory(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True

    cast_on_stitches = 36 * 7
    main_pattern_stitches = 36 * 7
    edging_height_in_rows = 5
    total_rows = 60


class CowlPieceFactory(PatternPieceFactory, _BaseCowlPieceFactory):
    class Meta:
        model = CowlPiece

    schematic = factory.SubFactory(CowlGarmentSchematicFactory)


class CowlPatternPiecesFactory(PatternPiecesFactory):
    class Meta:
        model = CowlPatternPieces

    cowl = factory.SubFactory(
        CowlPieceFactory, schematic=factory.SelfAttribute("..schematic")
    )
    schematic = factory.SubFactory(CowlGarmentSchematicFactory)


class GradedCowlPieceFactory(GradedPatternPieceFactory, _BaseCowlPieceFactory):
    class Meta:
        model = GradedCowlPiece

    sort_key = 60

    graded_pattern_pieces = factory.SubFactory(
        "customfit.cowls.factories.GradedCowlPatternPiecesFactory"
    )


class GradedCowlPatternPiecesFactory(GradedPatternPiecesFactory):
    class Meta:
        model = GradedCowlPatternPieces

    schematic = factory.SubFactory(GradedCowlGarmentSchematicFactory)

    piece1 = factory.RelatedFactory(
        GradedCowlPieceFactory,
        "graded_pattern_pieces",
        cast_on_stitches=100,
        main_pattern_stitches=100,
        edging_height_in_rows=5,
        total_rows=43,
        sort_key=43,
    )
    piece2 = factory.RelatedFactory(
        GradedCowlPieceFactory,
        "graded_pattern_pieces",
        cast_on_stitches=130,
        main_pattern_stitches=130,
        edging_height_in_rows=5,
        total_rows=51,
        sort_key=51,
    )
    piece3 = factory.RelatedFactory(
        GradedCowlPieceFactory,
        "graded_pattern_pieces",
        cast_on_stitches=210,
        main_pattern_stitches=210,
        edging_height_in_rows=5,
        total_rows=68,
        sort_key=68,
    )
    piece4 = factory.RelatedFactory(
        GradedCowlPieceFactory,
        "graded_pattern_pieces",
        cast_on_stitches=300,
        main_pattern_stitches=300,
        edging_height_in_rows=5,
        total_rows=85,
        sort_key=85,
    )


################################################################################################################
#
# patterns
#
################################################################################################################


class CowlPatternFactory(IndividualPatternFactory):
    class Meta:
        model = CowlPattern

    pieces = factory.SubFactory(
        CowlPatternPiecesFactory,
        schematic__individual_garment_parameters__user=factory.SelfAttribute(
            "....user"
        ),
    )

    @classmethod
    def from_pspec(cls, pspec):
        return cls(
            pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
            user=pspec.user,
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


class GradedCowlPatternFactory(GradedPatternFactory):
    class Meta:
        model = GradedCowlPattern

    pieces = factory.SubFactory(GradedCowlPatternPiecesFactory)

    # @classmethod
    # def from_pspec(cls, pspec):
    #     return cls(pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
    #                user = pspec.user)
    # @classmethod
    # def from_us(cls, user=None, swatch=None):
    #     kwargs = {}
    #
    #     if user:
    #         kwargs['user'] = user
    #
    #     if swatch:
    #         kwargs['pieces__schematic__individual_garment_parameters__pattern_spec__swatch'] = swatch
    #
    #     return cls(**kwargs)


class ApprovedCowlPatternFactory(CowlPatternFactory, ApprovedPatternFactory):
    pass


class CowlRedoFactory(CowlIndividualBaseFactory, RedoFactory):
    class Meta:
        model = CowlRedo

    pattern = factory.SubFactory(ApprovedCowlPatternFactory)
    circumference = CDC.COWL_CIRC_LARGE
    height = CDC.COWL_HEIGHT_TALL


class RedoneCowlPatternFactory(ApprovedCowlPatternFactory):

    @factory.post_generation
    def redo(self, create, extracted, **kwargs):
        ## Create a Redo object, then redo the pattern
        assert "pattern" not in kwargs
        kwargs["pattern"] = self
        new_redo_object = CowlRedoFactory(**kwargs)
        new_igp = CowlIndividualGarmentParametersFactory(
            pattern_spec=None, redo=new_redo_object, user=new_redo_object.pattern.user
        )
        new_pieces = CowlPatternPiecesFactory(
            schematic__individual_garment_parameters=new_igp
        )
        self.update_with_new_pieces(new_pieces)
        self.save()
        return self
