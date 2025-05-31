from factory import LazyAttribute, RelatedFactory, SubFactory
from factory.django import DjangoModelFactory

from customfit.schematics.factories import (
    ConstructionSchematicFactory,
    GradedConstructionSchematicFactory,
    GradedPieceSchematicFactory,
    PieceSchematicFactory,
)

from ..helpers import sweater_design_choices as SDC
from ..models.schematics import (
    BaseBackPieceSchematic,
    BaseBodyPieceSchematic,
    BaseFrontPieceSchematic,
    BaseSleeveSchematic,
    BaseSweaterFrontSchematic,
    GradedSleeveSchematic,
    GradedSweaterBackSchematic,
    GradedSweaterFrontSchematic,
    GradedSweaterSchematic,
    GradedVestBackSchematic,
    SweaterBackSchematic,
    SweaterSchematic,
)
from .garment_parameters import (
    SweaterGradedGarmentParametersFactory,
    SweaterIndividualGarmentParametersFactory,
)


class _GradedSweaterSchematicPieceMixin(DjangoModelFactory):
    class Meta:
        abstract = True

    construction_schematic = SubFactory(
        "customfit.sweaters.factories.GradedSweaterSchematicFactory"
    )
    gp_grade = LazyAttribute(
        lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
            "SweaterGradedGarmentParametersGrade___grade__bust_circ"
        )[
            0
        ]
    )


class BaseBodyPieceSchematicFactory(DjangoModelFactory):
    class Meta:
        model = BaseBodyPieceSchematic
        abstract = True

    hip_width = 19.5
    shoulder_height = 24
    armpit_height = 16
    waist_height = 7
    bust_width = 19.625
    waist_width = 17.5
    neck_height = 23


class BaseBackPieceSchematicFactory(BaseBodyPieceSchematicFactory):
    class Meta:
        model = BaseBackPieceSchematic
        abstract = True

    cross_back_width = 14
    neck_opening_width = 7


class BaseSweaterBackSchematicFactory(BaseBackPieceSchematicFactory):
    class Meta:
        model = BaseBackPieceSchematic
        abstract = True


class SweaterBackSchematicFactory(
    BaseSweaterBackSchematicFactory, PieceSchematicFactory
):
    class Meta:
        model = SweaterBackSchematic

    sweaterschematic = RelatedFactory(
        "customfit.sweaters.factories.SweaterSchematicFactory", "sweater_back"
    )


class GradedSweaterBackSchematicFactory(
    BaseSweaterBackSchematicFactory,
    _GradedSweaterSchematicPieceMixin,
    GradedPieceSchematicFactory,
):
    class Meta:
        model = GradedSweaterBackSchematic


class GradedVestBackSchematicFactory(
    BaseSweaterBackSchematicFactory,
    _GradedSweaterSchematicPieceMixin,
    GradedPieceSchematicFactory,
):
    class Meta:
        model = GradedVestBackSchematic


class BaseFrontPieceSchematic(BaseBodyPieceSchematicFactory):
    class Meta:
        model = BaseFrontPieceSchematic
        abstract = True

    neckline_style = SDC.NECK_VEE
    below_armpit_straight = 1.5


class BaseSweaterFrontSchematicFactory(BaseFrontPieceSchematic):
    class Meta:
        model = BaseSweaterFrontSchematic
        abstract = True


class GradedSweaterFrontSchematicFactory(
    BaseSweaterFrontSchematicFactory,
    _GradedSweaterSchematicPieceMixin,
    GradedPieceSchematicFactory,
):
    class Meta:
        model = GradedSweaterFrontSchematic


class BaseSleeveSchematicFactory(DjangoModelFactory):
    class Meta:
        model = BaseSleeveSchematic
        abstract = True

    sleeve_to_armcap_start_height = 17.5
    bicep_width = 13.25
    sleeve_cast_on_width = 9


class GradedSleeveSchematicFactory(
    BaseSleeveSchematicFactory, _GradedSweaterSchematicPieceMixin, DjangoModelFactory
):
    class Meta:
        model = GradedSleeveSchematic


