import copy

import customfit.sweaters.helpers.sweater_design_choices as SDC
from customfit.helpers.math_helpers import ROUND_DOWN, ROUND_UP

# How much ease to add for various fits. Note: defined for entire circumferences
_set_in_sleeve_hourglass_eases = {
    SDC.FIT_HOURGLASS_TIGHT: {
        "case0": {
            "upper_torso": 0.5,
            "bust": -2,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: -4,
            SDC.MED_HIP_LENGTH: -4,
            SDC.LOW_HIP_LENGTH: -4,
            SDC.TUNIC_LENGTH: 2,
        },
        "case1": {
            "upper_torso": 0.5,
            "bust": -2,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: -3,
            SDC.MED_HIP_LENGTH: -3,
            SDC.LOW_HIP_LENGTH: -3,
            SDC.TUNIC_LENGTH: 2,
        },
        "case2": {
            "upper_torso": 0,
            "bust": -1,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: -4,
            SDC.MED_HIP_LENGTH: -4,
            SDC.LOW_HIP_LENGTH: -4,
            SDC.TUNIC_LENGTH: 2,
        },
        "case3": {
            "upper_torso": 0.5,
            "bust": -1,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: -3,
            SDC.MED_HIP_LENGTH: -2,
            SDC.LOW_HIP_LENGTH: -2,
            SDC.TUNIC_LENGTH: 2,
        },
        "case4": {
            "upper_torso": 1,
            "bust": -0.5,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: -3,
            SDC.MED_HIP_LENGTH: -1.5,
            SDC.LOW_HIP_LENGTH: -1.5,
            SDC.TUNIC_LENGTH: 2,
        },
        "case5": {
            "upper_torso": 0.5,
            "bust": -1,
            "waist": 1,
            SDC.HIGH_HIP_LENGTH: -2,
            SDC.MED_HIP_LENGTH: 0,
            SDC.LOW_HIP_LENGTH: 0,
            SDC.TUNIC_LENGTH: 2,
        },
        "case6": {
            "upper_torso": 0.5,
            "bust": 0,
            "waist": 1,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 0,
            SDC.LOW_HIP_LENGTH: 0,
            SDC.TUNIC_LENGTH: 2,
        },
        "case7": {
            "upper_torso": 0.25,
            "bust": 0,
            "waist": 1,
            SDC.HIGH_HIP_LENGTH: -2,
            SDC.MED_HIP_LENGTH: -1,
            SDC.LOW_HIP_LENGTH: -1,
            SDC.TUNIC_LENGTH: 2,
        },
        "case8": {
            "upper_torso": 0.5,
            "bust": -1,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 3,
        },
        "case9": {
            "upper_torso": 1,
            "bust": 0,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 3,
        },
        "armhole_depth": -0.25,
        "bicep": 0.5,
        "cross_chest": -1,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_HOURGLASS_AVERAGE: {
        "case0": {
            "upper_torso": 1.5,
            "bust": -1,
            "waist": 5,
            SDC.HIGH_HIP_LENGTH: -3,
            SDC.MED_HIP_LENGTH: -3,
            SDC.LOW_HIP_LENGTH: -3,
            SDC.TUNIC_LENGTH: 4,
        },
        "case1": {
            "upper_torso": 1.5,
            "bust": -1,
            "waist": 5,
            SDC.HIGH_HIP_LENGTH: -2,
            SDC.MED_HIP_LENGTH: -1,
            SDC.LOW_HIP_LENGTH: -1,
            SDC.TUNIC_LENGTH: 4,
        },
        "case2": {
            "upper_torso": 1.25,
            "bust": 0,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: -3,
            SDC.MED_HIP_LENGTH: -3,
            SDC.LOW_HIP_LENGTH: -3,
            SDC.TUNIC_LENGTH: 4,
        },
        "case3": {
            "upper_torso": 1.25,
            "bust": -1,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: -2,
            SDC.MED_HIP_LENGTH: -1,
            SDC.LOW_HIP_LENGTH: -1,
            SDC.TUNIC_LENGTH: 4,
        },
        "case4": {
            "upper_torso": 1.5,
            "bust": 0.5,
            "waist": 2.5,
            SDC.HIGH_HIP_LENGTH: -1,
            SDC.MED_HIP_LENGTH: 0,
            SDC.LOW_HIP_LENGTH: 0,
            SDC.TUNIC_LENGTH: 4,
        },
        "case5": {
            "upper_torso": 1,
            "bust": -1,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 4,
        },
        "case6": {
            "upper_torso": 1.5,
            "bust": 2,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 4,
        },
        "case7": {
            "upper_torso": 1,
            "bust": 0,
            "waist": 2,
            SDC.HIGH_HIP_LENGTH: 0,
            SDC.MED_HIP_LENGTH: 0,
            SDC.LOW_HIP_LENGTH: 0,
            SDC.TUNIC_LENGTH: 4,
        },
        "case8": {
            "upper_torso": 1.25,
            "bust": 0,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 4,
        },
        "case9": {
            "upper_torso": 1.5,
            "bust": 1,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 1,
            SDC.LOW_HIP_LENGTH: 1,
            SDC.TUNIC_LENGTH: 4,
        },
        "armhole_depth": 0,
        "bicep": 1.25,
        "cross_chest": 0,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_HOURGLASS_RELAXED: {
        "case0": {
            "upper_torso": 2.5,
            "bust": 1,
            "waist": 6,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 1.5,
            SDC.LOW_HIP_LENGTH: 2,
            SDC.TUNIC_LENGTH: 6,
        },
        "case1": {
            "upper_torso": 2.5,
            "bust": 1,
            "waist": 5,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 2.5,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case2": {
            "upper_torso": 2.25,
            "bust": 1,
            "waist": 4,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 2,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case3": {
            "upper_torso": 2.25,
            "bust": 1,
            "waist": 4,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 2.5,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case4": {
            "upper_torso": 2.5,
            "bust": 3,
            "waist": 3.5,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 2.5,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case5": {
            "upper_torso": 2,
            "bust": 2,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: 1.5,
            SDC.MED_HIP_LENGTH: 2,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case6": {
            "upper_torso": 2.5,
            "bust": 3,
            "waist": 4,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 3,
            SDC.LOW_HIP_LENGTH: 3,
            SDC.TUNIC_LENGTH: 6,
        },
        "case7": {
            "upper_torso": 2.5,
            "bust": 2,
            "waist": 3,
            SDC.HIGH_HIP_LENGTH: 1.5,
            SDC.MED_HIP_LENGTH: 2,
            SDC.LOW_HIP_LENGTH: 2.5,
            SDC.TUNIC_LENGTH: 6,
        },
        "case8": {
            "upper_torso": 2.75,
            "bust": 2,
            "waist": 4,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 1.5,
            SDC.LOW_HIP_LENGTH: 1.5,
            SDC.TUNIC_LENGTH: 6,
        },
        "case9": {
            "upper_torso": 3,
            "bust": 3,
            "waist": 4,
            SDC.HIGH_HIP_LENGTH: 1,
            SDC.MED_HIP_LENGTH: 1.5,
            SDC.LOW_HIP_LENGTH: 1.5,
            SDC.TUNIC_LENGTH: 6,
        },
        "armhole_depth": 0.5,
        "bicep": 2,
        "cross_chest": 1,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_HOURGLASS_OVERSIZED: {
        "case0": {
            "upper_torso": 3,
            "bust": 4,
            "waist": 9,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 4.5,
            SDC.LOW_HIP_LENGTH: 5,
            SDC.TUNIC_LENGTH: 8,
        },
        "case1": {
            "upper_torso": 3,
            "bust": 4,
            "waist": 8,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 5.5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case2": {
            "upper_torso": 2.75,
            "bust": 4,
            "waist": 7,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case3": {
            "upper_torso": 2.75,
            "bust": 4,
            "waist": 7,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 5.5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case4": {
            "upper_torso": 2.75,
            "bust": 6,
            "waist": 6.5,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 5.5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case5": {
            "upper_torso": 2.5,
            "bust": 5,
            "waist": 6,
            SDC.HIGH_HIP_LENGTH: 4.5,
            SDC.MED_HIP_LENGTH: 5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case6": {
            "upper_torso": 3,
            "bust": 6,
            "waist": 7,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 6,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case7": {
            "upper_torso": 3,
            "bust": 5,
            "waist": 6,
            SDC.HIGH_HIP_LENGTH: 4.5,
            SDC.MED_HIP_LENGTH: 5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case8": {
            "upper_torso": 2.75,
            "bust": 5,
            "waist": 7,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 4.5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "case9": {
            "upper_torso": 3.5,
            "bust": 6,
            "waist": 7,
            SDC.HIGH_HIP_LENGTH: 4,
            SDC.MED_HIP_LENGTH: 4.5,
            SDC.LOW_HIP_LENGTH: 6,
            SDC.TUNIC_LENGTH: 8,
        },
        "armhole_depth": 0.75,
        "bicep": 2.5,
        "cross_chest": 1.5,
        SDC.SLEEVE_SHORT: 0.75,
        SDC.SLEEVE_ELBOW: 0.75,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
}


_set_in_sleeve_non_hourglass_shared_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "upper_torso": 0.5,
        "bust": -2,
        "armhole_depth": -0.25,
        "bicep": 0.5,
        "cross_chest": 0,
        SDC.SLEEVE_SHORT: -0.5,
        SDC.SLEEVE_ELBOW: -0.5,
        SDC.SLEEVE_THREEQUARTER: -0.5,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "upper_torso": 1.5,
        "bust": 0,
        "armhole_depth": 0,
        "bicep": 1.25,
        "cross_chest": 1,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "upper_torso": 2.25,
        "bust": 2,
        "armhole_depth": 0.25,
        "bicep": 2,
        "cross_chest": 1.5,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 0.5,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "upper_torso": 3,
        "bust": 4,
        "armhole_depth": 0.5,
        "bicep": 3,
        "cross_chest": 2,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4.5,
    },
    SDC.FIT_MENS_TIGHT: {
        "upper_torso": 2,
        "bust": 2,
        "armhole_depth": 0,
        "bicep": 2,
        "cross_chest": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_MENS_AVERAGE: {
        "upper_torso": 4,
        "bust": 4,
        "armhole_depth": 0,
        "bicep": 3.5,
        "cross_chest": 1,
        SDC.SLEEVE_SHORT: 1,
        SDC.SLEEVE_ELBOW: 1,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_MENS_RELAXED: {
        "upper_torso": 6,
        "bust": 6,
        "armhole_depth": 0.25,
        "bicep": 4,
        "cross_chest": 1.5,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "upper_torso": 8,
        "bust": 8,
        "armhole_depth": 0.5,
        "bicep": 5,
        "cross_chest": 2,
        SDC.SLEEVE_SHORT: 3,
        SDC.SLEEVE_ELBOW: 3,
        SDC.SLEEVE_THREEQUARTER: 3,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "upper_torso": 2,
        "bust": 2,
        "armhole_depth": 0,
        "bicep": 2,
        "cross_chest": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "upper_torso": 3,
        "bust": 4,
        "armhole_depth": 0,
        "bicep": 3,
        "cross_chest": 1,
        SDC.SLEEVE_SHORT: 1,
        SDC.SLEEVE_ELBOW: 1,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 2.5,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "upper_torso": 4,
        "bust": 6,
        "armhole_depth": 0.25,
        "bicep": 4,
        "cross_chest": 1.5,
        SDC.SLEEVE_SHORT: 1.5,
        SDC.SLEEVE_ELBOW: 1.5,
        SDC.SLEEVE_THREEQUARTER: 1.5,
        SDC.SLEEVE_FULL: 3.5,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "upper_torso": 5,
        "bust": 8,
        "armhole_depth": 0.5,
        "bicep": 5,
        "cross_chest": 2,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
}

_set_in_sleeve_straight_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": 0,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": 2,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 4,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 6,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 2,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 4,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 6,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 8,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": 2,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 4,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 6,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 8,
    },
}
for fit, eases in list(_set_in_sleeve_non_hourglass_shared_eases.items()):
    _set_in_sleeve_straight_eases[fit].update(eases)
    _set_in_sleeve_straight_eases[fit]["waist"] = _set_in_sleeve_straight_eases[fit][
        "cast_on"
    ]


_set_in_sleeve_aline_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": 4,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": 6,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 8,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 10,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 4,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 6,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 8,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 10,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": 2,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 4,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 6,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 8,
    },
}
for fit, eases in list(_set_in_sleeve_non_hourglass_shared_eases.items()):
    _set_in_sleeve_aline_eases[fit].update(eases)
    _set_in_sleeve_aline_eases[fit]["waist"] = _set_in_sleeve_aline_eases[fit][
        "cast_on"
    ]


_set_in_sleeve_tapered_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": -4,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": -2,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 0,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 2,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 0,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 1,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 1.5,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 2.5,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": -1,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 0,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 1,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 1.5,
    },
}
for fit, eases in list(_set_in_sleeve_non_hourglass_shared_eases.items()):
    _set_in_sleeve_tapered_eases[fit].update(eases)
    _set_in_sleeve_tapered_eases[fit]["waist"] = _set_in_sleeve_tapered_eases[fit][
        "cast_on"
    ]


