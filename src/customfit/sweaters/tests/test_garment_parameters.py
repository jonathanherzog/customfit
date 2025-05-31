"""
Created on Jul 5, 2012
"""

import copy
import csv
import os.path

import django.test
import factory
from django.core.exceptions import ValidationError

from customfit.bodies.factories import (
    BodyFactory,
    GradeFactory,
    MaleBodyFactory,
    SimpleBodyFactory,
    get_csv_body,
)
from customfit.bodies.models import Body
from customfit.stitches.factories import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ..factories import (
    GradedSweaterPatternSpecFactory,
    SweaterDesignFactory,
    SweaterGradedGarmentParametersFactory,
    SweaterGradedGarmentParametersGradeFactory,
    SweaterIndividualGarmentParametersFactory,
    SweaterPatternSpecFactory,
    VestPatternSpecFactory,
    create_csv_combo,
    make_patternspec_from_design,
)
from ..forms import TweakSweaterIndividualGarmentParameters
from ..helpers import secret_sauce
from ..helpers import sweater_design_choices as SDC
from ..models import (
    SweaterGradedGarmentParameters,
    SweaterGradedGarmentParametersGrade,
    SweaterIndividualGarmentParameters,
)

# First, make a TestCase of static tests.
#
# Then we dynamically create tests based on the tests in the CSV files.


