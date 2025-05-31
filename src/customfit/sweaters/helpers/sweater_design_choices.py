from django.utils.safestring import mark_safe

# Fits for hourglass designs

FIT_HOURGLASS_TIGHT = "FIT_HOURGLASS_TIGHT"
FIT_HOURGLASS_AVERAGE = "FIT_HOURGLASS_AVERAGE"
FIT_HOURGLASS_RELAXED = "FIT_HOURGLASS_RELAXED"
FIT_HOURGLASS_OVERSIZED = "FIT_HOURGLASS_OVERSIZED"

# Fits for non-hourglass designs

FIT_WOMENS_TIGHT = "FIT_WOMENS_TIGHT"
FIT_WOMENS_AVERAGE = "FIT_WOMENS_AVERAGE"
FIT_WOMENS_RELAXED = "FIT_WOMENS_RELAXED"
FIT_WOMENS_OVERSIZED = "FIT_WOMENS_OVERSIZED"

FIT_MENS_TIGHT = "FIT_MENS_TIGHT"
FIT_MENS_AVERAGE = "FIT_MENS_AVERAGE"
FIT_MENS_RELAXED = "FIT_MENS_RELAXED"
FIT_MENS_OVERSIZED = "FIT_MENS_OVERSIZED"

FIT_CHILDS_TIGHT = "FIT_CHILDS_TIGHT"
FIT_CHILDS_AVERAGE = "FIT_CHILDS_AVERAGE"
FIT_CHILDS_RELAXED = "FIT_CHILDS_RELAXED"
FIT_CHILDS_OVERSIZED = "FIT_CHILDS_OVERSIZED"

FIT_HOURGLASS = [
    FIT_HOURGLASS_TIGHT,
    FIT_HOURGLASS_AVERAGE,
    FIT_HOURGLASS_RELAXED,
    FIT_HOURGLASS_OVERSIZED,
]
FIT_WOMENS = [
    FIT_WOMENS_TIGHT,
    FIT_WOMENS_AVERAGE,
    FIT_WOMENS_RELAXED,
    FIT_WOMENS_OVERSIZED,
]
FIT_MENS = [FIT_MENS_TIGHT, FIT_MENS_AVERAGE, FIT_MENS_RELAXED, FIT_MENS_OVERSIZED]
FIT_CHILDS = [
    FIT_CHILDS_TIGHT,
    FIT_CHILDS_AVERAGE,
    FIT_CHILDS_RELAXED,
    FIT_CHILDS_OVERSIZED,
]

FITS = FIT_WOMENS + FIT_MENS + FIT_CHILDS + FIT_HOURGLASS

GARMENT_FIT_CHOICES_HOURGLASS = [
    (FIT_HOURGLASS_TIGHT, "Hourglass close fit"),
    (FIT_HOURGLASS_AVERAGE, "Hourglass average fit"),
    (FIT_HOURGLASS_RELAXED, "Hourglass relaxed fit"),
    (FIT_HOURGLASS_OVERSIZED, "Hourglass oversized fit"),
]

GARMENT_FIT_CHOICES_NON_HOURGLASS = [
    (FIT_WOMENS_TIGHT, "Women's close fit"),
    (FIT_WOMENS_AVERAGE, "Women's average fit"),
    (FIT_WOMENS_RELAXED, "Women's relaxed fit"),
    (FIT_WOMENS_OVERSIZED, "Women's oversized fit"),
    (FIT_MENS_TIGHT, "Men's close fit"),
    (FIT_MENS_AVERAGE, "Men's average fit"),
    (FIT_MENS_RELAXED, "Men's relaxed fit"),
    (FIT_MENS_OVERSIZED, "Men's oversized fit"),
    (FIT_CHILDS_TIGHT, "Children's close fit"),
    (FIT_CHILDS_AVERAGE, "Children's average fit"),
    (FIT_CHILDS_RELAXED, "Children's relaxed fit"),
    (FIT_CHILDS_OVERSIZED, "Children's oversized fit"),
]

