import copy

from factory import CREATE_STRATEGY, Sequence, SubFactory
from factory.django import DjangoModelFactory

from customfit.designs.factories import (
    DesignFactory,
    _AdditionalDesignElementFactoryBase,
)
from customfit.stitches.factories import StitchFactory

from ..helpers import sweater_design_choices as SDC
from ..models import (
    AdditionalBackElement,
    AdditionalBodyPieceElement,
    AdditionalFrontElement,
    AdditionalFullTorsoElement,
    AdditionalSleeveElement,
    SweaterDesign,
)

# Copied from designs


class SweaterDesignFactoryBase(DjangoModelFactory):

    class Meta:
        strategy = CREATE_STRATEGY
        abstract = True

    # DesignBase fields
    name = Sequence(lambda n: "factory-made design %s" % n)
    garment_type = SDC.PULLOVER_SLEEVED
    sleeve_length = SDC.SLEEVE_FULL
    sleeve_shape = SDC.SLEEVE_TAPERED
    bell_type = None
    drop_shoulder_additional_armhole_depth = None
    neckline_style = SDC.NECK_VEE
    torso_length = SDC.MED_HIP_LENGTH
    neckline_width = SDC.NECK_AVERAGE
    neckline_other_val_percentage = None
    neckline_depth = 6
    neckline_depth_orientation = SDC.BELOW_SHOULDERS
    back_allover_stitch = SubFactory(StitchFactory, name="Stockinette")
    front_allover_stitch = SubFactory(StitchFactory, name="Other Stitch")
    sleeve_allover_stitch = SubFactory(StitchFactory, name="Sugar Cube Stitch")
    hip_edging_stitch = SubFactory(StitchFactory, name="1x1 Ribbing")
    hip_edging_height = 1.5
    sleeve_edging_stitch = SubFactory(StitchFactory, name="1x1 Ribbing")
    sleeve_edging_height = 0.5
    neck_edging_stitch = SubFactory(StitchFactory, name="1x1 Ribbing")
    neck_edging_height = 1
    armhole_edging_stitch = None
    armhole_edging_height = None
    button_band_edging_stitch = None
    button_band_edging_height = None
    button_band_allowance = None
    button_band_allowance_percentage = None
    number_of_buttons = None
    panel_stitch = None
    back_cable_stitch = None
    back_cable_extra_stitches = None
    front_cable_stitch = None
    front_cable_extra_stitches = None
    sleeve_cable_stitch = None
    sleeve_cable_extra_stitches = None
    sleeve_cable_extra_stitches_caston_only = False
    pattern_credits = ""


class VestDesignFactoryBaseMixin(DjangoModelFactory):
    class Meta:
        abstract = True

    sleeve_length = None
    sleeve_shape = None
    bell_type = None
    sleeve_edging_stitch = None
    sleeve_edging_height = None
    armhole_edging_stitch = SubFactory(StitchFactory, name="1x1 Ribbing")
    armhole_edging_height = 2


class VestDesignFactoryBase(VestDesignFactoryBaseMixin, SweaterDesignFactoryBase):
    garment_type = SDC.PULLOVER_VEST


class CardiganDesignFactoryBaseMixin(DjangoModelFactory):
    class Meta:
        abstract = True

    button_band_edging_stitch = SubFactory(StitchFactory, name="1x1 Ribbing")
    button_band_edging_height = 1
    button_band_allowance = 2
    button_band_allowance_percentage = None
    number_of_buttons = 5


class CardiganDesignFactoryBase(
    CardiganDesignFactoryBaseMixin, SweaterDesignFactoryBase
):
    garment_type = SDC.CARDIGAN_SLEEVED


class CardiganVestDesignFactoryBase(
    VestDesignFactoryBaseMixin, CardiganDesignFactoryBaseMixin, SweaterDesignFactoryBase
):
    garment_type = SDC.CARDIGAN_VEST


