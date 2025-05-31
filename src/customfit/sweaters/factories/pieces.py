from factory import LazyAttribute, SubFactory
from factory.django import DjangoModelFactory

from customfit.pieces.factories import GradedPatternPiecesFactory

from ..models import (
    BackNeckline,
    CrewNeck,
    GradedSweaterPatternPieces,
    ScoopNeck,
    Sleeve,
    SweaterBack,
    SweaterFront,
    SweaterPatternPieces,
    VeeNeck,
    VestBack,
    VestFront,
)
from .pattern_specs import SweaterPatternSpecFactory
from .schematics import GradedSweaterSchematicFactory, SweaterSchematicFactory

#
# Necklines
#


class BackNecklineFactory(DjangoModelFactory):
    class Meta:
        model = BackNeckline

    bindoff_stitches = 20
    stitches_before_initial_bindoffs = 13
    neckline_depth = 6
    pickup_stitches = 40


class VeeNeckFactory(DjangoModelFactory):
    class Meta:
        model = VeeNeck

    depth = 6
    extra_bindoffs = 1
    rows_per_decrease = 3
    decrease_rows = 7
    pickup_stitches = 40


class CrewNeckFactory(DjangoModelFactory):
    class Meta:
        model = CrewNeck

    depth = 4
    bindoffs_before_marker = 6
    center_bindoffs = 12
    marker_before_center_stitch = False
    neck_edge_decreases = 3
    rs_edge_decreases = 3
    pickup_stitches = 57


class ScoopNeckFactory(DjangoModelFactory):
    class Meta:
        model = ScoopNeck

    marker_before_center_stitch = False
    bindoff_stitches_before_marker = 8
    y_bindoffs = 5
    z_bindoffs = 4
    q_bindoffs = 3
    _total_depth = 6
    pickup_stitches = 57


#
# IPP
#


class SweaterPatternPiecesFactory(DjangoModelFactory):
    class Meta:
        model = SweaterPatternPieces

    schematic = SubFactory(SweaterSchematicFactory)

    @classmethod
    def _compute_attr(cls, resolver, attr_name):
        try:
            computed_pieces = resolver.computed_pieces
        except AttributeError:
            ips = resolver.schematic
            computed_pieces = cls._meta.model.make_from_individual_pieced_schematic(ips)
            # Note we need to use the private API of the Resolver class to get around
            # some of its internal safeties
            resolver.__dict__["computed_pieces"] = computed_pieces
        return getattr(computed_pieces, attr_name)

    sweater_back = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "sweater_back")
    )
    sweater_front = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "sweater_front")
    )
    vest_back = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "vest_back")
    )
    vest_front = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "vest_front")
    )
    sleeve = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "sleeve")
    )
    cardigan_vest = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "cardigan_vest")
    )
    cardigan_sleeved = LazyAttribute(
        lambda r: SweaterPatternPiecesFactory._compute_attr(r, "cardigan_sleeved")
    )


#
# Pieces
#


# sweater back


def create_sweater_back(**kwargs):
    from .patterns import SweaterPatternFactory

    pattern = SweaterPatternFactory()
    sb = pattern.get_back_piece()
    assert isinstance(sb, SweaterBack)
    sb.__dict__.update(**kwargs)
    return sb


def make_sweaterback_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory.from_pspec(pspec)
    sb = p.get_back_piece()
    assert isinstance(sb, SweaterBack)
    return sb


# sweater front


def create_sweater_front(**kwargs):
    from .patterns import SweaterPatternFactory

    pattern = SweaterPatternFactory()
    sb = pattern.get_front_piece()
    assert isinstance(sb, SweaterFront)
    sb.__dict__.update(**kwargs)
    return sb


def make_sweaterfront_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory.from_pspec(pspec)
    sf = p.get_front_piece()
    assert isinstance(sf, SweaterFront)
    return sf


def make_sweaterfront_from_pspec_kwargs(**kwargs):
    from .patterns import SweaterPatternFactory

    pspec = SweaterPatternSpecFactory(**kwargs)
    return make_sweaterfront_from_pspec(pspec)


def make_sweaterfront_from_ips(ips):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory(pieces__schematic=ips)
    sb = p.get_front_piece()
    assert isinstance(sb, SweaterFront)
    return sb


# vest back


def make_vestback_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory.from_pspec(pspec)
    sb = p.get_back_piece()
    assert isinstance(sb, VestBack)
    return sb


# vest front


def make_vestfront_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory.from_pspec(pspec)
    sb = p.get_front_piece()
    assert isinstance(sb, VestFront)
    return sb


def make_vestfront_from_pspec_kwargs(**kwargs):
    pspec = SweaterPatternSpecFactory(**kwargs)
    return make_vestfront_from_pspec(pspec)


# sleeve


def create_sleeve(**kwargs):
    from .patterns import SweaterPatternFactory

    pattern = SweaterPatternFactory()
    sl = pattern.get_sleeve()
    sl.__dict__.update(**kwargs)
    return sl


