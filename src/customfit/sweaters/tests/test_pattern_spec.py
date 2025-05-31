# -*- coding: utf-8 -*-


from django.core.exceptions import ValidationError
from django.test import TestCase

from customfit.designs.models import ExtraFinishingTemplate
from customfit.stitches.factories import (
    ButtonBandTemplateFactory,
    ButtonBandVeeneckTemplateFactory,
    SleeveHemTemplateFactory,
    StitchFactory,
    TrimArmholeTemplateFactory,
    TrimNecklineTemplateFactory,
    WaistHemTemplateFactory,
)
from customfit.stitches.models import RepeatsSpec
from customfit.swatches.factories import SwatchFactory

from ..factories import (
    GradedSweaterPatternSpecFactory,
    SweaterDesignFactory,
    SweaterPatternSpecFactory,
)
from ..helpers import sweater_design_choices as SDC


class BasePatternSpecTest(object):

    def test_hourglass(self):
        pspec = self.factory(silhouette=SDC.SILHOUETTE_HOURGLASS)
        self.assertTrue(pspec.is_hourglass)
        self.assertFalse(pspec.is_half_hourglass)
        self.assertFalse(pspec.is_straight)
        self.assertFalse(pspec.is_aline)
        self.assertFalse(pspec.is_tapered)
        self.assertEqual(pspec.silhouette_patterntext(), "Hourglass silhouette")

    def test_half_hourglass(self):
        pspec = self.factory(silhouette=SDC.SILHOUETTE_HALF_HOURGLASS)
        self.assertFalse(pspec.is_hourglass)
        self.assertTrue(pspec.is_half_hourglass)
        self.assertFalse(pspec.is_straight)
        self.assertFalse(pspec.is_aline)
        self.assertFalse(pspec.is_tapered)
        self.assertEqual(pspec.silhouette_patterntext(), "Half-hourglass silhouette")

    def test_aline(self):
        pspec = self.factory(silhouette=SDC.SILHOUETTE_ALINE)
        self.assertFalse(pspec.is_hourglass)
        self.assertFalse(pspec.is_half_hourglass)
        self.assertFalse(pspec.is_straight)
        self.assertTrue(pspec.is_aline)
        self.assertFalse(pspec.is_tapered)
        self.assertEqual(pspec.silhouette_patterntext(), "A-line silhouette")

    def test_straight(self):
        pspec = self.factory(silhouette=SDC.SILHOUETTE_STRAIGHT)
        self.assertFalse(pspec.is_hourglass)
        self.assertFalse(pspec.is_half_hourglass)
        self.assertTrue(pspec.is_straight)
        self.assertFalse(pspec.is_aline)
        self.assertFalse(pspec.is_tapered)
        self.assertEqual(pspec.silhouette_patterntext(), "Straight silhouette")

    def test_tapered(self):
        pspec = self.factory(silhouette=SDC.SILHOUETTE_TAPERED)
        self.assertFalse(pspec.is_hourglass)
        self.assertFalse(pspec.is_half_hourglass)
        self.assertFalse(pspec.is_straight)
        self.assertFalse(pspec.is_aline)
        self.assertTrue(pspec.is_tapered)
        self.assertEqual(pspec.silhouette_patterntext(), "Tapered silhouette")

    def test_sleeve_combinations_no_design_origin(self):
        # We used to have limits in place about what kinds of designs/etc. could have
        # short sleeves, but now we're taking them out. Make sure that we allow
        # all combinations of sleeve lengths/shapes.

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

                pspec = self.factory(**choices_dict)
                pspec.full_clean()
                self.assertEqual(pspec.sleeve_shape, sleeve_shape)
                self.assertEqual(pspec.sleeve_length, sleeve_length)

    def test_sleeve_combinations_design_origin(self):
        # We used to have limits in place about what kinds of designs/etc. could have
        # short sleeves, but now we're taking them out. Make sure that we allow
        # all combinations of sleeve lengths/shapes.

        for sleeve_shape in [SDC.SLEEVE_STRAIGHT, SDC.SLEEVE_TAPERED, SDC.SLEEVE_BELL]:
            for sleeve_length in [
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_SHORT,
            ]:

                for design_sleeve_shape in [
                    SDC.SLEEVE_STRAIGHT,
                    SDC.SLEEVE_TAPERED,
                    SDC.SLEEVE_BELL,
                ]:
                    for design_sleeve_length in [
                        SDC.SLEEVE_FULL,
                        SDC.SLEEVE_ELBOW,
                        SDC.SLEEVE_THREEQUARTER,
                        SDC.SLEEVE_SHORT,
                    ]:

                        design_choices_dict = {
                            "sleeve_length": design_sleeve_length,
                            "sleeve_shape": design_sleeve_shape,
                        }
                        if design_sleeve_shape == SDC.SLEEVE_BELL:
                            design_choices_dict["bell_type"] = SDC.BELL_MODERATE

                        design_origin = SweaterDesignFactory(**design_choices_dict)

                        choices_dict = {
                            "sleeve_length": sleeve_length,
                            "sleeve_shape": sleeve_shape,
                            "design_origin": design_origin,
                        }
                        if sleeve_shape == SDC.SLEEVE_BELL:
                            choices_dict["bell_type"] = SDC.BELL_MODERATE

                        pspec = self.factory(**choices_dict)
                        pspec.full_clean()
                        self.assertEqual(pspec.sleeve_shape, sleeve_shape)
                        self.assertEqual(pspec.sleeve_length, sleeve_length)

    def test_fit_patterntext(self):

        pspec = self.factory(garment_fit=SDC.FIT_HOURGLASS_AVERAGE)
        self.assertEqual(pspec.fit_patterntext(), "Hourglass average fit")

        pspec = self.factory(garment_fit=SDC.FIT_HOURGLASS_TIGHT)
        self.assertEqual(pspec.fit_patterntext(), "Hourglass close fit")

        pspec = self.factory(garment_fit=SDC.FIT_HOURGLASS_RELAXED)
        self.assertEqual(pspec.fit_patterntext(), "Hourglass relaxed fit")

        pspec = self.factory(garment_fit=SDC.FIT_HOURGLASS_OVERSIZED)
        self.assertEqual(pspec.fit_patterntext(), "Hourglass oversized fit")

        pspec = self.factory(garment_fit=SDC.FIT_WOMENS_AVERAGE)
        self.assertEqual(pspec.fit_patterntext(), "Women's average fit")

        pspec = self.factory(garment_fit=SDC.FIT_WOMENS_TIGHT)
        self.assertEqual(pspec.fit_patterntext(), "Women's close fit")

        pspec = self.factory(garment_fit=SDC.FIT_WOMENS_RELAXED)
        self.assertEqual(pspec.fit_patterntext(), "Women's relaxed fit")

        pspec = self.factory(garment_fit=SDC.FIT_WOMENS_OVERSIZED)
        self.assertEqual(pspec.fit_patterntext(), "Women's oversized fit")

        pspec = self.factory(garment_fit=SDC.FIT_MENS_AVERAGE)
        self.assertEqual(pspec.fit_patterntext(), "Men's average fit")

        pspec = self.factory(garment_fit=SDC.FIT_MENS_TIGHT)
        self.assertEqual(pspec.fit_patterntext(), "Men's close fit")

        pspec = self.factory(garment_fit=SDC.FIT_MENS_RELAXED)
        self.assertEqual(pspec.fit_patterntext(), "Men's relaxed fit")

        pspec = self.factory(garment_fit=SDC.FIT_MENS_OVERSIZED)
        self.assertEqual(pspec.fit_patterntext(), "Men's oversized fit")

        pspec = self.factory(garment_fit=SDC.FIT_CHILDS_AVERAGE)
        self.assertEqual(pspec.fit_patterntext(), "Children's average fit")

        pspec = self.factory(garment_fit=SDC.FIT_CHILDS_TIGHT)
        self.assertEqual(pspec.fit_patterntext(), "Children's close fit")

        pspec = self.factory(garment_fit=SDC.FIT_CHILDS_RELAXED)
        self.assertEqual(pspec.fit_patterntext(), "Children's relaxed fit")

        pspec = self.factory(garment_fit=SDC.FIT_CHILDS_OVERSIZED)
        self.assertEqual(pspec.fit_patterntext(), "Children's oversized fit")

    def test_drop_shoulder_armhole_patterntext(self):
        for depth, ptext_display in [
            (SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_SHALLOW, "shallow"),
            (SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE, "average"),
            (SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_DEEP, "deep"),
        ]:
            p = self.factory(
                construction=SDC.CONSTRUCTION_DROP_SHOULDER,
                drop_shoulder_additional_armhole_depth=depth,
            )
            self.assertEqual(
                p.drop_shoulder_armhole_length_patterntext(), ptext_display
            )

    def test_hem_templates_1(self):
        # Force default templates by having no other templates
        des = SweaterDesignFactory(
            waist_hem_template=None,
            sleeve_hem_template=None,
            trim_armhole_template=None,
            trim_neckline_template=None,
            button_band_template=None,
            button_band_veeneck_template=None,
        )
        waist_hem_stitch = StitchFactory()
        pspec = self.factory(
            design_origin=des,
            # Alas, can't get away with no hip-stitch
            hip_edging_stitch=waist_hem_stitch,
            hip_edging_height=1,
            sleeve_edging_stitch=None,
            sleeve_edging_height=1,
            neck_edging_stitch=None,
            neck_edging_height=1,
            armhole_edging_stitch=None,
            armhole_edging_height=1,
            button_band_edging_stitch=None,
            button_band_edging_height=1,
        )
        # DEBUG must be true for Templates to have an 'origin' attribute--
        # in Django 1.8 anyway. This may become unnecessary in later versions
        with self.settings(DEBUG=True):
            self.assertEqual(
                pspec.get_sleeve_hem_template().origin.template_name,
                "sweater_pattern_spec/sleeve_hem.html",
            )
            self.assertEqual(
                pspec.get_trim_armhole_template().origin.template_name,
                "sweater_pattern_spec/trim_armhole.html",
            )
            self.assertEqual(
                pspec.get_trim_neckline_template().origin.template_name,
                "sweater_pattern_spec/trim_neckline.html",
            )
            self.assertEqual(
                pspec.get_button_band_template().origin.template_name,
                "sweater_pattern_spec/button_band.html",
            )
            self.assertEqual(
                pspec.get_button_band_veeneck_template().origin.template_name,
                "sweater_pattern_spec/button_band_veeneck.html",
            )

    def test_hem_templates_2(self):
        # Force default templates by zero-height edging
        des = SweaterDesignFactory(
            waist_hem_template=None,
            sleeve_hem_template=None,
            trim_armhole_template=None,
            trim_neckline_template=None,
            button_band_template=None,
            button_band_veeneck_template=None,
        )

        stitch_waist_template = WaistHemTemplateFactory()
        stitch_sleeve_template = SleeveHemTemplateFactory()
        stitch_neck_template = TrimNecklineTemplateFactory()
        stitch_armhole_template = TrimArmholeTemplateFactory()
        stitch_buttonband_tempate = ButtonBandTemplateFactory()
        stitch_buttonband_veeneck_template = ButtonBandVeeneckTemplateFactory()
        pspec = self.factory(
            design_origin=des,
            hip_edging_stitch=StitchFactory(
                _waist_hem_stitch_template=stitch_waist_template
            ),
            hip_edging_height=0,
            sleeve_edging_stitch=StitchFactory(
                _sleeve_hem_template=stitch_sleeve_template
            ),
            sleeve_edging_height=0,
            neck_edging_stitch=StitchFactory(
                _trim_neckline_template=stitch_neck_template
            ),
            neck_edging_height=0,
            armhole_edging_stitch=StitchFactory(
                _trim_armhole_template=stitch_armhole_template
            ),
            armhole_edging_height=0,
            button_band_edging_stitch=StitchFactory(
                _button_band_template=stitch_buttonband_tempate,
                _button_band_veeneck_template=stitch_buttonband_veeneck_template,
            ),
            button_band_edging_height=0,
        )

        self.assertEqual(
            pspec.get_waist_hem_template().origin.template_name,
            "sweater_pattern_spec/waist_hem.html",
        )
        self.assertEqual(
            pspec.get_sleeve_hem_template().origin.template_name,
            "sweater_pattern_spec/sleeve_hem.html",
        )
        self.assertEqual(
            pspec.get_trim_armhole_template().origin.template_name,
            "sweater_pattern_spec/trim_armhole.html",
        )
        self.assertEqual(
            pspec.get_trim_neckline_template().origin.template_name,
            "sweater_pattern_spec/trim_neckline.html",
        )
        self.assertEqual(
            pspec.get_button_band_template().origin.template_name,
            "sweater_pattern_spec/button_band.html",
        )
        self.assertEqual(
            pspec.get_button_band_veeneck_template().origin.template_name,
            "sweater_pattern_spec/button_band_veeneck.html",
        )

    def test_hem_templates_3(self):
        # Force templates from stitch by no templates in design
        des = SweaterDesignFactory(
            waist_hem_template=None,
            sleeve_hem_template=None,
            trim_armhole_template=None,
            trim_neckline_template=None,
            button_band_template=None,
            button_band_veeneck_template=None,
        )

        stitch_waist_template = WaistHemTemplateFactory(name="stitch_waist_template")
        stitch_sleeve_template = SleeveHemTemplateFactory(name="stitch_sleeve_template")
        stitch_neck_template = TrimNecklineTemplateFactory(name="stitch_neck_template")
        stitch_armhole_template = TrimArmholeTemplateFactory(
            name="stitch_armhole_template"
        )
        stitch_buttonband_tempate = ButtonBandTemplateFactory(
            name="stitch_buttonband_tempate"
        )
        stitch_buttonband_veeneck_template = ButtonBandVeeneckTemplateFactory(
            content="stitch_buttonband_veeneck_template"
        )
        pspec = self.factory(
            design_origin=des,
            hip_edging_stitch=StitchFactory(
                _waist_hem_stitch_template=stitch_waist_template
            ),
            hip_edging_height=1,
            sleeve_edging_stitch=StitchFactory(
                _sleeve_hem_template=stitch_sleeve_template
            ),
            sleeve_edging_height=1,
            neck_edging_stitch=StitchFactory(
                _trim_neckline_template=stitch_neck_template
            ),
            neck_edging_height=1,
            armhole_edging_stitch=StitchFactory(
                _trim_armhole_template=stitch_armhole_template
            ),
            armhole_edging_height=1,
            button_band_edging_stitch=StitchFactory(
                _button_band_template=stitch_buttonband_tempate,
                _button_band_veeneck_template=stitch_buttonband_veeneck_template,
            ),
            button_band_edging_height=1,
        )

        # Cannot test direct equality of template as a DBTemplate instance is
        # not the same as a django Template
        self.assertEqual(
            pspec.get_waist_hem_template().name, stitch_waist_template.name
        )
        self.assertEqual(
            pspec.get_sleeve_hem_template().name, stitch_sleeve_template.name
        )
        self.assertEqual(
            pspec.get_trim_armhole_template().name, stitch_armhole_template.name
        )
        self.assertEqual(
            pspec.get_trim_neckline_template().name, stitch_neck_template.name
        )
        self.assertEqual(
            pspec.get_button_band_template().name, stitch_buttonband_tempate.name
        )
        self.assertEqual(
            pspec.get_button_band_veeneck_template().name,
            stitch_buttonband_veeneck_template.name,
        )

    def test_hem_templates_4(self):
        # ensure that templates come from the design when available

        design_waist_template = WaistHemTemplateFactory(name="design_waist_template")
        design_sleeve_template = SleeveHemTemplateFactory(name="design_sleeve_template")
        design_neck_template = TrimNecklineTemplateFactory(name="design_neck_template")
        design_armhole_template = TrimArmholeTemplateFactory(
            name="design_armhole_template"
        )
        design_buttonband_tempate = ButtonBandTemplateFactory(
            name="design_buttonband_tempate"
        )
        design_buttonband_veeneck_template = ButtonBandVeeneckTemplateFactory(
            content="designbuttonband_veeneck_template"
        )
        des = SweaterDesignFactory(
            waist_hem_template=design_waist_template,
            sleeve_hem_template=design_sleeve_template,
            trim_armhole_template=design_armhole_template,
            trim_neckline_template=design_neck_template,
            button_band_template=design_buttonband_tempate,
            button_band_veeneck_template=design_buttonband_veeneck_template,
        )

        stitch_waist_template = WaistHemTemplateFactory(name="stitch_waist_template")
        stitch_sleeve_template = SleeveHemTemplateFactory(name="stitch_sleeve_template")
        stitch_neck_template = TrimNecklineTemplateFactory(name="stitch_neck_template")
        stitch_armhole_template = TrimArmholeTemplateFactory(
            name="stitch_armhole_template"
        )
        stitch_buttonband_tempate = ButtonBandTemplateFactory(
            name="stitch_buttonband_tempate"
        )
        stitch_buttonband_veeneck_template = ButtonBandVeeneckTemplateFactory(
            content="stitch_buttonband_veeneck_template"
        )
        pspec = self.factory(
            design_origin=des,
            hip_edging_stitch=StitchFactory(
                _waist_hem_stitch_template=stitch_waist_template
            ),
            hip_edging_height=1,
            sleeve_edging_stitch=StitchFactory(
                _sleeve_hem_template=stitch_sleeve_template
            ),
            sleeve_edging_height=1,
            neck_edging_stitch=StitchFactory(
                _trim_neckline_template=stitch_neck_template
            ),
            neck_edging_height=1,
            armhole_edging_stitch=StitchFactory(
                _trim_armhole_template=stitch_armhole_template
            ),
            armhole_edging_height=1,
            button_band_edging_stitch=StitchFactory(
                _button_band_template=stitch_buttonband_tempate,
                _button_band_veeneck_template=stitch_buttonband_veeneck_template,
            ),
            button_band_edging_height=1,
        )

        # Cannot test direct equality of template as a DBTemplate instance is
        # not the same as a django Template
        self.assertEqual(
            pspec.get_waist_hem_template().name, design_waist_template.name
        )
        self.assertEqual(
            pspec.get_sleeve_hem_template().name, design_sleeve_template.name
        )
        self.assertEqual(
            pspec.get_trim_armhole_template().name, design_armhole_template.name
        )
        self.assertEqual(
            pspec.get_trim_neckline_template().name, design_neck_template.name
        )
        self.assertEqual(
            pspec.get_button_band_template().name, design_buttonband_tempate.name
        )
        self.assertEqual(
            pspec.get_button_band_veeneck_template().name,
            design_buttonband_veeneck_template.name,
        )

    def test_first_repeats(self):

        allover_stitch = StitchFactory(repeats_x_mod=1, repeats_mod_y=4)
        allover_repeats = RepeatsSpec(x_mod=1, mod_y=4)

        edge_stitch = StitchFactory(repeats_x_mod=0, repeats_mod_y=3)
        edge_repeats = RepeatsSpec(x_mod=0, mod_y=3)

        swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=4, additional_stitches=3
        )
        swatch_repeats = RepeatsSpec(x_mod=3, mod_y=4)

        plain_swatch = SwatchFactory(use_repeats=False)
        trivial_repeats = RepeatsSpec(x_mod=0, mod_y=1)

        pspec1 = self.factory(
            front_allover_stitch=allover_stitch,
            back_allover_stitch=allover_stitch,
            sleeve_allover_stitch=allover_stitch,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=swatch,
        )
        self.assertEqual(pspec1.front_repeats(), allover_repeats)
        self.assertEqual(pspec1.back_repeats(), allover_repeats)
        self.assertEqual(pspec1.sleeve_repeats(), allover_repeats)

        pspec2 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=swatch,
        )
        self.assertEqual(pspec2.front_repeats(), swatch_repeats)
        self.assertEqual(pspec2.back_repeats(), swatch_repeats)
        self.assertEqual(pspec2.sleeve_repeats(), swatch_repeats)

        pspec3 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=plain_swatch,
        )
        self.assertEqual(pspec3.front_repeats(), edge_repeats)
        self.assertEqual(pspec3.back_repeats(), edge_repeats)
        self.assertEqual(pspec3.sleeve_repeats(), edge_repeats)

        # Note: StitchFactory(name = "1x1 Ribbing") has no repeats
        pspec4 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            swatch=plain_swatch,
        )

        def assert_trivial_repeats(repeats):
            self.assertIn(repeats, [None, trivial_repeats])

        assert_trivial_repeats(pspec4.front_repeats())
        assert_trivial_repeats(pspec4.back_repeats())
        assert_trivial_repeats(pspec4.sleeve_repeats())

    def test_pass_through_to_design(self):
        extra_finishing_template = ExtraFinishingTemplate(name="foo")
        extra_finishing_template.save()
        des = SweaterDesignFactory(extra_finishing_template=extra_finishing_template)
        pspec = self.factory(design_origin=des)
        self.assertEqual(pspec.get_extra_finishing_template(), extra_finishing_template)

    def test_app_label(self):
        pspec = self.factory()
        pspec.full_clean()
        # Note that 'sweaters' is a magic string in the model-to-view framework we put in so that
        # top-level views can handle different constructions. See design_wizard/views/construction_registry
        self.assertEqual(pspec._meta.app_label, "sweaters")

    #
    # Error tests
    #

    def test_error_20(self):
        # Must use hourglass fits for hourglass silhouettes
        d = self.factory(
            garment_fit=SDC.FIT_WOMENS_AVERAGE, silhouette=SDC.SILHOUETTE_HOURGLASS
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_error_21(self):
        # Can't use hourglass fits for non-hourglass silhouettes
        d = self.factory(
            garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
            torso_length=SDC.MED_HIP_LENGTH,
            silhouette=SDC.SILHOUETTE_ALINE,
        )
        with self.assertRaises(ValidationError):
            d.full_clean()

    def test_clean(self):
        ps = self.factory(
            construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        with self.assertRaises(ValidationError):
            ps.clean()

        ps = self.factory(
            construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=None,
        )
        with self.assertRaises(ValidationError):
            ps.clean()


class PatternSpecTests(TestCase, BasePatternSpecTest):
    factory = SweaterPatternSpecFactory

    def test_first_repeats(self):

        allover_stitch = StitchFactory(repeats_x_mod=1, repeats_mod_y=4)
        allover_repeats = RepeatsSpec(x_mod=1, mod_y=4)

        edge_stitch = StitchFactory(repeats_x_mod=0, repeats_mod_y=3)
        edge_repeats = RepeatsSpec(x_mod=0, mod_y=3)

        swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=4, additional_stitches=3
        )
        swatch_repeats = RepeatsSpec(x_mod=3, mod_y=4)

        plain_swatch = SwatchFactory(use_repeats=False)
        trivial_repeats = RepeatsSpec(x_mod=0, mod_y=1)

        pspec1 = self.factory(
            front_allover_stitch=allover_stitch,
            back_allover_stitch=allover_stitch,
            sleeve_allover_stitch=allover_stitch,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=swatch,
        )
        self.assertEqual(pspec1.front_repeats(), allover_repeats)
        self.assertEqual(pspec1.back_repeats(), allover_repeats)
        self.assertEqual(pspec1.sleeve_repeats(), allover_repeats)

        pspec2 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=swatch,
        )
        self.assertEqual(pspec2.front_repeats(), swatch_repeats)
        self.assertEqual(pspec2.back_repeats(), swatch_repeats)
        self.assertEqual(pspec2.sleeve_repeats(), swatch_repeats)

        pspec3 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
            swatch=plain_swatch,
        )
        self.assertEqual(pspec3.front_repeats(), edge_repeats)
        self.assertEqual(pspec3.back_repeats(), edge_repeats)
        self.assertEqual(pspec3.sleeve_repeats(), edge_repeats)

        # Note: StitchFactory(name = "1x1 Ribbing") has no repeats
        pspec4 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            swatch=plain_swatch,
        )

        def assert_trivial_repeats(repeats):
            self.assertIn(repeats, [None, trivial_repeats])

        assert_trivial_repeats(pspec4.front_repeats())
        assert_trivial_repeats(pspec4.back_repeats())
        assert_trivial_repeats(pspec4.sleeve_repeats())