class HourglassSilhouetteIGPTest(django.test.TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_default_individual_garment_parameters(self):
        igp = SweaterIndividualGarmentParametersFactory()
        igp.full_clean()

    def test_save_delete_default_individual_garment_parameters(self):
        igp = SweaterIndividualGarmentParametersFactory()
        igp.save()
        igp.delete()

    def test_make_from_design_and_body(self):
        igp = SweaterIndividualGarmentParametersFactory()
        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.waist_height_front, 7)
        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)

        self.assertEqual(igp.hip_width_back, 19.5)
        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        self.assertEqual(igp.hip_width_front, 19.5)
        self.assertEqual(igp.waist_width_front, 17.5)
        self.assertEqual(igp.bust_width_front, 20.375)

        self.assertEqual(igp.hip_circ_total, 39)
        self.assertEqual(igp.waist_circ_total, 35)
        self.assertEqual(igp.bust_circ_total, 40)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

        self.assertEqual(igp.front_neck_opening_width, 7 - 19.625 + 20.375)

    def test_make_from_design_and_body_without_optionals(self):
        body = BodyFactory()
        body.inter_nipple_distance = None
        body.cross_chest_distance = None
        body.full_clean()
        pattern_spec = SweaterPatternSpecFactory(body=body)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pattern_spec
        )
        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.waist_height_front, 7)
        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)

        self.assertEqual(igp.hip_width_back, 19.5)
        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        self.assertEqual(igp.hip_width_front, 19.5)
        self.assertEqual(igp.waist_width_front, 17.5)
        self.assertEqual(igp.bust_width_front, 20.375)

        self.assertEqual(igp.hip_circ_total, 39)
        self.assertEqual(igp.waist_circ_total, 35)
        self.assertEqual(igp.bust_circ_total, 40)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

        self.assertEqual(igp.front_neck_opening_width, 7 - 19.625 + 20.375)

    def test_torso_lengths1(self):
        design = SweaterPatternSpecFactory(torso_length=SDC.HIGH_HIP_LENGTH)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()
        self.assertEqual(igp.waist_height_front, 6.25)
        self.assertEqual(igp.waist_height_back, 6.25)
        self.assertEqual(igp.shoulder_height, 23.25)
        # body + ease, but adjusted to be 0.5 larger than waist
        self.assertEqual(igp.hip_width_back, 18)

    def test_torso_lengths2(self):
        design = SweaterPatternSpecFactory(torso_length=SDC.MED_HIP_LENGTH)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()
        self.assertEqual(igp.waist_height_front, 7 + 0)  # body + neg ease
        self.assertEqual(igp.waist_height_back, 7 + 0)  # body + neg ease
        self.assertEqual(igp.shoulder_height, 7 + 17 + 0)  # body + neg ease
        self.assertEqual(igp.hip_width_back, 40 / 2 - 0.5)  # body + ease

    def test_torso_lengths3(self):
        design = SweaterPatternSpecFactory(torso_length=SDC.LOW_HIP_LENGTH)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()
        self.assertEqual(igp.waist_height_front, 9 + 0)  # body + neg ease
        self.assertEqual(igp.waist_height_back, 9 + 0)  # body + neg ease
        self.assertEqual(igp.shoulder_height, 9 + 17 + 0)  # body + neg ease
        self.assertEqual(igp.hip_width_back, 42 / 2 - 0.5)  # body + ease

    def test_torso_lengths4(self):
        design = SweaterPatternSpecFactory(torso_length=SDC.TUNIC_LENGTH)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()
        self.assertEqual(igp.waist_height_front, 15 + 0)  # body + neg ease
        self.assertEqual(igp.waist_height_back, 15 + 0)  # body + neg ease
        self.assertEqual(igp.shoulder_height, 15 + 17 + 0)  # body + neg ease
        self.assertEqual(igp.hip_width_back, 44 / 2 + 2.0)  # body + ease

    def test_neckline_other_val(self):
        design = SweaterPatternSpecFactory(
            neckline_width=SDC.NECK_OTHERWIDTH, neckline_other_val_percentage=50
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()

    def test_bell_sleeve(self):
        design = SweaterPatternSpecFactory(
            sleeve_shape=SDC.SLEEVE_BELL, bell_type=SDC.BELL_MODERATE
        )
        user = UserFactory()

        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        igp.full_clean()

    def test_neckline_orientation(self):
        design = SweaterPatternSpecFactory(
            neckline_depth=3, neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        self.assertEqual(igp.front_neck_height, 19)

        design = SweaterPatternSpecFactory(
            neckline_depth=3, neckline_depth_orientation=SDC.BELOW_ARMPIT
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)
        self.assertEqual(igp.front_neck_height, 13)

    def test_hip_circ(self):

        self.longMessage = True

        body_dict = {
            "high": BodyFactory(
                high_hip_circ=44, med_hip_circ=40, low_hip_circ=40, tunic_circ=40
            ),
            "med": BodyFactory(
                high_hip_circ=40, med_hip_circ=44, low_hip_circ=40, tunic_circ=40
            ),
            "low": BodyFactory(
                high_hip_circ=40, med_hip_circ=40, low_hip_circ=44, tunic_circ=40
            ),
            "tunic": BodyFactory(
                high_hip_circ=40, med_hip_circ=40, low_hip_circ=40, tunic_circ=44
            ),
        }

        correct_hip_params = {
            ("high", SDC.HIGH_HIP_LENGTH): (21, 21),
            ("high", SDC.MED_HIP_LENGTH): (21.5, 21.5),
            ("high", SDC.LOW_HIP_LENGTH): (21.5, 21.5),
            ("high", SDC.TUNIC_LENGTH): (24.0, 24.0),
            ("med", SDC.HIGH_HIP_LENGTH): (18.5, 18.5),
            ("med", SDC.MED_HIP_LENGTH): (20.5, 20.5),
            ("med", SDC.LOW_HIP_LENGTH): (20.5, 20.5),
            ("med", SDC.TUNIC_LENGTH): (24.0, 24.0),
            ("low", SDC.HIGH_HIP_LENGTH): (19, 19),
            ("low", SDC.MED_HIP_LENGTH): (19.5, 19.5),
            ("low", SDC.LOW_HIP_LENGTH): (21.5, 21.5),
            ("low", SDC.TUNIC_LENGTH): (24.0, 24.0),
            ("tunic", SDC.HIGH_HIP_LENGTH): (19, 19),
            ("tunic", SDC.MED_HIP_LENGTH): (19.5, 19.5),
            ("tunic", SDC.LOW_HIP_LENGTH): (19.5, 19.5),
            ("tunic", SDC.TUNIC_LENGTH): (24.0, 24.0),
        }

        for body_name, body in list(body_dict.items()):

            correct_circ_dict = {
                SDC.HIGH_HIP_LENGTH: body.high_hip_circ,
                SDC.MED_HIP_LENGTH: max([body.high_hip_circ, body.med_hip_circ]),
                SDC.LOW_HIP_LENGTH: max(
                    [body.high_hip_circ, body.med_hip_circ, body.low_hip_circ]
                ),
                SDC.TUNIC_LENGTH: max(
                    [
                        body.high_hip_circ,
                        body.med_hip_circ,
                        body.low_hip_circ,
                        body.tunic_circ,
                    ]
                ),
            }

            for length in [
                SDC.HIGH_HIP_LENGTH,
                SDC.MED_HIP_LENGTH,
                SDC.LOW_HIP_LENGTH,
                SDC.TUNIC_LENGTH,
            ]:
                pspec = SweaterPatternSpecFactory(body=body, torso_length=length)

                user = UserFactory()
                igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                    user, pspec
                )

                self.assertEqual(igp._get_hip_circ(), correct_circ_dict[length])

                goal_params = correct_hip_params[(body_name, length)]
                actual_params = (igp.hip_width_back, igp.hip_width_front)

                self.assertEqual(actual_params, goal_params, (body_name, length))

    def test_button_band_allowance(self):
        # 'standard' case
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            button_band_allowance=None,
            button_band_allowance_percentage=None,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertIsNone(igp.button_band_allowance)
        self.assertIsNone(igp.button_band_allowance_percentage)

        # Test a valid inch-value for button-band allowances
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=4,
            button_band_allowance_percentage=None,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertEqual(igp.front_neck_opening_width, 7.75)
        self.assertEqual(igp.button_band_allowance, 4)
        self.assertIsNone(igp.button_band_allowance_percentage)

        # Test a button-band inch-value that is way too big
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=16,
            button_band_allowance_percentage=None,
        )
        user = UserFactory()
        with self.assertRaises(ValidationError):
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        # Test a button-band allowance value in percentages
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=None,
            button_band_allowance_percentage=50,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertEqual(igp.front_neck_opening_width, 7.75)
        self.assertIsNone(igp.button_band_allowance)
        self.assertEqual(igp.button_band_allowance_percentage, 50)

        # Test a button-band allowance value in percentages, corner case
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=None,
            button_band_allowance_percentage=100,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertEqual(igp.front_neck_opening_width, 7.75)
        self.assertIsNone(igp.button_band_allowance)
        self.assertEqual(igp.button_band_allowance_percentage, 100)

        # Test a button-band allowance value in percentages, corner case
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=None,
            button_band_allowance_percentage=0,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertEqual(igp.front_neck_opening_width, 7.75)
        self.assertIsNone(igp.button_band_allowance)
        self.assertEqual(igp.button_band_allowance_percentage, 0)

        # Test a button-band allowance value in percentages, corner case
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=None,
            button_band_allowance_percentage=-75,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        self.assertEqual(igp.front_neck_opening_width, 7.75)
        self.assertIsNone(igp.button_band_allowance)
        self.assertEqual(igp.button_band_allowance_percentage, -75)

    def test_cross_chest(self):
        user = UserFactory()
        body1 = BodyFactory(user=user, upper_torso_circ=38, cross_chest_distance=None)
        pattern_spec1 = SweaterPatternSpecFactory(body=body1, user=user)
        igp1 = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pattern_spec1
        )
        self.assertEqual(igp1.back_cross_back_width, 14)

        body2 = BodyFactory(user=user, upper_torso_circ=38, cross_chest_distance=13)
        pattern_spec2 = SweaterPatternSpecFactory(
            body=body2, garment_fit=SDC.FIT_HOURGLASS_AVERAGE, user=user
        )
        igp2 = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pattern_spec2
        )
        self.assertEqual(igp2.back_cross_back_width, 13)

        body3 = BodyFactory(user=user, upper_torso_circ=38, cross_chest_distance=13)
        pattern_spec3 = SweaterPatternSpecFactory(
            body=body3, garment_fit=SDC.FIT_HOURGLASS_RELAXED, user=user
        )
        igp3 = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pattern_spec3
        )
        self.assertEqual(igp3.back_cross_back_width, 14)

        body4 = BodyFactory(user=user, upper_torso_circ=38, cross_chest_distance=13)
        pattern_spec4 = SweaterPatternSpecFactory(
            body=body4, garment_fit=SDC.FIT_HOURGLASS_TIGHT, user=user
        )
        igp4 = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pattern_spec4
        )
        self.assertEqual(igp4.back_cross_back_width, 12)

    def test_cross_back_calculations(self):
        user = UserFactory()

        body_ccd = BodyFactory(user=user, upper_torso_circ=38, cross_chest_distance=13)
        pspec_ccd = SweaterPatternSpecFactory(
            body=body_ccd, garment_fit=SDC.FIT_HOURGLASS_TIGHT, user=user
        )
        igp_ccd = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_ccd
        )

        self.assertEqual(igp_ccd.back_cross_back_width, 12)

        body_magic = BodyFactory(user=user, upper_torso_circ=38)
        pspec_magic = SweaterPatternSpecFactory(
            body=body_magic, garment_fit=SDC.FIT_HOURGLASS_TIGHT, user=user
        )
        igp_magic = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_magic
        )

        self.assertEqual(igp_magic.back_cross_back_width, 13.75)

        body_error = BodyFactory(user=user, upper_torso_circ=15)
        pspec_error = SweaterPatternSpecFactory(
            body=body_error, garment_fit=SDC.FIT_HOURGLASS_TIGHT, user=user
        )

        self.assertRaises(
            ValueError,
            SweaterIndividualGarmentParameters.make_from_patternspec,
            user,
            pspec_error,
        )

    def test_get_hip_height(self):

        user = UserFactory()

        _ = BodyFactory(
            armpit_to_high_hip=14.5,
            armpit_to_med_hip=16,
            armpit_to_low_hip=18,
            armpit_to_tunic=24,
        )

        pspec_high = SweaterPatternSpecFactory(torso_length=SDC.HIGH_HIP_LENGTH)
        igp_high = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_high
        )
        self.assertEqual(igp_high._get_relevant_hip_height_from_body(), 14.5)

        pspec_med = SweaterPatternSpecFactory(torso_length=SDC.MED_HIP_LENGTH)
        igp_med = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_med
        )
        self.assertEqual(igp_med._get_relevant_hip_height_from_body(), 16)

        pspec_low = SweaterPatternSpecFactory(torso_length=SDC.LOW_HIP_LENGTH)
        igp_low = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_low
        )
        self.assertEqual(igp_low._get_relevant_hip_height_from_body(), 18)

        pspec_tunic = SweaterPatternSpecFactory(torso_length=SDC.TUNIC_LENGTH)
        igp_tunic = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_tunic
        )
        self.assertEqual(igp_tunic._get_relevant_hip_height_from_body(), 24)

    def test_get_sleeve_height(self):

        user = UserFactory()

        _ = BodyFactory(
            armpit_to_short_sleeve=1,
            armpit_to_elbow_sleeve=6,
            armpit_to_three_quarter_sleeve=12,
            armpit_to_full_sleeve=17.5,
        )

        pspec_short = SweaterPatternSpecFactory(sleeve_length=SDC.SLEEVE_SHORT)
        igp_short = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_short
        )
        self.assertEqual(igp_short._get_relevant_sleeve_length_from_body(), 1)

        pspec_elbow = SweaterPatternSpecFactory(sleeve_length=SDC.SLEEVE_ELBOW)
        igp_elbow = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_elbow
        )
        self.assertEqual(igp_elbow._get_relevant_sleeve_length_from_body(), 6)

        pspec_threeq = SweaterPatternSpecFactory(sleeve_length=SDC.SLEEVE_THREEQUARTER)
        igp_threeq = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_threeq
        )
        self.assertEqual(igp_threeq._get_relevant_sleeve_length_from_body(), 12)

        pspec_full = SweaterPatternSpecFactory(sleeve_length=SDC.SLEEVE_FULL)
        igp_full = SweaterIndividualGarmentParameters.make_from_patternspec(
            user, pspec_full
        )
        self.assertEqual(igp_full._get_relevant_sleeve_length_from_body(), 17.5)

    def test_adjust_and_unadjust_lengths_for_negative_ease(self):

        igp = SweaterIndividualGarmentParametersFactory()

        # 5 inches of negative ease in bust
        # should add 2.5 inches to waist-to-armhole
        igp.bust_width_front = 18
        igp.bust_width_back = 18

        # 4 inches of negative ease in hips should
        # add two inches to waist-height
        igp.hip_width_front = 18
        igp.hip_width_back = 18

        # Control: before adjusting
        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.waist_height_front, 7)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)

        igp.adjust_lengths_for_negative_ease()

        # Test: after adjusting
        self.assertEqual(igp.waist_height_back, 9)
        self.assertEqual(igp.waist_height_front, 9)
        self.assertEqual(igp.armpit_height, 20.5)
        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)

        # Test: can un-adjust
        (
            readj_waist_height_front,
            readj_waist_height_back,
            readj_armpit_height,
            readj_sleeve_height,
        ) = igp.unadjust_lengths_for_negative_ease()
        self.assertEqual(readj_waist_height_back, 7)
        self.assertEqual(readj_waist_height_front, 7)
        self.assertEqual(readj_armpit_height, 16)
        self.assertEqual(readj_sleeve_height, 17.5)

    # TODO: write some tests that check actual values in single-size cases
    # 1) No extras
    # 2) Horizontal bust darts
    # 3) Vertical bust darts
    #
    # times
    #
    # all three fits
    #
    # And then all-three fits (no bust darts) for all five sleeve-types

    #
    # Error-cases / code-coverage tests
    #

    def test_waist_and_hip_width_back(self):
        pspec = create_csv_combo("Test 4", "DK Stitch repeats", "Test 7")
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

    def test_error_case_body3_sport_design2(self):

        pspec = create_csv_combo("Test 6", "Sport stitch repeats", "Test 2")
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 22)
        self.assertEqual(igp.armpit_height, 12)
        self.assertEqual(igp.waist_height_front, 4)
        self.assertEqual(igp.waist_height_back, 4)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 21)
        self.assertEqual(igp.front_neck_height, 16)

        self.assertEqual(igp.hip_width_back, 27)
        self.assertEqual(igp.waist_width_back, 21.75)
        self.assertEqual(igp.bust_width_back, 21.75)
        self.assertEqual(igp.back_cross_back_width, 15)
        self.assertEqual(igp.back_neck_opening_width, 7.5)

        self.assertEqual(igp.hip_width_front, 27)
        self.assertEqual(igp.waist_width_front, 25.75)
        self.assertEqual(igp.bust_width_front, 25.75)

        self.assertEqual(igp.hip_circ_total, 54)
        self.assertEqual(igp.waist_circ_total, 47.5)
        self.assertEqual(igp.bust_circ_total, 47.5)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, None)
        self.assertEqual(igp.sleeve_edging_height, None)
        self.assertEqual(igp.bicep_width, None)
        self.assertEqual(igp.sleeve_cast_on_width, None)

    def test_straight_with_padding_body(self):
        pspec = create_csv_combo("Test 3", "Cascade 220 St st", "Test 7")
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 21.5625)
        self.assertEqual(igp.armpit_height, 13.0625)
        self.assertEqual(igp.waist_height_front, 4.5625)
        self.assertEqual(igp.waist_height_back, 4.5625)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 20.5625)
        self.assertEqual(igp.front_neck_height, 15.5625)

        self.assertEqual(igp.hip_width_back, 20.5)
        self.assertEqual(igp.waist_width_back, 18.625)
        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        self.assertEqual(igp.hip_width_front, 21.375)
        self.assertEqual(igp.waist_width_front, 21.375)
        self.assertEqual(igp.bust_width_front, 25.375)

        self.assertEqual(igp.hip_circ_total, 41.875)
        self.assertEqual(igp.waist_circ_total, 40)
        self.assertEqual(igp.bust_circ_total, 45)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 12.75)
        self.assertEqual(igp.sleeve_cast_on_width, 12.75)

    def test_a_line_shaping_case9(self):
        body = BodyFactory(waist_circ=45)
        pspec = SweaterPatternSpecFactory(body=body)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)

        # Larger of waist and hip, divided evenly
        self.assertEqual(igp.hip_width_back, 24)

        # equal to bust
        self.assertEqual(igp.waist_width_back, 19.75)

        # unchanged
        self.assertEqual(igp.bust_width_back, 19.75)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        # Larger of waist and hip, divided evenly
        self.assertEqual(igp.hip_width_front, 24)

        # equal to bust
        self.assertEqual(igp.waist_width_front, 22.25)

        # No longer larger of bust-ront and waist-front. Now just bust-front
        self.assertEqual(igp.bust_width_front, 22.25)

        # Waist = bust
        # hip gets larger of waist and hip (incl. eases)
        self.assertEqual(igp.hip_circ_total, 48)
        self.assertEqual(igp.waist_circ_total, 42)
        self.assertEqual(igp.bust_circ_total, 42)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

        self.assertEqual(igp.waist_height_front, 12)
        self.assertEqual(igp.waist_height_back, 12)

    def test_a_line_shaping_case7(self):
        body = BodyFactory(waist_circ=44, med_hip_circ=48)
        pspec = SweaterPatternSpecFactory(body=body)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)
        self.assertEqual(igp.hip_width_back, 24)
        self.assertEqual(igp.waist_width_back, 19.5)

        # unchanged
        self.assertEqual(igp.bust_width_back, 19.5)
        self.assertEqual(igp.back_cross_back_width, 13.75)
        self.assertEqual(igp.back_neck_opening_width, 6.875)

        # Larger of waist and hip, divided evenly
        self.assertEqual(igp.hip_width_front, 24)

        # equal to bust
        self.assertEqual(igp.waist_width_front, 21.5)

        # No longer larger of bust-ront and waist-front. Now just bust-front
        self.assertEqual(igp.bust_width_front, 21.5)

        # Waist = bust
        # hip gets larger of waist and hip (incl. eases)
        self.assertEqual(igp.hip_circ_total, 48)
        self.assertEqual(igp.waist_circ_total, 41)
        self.assertEqual(igp.bust_circ_total, 41)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

        self.assertEqual(igp.waist_height_front, 12)
        self.assertEqual(igp.waist_height_back, 12)

    def test_basic_sleeve_error1(self):
        pspec = SweaterPatternSpecFactory()
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.sleeve_to_armcap_start_height = None
        self.assertRaises(ValidationError, igp.full_clean)

    # def test_basic_sleeve_error2(self):
    #     pspec = test_design.create_pattern_spec()
    #     user = UserFactory()
    #     igp =  SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
    #     igp.sleeve_edging_height = None
    #     self.assertRaises(ValidationError, igp.full_clean)

    def test_basic_sleeve_error3(self):
        pspec = SweaterPatternSpecFactory()
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.bicep_width = None
        self.assertRaises(ValidationError, igp.full_clean)

    def test_basic_sleeve_error4(self):
        pspec = SweaterPatternSpecFactory()
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.sleeve_cast_on_width = None
        self.assertRaises(ValidationError, igp.full_clean)

    def test_impossible_error_case1(self):
        pspec = SweaterPatternSpecFactory(sleeve_length="FOO")
        user = UserFactory()
        self.assertRaises(
            KeyError,
            SweaterIndividualGarmentParameters.make_from_patternspec,
            user,
            pspec,
        )

    def test_impossible_error_case2(self):
        pspec = SweaterPatternSpecFactory(sleeve_shape="FOO")
        user = UserFactory()
        self.assertRaises(
            ValueError,
            SweaterIndividualGarmentParameters.make_from_patternspec,
            user,
            pspec,
        )

    def test_errorbody_from_report_1(self):
        body_dict = {
            "waist_circ": 46.5,
            "bust_circ": 47,
            "upper_torso_circ": 41.5,
            "wrist_circ": 6.75,
            "forearm_circ": 11,
            "bicep_circ": 13,
            "elbow_circ": 11,
            "armpit_to_short_sleeve": 6,
            "armpit_to_elbow_sleeve": 11,
            "armpit_to_three_quarter_sleeve": 14,
            "armpit_to_full_sleeve": 20.75,
            "inter_nipple_distance": 8.5,
            "armpit_to_waist": 12.25,
            "armhole_depth": 7.5,
            "armpit_to_high_hip": 12.25 + 3,
            "armpit_to_med_hip": 12.25 + 5,
            "armpit_to_low_hip": 12.25 + 7,
            "armpit_to_tunic": 12.25 + 8.5,
            "high_hip_circ": 49,
            "med_hip_circ": 49.5,
            "low_hip_circ": 48.5,
            "tunic_circ": 44,
        }

        body = BodyFactory(**body_dict)
        pspec = SweaterPatternSpecFactory(body=body)
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()

    # The following test cases check that invalid combinations of Body and
    # Design are caught during clean().
    # --------------------------------------------------------------------------
    def test_validation_neckline_depth(self):
        pspec = SweaterPatternSpecFactory()
        pspec.neckline_depth_orientation = SDC.ABOVE_ARMPIT
        # Assumed to be greater than body armpit depth plus ease.
        pspec.neckline_depth = 20
        pspec.save()

        with self.assertRaises(
            SweaterIndividualGarmentParameters.IncompatibleDesignInputs
        ):
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                pspec.user, pspec
            )
            igp.clean()

    def test_validation_hip_edging(self):
        """
        If the body's hip height cannot accommodate the design's hip edging
        height, IGP.clean() should raise IncompatibleDesignInputs.
        For hourglass silhouettes, hip edging can extend to the waist.
        """
        body = BodyFactory(armpit_to_low_hip=18, armpit_to_waist=9)
        pspec = SweaterPatternSpecFactory(
            hip_edging_height=20, body=body  # note: bigger than armpit to hip
        )

        with self.assertRaises(
            SweaterIndividualGarmentParameters.IncompatibleDesignInputs
        ):
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                pspec.user, pspec
            )
            igp.clean()

        pspec = SweaterPatternSpecFactory(
            hip_edging_height=10, body=body  # bigger than waist height but not armpit
        )

        with self.assertRaises(
            SweaterIndividualGarmentParameters.IncompatibleDesignInputs
        ):
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                pspec.user, pspec
            )
            igp.clean()