_set_in_sleeve_eases = {
    SDC.SILHOUETTE_HOURGLASS: _set_in_sleeve_hourglass_eases,
    SDC.SILHOUETTE_HALF_HOURGLASS: _set_in_sleeve_hourglass_eases,
    SDC.SILHOUETTE_STRAIGHT: _set_in_sleeve_straight_eases,
    SDC.SILHOUETTE_ALINE: _set_in_sleeve_aline_eases,
    SDC.SILHOUETTE_TAPERED: _set_in_sleeve_tapered_eases,
}


_drop_shoulder_hourglass_eases = {
    SDC.FIT_HOURGLASS_TIGHT: {
        "case0": {"bust": 4, "waist": 12, "hip": 4},
        "case1": {"bust": 4, "waist": 12, "hip": 9},
        "case2": {"bust": 9, "waist": 12, "hip": 4},
        "case3": {"bust": 4, "waist": 7, "hip": 4},
        "case4": {"bust": 4, "waist": 4, "hip": 4},
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_HOURGLASS_AVERAGE: {
        "case0": {"bust": 6, "waist": 14, "hip": 6},
        "case1": {"bust": 6, "waist": 14, "hip": 11},
        "case2": {"bust": 11, "waist": 14, "hip": 6},
        "case3": {"bust": 6, "waist": 9, "hip": 6},
        "case4": {"bust": 6, "waist": 6, "hip": 6},
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_HOURGLASS_RELAXED: {
        "case0": {"bust": 9, "waist": 17, "hip": 9},
        "case1": {"bust": 9, "waist": 17, "hip": 14},
        "case2": {"bust": 14, "waist": 17, "hip": 9},
        "case3": {"bust": 9, "waist": 12, "hip": 9},
        "case4": {"bust": 9, "waist": 9, "hip": 9},
        "armhole_depth": 0.5,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_HOURGLASS_OVERSIZED: {
        "case0": {"bust": 12, "waist": 20, "hip": 12},
        "case1": {"bust": 12, "waist": 20, "hip": 17},
        "case2": {"bust": 17, "waist": 20, "hip": 12},
        "case3": {"bust": 12, "waist": 15, "hip": 1},
        "case4": {"bust": 12, "waist": 12, "hip": 12},
        "armhole_depth": 0.75,
        SDC.SLEEVE_SHORT: 0.75,
        SDC.SLEEVE_ELBOW: 0.75,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
}

_drop_shoulder_non_hourglass_shared_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "bust": 4,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: -0.5,
        SDC.SLEEVE_ELBOW: -0.5,
        SDC.SLEEVE_THREEQUARTER: -0.5,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "bust": 6,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "bust": 9,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 0.5,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "bust": 12,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_MENS_TIGHT: {
        "bust": 4,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_MENS_AVERAGE: {
        "bust": 8,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 1,
        SDC.SLEEVE_ELBOW: 1,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 3,
    },
    SDC.FIT_MENS_RELAXED: {
        "bust": 12,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "bust": 16,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 3,
        SDC.SLEEVE_ELBOW: 3,
        SDC.SLEEVE_THREEQUARTER: 3,
        SDC.SLEEVE_FULL: 4,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "bust": 4,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 0,
        SDC.SLEEVE_ELBOW: 0,
        SDC.SLEEVE_THREEQUARTER: 0,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "bust": 6,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 1,
        SDC.SLEEVE_ELBOW: 1,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 2.5,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "bust": 10,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 1.5,
        SDC.SLEEVE_ELBOW: 1.5,
        SDC.SLEEVE_THREEQUARTER: 1.5,
        SDC.SLEEVE_FULL: 3.5,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "bust": 14,
        "armhole_depth": 0,
        SDC.SLEEVE_SHORT: 2,
        SDC.SLEEVE_ELBOW: 2,
        SDC.SLEEVE_THREEQUARTER: 2,
        SDC.SLEEVE_FULL: 4,
    },
}

_drop_shoulder_straight_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": 4,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": 6,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 9,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 12,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 4,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 8,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 12,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 16,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": 4,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 6,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 10,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 14,
    },
}
for fit, eases in list(_drop_shoulder_non_hourglass_shared_eases.items()):
    _drop_shoulder_straight_eases[fit].update(eases)
    _drop_shoulder_straight_eases[fit]["waist"] = _drop_shoulder_straight_eases[fit][
        "bust"
    ]


_drop_shoulder_aline_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": 12,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": 15,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 18,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 20,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 10,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 14,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 16,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 20,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": 10,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 12,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 16,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 20,
    },
}
for fit, eases in list(_drop_shoulder_non_hourglass_shared_eases.items()):
    _drop_shoulder_aline_eases[fit].update(eases)
    _drop_shoulder_aline_eases[fit]["waist"] = _drop_shoulder_aline_eases[fit]["bust"]


