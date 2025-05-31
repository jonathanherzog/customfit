import copy

from django.test import TestCase
from django.test.client import Client

from customfit.bodies.factories import BodyFactory, SimpleBodyFactory
from customfit.bodies.models import Body
from customfit.helpers.math_helpers import CompoundResult
from customfit.stitches.factories import StitchFactory
from customfit.stitches.models import Stitch
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import StaffFactory, UserFactory

from ..factories import (
    ApprovedSweaterPatternFactory,
    GradedCardiganPatternSpecFactory,
    GradedCardiganVestPatternSpecFactory,
    GradedSweaterPatternFactory,
    GradedSweaterPatternSpecFactory,
    GradedVestPatternSpecFactory,
    SweaterDesignFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    create_csv_combo,
    create_sweater_back,
    make_cardigan_sleeved_from_pspec,
    make_cardigan_vest_from_pspec,
    make_patternspec_from_design,
    make_sweaterfront_from_pspec_kwargs,
    make_vestfront_from_pspec_kwargs,
)
from ..helpers import sweater_design_choices as SDC
from ..renderers import (
    CardiganSleevedRenderer,
    CardiganVestRenderer,
    GradedSweaterPatternRendererWebFull,
    SweaterbackRenderer,
    SweaterfrontRenderer,
    SweaterPatternRendererWebFull,
    VestfrontRenderer,
)

# Base Class with helper method


class PatterntextTestCase(TestCase):

    def do_create_pattern_get_patterntext(self, user, pspec):
        p = SweaterPatternFactory.from_pspec(pspec)
        # Re-fetch the pattern from the DB to force all the type coercions
        p.refresh_from_db()

        renderer = SweaterPatternRendererWebFull(p)

        # We used to take the opportunity to test for missing variables by
        # setting the 'string_if_invalid' option in TEMPLATES:
        #
        # TEST_TEMPLATES[0]['OPTIONS']['string_if_invalid'] = "(BAD VAR: %s)"
        # with self.settings(TEMPLATES = TEST_TEMPLATES):
        #   patterntext = ...
        #
        # but that setting is apparently shared across tests and started causing
        # other tests to fail. We tried for a while to figure out how capture the
        # missing vars while still returning '' (as is required elsewhere in the template
        # engine) including writing a specialized class, but couldn't find a good option.
        # So, we're going to accept the possibility of a missing variable until we
        # find a better option or switch to Jinja or something.

        for method_call in [
            renderer.render_instructions,
            renderer.render_postamble,
            renderer.render_pattern,
        ]:
            patterntext = method_call()

        return patterntext