def make_sleeve_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    pattern = SweaterPatternFactory.from_pspec(pspec)
    sl = pattern.get_sleeve()
    assert isinstance(sl, Sleeve)
    return sl


def make_sleeve_from_ips(ips):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory(pieces__schematic=ips)
    sl = p.get_sleeve()
    assert isinstance(sl, Sleeve)
    return sl


# button band


def make_buttonband_from_pspec(pspec):
    from .patterns import SweaterPatternFactory

    p = SweaterPatternFactory.from_pspec(pspec)
    p.full_clean()
    return p.get_buttonband()


#########################################
#  Graded
##########################################


class GradedSweaterPatternPiecesFactory(GradedPatternPiecesFactory):
    class Meta:
        model = GradedSweaterPatternPieces

    schematic = SubFactory(GradedSweaterSchematicFactory)

    @classmethod
    def from_pspec_kwargs(cls, **kwargs):
        gcs = GradedSweaterSchematicFactory.from_pspec_kwargs(**kwargs)
        return GradedSweaterPatternPieces.make_from_schematic(gcs)

    @classmethod
    def from_pspec(cls, pspec):
        gcs = GradedSweaterSchematicFactory.from_pspec(pspec)
        return GradedSweaterPatternPieces.make_from_schematic(gcs)


# class GradedSweaterBackFactory(GradedPatternPieceFactory):
#     class Meta:
#         model = GradedSweaterBack
#
#     sort_key = 53.0
#     _hourglass = True
#     cast_ons = 638
#     num_waist_standard_decrease_rows = 25
#     rows_between_waist_standard_decrease_rows = 3
#     num_waist_double_dart_rows = 0
#     num_waist_triple_dart_rows = 0
#     pre_marker = 213
#     waist_double_dart_marker = None
#     waist_triple_dart_marker = None
#     begin_decreases_height = 2.62
#     hem_to_waist = 7.5
#     num_bust_standard_increase_rows = 13
#     rows_between_bust_standard_increase_rows = 13
#     num_bust_double_dart_increase_rows = 0
#     num_bust_triple_dart_rows = 0
#     bust_pre_standard_dart_marker = 188
#     bust_pre_double_dart_marker = None
#     bust_pre_triple_dart_marker = None
#     hem_to_armhole_shaping_start = 16.0
#     armhole_x = 26
#     armhole_y = 25
#     armhole_z = 46
#     hem_to_shoulders = 27.0
#     first_shoulder_bindoff = 53
#     num_shoulder_stitches = 105
#     actual_armhole_circumference = 13.394365078599613
#     cross_chest_stitches = 420
#     actual_neck_opening = 8.4
#     neckline = SubFactory(BackNecklineFactory, bindoff_stitches=206, stitches_before_initial_bindoffs=107,
#                           neckline_depth=1.0, pickup_stitches=260, row_gauge=25.0, stitch_gauge=25.0)
#     graded_pattern_pieces = SubFactory(GradedSweaterPatternPiecesFactory)
#     schematic = SubFactory(GradedSweaterBackSchematicFactory, construction_schematic=SelfAttribute('..graded_pattern_pieces.schematic'))
#
#
# class GradedVestBackFactory(GradedPatternPieceFactory):
#     class Meta:
#         model = GradedVestBack
#
#     sort_key = 53.0
#     _hourglass = True
#     cast_ons = 638
#     num_waist_standard_decrease_rows = 25
#     rows_between_waist_standard_decrease_rows = 3
#     num_waist_double_dart_rows = 0
#     num_waist_triple_dart_rows = 0
#     pre_marker = 213
#     waist_double_dart_marker = None
#     waist_triple_dart_marker = None
#     begin_decreases_height = 2.62
#     hem_to_waist = 7.5
#     num_bust_standard_increase_rows = 13
#     rows_between_bust_standard_increase_rows = 13
#     num_bust_double_dart_increase_rows = 0
#     num_bust_triple_dart_rows = 0
#     bust_pre_standard_dart_marker = 188
#     bust_pre_double_dart_marker = None
#     bust_pre_triple_dart_marker = None
#     hem_to_armhole_shaping_start = 16.0
#     armhole_x = 26
#     armhole_y = 25
#     armhole_z = 46
#     hem_to_shoulders = 27.0
#     first_shoulder_bindoff = 53
#     num_shoulder_stitches = 105
#     actual_armhole_circumference = 13.394365078599613
#     cross_chest_stitches = 420
#     actual_neck_opening = 8.4
#     neckline = SubFactory(BackNecklineFactory, bindoff_stitches=206, stitches_before_initial_bindoffs=107,
#                           neckline_depth=1.0, pickup_stitches=260, row_gauge=25.0, stitch_gauge=25.0)
#     graded_pattern_pieces = SubFactory(GradedSweaterPatternPiecesFactory)
#     schematic = SubFactory(GradedVestBackSchematicFactory,
#                            construction_schematic=SelfAttribute('..graded_pattern_pieces.schematic'))