GARMENT_FIT_CHOICES = GARMENT_FIT_CHOICES_HOURGLASS + GARMENT_FIT_CHOICES_NON_HOURGLASS

GARMENT_FIT_USER_TEXT = {id: text for (id, text) in GARMENT_FIT_CHOICES}

PULLOVER_SLEEVED = "PULLOVER_SLEEVED"
PULLOVER_VEST = "PULLOVER_VEST"
CARDIGAN_SLEEVED = "CARDIGAN_SLEEVED"
CARDIGAN_VEST = "CARDIGAN_VEST"
ALL_PIECES = "ALL_PIECES"

GARMENT_TYPE_CHOICES = [
    (PULLOVER_SLEEVED, "Sleeved pullover"),
    (PULLOVER_VEST, "Pullover vest"),
    (CARDIGAN_SLEEVED, "Sleeved cardigan"),
    (CARDIGAN_VEST, "Cardigan vest"),
    (ALL_PIECES, "All pieces"),
]


SILHOUETTE_HOURGLASS = "SILHOUETTE_HOURGLASS"
SILHOUETTE_ALINE = "SILHOUETTE_ALINE"
SILHOUETTE_STRAIGHT = "SILHOUETTE_STRAIGHT"
SILHOUETTE_TAPERED = "SILHOUETTE_TAPERED"
SILHOUETTE_HALF_HOURGLASS = "SILHOUETTE_HALFGLASS"

# Choices available for the database field.
SILHOUETTE_CHOICES = [
    (SILHOUETTE_HOURGLASS, "Hourglass silhouette"),
    (SILHOUETTE_HALF_HOURGLASS, "Half-hourglass silhouette"),
    (SILHOUETTE_ALINE, "A-line silhouette"),
    (SILHOUETTE_STRAIGHT, "Straight silhouette"),
    (SILHOUETTE_TAPERED, "Tapered silhouette"),
]

SILHOUETTE_TO_SHORT_NAME = {
    SILHOUETTE_STRAIGHT: "straight",
    SILHOUETTE_HOURGLASS: "hourglass",
    SILHOUETTE_TAPERED: "tapered",
    SILHOUETTE_ALINE: "aline",
    SILHOUETTE_HALF_HOURGLASS: "halfhourglass",
}

# Silhouettes we're actually supporting in CF right now.
SUPPORTED_SILHOUETTES = [
    (SILHOUETTE_HOURGLASS, "Hourglass silhouette"),
    (SILHOUETTE_STRAIGHT, "Straight silhouette"),
    (SILHOUETTE_ALINE, "A-line silhouette"),
    (SILHOUETTE_TAPERED, "Tapered silhouette"),
    (SILHOUETTE_HALF_HOURGLASS, "Half-hourglass silhouette"),
]

SILHOUETTE_USER_TEXT = {id: text for (id, text) in SILHOUETTE_CHOICES}


CONSTRUCTION_SET_IN_SLEEVE = "setinsleeve"
CONSTRUCTION_DROP_SHOULDER = "dropshoulder"
CONSTRUCTION_RAGLAN = "raglan"

# Choices available for the database field.
CONSTRUCTION_CHOICES = [
    (CONSTRUCTION_SET_IN_SLEEVE, "set-in sleeve"),
    (CONSTRUCTION_DROP_SHOULDER, "drop-shoulder"),
]

SUPPORTED_CONSTRUCTIONS = [
    (CONSTRUCTION_SET_IN_SLEEVE, "set-in sleeve"),
    (CONSTRUCTION_DROP_SHOULDER, "drop-shoulder"),
]


CONSTRUCTION_TO_SHORT_NAME = {
    CONSTRUCTION_SET_IN_SLEEVE: "setinsleeve",
    CONSTRUCTION_DROP_SHOULDER: "dropshoulder",
}

DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW = "shallowdepth"
DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE = "averagedepth"
DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_DEEP = "deepdepth"

DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES = [
    (DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW, "shallow"),
    (DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE, "average"),
    (DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_DEEP, "deep"),
]

