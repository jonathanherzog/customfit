# -*- coding: utf-8 -*-

import datetime
import itertools
import unittest.mock as mock

import pytz
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from customfit.bodies.factories import BodyFactory, get_csv_body
from customfit.stitches.factories import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.uploads.factories import create_individual_pattern_picture
from customfit.uploads.models import IndividualPatternPicture
from customfit.userauth.factories import UserFactory

from ..factories import (
    ApprovedSweaterPatternFactory,
    GradedSweaterPatternPiecesFactory,
    SweaterDesignFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    create_csv_combo,
    pattern_from_csv_combo,
)
from ..helpers import sweater_design_choices as SDC
from ..models import (
    ButtonBand,
    GradedSweaterPattern,
    SweaterIndividualGarmentParameters,
    SweaterPattern,
    SweaterPatternPieces,
    SweaterSchematic,
)


class SweaterPatternTestGeneral(TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_default_clean(self):
        p = SweaterPatternFactory()
        p.full_clean()

    def test_default_save_delete(self):
        p = SweaterPatternFactory()
        p.save()
        p.delete()


class SweaterPatternTestErrors(TestCase):
    """
    This test case contains combinations of body/pattern/gauge
    that caused errors at some point. Collected here for debugging
    and regression-testing.
    """

    def test_problem_body1_design5_gaugeDK(self):
        pattern_from_csv_combo("Test 1", "DK Stitch repeats", "Test 5")

    def test_problem_body4_design7_gaugeSport(self):
        pattern_from_csv_combo("Test 7", "Sport stitch repeats", "Test 7")

    def test_problem_body3_design8_gaugeDKst(self):
        pattern_from_csv_combo("Test 6", "DK St st", "Test 8")

    def test_problem_body3_design4_gaugeDK(self):
        pattern_from_csv_combo("Test 6", "DK St st", "Test 4")

    def test_problem_body4_design4_gaugeDK(self):
        pattern_from_csv_combo("Test 7", "DK St st", "Test 4")

    def test_problem_body3_design4_gaugeBulky(self):
        pattern_from_csv_combo("Test 6", "Bulky St st", "Test 4")

    def test_problem_body2_design7_gaugeBulky(self):
        pattern_from_csv_combo("Test 5", "Bulky St st", "Test 7")

    def test_problem_body3_design8_gaugeDKrepeats(self):
        pattern_from_csv_combo("Test 6", "DK Stitch repeats", "Test 8")

    def test_problem_body2_design5_gaugeDKrepeats(self):
        pattern_from_csv_combo("Test 5", "DK Stitch repeats", "Test 5")

    def test_problem_body3_design1_gaugeCascade(self):
        pattern_from_csv_combo("Test 6", "Cascade 220 St st", "Test 1")

    def test_problem_body1_design1_gaugeCascade(self):
        pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 1")

    def test_problem_body4_design7_gaugeBulky(self):
        pattern_from_csv_combo("Test 7", "Bulky St st", "Test 7")

    def test_problem_body4_design8_gaugeBulky(self):
        pattern_from_csv_combo("Test 7", "Bulky St st", "Test 8")

    def test_problem_body2_design8_gaugeDKRepeats(self):
        pattern_from_csv_combo("Test 5", "DK Stitch repeats", "Test 8")

    def test_problem_body2_design1_gaugeBulky(self):
        pattern_from_csv_combo("Test 5", "Bulky St st", "Test 1")

    def test_problem_body1_design5_gaugeDKRepeats(self):
        pattern_from_csv_combo("Test 4", "DK Stitch repeats", "Test 5")

    def test_problem_body3_sport_stitch_repeats_design5(self):
        pattern_from_csv_combo("Test 6", "Sport stitch repeats", "Test 2")

    def test_problem_body2_bulky_st_design5(self):
        pattern_from_csv_combo("Test 2", "Bulky St st", "Test 7")

    def test_problem_test1_bulky_st_design5(self):
        pattern_from_csv_combo("Test 4", "Bulky St st", "Test 7")

    def test_test9_assertion_error(self):
        body = get_csv_body("Test 9")
        pspec = SweaterPatternSpecFactory(body=body)
        p = SweaterPatternFactory.from_pspec(pspec)
        p.full_clean()

    def test_problem_test5_DK_Stitch_repeats_design7(self):
        pattern_from_csv_combo("Test 8", "DK Stitch repeats", "Test 7")

    def test_problem_body3_DKStitchRepeats_Design7(self):
        pattern_from_csv_combo("Test 6", "DK Stitch repeats", "Test 7")

    def test_no_waist_decreases(self):
        pspec = create_csv_combo("Test 1", "Fingering St st", "Test 7")
        p = SweaterPatternFactory.from_pspec(pspec)
        p.full_clean()

    def test_xmod_bigger_then_mody(self):
        swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=4, additional_stitches=6
        )
        pspec = SweaterPatternSpecFactory(swatch=swatch)
        p = SweaterPatternFactory.from_pspec(pspec)
        p.full_clean()

    def test_pattern_generates_buttonband_does_not(self):
        """
        We successfully generated and sold a pattern from these parameters
        which we could not subsequently render, because the borked
        stitches_number could not be made into a buttonband (but we were not
        checking for this in pattern generation, just running across it in
        rendering). We should now ensure that buttonbands are generate-able
        during pattern creation.
        """

        error_report_body_dict = {
            "armpit_to_short_sleeve": 1.0,
            "low_hip_circ": 38.5,
            "high_hip_circ": 35.25,
            "upper_torso_circ": 35.5,
            "tunic_circ": 36.5,
            "armpit_to_elbow_sleeve": 5.5,
            "featured_pic": None,
            "armpit_to_low_hip": 7.5 + 6.5,
            "archived": False,
            "armpit_to_tunic": 7.5 + 11.5,
            "bicep_circ": 11.0,
            "armpit_to_waist": 7.5,
            "forearm_circ": 7.5,
            "inter_nipple_distance": 7.0,
            "wrist_circ": 6.25,
            "med_hip_circ": 37.0,
            "armpit_to_three_quarter_sleeve": 10.0,
            "armhole_depth": 8.5,
            "armpit_to_high_hip": 7.5 + 3.0,
            "elbow_circ": 10.5,
            "waist_circ": 35.0,
            "armpit_to_med_hip": 7.5 + 4.0,
            "notes": "",
            "bust_circ": 39.0,
            "armpit_to_full_sleeve": 15.5,
        }
        error_report_body = BodyFactory(**error_report_body_dict)

        error_report_swatch_dict = {
            "stitches_per_repeat": 2,
            "stitches_length": 5.5,
            "archived": False,
            "additional_stitches": 0,
            "full_swatch_width": 7.0,
            "yarn_maker": "",
            "notes": "",
            "full_swatch_weight": 12.0,
            "rows_number": 19.0,
            "featured_pic": None,
            "length_per_hank": 356.0,
            "yarn_name": "",
            "full_swatch_height": 5.5,
            "use_repeats": True,
            "stitches_number": 504.0,
            "needle_size": "9",
            "weight_per_hank": 100.0,
            "rows_length": 3.25,
        }
        error_report_swatch = SwatchFactory(**error_report_swatch_dict)

        design_params = {
            "torso_length": "low_hip_length",
            "garment_type": "CARDIGAN_SLEEVED",
            "sleeve_edging_height": 1.0,
            "sleeve_shape": "SLEEVE_TAPERED",
            "neckline_depth": 1.0,
            "sleeve_length": "SLEEVE_THREEQUARTER",
            "neckline_style": "NECK_VEE",
            "number_of_buttons": 0,
            "front_allover_stitch": None,
            "button_band_allowance": 1.0,
            "neckline_width": "NECK_NARROW",
            "garment_fit": "FIT_HOURGLASS_AVERAGE",
            "neckline_depth_orientation": "BELOW_ARMPIT",
            "button_band_edging_height": 1.0,
            "hip_edging_height": 2.0,
            "back_allover_stitch": None,
            "neck_edging_height": None,
        }

        pspec = SweaterPatternSpecFactory(
            body=error_report_body, swatch=error_report_swatch, **design_params
        )

        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        gp.save()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        ips.full_clean()
        ips.save()
        with self.assertRaises(AssertionError):
            ipp = SweaterPatternPieces.make_from_individual_pieced_schematic(ips)
            ipp.full_clean()

    def test_drop_shoulder_bicep_amrhole_mismatch(self):
        # We were getting a bug where drop-shoulder sleeves were bigger than the armhole.
        swatch = SwatchFactory(
            rows_number=29,
            rows_length=4,
            stitches_number=22,
            stitches_length=4,
            use_repeats=True,
            stitches_per_repeat=21,
            additional_stitches=2,
        )
        pspec = SweaterPatternSpecFactory(
            sleeve_length=SDC.SLEEVE_FULL,
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            sleeve_edging_height=4.0,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            garment_fit=SDC.FIT_WOMENS_TIGHT,
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW,
            swatch=swatch,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(
            pspec.user, pspec
        )
        igp.save()
        self.assertEqual(igp.bicep_width, 2 * igp.armhole_depth)

        schematic = SweaterSchematic.make_from_garment_parameters(pspec.user, igp)
        schematic.save()
        self.assertEqual(
            schematic.sleeve.bicep_width,
            schematic.sweater_back.armhole_depth
            + schematic.sweater_front.armhole_depth,
        )

        pieces = SweaterPatternPieces.make_from_individual_pieced_schematic(schematic)
        pieces.save()
        sleeve = pieces.sleeve
        front = pieces.sweater_front
        back = pieces.sweater_back
        self.assertAlmostEqual(
            sleeve.actual_bicep,
            front.actual_armhole_depth + back.actual_armhole_depth,
            delta=0.25,
        )


class PatternMethodsTest(TestCase):

    def test_circumferences(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 1")
        self.assertEqual(p.total_finished_bust(), 39.6)
        self.assertEqual(p.total_finished_waist(), 34)
        self.assertEqual(p.total_finished_hip(), 38)

    def test_neck_edging_methods(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 1")
        self.assertEqual(p.vee_neck(), True)
        self.assertEqual(p.is_cardigan(), False)
        self.assertEqual(p.has_sleeves(), True)
        self.assertEqual(p.total_neckline_pickup_stitches(), 127)
        self.assertEqual(p.neck_edging_height_in_rows(), 7)
        self.assertAlmostEqual(p.area(), 990.3, 1)

    def test_buttonband(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 4")
        bb = p.get_buttonband()
        self.assertIsInstance(bb, ButtonBand)

    # TODO: Make these next four tests more robust and stop using CSV vectors
    def test_neck_buttonband_error1(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 1")
        pspec = p.get_spec_source()
        pspec.button_band_edging_height = 2
        self.assertFalse(p.has_button_band())

    def test_neck_buttonband_error2(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 1")
        self.assertFalse(p.has_button_band())

    def test_neck_buttonband_error3(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 4")
        self.assertTrue(p.has_button_band())

    def test_neck_buttonband_error4(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 4")
        pspec = p.get_spec_source()
        pspec.button_band_edging_height = 0
        self.assertFalse(p.has_button_band())

    def test_yards_and_weight(self):
        p = pattern_from_csv_combo("Test 1", "Cascade 220 St st", "Test 4")
        # inputs
        self.assertAlmostEqual(p.area(), 1218.05, 2)
        self.assertEqual(p.swatch.full_swatch_height, 7.75)
        self.assertEqual(p.swatch.full_swatch_width, 5.25)
        self.assertEqual(p.swatch.full_swatch_weight, 19)
        self.assertEqual(p.swatch.weight_per_hank, 100)
        self.assertEqual(p.swatch.length_per_hank, 220)

        # outputs
        self.assertEqual(p.weight(), 569)
        self.assertEqual(p.yards(), 1252)
        self.assertEqual(p.hanks(), 6)

    # area tests
    def test_neck_trim_area(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_length=1,
            rows_number=10,
            stitches_length=1,
            stitches_number=5,
            user=user,
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.PULLOVER_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
            user=user,
        )
        p = SweaterPatternFactory.from_pspec(pspec)

        self.assertEqual(p.neck_edging_height_in_rows(), 10)
        self.assertEqual(p.total_neckline_pickup_stitches(), 117)
        self.assertEqual(p.pieces._neck_trim_area(), 23.4)

    # area tests
    def test_armhole_trim_area(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_length=1,
            rows_number=10,
            stitches_length=1,
            stitches_number=5,
            user=user,
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.PULLOVER_VEST,
            neckline_style=SDC.NECK_VEE,
            armhole_edging_height=2,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            user=user,
        )
        p = SweaterPatternFactory.from_pspec(pspec)

        self.assertEqual(p.total_armhole_stitches(), 97)
        self.assertEqual(p.pieces._armhole_trim_area(), 77.6)

    def test_trim_area_pullover(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_length=1,
            rows_number=10,
            stitches_length=1,
            stitches_number=5,
            user=user,
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.PULLOVER_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            armhole_edging_height=2,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
            user=user,
        )
        p = SweaterPatternFactory.from_pspec(pspec)

        self.assertEqual(p.pieces._armhole_trim_area(), 77.6)
        self.assertEqual(p.pieces._neck_trim_area(), 23.4)
        self.assertEqual(p.pieces._trim_area(), 101)

    def test_trim_area_pullover_crew_neck_cardi(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_length=1,
            rows_number=10,
            stitches_length=1,
            stitches_number=5,
            user=user,
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
            armhole_edging_height=2,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            user=user,
        )
        p = SweaterPatternFactory.from_pspec(pspec)

        self.assertEqual(p.pieces._armhole_trim_area(), 77.6)
        self.assertEqual(p.pieces._neck_trim_area(), 25.4)
        self.assertEqual(p.get_buttonband().area(), 72.0)
        self.assertEqual(p.pieces._trim_area(), 175)

    def test_trim_area_pullover_vee_neck_cardi(self):
        user = UserFactory()
        swatch = SwatchFactory(
            rows_length=1,
            rows_number=10,
            stitches_length=1,
            stitches_number=5,
            user=user,
        )
        pspec = SweaterPatternSpecFactory(
            swatch=swatch,
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=2,
            button_band_edging_height=2,
            button_band_edging_stitch=StitchFactory(name="Garter Stitch"),
            number_of_buttons=7,
            armhole_edging_height=2,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            user=user,
        )
        p = SweaterPatternFactory.from_pspec(pspec)

        self.assertEqual(p.pieces._armhole_trim_area(), 77.6)
        self.assertEqual(p.get_buttonband().area(), 116.8)
        self.assertAlmostEqual(p.pieces._trim_area(), 194.4, 1)

    def test_schematic_images(self):
        sleeve_dict = {
            SDC.SLEEVE_FULL: "img/schematics/set-in-sleeve/Long-Sleeve.png",
            SDC.SLEEVE_THREEQUARTER: "img/schematics/set-in-sleeve/3-4-Sleeve.png",
            SDC.SLEEVE_ELBOW: "img/schematics/set-in-sleeve/Elbow-Sleeve.png",
            SDC.SLEEVE_SHORT: "img/schematics/set-in-sleeve/Short-Sleeve.png",
        }
        pullover_dict = {
            SDC.NECK_VEE: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-V.png",
            SDC.NECK_CREW: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Crew.png",
            SDC.NECK_SCOOP: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Scoop.png",
            SDC.NECK_BOAT: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Boat.png",
        }

        for sleeve_pair, neck_pair in zip(
            list(sleeve_dict.items()), list(pullover_dict.items())
        ):
            (sleeve_length, sleeve_goal_image) = sleeve_pair
            (neckline, neck_goal_image) = neck_pair
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED,
                sleeve_length=sleeve_length,
                neckline_style=neckline,
                name="goo",
            )
            p = SweaterPatternFactory.from_pspec(pspec)

            sleeve_schematic_image = p.get_sleeve_schematic_image()
            self.assertEqual(sleeve_schematic_image, sleeve_goal_image)

            front_schematic_image = p.get_front_schematic_image()
            self.assertEqual(front_schematic_image, neck_goal_image)

            back_schematic_image = p.get_back_schematic_image()
            self.assertEqual(
                back_schematic_image, "img/schematics/set-in-sleeve/Hourglass-Back.png"
            )

    def test_schematic_images_cardigan_front(self):

        necklines = [SDC.NECK_BOAT, SDC.NECK_CREW, SDC.NECK_SCOOP, SDC.NECK_VEE]
        percentages = [100, 50, 0, -50]
        cardi_dict = {
            SDC.NECK_VEE: "img/schematics/set-in-sleeve/Hourglass-Front-Cardi-V.png",
            SDC.NECK_CREW: "img/schematics/set-in-sleeve/Hourglass-Front-Cardi-Crew.png",
            SDC.NECK_SCOOP: "img/schematics/set-in-sleeve/Hourglass-Front-Cardi-Scoop.png",
            SDC.NECK_BOAT: "img/schematics/set-in-sleeve/Hourglass-Front-Cardi-Boat.png",
        }
        for neckline, percent in itertools.product(necklines, percentages):
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                button_band_allowance_percentage=percent,
                neckline_style=neckline,
                button_band_edging_height=1,
                number_of_buttons=5,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                name="goo",
            )
            p = SweaterPatternFactory.from_pspec(pspec)
            schematic_image = p.get_front_schematic_image()
            if percent == 100:
                self.assertEqual(
                    schematic_image,
                    "img/schematics/set-in-sleeve/Hourglass-Front-Cardi-Straight-Neck.png",
                )
            else:
                goal_image = cardi_dict[neckline]
                self.assertEqual(schematic_image, goal_image)

    def test_fit_text(self):

        def _inner_test_fit_text(parameter, text):
            design = SweaterPatternSpecFactory(garment_fit=parameter)
            pattern = SweaterPatternFactory.from_pspec(design)
            self.assertEqual(pattern.fit_text, text)

        _inner_test_fit_text(SDC.FIT_HOURGLASS_TIGHT, "Hourglass close fit")
        _inner_test_fit_text(SDC.FIT_HOURGLASS_AVERAGE, "Hourglass average fit")
        _inner_test_fit_text(SDC.FIT_HOURGLASS_RELAXED, "Hourglass relaxed fit")
        _inner_test_fit_text(SDC.FIT_HOURGLASS_OVERSIZED, "Hourglass oversized fit")

    def test_pattern_url(self):

        myo_pattern = SweaterPatternFactory()
        with self.settings(STATIC_URL="http://example.com/"):
            self.assertEqual(
                myo_pattern.preferred_picture_url,
                "http://example.com/img/Build-Your-Own-Photo-Card.png",
            )

        design_origin = SweaterDesignFactory()
        design_pattern = SweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(design_origin=design_origin)
        )
        with self.settings(STATIC_URL="http://example.com/"):
            self.assertRegex(
                design_pattern.preferred_picture_url,
                "http://example.com/media/classic_images/[-0-9a-f]+image.jpg",
            )

        with_pictures = SweaterPatternFactory()
        create_individual_pattern_picture(with_pictures)
        with self.settings(STATIC_URL="http://example.com/"):
            self.assertRegex(
                with_pictures.preferred_picture_url,
                "http://example.com/media/.*cutout.png",
            )

        with_featured_pic = SweaterPatternFactory()
        featured_pic = IndividualPatternPicture(
            picture=SimpleUploadedFile("image.jpg", None), object=with_featured_pic
        ).save()
        with_featured_pic.featured_pic = featured_pic
        with_featured_pic.save()
        with self.settings(STATIC_URL="http://example.com/"):
            self.assertRegex(
                with_featured_pic.preferred_picture_url,
                "http://example.com/media/.*image.jpg",
            )


class GradedSweaterPatternTests(TestCase):

    def test_make(self):
        pieces = GradedSweaterPatternPiecesFactory.from_pspec_kwargs()
        GradedSweaterPattern.make_from_graded_pattern_pieces(pieces)