_drop_shoulder_tapered_eases = {
    SDC.FIT_WOMENS_TIGHT: {
        "cast_on": -2,
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "cast_on": 0,
    },
    SDC.FIT_WOMENS_RELAXED: {
        "cast_on": 3,
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "cast_on": 6,
    },
    SDC.FIT_MENS_TIGHT: {
        "cast_on": 2,
    },
    SDC.FIT_MENS_AVERAGE: {
        "cast_on": 3,
    },
    SDC.FIT_MENS_RELAXED: {
        "cast_on": 3.5,
    },
    SDC.FIT_MENS_OVERSIZED: {
        "cast_on": 4.5,
    },
    SDC.FIT_CHILDS_TIGHT: {
        "cast_on": 1,
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "cast_on": 2,
    },
    SDC.FIT_CHILDS_RELAXED: {
        "cast_on": 3,
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "cast_on": 4.5,
    },
}
for fit, eases in list(_drop_shoulder_non_hourglass_shared_eases.items()):
    _drop_shoulder_tapered_eases[fit].update(eases)
    _drop_shoulder_tapered_eases[fit]["waist"] = _drop_shoulder_tapered_eases[fit][
        "bust"
    ]


_drop_shoulder_eases = {
    SDC.SILHOUETTE_HOURGLASS: _drop_shoulder_hourglass_eases,
    SDC.SILHOUETTE_HALF_HOURGLASS: _drop_shoulder_hourglass_eases,
    SDC.SILHOUETTE_STRAIGHT: _drop_shoulder_straight_eases,
    SDC.SILHOUETTE_ALINE: _drop_shoulder_aline_eases,
    SDC.SILHOUETTE_TAPERED: _drop_shoulder_tapered_eases,
}