DROP_SHOULDER_ARMHOLE_DEPTH_CHOICES = DROP_SHOULDER_USER_VISIBLE_ARMHOLE_DEPTH_CHOICES


SLEEVE_TAPERED = "SLEEVE_TAPERED"
SLEEVE_STRAIGHT = "SLEEVE_STRAIGHT"
SLEEVE_BELL = "SLEEVE_BELL"

SLEEVE_SHAPE_CHOICES = [
    (SLEEVE_TAPERED, "Tapered sleeve"),
    (SLEEVE_STRAIGHT, "Straight sleeve"),
    (SLEEVE_BELL, "Bell sleeve"),
]

SLEEVE_SHAPE_SHORT_FORMS = {
    SLEEVE_TAPERED: "Tapered",
    SLEEVE_STRAIGHT: "Straight",
    SLEEVE_BELL: "Bell",
}

BELL_SLIGHT = "BELL_SLIGHT"
BELL_MODERATE = "BELL_MODERATE"
BELL_EXTREME = "BELL_EXTREME"

BELL_TYPE_CHOICES = [
    (BELL_SLIGHT, "Slight bell"),
    (BELL_MODERATE, "Moderate bell"),
    (BELL_EXTREME, "Extreme bell"),
]

BELL_TYPE_SHORT_FORMS = {
    BELL_SLIGHT: "Slight",
    BELL_MODERATE: "Moderate",
    BELL_EXTREME: "Extreme",
}

SLEEVE_SHORT = "SLEEVE_SHORT"
SLEEVE_ELBOW = "SLEEVE_ELBOW"
SLEEVE_THREEQUARTER = "SLEEVE_THREEQUARTER"
SLEEVE_FULL = "SLEEVE_FULL"

SLEEVE_LENGTHS = [
    # Format: (unique string, long display string, short display string)
    (SLEEVE_SHORT, "Short sleeve", "Short"),
    (SLEEVE_ELBOW, "Elbow-length sleeve", "Elbow-length"),
    (SLEEVE_THREEQUARTER, "Three-quarter length sleeve", "Three-quarter-length"),
    (SLEEVE_FULL, "Full-length sleeve", "Full-length"),
]


SLEEVE_LENGTH_CHOICES = [(id, longform) for (id, longform, _) in SLEEVE_LENGTHS]

# used in templates
SLEEVE_LENGTH_SHORT_FORMS = {id: shortform for (id, _, shortform) in SLEEVE_LENGTHS}

SLEEVE_LENGTH_CUSTOM_FORM = {
    SLEEVE_SHORT: "Short",
    SLEEVE_ELBOW: "Elbow",
    SLEEVE_THREEQUARTER: mark_safe("&frac34;"),  # HTML 3/4 character
    SLEEVE_FULL: "Long",
}

NECK_VEE = "NECK_VEE"
NECK_CREW = "NECK_CREW"
NECK_SCOOP = "NECK_SCOOP"
NECK_BACK = "NECK_BACK"
NECK_BOAT = "NECK_BOAT"
NECK_TURKS_AND_CAICOS = "NECK_TURKS"

# NOTE: NECK_BACK intentionally omitted
USER_VISIBLE_NECKLINE_STYLE_CHOICES = [
    (NECK_VEE, "Vee neck"),
    (NECK_CREW, "Crew neck"),
    (NECK_SCOOP, "Scoop neck"),
    (NECK_BOAT, "Boat neck"),
]
DESIGNER_ONLY_NECKLINE_STYLE_CHOICES = [
    # the Turks and Caicos neck should never be made visible to users
    # as it only works for pullovers and requires certain neck-depths and
    # -widths. See the TurksAndCaicosNeck model for more information
    (NECK_TURKS_AND_CAICOS, "Turks and Caicos neck")
]

NECKLINE_STYLE_CHOICES = (
    USER_VISIBLE_NECKLINE_STYLE_CHOICES + DESIGNER_ONLY_NECKLINE_STYLE_CHOICES
)


