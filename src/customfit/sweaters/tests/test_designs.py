# -*- coding: utf-8 -*-

import unittest.mock as mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from customfit.designs.tests import AdditionalElementsTestsBase
from customfit.helpers.math_helpers import CompoundResult
from customfit.stitches.factories import StitchFactory
from customfit.stitches.models import Stitch
from customfit.swatches.factories import GaugeFactory, SwatchFactory

from ..factories import (
    AdditionalBackElementFactory,
    AdditionalFrontElementFactory,
    AdditionalFullTorsoElementFactory,
    AdditionalSleeveElementFactory,
    SweaterDesignFactory,
)
from ..helpers import sweater_design_choices as SDC
from ..models import AdditionalBodyPieceElement, AdditionalSleeveElement


class SweaterDesignBaseMethodTests(TestCase):

    def test_pullover_sleeved(self):
        des = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED, name="test design"
        )
        des.full_clean()
        self.assertTrue(des.has_sweater_back())
        self.assertTrue(des.has_sweater_front())
        self.assertTrue(des.has_sleeves())
        self.assertFalse(des.has_vest_back())
        self.assertFalse(des.has_vest_front())
        self.assertFalse(des.has_cardigan_sleeved())
        self.assertFalse(des.has_cardigan_vest())
        self.assertFalse(des.is_cardigan())
        self.assertTrue(des.has_sleeves())
        self.assertFalse(des.sleeve_is_bell())
        self.assertFalse(des.is_vest())

        self.assertEqual(str(des), "test design")

        self.assertListEqual(
            des.supported_sleeve_length_choices(),
            [
                (SDC.SLEEVE_SHORT, "Short sleeve"),
                (SDC.SLEEVE_ELBOW, "Elbow-length sleeve"),
                (SDC.SLEEVE_THREEQUARTER, "Three-quarter length sleeve"),
                (SDC.SLEEVE_FULL, "Full-length sleeve"),
            ],
        )

        self.assertListEqual(
            des.supported_torso_length_choices(), SDC.HIP_LENGTH_CHOICES
        )

        self.assertEqual(des.is_veeneck(), True)

        self.assertEqual(des.neck_edging_stitch_patterntext(), "1x1 Ribbing")

        self.assertEqual(des.neckline_style_patterntext(), "Average-width vee neck")

        self.assertEqual(
            des.neckline_depth_orientation_patterntext(), "Below shoulders"
        )

        self.assertEqual(des.neckline_width_patterntext_short_form(), "Average-width")

        self.assertEqual(des.torso_length_patterntext(), "Average")

        self.assertEqual(des.hip_edging_stitch_patterntext(), "1x1 Ribbing")

        self.assertEqual(des.sleeve_length_patterntext(), "Full-length tapered sleeve")

        self.assertEqual(des.sleeve_length_patterntext_short_form(), "Full-length")

        self.assertEqual(des.sleeve_edging_stitch_patterntext(), "1x1 Ribbing")

        self.assertEqual(des.armhole_edging_stitch_patterntext(), None)

        self.assertEqual(des.button_band_edging_stitch_patterntext(), None)

        self.assertListEqual(
            des.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                StitchFactory(name="Sugar Cube Stitch"),
            ],
        )
        # Additional elements
        back_el_stitch = StitchFactory(name="back element stitch")
        front_el_stitch = StitchFactory(name="front element stitch")
        sleeve_el_stitch = StitchFactory(name="sleeve element stitch")
        full_el_stitch = StitchFactory(name="full-torso element stitch")
        design = SweaterDesignFactory(garment_type=SDC.PULLOVER_SLEEVED)
        AdditionalBackElementFactory(design=design, stitch=back_el_stitch)
        AdditionalSleeveElementFactory(design=design, stitch=sleeve_el_stitch)
        AdditionalFrontElementFactory(design=design, stitch=front_el_stitch)
        AdditionalFullTorsoElementFactory(design=design, stitch=full_el_stitch)
        design.full_clean()
        self.assertListEqual(
            design.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                back_el_stitch,
                full_el_stitch,
                front_el_stitch,
                sleeve_el_stitch,
                StitchFactory(name="Sugar Cube Stitch"),
            ],
        )

    def test_individual_pullover_vest(self):
        des = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            armhole_edging_height=0.25,
        )
        des.full_clean()
        self.assertFalse(des.has_sweater_back())
        self.assertFalse(des.has_sweater_front())
        self.assertFalse(des.has_sleeves())
        self.assertTrue(des.has_vest_back())
        self.assertTrue(des.has_vest_front())
        self.assertFalse(des.has_cardigan_vest())
        self.assertFalse(des.has_cardigan_sleeved())
        self.assertFalse(des.is_cardigan())
        self.assertTrue(des.is_vest())

        # testing template properties
        self.assertListEqual(des.supported_sleeve_length_choices(), [])
        self.assertListEqual(
            des.supported_torso_length_choices(), SDC.HIP_LENGTH_CHOICES
        )
        self.assertEqual(des.is_veeneck(), True)
        self.assertEqual(des.neck_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(des.neckline_style_patterntext(), "Average-width vee neck")
        self.assertEqual(des.neckline_width_patterntext_short_form(), "Average-width")
        self.assertEqual(
            des.neckline_depth_orientation_patterntext(), "Below shoulders"
        )
        self.assertEqual(des.torso_length_patterntext(), "Average")
        self.assertEqual(des.hip_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(des.sleeve_length_patterntext(), None)
        self.assertEqual(des.sleeve_length_patterntext_short_form(), None)
        self.assertEqual(des.sleeve_edging_stitch_patterntext(), None)
        self.assertEqual(des.armhole_edging_stitch_patterntext(), "Garter Stitch")
        self.assertEqual(des.button_band_edging_stitch_patterntext(), None)

        self.assertListEqual(
            des.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                StitchFactory(name="Garter Stitch"),
            ],
        )

        # Additional elements
        back_el_stitch = StitchFactory(name="back element stitch")
        front_el_stitch = StitchFactory(name="front element stitch")
        sleeve_el_stitch = StitchFactory(name="sleeve element stitch")
        full_el_stitch = StitchFactory(name="full-torso element stitch")
        design = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="Garter Stitch"),
            armhole_edging_height=0.25,
        )
        AdditionalBackElementFactory(design=design, stitch=back_el_stitch)
        AdditionalSleeveElementFactory(design=design, stitch=sleeve_el_stitch)
        AdditionalFrontElementFactory(design=design, stitch=front_el_stitch)
        AdditionalFullTorsoElementFactory(design=design, stitch=full_el_stitch)
        design.full_clean()
        self.assertListEqual(
            design.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                back_el_stitch,
                full_el_stitch,
                front_el_stitch,
                StitchFactory(name="Garter Stitch"),
            ],
        )

    def test_individual_cardigan_sleeved(self):
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
            sleeve_shape=SDC.SLEEVE_BELL,
            bell_type=SDC.BELL_MODERATE,
        )

        des.full_clean()
        self.assertTrue(des.has_sweater_back())
        self.assertFalse(des.has_sweater_front())
        self.assertTrue(des.has_sleeves())
        self.assertFalse(des.has_vest_back())
        self.assertFalse(des.has_vest_front())
        self.assertTrue(des.has_cardigan_sleeved())
        self.assertFalse(des.has_cardigan_vest())
        self.assertTrue(des.is_cardigan())
        self.assertTrue(des.sleeve_is_bell())
        self.assertFalse(des.is_vest())

        # testing template properties
        self.assertListEqual(
            des.supported_sleeve_length_choices(),
            [
                (SDC.SLEEVE_SHORT, "Short sleeve"),
                (SDC.SLEEVE_ELBOW, "Elbow-length sleeve"),
                (SDC.SLEEVE_THREEQUARTER, "Three-quarter length sleeve"),
                (SDC.SLEEVE_FULL, "Full-length sleeve"),
            ],
        )
        self.assertListEqual(
            des.supported_torso_length_choices(), SDC.HIP_LENGTH_CHOICES
        )
        self.assertEqual(des.is_veeneck(), True)
        self.assertEqual(des.neck_edging_stitch_patterntext(), None)
        self.assertEqual(des.neckline_style_patterntext(), "Average-width vee neck")
        self.assertEqual(des.neckline_width_patterntext_short_form(), "Average-width")
        self.assertEqual(
            des.neckline_depth_orientation_patterntext(), "Below shoulders"
        )
        self.assertEqual(des.torso_length_patterntext(), "Average")
        self.assertEqual(des.hip_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(
            des.sleeve_length_patterntext(), "Full-length moderate bell sleeve"
        )
        self.assertEqual(des.sleeve_length_patterntext_short_form(), "Full-length")
        self.assertEqual(des.sleeve_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(des.armhole_edging_stitch_patterntext(), None)
        self.assertEqual(des.button_band_edging_stitch_patterntext(), "Seed Stitch")

        self.assertListEqual(
            des.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                StitchFactory(name="Sugar Cube Stitch"),
                StitchFactory(name="Seed Stitch"),
            ],
        )

        # Additional elements
        back_el_stitch = StitchFactory(name="back element stitch")
        front_el_stitch = StitchFactory(name="front element stitch")
        sleeve_el_stitch = StitchFactory(name="sleeve element stitch")
        full_el_stitch = StitchFactory(name="full-torso element stitch")
        design = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
            sleeve_shape=SDC.SLEEVE_BELL,
            bell_type=SDC.BELL_MODERATE,
        )
        AdditionalBackElementFactory(design=design, stitch=back_el_stitch)
        AdditionalSleeveElementFactory(design=design, stitch=sleeve_el_stitch)
        AdditionalFrontElementFactory(design=design, stitch=front_el_stitch)
        AdditionalFullTorsoElementFactory(design=design, stitch=full_el_stitch)
        design.full_clean()
        self.assertListEqual(
            design.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                back_el_stitch,
                full_el_stitch,
                front_el_stitch,
                sleeve_el_stitch,
                StitchFactory(name="Sugar Cube Stitch"),
                StitchFactory(name="Seed Stitch"),
            ],
        )

    def test_individual_cardigan_vest(self):
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_stitch=StitchFactory(name="2x2 Ribbing"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
            armhole_edging_height=0.5,
            # And throw in some new stitches to test a corner
            # case of stitches_used
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_stitch=StitchFactory(name="Seed Stitch"),
        )
        des.full_clean()
        self.assertFalse(des.has_sweater_back())
        self.assertFalse(des.has_sweater_front())
        self.assertFalse(des.has_sleeves())
        self.assertTrue(des.has_vest_back())
        self.assertFalse(des.has_vest_front())
        self.assertFalse(des.has_cardigan_sleeved())
        self.assertTrue(des.has_cardigan_vest())
        self.assertTrue(des.is_cardigan())
        self.assertTrue(des.is_vest())

        # testing template properties
        self.assertListEqual(des.supported_sleeve_length_choices(), [])
        self.assertListEqual(
            des.supported_torso_length_choices(), SDC.HIP_LENGTH_CHOICES
        )
        self.assertEqual(des.is_veeneck(), False)
        self.assertEqual(des.neck_edging_stitch_patterntext(), "Seed Stitch")
        self.assertEqual(des.neckline_style_patterntext(), "Average-width crew neck")
        self.assertEqual(des.neckline_width_patterntext_short_form(), "Average-width")
        self.assertEqual(
            des.neckline_depth_orientation_patterntext(), "Below shoulders"
        )
        self.assertEqual(des.torso_length_patterntext(), "Average")
        self.assertEqual(des.hip_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(des.sleeve_length_patterntext(), None)
        self.assertEqual(des.sleeve_length_patterntext_short_form(), None)
        self.assertEqual(des.sleeve_edging_stitch_patterntext(), None)
        self.assertEqual(des.armhole_edging_stitch_patterntext(), "1x1 Ribbing")
        self.assertEqual(des.button_band_edging_stitch_patterntext(), "2x2 Ribbing")

        self.assertListEqual(
            des.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                StitchFactory(name="2x2 Ribbing"),
                StitchFactory(name="Seed Stitch"),
            ],
        )

        # Additional elements
        back_el_stitch = StitchFactory(name="back element stitch")
        front_el_stitch = StitchFactory(name="front element stitch")
        sleeve_el_stitch = StitchFactory(name="sleeve element stitch")
        full_el_stitch = StitchFactory(name="full-torso element stitch")
        design = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_stitch=StitchFactory(name="2x2 Ribbing"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
            armhole_edging_height=0.5,
            # And throw in some new stitches to test a corner
            # case of stitches_used
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_stitch=StitchFactory(name="Seed Stitch"),
        )

        AdditionalBackElementFactory(design=design, stitch=back_el_stitch)
        AdditionalSleeveElementFactory(design=design, stitch=sleeve_el_stitch)
        AdditionalFrontElementFactory(design=design, stitch=front_el_stitch)
        AdditionalFullTorsoElementFactory(design=design, stitch=full_el_stitch)
        design.full_clean()
        self.assertListEqual(
            design.stitches_used(),
            [
                StitchFactory(name="1x1 Ribbing"),
                StitchFactory(name="Other Stitch"),
                StitchFactory(name="Stockinette"),
                back_el_stitch,
                full_el_stitch,
                front_el_stitch,
                StitchFactory(name="2x2 Ribbing"),
                StitchFactory(name="Seed Stitch"),
            ],
        )

    def test_pullover_sleeved_no_hems(self):
        des = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neck_edging_height=0,
            neck_edging_stitch=None,
            sleeve_edging_stitch=None,
            sleeve_edging_height=0,
        )
        des.full_clean()
        self.assertIsNone(des.neck_edging_stitch_patterntext())
        self.assertIsNone(des.sleeve_edging_stitch_patterntext())

    def test_vneck_cardigan_vest_no_hems(self):
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neck_edging_height=0,
            neck_edging_stitch=None,
            sleeve_edging_stitch=None,
            sleeve_edging_height=0,
            armhole_edging_stitch=None,
            armhole_edging_height=0,
            button_band_allowance=5,
            button_band_edging_stitch=None,
            button_band_edging_height=0,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_edging_stitch_patterntext())
        self.assertIsNone(des.armhole_edging_stitch_patterntext())

    def test_short_sleeve(self):
        gd = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_length=SDC.SLEEVE_SHORT,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
        )

        gd.full_clean()
        self.assertListEqual(
            gd.supported_sleeve_length_choices(),
            [
                (SDC.SLEEVE_SHORT, "Short sleeve"),
                (SDC.SLEEVE_ELBOW, "Elbow-length sleeve"),
                (SDC.SLEEVE_THREEQUARTER, "Three-quarter length sleeve"),
                (SDC.SLEEVE_FULL, "Full-length sleeve"),
            ],
        )
        self.assertListEqual(
            gd.supported_torso_length_choices(), SDC.HIP_LENGTH_CHOICES
        )

    def test_button_band(self):

        # Should be fine
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertEqual(des.button_band_allowance, 2)
        self.assertIsNone(des.button_band_allowance_percentage)

        # Should be fine
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance_percentage=50,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_allowance)
        self.assertEqual(des.button_band_allowance_percentage, 50)

        # Should be fine
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance_percentage=0,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_allowance)
        self.assertEqual(des.button_band_allowance_percentage, 0)

        # Should be fine
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance_percentage=100,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_allowance)
        self.assertEqual(des.button_band_allowance_percentage, 100)

        # Should be fine
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance_percentage=50.5,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_allowance)
        self.assertEqual(des.button_band_allowance_percentage, 50.5)

        # Should be fine-- negative button-band allowances are okay
        des = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
            button_band_edging_height=2,
            button_band_allowance_percentage=-1,
            number_of_buttons=7,
        )
        des.full_clean()
        self.assertIsNone(des.button_band_allowance)
        self.assertEqual(des.button_band_allowance_percentage, -1)

        # button_band_allowance_percentage should be 100 or less
        with self.assertRaises(ValidationError):
            des = SweaterDesignFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
                button_band_edging_height=2,
                button_band_allowance_percentage=101,
                number_of_buttons=7,
            )
            des.full_clean()

        # cannot have both button_band_allowance
        # and button_band_allowance_percentage
        with self.assertRaises(ValidationError):
            des = SweaterDesignFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                button_band_edging_stitch=StitchFactory(name="Seed Stitch"),
                button_band_edging_height=2,
                button_band_allowance=4,
                button_band_allowance_percentage=50,
                number_of_buttons=7,
            )
            des.full_clean()

    def test_button_band_to_fill_allowance_test(self):
        des1 = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=2,
            button_band_allowance=2,
            number_of_buttons=7,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=0.5,
        )
        self.assertTrue(des1.button_band_to_fill_allowance())

        des2 = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=2,
            button_band_allowance=3,
            number_of_buttons=7,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=0.5,
        )
        self.assertFalse(des2.button_band_to_fill_allowance())

        des3 = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_height=2,
            button_band_allowance_percentage=75,
            number_of_buttons=7,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=0.5,
        )
        self.assertFalse(des3.button_band_to_fill_allowance())

    def test_compatible_swatch(self):
        swatch = SwatchFactory()
        des = SweaterDesignFactory()

        with mock.patch.object(Stitch, "is_compatible", return_value=True):
            self.assertTrue(des.compatible_swatch(swatch))

        with mock.patch.object(Stitch, "is_compatible", return_value=False):
            self.assertFalse(des.compatible_swatch(swatch))

    def test_stitches_used(self):
        d_ps = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            back_allover_stitch=StitchFactory(name="back allover stitch"),
            front_allover_stitch=StitchFactory(name="front allover stitch"),
            sleeve_allover_stitch=StitchFactory(name="sleeve allover stitch"),
            hip_edging_stitch=StitchFactory(name="hip edging stitch"),
            sleeve_edging_stitch=StitchFactory(name="sleeve edging stitch"),
            neck_edging_stitch=StitchFactory(name="neck edging stitch"),
            armhole_edging_stitch=StitchFactory(name="armhole edging stitch"),
            button_band_edging_stitch=StitchFactory(name="buttonband edging stitch"),
            panel_stitch=StitchFactory(name="panel stitch"),
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            front_cable_extra_stitches=0,
            back_cable_extra_stitches=0,
            sleeve_cable_extra_stitches=0,
        )
        d_ps.full_clean()
        self.assertEqual(
            d_ps.stitches_used(),
            [
                StitchFactory(name="hip edging stitch"),
                StitchFactory(name="front allover stitch"),
                StitchFactory(name="back allover stitch"),
                StitchFactory(name="panel stitch"),
                StitchFactory(name="sleeve edging stitch"),
                StitchFactory(name="sleeve allover stitch"),
                StitchFactory(name="neck edging stitch"),
                StitchFactory(name="back cable stitch"),
                StitchFactory(name="front cable stitch"),
                StitchFactory(name="sleeve cable stitch"),
            ],
        )

        d_pv = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            neckline_style=SDC.NECK_CREW,
            back_allover_stitch=StitchFactory(name="back allover stitch"),
            front_allover_stitch=StitchFactory(name="front allover stitch"),
            sleeve_allover_stitch=StitchFactory(name="sleeve allover stitch"),
            hip_edging_stitch=StitchFactory(name="hip edging stitch"),
            sleeve_edging_stitch=StitchFactory(name="sleeve edging stitch"),
            neck_edging_stitch=StitchFactory(name="neck edging stitch"),
            armhole_edging_stitch=StitchFactory(name="armhole edging stitch"),
            button_band_edging_stitch=StitchFactory(name="buttonband edging stitch"),
            panel_stitch=StitchFactory(name="panel stitch"),
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            armhole_edging_height=1,
            front_cable_extra_stitches=0,
            back_cable_extra_stitches=0,
        )
        d_pv.full_clean()
        self.assertEqual(
            d_pv.stitches_used(),
            [
                StitchFactory(name="hip edging stitch"),
                StitchFactory(name="front allover stitch"),
                StitchFactory(name="back allover stitch"),
                StitchFactory(name="panel stitch"),
                StitchFactory(name="armhole edging stitch"),
                StitchFactory(name="neck edging stitch"),
                StitchFactory(name="back cable stitch"),
                StitchFactory(name="front cable stitch"),
            ],
        )

        d_cs = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            back_allover_stitch=StitchFactory(name="back allover stitch"),
            front_allover_stitch=StitchFactory(name="front allover stitch"),
            sleeve_allover_stitch=StitchFactory(name="sleeve allover stitch"),
            hip_edging_stitch=StitchFactory(name="hip edging stitch"),
            sleeve_edging_stitch=StitchFactory(name="sleeve edging stitch"),
            neck_edging_stitch=StitchFactory(name="neck edging stitch"),
            armhole_edging_stitch=StitchFactory(name="armhole edging stitch"),
            button_band_edging_stitch=StitchFactory(name="buttonband edging stitch"),
            panel_stitch=StitchFactory(name="panel stitch"),
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            front_cable_extra_stitches=0,
            back_cable_extra_stitches=0,
            sleeve_cable_extra_stitches=0,
            button_band_allowance=1,
            button_band_edging_height=1,
            number_of_buttons=5,
        )
        d_cs.full_clean()
        self.assertEqual(
            d_cs.stitches_used(),
            [
                StitchFactory(name="hip edging stitch"),
                StitchFactory(name="front allover stitch"),
                StitchFactory(name="back allover stitch"),
                StitchFactory(name="panel stitch"),
                StitchFactory(name="sleeve edging stitch"),
                StitchFactory(name="sleeve allover stitch"),
                StitchFactory(name="buttonband edging stitch"),
                StitchFactory(name="neck edging stitch"),
                StitchFactory(name="back cable stitch"),
                StitchFactory(name="front cable stitch"),
                StitchFactory(name="sleeve cable stitch"),
            ],
        )

        d_cv = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            back_allover_stitch=StitchFactory(name="back allover stitch"),
            front_allover_stitch=StitchFactory(name="front allover stitch"),
            sleeve_allover_stitch=StitchFactory(name="sleeve allover stitch"),
            hip_edging_stitch=StitchFactory(name="hip edging stitch"),
            sleeve_edging_stitch=StitchFactory(name="sleeve edging stitch"),
            neck_edging_stitch=StitchFactory(name="neck edging stitch"),
            armhole_edging_stitch=StitchFactory(name="armhole edging stitch"),
            button_band_edging_stitch=StitchFactory(name="buttonband edging stitch"),
            panel_stitch=StitchFactory(name="panel stitch"),
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            button_band_allowance=1,
            button_band_edging_height=1,
            number_of_buttons=5,
            armhole_edging_height=2,
            front_cable_extra_stitches=0,
            back_cable_extra_stitches=0,
        )
        d_cv.full_clean()
        self.assertEqual(
            d_cv.stitches_used(),
            [
                StitchFactory(name="hip edging stitch"),
                StitchFactory(name="front allover stitch"),
                StitchFactory(name="back allover stitch"),
                StitchFactory(name="panel stitch"),
                StitchFactory(name="armhole edging stitch"),
                StitchFactory(name="buttonband edging stitch"),
                StitchFactory(name="neck edging stitch"),
                StitchFactory(name="back cable stitch"),
                StitchFactory(name="front cable stitch"),
            ],
        )

        # Additional elements -- pullover sleeved
        back_el_stitch = StitchFactory(name="back element stitch")
        front_el_stitch = StitchFactory(name="front element stitch")
        sleeve_el_stitch = StitchFactory(name="sleeve element stitch")
        full_el_stitch = StitchFactory(name="full-torso element stitch")

        for gt, slv in [
            (SDC.PULLOVER_SLEEVED, True),
            (SDC.PULLOVER_VEST, False),
            (SDC.CARDIGAN_SLEEVED, True),
            (SDC.CARDIGAN_VEST, False),
        ]:
            design = SweaterDesignFactory(
                garment_type=gt,
                button_band_allowance=1,
                button_band_edging_height=1,
                number_of_buttons=5,
                armhole_edging_stitch=StitchFactory(),
                button_band_edging_stitch=StitchFactory(),
                armhole_edging_height=2,
            )
            AdditionalBackElementFactory(design=design, stitch=back_el_stitch)
            AdditionalSleeveElementFactory(design=design, stitch=sleeve_el_stitch)
            AdditionalFrontElementFactory(design=design, stitch=front_el_stitch)
            AdditionalFullTorsoElementFactory(design=design, stitch=full_el_stitch)
            design.full_clean()
            stitches = design.stitches_used()
            self.assertIn(back_el_stitch, stitches)
            self.assertIn(front_el_stitch, stitches)
            self.assertIn(full_el_stitch, stitches)
            if slv:
                self.assertIn(sleeve_el_stitch, stitches)
            else:
                self.assertNotIn(sleeve_el_stitch, stitches)

    def test_sleeve_length_patterntext(self):

        test_vectors = [
            # (Sleeve length, sleeve shape, bell type, expected text)
            (SDC.SLEEVE_SHORT, SDC.SLEEVE_TAPERED, None, "Short sleeve"),
            (SDC.SLEEVE_SHORT, SDC.SLEEVE_STRAIGHT, None, "Short sleeve"),
            (SDC.SLEEVE_SHORT, SDC.SLEEVE_BELL, SDC.BELL_SLIGHT, "Short sleeve"),
            (SDC.SLEEVE_SHORT, SDC.SLEEVE_BELL, SDC.BELL_MODERATE, "Short sleeve"),
            (SDC.SLEEVE_SHORT, SDC.SLEEVE_BELL, SDC.BELL_EXTREME, "Short sleeve"),
            (SDC.SLEEVE_ELBOW, SDC.SLEEVE_TAPERED, None, "Elbow-length tapered sleeve"),
            (
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_STRAIGHT,
                None,
                "Elbow-length straight sleeve",
            ),
            (
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_BELL,
                SDC.BELL_SLIGHT,
                "Elbow-length slight bell sleeve",
            ),
            (
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_BELL,
                SDC.BELL_MODERATE,
                "Elbow-length moderate bell sleeve",
            ),
            (
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_BELL,
                SDC.BELL_EXTREME,
                "Elbow-length extreme bell sleeve",
            ),
            (
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_TAPERED,
                None,
                "Three-quarter-length tapered sleeve",
            ),
            (
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_STRAIGHT,
                None,
                "Three-quarter-length straight sleeve",
            ),
            (
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_BELL,
                SDC.BELL_SLIGHT,
                "Three-quarter-length slight bell sleeve",
            ),
            (
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_BELL,
                SDC.BELL_MODERATE,
                "Three-quarter-length moderate bell sleeve",
            ),
            (
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_BELL,
                SDC.BELL_EXTREME,
                "Three-quarter-length extreme bell sleeve",
            ),
            (SDC.SLEEVE_FULL, SDC.SLEEVE_TAPERED, None, "Full-length tapered sleeve"),
            (SDC.SLEEVE_FULL, SDC.SLEEVE_STRAIGHT, None, "Full-length straight sleeve"),
            (
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_BELL,
                SDC.BELL_SLIGHT,
                "Full-length slight bell sleeve",
            ),
            (
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_BELL,
                SDC.BELL_MODERATE,
                "Full-length moderate bell sleeve",
            ),
            (
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_BELL,
                SDC.BELL_EXTREME,
                "Full-length extreme bell sleeve",
            ),
        ]

        for length, shape, bell_type, text in test_vectors:
            design = SweaterDesignFactory(
                sleeve_length=length, sleeve_shape=shape, bell_type=bell_type
            )
            self.assertEqual(design.sleeve_length_patterntext(), text)

    def test_neckline_style_patterntext(self):

        test_vectors = [
            # (neck shape, neck width, neck-width-percentage, text)
            (SDC.NECK_VEE, SDC.NECK_NARROW, None, "Narrow-width vee neck"),
            (SDC.NECK_VEE, SDC.NECK_AVERAGE, None, "Average-width vee neck"),
            (SDC.NECK_VEE, SDC.NECK_WIDE, None, "Wide vee neck"),
            (SDC.NECK_VEE, SDC.NECK_OTHERWIDTH, 50, "Custom-width vee neck"),
            (SDC.NECK_VEE, SDC.NECK_OTHERWIDTH, 100, "No neck shaping"),
            (SDC.NECK_VEE, SDC.NECK_OTHERWIDTH, 0, "No neck"),
        ]

        for shape, width, percentage, text in test_vectors:
            design = SweaterDesignFactory(
                neckline_style=shape,
                neckline_width=width,
                neckline_other_val_percentage=percentage,
            )
            self.assertEqual(design.neckline_style_patterntext(), text)

    #
    # Error tests
    #

    def test_error_1(self):
        d = SweaterDesignFactory(sleeve_length=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_2(self):
        d = SweaterDesignFactory(sleeve_edging_height=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_3(self):
        d = SweaterDesignFactory(sleeve_shape=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_4(self):
        d = SweaterDesignFactory(sleeve_shape=SDC.SLEEVE_BELL, bell_type=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_5(self):
        d = SweaterDesignFactory(
            neckline_width=SDC.NECK_OTHERWIDTH, neckline_other_val_percentage=None
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_7(self):
        d = SweaterDesignFactory(sleeve_edging_stitch=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_8(self):
        d = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_height=1,
            armhole_edging_stitch=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_9(self):
        d = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_10(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=None,
            button_band_allowance=1.5,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_11(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=None,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=6,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_12(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1.5,
            button_band_edging_stitch=None,
            number_of_buttons=6,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_13(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1.5,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_14(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neck_edging_stitch=None,
            neck_edging_height=1,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_15(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_17(self):
        d = SweaterDesignFactory(neck_edging_stitch=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_18(self):
        d = SweaterDesignFactory(neck_edging_height=None)
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_19(self):
        # Slugs should not be empty
        d = SweaterDesignFactory(slug="")
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_20(self):
        # Slugs should not be all-digit
        d = SweaterDesignFactory(slug="12345")
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_sleeve_cable_stitches(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_cable_stitch=StitchFactory(name="sleeve cable stitch"),
            sleeve_cable_extra_stitches=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            sleeve_cable_stitch=None,
            sleeve_cable_extra_stitches=4,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_back_cable_stitches(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            back_cable_stitch=StitchFactory(name="back cable stitch"),
            back_cable_extra_stitches=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            back_cable_stitch=None,
            back_cable_extra_stitches=4,
        )
        self.assertRaises(ValidationError, d.full_clean)

    def test_error_front_cable_stitches(self):
        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=None,
        )
        self.assertRaises(ValidationError, d.full_clean)

        d = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            front_cable_stitch=None,
            front_cable_extra_stitches=4,
        )
        self.assertRaises(ValidationError, d.full_clean)

        d = SweaterDesignFactory(
            neckline_style=SDC.NECK_VEE,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=4,
        )
        self.assertRaises(ValidationError, d.full_clean)

        d = SweaterDesignFactory(
            neckline_style=SDC.NECK_TURKS_AND_CAICOS,
            front_cable_stitch=StitchFactory(name="front cable stitch"),
            front_cable_extra_stitches=4,
        )
        self.assertRaises(ValidationError, d.full_clean)


class SweaterDesignModelTests(TestCase):

    def test_sleeve_combinations(self):
        # WE used to silently change short sleeves to straight sleeves.
        # Lets's test that we no longer do that.

        for sleeve_shape in [SDC.SLEEVE_STRAIGHT, SDC.SLEEVE_TAPERED, SDC.SLEEVE_BELL]:
            for sleeve_length in [
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_SHORT,
            ]:

                choices_dict = {
                    "sleeve_length": sleeve_length,
                    "sleeve_shape": sleeve_shape,
                }
                if sleeve_shape == SDC.SLEEVE_BELL:
                    choices_dict["bell_type"] = SDC.BELL_MODERATE

                design = SweaterDesignFactory(**choices_dict)
                design.full_clean()
                self.assertEqual(design.sleeve_shape, sleeve_shape)
                self.assertEqual(design.sleeve_length, sleeve_length)

    def test_supported_fit_choices(self):

        test_vectors = [
            # aline allowed, half-hourglass allowed, hourglass allowed, straight allowed, tapered allowed, expected output
            (False, False, False, False, True, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (False, False, False, True, False, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (False, False, False, True, True, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (False, False, True, False, False, SDC.GARMENT_FIT_CHOICES_HOURGLASS),
            (
                False,
                False,
                True,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                False,
                True,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                False,
                True,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (True, False, False, False, False, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (True, False, False, False, True, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (True, False, False, True, False, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (True, False, False, True, True, SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS),
            (
                True,
                False,
                True,
                False,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                False,
                True,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                False,
                True,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                False,
                True,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                True,
                False,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                True,
                False,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                True,
                False,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (False, True, True, False, False, SDC.GARMENT_FIT_CHOICES_HOURGLASS),
            (
                False,
                True,
                True,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                True,
                True,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                False,
                True,
                True,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                False,
                False,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                False,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                False,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                False,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                True,
                False,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                True,
                False,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                True,
                True,
                False,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
            (
                True,
                True,
                True,
                True,
                True,
                SDC.GARMENT_FIT_CHOICES_HOURGLASS
                + SDC.GARMENT_FIT_CHOICES_NON_HOURGLASS,
            ),
        ]

        for aline, half_hourglass, hourglass, straight, tapered, goal in test_vectors:
            if aline:
                primary = SDC.SILHOUETTE_ALINE
            elif hourglass:
                primary = SDC.SILHOUETTE_HOURGLASS
            elif half_hourglass:
                primary = SDC.SILHOUETTE_HALF_HOURGLASS
            elif straight:
                primary = SDC.SILHOUETTE_STRAIGHT
            else:
                assert tapered
                primary = SDC.SILHOUETTE_TAPERED

            design = SweaterDesignFactory(
                primary_silhouette=primary,
                silhouette_half_hourglass_allowed=half_hourglass,
                silhouette_aline_allowed=aline,
                silhouette_hourglass_allowed=hourglass,
                silhouette_straight_allowed=straight,
                silhouette_tapered_allowed=tapered,
            )
            design.full_clean()
            self.assertEqual(
                design.supported_fit_choices(),
                goal,
                (aline, half_hourglass, hourglass, straight, tapered),
            )

    def test_supported_silhouette_choices(self):

        self.max_diff = None

        HOURGLASS_CHOICE = SDC.SILHOUETTE_CHOICES[0]
        HALF_HOURGLASS_CHOICE = SDC.SILHOUETTE_CHOICES[1]
        ALINE_CHOICE = SDC.SILHOUETTE_CHOICES[2]
        STRAIGHT_CHOICE = SDC.SILHOUETTE_CHOICES[3]
        TAPERED_CHOICE = SDC.SILHOUETTE_CHOICES[4]

        test_vectors = [
            # aline allowed, half-hourglass allowed, hourglass allowed, straight allowed, tapered allowed, expected output
            (False, False, False, False, True, [TAPERED_CHOICE]),
            (False, False, False, True, False, [STRAIGHT_CHOICE]),
            (False, False, False, True, True, [STRAIGHT_CHOICE, TAPERED_CHOICE]),
            (False, False, True, False, False, [HOURGLASS_CHOICE]),
            (False, False, True, False, True, [HOURGLASS_CHOICE, TAPERED_CHOICE]),
            (False, False, True, True, False, [HOURGLASS_CHOICE, STRAIGHT_CHOICE]),
            (
                False,
                False,
                True,
                True,
                True,
                [HOURGLASS_CHOICE, STRAIGHT_CHOICE, TAPERED_CHOICE],
            ),
            (True, False, False, False, False, [ALINE_CHOICE]),
            (True, False, False, False, True, [ALINE_CHOICE, TAPERED_CHOICE]),
            (True, False, False, True, False, [ALINE_CHOICE, STRAIGHT_CHOICE]),
            (
                True,
                False,
                False,
                True,
                True,
                [ALINE_CHOICE, STRAIGHT_CHOICE, TAPERED_CHOICE],
            ),
            (
                True,
                False,
                True,
                False,
                False,
                [
                    HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                ],
            ),
            (
                True,
                False,
                True,
                False,
                True,
                [
                    HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                    TAPERED_CHOICE,
                ],
            ),
            (
                True,
                False,
                True,
                True,
                False,
                [HOURGLASS_CHOICE, ALINE_CHOICE, STRAIGHT_CHOICE],
            ),
            (
                True,
                False,
                True,
                True,
                True,
                [HOURGLASS_CHOICE, ALINE_CHOICE, STRAIGHT_CHOICE, TAPERED_CHOICE],
            ),
            (False, True, False, False, True, [HALF_HOURGLASS_CHOICE, TAPERED_CHOICE]),
            (False, True, False, True, False, [HALF_HOURGLASS_CHOICE, STRAIGHT_CHOICE]),
            (
                False,
                True,
                False,
                True,
                True,
                [HALF_HOURGLASS_CHOICE, STRAIGHT_CHOICE, TAPERED_CHOICE],
            ),
            (
                False,
                True,
                True,
                False,
                False,
                [HOURGLASS_CHOICE, HALF_HOURGLASS_CHOICE],
            ),
            (
                False,
                True,
                True,
                False,
                True,
                [HOURGLASS_CHOICE, HALF_HOURGLASS_CHOICE, TAPERED_CHOICE],
            ),
            (
                False,
                True,
                True,
                True,
                False,
                [HOURGLASS_CHOICE, HALF_HOURGLASS_CHOICE, STRAIGHT_CHOICE],
            ),
            (
                False,
                True,
                True,
                True,
                True,
                [
                    HOURGLASS_CHOICE,
                    HALF_HOURGLASS_CHOICE,
                    STRAIGHT_CHOICE,
                    TAPERED_CHOICE,
                ],
            ),
            (True, True, False, False, False, [HALF_HOURGLASS_CHOICE, ALINE_CHOICE]),
            (
                True,
                True,
                False,
                False,
                True,
                [HALF_HOURGLASS_CHOICE, ALINE_CHOICE, TAPERED_CHOICE],
            ),
            (
                True,
                True,
                False,
                True,
                False,
                [HALF_HOURGLASS_CHOICE, ALINE_CHOICE, STRAIGHT_CHOICE],
            ),
            (
                True,
                True,
                False,
                True,
                True,
                [HALF_HOURGLASS_CHOICE, ALINE_CHOICE, STRAIGHT_CHOICE, TAPERED_CHOICE],
            ),
            (
                True,
                True,
                True,
                False,
                False,
                [
                    HOURGLASS_CHOICE,
                    HALF_HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                ],
            ),
            (
                True,
                True,
                True,
                False,
                True,
                [
                    HOURGLASS_CHOICE,
                    HALF_HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                    TAPERED_CHOICE,
                ],
            ),
            (
                True,
                True,
                True,
                True,
                False,
                [
                    HOURGLASS_CHOICE,
                    HALF_HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                    STRAIGHT_CHOICE,
                ],
            ),
            (
                True,
                True,
                True,
                True,
                True,
                [
                    HOURGLASS_CHOICE,
                    HALF_HOURGLASS_CHOICE,
                    ALINE_CHOICE,
                    STRAIGHT_CHOICE,
                    TAPERED_CHOICE,
                ],
            ),
        ]

        for aline, half_hourglass, hourglass, straight, tapered, goal in test_vectors:
            if aline:
                primary = SDC.SILHOUETTE_ALINE
            elif hourglass:
                primary = SDC.SILHOUETTE_HOURGLASS
            elif half_hourglass:
                primary = SDC.SILHOUETTE_HALF_HOURGLASS
            elif straight:
                primary = SDC.SILHOUETTE_STRAIGHT
            else:
                assert tapered
                primary = SDC.SILHOUETTE_TAPERED

            design = SweaterDesignFactory(
                primary_silhouette=primary,
                silhouette_half_hourglass_allowed=half_hourglass,
                silhouette_aline_allowed=aline,
                silhouette_hourglass_allowed=hourglass,
                silhouette_straight_allowed=straight,
                silhouette_tapered_allowed=tapered,
            )
            design.full_clean()
            self.assertEqual(
                design.supported_silhouette_choices(),
                goal,
                (
                    aline,
                    half_hourglass,
                    hourglass,
                    straight,
                    tapered,
                    design.supported_silhouette_choices(),
                    goal,
                ),
            )

    def test_supported_silhouette_patterntext(self):

        test_vectors = [
            # components:
            # primary silhouette, half-hourglass allowed, aline allowed, hourglass allowed, straight allowed, tapered allowed, expected output
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                False,
                False,
                "Pictured in a-line silhouette. Also available in half-hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                False,
                True,
                "Pictured in a-line silhouette. Also available in half-hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                True,
                False,
                "Pictured in a-line silhouette. Also available in half-hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                True,
                True,
                "Pictured in a-line silhouette. Also available in half-hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                False,
                False,
                "Pictured in a-line silhouette. Also available in hourglass and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                False,
                True,
                "Pictured in a-line silhouette. Also available in hourglass, half-hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                True,
                False,
                "Pictured in a-line silhouette. Also available in hourglass, half-hourglass, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                True,
                True,
                "Pictured in a-line silhouette. Also available in hourglass, half-hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                False,
                False,
                False,
                "Pictured in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                False,
                False,
                True,
                "Pictured in a-line silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                False,
                True,
                False,
                "Pictured in a-line silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                False,
                True,
                True,
                "Pictured in a-line silhouette. Also available in straight and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                True,
                False,
                False,
                "Pictured in a-line silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                True,
                False,
                True,
                "Pictured in a-line silhouette. Also available in hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                True,
                True,
                False,
                "Pictured in a-line silhouette. Also available in hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                False,
                True,
                True,
                True,
                True,
                "Pictured in a-line silhouette. Also available in hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                False,
                True,
                False,
                False,
                "Pictured in hourglass silhouette. Also available in half-hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                False,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in half-hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                False,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in half-hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                False,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in half-hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                False,
                False,
                "Pictured in hourglass silhouette. Also available in half-hourglass and a-line silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in half-hourglass, a-line, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in half-hourglass, a-line, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in half-hourglass, a-line, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                False,
                True,
                False,
                False,
                "Pictured in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                False,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                False,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                False,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in straight and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                False,
                False,
                "Pictured in hourglass silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in a-line and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in a-line and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in a-line, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                False,
                True,
                False,
                "Pictured in straight silhouette. Also available in half-hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                False,
                True,
                True,
                "Pictured in straight silhouette. Also available in half-hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in hourglass and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in hourglass, half-hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                False,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                False,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line, half-hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line, hourglass, and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line, hourglass, half-hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                False,
                False,
                True,
                False,
                "Pictured in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                False,
                False,
                True,
                True,
                "Pictured in straight silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                False,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                False,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                False,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                False,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line and hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line, hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                False,
                False,
                True,
                "Pictured in tapered silhouette. Also available in half-hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                False,
                True,
                True,
                "Pictured in tapered silhouette. Also available in half-hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in hourglass and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in hourglass, half-hourglass, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                False,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                False,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line, half-hourglass, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line, hourglass, and half-hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line, hourglass, half-hourglass, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                False,
                False,
                False,
                True,
                "Pictured in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                False,
                False,
                True,
                True,
                "Pictured in tapered silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                False,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                False,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                False,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                False,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line and hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line, hourglass, and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                False,
                False,
                True,
                "Pictured in half-hourglass silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                False,
                True,
                True,
                "Pictured in half-hourglass silhouette. Also available in straight and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                True,
                False,
                True,
                "Pictured in half-hourglass silhouette. Also available in hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                True,
                True,
                True,
                "Pictured in half-hourglass silhouette. Also available in hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                False,
                False,
                True,
                "Pictured in half-hourglass silhouette. Also available in a-line and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                False,
                True,
                True,
                "Pictured in half-hourglass silhouette. Also available in a-line, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                True,
                False,
                True,
                "Pictured in half-hourglass silhouette. Also available in a-line, hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                True,
                True,
                True,
                "Pictured in half-hourglass silhouette. Also available in a-line, hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                False,
                False,
                False,
                "Pictured in half-hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                False,
                True,
                False,
                "Pictured in half-hourglass silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                True,
                False,
                False,
                "Pictured in half-hourglass silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                False,
                True,
                True,
                False,
                "Pictured in half-hourglass silhouette. Also available in hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                False,
                False,
                False,
                "Pictured in half-hourglass silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                False,
                True,
                False,
                "Pictured in half-hourglass silhouette. Also available in a-line and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                True,
                False,
                False,
                "Pictured in half-hourglass silhouette. Also available in a-line and hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HALF_HOURGLASS,
                True,
                True,
                True,
                True,
                False,
                "Pictured in half-hourglass silhouette. Also available in a-line, hourglass, and straight silhouettes.",
            ),
        ]

        for (
            primary,
            half_hourglass,
            aline,
            hourglass,
            straight,
            tapered,
            goal,
        ) in test_vectors:
            design = SweaterDesignFactory(
                primary_silhouette=primary,
                silhouette_half_hourglass_allowed=half_hourglass,
                silhouette_aline_allowed=aline,
                silhouette_hourglass_allowed=hourglass,
                silhouette_straight_allowed=straight,
                silhouette_tapered_allowed=tapered,
            )
            design.full_clean()
            self.assertEqual(
                design.supported_silhouettes_patterntext(),
                goal,
                (
                    design.supported_silhouettes_patterntext(),
                    goal,
                    primary,
                    half_hourglass,
                    aline,
                    hourglass,
                    straight,
                    tapered,
                ),
            )

    def test_isotope_classes_silhouettes(self):

        self.max_diff = None

        test_vectors = [
            # half-hourglass allowed, hourglass allowed, aline allowed, straight allowed, tapered allowed, expected output
            (False, False, False, False, True, "tapered"),
            (False, False, False, True, False, "straight"),
            (False, False, False, True, True, "straight tapered"),
            (False, False, True, False, False, "aline"),
            (False, False, True, False, True, "aline tapered"),
            (False, False, True, True, False, "aline straight"),
            (False, False, True, True, True, "aline straight tapered"),
            (False, True, False, False, False, "hourglass"),
            (False, True, False, False, True, "hourglass tapered"),
            (False, True, False, True, False, "hourglass straight"),
            (False, True, False, True, True, "hourglass straight tapered"),
            (False, True, True, False, False, "hourglass aline"),
            (False, True, True, False, True, "hourglass aline tapered"),
            (False, True, True, True, False, "hourglass aline straight"),
            (False, True, True, True, True, "hourglass aline straight tapered"),
            (False, False, False, False, True, "tapered"),
            (False, False, False, True, False, "straight"),
            (False, False, False, True, True, "straight tapered"),
            (False, False, True, False, False, "aline"),
            (False, False, True, False, True, "aline tapered"),
            (False, False, True, True, False, "aline straight"),
            (False, False, True, True, True, "aline straight tapered"),
            (False, True, False, False, False, "hourglass"),
            (False, True, False, False, True, "hourglass tapered"),
            (False, True, False, True, False, "hourglass straight"),
            (False, True, False, True, True, "hourglass straight tapered"),
            (False, True, True, False, False, "hourglass aline"),
            (False, True, True, False, True, "hourglass aline tapered"),
            (False, True, True, True, False, "hourglass aline straight"),
            (False, True, True, True, True, "hourglass aline straight tapered"),
            (True, False, False, False, True, "halfhourglass tapered"),
            (True, False, False, True, False, "halfhourglass straight"),
            (True, False, False, True, True, "halfhourglass straight tapered"),
            (True, False, True, False, False, "halfhourglass aline"),
            (True, False, True, False, True, "halfhourglass aline tapered"),
            (True, False, True, True, False, "halfhourglass aline straight"),
            (True, False, True, True, True, "halfhourglass aline straight tapered"),
            (True, True, False, False, False, "hourglass halfhourglass"),
            (True, True, False, False, True, "hourglass halfhourglass tapered"),
            (True, True, False, True, False, "hourglass halfhourglass straight"),
            (True, True, False, True, True, "hourglass halfhourglass straight tapered"),
            (True, True, True, False, False, "hourglass halfhourglass aline"),
            (True, True, True, False, True, "hourglass halfhourglass aline tapered"),
            (True, True, True, True, False, "hourglass halfhourglass aline straight"),
            (
                True,
                True,
                True,
                True,
                True,
                "hourglass halfhourglass aline straight tapered",
            ),
            (True, False, False, False, True, "halfhourglass tapered"),
            (True, False, False, True, False, "halfhourglass straight"),
            (True, False, False, True, True, "halfhourglass straight tapered"),
            (True, False, True, False, False, "halfhourglass aline"),
            (True, False, True, False, True, "halfhourglass aline tapered"),
            (True, False, True, True, False, "halfhourglass aline straight"),
            (True, False, True, True, True, "halfhourglass aline straight tapered"),
            (True, True, False, False, False, "hourglass halfhourglass"),
            (True, True, False, False, True, "hourglass halfhourglass tapered"),
            (True, True, False, True, False, "hourglass halfhourglass straight"),
            (True, True, False, True, True, "hourglass halfhourglass straight tapered"),
            (True, True, True, False, False, "hourglass halfhourglass aline"),
            (True, True, True, False, True, "hourglass halfhourglass aline tapered"),
            (True, True, True, True, False, "hourglass halfhourglass aline straight"),
            (
                True,
                True,
                True,
                True,
                True,
                "hourglass halfhourglass aline straight tapered",
            ),
        ]

        for half_hourglass, hourglass, aline, straight, tapered, goal in test_vectors:
            if aline:
                primary = SDC.SILHOUETTE_ALINE
            elif hourglass:
                primary = SDC.SILHOUETTE_HOURGLASS
            elif straight:
                primary = SDC.SILHOUETTE_STRAIGHT
            else:
                assert tapered
                primary = SDC.SILHOUETTE_TAPERED

            goal += " setinsleeve"

            design = SweaterDesignFactory(
                primary_silhouette=primary,
                silhouette_aline_allowed=aline,
                silhouette_half_hourglass_allowed=half_hourglass,
                silhouette_hourglass_allowed=hourglass,
                silhouette_straight_allowed=straight,
                silhouette_tapered_allowed=tapered,
                primary_construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
                construction_set_in_sleeve_allowed=True,
                construction_drop_shoulder_allowed=False,
            )
            design.full_clean()
            self.assertEqual(design.isotope_classes(), goal)

    def test_isotope_classes_constructions(self):

        self.max_diff = None

        test_vectors = [
            # set-in-sleeve allowed, drop-shoulder allowed
            (True, True, "setinsleeve dropshoulder"),
            (True, False, "setinsleeve"),
            (False, True, "dropshoulder"),
        ]

        for set_in_sleeve, drop_shoulder, goal in test_vectors:
            if set_in_sleeve:
                primary = SDC.CONSTRUCTION_SET_IN_SLEEVE
            else:
                assert drop_shoulder
                primary = SDC.CONSTRUCTION_DROP_SHOULDER

            goal = "hourglass " + goal

            armhole = (
                SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE
                if drop_shoulder
                else None
            )

            design = SweaterDesignFactory(
                primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
                silhouette_aline_allowed=False,
                silhouette_half_hourglass_allowed=False,
                silhouette_hourglass_allowed=True,
                silhouette_straight_allowed=False,
                silhouette_tapered_allowed=False,
                primary_construction=primary,
                construction_set_in_sleeve_allowed=set_in_sleeve,
                construction_drop_shoulder_allowed=drop_shoulder,
                drop_shoulder_additional_armhole_depth=armhole,
            )
            design.full_clean()
            self.assertEqual(design.isotope_classes(), goal)

    def test_clean1(self):
        d = SweaterDesignFactory(
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=True,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=False,
            primary_silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            silhouette_aline_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=True,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=True,
            primary_silhouette=SDC.SILHOUETTE_ALINE,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=False,
            silhouette_tapered_allowed=True,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=True,
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=False,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=True,
            primary_silhouette=SDC.SILHOUETTE_TAPERED,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=True,
            silhouette_hourglass_allowed=False,
            silhouette_half_hourglass_allowed=True,
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_3(self):
        d = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_aline_allowed=False,
            silhouette_straight_allowed=False,
            silhouette_tapered_allowed=False,
            silhouette_half_hourglass_allowed=False,
            silhouette_hourglass_allowed=False,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_4(self):
        d = SweaterDesignFactory(
            primary_construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            construction_drop_shoulder_allowed=False,
            construction_set_in_sleeve_allowed=True,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            primary_construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            construction_set_in_sleeve_allowed=False,
            construction_drop_shoulder_allowed=True,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean_5(self):
        d = SweaterDesignFactory(
            construction_drop_shoulder_allowed=False,
            construction_set_in_sleeve_allowed=False,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean6(self):
        d = SweaterDesignFactory(
            construction_drop_shoulder_allowed=False,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

        d = SweaterDesignFactory(
            construction_drop_shoulder_allowed=True,
            drop_shoulder_additional_armhole_depth=None,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_app_label(self):
        des = SweaterDesignFactory()
        des.full_clean()
        # Note that 'sweaters' is a magic string in the model-to-view framework we put in so that
        # top-level views can handle different constructions. See design_wizard/views/construction_registry
        self.assertEqual(des._meta.app_label, "sweaters")


class AdditionalSleeveElementTests(TestCase, AdditionalElementsTestsBase):

    factory = AdditionalSleeveElementFactory

    def test_sleeve_validation(self):
        el = self.factory(start_location_value=0)
        el.full_clean()

        el = self.factory(start_location_value=-1)
        with self.assertRaises(ValidationError):
            el.full_clean()

    def test_start_row(self):
        gauge = GaugeFactory(rows=5)

        armcap_height = CompoundResult([10])

        el = self.factory(
            start_location_value=3,
            start_location_type=AdditionalSleeveElement.START_AFTER_CASTON,
        )
        self.assertEqual(el.start_rows(armcap_height, gauge), [15])

        el = self.factory(
            start_location_value=4,
            start_location_type=AdditionalSleeveElement.START_AFTER_CASTON,
        )
        self.assertEqual(
            el.start_rows(armcap_height, gauge), [21]
        )  # Note the rounding to odd number

        el = self.factory(
            start_location_value=1,
            start_location_type=AdditionalSleeveElement.START_BEFORE_CAP,
        )
        self.assertEqual(el.start_rows(armcap_height, gauge), [(10 - 1) * 5])

        el = self.factory(
            start_location_value=2,
            start_location_type=AdditionalSleeveElement.START_BEFORE_CAP,
        )
        self.assertEqual(
            el.start_rows(armcap_height, gauge), [41]
        )  # Note the rounding to odd number

        # Corner case-- if the start location should be before cast-ons, then we slide the whole element
        # up to start at the cast-ons
        el = self.factory(
            start_location_value=20,
            start_location_type=AdditionalSleeveElement.START_BEFORE_CAP,
        )
        self.assertEqual(el.start_rows(armcap_height, gauge), [1])


class AdditionalBodyElementTestsBase(AdditionalElementsTestsBase):

    def test_common_body_piece_validation(self):

        # validation-- control group
        good_input = [
            (3.5, AdditionalBodyPieceElement.START_AFTER_CASTON),
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON),
            (3.5, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE),
            (-3.5, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE),
            (3.5, AdditionalBodyPieceElement.START_BEFORE_NECKLINE),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE),
            (-3.5, AdditionalBodyPieceElement.START_BEFORE_NECKLINE),
            (3.5, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS),
        ]
        for sv, st in good_input:
            el = self.factory(start_location_value=sv, start_location_type=st)
            el.full_clean()

        # Now test validation:
        bad_input = [
            (-3.5, AdditionalBodyPieceElement.START_AFTER_CASTON),
            (-3.5, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS),
        ]
        for sv, st in bad_input:
            el = self.factory(start_location_value=sv, start_location_type=st)
            with self.assertRaises(ValidationError):
                el.full_clean()


class AdditionalFrontElementTests(TestCase, AdditionalBodyElementTestsBase):

    longMessage = True

    factory = AdditionalFrontElementFactory

    def test_start_row(self):

        vectors = [
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 1),
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 1),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 5),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 7),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 21),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 25),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 25),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 31),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 31),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 37),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 31),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 37),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 35),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 43),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 41),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 49),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 45),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 55),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 51),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 61),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            start_row = el.start_rows(
                gauge,
                CompoundResult([5]),  # front armhole
                CompoundResult([7]),  # front neck,
                CompoundResult([10]),  # front shoulder
                CompoundResult([6]),  # back armhole
                CompoundResult([11]),  # back neckline
                CompoundResult([12]),
            )  # back shoulder
            self.assertEqual(
                start_row,
                CompoundResult([goal_row]),
                (slv, slt, rows_per_inch, goal_row),
            )

        # Test error cases
        vectors = [
            (6, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 21),
            (8, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 31),
            (11, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 45),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            with self.assertRaises(
                AdditionalBodyPieceElement.ElementBelowStartException
            ):
                start_row = el.start_rows(
                    gauge,
                    CompoundResult([5]),  # front armhole
                    CompoundResult([7]),  # front neck,
                    CompoundResult([10]),  # front shoulder
                    CompoundResult([6]),  # back armhole
                    CompoundResult([11]),  # back neckline
                    CompoundResult([12]),
                )  # back shoulder


class AdditionalFullTorsoElementTests(TestCase, AdditionalBodyElementTestsBase):

    longMessage = True

    factory = AdditionalFullTorsoElementFactory

    def test_start_row(self):

        vectors = [
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 1),
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 1),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 5),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 7),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 21),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 25),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 25),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 31),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 31),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 37),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 31),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 37),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 35),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 43),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 41),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 49),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 45),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 55),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 51),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 61),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            start_row = el.start_rows(
                gauge,
                CompoundResult([5]),  # front armhole
                CompoundResult([7]),  # front neck,
                CompoundResult([10]),  # front shoulder
                CompoundResult([6]),  # back armhole
                CompoundResult([11]),  # back neckline
                CompoundResult([12]),
            )  # back shoulder
            self.assertEqual(
                start_row,
                CompoundResult([goal_row]),
                (slv, slt, rows_per_inch, goal_row),
            )

        # Test error cases
        vectors = [
            (6, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 21),
            (8, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 31),
            (11, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 45),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            with self.assertRaises(
                AdditionalBodyPieceElement.ElementBelowStartException
            ):
                start_row = el.start_rows(
                    gauge,
                    CompoundResult([5]),  # front armhole
                    CompoundResult([7]),  # front neck,
                    CompoundResult([10]),  # front shoulder
                    CompoundResult([6]),  # back armhole
                    CompoundResult([11]),  # back neckline
                    CompoundResult([12]),
                )  # back shoulder


class AdditionalBackElementTests(TestCase, AdditionalBodyElementTestsBase):

    factory = AdditionalBackElementFactory

    longMessage = True

    def test_start_row(self):

        vectors = [
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 1),
            (0, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 1),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 5, 5),
            (1, AdditionalBodyPieceElement.START_AFTER_CASTON, 6, 7),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 25),
            (1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 31),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 31),
            (0, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 37),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 35),
            (-1, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 6, 43),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 35),
            (1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 43),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 41),
            (0, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 49),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 45),
            (-1, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 6, 55),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 55),
            (1, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 67),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 61),
            (0, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 6, 73),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            start_row = el.start_rows(
                gauge,
                CompoundResult([5]),  # front armhole
                CompoundResult([7]),  # front neck,
                CompoundResult([10]),  # front shoulder
                CompoundResult([6]),  # back armhole
                CompoundResult([8]),  # back neckline
                CompoundResult([12]),  # back shoulder
            )
            with self.subTest():
                self.assertEqual(
                    start_row,
                    CompoundResult([goal_row]),
                    (slv, slt, rows_per_inch, goal_row),
                )

        # Test error cases
        vectors = [
            (7, AdditionalBodyPieceElement.START_BEFORE_ARMHOLE, 5, 21),
            (9, AdditionalBodyPieceElement.START_BEFORE_NECKLINE, 5, 31),
            (13, AdditionalBodyPieceElement.START_BEFORE_SHOULDERS, 5, 45),
        ]

        for slv, slt, rows_per_inch, goal_row in vectors:
            gauge = GaugeFactory(rows=rows_per_inch)
            el = self.factory(start_location_value=slv, start_location_type=slt)
            with self.subTest():
                with self.assertRaises(
                    AdditionalBodyPieceElement.ElementBelowStartException
                ):
                    start_row = el.start_rows(
                        gauge,
                        CompoundResult([5]),  # front armhole
                        CompoundResult([7]),  # front neck,
                        CompoundResult([10]),  # front shoulder
                        CompoundResult([6]),  # back armhole
                        CompoundResult([8]),  # back neckline
                        CompoundResult([12]),
                    )  # back shoulder
