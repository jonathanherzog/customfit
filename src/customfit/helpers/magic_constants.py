"""
Created on Jun 22, 2012

This module holds all the constants used elsewhere in the code.
"""

CM_PER_INCHES = 2.54
YARDS_PER_METRE = 100.0 / (CM_PER_INCHES * 12 * 3)
OUNCES_PER_GRAM = 1.0 / 28.349523125  # definition of avoirdupois ounce


# If two schematics differ by this or less along any dimension, they can
# be considered to be the same along that dimension. That is, differences
# smaller than this can be ignored. (Measured in inches.)
SCHEMATIC_MATERIAL_DIFFERENCE = 0.5

#

# How close do two floating-point numbers need to be before we decide
# they are really the same number? I'd like something like this:
# FLOATING_POINT_NOISE = sys.float_info.epsilon * 100
# But that need python 2.6 or later. FOr now:
FLOATING_POINT_NOISE = 10**-6