def get_eases(fit, silhouette, construction, case=None):
    if construction == SDC.CONSTRUCTION_SET_IN_SLEEVE:
        return_me = copy.deepcopy(_set_in_sleeve_eases[silhouette][fit])
        if case is not None:
            return_me = return_me[case]
        return copy.copy(return_me)
    else:
        assert construction == SDC.CONSTRUCTION_DROP_SHOULDER
        return_me = copy.deepcopy(_drop_shoulder_eases[silhouette][fit])
        if case is not None:
            if case in ["case5", "case6", "case7", "case8", "case9"]:
                search_case = "case4"
            else:
                search_case = case
            return_me = return_me[search_case]
            if silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:
                return_me[SDC.HIGH_HIP_LENGTH] = return_me["hip"]
                return_me[SDC.MED_HIP_LENGTH] = return_me["hip"]
                return_me[SDC.LOW_HIP_LENGTH] = return_me["hip"]
                return_me[SDC.TUNIC_LENGTH] = return_me["hip"]
                return_me.pop("hip")
        if "bust" in return_me:
            return_me["upper_torso"] = return_me["bust"]
        return copy.copy(return_me)


# No one remembers what these were originally for, but we're keeping them around because (1) we may use
# them again in the future, and (2) it will be a tremendous amount of work to rip them out of everything.
ease_tolerances = {}
for fit in SDC.FITS:
    ease_tolerances[fit] = {
        "upper_torso": -float("inf"),
        "bust": -float("inf"),
        "waist": -float("inf"),
        "hips": -float("inf"),
        "bicep": -float("inf"),
        "cross_chest": -float("inf"),
        "neck_width": -float("inf"),
        SDC.SLEEVE_SHORT: -float("inf"),
        SDC.SLEEVE_ELBOW: -float("inf"),
        SDC.SLEEVE_THREEQUARTER: -float("inf"),
        SDC.SLEEVE_FULL: -float("inf"),
    }