class HalfHourglassSilhouetteIGPTests(django.test.TestCase):

    def test_validation(self):

        pspec = SweaterPatternSpecFactory(silhouette=SDC.SILHOUETTE_HALF_HOURGLASS)
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        gp.waist_width_front = 20
        gp.hip_width_front = 20
        gp.bust_width_front = 20
        gp.full_clean()

        gp.waist_width_front = 21
        gp.hip_width_front = 20
        gp.bust_width_front = 20
        with self.assertRaises(ValidationError):
            gp.full_clean()

        gp.waist_width_front = 20
        gp.hip_width_front = 21
        gp.bust_width_front = 20
        with self.assertRaises(ValidationError):
            gp.full_clean()

        gp.waist_width_front = 20
        gp.hip_width_front = 20
        gp.bust_width_front = 21
        with self.assertRaises(ValidationError):
            gp.full_clean()

    def test_compare_to_hourglass(self):

        # 'standard' case
        pspec = SweaterPatternSpecFactory()
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.waist_height_front, 7)
        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)

        self.assertEqual(igp.hip_width_back, 19.5)
        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        self.assertEqual(igp.hip_width_front, 19.5)
        self.assertEqual(igp.waist_width_front, 17.5)
        self.assertEqual(igp.bust_width_front, 20.375)

        self.assertEqual(igp.hip_circ_total, 39)
        self.assertEqual(igp.waist_circ_total, 35)
        self.assertEqual(igp.bust_circ_total, 40)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

        pspec = SweaterPatternSpecFactory(silhouette=SDC.SILHOUETTE_HALF_HOURGLASS)
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        self.assertEqual(igp.shoulder_height, 24)
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(igp.waist_height_front, 7)
        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.torso_hem_height, 1.5)
        self.assertEqual(igp.back_neck_height, 23)
        self.assertEqual(igp.front_neck_height, 18)

        self.assertEqual(igp.hip_width_back, 19.5)
        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertEqual(igp.back_neck_opening_width, 7)

        self.assertEqual(igp.hip_width_front, 20.375)
        self.assertEqual(igp.waist_width_front, 20.375)
        self.assertEqual(igp.bust_width_front, 20.375)

        self.assertEqual(igp.hip_circ_total, 39.875)
        self.assertEqual(igp.waist_circ_total, 37.875)
        self.assertEqual(igp.bust_circ_total, 40)

        self.assertIsNone(igp.button_band_allowance)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.sleeve_edging_height, 0.5)
        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(igp.sleeve_cast_on_width, 9)

    def test_case_9_neckline_bug(self):
        # User was getting problems with her case 9 body pushng her
        # waist up higher then her neckline
        user = UserFactory()
        design = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            primary_silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.LOW_HIP_LENGTH,
            hip_edging_height=1.5,
            neckline_style=SDC.NECK_VEE,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            sleeve_edging_height=2.0,
            button_band_allowance=1.5,
            number_of_buttons=7,
            button_band_edging_height=1.5,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        body = BodyFactory(
            waist_circ=48.5,
            bust_circ=46.5,
            upper_torso_circ=44.25,
            wrist_circ=7.0,
            forearm_circ=10.25,
            bicep_circ=13.75,
            elbow_circ=12.4,
            armpit_to_short_sleeve=10.25,
            armpit_to_elbow_sleeve=12.0,
            armpit_to_three_quarter_sleeve=19.0,
            armpit_to_full_sleeve=22.5,
            inter_nipple_distance=9.5,
            armpit_to_waist=6.5,
            armhole_depth=10.5,
            armpit_to_high_hip=11.0,
            high_hip_circ=50.5,
            armpit_to_med_hip=14.5,
            med_hip_circ=52.5,
            armpit_to_low_hip=17.5,
            low_hip_circ=48.0,
            armpit_to_tunic=18.5,
            tunic_circ=43,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        swatch = SwatchFactory()

        ps = make_patternspec_from_design(
            design,
            user,
            design.name,
            swatch,
            body,
            SDC.SILHOUETTE_HOURGLASS,
            SDC.FIT_HOURGLASS_AVERAGE,
        )
        ps.full_clean()
        ps.save()

        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, ps)
        igp.full_clean()

        ps.delete()


