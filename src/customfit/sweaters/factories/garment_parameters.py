import copy

from factory import (
    CREATE_STRATEGY,
    LazyAttribute,
    RelatedFactory,
    SelfAttribute,
    SubFactory,
)
from factory.django import DjangoModelFactory

from customfit.bodies.factories import get_csv_body
from customfit.garment_parameters.factories import (
    GradedGarmentParametersFactory,
    GradedGarmentParametersGradeFactory,
    IndividualGarmentParametersFactory,
)
from customfit.swatches.factories import get_csv_swatch

from ..models import (
    SweaterGradedGarmentParameters,
    SweaterGradedGarmentParametersGrade,
    SweaterIndividualGarmentParameters,
)
from .designs import make_csv_designs
from .pattern_specs import GradedSweaterPatternSpecFactory, SweaterPatternSpecFactory


class _SweaterGarmentParametersTopLevelFactory(DjangoModelFactory):
    class Meta:
        abstract = True


class _SweaterGarmentDimensionsFactory(DjangoModelFactory):
    class Meta:
        abstract = True


class SweaterIndividualGarmentParametersFactory(
    IndividualGarmentParametersFactory,
    _SweaterGarmentParametersTopLevelFactory,
    _SweaterGarmentDimensionsFactory,
):

    class Meta:
        model = SweaterIndividualGarmentParameters
        strategy = CREATE_STRATEGY

    pattern_spec = SubFactory(SweaterPatternSpecFactory, user=SelfAttribute("..user"))

    @classmethod
    def _compute_attr(cls, resolver, attr_name):
        try:
            computed_igp = resolver.computed_igp
        except AttributeError:
            if resolver.redo is not None:
                # Should not have both redo and pattern_spec
                assert resolver.pattern_spec is None
                computed_igp = SweaterIndividualGarmentParameters.make_from_redo(
                    resolver.user, resolver.redo
                )
            else:
                computed_igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                    resolver.user, resolver.pattern_spec
                )
            spec_source = (
                resolver.redo if resolver.redo is not None else resolver.pattern_spec
            )
            # Note we need to use the private API of the Resolver class to get around
            # some of its internal safeties
            resolver.__dict__["computed_igp"] = computed_igp
        return getattr(computed_igp, attr_name)

    waist_height_front = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "waist_height_front"
        )
    )

    waist_height_back = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "waist_height_back"
        )
    )

    armpit_height = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "armpit_height"
        )
    )

    armhole_depth = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "armhole_depth"
        )
    )

    below_armhole_straight = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "below_armhole_straight"
        )
    )

    back_neck_depth = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "back_neck_depth"
        )
    )

    front_neck_depth = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "front_neck_depth"
        )
    )

    hip_width_back = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "hip_width_back"
        )
    )

    hip_width_front = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "hip_width_front"
        )
    )

    bust_width_back = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "bust_width_back"
        )
    )

    bust_width_front = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "bust_width_front"
        )
    )

    back_cross_back_width = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "back_cross_back_width"
        )
    )

    back_neck_opening_width = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "back_neck_opening_width"
        )
    )

    waist_width_back = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "waist_width_back"
        )
    )

    waist_width_front = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "waist_width_front"
        )
    )

    sleeve_to_armcap_start_height = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "sleeve_to_armcap_start_height"
        )
    )

    bicep_width = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "bicep_width"
        )
    )

    sleeve_cast_on_width = LazyAttribute(
        lambda r: SweaterIndividualGarmentParametersFactory._compute_attr(
            r, "sleeve_cast_on_width"
        )
    )


def create_csv_combo(body_name, swatch_name, design_name):
    """
    Create an PatternSpec from the names of bodies, swatches and
    designs in the CSV files. Convenience function for making tests.
    """
    b = get_csv_body(body_name)

    sw = get_csv_swatch(swatch_name)

    csv_designs = make_csv_designs()
    pspec_dict = copy.copy(csv_designs[design_name])

    name = "CSV: %s / %s / %s" % (b.name, sw.name, pspec_dict["name"])

    pspec_dict["body"] = b
    pspec_dict["swatch"] = sw
    pspec_dict["name"] = name
    pspec = SweaterPatternSpecFactory(**pspec_dict)

    return pspec


class SweaterGradedGarmentParametersGradeFactory(
    _SweaterGarmentDimensionsFactory, GradedGarmentParametersGradeFactory
):
    class Meta:
        model = SweaterGradedGarmentParametersGrade
        strategy = CREATE_STRATEGY

    graded_garment_parameters = SubFactory(
        "customfit.sweaters.factories.SweaterGradedGarmentParametersFactory"
    )
    grade = LazyAttribute(
        lambda sggpg: sggpg.graded_garment_parameters.pattern_spec.all_grades()[0]
    )

    waist_height_front = 8.0
    waist_height_back = 8.0
    armpit_height = 16.0
    armhole_depth = 7.0
    below_armhole_straight = 1.5
    back_neck_depth = 1.0
    front_neck_depth = 6.0
    hip_width_back = 14.5
    hip_width_front = 14.5
    bust_width_back = 14.5
    bust_width_front = 14.5
    back_cross_back_width = 12.5
    back_neck_opening_width = 6.25
    waist_width_back = 13.5
    waist_width_front = 14.5
    sleeve_to_armcap_start_height = 18.0
    bicep_width = 10.25
    sleeve_cast_on_width = 8.0