class SweaterDesignFactory(SweaterDesignFactoryBase, DesignFactory):
    class Meta:
        model = SweaterDesign
        strategy = CREATE_STRATEGY
        django_get_or_create = ("name",)

    name = Sequence(lambda n: "factory-made sweater design %s" % n)

    primary_silhouette = SDC.SILHOUETTE_HOURGLASS
    silhouette_aline_allowed = False
    silhouette_hourglass_allowed = True
    silhouette_straight_allowed = True
    silhouette_tapered_allowed = False
    waist_hem_template = None
    sleeve_hem_template = None
    trim_armhole_template = None
    trim_neckline_template = None
    button_band_template = None
    button_band_veeneck_template = None
    extra_finishing_template = None
    primary_construction = SDC.CONSTRUCTION_SET_IN_SLEEVE
    construction_set_in_sleeve_allowed = True
    construction_drop_shoulder_allowed = False


class VestDesignFactory(VestDesignFactoryBase, DesignFactory):
    class Meta:
        model = SweaterDesign
        strategy = CREATE_STRATEGY
        django_get_or_create = ("name",)

    name = Sequence(lambda n: "factory-made vest design %s" % n)

    primary_silhouette = SDC.SILHOUETTE_HOURGLASS
    silhouette_aline_allowed = False
    silhouette_hourglass_allowed = True
    silhouette_straight_allowed = True
    silhouette_tapered_allowed = False
    waist_hem_template = None
    sleeve_hem_template = None
    trim_armhole_template = None
    trim_neckline_template = None
    button_band_template = None
    button_band_veeneck_template = None
    extra_finishing_template = None
    primary_construction = SDC.CONSTRUCTION_SET_IN_SLEEVE
    construction_set_in_sleeve_allowed = True
    construction_drop_shoulder_allowed = False




class AdditionalSleeveElementFactory(_AdditionalDesignElementFactoryBase):
    class Meta:
        strategy = CREATE_STRATEGY
        model = AdditionalSleeveElement

    # Shadow the declaration in _AdditionalDesignElementFactoryBase to enforce the design is a sweater
    design = SubFactory(SweaterDesignFactory)
    start_location_value = 3.0
    start_location_type = AdditionalSleeveElement.START_AFTER_CASTON


class _AdditionalBodyPieceElementBase(_AdditionalDesignElementFactoryBase):
    # Shadow the declaration in _AdditionalDesignElementFactoryBase to enforce the design is a sweater
    design = SubFactory(SweaterDesignFactory)
    start_location_value = 3.0
    start_location_type = AdditionalBodyPieceElement.START_AFTER_CASTON


class AdditionalFrontElementFactory(_AdditionalBodyPieceElementBase):
    class Meta:
        strategy = CREATE_STRATEGY
        model = AdditionalFrontElement


class AdditionalFrontElementFactory(_AdditionalBodyPieceElementBase):
    class Meta:
        strategy = CREATE_STRATEGY
        model = AdditionalFrontElement


class AdditionalBackElementFactory(_AdditionalBodyPieceElementBase):
    class Meta:
        strategy = CREATE_STRATEGY
        model = AdditionalBackElement


class AdditionalFullTorsoElementFactory(_AdditionalBodyPieceElementBase):
    class Meta:
        strategy = CREATE_STRATEGY
        model = AdditionalFullTorsoElement


"""
Hardcoded designs for testing purposes. Note: called csv_designs for
historical reasons (they used to be stored in CSV format.)
"""