## And now we generate the dynamic tests from the CSV files
# Dynamic tests
# These tests grew too slow to run on Jenkins. Commenting out, but leaving in
# so that they can be salvaged later
#
#
# def make_clean_from_pspec(pspec):
#     user = UserFactory()
#     g = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
#     g.full_clean()
#
#
# @attr('slow')
# def test_csv_combos():
#     for pspec in create_csv_combos():
#         make_clean_from_pspec(pspec)


class SweaterIndividualGarmentParametersBugs(django.test.TestCase):
    """
    TestCase object containing bugs found during testing.
    """

    def test_errorcase_1(self):
        user = UserFactory()
        body = BodyFactory(
            user=user,
            waist_circ=37.0,
            bust_circ=41,
            upper_torso_circ=38,
            wrist_circ=6,
            forearm_circ=8.5,
            bicep_circ=13,
            elbow_circ=9.5,
            armpit_to_short_sleeve=3,
            armpit_to_elbow_sleeve=7,
            armpit_to_three_quarter_sleeve=14,
            armpit_to_full_sleeve=19,
            inter_nipple_distance=8,
            armpit_to_waist=6.5,
            armhole_depth=8.5,
            armpit_to_high_hip=15.5,
            high_hip_circ=43.5,
            armpit_to_med_hip=17,
            med_hip_circ=44.5,
            armpit_to_low_hip=19,
            low_hip_circ=46,
            armpit_to_tunic=22,
            tunic_circ=44,
            cross_chest_distance=14,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        swatch = SwatchFactory(
            user=user,
            stitches_length=3.1875,
            stitches_number=16,
            rows_length=1.65625,
            rows_number=13,
            use_repeats=True,
            stitches_per_repeat=4,
            additional_stitches=0,
        )

        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_OVERSIZED,
            silhouette=SDC.SILHOUETTE_TAPERED,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            user=user,
            body=body,
            swatch=swatch,
        )

        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)