class SweaterGradedGarmentParametersFactory(
    GradedGarmentParametersFactory, _SweaterGarmentParametersTopLevelFactory
):
    class Meta:
        model = SweaterGradedGarmentParameters

    pattern_spec = SubFactory(
        GradedSweaterPatternSpecFactory, user=SelfAttribute("..user")
    )

    @classmethod
    def from_pspec_kwargs(cls, **kwargs):
        gps = GradedSweaterPatternSpecFactory(**kwargs)
        return SweaterGradedGarmentParameters.make_from_patternspec(gps.user, gps)

    @classmethod
    def from_pspec(cls, pspec):
        return SweaterGradedGarmentParameters.make_from_patternspec(pspec.user, pspec)

    grade1 = RelatedFactory(
        SweaterGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        waist_height_front=8.0,
        waist_height_back=8.0,
        armpit_height=16.0,
        armhole_depth=7.0,
        below_armhole_straight=1.5,
        back_neck_depth=1.0,
        front_neck_depth=6.0,
        hip_width_back=14.5,
        hip_width_front=14.5,
        bust_width_back=14.5,
        bust_width_front=14.5,
        back_cross_back_width=12.5,
        back_neck_opening_width=6.25,
        waist_width_back=13.5,
        waist_width_front=14.5,
        sleeve_to_armcap_start_height=18.0,
        bicep_width=10.25,
        sleeve_cast_on_width=8.0,
        grade=LazyAttribute(
            lambda grade: grade.graded_garment_parameters.pattern_spec.gradeset.grades.order_by(
                "bust_circ"
            )[
                0
            ]
        ),
    )

    grade2 = RelatedFactory(
        SweaterGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        waist_height_front=6.5,
        waist_height_back=6.5,
        armpit_height=13.5,
        armhole_depth=7.0,
        below_armhole_straight=1.5,
        back_neck_depth=1.0,
        front_neck_depth=6.0,
        hip_width_back=16.5,
        hip_width_front=16.5,
        bust_width_back=17.5,
        bust_width_front=17.5,
        back_cross_back_width=13.25,
        back_neck_opening_width=6.625,
        waist_width_back=14.5,
        waist_width_front=14.5,
        sleeve_to_armcap_start_height=16.5,
        bicep_width=11.25,
        sleeve_cast_on_width=8.0,
        grade=LazyAttribute(
            lambda grade: grade.graded_garment_parameters.pattern_spec.gradeset.grades.order_by(
                "bust_circ"
            )[
                1
            ]
        ),
    )

    grade3 = RelatedFactory(
        SweaterGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        waist_height_front=4.0,
        waist_height_back=4.0,
        armpit_height=10.0,
        armhole_depth=8.0,
        below_armhole_straight=1.5,
        back_neck_depth=1.0,
        front_neck_depth=6.0,
        hip_width_back=19.5,
        hip_width_front=19.5,
        bust_width_back=19.0,
        bust_width_front=20.0,
        back_cross_back_width=13.5,
        back_neck_opening_width=6.75,
        waist_width_back=18.0,
        waist_width_front=19.0,
        sleeve_to_armcap_start_height=18.0,
        bicep_width=13.75,
        sleeve_cast_on_width=9.5,
        grade=LazyAttribute(
            lambda grade: grade.graded_garment_parameters.pattern_spec.gradeset.grades.order_by(
                "bust_circ"
            )[
                2
            ]
        ),
    )

    grade4 = RelatedFactory(
        SweaterGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        waist_height_front=7.0,
        waist_height_back=7.0,
        armpit_height=15.0,
        armhole_depth=10.0,
        below_armhole_straight=1.5,
        back_neck_depth=1.0,
        front_neck_depth=6.0,
        hip_width_back=29.0,
        hip_width_front=29.0,
        bust_width_back=21.75,
        bust_width_front=25.75,
        back_cross_back_width=15.0,
        back_neck_opening_width=7.5,
        waist_width_back=21.75,
        waist_width_front=25.75,
        sleeve_to_armcap_start_height=17.0,
        bicep_width=16.25,
        sleeve_cast_on_width=9.0,
        grade=LazyAttribute(
            lambda grade: grade.graded_garment_parameters.pattern_spec.gradeset.grades.order_by(
                "bust_circ"
            )[
                3
            ]
        ),
    )

    grade5 = RelatedFactory(
        SweaterGradedGarmentParametersGradeFactory,
        "graded_garment_parameters",
        waist_height_front=7.0,
        waist_height_back=7.0,
        armpit_height=16.0,
        armhole_depth=11.0,
        below_armhole_straight=1.5,
        back_neck_depth=1.0,
        front_neck_depth=6.0,
        hip_width_back=25.5,
        hip_width_front=26.5,
        bust_width_back=24.5,
        bust_width_front=27.5,
        back_cross_back_width=16.75,
        back_neck_opening_width=8.375,
        waist_width_back=23.5,
        waist_width_front=26.5,
        sleeve_to_armcap_start_height=19.0,
        bicep_width=16.25,
        sleeve_cast_on_width=10.0,
        grade=LazyAttribute(
            lambda grade: grade.graded_garment_parameters.pattern_spec.gradeset.grades.order_by(
                "bust_circ"
            )[
                4
            ]
        ),
    )