_csv_designs = {
    "Test 1": {
        "garment_fit": SDC.FIT_HOURGLASS_TIGHT,
        "garment_type": SDC.PULLOVER_SLEEVED,
        "hip_edging_stitch": "1x1 Ribbing",
        "name": "Test 1",
        "neck_edging_stitch": "1x1 Ribbing",
        "neckline_style": SDC.NECK_VEE,
        "sleeve_edging_stitch": "1x1 Ribbing",
        "sleeve_length": SDC.SLEEVE_SHORT,
        "sleeve_shape": SDC.SLEEVE_TAPERED,
        "torso_length": SDC.MED_HIP_LENGTH,
    },
    "Test 10": {
        "armhole_edging_height": 0.5,
        "armhole_edging_stitch": "Icord Stitch",
        "garment_fit": SDC.FIT_HOURGLASS_TIGHT,
        "garment_type": SDC.PULLOVER_VEST,
        "hip_edging_stitch": "Seed Stitch",
        "name": "Test 10",
        "neck_edging_stitch": "Seed Stitch",
        "neckline_style": SDC.NECK_BOAT,
        "sleeve_length": None,
        "sleeve_shape": None,
        "torso_length": SDC.TUNIC_LENGTH,
    },
    "Test 11": {
        "button_band_allowance": 1,
        "button_band_edging_height": 1,
        "button_band_edging_stitch": "Icord Stitch",
        "garment_fit": SDC.FIT_HOURGLASS_RELAXED,
        "garment_type": SDC.CARDIGAN_SLEEVED,
        "hip_edging_stitch": "1x1 Ribbing",
        "name": "Test 11",
        "neck_edging_stitch": "1x1 Ribbing",
        "neckline_style": SDC.NECK_SCOOP,
        "number_of_buttons": 6,
        "sleeve_edging_stitch": "1x1 Ribbing",
        "sleeve_length": SDC.SLEEVE_FULL,
        "sleeve_shape": SDC.SLEEVE_TAPERED,
        "torso_length": SDC.MED_HIP_LENGTH,
    },
    "Test 2": {
        "armhole_edging_height": 0.5,
        "armhole_edging_stitch": "Other Stitch",
        "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
        "garment_type": SDC.PULLOVER_VEST,
        "hip_edging_stitch": "Other Stitch",
        "name": "Test 2",
        "neck_edging_stitch": "Other Stitch",
        "neckline_style": SDC.NECK_CREW,
        "sleeve_length": None,
        "sleeve_shape": None,
        "torso_length": SDC.HIGH_HIP_LENGTH,
    },
    "Test 3": {
        "garment_fit": SDC.FIT_HOURGLASS_RELAXED,
        "garment_type": SDC.PULLOVER_SLEEVED,
        "hip_edging_stitch": "Folded hem",
        "name": "Test 3",
        "neck_edging_stitch": "2x2 Ribbing",
        "neckline_style": SDC.NECK_SCOOP,
        "sleeve_edging_stitch": "Folded hem",
        "sleeve_length": SDC.SLEEVE_ELBOW,
        "sleeve_shape": SDC.SLEEVE_STRAIGHT,
        "torso_length": SDC.LOW_HIP_LENGTH,
    },
    "Test 4": {
        "armhole_edging_height": 0.5,
        "armhole_edging_stitch": "Icord Stitch",
        "button_band_allowance": 1,
        "button_band_edging_height": 1,
        "button_band_edging_stitch": "Icord Stitch",
        "garment_fit": SDC.FIT_HOURGLASS_TIGHT,
        "garment_type": SDC.CARDIGAN_VEST,
        "hip_edging_stitch": "Other Stitch",
        "name": "Test 4",
        "neck_edging_stitch": "Other Stitch",
        "neckline_style": SDC.NECK_VEE,
        "number_of_buttons": 6,
        "sleeve_length": None,
        "sleeve_shape": None,
        "torso_length": SDC.TUNIC_LENGTH,
    },
    "Test 5": {
        "button_band_allowance": 1,
        "button_band_edging_height": 1,
        "button_band_edging_stitch": "1x1 Ribbing",
        "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
        "garment_type": SDC.CARDIGAN_SLEEVED,
        "hip_edging_stitch": "1x1 Ribbing",
        "name": "Test 5",
        "neck_edging_stitch": "1x1 Ribbing",
        "neckline_style": SDC.NECK_CREW,
        "number_of_buttons": 6,
        "sleeve_edging_stitch": "1x1 Ribbing",
        "sleeve_length": SDC.SLEEVE_THREEQUARTER,
        "sleeve_shape": SDC.SLEEVE_TAPERED,
        "torso_length": SDC.MED_HIP_LENGTH,
    },
    "Test 6": {
        "armhole_edging_height": 0.5,
        "armhole_edging_stitch": "1x1 Ribbing",
        "button_band_allowance": 1,
        "button_band_edging_height": 1,
        "button_band_edging_stitch": "1x1 Ribbing",
        "garment_fit": SDC.FIT_HOURGLASS_RELAXED,
        "garment_type": SDC.CARDIGAN_VEST,
        "hip_edging_stitch": "1x1 Ribbing",
        "name": "Test 6",
        "neck_edging_stitch": "1x1 Ribbing",
        "neckline_style": SDC.NECK_SCOOP,
        "number_of_buttons": 6,
        "sleeve_length": None,
        "sleeve_shape": None,
        "torso_length": SDC.LOW_HIP_LENGTH,
    },
    "Test 7": {
        "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
        "garment_type": SDC.PULLOVER_SLEEVED,
        "hip_edging_stitch": "Folded hem",
        "name": "Test 7",
        "neck_edging_stitch": "Garter Stitch",
        "neckline_style": SDC.NECK_VEE,
        "sleeve_edging_stitch": "Folded hem",
        "sleeve_length": SDC.SLEEVE_FULL,
        "sleeve_shape": SDC.SLEEVE_STRAIGHT,
        "torso_length": SDC.HIGH_HIP_LENGTH,
    },
    "Test 8": {
        "garment_fit": SDC.FIT_HOURGLASS_RELAXED,
        "garment_type": SDC.PULLOVER_SLEEVED,
        "hip_edging_stitch": "Other Stitch",
        "name": "Test 8",
        "neck_edging_stitch": "Other Stitch",
        "neckline_style": SDC.NECK_SCOOP,
        "sleeve_edging_stitch": "Other Stitch",
        "sleeve_length": SDC.SLEEVE_ELBOW,
        "sleeve_shape": SDC.SLEEVE_TAPERED,
        "torso_length": SDC.TUNIC_LENGTH,
    },
    "Test 9": {
        "bell_type": SDC.BELL_MODERATE,
        "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
        "garment_type": SDC.PULLOVER_SLEEVED,
        "hip_edging_stitch": "Seed Stitch",
        "name": "Test 9",
        "neck_edging_stitch": "Seed Stitch",
        "neckline_style": SDC.NECK_BOAT,
        "sleeve_edging_stitch": "Seed Stitch",
        "sleeve_length": SDC.SLEEVE_THREEQUARTER,
        "sleeve_shape": SDC.SLEEVE_BELL,
        "torso_length": SDC.MED_HIP_LENGTH,
    },
}


