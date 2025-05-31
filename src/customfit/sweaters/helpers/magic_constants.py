"""
Created on Jun 22, 2012

This module holds all the constants used elsewhere in the code.
"""

from .sweater_design_choices import (
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_DEEP,
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW,
    FIT_CHILDS_AVERAGE,
    FIT_CHILDS_OVERSIZED,
    FIT_CHILDS_RELAXED,
    FIT_CHILDS_TIGHT,
    FIT_HOURGLASS_AVERAGE,
    FIT_HOURGLASS_OVERSIZED,
    FIT_HOURGLASS_RELAXED,
    FIT_HOURGLASS_TIGHT,
    FIT_MENS_AVERAGE,
    FIT_MENS_OVERSIZED,
    FIT_MENS_RELAXED,
    FIT_MENS_TIGHT,
    FIT_WOMENS_AVERAGE,
    FIT_WOMENS_OVERSIZED,
    FIT_WOMENS_RELAXED,
    FIT_WOMENS_TIGHT,
)

#
# Values used in garment_parameters.py
#


# Some magic numbers, in inches
NECKDEPTH = 1
BUSTTOARMPIT = 1.5
MAXBUSTTOARMPIT = (
    5.0  # Max value we will accept (from the user) for IGP.below_armhole_straight. Note
)
# that the engine can accept a higher value-- the engine will automatically
# reduce the below_armhole_straight value if it must in order to
# achieve the desired bust shaping.
# WAISTALLOWANCE = .5


# How high the armhole shaping in sweaterback is allowed to be, as percentage of total armhole height
MAX_ARMHOLE_SHAPING_HEIGHT_PERCENTAGE = 0.35

# How wide the armhole needs to be (on each side, in inches)
MIN_ARMHOLE_WIDTH_SET_IN_SLEEVE = 1.5
MIN_ARMHOLE_WIDTH_DROP_SHOULDER = 0.5


# How much to increase armholes for drop-shoulder constructions? (in inches)
DROP_SHOULDER_ARMHOLE_DEPTH_INCHES = {
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW: 0.75,
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE: 1.5,
    DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_DEEP: 2.5,
}


# When should we use the special front-bust computation for drop shoulders?
DROP_SHOULDER_FRONT_BUST_THRESHOLDS = {
    FIT_HOURGLASS_TIGHT: 0,
    FIT_HOURGLASS_AVERAGE: 1,
    FIT_HOURGLASS_RELAXED: 3,
    FIT_HOURGLASS_OVERSIZED: 6,
    FIT_WOMENS_TIGHT: 0,
    FIT_WOMENS_AVERAGE: 1,
    FIT_WOMENS_RELAXED: 3,
    FIT_WOMENS_OVERSIZED: 6,
    FIT_MENS_TIGHT: 0,
    FIT_MENS_AVERAGE: 1,
    FIT_MENS_RELAXED: 3,
    FIT_MENS_OVERSIZED: 6,
    FIT_CHILDS_TIGHT: 0,
    FIT_CHILDS_AVERAGE: 1,
    FIT_CHILDS_RELAXED: 3,
    FIT_CHILDS_OVERSIZED: 6,
}

# How much can drop-shoulder biceps be (in inches) from the goal width (which should be the armhold vertical circ,
# or twice the armhole height) before we need to take measures to adjust the bicep?
DROP_SHOULDER_BICEP_TOLERANCE = 0.25

# Drop-shoulder necklines need to be computed from the cross-back we *would* have gotten
# from the set-in-sleeve construction. These are fixed eases to use for that purpose
CROSS_CHEST_EASE_FOR_DROP_SHOULDER_NECKLINE = 0
UPPER_TORSO_EASE_FOR_DROP_SHOULDER_NECKLINE = 2