class TestPatterntextViewDoesntBreak(PatterntextTestCase):

    #####################################
    # Bug-cases for regression testing
    ####################################

    def test_body1_Cascade_Test1(self):
        pspec = create_csv_combo("Test 1", "Cascade 220 St st", "Test 1")
        user = UserFactory()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_body3_design4_gaugeFingerling(self):
        pspec = create_csv_combo("Test 6", "Fingering St st", "Test 4")
        user = UserFactory()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_body2_design8_gaugeFingerling(self):
        pspec = create_csv_combo("Test 5", "Fingering St st", "Test 8")
        user = UserFactory()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_test3_dk_reps_test10(self):
        pspec = create_csv_combo("Test 3", "DK Stitch repeats", "Test 10")
        user = UserFactory()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_none_stitches1(self):
        user = UserFactory()

        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_edging_stitch=None,
            sleeve_edging_height=0,
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_none_stitches2(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neck_edging_stitch=None,
            neck_edging_height=0,
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_none_stitches3(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=None,
            armhole_edging_height=0,
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_none_stitches4(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            button_band_edging_stitch=None,
            button_band_edging_height=0,
            button_band_allowance=1,
            armhole_edging_height=1,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_folded_hem_buttonband1(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_VEE,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
            armhole_edging_height=1,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_folded_hem_buttonband2(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.CARDIGAN_VEST,
            neckline_style=SDC.NECK_CREW,
            button_band_edging_stitch=StitchFactory(name="Folded hem"),
            button_band_edging_height=1,
            button_band_allowance=1,
            number_of_buttons=0,
            armhole_edging_height=1,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        pspec.clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_buttonband_percentages(self):

        user = UserFactory()

        # Use a variety of necklines
        necklines = [
            SDC.NECK_VEE,
            SDC.NECK_SCOOP,
            SDC.NECK_CREW,
            SDC.NECK_BOAT,
        ]

        percentages = [-100, -50, -1, 0, 1, 50, 99, 100]

        for neckline in necklines:
            for percentage in percentages:
                pspec = SweaterPatternSpecFactory(
                    garment_type=SDC.CARDIGAN_VEST,
                    neckline_style=neckline,
                    button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                    button_band_edging_height=1,
                    button_band_allowance=None,
                    button_band_allowance_percentage=percentage,
                    number_of_buttons=0,
                    armhole_edging_height=1,
                    armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
                )
                pspec.clean()
                self.do_create_pattern_get_patterntext(user, pspec)


class TestPatterntextGenerationFullBody(PatterntextTestCase):

    def test_hourglass_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_half_hourglass_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_straight_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_hourglass_silhouette_cardi(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_half_hourglass_silhouette_cardi(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_straight_silhouette_cardi(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette_cardi(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette_cardi(self):
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False


class TestPatterntextGenerationBodyNoOptionals(PatterntextTestCase):

    def test_hourglass_silhouette(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_half_hourglass_silhouette(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            torso_length=SDC.HIGH_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_straight_silhouette(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette(self):
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        user = UserFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_hourglass_silhouette_cardi(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HOURGLASS,
            body=body,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_half_hourglass_silhouette_cardi(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_HALF_HOURGLASS,
            body=body,
            torso_length=SDC.HIGH_HIP_LENGTH,
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_straight_silhouette_cardi(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette_cardi(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette_cardi(self):
        user = UserFactory()
        body = BodyFactory(cross_chest_distance=None, inter_nipple_distance=None)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False


class TestPatterntextGenerationNonHourglassSimpleBody(PatterntextTestCase):

    def test_straight_silhouette(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            torso_length=SDC.MED_HIP_LENGTH,
            body=body,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_straight_silhouette_cardi(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_aline_silhouette_cardi(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)
        # assert False

    def test_tapered_silhouette_cardi(self):
        user = UserFactory()
        body = SimpleBodyFactory()
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_TAPERED,
            body=body,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            button_band_edging_height=1,
            button_band_allowance=1,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            number_of_buttons=2,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_generate_body2_pattern_1(self):
        user = UserFactory()
        swatch = SwatchFactory(
            stitches_number=24,
            stitches_length=4.75,
            rows_number=33,
            rows_length=4.5,
            yarn_name="",
            yarn_maker="",
            length_per_hank=None,
            weight_per_hank=None,
            full_swatch_height=None,
            full_swatch_width=None,
            full_swatch_weight=None,
            needle_size="",
        )
        body = SimpleBodyFactory(
            waist_circ=29,
            bust_circ=33.5,
            wrist_circ=6,
            bicep_circ=12,
            armpit_to_med_hip=8 + 8.5,
            med_hip_circ=36.5,
            armpit_to_full_sleeve=17,
            armhole_depth=15.25 - 8,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            body=body,
            swatch=swatch,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_OVERSIZED,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            neckline_width=SDC.NECK_NARROW,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            hip_edging_height=1,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=1,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_edging_height=0.5,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            back_allover_stitch=StitchFactory(name="Stockinette"),
            front_allover_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_allover_stitch=StitchFactory(name="1x1 Ribbing"),
        )

        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_generate_body2_pattern_2(self):
        user = UserFactory()
        swatch = SwatchFactory(
            stitches_number=24,
            stitches_length=4.75,
            rows_number=33,
            rows_length=4.5,
            yarn_name="",
            yarn_maker="",
            length_per_hank=None,
            weight_per_hank=None,
            full_swatch_height=None,
            full_swatch_width=None,
            full_swatch_weight=None,
            needle_size="",
        )
        body = SimpleBodyFactory(
            waist_circ=29,
            bust_circ=33.5,
            wrist_circ=6,
            bicep_circ=12,
            armpit_to_med_hip=8 + 8.5,
            med_hip_circ=36.5,
            armpit_to_full_sleeve=17,
            armhole_depth=15.25 - 8,
            body_type=Body.BODY_TYPE_UNSTATED,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            swatch=swatch,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=2,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=StitchFactory(name="Rosette"),
            button_band_edging_height=2.5,
            button_band_allowance=1,
            number_of_buttons=0,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            hip_edging_height=2.5,
            hip_edging_stitch=StitchFactory(name="Rosette"),
            neck_edging_stitch=StitchFactory(name="Rosette"),
            neck_edging_height=2.5,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_edging_height=2.5,
            sleeve_edging_stitch=StitchFactory(name="Rosette"),
            back_allover_stitch=StitchFactory(name="Stockinette"),
            front_allover_stitch=StitchFactory(name="Stockinette"),
            sleeve_allover_stitch=StitchFactory(name="Stockinette"),
        )

        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_generate_errorcase_pattern_1(self):
        # An oversized, A-line, wide V-neck pullover in stockinette with 2x2
        # ribbing on all edges, using errorcase body. Any swatch works.
        user = UserFactory()
        swatch = SwatchFactory(
            stitches_number=40.5,
            stitches_length=6,
            rows_number=41,
            rows_length=3.9375,
            yarn_name="",
            yarn_maker="",
            length_per_hank=375,
            weight_per_hank=115,
            full_swatch_height=7.5,
            full_swatch_width=8,
            full_swatch_weight=21,
            needle_size="2",
        )
        body = SimpleBodyFactory(
            waist_circ=32.5,
            bust_circ=38.5,
            name="errorcase body",
            wrist_circ=6.25,
            bicep_circ=11.5,
            armpit_to_med_hip=8.25 + 10,
            med_hip_circ=41.25,
            armpit_to_full_sleeve=20.5,
            armhole_depth=16 - 8.25,
            body_type=Body.BODY_TYPE_ADULT_WOMAN,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_ALINE,
            body=body,
            swatch=swatch,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_OVERSIZED,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_width=SDC.NECK_WIDE,
            neckline_depth=2,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            button_band_edging_stitch=None,
            button_band_edging_height=None,
            button_band_allowance=None,
            number_of_buttons=None,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            hip_edging_height=1,
            hip_edging_stitch=StitchFactory(name="2x2 Ribbing"),
            neck_edging_stitch=StitchFactory(name="2x2 Ribbing"),
            neck_edging_height=1,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_edging_height=1,
            sleeve_edging_stitch=StitchFactory(name="2x2 Ribbing"),
            back_allover_stitch=StitchFactory(name="Stockinette"),
            front_allover_stitch=StitchFactory(name="Stockinette"),
            sleeve_allover_stitch=StitchFactory(name="Stockinette"),
        )

        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_generate_errorcase_body_pattern_2(self):
        # A straight, crew neck, average fit pullover with a narrow crew neck.
        # 1x1 rib edging. Use errrorcase body from my account, any swatch works.
        user = UserFactory()
        swatch = SwatchFactory(
            stitches_number=40.5,
            stitches_length=6,
            rows_number=41,
            rows_length=3.9375,
            yarn_name="",
            yarn_maker="",
            length_per_hank=375,
            weight_per_hank=115,
            full_swatch_height=7.5,
            full_swatch_width=8,
            full_swatch_weight=21,
            needle_size="2",
        )
        body = SimpleBodyFactory(
            waist_circ=28,
            bust_circ=36,
            name="errorcase body2",
            wrist_circ=5.75,
            bicep_circ=11.0,
            armpit_to_med_hip=9 + 10.5,
            med_hip_circ=36.25,
            armpit_to_full_sleeve=19.375,
            armhole_depth=16.5 - 9,
            body_type=Body.BODY_TYPE_UNSTATED,
        )
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            body=body,
            swatch=swatch,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            neckline_width=SDC.NECK_AVERAGE,
            neckline_depth=4,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            button_band_edging_stitch=None,
            button_band_edging_height=None,
            button_band_allowance=None,
            number_of_buttons=None,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            hip_edging_height=2,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=2,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_edging_height=2,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            back_allover_stitch=StitchFactory(name="Stockinette"),
            front_allover_stitch=StitchFactory(name="Stockinette"),
            sleeve_allover_stitch=StitchFactory(name="Stockinette"),
        )

        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)

    def test_generate_kid_patterns_coarse_swatch(self):
        user = UserFactory()
        swatch = SwatchFactory(
            stitches_number=5, stitches_length=1, rows_number=7, rows_length=1
        )

        body_dict = {
            "bust_circ": 23,
            "waist_circ": 21.5,
            "med_hip_circ": 23.5,
            "armpit_to_med_hip": 11,
            "armhole_depth": 5.75,
            "bicep_circ": 7.5,
            "wrist_circ": 5,
            "armpit_to_full_sleeve": 10.5,
            "body_type": Body.BODY_TYPE_CHILD
        }

        body = SimpleBodyFactory(**body_dict)
        pspec = SweaterPatternSpecFactory(
            silhouette=SDC.SILHOUETTE_STRAIGHT,
            body=body,
            swatch=swatch,
            torso_length=SDC.MED_HIP_LENGTH,
            garment_fit=SDC.FIT_CHILDS_TIGHT,
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_CREW,
            neckline_width=SDC.NECK_NARROW,
            neckline_depth=3,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            sleeve_shape=SDC.SLEEVE_TAPERED,
            hip_edging_height=1,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=1,
            sleeve_length=SDC.SLEEVE_FULL,
            sleeve_edging_height=0.5,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            back_allover_stitch=StitchFactory(name="Stockinette"),
            front_allover_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_allover_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(user, pspec)


class TestPatterntextViewCorrectness(PatterntextTestCase):

    def setUp(self):
        super(TestPatterntextViewCorrectness, self).setUp()

        self.alice = UserFactory()
        self.alice.save()

        self.client = Client(HTTP_HOST="example.com")
        self.client.force_login(self.alice)

    def tearDown(self):
        self.client.logout()
        # This will also delete objects FKed off of her in a cascade.
        self.alice.delete()
        super(TestPatterntextViewCorrectness, self).tearDown()

    def _make_pattern_from_pspec(self, pspec):
        return ApprovedSweaterPatternFactory.from_pspec(pspec)

    def _view_pattern(self, **kwargs):
        des = SweaterDesignFactory(**kwargs)
        name = "foo"
        swatch = SwatchFactory()
        body = BodyFactory()
        fit = SDC.FIT_HOURGLASS_AVERAGE
        silhouette = SDC.SILHOUETTE_HOURGLASS
        pspec = make_patternspec_from_design(
            des, self.alice, name, swatch, body, silhouette, fit
        )
        pspec.clean()
        pspec.save()
        p = self._make_pattern_from_pspec(pspec)
        url = p.get_absolute_url()
        response = self.client.get(url)
        return response

    def test_cable_stitches(self):
        # Let's test that cable stitches make it into the final pattern
        with self.settings(ALLOWED_HOSTS=["example.com"]):
            response = self._view_pattern(
                garment_type=SDC.PULLOVER_SLEEVED,
                neckline_style=SDC.NECK_CREW,
                back_cable_stitch=StitchFactory(
                    name="back cable stitch", notes="Back cable stitch notes"
                ),
                front_cable_stitch=StitchFactory(
                    name="front cable stitch", notes="Front cable stitch notes"
                ),
                sleeve_cable_stitch=StitchFactory(
                    name="sleeve cable stitch", notes="Sleeve cable stitch notes"
                ),
                front_cable_extra_stitches=0,
                back_cable_extra_stitches=0,
                sleeve_cable_extra_stitches=0,
            )
        self.assertContains(response, "Back cable stitch notes")
        self.assertContains(response, "Front cable stitch notes")
        self.assertContains(response, "Sleeve cable stitch notes")


class TestSweaterBackPieceElements(TestCase):

    maxDiff = None

    def _get_element_by_name(
        self, sweaterback_renderer, element_name, additional_context=None
    ):
        if additional_context is None:
            additional_context = {"piece": sweaterback_renderer.piece_list}
        elements = sweaterback_renderer._make_elements(additional_context)
        elements = [el for el in elements if el.display_name == element_name]
        self.assertEqual(len(elements), 1)
        element = elements[0]
        return element

    def setUp(self):
        self.sweaterback = create_sweater_back()
        self.sweaterback_renderer = SweaterbackRenderer(self.sweaterback)

    def test_armhole_element(self):

        # Armholes start before neckline
        armhole_element = self._get_element_by_name(
            self.sweaterback_renderer, "Armhole shaping"
        )

        self.assertEqual(armhole_element.start_rows(), CompoundResult([113]))
        self.assertEqual(armhole_element.end_rows(), CompoundResult([129]))

        subsections = armhole_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([113]))
        self.assertEqual(subsection.end_rows, CompoundResult([129]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                10 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
                BO 5 stitches at the beginning of the next 2 rows.
                    BO 3 stitches at the beginning of following 2 rows.
                Decrease 1 stitch at <em><strong>each end</strong></em> of every RS row
                7 times as follows:
            </p><p>
            <em>
            Decrease row (RS):
            </em> Knit 1, ssk, work to last 3 sts, k2tog, k 1. Two stitches decreased.
            </p><p>
                    70 stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_shoulder_element(self):

        # Armholes start before neckline

        shoulder_element = self._get_element_by_name(
            self.sweaterback_renderer, "Shoulder shaping"
        )
        self.assertEqual(shoulder_element.start_rows(), CompoundResult([169]))
        self.assertEqual(shoulder_element.end_rows(), CompoundResult([172]))

        subsections = shoulder_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([170]))
        self.assertEqual(subsection1.end_rows, CompoundResult([172]))
        text = subsection1.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a RS row:
              169 rows from beginning,
                    40 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (WS):</em> BO 9
              sts, work to end. Work 1 RS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>

            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([169]))
        self.assertEqual(subsection2.end_rows, CompoundResult([171]))
        text = subsection2.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a WS row:
              168 rows from beginning,
                    39 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (RS):</em> BO 9
              sts, work to end. Work 1 WS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element(self):

        # Armholes start before neckline

        neckline_element = self._get_element_by_name(
            self.sweaterback_renderer, "Neckline"
        )
        self.assertEqual(neckline_element.start_rows(), CompoundResult([163]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([167]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([163]))
        self.assertEqual(subsection1.end_rows, CompoundResult([167]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              23&quot;/58.5 cm,
              ending with a WS row:
                162 rows from beginning,
                34 rows from (and including) last armhole shaping row.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
            <p>
                <em>Next row (RS):</em> Work 19
                stitches, BO 32 stitches, work to end.
                You will now work the left shoulder only; place stitches for
                right shoulder on a holder if desired.
            </p>
                <p>
                    Work as established, decreasing 1 stitch at neck edge every
                    RS row twice as follows:
                </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                  </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([164]))
        self.assertEqual(subsection2.end_rows, CompoundResult([167]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
                <p>
                    Work as established, decreasing 1 stitch at neck edge every
                    RS row twice as follows:
                </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Work to last 3 sts, k2tog, k 1.
                  </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>

            """
        self.assertHTMLEqual(text, goal_text)


class TestSweaterFrontPieceElements(TestCase):

    maxDiff = None

    def _get_element_by_name(self, renderer, element_name, additional_context=None):
        if additional_context is None:
            additional_context = {"piece": renderer.piece_list}
        elements = renderer._make_elements(additional_context)
        elements = [el for el in elements if el.display_name == element_name]
        self.assertEqual(len(elements), 1)
        element = elements[0]
        return element

    def setUp(self):
        sweater_front_armhole_first = make_sweaterfront_from_pspec_kwargs(
            neckline_depth_orientation=SDC.ABOVE_ARMPIT, neckline_depth=2
        )
        self.assertLess(
            sweater_front_armhole_first.hem_to_armhole_shaping_start,
            sweater_front_armhole_first.hem_to_neckline_shaping_start,
        )
        self.sweaterfront_renderer_armhole_first = SweaterfrontRenderer(
            sweater_front_armhole_first
        )

        sweater_front_neckline_first = make_sweaterfront_from_pspec_kwargs(
            neckline_depth_orientation=SDC.BELOW_ARMPIT, neckline_depth=2
        )
        self.assertLess(
            sweater_front_neckline_first.hem_to_neckline_shaping_start,
            sweater_front_neckline_first.hem_to_armhole_shaping_start,
        )
        self.sweaterfront_renderer_neckline_first = SweaterfrontRenderer(
            sweater_front_neckline_first
        )

    def test_armhole_element_before_neckline(self):

        # Armholes start before neckline

        armhole_element = self._get_element_by_name(
            self.sweaterfront_renderer_armhole_first, "Armhole shaping"
        )

        self.assertEqual(armhole_element.start_rows(), CompoundResult([113]))
        self.assertEqual(armhole_element.end_rows(), CompoundResult([129]))

        subsections = armhole_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([113]))
        self.assertEqual(subsection.end_rows, CompoundResult([129]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                12 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
                BO 5 stitches at the beginning of the next 2 rows.
                    BO 3 stitches at the beginning of following 2 rows.
                Decrease 1 stitch at <em><strong>each end</strong></em> of every RS row
                7 times as follows:
                </p><p>
                <em>
                Decrease row (RS):</em> Knit 1, ssk, work to last 3 sts, k2tog, k 1. Two stitches decreased.
                </p><p>

                    72 stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

    def test_armhole_element_after_neckline(self):

        # Armholes start before neckline
        armhole_element = self._get_element_by_name(
            self.sweaterfront_renderer_neckline_first, "Armhole shaping"
        )

        self.assertEqual(armhole_element.start_rows(), CompoundResult([113]))
        self.assertEqual(armhole_element.end_rows(), CompoundResult([129]))

        subsections = armhole_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([114]))
        self.assertEqual(subsection1.end_rows, CompoundResult([129]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                15 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              RS row even.
            </p>
            <p>
                  <em>Next row (WS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1. One stitch decreased.
              </p>
              <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([113]))
        self.assertEqual(subsection2.end_rows, CompoundResult([129]))
        text = subsection2.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                13 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              WS row even.
            </p>
            <p>
                  <em>Next row (RS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end. One stitch decreased.
              </p>
              <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

    def test_shoulder_element(self):

        # Armholes start before neckline
        shoulder_element = self._get_element_by_name(
            self.sweaterfront_renderer_neckline_first, "Shoulder shaping"
        )

        self.assertEqual(shoulder_element.start_rows(), CompoundResult([169]))
        self.assertEqual(shoulder_element.end_rows(), CompoundResult([172]))

        subsections = shoulder_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([170]))
        self.assertEqual(subsection1.end_rows, CompoundResult([172]))
        text = subsection1.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a RS row:
              169 rows from beginning,
                    40 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (WS):</em> BO 9
              sts, work to end. Work 1 RS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([169]))
        self.assertEqual(subsection2.end_rows, CompoundResult([171]))
        text = subsection2.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a WS row:
              168 rows from beginning,
                    39 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (RS):</em> BO 9
              sts, work to end. Work 1 WS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_veeneck(self):

        # Armholes start before neckline
        sweaterfront_veeneck = make_sweaterfront_from_pspec_kwargs(
            neckline_style=SDC.NECK_VEE
        )
        sweaterfront_renderer_veeneck = SweaterbackRenderer(sweaterfront_veeneck)
        neckline_element = self._get_element_by_name(
            sweaterfront_renderer_veeneck, "Neckline"
        )

        self.assertEqual(neckline_element.start_rows(), CompoundResult([127]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([165]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([165]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                14 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
              <p>
                <em>Next row (RS)</em>: Work to the center of your stitches, place
                these stitches on a holder for left shoulder, work to end. You will now
                work on right shoulder stitches only.
              </p>
                <p>
                  Decrease 1 stitch at neck edge of next RS row
                  and then every 2 rows
                  18 additional
                  times as follows:
                </p>                  
                <p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p>
                <p>
                  19 total decrease rows worked.
                </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([128]))
        self.assertEqual(subsection2.end_rows, CompoundResult([165]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
                <p>
                  Decrease 1 stitch at neck edge of next RS row
                  and then every 2 rows
                  18 additional
                  times as follows:
                  </p>
                  <p>
                    <em>
                    Decrease row (RS):
                    </em>Work to last 3 sts, k2tog, k 1.
                    </p>
                  <p>
                  19 total decrease rows worked.
                </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_scoopneck(self):

        # Armholes start before neckline
        sweaterfront_veeneck = make_sweaterfront_from_pspec_kwargs(
            neckline_style=SDC.NECK_SCOOP
        )
        sweaterfront_renderer_veeneck = SweaterbackRenderer(sweaterfront_veeneck)
        neckline_element = self._get_element_by_name(
            sweaterfront_renderer_veeneck, "Neckline"
        )

        self.assertEqual(neckline_element.start_rows(), CompoundResult([127]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([149]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([149]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                14 rows from start of armhole bind-offs.
            </p>
            <p>
              On your last row, mark center 14 sts.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
              <p>
                <em>Next row (RS):</em>Work to marker, BO center 14 sts to next marker, work to end. 
                You will now work the right shoulder only; place stitches for the left shoulder on a holder if desired.
              </p>
                  <p>
                         Decrease 1 stitch at neck edge of <strong>every row</strong>
                         5 times, then every RS row
                         4 times, and then every other RS row
                         3 times as follows:
                  </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p><p>
                <em>
                Decrease row (WS):
                </em>Work to last 3 sts, p2tog-tbl, p 1.
                  </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([128]))
        self.assertEqual(subsection2.end_rows, CompoundResult([149]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
                  <p>
                         Decrease 1 stitch at neck edge of <strong>every row</strong>
                         5 times, then every RS row
                         4 times, and then every other RS row
                         3 times as follows:
                  </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1.
            </p><p>
            <em>
            Decrease row (WS):
            </em>P 1, p2tog, work to end.
              </p>      
                  
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_boatneck(self):

        # Armholes start before neckline
        sweaterfront_veeneck = make_sweaterfront_from_pspec_kwargs(
            neckline_style=SDC.NECK_BOAT
        )
        sweaterfront_renderer_veeneck = SweaterbackRenderer(sweaterfront_veeneck)
        neckline_element = self._get_element_by_name(
            sweaterfront_renderer_veeneck, "Neckline"
        )

        self.assertEqual(neckline_element.start_rows(), CompoundResult([127]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([132]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([132]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                14 rows from start of armhole bind-offs.
            </p>
            <p>
                On your last row, mark center 32 stitches.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
            <p>
                <em>Next row (RS):</em> Work to marker, BO center 32 sts to next marker, work to end. 
                You will now work the right shoulder only; place stitches for left shoulder on a holder if desired.
            </p>
            <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 3 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end.
              </p>
              <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([128]))
        self.assertEqual(subsection2.end_rows, CompoundResult([132]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
            <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 3 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1.
              </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_tcneck(self):

        # Armholes start before neckline
        sweaterfront_veeneck = make_sweaterfront_from_pspec_kwargs(
            neckline_style=SDC.NECK_TURKS_AND_CAICOS
        )
        sweaterfront_renderer_veeneck = SweaterbackRenderer(sweaterfront_veeneck)
        neckline_element = self._get_element_by_name(
            sweaterfront_renderer_veeneck, "Neckline"
        )

        self.assertEqual(neckline_element.start_rows(), CompoundResult([127]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([132]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([132]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              <strong>
                Lace And Neck Shaping:
              </strong>
            </p>
            <p>
              Work as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                14 rows from armhole.
              On last row, place markers around center 24 stitches.
            </p>
            <p>
              <em>Work lace:</em>
            </p>
            <p>
              <em>Next row (RS):</em> Work to first lace marker, sm, work Row 1 of
              Shower Stitch to next lace marker, sm, work to end. Stockinette and
              armhole shaping on outside of lace markers, Shower Stitch between lace
              markers.
            </p>
            <p>
              Continue armhole shaping, Stockinette Stitch, and Shower Stitch as
              established until lace measures
              3\xbd&quot;/9 cm:
              23 rows from start of lace, ending with a
              RS row. On your last row, mark center 32 sts.
            </p>
            <p>
              <em>Next row (WS):</em> Purl to first marker, rm, work in Shower Stitch
              to final marker, rm, purl to end. One marker remains, for neck shaping.
            </p>
            <p>
              <em>Shape neck:</em>
            </p>
              <p>
                <em>Next row (RS):</em>Work to marker, BO center 32 sts to marker, work to end. 
                You will now work the right shoulder only; place stitches for left shoulder on a holder if desired.
              </p>
              <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 3 times.
              </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """

        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([128]))
        self.assertEqual(subsection2.end_rows, CompoundResult([132]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
              <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 3 times.
              </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_crewneck(self):

        # Armholes start before neckline
        sweaterfront_veeneck = make_sweaterfront_from_pspec_kwargs(
            neckline_style=SDC.NECK_CREW
        )
        sweaterfront_renderer_veeneck = SweaterbackRenderer(sweaterfront_veeneck)
        neckline_element = self._get_element_by_name(
            sweaterfront_renderer_veeneck, "Neckline"
        )

        self.assertEqual(neckline_element.start_rows(), CompoundResult([127]))
        self.assertEqual(neckline_element.end_rows(), CompoundResult([141]))

        subsections = neckline_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([141]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                14 rows from start of armhole bind-offs.
            </p>
            <p>
                    On your last row, mark 18 center stitches.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
            <p>
                        <em>Next row (RS):</em> Work to first neck marker, BO 18 sts to next marker, work to end.
            </p>
            <p>
                You will now work right neck only; place sts for left neck on holder
                if desired.
            </p>
                <p>
                    Decrease 1 stitch at neck edge of every row
                    5 times and every RS row
                    5 times as follows:
                </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p><p>
                <em>
                Decrease row (WS):
                </em>Work to last 3 sts, p2tog-tbl, p 1.
                  </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
           """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([128]))
        self.assertEqual(subsection2.end_rows, CompoundResult([141]))
        text = subsection2.render(False)
        goal_text = """
            <p>
                Reattach yarn to WS of held stitches.
            </p>
                <p>
                    Decrease 1 stitch at neck edge of every row
                    5 times and every RS row
                    5 times as follows:
                </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Work to last 3 sts, k2tog, k 1.
                </p><p>
                <em>
                Decrease row (WS):
                </em>P 1, p2tog, work to end.
                  </p>
              <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)


class TestCardiganSleevedFrontPieceElements(TestCase):

    maxDiff = None

    def _make_cardigan_front(self, **kwargs):
        default_kwargs = {
            "garment_type": SDC.CARDIGAN_SLEEVED,
            "button_band_allowance": 2,
            "button_band_edging_stitch": StitchFactory(),
            "neckline_depth_orientation": SDC.ABOVE_ARMPIT,
            "neckline_depth": 2,
        }
        default_kwargs.update(kwargs)
        pspec = SweaterPatternSpecFactory(**default_kwargs)
        return make_cardigan_sleeved_from_pspec(pspec)

    def _get_elements_by_name(self, renderer, element_name):
        context1 = {"piece": renderer.piece_list}
        context1.update(renderer.side_one_dict)
        context2 = {"piece": renderer.piece_list}
        context2.update(renderer.side_two_dict)

        def _get_element_by_name(context):
            elements = renderer._make_elements(context)
            elements = [el for el in elements if el.display_name == element_name]
            self.assertEqual(len(elements), 1)
            element = elements[0]
            return element

        return (_get_element_by_name(context1), _get_element_by_name(context2))

    def _generate_element_pair(self, name, **kwargs):
        cf = self._make_cardigan_front(**kwargs)
        cfr = CardiganSleevedRenderer(cf)
        pair = self._get_elements_by_name(cfr, name)
        return pair

    def test_armhole_element_before_neckline(self):

        # Armholes start before neckline

        (side1_element, side2_element) = self._generate_element_pair(
            "Armhole shaping", neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([114]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([129]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([114]))
        self.assertEqual(subsection.end_rows, CompoundResult([129]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                13 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              RS row even.
            </p>
            <p>
                  <em>Next row (WS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p><p>
                <em>Decrease row (RS): </em>Work to last 3 sts, k2tog, k 1. One stitch decreased.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([113]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([129]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([113]))
        self.assertEqual(subsection.end_rows, CompoundResult([129]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                12 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              WS row even.
            </p>
            <p>
                  <em>Next row (RS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p><p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end. One stitch decreased.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

    def test_armhole_element_after_neckline(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Armhole shaping", neckline_depth_orientation=SDC.BELOW_ARMPIT
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([114]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([129]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([114]))
        self.assertEqual(subsection1.end_rows, CompoundResult([129]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                15 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              RS row even.
            </p>
            <p>
                  <em>Next row (WS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p><p>
            <em>
                Decrease row (RS): </em>Work to last 3 sts, k2tog, k 1. One stitch decreased.
            </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([113]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([129]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([113]))
        self.assertEqual(subsection1.end_rows, CompoundResult([129]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                13 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end. Work 1
              WS row even.
            </p>
            <p>
                  <em>Next row (RS)</em>:
                BO 3 stitches, work to end.
            </p>
            <p>
              Decrease 1 stitch at armhole edge of every RS row
              7 times as follows:
            </p><p>
                <em> Decrease row (RS): </em>Knit 1, ssk, work to end. One stitch decreased.
            </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

    def test_shoulder_element(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Shoulder shaping", neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([170]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([172]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([170]))
        self.assertEqual(subsection1.end_rows, CompoundResult([172]))
        text = subsection1.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a RS row:
              169 rows from beginning,
                    40 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (WS):</em> BO 9
              sts, work to end. Work 1 RS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([169]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([171]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([169]))
        self.assertEqual(subsection1.end_rows, CompoundResult([171]))
        text = subsection1.render(False)
        goal_text = """
            <p>Continue as established until piece measures
              24&quot;/61 cm, ending with a WS row:
              168 rows from beginning,
                    39 rows from (and including) last armhole decrease row.
            </p>
            <p>
              <strong>Shape shoulders</strong>:
            </p>
            <p>
              <em>Next row (RS):</em> BO 9
              sts, work to end. Work 1 WS row even.
            </p>
            <p>
              BO remaining
              8 sts.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_veeneck(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Neckline",
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            neckline_style=SDC.NECK_VEE,
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([127]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([166]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([166]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                13 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
                <p>
                  Beginning with a RS row, decrease 1 stitch at neck edge of this row
                  and then every 3 rows
                  13 additional times as follows:
                </p><p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p><p>
                <strong>
                  NOTE: Some decreases will fall on WS rows.
                  </strong>
                  </p><p>
                <em>
                Decrease row (WS):
                </em>Work to last 3 sts, p2tog-tbl, p 1.
                </p><p>
                14 total decrease rows worked.
                </p>            
                <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([128]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([167]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([128]))
        self.assertEqual(subsection1.end_rows, CompoundResult([167]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a RS row:
                127 rows from beginning,
                15 rows from start of armhole bind-offs.
            </p>
            <p>
              Work one WS row even.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
                <p>
                  Beginning with a RS row, decrease 1 stitch at neck edge of this row
                  and then every 3 rows
                  13 additional times as follows:
                </p>
                <p>
                <em>
                Decrease row (RS):
                </em> Work to last 3 sts, k2tog, k 1.
                </p><p>
                <strong>
                  NOTE: Some decreases will fall on WS rows.
                  </strong>
                  </p><p>
                <em>
                Decrease row (WS):
                </em>P 1, p2tog, work to end.
                </p><p>
                14 total decrease rows worked.
                </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_scoopneck(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Neckline",
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            neckline_style=SDC.NECK_SCOOP,
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([127]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([143]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([143]))
        text = subsection1.render(False)
        goal_text = """
                <p>
                  Continue as established until piece measures
                  18&quot;/45.5 cm,
                  ending with a WS row:
                    126 rows from beginning,
                    13 rows from start of armhole bind-offs.
                </p>
                <p>
                  <strong>
                    Shape neck:
                  </strong>
                </p>
                  <p>
                    <em>Next row (RS):</em> BO
                    5 stitches, work to end.
                  </p>
                            <p>
                                Decrease 1 stitch at neck edge of <strong>every row</strong>
                                4 times, then every RS row
                                3 times, and then every other RS row
                                2 times as follows:
                            </p>
                <p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p><p>
                <em>
                Decrease row (WS):
                </em>Work to last 3 sts, p2tog-tbl, p 1.
                  </p>
                <p>
                  When all shaping is complete, 17
                  shoulder stitches remain.
                </p>
            """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([128]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([143]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([128]))
        self.assertEqual(subsection1.end_rows, CompoundResult([143]))
        text = subsection1.render(False)
        goal_text = """
                <p>
                  Continue as established until piece measures
                  18&quot;/45.5 cm,
                  ending with a RS row:
                    127 rows from beginning,
                    15 rows from start of armhole bind-offs.
                </p>
                <p>
                  <strong>
                    Shape neck:
                  </strong>
                </p>
                  <p>
                    <em>Next row (WS):</em> BO
                    5 stitches, work to end.
                  </p>
                            <p>
                                Decrease 1 stitch at neck edge of <strong>every row</strong>
                                4 times, then every RS row
                                3 times, and then every other RS row
                                2 times as follows:
                            </p>
                    <p>
                    <em>
                    Decrease row (RS):
                    </em>Work to last 3 sts, k2tog, k 1.
                    </p><p>
                    <em>
                    Decrease row (WS):
                    </em>P 1, p2tog, work to end.
                      </p>
                  <p>
                  When all shaping is complete, 17
                  shoulder stitches remain.
                </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_boatneck(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Neckline",
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            neckline_style=SDC.NECK_BOAT,
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([127]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([131]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([131]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                13 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
            <p>
                <em>Next row (RS):</em> BO 12
                stitches, work to end.
            </p>
            <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 2 times as follows:
            </p>
        <p>
        <em>
        Decrease row (RS):
        </em>Knit 1, ssk, work to end.
        </p><p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([128]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([131]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([128]))
        self.assertEqual(subsection1.end_rows, CompoundResult([131]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a RS row:
                127 rows from beginning,
                15 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
            <p>
                <em>Next row (WS):</em> BO 12
                stitches, work to end.
            </p>
            <p>
                Work as established, decreasing 1 stitch at the neck edge every
                RS row 2 times as follows:
          </p><p>
          <em>
          Decrease row (RS):
          </em>Work to last 3 sts, k2tog, k 1.
          </p><p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
            """
        self.assertHTMLEqual(text, goal_text)

    def test_neckline_element_crewneck(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Neckline",
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            neckline_style=SDC.NECK_CREW,
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([127]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([137]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([127]))
        self.assertEqual(subsection1.end_rows, CompoundResult([137]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a WS row:
                126 rows from beginning,
                13 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
                <p>
                    <em>Next row (RS):</em> BO
                    7 stitches, work to end.
                </p>
                    <p>
                    Decrease 1 stitch at neck edge of every row
                    4 times and every RS row
                    3 times as follows:
                </p><p>
                <em>
                Decrease row (RS):
                </em>Knit 1, ssk, work to end.
                </p><p>
                <em>
                Decrease row (WS):
                </em>Work to last 3 sts, p2tog-tbl, p 1.
                    </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
           """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([128]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([137]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([128]))
        self.assertEqual(subsection1.end_rows, CompoundResult([137]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              18&quot;/45.5 cm,
              ending with a RS row:
                127 rows from beginning,
                15 rows from start of armhole bind-offs.
            </p>
            <p>
              <strong>
                Shape neck:
              </strong>
            </p>
                <p>
                    <em>Next row (WS):</em> BO
                    7 stitches, work to end.
                </p>
                    <p>
                    Decrease 1 stitch at neck edge of every row
                    4 times and every RS row
                    3 times as follows:
                </p><p>
                <em>
                Decrease row (RS):
                </em>Work to last 3 sts, k2tog, k 1.
                </p><p>
                <em>
                Decrease row (WS):
                </em>P 1, p2tog, work to end.
                    </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
           """
        self.assertHTMLEqual(text, goal_text)


class TestVestFrontPieceElements(TestCase):

    maxDiff = None

    def _make_vestfront(self, **kwargs):
        pspec_params = {"garment_type": SDC.PULLOVER_VEST}
        pspec_params.update(kwargs)
        return make_vestfront_from_pspec_kwargs(**pspec_params)

    def _get_element_by_name(self, renderer, element_name, additional_context=None):
        if additional_context is None:
            additional_context = {"piece": renderer.piece_list}
        elements = renderer._make_elements(additional_context)
        elements = [el for el in elements if el.display_name == element_name]
        self.assertEqual(len(elements), 1)
        element = elements[0]
        return element

    def setUp(self):
        vest_front_armhole_first = self._make_vestfront(
            neckline_depth_orientation=SDC.ABOVE_ARMPIT, neckline_depth=2
        )
        self.assertLess(
            vest_front_armhole_first.hem_to_armhole_shaping_start,
            vest_front_armhole_first.hem_to_neckline_shaping_start,
        )
        self.vestfront_renderer_armhole_first = VestfrontRenderer(
            vest_front_armhole_first
        )

        vest_front_neckline_first = self._make_vestfront(
            neckline_depth_orientation=SDC.BELOW_ARMPIT, neckline_depth=2
        )
        self.assertLess(
            vest_front_neckline_first.hem_to_neckline_shaping_start,
            vest_front_neckline_first.hem_to_armhole_shaping_start,
        )
        self.vestfront_renderer_neckline_first = VestfrontRenderer(
            vest_front_neckline_first
        )

    def test_armhole_element_before_neckline(self):

        # Armholes start before neckline

        armhole_element = self._get_element_by_name(
            self.vestfront_renderer_armhole_first, "Armhole shaping"
        )

        self.assertEqual(armhole_element.start_rows(), CompoundResult([113]))
        self.assertEqual(armhole_element.end_rows(), CompoundResult([131]))

        subsections = armhole_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([113]))
        self.assertEqual(subsection.end_rows, CompoundResult([131]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                12 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              BO 5 stitches at the beginning of the next 2 rows.
                Decrease 1 stitch at <em><strong>each end</strong></em> of
                every row 3 times,
                then every RS row 7 times as follows:
                </p>
               <p>
            <em>
            Decrease row (RS):</em> Knit 1, ssk, work to last 3 sts, k2tog, k 1.
            </p><p>
            <em>
            Decrease row (WS):</em> Purl 1, p2tog, work to last 3 sts, p2tog-tbl, p 1.
            </p><p> Two stitches
            decreased.
            </p>
            <p>
                72 stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

    def test_armhole_element_after_neckline(self):

        # Armholes start before neckline
        armhole_element = self._get_element_by_name(
            self.vestfront_renderer_neckline_first, "Armhole shaping"
        )

        self.assertEqual(armhole_element.start_rows(), CompoundResult([113]))
        self.assertEqual(armhole_element.end_rows(), CompoundResult([131]))

        subsections = armhole_element.subsections
        self.assertEqual(len(subsections), 2)

        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([114]))
        self.assertEqual(subsection1.end_rows, CompoundResult([131]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                15 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
           <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl 1, p2tog, work to end.
            </p><p>
            One stitch decreased.
            </p> 
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

        subsection2 = subsections[1]
        self.assertEqual(subsection2.start_rows, CompoundResult([113]))
        self.assertEqual(subsection2.end_rows, CompoundResult([129]))
        text = subsection2.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                13 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl to last 3 sts, p2tog-tbl, p 1.
            </p><p>
            One stitch decreased.
          </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)


class TestCardiganVestFrontPieceElements(TestCase):

    maxDiff = None

    def _make_cardigan_front(self, **kwargs):

        default_kwargs = {
            "garment_type": SDC.CARDIGAN_VEST,
            "button_band_allowance": 2,
            "button_band_edging_stitch": StitchFactory(),
            "neckline_depth_orientation": SDC.ABOVE_ARMPIT,
            "neckline_depth": 2,
        }
        default_kwargs.update(kwargs)
        pspec = SweaterPatternSpecFactory(**default_kwargs)
        return make_cardigan_vest_from_pspec(pspec)

    def _get_elements_by_name(self, renderer, element_name):
        context1 = {"piece": renderer.piece_list}
        context1.update(renderer.side_one_dict)
        context2 = {"piece": renderer.piece_list}
        context2.update(renderer.side_two_dict)

        def _get_element_by_name(context):
            elements = renderer._make_elements(context)
            elements = [el for el in elements if el.display_name == element_name]
            self.assertEqual(len(elements), 1)
            element = elements[0]
            return element

        return (_get_element_by_name(context1), _get_element_by_name(context2))

    def _generate_element_pair(self, name, **kwargs):
        cf = self._make_cardigan_front(**kwargs)
        cfr = CardiganVestRenderer(cf)
        pair = self._get_elements_by_name(cfr, name)
        return pair

    def test_armhole_element_before_neckline(self):

        # Armholes start before neckline

        (side1_element, side2_element) = self._generate_element_pair(
            "Armhole shaping", neckline_depth_orientation=SDC.ABOVE_ARMPIT
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([114]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([131]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([114]))
        self.assertEqual(subsection.end_rows, CompoundResult([131]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                13 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl 1, p2tog, work to end.
            </p><p>
            One stitch decreased.
              </p>
        """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([113]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([129]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection = subsections[0]
        self.assertEqual(subsection.start_rows, CompoundResult([113]))
        self.assertEqual(subsection.end_rows, CompoundResult([129]))
        text = subsection.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                12 rows from (and including)
                last increase row.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl to last 3 sts, p2tog-tbl, p 1.
            </p><p>
            One stitch decreased.
            </p>        
            """
        self.assertHTMLEqual(text, goal_text)

    def test_armhole_element_after_neckline(self):

        # Armholes start before neckline
        (side1_element, side2_element) = self._generate_element_pair(
            "Armhole shaping", neckline_depth_orientation=SDC.BELOW_ARMPIT
        )

        self.assertEqual(side1_element.start_rows(), CompoundResult([114]))
        self.assertEqual(side1_element.end_rows(), CompoundResult([131]))
        subsections = side1_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([114]))
        self.assertEqual(subsection1.end_rows, CompoundResult([131]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a RS row:
                113 rows from beginning,
                15 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (WS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Work to last 3 sts, k2tog, k 1.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl 1, p2tog, work to end.
            </p><p>
            One stitch decreased.
            </p>
              <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)

        self.assertEqual(side2_element.start_rows(), CompoundResult([113]))
        self.assertEqual(side2_element.end_rows(), CompoundResult([129]))
        subsections = side2_element.subsections
        self.assertEqual(len(subsections), 1)
        subsection1 = subsections[0]
        self.assertEqual(subsection1.start_rows, CompoundResult([113]))
        self.assertEqual(subsection1.end_rows, CompoundResult([129]))
        text = subsection1.render(False)
        goal_text = """
            <p>
              Continue as established until piece measures
              16&quot;/40.5 cm,
              ending with a WS row:
                112 rows from beginning,
                13 rows from neckline.
            </p>
            <p>
              <strong>
                Shape Armhole:
              </strong>
            </p>
            <p>
              <em>Next row (RS)</em>:
              BO 5 stitches, then work as established to end.
            </p>
            <p>
                Decrease one stitch at armhole edge of every row
                3 times, then every RS row
                7 times as follows:
            </p>
            <p>
            <em>
            Decrease row (RS):
            </em>Knit 1, ssk, work to end.
            </p><p>
            <em>
            Decrease row (WS):
            </em>Purl to last 3 sts, p2tog-tbl, p 1.
            </p><p>
            One stitch decreased.
              </p>
            <p>
              When all shaping is complete, 17
              shoulder stitches remain.
            </p>
        """
        self.assertHTMLEqual(text, goal_text)


class StitchesTests(TestCase):
    """
    Test that the stitches templates work. (Note: we're pulling this out
    into its own test class because we're going to re-factor and expand
    the stitches framework.)
    """

    def setUp(self):
        super(StitchesTests, self).setUp()

        # Elf is a CF staff member
        self.elf = StaffFactory()

        self.client = Client()
        self.client.force_login(self.elf)

    def tearDown(self):
        self.client.logout()
        # This will also delete objects FKed off of her in a cascade.
        self.elf.delete()
        super(StitchesTests, self).tearDown()

    def test_hem_stitches(self):
        waist_hem_stitches = Stitch.public_waist_hem_stitches.all()
        for hem_stitch in waist_hem_stitches:
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED, hip_edging_stitch=hem_stitch
            )
            self.do_create_pattern_get_patterntext(user, pspec)

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                hip_edging_stitch=hem_stitch,
                button_band_edging_stitch=StitchFactory(name="Daisy Stitch"),
                button_band_edging_height=1,
                button_band_allowance=1,
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_sleeve_hem_stitches(self):
        sleeve_hem_stitches = Stitch.public_sleeve_hem_stitches.all()
        for hem_stitch in sleeve_hem_stitches:
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED, sleeve_edging_stitch=hem_stitch
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_neck_trims(self):
        # Note: v-neck cardigans are covered by the vneck-cardi test
        neck_hem_stitches = Stitch.public_neckline_hem_stitches.all()
        for hem_stitch in neck_hem_stitches:
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_SLEEVED, neck_edging_stitch=hem_stitch
            )
            self.do_create_pattern_get_patterntext(user, pspec)

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=SDC.NECK_CREW,
                neck_edging_stitch=hem_stitch,
                button_band_edging_stitch=StitchFactory(name="Daisy Stitch"),
                button_band_edging_height=1,
                button_band_allowance=1,
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_armhole_trip_stitches(self):
        armhole_hem_stitches = Stitch.public_armhole_hem_stitches
        for armhole_stitch in armhole_hem_stitches.all():
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.PULLOVER_VEST,
                armhole_edging_stitch=armhole_stitch,
                armhole_edging_height=1,
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_buttonband_trims(self):
        # Note: v-neck cardigans are covered by the vneck-cardi
        buttonband_hem_stitches = Stitch.public_buttonband_hem_stitches.all()
        for hem_stitch in buttonband_hem_stitches:
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=SDC.NECK_CREW,
                button_band_edging_stitch=hem_stitch,
                button_band_edging_height=1,
                button_band_allowance=1,
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_vneck_cardi_neck(self):
        buttonband_hem_stitches = Stitch.public_buttonband_hem_stitches.all()
        for hem_stitch in buttonband_hem_stitches:
            user = UserFactory()

            pspec = SweaterPatternSpecFactory(
                garment_type=SDC.CARDIGAN_SLEEVED,
                neckline_style=SDC.NECK_VEE,
                button_band_edging_stitch=hem_stitch,
                button_band_edging_height=1,
                button_band_allowance=1,
            )
            self.do_create_pattern_get_patterntext(user, pspec)

    def test_stitch_markdown(self):
        """
        Test that the markdown fields of a Stitch model are being rendered
        properly
        """

        notes_text = """
### Heading

lorem ipsem

* Item 1
* Item 2
"""

        # I don't know why this test fails when you try to factor hem_stitch into
        # the call to SweaterPatternSpecFactory, but it does.
        hem_stitch = StitchFactory(notes=notes_text)
        pspec = SweaterPatternSpecFactory(
            garment_type=SDC.PULLOVER_SLEEVED, hip_edging_stitch=hem_stitch
        )
        p = ApprovedSweaterPatternFactory.from_pspec(pspec)

        pattern_url = p.get_absolute_url()
        response = self.client.get(pattern_url)
        self.assertEqual(response.status_code, 200)

        # Unfortunately, assertContains can only operate on a single HTML
        # element when html=True is being used. Thus, there is no way to
        # look for all of the entire notes_text at once and we need to
        # break it up.
        goal_html1 = "<h3>Heading</h3>"
        goal_html2 = "<p>lorem ipsem</p>"
        goal_html3 = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        self.assertContains(response, goal_html1, html=True)
        self.assertContains(response, goal_html2, html=True)
        self.assertContains(response, goal_html3, html=True)


class GradedPatterntextTests(TestCase):

    def do_create_pattern_get_patterntext(self, pspec):
        p = GradedSweaterPatternFactory.from_pspec(pspec)
        # Re-fetch the pattern from the DB to force all the type coercions
        p.refresh_from_db()

        renderer = GradedSweaterPatternRendererWebFull(p)

        # We used to take the opportunity to test for missing variables by
        # setting the 'string_if_invalid' option in TEMPLATES:
        #
        # TEST_TEMPLATES[0]['OPTIONS']['string_if_invalid'] = "(BAD VAR: %s)"
        # with self.settings(TEMPLATES = TEST_TEMPLATES):
        #   patterntext = ...
        #
        # but that setting is apparently shared across tests and started causing
        # other tests to fail. We tried for a while to figure out how capture the
        # missing vars while still returning '' (as is required elsewhere in the template
        # engine) including writing a specialized class, but couldn't find a good option.
        # So, we're going to accept the possibility of a missing variable until we
        # find a better option or switch to Jinja or something.

        for method_call in [
            renderer.render_instructions,
            renderer.render_postamble,
            renderer.render_pattern,
        ]:
            patterntext = method_call()

        return patterntext

    def test_render_sleeved_pullover(self):
        pspec = GradedSweaterPatternSpecFactory()
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_pullover_vest(self):
        pspec = GradedVestPatternSpecFactory()
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_cardigan_sleeved(self):
        pspec = GradedCardiganPatternSpecFactory()
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_cardigan_vest(self):
        pspec = GradedCardiganVestPatternSpecFactory()
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_vneck_cardigan(self):
        pspec = GradedCardiganVestPatternSpecFactory(neckline_style=SDC.NECK_VEE)
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_neck_below_armhole(self):
        pspec = GradedSweaterPatternSpecFactory(
            neckline_style=SDC.NECK_VEE,
            neckline_depth=2,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_neck_deep_below_shoulders(self):
        pspec = GradedSweaterPatternSpecFactory(
            neckline_style=SDC.NECK_VEE,
            neckline_depth=8,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)

    def test_render_neck_above_armhole(self):
        pspec = GradedSweaterPatternSpecFactory(
            neckline_style=SDC.NECK_VEE,
            neckline_depth=2,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
        )
        pspec.full_clean()
        self.do_create_pattern_get_patterntext(pspec)


class TestGradedPatterntextView(TestCase):

    def setUp(self):
        super(TestGradedPatterntextView, self).setUp()

        self.alice = StaffFactory()
        self.client.force_login(self.alice)

    def _make_pattern_from_pspec(self, pspec):
        return GradedSweaterPatternFactory.from_pspec(pspec)

    def _view_pattern(self, **kwargs):
        kwargs["user"] = self.alice
        pspec = GradedSweaterPatternSpecFactory(**kwargs)
        pspec.full_clean()
        pspec.save()
        p = self._make_pattern_from_pspec(pspec)
        url = p.get_absolute_url()
        response = self.client.get(url)
        return response

    def test_get(self):
        resp = self._view_pattern()
        self.assertEqual(resp.status_code, 200)