def make_csv_designs():

    # First, make the stiches in the designs
    stitches = {
        "1x1 Ribbing": StitchFactory(
            name="1x1 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Folded hem": StitchFactory(
            name="Folded hem",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Seed Stitch": StitchFactory(
            name="Seed Stitch",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Other Stitch": StitchFactory(
            name="Other Stitch",
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=False,
        ),
        "Icord Stitch": StitchFactory(
            name="Icord Stitch",
            user_visible=False,
            is_waist_hem_stitch=False,
            is_sleeve_hem_stitch=False,
            is_neckline_hem_stitch=False,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Daisy Stitch": StitchFactory(
            name="Daisy Stitch",
            user_visible=True,
            repeats_x_mod=1,
            repeats_mod_y=4,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Garter Stitch": StitchFactory(
            name="Garter Stitch",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Open Mesh Lace": StitchFactory(
            name="Open Mesh Lace",
            user_visible=True,
            repeats_x_mod=0,
            repeats_mod_y=3,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=False,
        ),
        "Reverse Stockinette": StitchFactory(
            name="Reverse Stockinette",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "Twisted 1x1 Ribbing": StitchFactory(
            name="Twisted 1x1 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
        ),
        "2x2 Ribbing": StitchFactory(
            name="2x2 Ribbing",
            user_visible=True,
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=False,
        ),
    }

    csv_designs = copy.deepcopy(_csv_designs)
    for design in list(csv_designs.values()):
        for field in [
            "hip_edging_stitch",
            "neck_edging_stitch",
            "sleeve_edging_stitch",
            "armhole_edging_stitch",
            "button_band_edging_stitch",
        ]:
            if field in design:
                old_val = design[field]
                if old_val is not None:
                    new_val = stitches[old_val]
                    design[field] = new_val
    return csv_designs