womens_cross_chest_table = {
    22: 9.5,
    23: 9.75,
    24: 10,
    25: 10.25,
    26: 10.5,
    27: 10.75,
    28: 11,
    29: 11.25,
    30: 11.5,
    31: 11.75,
    32: 12,
    33: 12.25,
    34: 12.5,
    35: 12.75,
    36: 13,
    37: 13.25,
    38: 13.5,
    39: 13.75,
    40: 14,
    41: 14.25,
    42: 14.5,
    43: 14.75,
    44: 15,
    45: 15.5,
    46: 16,
    47: 16.25,
    48: 16.5,
    49: 16.75,
    50: 17,
    51: 17,
    52: 17,
    53: 17.25,
    54: 17.25,
    55: 17.5,
    56: 17.5,
    57: 17.75,
    58: 17.75,
    59: 18,
    60: 18,
    61: 18.25,
    62: 18.25,
    63: 18.5,
    64: 18.5,
    65: 18.75,
    66: 19,
    67: 19,
    68: 19.5,
    69: 19.75,
    70: 20,
}

mens_cross_chest_table = {k: v + 1 for k, v in list(womens_cross_chest_table.items())}

childrens_cross_chest_table = {
    k: v for k, v in list(womens_cross_chest_table.items()) if k <= 50
}


#
# Values used in back_pieces
#

BACKMARKERRATIO = float(1) / float(3)
FRONTMARKERRATIO = float(1) / float(4)
HALFWAISTEVEN = 0.5
PREUNDERARMEVEN = 1
BACKNECKLINEDEPTH = 1

ONEINCH = 1.0
HALF_INCH = 0.5


#
# Values needed by Sleeve
#

# Are these right?
ARMSCYE_C_RATIO = 0.2
ARMSCYE_D_RATIO = 0.04
MAX_ARMSCYE_Y = 1.5


# After we finish the hip-hem, how much longer must we wait before we can
# start the waist-shaiping? (in inches)
POST_HEM_MARGIN = 0.5

# How much negative ease can we tolerate before we adjust heights?
NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS = -1.0

# If we have more than NEGATIVE_EASE_THRESHOLD_FOR_LENGTHS negative ease,
# how much should we adjust heights (as a factor of the negative ease)?
NEGATIVE_EASE_LENGTH_ADJUSTMENT_FACTOR = 0.5

# If we need the waist-shaping to go down into the hem, how much hem to
# work straight, at a minimum?
MINIMUM_WAIST_STRAIGHT = 0.5


# How much room should we allow, max, body-piece shaping rows to be apart?
MAX_INCHES_BETWEEN_BODY_SHAPING_ROWS = 2.0

# How much room should we allow, max, sleeve-piece shaping rows to be apart?
MAX_INCHES_BETWEEN_SLEEVE_SHAPING_ROWS = 5.0

# When we need to shrink the wrist-edging height, how small can we go?
MINIMUM_WRIST_EDGING_HEIGHT = 0.5

# When we need to expand back hips to be as large as waist, how much bigger
# do we want the back hips to be?
FORCED_SHAPING_BACK_HIP = 0.5


# When we're in the A-line cases (caes 7 and 9) we want to move the 'waist'
# up to jsut below the bust. But how much?
ALINE_WAIST_TO_BUST = 4 - BUSTTOARMPIT

# How much room (in inches) to *ideally* leave above the top buttonhole
# and below the bottom buttonhole?
BUTTONHOLE_MARGIN_GOAL = 1.0

# How much room (in inches) MUST be left above the top buttonhole
# and below the bottom buttonhole?
BUTTONHOLE_MARGIN_MIN = 0.75

# How much distance to add to inter-nipple distances when placing the
# interior markers for horizontal bust darts?
BUST_DART_MARKER_ALLOWANCE = 1.0

# When we give instructions for horizontal bust darts, what heights should we
# give:
BUST_DART_INSTRUCTION_HEIGHTS = [0.5, 1, 1.5, 2, 3]


# When making an A-line garment, how much bigger must the cast-on circumference
# be than the bust-circumference? (in inches)
MINIMUM_ALINE_BUST_CIRC_TO_HIP_CIRC_DIFF = 6


# When making a tapered garment, how much smaller must the cast-on circumference
# be than the bust-circumference? (in inches)
MINIMUM_TAPERED_BUST_CIRC_TO_HIP_CIRC_DIFF = 4

# In the non-hourglass logic for the IndividualGarmentParameters model:
# To be put in the 'busty woman' case, how busty must the woman be? That is
# how much larger than upper-torso-circ must the bust-circ be (in inches)?
BUSTY_WOMAN_THRESHOLD = 2