class NonHourglassSilhouetteIGPTest(django.test.TestCase):

    # Straight silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_straight(self):
        user = UserFactory()
        body = BodyFactory(
            waist_circ=32, bust_circ=41, body_type=Body.BODY_TYPE_ADULT_WOMAN
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 21.0)
        self.assertEqual(igp.bust_width_front, 21.0)
        self.assertEqual(igp.hip_width_back, 21.0)
        self.assertEqual(igp.hip_width_front, 21.0)
        self.assertEqual(igp.back_cross_back_width, 14.0)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_straight(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 33)
        self.assertEqual(igp.hip_width_back, 21)
        self.assertEqual(igp.hip_width_front, 33)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_straight(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 18.5)
        self.assertEqual(igp.bust_width_front, 18.5)
        self.assertEqual(igp.hip_width_back, 18.5)
        self.assertEqual(igp.hip_width_front, 18.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    # A-line silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_aline(self):
        user = UserFactory()
        body = BodyFactory(
            waist_circ=32, bust_circ=41, body_type=Body.BODY_TYPE_ADULT_WOMAN
        )
        pspec = SweaterPatternSpecFactory(
            body=body,
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 19.75)
        self.assertEqual(igp.bust_width_front, 21.25)
        self.assertEqual(igp.hip_width_back, 22.75)
        self.assertEqual(igp.hip_width_front, 24.25)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_busty_case_9_woman_aline(self):
        user = UserFactory()
        body = BodyFactory(
            waist_circ=42,
            med_hip_circ=46,
            bust_circ=41,
            upper_torso_circ=37,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        pspec = SweaterPatternSpecFactory(
            body=body,
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 19.25)
        self.assertEqual(igp.bust_width_front, 21.75)
        self.assertEqual(igp.hip_width_back, 26.0)
        self.assertEqual(igp.hip_width_front, 26.0)
        self.assertEqual(igp.back_cross_back_width, 13.75)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_non_busty_case_9_woman_aline(self):
        user = UserFactory()
        body = BodyFactory(
            waist_circ=42,
            med_hip_circ=46,
            bust_circ=41,
            upper_torso_circ=40,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        pspec = SweaterPatternSpecFactory(
            body=body,
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 20.5)
        self.assertEqual(igp.bust_width_front, 20.5)
        self.assertEqual(igp.hip_width_back, 26.0)
        self.assertEqual(igp.hip_width_front, 26.0)
        self.assertEqual(igp.back_cross_back_width, 14.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_aline(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, med_hip_circ=48, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 21)
        self.assertEqual(igp.hip_width_back, 27)
        self.assertEqual(igp.hip_width_front, 27)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_aline(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 16)
        self.assertEqual(igp.bust_width_front, 16)
        self.assertEqual(igp.hip_width_back, 20.5)
        self.assertEqual(igp.hip_width_front, 20.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    # Tapered silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_tapered(self):
        user = UserFactory()
        body = BodyFactory(
            waist_circ=32, bust_circ=41, body_type=Body.BODY_TYPE_ADULT_WOMAN
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 20.25)
        self.assertEqual(igp.bust_width_front, 21.75)
        self.assertEqual(igp.hip_width_back, 19)
        self.assertEqual(igp.hip_width_front, 19)
        self.assertEqual(igp.back_cross_back_width, 14.0)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_tapered(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 30)
        self.assertEqual(igp.hip_width_back, 20.5)
        self.assertEqual(igp.hip_width_front, 20.5)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_tapered(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 18.5)
        self.assertEqual(igp.bust_width_front, 18.5)
        self.assertEqual(igp.hip_width_back, 16.5)
        self.assertEqual(igp.hip_width_front, 16.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    # Hip parameters
    # --------------------------------------------------------------------------

    def test_validation_hip_edging(self):
        """
        If the body's hip height cannot accommodate the design's hip edging
        height, IGP.clean() should raise IncompatibleDesignInputs.
        For non-hourglass silhouettes, hip edging can extend to the armpit.
        """
        body = BodyFactory(armpit_to_low_hip=18, armpit_to_waist=9)
        pspec = SweaterPatternSpecFactory(
            hip_edging_height=20,  # note: bigger than armpit to hip
            body=body,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )

        with self.assertRaises(
            SweaterIndividualGarmentParameters.IncompatibleDesignInputs
        ):
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                pspec.user, pspec
            )
            igp.clean()

        pspec = SweaterPatternSpecFactory(
            hip_edging_height=10,  # bigger than waist height but not armpit
            body=body,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )

        # Should not raise anything.
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(
            pspec.user, pspec
        )
        igp.clean()

    def test_high_hip_length(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.HIGH_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.armpit_height, 14)

    def test_med_hip_length(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.armpit_height, 17)

    def test_low_hip_length(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.LOW_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.armpit_height, 19)

    def test_tunic_length(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.TUNIC_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.armpit_height, 21)

    # Sleeve parameters
    # --------------------------------------------------------------------------

    def test_short_sleeve(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_SHORT,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.sleeve_to_armcap_start_height, 2)

    def test_elbow_sleeve(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_ELBOW,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.sleeve_to_armcap_start_height, 6)

    def test_three_quarter_sleeve(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_THREEQUARTER,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.sleeve_to_armcap_start_height, 12)

    def test_full_sleeve(self):
        user = UserFactory()
        body = get_csv_body("Test 2")
        body.upper_torso_circ = None
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_FULL,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17)


class NonHourglassSilhouetteSimpleBodyTests(django.test.TestCase):

    # Straight silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_straight(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            waist_circ=32,
            bust_circ=41,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
            upper_torso_circ=38,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 21.0)
        self.assertEqual(igp.bust_width_front, 21.0)
        self.assertEqual(igp.hip_width_back, 21.0)
        self.assertEqual(igp.hip_width_front, 21.0)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_straight(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 33)
        self.assertEqual(igp.hip_width_back, 21)
        self.assertEqual(igp.hip_width_front, 33)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_straight(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            armpit_to_full_sleeve=17.0,
            bicep_circ=10.0,
            bust_circ=32.0,
            waist_circ=29.0,
            armhole_depth=7.5,
            armpit_to_med_hip=17,
            med_hip_circ=35.0,
            wrist_circ=6.0,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, igp.hip_width_back)
        self.assertEqual(igp.bust_width_front, igp.hip_width_front)
        self.assertEqual(igp.bust_width_back, 18.5)
        self.assertEqual(igp.bust_width_front, 18.5)
        self.assertEqual(igp.hip_width_back, 18.5)
        self.assertEqual(igp.hip_width_front, 18.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    # A-line silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_aline(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            waist_circ=32,
            bust_circ=41,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
            upper_torso_circ=38,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 19.75)
        self.assertEqual(igp.bust_width_front, 21.25)
        self.assertEqual(igp.hip_width_back, 22.75)
        self.assertEqual(igp.hip_width_front, 24.25)
        self.assertEqual(igp.back_cross_back_width, 14)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_aline(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 21)
        self.assertEqual(igp.hip_width_back, 24)
        self.assertEqual(igp.hip_width_front, 24)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_aline(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            armpit_to_full_sleeve=17.0,
            bicep_circ=10.0,
            bust_circ=32.0,
            waist_circ=29.0,
            armhole_depth=7.5,
            armpit_to_med_hip=17,
            med_hip_circ=35.0,
            wrist_circ=6.0,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 16)
        self.assertEqual(igp.bust_width_front, 16)
        self.assertEqual(igp.hip_width_back, 20.5)
        self.assertEqual(igp.hip_width_front, 20.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    # Tapered silhouettes
    # --------------------------------------------------------------------------

    def test_busty_woman_tapered(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            waist_circ=32,
            bust_circ=41,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
            upper_torso_circ=38,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 20.25)
        self.assertEqual(igp.bust_width_front, 21.75)
        self.assertEqual(igp.hip_width_back, 19)
        self.assertEqual(igp.hip_width_front, 19)
        self.assertEqual(igp.back_cross_back_width, 14.0)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_portly_man_tapered(self):
        user = UserFactory()
        body = MaleBodyFactory(bust_circ=38, waist_circ=50)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_MENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(igp.bust_width_back, 21)
        self.assertEqual(igp.bust_width_front, 30)
        self.assertEqual(igp.hip_width_back, 20.5)
        self.assertEqual(igp.hip_width_front, 20.5)
        self.assertEqual(igp.back_cross_back_width, 15.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_other_tapered(self):
        user = UserFactory()
        body = SimpleBodyFactory(
            armpit_to_full_sleeve=17.0,
            bicep_circ=10.0,
            bust_circ=32.0,
            waist_circ=29.0,
            armhole_depth=7.5,
            armpit_to_med_hip=17,
            med_hip_circ=35.0,
            wrist_circ=6.0,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

        self.assertEqual(
            igp.bust_width_back - igp.bust_width_front,
            igp.hip_width_back - igp.hip_width_front,
        )
        self.assertEqual(igp.bust_width_back, 18.5)
        self.assertEqual(igp.bust_width_front, 18.5)
        self.assertEqual(igp.hip_width_back, 16.5)
        self.assertEqual(igp.hip_width_front, 16.5)
        self.assertEqual(igp.back_cross_back_width, 12.5)
        self.assertIsNone(igp.waist_width_back)
        self.assertIsNone(igp.waist_width_front)

    def test_tapered_sleeve(self):
        # Just to check: can we do tapered sleeves with just a simple body?
        user = UserFactory()
        body = SimpleBodyFactory()
        # Sanity check: make sure that SimpleBodyFactory acts as we expect
        self.assertIsNone(body.forearm_circ)
        self.assertIsNone(body.elbow_circ)

        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_length=SDC.SLEEVE_FULL,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()


class SleeveTests(django.test.TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.body = BodyFactory()
        self.sleeve_lengths = [
            SDC.SLEEVE_FULL,
            SDC.SLEEVE_THREEQUARTER,
            SDC.SLEEVE_ELBOW,
            SDC.SLEEVE_SHORT,
        ]

    def test_straight_sleeves(self):
        for sleeve_length in self.sleeve_lengths:
            pspec = SweaterPatternSpecFactory(
                silhouette=SDC.SILHOUETTE_STRAIGHT,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
                body=self.body,
                torso_length=SDC.MED_HIP_LENGTH,
                garment_type=SDC.PULLOVER_SLEEVED,
                sleeve_length=sleeve_length,
                sleeve_shape=SDC.SLEEVE_STRAIGHT,
            )

            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                self.user, pspec
            )

            self.assertEqual(igp.sleeve_cast_on_width, igp.bicep_width)

    def test_tapered_sleeves(self):
        for sleeve_length in self.sleeve_lengths:
            pspec = SweaterPatternSpecFactory(
                silhouette=SDC.SILHOUETTE_STRAIGHT,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
                body=self.body,
                torso_length=SDC.MED_HIP_LENGTH,
                garment_type=SDC.PULLOVER_SLEEVED,
                sleeve_length=sleeve_length,
                sleeve_shape=SDC.SLEEVE_TAPERED,
            )

            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                self.user, pspec
            )

            if sleeve_length == SDC.SLEEVE_SHORT:
                self.assertEqual(
                    igp.sleeve_cast_on_width, igp.bicep_width, sleeve_length
                )
            else:
                self.assertLess(
                    igp.sleeve_cast_on_width, igp.bicep_width, sleeve_length
                )

    def test_bell_sleeves(self):
        for sleeve_length in self.sleeve_lengths:
            pspec = SweaterPatternSpecFactory(
                silhouette=SDC.SILHOUETTE_STRAIGHT,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
                body=self.body,
                torso_length=SDC.MED_HIP_LENGTH,
                garment_type=SDC.PULLOVER_SLEEVED,
                sleeve_length=sleeve_length,
                sleeve_shape=SDC.SLEEVE_BELL,
                bell_type=SDC.BELL_MODERATE,
            )

            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                self.user, pspec
            )

            if sleeve_length == SDC.SLEEVE_SHORT:
                self.assertEqual(
                    igp.sleeve_cast_on_width, igp.bicep_width, sleeve_length
                )
            else:
                self.assertGreater(
                    igp.sleeve_cast_on_width, igp.bicep_width, sleeve_length
                )

    def test_edging_heights(self):
        # We should allow sleeve-edging to extend into the cap (we will shrink it in the Sleeve model)

        body = BodyFactory(armpit_to_short_sleeve=4)

        for edging_height in [2, 4, 5]:
            pspec = SweaterPatternSpecFactory(
                silhouette=SDC.SILHOUETTE_STRAIGHT,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
                body=self.body,
                torso_length=SDC.MED_HIP_LENGTH,
                garment_type=SDC.PULLOVER_SLEEVED,
                sleeve_length=SDC.SLEEVE_SHORT,
                sleeve_shape=SDC.SLEEVE_BELL,
                bell_type=SDC.BELL_MODERATE,
                sleeve_edging_height=edging_height,
            )

            igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                self.user, pspec
            )
            igp.full_clean()


class GarmentParametersTestVectors(django.test.TestCase):

    # First, determine if a row from the CSV file matches the template for tests:

    longMessage = True

    csv_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "csv_test_cases"
    )

    def parse_vector_row(self, row, fit):

        name = row["Name"]
        body_measurements = (
            row["Body UT"],
            row["Body Bust"],
            row["Body Waist"],
            row["Body Hip"],
        )

        bust_triple = (row["GP Total Bust"], row["GP Back Bust"], row["GP Front Bust"])

        waist_triple = (
            row["GP total waist"],
            row["GP Back Waist"],
            row["GP Front Waist"],
        )

        hip_triple = (row["GP total hip"], row["GP Back Hip"], row["GP Front Hip"])

        upper_torso = row["GP Back UT"]

        class TestVector(object):
            def __init__(
                self, name, body_measurements, upper_torso, bust, waist, hip, fit
            ):
                self.name = name
                self.body_measurements = body_measurements
                self.upper_torso = upper_torso
                self.bust_triple = bust
                self.waist_triple = waist
                self.hip_triple = hip
                self.fit = fit

        return TestVector(
            name,
            body_measurements,
            upper_torso,
            bust_triple,
            waist_triple,
            hip_triple,
            fit,
        )

    # Now, create a test-vector for every test-row in the CSV file
    def generate_vectors_from_file(self, filehandle, fit):
        test_vectors = []
        csv_reader = csv.DictReader(filehandle)
        for row in csv_reader:
            for key, val in list(row.items()):
                if key != "Name":
                    row[key] = float(val)
            tv = self.parse_vector_row(row, fit)
            if tv is not None:
                test_vectors.append(tv)
        return test_vectors

    def check_vector(self, test_vector):

        (upper_torso, bust, waist, hips) = test_vector.body_measurements
        fit = test_vector.fit
        msg = "test vector '%s' (%s/%s/%s/%s), %s fit" % (
            test_vector.name,
            upper_torso,
            bust,
            waist,
            hips,
            fit,
        )

        body = BodyFactory(
            med_hip_circ=hips,
            waist_circ=waist,
            bust_circ=bust,
            upper_torso_circ=upper_torso,
            # This next one added to keep the default body's
            # high-hip measurement from shadowing the med_hip
            # above
            high_hip_circ=hips - 1,
        )

        body.full_clean()
        design = SweaterPatternSpecFactory(
            garment_fit=fit, torso_length=SDC.MED_HIP_LENGTH, body=body
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, design)

        gp_bust = (gp.bust_circ_total, gp.bust_width_back, gp.bust_width_front)
        self.assertTupleEqual(gp_bust, test_vector.bust_triple, msg)

        gp_waist = (gp.waist_circ_total, gp.waist_width_back, gp.waist_width_front)
        self.assertTupleEqual(gp_waist, test_vector.waist_triple, msg)

        gp_hips = (gp.hip_circ_total, gp.hip_width_back, gp.hip_width_front)
        self.assertTupleEqual(gp_hips, test_vector.hip_triple, msg)

        #        ut_back = test_vector.upper_torso
        #        self.assertEqual(gp.upper_torso_width_back, ut_back)

        gp.full_clean()

    def test_average_fit_test_vectors(self):
        file_path = os.path.join(self.csv_file_path, "gp_tests_average.csv")
        csv_file_handle = open(file_path, "r")
        tvs = self.generate_vectors_from_file(
            csv_file_handle, SDC.FIT_HOURGLASS_AVERAGE
        )
        self.assertEqual(len(tvs), 17)
        for tv in tvs:
            self.check_vector(tv)

    def test_snug_fit_test_vectors(self):
        file_path = os.path.join(self.csv_file_path, "gp_tests_snug.csv")
        csv_file_handle = open(file_path, "r")
        tvs = self.generate_vectors_from_file(csv_file_handle, SDC.FIT_HOURGLASS_TIGHT)
        self.assertEqual(len(tvs), 17)
        for tv in tvs:
            self.check_vector(tv)

    def test_relaxed_fit_test_vectors(self):
        file_path = os.path.join(self.csv_file_path, "gp_tests_relaxed.csv")
        csv_file_handle = open(file_path, "r")
        tvs = self.generate_vectors_from_file(
            csv_file_handle, SDC.FIT_HOURGLASS_RELAXED
        )
        self.assertEqual(len(tvs), 17)
        for tv in tvs:
            self.check_vector(tv)

    def test_new_case_four(self):
        # Small differences between waist and bust
        user = UserFactory()

        def check_test_vector(body_tuple, fit, goal_tuple):
            (waist_circ, bust_circ, upper_torso_circ) = body_tuple
            body = BodyFactory(
                waist_circ=waist_circ,
                bust_circ=bust_circ,
                upper_torso_circ=upper_torso_circ,
            )
            pspec = SweaterPatternSpecFactory(body=body, garment_fit=fit)
            igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            igp.full_clean()
            actual_tuple = (
                igp.waist_width_back,
                igp.waist_width_front,
                igp.bust_width_back,
                igp.bust_width_front,
            )
            msg = "body tuple: %s, fit: %s" % (body_tuple, fit)
            self.assertTupleEqual(goal_tuple, actual_tuple, msg)

        test_vectors = [
            ((32, 33, 32), SDC.FIT_HOURGLASS_TIGHT, (16.25, 17.75, 16.25, 17.75)),
            ((32, 34, 32), SDC.FIT_HOURGLASS_TIGHT, (16.75, 17.25, 16.75, 17.25)),
            ((32, 35.5, 32), SDC.FIT_HOURGLASS_TIGHT, (15.5, 18.5, 16.5, 18.5)),
            ((32, 33, 32), SDC.FIT_HOURGLASS_AVERAGE, (16.75, 17.75, 16.75, 17.75)),
            ((32, 34, 32), SDC.FIT_HOURGLASS_AVERAGE, (17.25, 17.25, 17.25, 17.25)),
            ((32, 35.5, 32), SDC.FIT_HOURGLASS_AVERAGE, (15.75, 18.75, 16.75, 19.25)),
            ((32, 33, 32), SDC.FIT_HOURGLASS_RELAXED, (17.5, 18.0, 18.0, 18.0)),
            ((32, 34, 32), SDC.FIT_HOURGLASS_RELAXED, (17.5, 18.0, 18.5, 18.5)),
            ((32, 35.5, 32), SDC.FIT_HOURGLASS_RELAXED, (16.25, 19.25, 17.25, 21.25)),
        ]

        for body_tuple, fit, goal_tuple in test_vectors:
            check_test_vector(body_tuple, fit, goal_tuple)


class TweakIGPTests(django.test.TestCase):

    def test_make_form_positive_ease(self):
        igp = SweaterIndividualGarmentParametersFactory()

        form = TweakSweaterIndividualGarmentParameters(user=igp.user, instance=igp)

        # as-knit measurements
        self.assertEqual(igp.bust_width_front, 20.375)
        self.assertEqual(form.initial["bust_width_front"], 20.375)

        self.assertEqual(igp.bust_width_back, 19.625)
        self.assertEqual(form.initial["bust_width_back"], 19.625)

        self.assertEqual(igp.waist_width_front, 17.5)
        self.assertEqual(form.initial["waist_width_front"], 17.5)

        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(form.initial["waist_width_back"], 17.5)

        self.assertEqual(igp.hip_width_front, 19.5)
        self.assertEqual(form.initial["hip_width_front"], 19.5)

        self.assertEqual(igp.hip_width_back, 19.5)
        self.assertEqual(form.initial["hip_width_back"], 19.5)

        self.assertEqual(igp.back_neck_opening_width, 7)
        self.assertEqual(form.initial["back_neck_opening_width"], 7)
        # Shoulder width does not appear in form.initial - it's calculated
        # later.

        self.assertEqual(igp.armhole_depth, 8)
        self.assertEqual(form.initial["armhole_depth"], 8)

        self.assertEqual(igp.front_neck_depth, 6)
        self.assertEqual(form.initial["front_neck_depth"], 6)

        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(form.initial["bicep_width"], 13.25)

        # As-worn measurements
        self.assertEqual(igp.armpit_height, 16)
        self.assertEqual(form.initial["armpit_height"], 16)

        self.assertEqual(igp.waist_height_back, 7)
        self.assertEqual(igp.grade.armpit_to_med_hip, 16)
        self.assertEqual(igp.grade.armpit_to_waist, 9)
        self.assertEqual(form.initial["waist_height_back"], 7)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.grade.armpit_to_full_sleeve, 17.5)
        self.assertEqual(form.initial["sleeve_to_armcap_start_height"], 17.5)

    def test_make_form_negative_ease(self):
        igp = SweaterIndividualGarmentParametersFactory()

        # 5 inches of negative ease in bust
        # should add 2.5 inches to waist-to-armhole
        igp.bust_width_front = 18
        igp.bust_width_back = 18

        # 4 inches of negative ease in hips should
        # add two inches to waist-height
        igp.hip_width_front = 18
        igp.hip_width_back = 18

        igp.adjust_lengths_for_negative_ease()
        igp.save()

        form = TweakSweaterIndividualGarmentParameters(user=igp.user, instance=igp)

        # as-knit measurements
        self.assertEqual(igp.bust_width_front, 18)
        self.assertEqual(form.initial["bust_width_front"], 18)

        self.assertEqual(igp.bust_width_back, 18)
        self.assertEqual(form.initial["bust_width_back"], 18)

        self.assertEqual(igp.waist_width_front, 17.5)
        self.assertEqual(form.initial["waist_width_front"], 17.5)

        self.assertEqual(igp.waist_width_back, 17.5)
        self.assertEqual(form.initial["waist_width_back"], 17.5)

        self.assertEqual(igp.hip_width_front, 18)
        self.assertEqual(form.initial["hip_width_front"], 18)

        self.assertEqual(igp.hip_width_back, 18)
        self.assertEqual(form.initial["hip_width_back"], 18)

        self.assertEqual(igp.back_neck_opening_width, 7)
        self.assertEqual(form.initial["back_neck_opening_width"], 7)

        self.assertEqual(igp.armhole_depth, 8)
        self.assertEqual(form.initial["armhole_depth"], 8)

        self.assertEqual(igp.front_neck_depth, 6)
        self.assertEqual(form.initial["front_neck_depth"], 6)

        self.assertEqual(igp.bicep_width, 13.25)
        self.assertEqual(form.initial["bicep_width"], 13.25)

        # As-worn measurements
        self.assertEqual(igp.armpit_height, 20.5)
        self.assertEqual(form.initial["armpit_height"], 16)

        self.assertEqual(igp.waist_height_back, 9)
        self.assertEqual(igp.grade.armpit_to_waist, 9)
        self.assertEqual(igp.grade.armpit_to_med_hip, 16)
        self.assertEqual(form.initial["waist_height_back"], 7)

        self.assertEqual(igp.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(igp.grade.armpit_to_full_sleeve, 17.5)
        self.assertEqual(form.initial["sleeve_to_armcap_start_height"], 17.5)

    def test_post_form_positive_ease(self):

        igp = SweaterIndividualGarmentParametersFactory()

        base_value_dict = {
            "bust_width_front": 31,
            "bust_width_back": 32,
            "hip_width_front": 33,
            "hip_width_back": 34,
            "waist_width_front": 28,
            "waist_width_back": 29,
            "back_neck_opening_width": 6,
            "armhole_depth": 9,
            "front_neck_depth": 8,
            "bicep_width": 15,
            "sleeve_cast_on_width": 14,
            "below_armhole_straight": 1.5,
            "armpit_height": 19,
            "waist_height_back": 9,
            "sleeve_to_armcap_start_height": 18,
        }

        value_dict = copy.copy(base_value_dict)
        value_dict.update({"shoulder_width": 6})
        form = TweakSweaterIndividualGarmentParameters(
            igp.user, value_dict, instance=igp
        )
        self.assertTrue(form.is_valid())
        form.save()

        new_igp = SweaterIndividualGarmentParameters.objects.get(pk=igp.pk)

        for k, v in list(base_value_dict.items()):
            self.assertEqual(getattr(new_igp, k), v)

        unchanged_attributes = [
            "back_cross_back_width",
            "waist_height_front",
            "back_neck_depth",
        ]

        for a in unchanged_attributes:
            self.assertEqual(getattr(new_igp, a), getattr(igp, a))

    def test_post_form_negative_ease(self):

        igp = SweaterIndividualGarmentParametersFactory()

        #
        # return form with negative ease and new lengths
        #

        as_knit_dict = {
            # 5 inches of negative ease in bust
            # should add 2.5 inches to waist-to-armhole
            "bust_width_front": 18,
            "bust_width_back": 18,
            # 4 inches of negative ease in hips should
            # add two inches to waist-height
            "hip_width_front": 18,
            "hip_width_back": 18,
            "waist_width_front": 16,
            "waist_width_back": 16,
            "back_neck_opening_width": 8,
            "armhole_depth": 8,
            "front_neck_depth": 8,
            # 1 inch negative ease in bicep
            "bicep_width": 11,
            # Zero ease in wrist
            "sleeve_cast_on_width": 6,
            "below_armhole_straight": 1.5,
        }

        as_worn_dict = {
            # Check: do these change?
            "armpit_height": 19,
            "waist_height_back": 9,
            # This should not change
            "sleeve_to_armcap_start_height": 19,
        }

        value_dict = {}
        value_dict.update(as_knit_dict)
        value_dict.update(as_worn_dict)
        # We want to feed this into the form, but we don't want it to be in
        # as_knit_dict because we don't want to feed it into the assertEqual
        # below - trying to getattr(igp, 'shoulder_width') will fail.
        value_dict.update({"shoulder_width": 8})
        form = TweakSweaterIndividualGarmentParameters(
            igp.user, value_dict, instance=igp
        )
        self.assertTrue(form.is_valid())
        form.save()

        #
        # Check: did the IGP adjust for negative ease correctly?
        #

        new_igp = SweaterIndividualGarmentParameters.objects.get(pk=igp.pk)

        # new as-knit measurements
        for k, v in list(as_knit_dict.items()):
            self.assertEqual(getattr(new_igp, k), v)

        # new as-worn measurements
        self.assertEqual(new_igp.armpit_height, 23.5)
        self.assertEqual(new_igp.waist_height_back, 11)
        self.assertEqual(new_igp.waist_height_front, 11)
        self.assertEqual(new_igp.sleeve_to_armcap_start_height, 19)

        # Fields not appearing in the form
        unchanged_attributes = [
            "back_cross_back_width",
            "waist_height_front",
            "back_neck_depth",
        ]

        for a in unchanged_attributes:
            self.assertEqual(getattr(new_igp, a), getattr(igp, a))

        #
        # Okay, now let's make a form from this IGP
        # Does it unadjust the negative ease correctly?
        #

        form = TweakSweaterIndividualGarmentParameters(user=igp.user, instance=new_igp)
        self.assertEqual(form.initial["armpit_height"], 19)
        self.assertEqual(form.initial["waist_height_back"], 9)
        self.assertEqual(form.initial["sleeve_to_armcap_start_height"], 19)


class ClassMethodsTest(django.test.TestCase):

    def test_missing_body_fields_full_body_hourglass(self):
        # BodyFactory fills in all values except cross_chest_distance
        body = BodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        self.assertFalse(missing_fields)

    def test_missing_body_fields_simple_body_hourglass(self):
        # SimpleBodyFactory only fills in:
        # waist_circ = 32
        # bust_circ = 41
        # wrist_circ = 6
        # bicep_circ = 12
        # armpit_to_med_hip = 16
        # med_hip_circ = 40
        # armpit_to_full_sleeve = 17.5
        # armhole_depth = 8
        body = SimpleBodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        missing_field_names = set(f.name for f in missing_fields)
        goal_set = set(
            [
                "upper_torso_circ",
                "elbow_circ",
                "armpit_to_elbow_sleeve",
                "armpit_to_waist",
                "armpit_to_tunic",
                "tunic_circ",
            ]
        )
        self.assertEqual(missing_field_names, goal_set)

    def test_missing_body_fields_full_body_half_hourglass(self):
        # BodyFactory fills in all values except cross_chest_distance
        body = BodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        self.assertFalse(missing_fields)

    def test_missing_body_fields_simple_body_half_hourglass(self):
        # SimpleBodyFactory only fills in:
        # waist_circ = 32
        # bust_circ = 41
        # wrist_circ = 6
        # bicep_circ = 12
        # armpit_to_med_hip = 16
        # med_hip_circ = 40
        # armpit_to_full_sleeve = 17.5
        # armhole_depth = 8
        body = SimpleBodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        missing_field_names = set(f.name for f in missing_fields)
        goal_set = set(
            [
                "upper_torso_circ",
                "elbow_circ",
                "armpit_to_elbow_sleeve",
                "armpit_to_waist",
                "armpit_to_tunic",
                "tunic_circ",
            ]
        )
        self.assertEqual(missing_field_names, goal_set)

    def test_missing_body_fields_full_body_non_hourglass(self):
        # BodyFactory fills in all values except cross_chest_distance
        body = BodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        self.assertFalse(missing_fields)

    def test_missing_body_fields_simple_body_non_hourglass(self):
        # SimpleBodyFactory only fills in:
        # waist_circ = 32
        # bust_circ = 41
        # wrist_circ = 6
        # bicep_circ = 12
        # armpit_to_med_hip = 16
        # med_hip_circ = 40
        # armpit_to_full_sleeve = 17.5
        # armhole_depth = 8
        body = SimpleBodyFactory()
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        self.assertFalse(missing_fields)

    def test_missing_body_fields_spot_checks(self):
        # BodyFactory fills in all values except cross_chest_distance
        body = BodyFactory()
        body.elbow_circ = None
        body.armpit_to_elbow_sleeve = None
        body.bust_circ = None
        body.tunic_circ = None
        body.armpit_to_low_hip = None
        pattern_spec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        missing_field_names = set(f.name for f in missing_fields)
        goal_set = set(
            ["elbow_circ", "armpit_to_elbow_sleeve", "tunic_circ", "bust_circ"]
        )
        self.assertEqual(missing_field_names, goal_set)

    def test_missing_body_fields_vests(self):
        # SimpleBodyFactory only fills in:
        # waist_circ = 32
        # bust_circ = 41
        # wrist_circ = 6
        # bicep_circ = 12
        # armpit_to_med_hip = 16
        # med_hip_circ = 40
        # armpit_to_full_sleeve = 17.5
        # armhole_depth = 8
        body = SimpleBodyFactory()
        pattern_spec = VestPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
        )
        missing_fields = SweaterIndividualGarmentParameters.missing_body_fields(
            pattern_spec
        )
        self.assertFalse(missing_fields)

    def test_garment(self):

        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        self.assertEqual(igp.construction, SDC.CONSTRUCTION_DROP_SHOULDER)

        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            drop_shoulder_additional_armhole_depth=None,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        self.assertEqual(igp.construction, SDC.CONSTRUCTION_SET_IN_SLEEVE)


class DropShoulderTests(django.test.TestCase):

    def test_can_make(self):
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        user = UserFactory()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()

    def test_drop_shoulder_neckline_depth(self):
        # Even though drop-shoulder armholes are bigger than set-in-sleeve, a neckline that is
        # defined 'above/below armhole' should be measured from where the armhole should be for
        # set-in-sleeves

        user = UserFactory()

        vectors = [
            (SDC.ABOVE_ARMPIT, 1),
            (SDC.ABOVE_ARMPIT, 0),
            (SDC.BELOW_ARMPIT, 1),
            (SDC.BELOW_ARMPIT, 0),
            (SDC.BELOW_SHOULDERS, 1),
            (SDC.BELOW_SHOULDERS, 0),
        ]

        for orientation, inches in vectors:
            ds_pspec = SweaterPatternSpecFactory(
                construction=SDC.CONSTRUCTION_DROP_SHOULDER,
                drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
                neckline_depth=inches,
                neckline_depth_orientation=orientation,
            )
            ds_igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                user, ds_pspec
            )
            ds_igp.full_clean()

            sis_pspec = SweaterPatternSpecFactory(
                construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
                neckline_depth=inches,
                neckline_depth_orientation=orientation,
            )
            sis_igp = SweaterIndividualGarmentParameters.make_from_patternspec(
                user, sis_pspec
            )
            sis_igp.full_clean()

            self.assertEqual(ds_igp.back_neck_depth, sis_igp.back_neck_depth)
            self.assertEqual(ds_igp.front_neck_depth, sis_igp.front_neck_depth)