class SweaterSchematicFactory(ConstructionSchematicFactory):
    class Meta:
        model = SweaterSchematic

    individual_garment_parameters = SubFactory(
        SweaterIndividualGarmentParametersFactory
    )

    @classmethod
    def _compute_attr(cls, resolver, attr_name):
        try:
            computed_schematic = resolver.computed_schematic
        except AttributeError:
            igp = resolver.individual_garment_parameters
            user = igp.user
            computed_schematic = cls._meta.model.make_from_garment_parameters(user, igp)
            # Note we need to use the private API of the Resolver class to get around
            # some of its internal safeties
            resolver.__dict__["computed_schematic"] = computed_schematic
        return getattr(computed_schematic, attr_name)

    sweater_back = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "sweater_back")
    )
    sweater_front = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "sweater_front")
    )
    vest_back = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "vest_back")
    )
    vest_front = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "vest_front")
    )
    sleeve = LazyAttribute(lambda r: SweaterSchematicFactory._compute_attr(r, "sleeve"))
    cardigan_vest = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "cardigan_vest")
    )
    cardigan_sleeved = LazyAttribute(
        lambda r: SweaterSchematicFactory._compute_attr(r, "cardigan_sleeved")
    )


class GradedSweaterSchematicFactory(GradedConstructionSchematicFactory):
    class Meta:
        model = GradedSweaterSchematic

    graded_garment_parameters = SubFactory(SweaterGradedGarmentParametersFactory)

    @classmethod
    def from_pspec_kwargs(cls, **kwargs):
        ggp = SweaterGradedGarmentParametersFactory.from_pspec_kwargs(**kwargs)
        return GradedSweaterSchematic.make_from_garment_parameters(ggp)

    @classmethod
    def from_pspec(cls, pspec):
        ggp = SweaterGradedGarmentParametersFactory.from_pspec(pspec)
        return GradedSweaterSchematic.make_from_garment_parameters(ggp)

    sweater_back1 = RelatedFactory(
        GradedSweaterBackSchematicFactory,
        "construction_schematic",
        hip_width=14.5,
        shoulder_height=23.0,
        armpit_height=16.0,
        waist_height=8.0,
        bust_width=14.5,
        waist_width=13.5,
        neck_height=22.0,
        cross_back_width=12.5,
        neck_opening_width=6.25,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                0
            ]
        ),
    )

    sweater_back2 = RelatedFactory(
        GradedSweaterBackSchematicFactory,
        "construction_schematic",
        hip_width=16.5,
        shoulder_height=20.5,
        armpit_height=13.5,
        waist_height=6.5,
        bust_width=17.5,
        waist_width=14.5,
        neck_height=19.5,
        cross_back_width=13.25,
        neck_opening_width=6.625,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                1
            ]
        ),
    )

    sweater_back3 = RelatedFactory(
        GradedSweaterBackSchematicFactory,
        "construction_schematic",
        hip_width=19.5,
        shoulder_height=18.0,
        armpit_height=10.0,
        waist_height=4.0,
        bust_width=19.0,
        waist_width=18.0,
        neck_height=17.0,
        cross_back_width=13.5,
        neck_opening_width=6.75,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                2
            ]
        ),
    )

    sweater_back4 = RelatedFactory(
        GradedSweaterBackSchematicFactory,
        "construction_schematic",
        hip_width=29.0,
        shoulder_height=25.0,
        armpit_height=15.0,
        waist_height=7.0,
        bust_width=21.75,
        waist_width=21.75,
        neck_height=24.0,
        cross_back_width=15.0,
        neck_opening_width=7.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                3
            ]
        ),
    )

    sweater_back5 = RelatedFactory(
        GradedSweaterBackSchematicFactory,
        "construction_schematic",
        hip_width=25.5,
        shoulder_height=27.0,
        armpit_height=16.0,
        waist_height=7.0,
        bust_width=24.5,
        waist_width=23.5,
        neck_height=26.0,
        cross_back_width=16.75,
        neck_opening_width=8.375,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                4
            ]
        ),
    )

    sweater_front1 = RelatedFactory(
        GradedSweaterFrontSchematicFactory,
        "construction_schematic",
        hip_width=14.5,
        shoulder_height=23.0,
        armpit_height=16.0,
        waist_height=8.0,
        bust_width=14.5,
        waist_width=14.5,
        neck_height=17.0,
        neckline_style=SDC.NECK_VEE,
        below_armpit_straight=1.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                0
            ]
        ),
    )

    sweater_front2 = RelatedFactory(
        GradedSweaterFrontSchematicFactory,
        "construction_schematic",
        hip_width=16.5,
        shoulder_height=20.5,
        armpit_height=13.5,
        waist_height=6.5,
        bust_width=17.5,
        waist_width=14.5,
        neck_height=14.5,
        neckline_style=SDC.NECK_VEE,
        below_armpit_straight=1.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                1
            ]
        ),
    )

    sweater_front3 = RelatedFactory(
        GradedSweaterFrontSchematicFactory,
        "construction_schematic",
        hip_width=19.5,
        shoulder_height=18.0,
        armpit_height=10.0,
        waist_height=4.0,
        bust_width=20.0,
        waist_width=19.0,
        neck_height=12.0,
        neckline_style=SDC.NECK_VEE,
        below_armpit_straight=1.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                2
            ]
        ),
    )

    sweater_front4 = RelatedFactory(
        GradedSweaterFrontSchematicFactory,
        "construction_schematic",
        hip_width=29.0,
        shoulder_height=25.0,
        armpit_height=15.0,
        waist_height=7.0,
        bust_width=25.75,
        waist_width=25.75,
        neck_height=19.0,
        neckline_style=SDC.NECK_VEE,
        below_armpit_straight=1.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                3
            ]
        ),
    )

    sweater_front5 = RelatedFactory(
        GradedSweaterFrontSchematicFactory,
        "construction_schematic",
        hip_width=26.5,
        shoulder_height=27.0,
        armpit_height=16.0,
        waist_height=7.0,
        bust_width=27.5,
        waist_width=26.5,
        neck_height=21.0,
        neckline_style=SDC.NECK_VEE,
        below_armpit_straight=1.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                4
            ]
        ),
    )

    sleeve1 = RelatedFactory(
        GradedSleeveSchematicFactory,
        "construction_schematic",
        sleeve_to_armcap_start_height=18.0,
        bicep_width=10.25,
        sleeve_cast_on_width=8.0,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                0
            ]
        ),
    )

    sleeve2 = RelatedFactory(
        GradedSleeveSchematicFactory,
        "construction_schematic",
        sleeve_to_armcap_start_height=16.5,
        bicep_width=11.25,
        sleeve_cast_on_width=8.0,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                1
            ]
        ),
    )

    sleeve3 = RelatedFactory(
        GradedSleeveSchematicFactory,
        "construction_schematic",
        sleeve_to_armcap_start_height=18.0,
        bicep_width=13.75,
        sleeve_cast_on_width=9.5,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                2
            ]
        ),
    )

    sleeve4 = RelatedFactory(
        GradedSleeveSchematicFactory,
        "construction_schematic",
        sleeve_to_armcap_start_height=17.0,
        bicep_width=16.25,
        sleeve_cast_on_width=9.0,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                3
            ]
        ),
    )

    sleeve5 = RelatedFactory(
        GradedSleeveSchematicFactory,
        "construction_schematic",
        sleeve_to_armcap_start_height=19.0,
        bicep_width=16.25,
        sleeve_cast_on_width=10.0,
        gp_grade=LazyAttribute(
            lambda sch: sch.construction_schematic.graded_garment_parameters.all_grades.order_by(
                "SweaterGradedGarmentParametersGrade___grade__bust_circ"
            )[
                4
            ]
        ),
    )
