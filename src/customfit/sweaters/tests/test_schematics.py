# -*- coding: utf-8 -*-

import itertools

from django.core.exceptions import ValidationError
from django.test import TestCase

from customfit.stitches.factories import StitchFactory
from customfit.userauth.factories import UserFactory

from ..factories import (
    GradedSweaterBackSchematicFactory,
    GradedSweaterSchematicFactory,
    SweaterBackSchematicFactory,
    SweaterGradedGarmentParametersFactory,
    SweaterIndividualGarmentParametersFactory,
    SweaterPatternSpecFactory,
    SweaterSchematicFactory,
)
from ..helpers import sweater_design_choices as SDC
from ..models import (
    CardiganVestSchematic,
    GradedSweaterSchematic,
    SweaterFrontSchematic,
    SweaterIndividualGarmentParameters,
    SweaterSchematic,
    VestFrontSchematic,
)


class SweaterSchematicTests(TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_defaut_individual_pieced_schematic(self):
        ips = SweaterSchematicFactory()
        ips.full_clean()

    def test_save_delete_default_individual_pieced_schematic(self):
        ips = SweaterSchematicFactory()
        ips.save()
        ips.delete()

    def test_check_right_pieces_got_made(self):
        ips = SweaterSchematicFactory()
        ips.save()

        pattern_spec = ips.individual_garment_parameters.pattern_spec

        def _is_true_not_none(a, b):
            self.assertEqual(a, b is not None)

        _is_true_not_none(pattern_spec.has_sweater_back(), ips.sweater_back)
        _is_true_not_none(pattern_spec.has_sweater_front(), ips.sweater_front)
        _is_true_not_none(pattern_spec.has_vest_back(), ips.vest_back)
        _is_true_not_none(pattern_spec.has_vest_front(), ips.vest_front)
        _is_true_not_none(pattern_spec.has_sleeves(), ips.sleeve)
        _is_true_not_none(pattern_spec.has_cardigan_vest(), ips.cardigan_vest)
        _is_true_not_none(pattern_spec.has_cardigan_sleeved(), ips.cardigan_sleeved)

    def test_garment(self):

        ips = SweaterSchematicFactory()
        ips.save()
        pattern_spec = ips.individual_garment_parameters.pattern_spec
        pattern_spec.construction = SDC.CONSTRUCTION_DROP_SHOULDER
        pattern_spec.save()

        self.assertEqual(ips.construction, SDC.CONSTRUCTION_DROP_SHOULDER)


class SweaterbackSchematicTest(TestCase):

    def test_make_from_gp(self):
        gp = SweaterIndividualGarmentParametersFactory()
        gp.save()
        user = UserFactory()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        sbs = ips.sweater_back
        self.assertEqual(sbs.shoulder_height, 24)
        self.assertEqual(sbs.armpit_height, 16)
        self.assertEqual(sbs.waist_height, 7)
        self.assertEqual(sbs.torso_hem_height, 1.5)
        self.assertEqual(sbs.hip_width, 19.5)
        self.assertEqual(sbs.cross_back_width, 14)
        self.assertEqual(sbs.neck_opening_width, 7)
        self.assertEqual(sbs.neck_height, 23)
        self.assertEqual(sbs.bust_width, 19.625)
        self.assertEqual(sbs.waist_width, 17.5)

    def test_schematic_image(self):
        sbs = SweaterBackSchematicFactory()
        self.assertEqual(
            sbs.get_schematic_image(), "img/schematics/set-in-sleeve/Hourglass-Back.png"
        )

    def test_straight_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbs = ips.sweater_back
        self.assertEqual(sbs.hip_width, 21.0)
        self.assertEqual(sbs.cross_back_width, 14)
        self.assertEqual(sbs.bust_width, 21.0)
        self.assertIsNone(sbs.waist_width)

    def test_half_hourglass_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbs = ips.sweater_back
        self.assertEqual(sbs.shoulder_height, 24)
        self.assertEqual(sbs.armpit_height, 16)
        self.assertEqual(sbs.waist_height, 7)
        self.assertEqual(sbs.torso_hem_height, 1.5)
        self.assertEqual(sbs.hip_width, 19.5)
        self.assertEqual(sbs.cross_back_width, 14)
        self.assertEqual(sbs.neck_opening_width, 7)
        self.assertEqual(sbs.neck_height, 23)
        self.assertEqual(sbs.bust_width, 19.625)
        self.assertEqual(sbs.waist_width, 17.5)

    def test_aline_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbs = ips.sweater_back
        self.assertEqual(sbs.hip_width, 22.75)
        self.assertEqual(sbs.cross_back_width, 14)
        self.assertEqual(sbs.bust_width, 19.75)
        self.assertIsNone(sbs.waist_width)

    def test_tapered_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbs = ips.sweater_back
        self.assertEqual(sbs.hip_width, 19)
        self.assertEqual(sbs.cross_back_width, 14)
        self.assertEqual(sbs.bust_width, 20.25)
        self.assertIsNone(sbs.waist_width)

    def test_garment(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbs = ips.sweater_back

        self.assertEqual(sbs.construction, SDC.CONSTRUCTION_DROP_SHOULDER)


class SweaterfrontSchematicTest(TestCase):

    def test_make_from_gp(self):
        gp = SweaterIndividualGarmentParametersFactory()
        gp.save()
        user = UserFactory()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        sbf = ips.sweater_front
        self.assertEqual(sbf.shoulder_height, 24)
        self.assertEqual(sbf.armpit_height, 16)
        self.assertEqual(sbf.waist_height, 7)
        self.assertEqual(sbf.torso_hem_height, 1.5)
        self.assertEqual(sbf.hip_width, 19.5)
        self.assertEqual(sbf.neck_height, 18)
        self.assertEqual(sbf.bust_width, 20.375)
        self.assertEqual(sbf.waist_width, 17.5)

    def test_schematic_images(self):
        pullover_dict = {
            SDC.NECK_VEE: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-V.png",
            SDC.NECK_CREW: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Crew.png",
            SDC.NECK_SCOOP: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Scoop.png",
            SDC.NECK_BOAT: "img/schematics/set-in-sleeve/Hourglass-Front-Pullover-Boat.png",
        }
        for neckline, goal_image in list(pullover_dict.items()):
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED, neckline_style=neckline
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            ips = SweaterSchematic.make_from_garment_parameters(user, gp)
            sfs = ips.sweater_front
            schematic_image = sfs.get_schematic_image()
            self.assertEqual(schematic_image, goal_image)

    def test_half_hourglass_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sfs = ips.sweater_front
        self.assertEqual(sfs.shoulder_height, 24)
        self.assertEqual(sfs.armpit_height, 16)
        self.assertEqual(sfs.waist_height, 7)
        self.assertEqual(sfs.torso_hem_height, 1.5)
        self.assertAlmostEqual(sfs.hip_width, 20.375, 2)
        self.assertEqual(sfs.neck_height, 18)
        self.assertEqual(sfs.bust_width, 20.375)
        self.assertEqual(sfs.waist_width, 20.375)

    def test_straight_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sfs = ips.sweater_front
        self.assertEqual(sfs.hip_width, 21.0)
        self.assertEqual(sfs.bust_width, 21.0)
        self.assertIsNone(sfs.waist_width)

    def test_aline_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sfs = ips.sweater_front
        self.assertEqual(sfs.hip_width, 24.25)
        self.assertEqual(sfs.bust_width, 21.25)
        self.assertIsNone(sfs.waist_width)

    def test_tapered_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sfs = ips.sweater_front
        self.assertEqual(sfs.hip_width, 19)
        self.assertEqual(sfs.bust_width, 21.75)
        self.assertIsNone(sfs.waist_width)

    def test_compress_bust_shaping(self):
        gp = SweaterIndividualGarmentParametersFactory(below_armhole_straight=2.0)
        gp.save()
        self.assertEqual(gp.below_armhole_straight, 2.0)
        user = UserFactory()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        sbf = ips.sweater_front
        self.assertEqual(sbf.below_armpit_straight, 2.0)

    def test_expand_bust_shaping(self):
        gp = SweaterIndividualGarmentParametersFactory(below_armhole_straight=1.0)
        gp.save()
        self.assertEqual(gp.below_armhole_straight, 1.0)
        user = UserFactory()
        ips = SweaterSchematic.make_from_garment_parameters(user, gp)
        sbf = ips.sweater_front
        self.assertEqual(sbf.below_armpit_straight, 1.0)

    def test_garment(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sbf = ips.sweater_front

        self.assertEqual(sbf.construction, SDC.CONSTRUCTION_DROP_SHOULDER)


class CardiganSchematicPiecesTest(TestCase):

    def setUp(self):
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        user = UserFactory()
        self.gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)

        self.gp.save()

        # (GP attr, schematic attr)
        self.direct_attrs = [
            ("shoulder_height", "shoulder_height"),
            ("armpit_height", "armpit_height"),
            ("waist_height_front", "waist_height"),
            ("torso_hem_height", "torso_hem_height"),
            ("front_neck_height", "neck_height"),
        ]
        self.adjusted_attrs = [
            ("hip_width_front", "hip_width"),
            ("bust_width_front", "bust_width"),
            ("waist_width_front", "waist_width"),
        ]

    def test_cardigan_make_from_gp(self):

        #
        # Absolute buttonbands
        #

        # CardiganVestSchematic
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
        cvs = s_sch.cardigan_vest

        self.assertEqual(cvs.button_band_allowance, 1)
        self.assertIsNone(cvs.button_band_allowance_percentage)
        self.assertIsNone(cvs.neck_opening_width)
        self.assertEqual(cvs.button_band_allowance_inches, 1)

        for gp_attr, sc_attr in self.direct_attrs:
            self.assertEqual(getattr(self.gp, gp_attr), getattr(cvs, sc_attr), sc_attr)

        for gp_attr, sc_attr in self.adjusted_attrs:
            goal = (getattr(self.gp, gp_attr) - 1.0) / 2.0
            self.assertEqual(goal, getattr(cvs, sc_attr), sc_attr)

        # CardiganSleevedSchematic
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
        css = s_sch.cardigan_sleeved

        self.assertEqual(css.button_band_allowance, 1)
        self.assertIsNone(cvs.button_band_allowance_percentage)
        self.assertIsNone(cvs.neck_opening_width)
        self.assertEqual(cvs.button_band_allowance_inches, 1)

        for gp_attr, sc_attr in self.direct_attrs:
            self.assertEqual(getattr(self.gp, gp_attr), getattr(css, sc_attr), sc_attr)

        for gp_attr, sc_attr in self.adjusted_attrs:
            goal = (getattr(self.gp, gp_attr) - 1.0) / 2.0
            self.assertEqual(goal, getattr(css, sc_attr), sc_attr)

        #
        # Percentage-based buttonbands
        #

        for percentage in [100, 50, 0, -50]:

            # CardiganVestSchematic
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_VEST,
                button_band_allowance=None,
                button_band_allowance_percentage=percentage,
                button_band_edging_height=1,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
            cvs = s_sch.cardigan_vest

            self.assertIsNone(cvs.button_band_allowance)
            self.assertEqual(cvs.button_band_allowance_percentage, percentage)
            self.assertIsNotNone(cvs.neck_opening_width)

            neck_width = cvs.neck_opening_width
            bb_inches = neck_width * percentage / 100.00
            self.assertEqual(cvs.button_band_allowance_inches, bb_inches)

            for gp_attr, sc_attr in self.direct_attrs:
                self.assertEqual(
                    getattr(self.gp, gp_attr), getattr(cvs, sc_attr), sc_attr
                )

            for gp_attr, sc_attr in self.adjusted_attrs:
                goal = (getattr(self.gp, gp_attr) - bb_inches) / 2.0
                self.assertEqual(goal, getattr(cvs, sc_attr), sc_attr)

            #         # CardiganSleevedSchematic

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                button_band_allowance=None,
                button_band_allowance_percentage=percentage,
                button_band_edging_height=1,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
            css = s_sch.cardigan_sleeved

            self.assertIsNone(css.button_band_allowance)
            self.assertEqual(css.button_band_allowance_percentage, percentage)
            self.assertIsNotNone(css.neck_opening_width)

            neck_width = css.neck_opening_width
            bb_inches = neck_width * percentage / 100.00
            self.assertEqual(cvs.button_band_allowance_inches, bb_inches)

            for gp_attr, sc_attr in self.direct_attrs:
                self.assertEqual(
                    getattr(self.gp, gp_attr), getattr(css, sc_attr), sc_attr
                )

            for gp_attr, sc_attr in self.adjusted_attrs:
                goal = (getattr(self.gp, gp_attr) - bb_inches) / 2.0
                self.assertEqual(goal, getattr(css, sc_attr), sc_attr)

    def test_cardigan_double_into_pullover(self):

        #
        # 'Inch' buttonbands
        #

        # CardiganVestSchematic
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
        cvs = s_sch.cardigan_vest

        pvs = cvs.double_into_pullover()
        self.assertIsInstance(pvs, VestFrontSchematic)

        for gp_attr, sc_attr in self.direct_attrs + self.adjusted_attrs:
            self.assertEqual(getattr(self.gp, gp_attr), getattr(pvs, sc_attr), sc_attr)

        # CardiganSleevedSchematic
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        user = UserFactory()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.save()
        s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
        css = s_sch.cardigan_sleeved
        css._get_values_from_gp(gp)
        pss = css.double_into_pullover()
        self.assertIsInstance(pss, SweaterFrontSchematic)

        for gp_attr, sc_attr in self.direct_attrs + self.adjusted_attrs:
            self.assertEqual(getattr(self.gp, gp_attr), getattr(pss, sc_attr), sc_attr)

        #
        # 'percentage' buttonbands
        #

        for percentage in [100, 50, 0, -50]:

            # CardiganVestSchematic
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_VEST,
                button_band_allowance=None,
                button_band_allowance_percentage=percentage,
                button_band_edging_height=1,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
            csv = s_sch.cardigan_vest

            pvs = cvs.double_into_pullover()
            self.assertIsInstance(pvs, VestFrontSchematic)

            for gp_attr, sc_attr in self.direct_attrs + self.adjusted_attrs:
                self.assertEqual(
                    getattr(self.gp, gp_attr), getattr(pvs, sc_attr), sc_attr
                )

            # CardiganSleevedSchematic
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                button_band_allowance=None,
                button_band_allowance_percentage=percentage,
                button_band_edging_height=1,
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
            css = s_sch.cardigan_sleeved
            pss = css.double_into_pullover()
            self.assertIsInstance(pss, SweaterFrontSchematic)

            for gp_attr, sc_attr in self.direct_attrs + self.adjusted_attrs:
                self.assertEqual(
                    getattr(self.gp, gp_attr), getattr(pss, sc_attr), sc_attr
                )

    def test_schematic_images(self):

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
                button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            )
            user = UserFactory()
            self.gp = SweaterIndividualGarmentParameters.make_from_patternspec(
                user, pspec
            )
            self.gp.save()
            s_sch = SweaterSchematic.make_from_garment_parameters(user, self.gp)
            css = s_sch.cardigan_sleeved
            schematic_image = css.get_schematic_image()
            goal_image = cardi_dict[neckline]
            self.assertEqual(schematic_image, goal_image)

    def test_clean(self):

        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            torso_length=SDC.MED_HIP_LENGTH,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            number_of_buttons=0,
            armhole_edging_height=1,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        pspec.full_clean()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        s_sch = SweaterSchematic.make_from_garment_parameters(user, gp)
        cvs = s_sch.cardigan_vest

        for combo in itertools.product([1, None], [50, None], [7, None]):
            (inches, percent, neck) = combo
            cvs.button_band_allowance = inches
            cvs.button_band_allowance_percentage = percent
            cvs.neck_opening_width = neck

            if combo in [(1, None, None), (None, 50, 7)]:
                cvs.full_clean()
            else:
                with self.assertRaises(ValidationError):
                    cvs.full_clean()

    def test_half_hourglass_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            torso_length=SDC.MED_HIP_LENGTH,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            number_of_buttons=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
        )
        pspec.full_clean()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        cvs = CardiganVestSchematic()
        cvs._get_values_from_gp(gp)
        self.assertAlmostEqual(cvs.hip_width, 9.6875, 2)
        self.assertAlmostEqual(cvs.bust_width, 9.6875, 2)
        self.assertAlmostEqual(cvs.waist_width, 9.6875, 2)

    def test_straight_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            torso_length=SDC.MED_HIP_LENGTH,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            number_of_buttons=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        pspec.full_clean()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        cvs = CardiganVestSchematic()
        cvs._get_values_from_gp(gp)
        self.assertEqual(cvs.hip_width, 10)
        self.assertEqual(cvs.bust_width, 10)
        self.assertIsNone(cvs.waist_width)

    def test_aline_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            torso_length=SDC.MED_HIP_LENGTH,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            number_of_buttons=0,
            button_band_edging_height=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_ALINE,
        )
        pspec.full_clean()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        cvs = CardiganVestSchematic()
        cvs._get_values_from_gp(gp)
        self.assertEqual(cvs.hip_width, 11.625)
        self.assertEqual(cvs.bust_width, 10.125)
        self.assertIsNone(cvs.waist_width)

    def test_tapered_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            torso_length=SDC.MED_HIP_LENGTH,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            number_of_buttons=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_TAPERED,
        )
        pspec.full_clean()
        gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        gp.full_clean()
        cvs = CardiganVestSchematic()
        cvs._get_values_from_gp(gp)
        self.assertEqual(cvs.hip_width, 9.0)
        self.assertEqual(cvs.bust_width, 10.375)
        self.assertIsNone(cvs.waist_width)

    def test_garment(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_allowance=1,
            button_band_allowance_percentage=None,
            button_band_edging_height=1,
            number_of_buttons=0,
            armhole_edging_height=1,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        cv = ips.cardigan_vest

        self.assertEqual(cv.construction, SDC.CONSTRUCTION_DROP_SHOULDER)

    def test_values(self):
        ssch = SweaterSchematicFactory()

        sweater_back = ssch.sweater_back
        self.assertEqual(sweater_back.hip_width, 19.5)
        self.assertEqual(sweater_back.shoulder_height, 24)
        self.assertEqual(sweater_back.armpit_height, 16)
        self.assertEqual(sweater_back.waist_height, 7)
        self.assertEqual(sweater_back.bust_width, 19.625)
        self.assertEqual(sweater_back.waist_width, 17.5)
        self.assertEqual(sweater_back.neck_height, 23)
        self.assertEqual(sweater_back.cross_back_width, 14)
        self.assertEqual(sweater_back.neck_opening_width, 7)

        sweater_front = ssch.sweater_front
        self.assertEqual(sweater_front.hip_width, 19.5)
        self.assertEqual(sweater_front.shoulder_height, 24)
        self.assertEqual(sweater_front.armpit_height, 16)
        self.assertEqual(sweater_front.waist_height, 7)
        self.assertEqual(sweater_front.bust_width, 20.375)
        self.assertEqual(sweater_front.waist_width, 17.5)
        self.assertEqual(sweater_front.neck_height, 18)
        self.assertEqual(sweater_front.neckline_style, SDC.NECK_VEE)
        self.assertEqual(sweater_front.below_armpit_straight, 1.5)

        sleeve = ssch.sleeve
        self.assertEqual(sleeve.sleeve_to_armcap_start_height, 17.5)
        self.assertEqual(sleeve.bicep_width, 13.25)
        self.assertEqual(sleeve.sleeve_cast_on_width, 9)


class SleeveSchematicTest(TestCase):

    def test_schematic_images(self):
        sleeve_dict = {
            SDC.SLEEVE_FULL: "img/schematics/set-in-sleeve/Long-Sleeve.png",
            SDC.SLEEVE_THREEQUARTER: "img/schematics/set-in-sleeve/3-4-Sleeve.png",
            SDC.SLEEVE_ELBOW: "img/schematics/set-in-sleeve/Elbow-Sleeve.png",
            SDC.SLEEVE_SHORT: "img/schematics/set-in-sleeve/Short-Sleeve.png",
        }
        for length, goal_image in list(sleeve_dict.items()):
            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED, sleeve_length=length
            )
            user = UserFactory()
            gp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
            gp.save()
            ips = SweaterSchematic.make_from_garment_parameters(user, gp)
            sls = ips.sleeve
            schematic_image = sls.get_schematic_image()
            self.assertEqual(schematic_image, goal_image)

    def test_garment(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        pspec.full_clean()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(user, pspec)
        igp.full_clean()
        ips = SweaterSchematic.make_from_garment_parameters(user, igp)
        sleeve = ips.sleeve

        self.assertEqual(sleeve.construction, SDC.CONSTRUCTION_DROP_SHOULDER)


class TestGradedSweaterBackSchematicTests(TestCase):

    def test_factory(self):
        GradedSweaterBackSchematicFactory()


class TestGradedSweaterSchematic(TestCase):

    def test_make(self):
        ggp = SweaterGradedGarmentParametersFactory()
        gss = GradedSweaterSchematic.make_from_garment_parameters(ggp)

        from ..models import GradedSweaterBackSchematic

        sweater_backs = GradedSweaterBackSchematic.objects.filter(
            construction_schematic=gss
        ).all()
        self.assertEqual(len(sweater_backs), 5)
        # for (i, sweater_back) in enumerate(sweater_backs):
        #     goal_txt = f"""
        #     sweater_back{i} = RelatedFactory(GradedSweaterBackSchematicFactory, "construction_schematic",
        #                         hip_width = {sweater_back.hip_width},
        #                         shoulder_height = {sweater_back.shoulder_height},
        #                         armpit_height = {sweater_back.armpit_height},
        #                         waist_height = {sweater_back.waist_height},
        #                         bust_width = {sweater_back.bust_width},
        #                         waist_width = {sweater_back.waist_width},
        #                         neck_height = {sweater_back.neck_height},
        #                         cross_back_width = {sweater_back.cross_back_width},
        #                         neck_opening_width = {sweater_back.neck_opening_width})"""
        #     print(goal_txt)

        from ..models import GradedSweaterFrontSchematic

        sweater_fronts = GradedSweaterFrontSchematic.objects.filter(
            construction_schematic=gss
        ).all()
        self.assertEqual(len(sweater_fronts), 5)
        # for (i, sweater_front) in enumerate(sweater_fronts):
        #     goal_txt = f"""
        #     sweater_front{i} = RelatedFactory(GradedSweaterFrontSchematicFactory, "construction_schematic",
        #                         hip_width = {sweater_front.hip_width},
        #                         shoulder_height = {sweater_front.shoulder_height},
        #                         armpit_height = {sweater_front.armpit_height},
        #                         waist_height = {sweater_front.waist_height},
        #                         bust_width = {sweater_front.bust_width},
        #                         waist_width = {sweater_front.waist_width},
        #                         neck_height = {sweater_front.neck_height},
        #                         neckline_style = SDC.{sweater_front.neckline_style},
        #                         below_armpit_straight = {sweater_front.below_armpit_straight})"""
        #     print(goal_txt)

        from ..models import GradedSleeveSchematic

        sleeves = GradedSleeveSchematic.objects.filter(construction_schematic=gss).all()
        self.assertEqual(len(sleeves), 5)
        # for (i, sleeve) in enumerate(sleeves):
        #     goal_txt = f"""
        #     sleeve{i} = RelatedFactory(GradedSleeveSchematicFactory, "construction_schematic",
        #                         sleeve_to_armcap_start_height = {sleeve.sleeve_to_armcap_start_height},
        #                         bicep_width = {sleeve.bicep_width},
        #                         sleeve_cast_on_width = {sleeve.sleeve_cast_on_width})"""
        #     print(goal_txt)

    def test_factories(self):
        _ = GradedSweaterSchematicFactory()

    def test_schematic_getters(self):
        gss = GradedSweaterSchematicFactory()
        self.assertEqual(len(gss.sweater_back_schematics), 5)
        self.assertEqual(len(gss.sweater_front_schematics), 5)
        self.assertEqual(len(gss.sleeve_schematics), 5)
        self.assertEqual(len(gss.vest_back_schematics), 0)
        self.assertEqual(len(gss.vest_front_schematics), 0)
        self.assertEqual(len(gss.cardigan_sleeved_schematics), 0)
        self.assertEqual(len(gss.cardigan_vest_schematics), 0)
