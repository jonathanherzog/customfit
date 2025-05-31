import copy

from factory import SelfAttribute, SubFactory
from factory.django import DjangoModelFactory

from customfit.bodies.factories import BodyFactory, GradeSetFactory, get_csv_body
from customfit.pattern_spec.factories import (
    GradedPatternSpecFactory,
    PatternSpecFactory,
)
from customfit.swatches.factories import get_csv_swatch

from ..helpers import sweater_design_choices as SDC
from ..models import GradedSweaterPatternSpec, SweaterDesignBase, SweaterPatternSpec
from .designs import (
    CardiganDesignFactoryBase,
    CardiganVestDesignFactoryBase,
    SweaterDesignFactoryBase,
    VestDesignFactoryBase,
    make_csv_designs,
)


class BaseSweaterPatternSpecFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    garment_fit = SDC.FIT_HOURGLASS_AVERAGE
    silhouette = SDC.SILHOUETTE_HOURGLASS
    construction = SDC.CONSTRUCTION_SET_IN_SLEEVE
    drop_shoulder_additional_armhole_depth = None


class IndividualSweaterPatternSpecFactoryBase(
    PatternSpecFactory, BaseSweaterPatternSpecFactory
):
    class Meta:
        model = SweaterPatternSpec
        abstract = True

    body = SubFactory(BodyFactory, user=SelfAttribute("..user"))


class SweaterPatternSpecFactory(
    IndividualSweaterPatternSpecFactoryBase, SweaterDesignFactoryBase
):
    class Meta:
        abstract = False


class VestPatternSpecFactory(
    IndividualSweaterPatternSpecFactoryBase, VestDesignFactoryBase
):
    class Meta:
        abstract = False


class GradedSweaterPatternSpecFactoryBase(
    GradedPatternSpecFactory, BaseSweaterPatternSpecFactory
):
    class Meta:
        model = GradedSweaterPatternSpec
        abstract = True

    gradeset = SubFactory(GradeSetFactory, user=SelfAttribute("..user"))
    row_gauge = 100
    stitch_gauge = 100
    neckline_depth = 2
    neckline_depth_orientation = SDC.BELOW_SHOULDERS
    neckline_style = SDC.NECK_CREW


class GradedSweaterPatternSpecFactory(
    GradedSweaterPatternSpecFactoryBase, SweaterDesignFactoryBase
):
    class Meta:
        abstract = False


class GradedVestPatternSpecFactory(
    GradedSweaterPatternSpecFactoryBase, VestDesignFactoryBase
):
    class Meta:
        abstract = False


class GradedCardiganPatternSpecFactory(
    GradedSweaterPatternSpecFactoryBase, CardiganDesignFactoryBase
):
    class Meta:
        abstract = False


class GradedCardiganVestPatternSpecFactory(
    GradedSweaterPatternSpecFactoryBase, CardiganVestDesignFactoryBase
):
    class Meta:
        abstract = False


class DropShoulderSweaterPatternSpecFactory(SweaterPatternSpecFactory):
    construction = SDC.CONSTRUCTION_DROP_SHOULDER
    drop_shoulder_additional_armhole_depth = (
        SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE
    )


def make_patternspec_from_design(
    design, user, name, swatch, body, silhouette, fit, construction=None
):
    ps = SweaterPatternSpec()
    ps.user = user
    ps.name = name
    ps.swatch = swatch
    ps.body = body
    ps.silhouette = silhouette
    ps.garment_fit = fit
    ps.construction = (
        construction if construction is not None else design.primary_construction
    )
    for field in SweaterDesignBase._meta.get_fields():
        setattr(ps, field.name, getattr(design, field.name))
    ps.name = design.name
    ps.pattern_credits = design.pattern_credits
    ps.design_origin = design
    return ps


#
# Quick-create of combinations
#


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
