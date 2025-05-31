from factory import SelfAttribute, SubFactory, post_generation

from customfit.patterns.factories import (
    ApprovedPatternFactory,
    ArchivedPatternFactory,
    GradedPatternFactory,
    IndividualPatternFactory,
)
from customfit.stitches.factories import StitchFactory

from ..helpers import sweater_design_choices as SDC
from ..models import CardiganSleeved, CardiganVest, GradedSweaterPattern, SweaterPattern
from .garment_parameters import SweaterIndividualGarmentParametersFactory
from .pattern_specs import SweaterPatternSpecFactory, create_csv_combo
from .pieces import GradedSweaterPatternPiecesFactory, SweaterPatternPiecesFactory

#
# Patterns
#


class SweaterPatternFactory(IndividualPatternFactory):
    class Meta:
        model = SweaterPattern

    pieces = SubFactory(
        SweaterPatternPiecesFactory,
        schematic__individual_garment_parameters__user=SelfAttribute("....user"),
    )

    @classmethod
    def for_user(cls, user):
        return cls(user=user)

    @classmethod
    def from_pspec(cls, pspec):
        return cls(
            pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
            user=pspec.user,
        )

    @classmethod
    def from_igp(cls, igp):
        return cls(
            pieces__schematic__individual_garment_parameters=igp,
            user=igp.pattern_spec.user,
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


class ApprovedSweaterPatternFactory(SweaterPatternFactory, ApprovedPatternFactory):
    pass


class ArchivedSweaterPatternFactory(
    ApprovedSweaterPatternFactory, ArchivedPatternFactory
):
    archived = True


# cardigan sleeved


def create_cardigan_sleeved(**kwargs):
    pspec = SweaterPatternSpecFactory(
        garment_type=SDC.CARDIGAN_SLEEVED,
        button_band_edging_height=0,
        button_band_allowance=0,
        button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        number_of_buttons=6,
    )
    p = SweaterPatternFactory.from_pspec(pspec)
    cs = p.get_front_piece()
    cs.__dict__.update(**kwargs)
    return cs


def make_cardigan_sleeved_from_pspec(pspec):
    p = SweaterPatternFactory.from_pspec(pspec)
    cs = p.get_front_piece()
    assert isinstance(cs, CardiganSleeved)
    return cs


# cardigan vest


def make_cardigan_vest_from_pspec(pspec):
    p = SweaterPatternFactory.from_pspec(pspec)
    cf = p.get_front_piece()
    assert isinstance(cf, CardiganVest)
    return cf


def pattern_from_csv_combo(body_name, swatch_name, design_name):
    pspec = create_csv_combo(body_name, swatch_name, design_name)
    p = SweaterPatternFactory.from_pspec(pspec)
    p.full_clean()
    return p


class RedoneSweaterPatternFactory(ApprovedSweaterPatternFactory):

    @post_generation
    def redo(self, create, extracted, **kwargs):

        from .redos import SweaterRedoFactory

        ## Create a Redo object, then redo the pattern
        assert "pattern" not in kwargs
        kwargs["pattern"] = self
        new_redo_object = SweaterRedoFactory(**kwargs)
        new_igp = SweaterIndividualGarmentParametersFactory(
            pattern_spec=None, redo=new_redo_object, user=new_redo_object.pattern.user
        )
        new_pieces = SweaterPatternPiecesFactory(
            schematic__individual_garment_parameters=new_igp
        )
        self.update_with_new_pieces(new_pieces)
        self.save()
        return self


def pattern_from_pspec_and_redo_kwargs(pspec, **kwargs):
    from .redos import SweaterRedoFactory

    redo = SweaterRedoFactory.from_original_pspec(pspec, **kwargs)
    pattern = redo.pattern
    new_igp = SweaterIndividualGarmentParametersFactory(
        pattern_spec=None, redo=redo, user=redo.pattern.user
    )
    new_pieces = SweaterPatternPiecesFactory(
        schematic__individual_garment_parameters=new_igp
    )
    pattern.update_with_new_pieces(new_pieces)
    pattern.save()
    return pattern


class GradedSweaterPatternFactory(GradedPatternFactory):
    class Meta:
        model = GradedSweaterPattern

    @classmethod
    def from_pspec_kwargs(cls, **kwargs):
        gpp = GradedSweaterPatternPiecesFactory.from_pspec_kwargs(**kwargs)
        return GradedSweaterPattern.make_from_graded_pattern_pieces(gpp)

    @classmethod
    def from_pspec(cls, pspec):
        gpp = GradedSweaterPatternPiecesFactory.from_pspec(pspec)
        p = GradedSweaterPattern.make_from_graded_pattern_pieces(gpp)
        p.save()
        return p