class GradedPatternSpecTests(TestCase, BasePatternSpecTest):
    factory = GradedSweaterPatternSpecFactory

    def test_first_repeats(self):

        allover_stitch = StitchFactory(repeats_x_mod=1, repeats_mod_y=4)
        allover_repeats = RepeatsSpec(x_mod=1, mod_y=4)

        edge_stitch = StitchFactory(repeats_x_mod=0, repeats_mod_y=3)
        edge_repeats = RepeatsSpec(x_mod=0, mod_y=3)

        plain_swatch = SwatchFactory(use_repeats=False)
        trivial_repeats = RepeatsSpec(x_mod=0, mod_y=1)

        pspec1 = self.factory(
            front_allover_stitch=allover_stitch,
            back_allover_stitch=allover_stitch,
            sleeve_allover_stitch=allover_stitch,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
        )
        self.assertEqual(pspec1.front_repeats(), allover_repeats)
        self.assertEqual(pspec1.back_repeats(), allover_repeats)
        self.assertEqual(pspec1.sleeve_repeats(), allover_repeats)

        pspec2 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=edge_stitch,
            sleeve_edging_stitch=edge_stitch,
        )
        self.assertEqual(pspec2.front_repeats(), edge_repeats)
        self.assertEqual(pspec2.back_repeats(), edge_repeats)
        self.assertEqual(pspec2.sleeve_repeats(), edge_repeats)

        # Note: StitchFactory(name = "1x1 Ribbing") has no repeats
        pspec3 = self.factory(
            front_allover_stitch=None,
            back_allover_stitch=None,
            sleeve_allover_stitch=None,
            hip_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )

        def assert_trivial_repeats(repeats):
            self.assertIn(repeats, [None, trivial_repeats])

        assert_trivial_repeats(pspec3.front_repeats())
        assert_trivial_repeats(pspec3.back_repeats())
        assert_trivial_repeats(pspec3.sleeve_repeats())