rounding_directions = {
    SDC.FIT_HOURGLASS_TIGHT: {
        "sweater_back": {
            "cast_ons": ROUND_DOWN,
            "waist": ROUND_UP,
            "bust": ROUND_DOWN,
            "cross_chest": ROUND_DOWN,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_DOWN,
            "bust_increase_height": ROUND_DOWN,
            "neckline_pickup_stitches": ROUND_DOWN,
        },
        "sleeve": {"cast_ons": ROUND_DOWN, "bicep": ROUND_DOWN},
    },
    SDC.FIT_HOURGLASS_AVERAGE: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_DOWN,
            "bust_increase_height": ROUND_DOWN,
            "neckline_pickup_stitches": ROUND_DOWN,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_HOURGLASS_RELAXED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_DOWN,
            "bust_increase_height": ROUND_DOWN,
            "neckline_pickup_stitches": ROUND_DOWN,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_HOURGLASS_OVERSIZED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_WOMENS_TIGHT: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_WOMENS_AVERAGE: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_WOMENS_RELAXED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_WOMENS_OVERSIZED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_MENS_TIGHT: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_MENS_AVERAGE: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_MENS_RELAXED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_MENS_OVERSIZED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_CHILDS_TIGHT: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_CHILDS_AVERAGE: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_CHILDS_RELAXED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
    SDC.FIT_CHILDS_OVERSIZED: {
        "sweater_back": {
            "cast_ons": ROUND_UP,
            "waist": ROUND_UP,
            "bust": ROUND_UP,
            "cross_chest": ROUND_UP,
            "neck_width": ROUND_UP,
            "waist_decrease_height": ROUND_UP,
            "bust_increase_height": ROUND_UP,
            "neckline_pickup_stitches": ROUND_UP,
        },
        "sleeve": {"cast_ons": ROUND_UP, "bicep": ROUND_UP},
    },
}

