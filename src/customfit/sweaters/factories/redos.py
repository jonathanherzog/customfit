from factory import SelfAttribute, SubFactory

from customfit.bodies.factories import BodyFactory
from customfit.patterns.factories import RedoFactory

from ..helpers import sweater_design_choices as SDC
from ..models import SweaterRedo
from .patterns import ApprovedSweaterPatternFactory

# Redos and redone patterns


class SweaterRedoFactory(RedoFactory):
    class Meta:
        model = SweaterRedo

    # The following have been chosen to differ from PatternSpecFactory
    garment_fit = SDC.FIT_HOURGLASS_RELAXED
    torso_length = SDC.LOW_HIP_LENGTH
    sleeve_length = SDC.SLEEVE_THREEQUARTER
    neckline_depth = 1
    neckline_depth_orientation = SDC.ABOVE_ARMPIT

    pattern = SubFactory(ApprovedSweaterPatternFactory)
    body = SubFactory(BodyFactory, user=SelfAttribute("..pattern.user"))

    @classmethod
    def from_original_pspec(cls, pspec, **kwargs):
        return cls(
            pattern__user=pspec.user,
            pattern__pieces__schematic__individual_garment_parameters__pattern_spec=pspec,
            **kwargs
        )