class SweaterGradedGarmentParametersGradeTests(django.test.TestCase):

    def test_get_spec_source(self):
        grade = SweaterGradedGarmentParametersGradeFactory()
        self.assertEqual(
            grade.get_spec_source(), grade.graded_garment_parameters.pattern_spec
        )

    def test_missing_body_fields(self):
        # Note- we depend on the tests in ClassMethodTests to really cover _innder_missing_body_fields
        grade = GradeFactory()
        grade.upper_torso_circ = None
        grade.elbow_circ = None
        pattern_spec = GradedSweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
        )
        missing_fields = SweaterGradedGarmentParametersGrade.missing_body_fields(
            pattern_spec, grade
        )
        missing_field_names = set(f.name for f in missing_fields)
        goal_set = set(
            [
                "upper_torso_circ",
                "elbow_circ",
            ]
        )
        self.assertEqual(missing_field_names, goal_set)


class GradedSweaterGarmentParametersTests(django.test.TestCase):

    def test_make(self):
        pspec = GradedSweaterPatternSpecFactory()
        self.assertEqual(len(pspec.gradeset.grades), 5)  # santiy check
        ggp = SweaterGradedGarmentParameters.make_from_patternspec(pspec.user, pspec)
        self.assertEqual(len(ggp.all_grades), 5)

    def test_missing_body_fields(self):
        pattern_spec = GradedSweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            sleeve_length=SDC.SLEEVE_ELBOW,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            torso_length=SDC.TUNIC_LENGTH,
        )
        grade1 = pattern_spec.gradeset.grades.get(bust_circ=42)
        grade5 = pattern_spec.gradeset.grades.get(bust_circ=46)
        grade1.upper_torso_circ = None
        grade1.elbow_circ = None
        grade1.save()
        grade5.upper_torso_circ = None
        grade5.armpit_to_tunic = None
        grade5.save()
        missing_fields = SweaterGradedGarmentParameters.missing_body_fields(
            pattern_spec
        )
        missing_field_names = set(f.name for f in missing_fields)
        goal_set = set(
            [
                "upper_torso_circ",
                "armpit_to_tunic",
                "elbow_circ",
            ]
        )
        self.assertEqual(missing_field_names, goal_set)
