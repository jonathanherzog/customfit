"""
A central collection of schematic-image names and paths.
"""

import os.path

import customfit.sweaters.helpers.sweater_design_choices as SDC

PATH = "img/schematics/"

SET_IN_SLEEVE_PATH = "set-in-sleeve"
DROP_SHOULDER_SLEEVE_PATH = "drop-shoulder"
CONSTRUCTION_MAP = {
    SDC.CONSTRUCTION_SET_IN_SLEEVE: SET_IN_SLEEVE_PATH,
    SDC.CONSTRUCTION_DROP_SHOULDER: DROP_SHOULDER_SLEEVE_PATH,
}

HOURGLASS_PREFIX = "Hourglass-"
STRAIGHT_PREFIX = "Straight-"
ALINE_PREFIX = "A-Line-"
TAPERED_PREFIX = "Tapered-"
SILHOUETTE_MAP = {
    SDC.SILHOUETTE_HOURGLASS: HOURGLASS_PREFIX,
    SDC.SILHOUETTE_STRAIGHT: STRAIGHT_PREFIX,
    SDC.SILHOUETTE_ALINE: ALINE_PREFIX,
    SDC.SILHOUETTE_TAPERED: TAPERED_PREFIX,
}

BACK_PIECE = "Back.png"

PULLOVER_VEE = "Front-Pullover-V.png"
PULLOVER_CREW = "Front-Pullover-Crew.png"
PULLOVER_SCOOP = "Front-Pullover-Scoop.png"
PULLOVER_BOAT = "Front-Pullover-Boat.png"
PULLOVER_TURKS = "Front-Pullover-Turks.png"
PULLOVER_MAP = {
    SDC.NECK_VEE: PULLOVER_VEE,
    SDC.NECK_CREW: PULLOVER_CREW,
    SDC.NECK_SCOOP: PULLOVER_SCOOP,
    SDC.NECK_BOAT: PULLOVER_BOAT,
    SDC.NECK_TURKS_AND_CAICOS: PULLOVER_TURKS,
}

CARDI_VEE = "Front-Cardi-V.png"
CARDI_CREW = "Front-Cardi-Crew.png"
CARDI_SCOOP = "Front-Cardi-Scoop.png"
CARDI_BOAT = "Front-Cardi-Boat.png"
CARDI_MAP = {
    SDC.NECK_VEE: CARDI_VEE,
    SDC.NECK_CREW: CARDI_CREW,
    SDC.NECK_SCOOP: CARDI_SCOOP,
    SDC.NECK_BOAT: CARDI_BOAT,
}


SLEEVE_FULL = "Long-Sleeve.png"
SLEEVE_THREEQUARTER = "3-4-Sleeve.png"
SLEEVE_ELBOW = "Elbow-Sleeve.png"
SLEEVE_SHORT = "Short-Sleeve.png"
SLEEVE_LENGTH_MAP = {
    SDC.SLEEVE_SHORT: SLEEVE_SHORT,
    SDC.SLEEVE_THREEQUARTER: SLEEVE_THREEQUARTER,
    SDC.SLEEVE_ELBOW: SLEEVE_ELBOW,
    SDC.SLEEVE_FULL: SLEEVE_FULL,
}


def get_back_schematic_url(silhouette, construction):
    cons_path = CONSTRUCTION_MAP[construction]
    sil_prefix = SILHOUETTE_MAP[silhouette]
    return os.path.join(PATH, cons_path, sil_prefix + BACK_PIECE)


def get_sleeve_schematic_url(length, construction):
    cons_path = CONSTRUCTION_MAP[construction]
    length_file = SLEEVE_LENGTH_MAP[length]
    return os.path.join(PATH, cons_path, length_file)


def get_front_schematic_url(
    silhouette, neckline_style, construction, cardigan=False, empty=False
):
    cons_path = CONSTRUCTION_MAP[construction]
    silhouette_prefix = SILHOUETTE_MAP[silhouette]
    if empty:
        basename = silhouette_prefix + "Front-Cardi-Straight-Neck.png"
    else:
        if cardigan:
            basename = silhouette_prefix + CARDI_MAP[neckline_style]
        else:
            basename = silhouette_prefix + PULLOVER_MAP[neckline_style]
    return os.path.join(PATH, cons_path, basename)