for fit in SDC.FITS:
    for garm in ["sweater_front", "cardigan_front"]:
        rounding_directions[fit][garm] = copy.deepcopy(
            rounding_directions[fit]["sweater_back"]
        )


minimum_sleeve_straights_below_cap = {
    SDC.CONSTRUCTION_SET_IN_SLEEVE: {
        SDC.SLEEVE_SHORT: 0.25,
        SDC.SLEEVE_ELBOW: 0.25,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 2,
    },
    SDC.CONSTRUCTION_DROP_SHOULDER: {
        SDC.SLEEVE_SHORT: 0.25,
        SDC.SLEEVE_ELBOW: 0.25,
        SDC.SLEEVE_THREEQUARTER: 0.25,
        SDC.SLEEVE_FULL: 0.25,
    },
}

maximum_sleeve_straights_below_cap = {
    SDC.CONSTRUCTION_SET_IN_SLEEVE: {
        SDC.SLEEVE_SHORT: 1.5,
        SDC.SLEEVE_ELBOW: 1.5,
        SDC.SLEEVE_THREEQUARTER: 2.5,
        SDC.SLEEVE_FULL: 2.5,
    },
    SDC.CONSTRUCTION_DROP_SHOULDER: {
        SDC.SLEEVE_SHORT: 0.5,
        SDC.SLEEVE_ELBOW: 0.5,
        SDC.SLEEVE_THREEQUARTER: 1,
        SDC.SLEEVE_FULL: 1,
    },
}


# Ratio of neckline width to cross-chest measurement:
neck_width_ratio = {SDC.NECK_NARROW: 0.4, SDC.NECK_AVERAGE: 0.5, SDC.NECK_WIDE: 0.65}


bell_eases = {SDC.BELL_SLIGHT: 2, SDC.BELL_MODERATE: 4, SDC.BELL_EXTREME: 6}