NECKLINE_STYLE_CUSTOM_FORM = {
    NECK_VEE: "Vee",
    NECK_CREW: "Crew",
    NECK_SCOOP: "Scoop",
    NECK_BOAT: "Boat",
    NECK_TURKS_AND_CAICOS: "Turks and Caicos",
}

NECK_NARROW = "NECK_NARROW"
NECK_AVERAGE = "NECK_AVERAGE"
NECK_WIDE = "NECK_WIDE"
NECK_OTHERWIDTH = "NECK_OTHERWIDTH"

NECKLINE_WIDTHS = [
    # format: (Unique ID, long form, short form)
    (NECK_NARROW, "Narrow-width neck", "Narrow-width"),
    (NECK_AVERAGE, "Average-width neck", "Average-width"),
    (NECK_WIDE, "Wide neck", "Wide"),
    (NECK_OTHERWIDTH, "Custom-width neck", "Custom-width"),
]

NECKLINE_WIDTH_CHOICES = [(id, long_form) for (id, long_form, _) in NECKLINE_WIDTHS]

NECKLINE_WIDTHS_SHORT_FORMS = {id: shortform for (id, _, shortform) in NECKLINE_WIDTHS}


# neckline orientations
BELOW_SHOULDERS = "BELOW_SHOULDERS"
BELOW_ARMPIT = "BELOW_ARMPIT"
ABOVE_ARMPIT = "ABOVE_ARMPIT"

NECKLINE_DEPTH_ORIENTATION_CHOICES = [
    (BELOW_SHOULDERS, "Below shoulders"),
    (ABOVE_ARMPIT, "Above armhole-shaping start"),
    (BELOW_ARMPIT, "Below armhole-shaping start"),
]


HIGH_HIP_LENGTH = "high_hip_length"
MED_HIP_LENGTH = "med_hip_length"
LOW_HIP_LENGTH = "low_hip_length"
TUNIC_LENGTH = "tunic_length"

HIP_LENGTH_CHOICES = [
    (HIGH_HIP_LENGTH, "Short"),
    (MED_HIP_LENGTH, "Average"),
    (LOW_HIP_LENGTH, "Long"),
    (TUNIC_LENGTH, "Tunic"),
]

# Help text

HELP_TEXT = {
    SLEEVE_SHORT: 'Sleeves will be your very own "short sleeve" length. '
    "Note! Short sleeves are typically not long enough "
    'for any shape but "straight".',
    SLEEVE_ELBOW: 'Sleeves will be your very own "elbow" length; typically just '
    "above the bend in your elbow.",
    SLEEVE_THREEQUARTER: 'Sleeves will be your very own "three-quarter" length; '
    "typically near the middle of your forearm.",
    SLEEVE_FULL: 'Sleeves will be your very own "long" length. '
    "Sleeve shape: Tapered sleeves are smaller at the cast-on "
    "than at the bicep. Straight sleeves are the same width for "
    "the entire length. Bell sleeves are wider at the cast-on than the bicep.",
    NECK_VEE: "Neck stitches are removed evenly along the entire neck depth. "
    'Typically at least 5"/12.5 cm below the shoulders.',
    NECK_CREW: "A fairly shallow neckline with a curved shape. Typically between "
    '2 - 5" / 5 - 12.5 cm below the shoulders in depth.',
    NECK_SCOOP: 'A rounded, deep neckline. Typically at least 5" / 12.5 cm below '
    "the shoulders. (As deep as the armholes, or even deeper, is very common!)",
    NECK_BOAT: 'A shallow neckline. Works  best with "wide" neck width; typically '
    '1.5 - 3.5" / 4 - 8.5 cm below the shoulders in depth.',
    HIGH_HIP_LENGTH: 'Sweater will be your very own "high hip" length, including trim.',
    MED_HIP_LENGTH: 'Sweater will be your very own "mid hip" length, including trim.',
    LOW_HIP_LENGTH: 'Sweater will be your very own "low hip" length, including trim.',
    TUNIC_LENGTH: 'Sweater will be your very own "tunic" length, including trim.',
}
