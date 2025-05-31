# -*- coding: utf-8 -*-
import logging
from unittest import mock
from urllib.parse import urljoin

from django.contrib.messages import get_messages
from django.test import LiveServerTestCase, TestCase, tag
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from seleniumlogin import force_login

from customfit.bodies.factories import (
    BodyFactory,
    ChildBodyFactory,
    FemaleBodyFactory,
    GradeSetFactory,
    MaleBodyFactory,
    SimpleBodyFactory,
    UnstatedTypeBodyFactory,
)
from customfit.bodies.models import Body
from customfit.bodies.views import BODY_SESSION_NAME
from customfit.design_wizard.constants import REDO_AND_APPROVE, REDO_AND_TWEAK
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.garment_parameters.models import (
    IndividualGarmentParameters,
    MissingMeasurement,
)
from customfit.helpers.math_helpers import cm_to_inches
from customfit.pattern_spec.models import PatternSpec
from customfit.patterns.models import Redo
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.models import Swatch
from customfit.swatches.views import SWATCH_SESSION_NAME
from customfit.sweaters.models import SweaterPatternSpec
from customfit.userauth.factories import StaffFactory, UserFactory

from ...factories import (
    ApprovedSweaterPatternFactory,
    SweaterDesignFactory,
    SweaterPatternSpecFactory,
    SweaterRedoFactory,
    VestDesignFactory,
)
from ...helpers import sweater_design_choices as SDC

# Get an instance of a logger
logger = logging.getLogger(__name__)


class PersonalizeDesignViewTestsMixin(object):
    """
    Written as a mixin to keep py.test from running the tests in here directly,
    and not only in sub-classes. (Nose, how I miss you...)

    Expects sub-classes to implement:
    * setUp, which must in turn:
        * set self.user, self.body, self.full_body, self.simple_body, self.swatch
        * call _set_up_designs()
    * login()
    """

    def _set_up_designs(self):
        self.design = SweaterDesignFactory(name="Bar")
        self.design.save()
        self.personalize_url = reverse(
            "design_wizard:personalize", args=(self.design.slug,)
        )

        self.definitely_hourglass_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_straight_allowed=False,
            silhouette_tapered_allowed=False,
        )
        self.definitely_hourglass_design.save()
        self.hourglass_personalize_url = reverse(
            "design_wizard:personalize", args=(self.definitely_hourglass_design.slug,)
        )

    def _tear_down_designs(self):
        self.design.delete()

    def _get_design_page(self, design):
        url = reverse("design_wizard:personalize", args=(design.slug,))
        resp = self.client.get(url)
        return resp

    def test_neck_shown_properly(self):
        # Test that neck-edging is shown in 'design choices' only when
        # appropriate

        # Control group: with neck-edging
        self.login()
        self.with_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=4,
        )
        self.with_edging.full_clean()
        self.with_edging.save()
        with_edging_response = self._get_design_page(self.with_edging)
        expected_string = "<li>Neck edging and height: 1x1 Ribbing, 4&quot/10 cm</li>"

        self.assertContains(with_edging_response, expected_string, html=True)

        # Case: pullover, but no neck edging
        self.no_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neck_edging_stitch=None,
            neck_edging_height=0,
        )
        self.no_edging.full_clean()
        self.no_edging.save()
        no_edging_response = self._get_design_page(self.no_edging)
        self.assertNotIn("Neck edging and height: ", str(no_edging_response))

        # case: v-neck cardi
        self.veeneck_cardi = SweaterDesignFactory(
            garment_type=SDC.CARDIGAN_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            button_band_allowance=3,
            button_band_edging_height=3,
            number_of_buttons=0,
            button_band_edging_stitch=StitchFactory(name="1x1 Ribbing"),
        )
        self.veeneck_cardi.full_clean()
        self.veeneck_cardi.save()
        veeneck_cardi_response = self._get_design_page(self.veeneck_cardi)
        self.assertNotIn("Neck edging and height: ", str(veeneck_cardi_response))

    def test_neck_depth_kludge(self):
        # Control: neckline-depth more than 1 inch below shoulders

        self.login()
        self.control = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1.5,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=0.5,
        )
        self.control.full_clean()
        self.control.save()
        control_response = self._get_design_page(self.control)
        expected_string = "Neck depth"
        self.assertContains(control_response, expected_string, html=False)

        # Control: neckline-depth less than 1 inch below armpit
        self.control = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1.5,
            neckline_depth_orientation=SDC.BELOW_ARMPIT,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=0.5,
        )
        self.control.full_clean()
        self.control.save()
        control_response = self._get_design_page(self.control)
        expected_string = "Neck depth"
        self.assertContains(control_response, expected_string, html=False)

        # Control: neckline-depth less than 1 inch above armpit
        self.control = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=1.5,
            neckline_depth_orientation=SDC.ABOVE_ARMPIT,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=0.5,
        )
        self.control.full_clean()
        self.control.save()
        control_response = self._get_design_page(self.control)
        expected_string = "Neck depth"
        self.assertContains(control_response, expected_string, html=False)

        # Corner-case: don't show Featherweight's neckline depth
        # Neckline less than 1 inch below shoulders
        self.featherweight = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            neckline_style=SDC.NECK_VEE,
            neckline_depth=0.5,
            neckline_depth_orientation=SDC.BELOW_SHOULDERS,
            neck_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            neck_edging_height=0.5,
        )
        self.featherweight.full_clean()
        self.featherweight.save()

        featherweight_response = self._get_design_page(self.featherweight)
        expected_string = "Neck depth"
        self.assertNotContains(featherweight_response, expected_string, html=False)

    def test_sleeve_shown_properly(self):
        # Test that sleeve-edging is shown in 'design choices' only when
        # appropriate

        self.login()
        # Control group: with sleeve-edging
        self.with_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            sleeve_edging_height=4,
        )
        self.with_edging.full_clean()
        self.with_edging.save()
        with_edging_response = self._get_design_page(self.with_edging)
        expected_string = "<li>Sleeve edging and height: 1x1 Ribbing, 4&quot/10 cm</li>"

        self.assertContains(with_edging_response, expected_string, html=True)

        # Case: sleeved, but no sleeve edging
        self.no_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_SLEEVED,
            sleeve_edging_stitch=None,
            sleeve_edging_height=0,
        )
        self.no_edging.full_clean()
        self.no_edging.save()
        no_edging_response = self._get_design_page(self.no_edging)
        self.assertNotIn("Sleeve edging and height: ", str(no_edging_response))

        # case: vest
        self.vest = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        self.vest.full_clean()
        self.vest.save()
        vest_response = self._get_design_page(self.vest)
        self.assertNotIn("Sleeve edging and height: ", str(vest_response))

    def test_armhole_shown_properly(self):
        # Test that armhole-edging is shown in 'design choices' only when
        # appropriate

        self.login()
        # Control group: vest with edging
        self.with_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=StitchFactory(name="1x1 Ribbing"),
            armhole_edging_height=1,
        )
        self.with_edging.full_clean()
        self.with_edging.save()
        with_edging_response = self._get_design_page(self.with_edging)
        expected_string = (
            "<li>Armhole edging and height: 1x1 Ribbing, 1&quot/2.5 cm</li>"
        )
        self.assertContains(with_edging_response, expected_string, html=True)

        # Case: vest, but no armhole edging
        self.no_edging = SweaterDesignFactory(
            garment_type=SDC.PULLOVER_VEST,
            armhole_edging_stitch=None,
            armhole_edging_height=0,
        )
        self.no_edging.full_clean()
        self.no_edging.save()
        no_edging_response = self._get_design_page(self.no_edging)
        self.assertNotIn("Armhole edging and height: ", str(no_edging_response))

        # case: Sleeved
        self.sleeved = SweaterDesignFactory(garment_type=SDC.PULLOVER_SLEEVED)
        self.sleeved.full_clean()
        self.sleeved.save()
        sleeved_response = self._get_design_page(self.sleeved)
        self.assertNotIn("Armhole edging and height: ", str(sleeved_response))

    def test_no_relevant_swatches(self):
        """
        Checks that the appropriate warning is thrown when the user has a
        swatch, but it's not suitable for the desired design.
        """
        self.login()

        repeats_stitch = StitchFactory(
            user_visible=True, repeats_x_mod=1, repeats_mod_y=4, is_allover_stitch=True
        )

        design = SweaterDesignFactory(
            back_allover_stitch=repeats_stitch,
            front_allover_stitch=repeats_stitch,
            sleeve_allover_stitch=repeats_stitch,
            name="Irrelevant design",
        )

        # This guarantees that the user has a swatch (so we should not be in the
        # test_no_swatches case), but the swatch is not compatible with the
        # design.
        Swatch.objects.filter(user=self.user).all().delete()
        _ = SwatchFactory(
            user=self.user, use_repeats=True, stitches_per_repeat=5
        )  # not equal to 4

        url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self._get_design_page(design)
        list_url = reverse("swatches:swatch_list_view")
        create_url = reverse("swatches:swatch_create_view")
        goal_html = """
        <div id="hint_id_swatch" class="help-block">
        None of your gauges' repeats match the stitch-pattern used in this design.
        Please <a href="{create_url}?next={next_url}">add a gauge</a> for this stitch pattern to make this
        design.</div>""".format(
            create_url=create_url, next_url=url
        )
        self.assertContains(response, goal_html, html=True)

    def test_no_bodies(self):
        self.login()
        Body.objects.filter(user=self.user).all().delete()
        response = self._get_design_page(self.design)
        goal_url = reverse("bodies:body_create_view")
        goal_html = (
            'You need to <a href="%s">add at least '
            "one measurement set</a> before you can make a sweater" % goal_url
        )
        self.assertContains(response, goal_html)

    #

    def test_css_selector_assumption(self):
        """
        The JavaScript makes some assumptions about the values in
        design_choices, for the sake of simplicity. Let's ensure those
        assumptions hold.
        """

        assert all([x.startswith("FIT_WOMENS") for x in SDC.FIT_WOMENS])
        assert all([x.startswith("FIT_MENS") for x in SDC.FIT_MENS])
        assert all([x.startswith("FIT_CHILDS") for x in SDC.FIT_CHILDS])

    def test_body_compatiblity(self):
        self.login()

        # If the design is a straight design, then the user should see all bodies
        straight_des = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_straight_allowed=True,
            silhouette_hourglass_allowed=False,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
            name="I am a straight design",
        )
        straight_des.save()
        response = self._get_design_page(straight_des)
        self.assertContains(response, self.body.name)
        self.assertContains(response, self.straight_body.name)
        self.assertContains(response, self.full_body.name)
        straight_des.delete()

        # If the design is am hourglass design, then the user should still see all bodies
        # (this wasn't always the case)
        hourglass_des = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_straight_allowed=False,
            silhouette_hourglass_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
            name="I am an hourglass design",
        )
        hourglass_des.save()

        response = self._get_design_page(hourglass_des)
        # We don't know about self.body, so don't test ig
        self.assertContains(response, self.straight_body.name)
        self.assertContains(response, self.full_body.name)
        hourglass_des.delete()

    def test_swatch_compatiblity(self):
        self.login()

        # Sanity check: the swatch is compatible with the design, and is shown
        self.assertTrue(self.design.compatible_swatch(self.swatch))
        response = self.client.get(
            reverse("design_wizard:personalize", args=(self.design.slug,))
        )
        self.assertContains(response, self.swatch.name)

        # Now change the design and swatch to be incompatible
        self.swatch.use_repeats = True
        self.swatch.stitches_per_repeat = 7
        self.swatch.additional_stitches = 3
        self.swatch.save()

        new_stitch = StitchFactory(repeats_x_mod=2, repeats_mod_y=5)
        new_stitch.save()
        self.design.back_allover_stitch = new_stitch
        self.design.save()

        self.assertFalse(self.design.compatible_swatch(self.swatch))  # sanity checl
        response = self.client.get(
            reverse("design_wizard:personalize", args=(self.design.slug,))
        )
        self.assertNotContains(response, self.swatch.name)

    def test_cable_stitches_listed(self):
        # Test that we see the cable-stitches. Test added when we added cables
        cabled_design = SweaterDesignFactory(
            back_cable_stitch=StitchFactory(name="Back cable stitch"),
            front_cable_stitch=StitchFactory(name="Front cable stitch"),
            sleeve_cable_stitch=StitchFactory(name="Sleeve cable stitch"),
            back_cable_extra_stitches=0,
            front_cable_extra_stitches=0,
            sleeve_cable_extra_stitches=0,
        )
        cabled_design.save()
        self.login()

        response = self._get_design_page(cabled_design)
        self.assertContains(response, "Back cable stitch")
        self.assertContains(response, "Front cable stitch")
        self.assertContains(response, "Sleeve cable stitch")
        cabled_design.delete()

    def test_sleeve_combinations(self):
        # We used to only be able to support short sleeves when the design was already short-sleeved
        # and we used to only be able to have straight short-sleeves on designs.
        # We've removed them, so let's test every combination is possible

        self.login()

        for sleeve_shape in [SDC.SLEEVE_STRAIGHT, SDC.SLEEVE_TAPERED, SDC.SLEEVE_BELL]:
            for sleeve_length in [
                SDC.SLEEVE_FULL,
                SDC.SLEEVE_ELBOW,
                SDC.SLEEVE_THREEQUARTER,
                SDC.SLEEVE_SHORT,
            ]:

                design = SweaterDesignFactory(
                    sleeve_length=sleeve_length,
                    sleeve_shape=sleeve_shape,
                    bell_type=SDC.BELL_MODERATE,
                    name="Long sleeve design-o",
                )
                response = self._get_design_page(design)
                goal_html = """
                <select class="select form-control" id="id_sleeve_length" name="sleeve_length"
                        aria-describedby="id_sleeve_length_helptext">
                    <option value="SLEEVE_SHORT">Short sleeve</option>
                    <option value="SLEEVE_ELBOW">Elbow-length sleeve</option>
                    <option value="SLEEVE_THREEQUARTER">Three-quarter length sleeve</option>
                    <option value="SLEEVE_FULL" selected="selected">Full-length sleeve</option>
                </select>"""
                self.assertContains(response, goal_html, html=True)

                url = reverse("design_wizard:personalize", args=(design.slug,))
                for sleeve_length_chosen in [
                    SDC.SLEEVE_FULL,
                    SDC.SLEEVE_ELBOW,
                    SDC.SLEEVE_THREEQUARTER,
                    SDC.SLEEVE_SHORT,
                ]:
                    url = reverse("design_wizard:personalize", args=(design.slug,))
                    response2 = self.client.post(
                        url,
                        {
                            "name": "name",
                            "body": self.body.id,
                            "swatch": self.swatch.id,
                            "torso_length": SDC.MED_HIP_LENGTH,
                            "silhouette": SDC.SILHOUETTE_HOURGLASS,
                            "sleeve_length": sleeve_length_chosen,
                            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
                        },
                    )

                    self.assertEqual(response2.status_code, 302)
                    self.assertRegex(response2["Location"], r"^/design/summary/\d+/$")

    def test_drop_shoulder_armhole_values_shown(self):
        self.login()
        response = self.client.get(self.personalize_url)
        goal_html = """
            <select name="drop_shoulder_additional_armhole_depth" 
              class="select form-control" 
              aria-describedby="id_drop_shoulder_additional_armhole_depth_helptext" 
              id="id_drop_shoulder_additional_armhole_depth"> 
            <option value="" selected>---------</option> 
            <option value="shallowdepth">shallow (¾&quot;/2 cm)</option> 
            <option value="averagedepth">average (1½&quot;/4 cm)</option> 
            <option value="deepdepth">deep (2½&quot;/6.5 cm)</option>
            </select>
        """
        self.assertContains(response, goal_html, html=True)

    def test_create_body_url(self):
        self.login()
        response = self.client.get(self.personalize_url)
        goal_html = (
            '<a href="/measurement/new/?next=%s">(or create a new one)</a>'
            % self.personalize_url
        )
        self.assertContains(response, goal_html)

    def test_create_swatch_url(self):
        self.login()
        response = self.client.get(self.personalize_url)
        goal_html = (
            '<a href="/swatch/new/?next=%s">(or create a new one)</a>'
            % self.personalize_url
        )
        self.assertContains(response, goal_html)

    def test_initial_body_from_session(self):
        self.login()

        # sanity check
        response = self.client.get(self.personalize_url)
        form_initial = response.context["form"].initial
        self.assertIsNone(form_initial["body"])

        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.personalize_url)

        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["body"], self.body)
        goal_html = '<option value="%d" selected="selected">%s</option>' % (
            self.body.id,
            self.body.name,
        )
        self.assertContains(response, goal_html, html=True)

    def test_initial_swatch_from_session(self):
        self.login()

        # sanity check
        response = self.client.get(self.personalize_url)
        form_initial = response.context["form"].initial
        self.assertIsNone(form_initial["swatch"])

        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        response = self.client.get(self.personalize_url)

        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["swatch"], self.swatch)
        goal_html = '<option value="%d" selected="selected">%s</option>' % (
            self.swatch.id,
            self.swatch.name,
        )
        self.assertContains(response, goal_html, html=True)

    def test_initial_values_from_design(self):
        self.login()

        # Test that we can set silhouette through query parameter
        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            primary_construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            drop_shoulder_additional_armhole_depth=None,
        )
        design_url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self.client.get(design_url)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["silhouette"], SDC.SILHOUETTE_HOURGLASS)
        self.assertEqual(form_initial["construction"], SDC.CONSTRUCTION_SET_IN_SLEEVE)
        self.assertIsNone(form_initial["drop_shoulder_additional_armhole_depth"])

        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_ALINE,
            silhouette_aline_allowed=True,
            primary_construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        design_url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self.client.get(design_url)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["silhouette"], SDC.SILHOUETTE_ALINE)
        self.assertEqual(form_initial["construction"], SDC.CONSTRUCTION_DROP_SHOULDER)
        self.assertEqual(
            form_initial["drop_shoulder_additional_armhole_depth"],
            SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )

    def test_form_clears_body_from_session(self):
        self.login()

        # user uses body from session
        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.personalize_url)

        response2 = self.client.post(
            self.personalize_url,
            {
                "name": "name",
                "body": self.body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            },
        )

        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

        # user uses body not in session
        body2 = BodyFactory(user=self.user)
        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.personalize_url)

        response2 = self.client.post(
            self.personalize_url,
            {
                "name": "name",
                "body": body2.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            },
        )

        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

    def test_non_hourglass_body_with_hourglass_silhouette(self):
        self.login()

        for silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:
            design = SweaterDesignFactory(
                primary_silhouette=silhouette,
                silhouette_straight_allowed=True,
                silhouette_half_hourglass_allowed=True,
                silhouette_hourglass_allowed=True,
            )
            url = reverse("design_wizard:personalize", args=(design.slug,))
            post_dict = {
                "name": "name",
                "body": self.straight_body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "silhouette": silhouette,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            }
            resp = self.client.post(url, post_dict, follow=False)
            patternspec = SweaterPatternSpec.objects.filter(
                body=self.straight_body
            ).get()
            goal_url = reverse(
                "design_wizard:missing",
                kwargs={"pk": patternspec.pk, "action": "summary"},
            )
            self.assertRedirects(resp, goal_url, fetch_redirect_response=False)
            patternspec.delete()

    def test_non_hourglass_fit_with_hourglass_silhouette(self):
        self.login()

        for silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:

            design = SweaterDesignFactory(
                primary_silhouette=silhouette,
                silhouette_straight_allowed=True,
                silhouette_half_hourglass_allowed=True,
                silhouette_hourglass_allowed=True,
            )
            url = reverse("design_wizard:personalize", args=(design.slug,))
            post_dict = {
                "name": "name",
                "body": self.body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "silhouette": silhouette,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_WOMENS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            }
            resp = self.client.post(url, post_dict)
            form = resp.context["form"]
            self.assertFormError(
                form,
                None,
                "Must use hourglass fit with hourglass/half-hourglass silhouette",
            )

    def test_hourglass_fit_with_non_hourglass_silhouette(self):
        self.login()

        for silhouette in [
            SDC.SILHOUETTE_ALINE,
            SDC.SILHOUETTE_STRAIGHT,
            SDC.SILHOUETTE_TAPERED,
        ]:
            design = SweaterDesignFactory(
                primary_silhouette=silhouette,
                silhouette_half_hourglass_allowed=True,
                silhouette_straight_allowed=True,
                silhouette_hourglass_allowed=True,
            )
            url = reverse("design_wizard:personalize", args=(design.slug,))
            post_dict = {
                "name": "name",
                "body": self.body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "silhouette": silhouette,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            }
            resp = self.client.post(url, post_dict)
            form = resp.context["form"]
            self.assertFormError(
                form,
                None,
                "Cannot use hourglass fit with non-hourglass/half-hourglass silhouette",
            )

    def test_missing_entries_drop_shoulder(self):
        self.login()
        design = SweaterDesignFactory(construction_drop_shoulder_allowed=True)
        post_dict = {
            "name": "name",
            "body": self.body.id,
            "swatch": self.swatch.id,
            "torso_length": SDC.MED_HIP_LENGTH,
            "silhouette": SDC.SILHOUETTE_HOURGLASS,
            "sleeve_length": SDC.SLEEVE_FULL,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "construction": SDC.CONSTRUCTION_DROP_SHOULDER,
            "drop_shoulder_additional_armhole_depth": "",
        }
        url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self.client.post(url, post_dict, follow=False)
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "Drop-shoulder sweaters need a valid drop-shoulder armhole depth",
        )

    def test_drop_shoulder_is_ignored(self):
        from ...models import SweaterIndividualGarmentParameters

        self.login()
        design = SweaterDesignFactory(construction_drop_shoulder_allowed=True)
        post_dict = {
            "name": "name",
            "body": self.body.id,
            "swatch": self.swatch.id,
            "torso_length": SDC.MED_HIP_LENGTH,
            "silhouette": SDC.SILHOUETTE_HOURGLASS,
            "sleeve_length": SDC.SLEEVE_FULL,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "drop_shoulder_additional_armhole_depth": SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        }

        url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self.client.post(url, post_dict, follow=False)
        self.assertEqual(response.status_code, 302)
        igp_id_str = response["Location"].split("/")[-2]
        igp_id = int(igp_id_str)
        igp = SweaterIndividualGarmentParameters.objects.get(id=igp_id)
        pspec = igp.get_spec_source()

        self.assertEqual(pspec.construction, SDC.CONSTRUCTION_SET_IN_SLEEVE)
        self.assertIsNone(pspec.drop_shoulder_additional_armhole_depth)

    def test_personalize_no_redirect_measurements_available_vest(self):
        """
        Ensure that the user does not go to missing-measurements for a vest
        when they have the hem measurement
        """
        self.login()

        # sanity check
        self.assertFalse(PatternSpec.objects.filter(user=self.user).exists())

        straight_vest_design = VestDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_hourglass_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        straight_vest_url = reverse(
            "design_wizard:personalize",
            kwargs={"design_slug": straight_vest_design.slug},
        )

        data = {
            "name": "foo",
            "body": self.straight_body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_WOMENS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_STRAIGHT,
            "torso_length": SDC.MED_HIP_LENGTH,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            # Since there are multiple submit buttons, we must specify the one
            # we want in the POST data.
            "redirect_approve": "Get this pattern!",
        }

        resp = self.client.post(straight_vest_url, data, follow=True)

        # # We can't reverse the summary & approve URL because we don't know the ID
        # # of the generated pattern objects.
        # resp_path = urlparse(self._get_final_url(resp)).path
        # self.assertTrue(resp_path.startswith('/design/summary'))

        pspec = PatternSpec.objects.get(user=self.user)
        igp = IndividualGarmentParameters.objects.get(pattern_spec=pspec)
        goal_url = reverse("design_wizard:summary", args=(igp.id,))
        self.assertRedirects(resp, goal_url)

    def test_personalize_redirect_missing_measurements_vest(self):
        """
        Ensure that the user goest to missing-measurements for a vest
        when they lack the hem measurement
        """
        self.login()

        # sanity check
        self.assertFalse(PatternSpec.objects.filter(user=self.user).exists())

        straight_vest_design = VestDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_hourglass_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        straight_vest_url = reverse(
            "design_wizard:personalize",
            kwargs={"design_slug": straight_vest_design.slug},
        )

        data = {
            "name": "foo",
            "body": self.straight_body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_WOMENS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_STRAIGHT,
            "torso_length": SDC.LOW_HIP_LENGTH,  # missing measurement
            "redirect_approve": "Get this pattern!",
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
        }

        resp = self.client.post(straight_vest_url, data, follow=True)
        # resp_path = urlparse(self._get_final_url(resp)).path
        # self.assertTrue(resp_path.startswith('/design/missing'))

        pspec = PatternSpec.objects.get(user=self.user)
        self.assertFalse(
            IndividualGarmentParameters.objects.filter(pattern_spec=pspec).exists()
        )
        goal_url = reverse(
            "design_wizard:missing", kwargs={"pk": pspec.pk, "action": "summary"}
        )
        self.assertRedirects(resp, goal_url)

    def test_silhouette_descriptions(self):
        self.login()

        test_vectors = [
            # components:
            # primary silhouette, aline allowed, hourglass allowed, straight allowed, tapered allowed, expected output
            (
                SDC.SILHOUETTE_ALINE,
                True,
                False,
                False,
                False,
                "Pictured in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                False,
                False,
                True,
                "Pictured in a-line silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                False,
                True,
                False,
                "Pictured in a-line silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                False,
                True,
                True,
                "Pictured in a-line silhouette. Also available in straight and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                False,
                "Pictured in a-line silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                False,
                True,
                "Pictured in a-line silhouette. Also available in hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                False,
                "Pictured in a-line silhouette. Also available in hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_ALINE,
                True,
                True,
                True,
                True,
                "Pictured in a-line silhouette. Also available in hourglass, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                False,
                False,
                "Pictured in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                False,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in straight and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                False,
                False,
                "Pictured in hourglass silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                False,
                True,
                "Pictured in hourglass silhouette. Also available in a-line and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                False,
                "Pictured in hourglass silhouette. Also available in a-line and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_HOURGLASS,
                True,
                True,
                True,
                True,
                "Pictured in hourglass silhouette. Also available in a-line, straight, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
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
                True,
                True,
                "Pictured in straight silhouette. Also available in tapered silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                False,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in hourglass and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                False,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                True,
                False,
                "Pictured in straight silhouette. Also available in a-line and hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_STRAIGHT,
                True,
                True,
                True,
                True,
                "Pictured in straight silhouette. Also available in a-line, hourglass, and tapered silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
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
                True,
                True,
                "Pictured in tapered silhouette. Also available in straight silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in hourglass silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                False,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in hourglass and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line silhouette.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                False,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line and straight silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                False,
                True,
                "Pictured in tapered silhouette. Also available in a-line and hourglass silhouettes.",
            ),
            (
                SDC.SILHOUETTE_TAPERED,
                True,
                True,
                True,
                True,
                "Pictured in tapered silhouette. Also available in a-line, hourglass, and straight silhouettes.",
            ),
        ]

        for (
            primary,
            aline,
            hourglass,
            straight,
            tapered,
            expected_english,
        ) in test_vectors:
            design = SweaterDesignFactory(
                primary_silhouette=primary,
                silhouette_aline_allowed=aline,
                silhouette_hourglass_allowed=hourglass,
                silhouette_straight_allowed=straight,
                silhouette_tapered_allowed=tapered,
            )
            url = reverse("design_wizard:personalize", args=(design.slug,))
            response = self.client.get(url)
            expected_description = (
                """
            <p><em>%s</em></p>
            """
                % expected_english
            )
            self.assertContains(response, expected_description, html=True)

    def test_missing_measurements_exception(self):
        # When we do raise a MissingMeasurements exception, it is handled properly?

        self.login()

        design = SweaterDesignFactory()
        design_url = reverse(
            "design_wizard:personalize", kwargs={"design_slug": design.slug}
        )

        data = {
            "name": "foo",
            "body": self.full_body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_WOMENS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_STRAIGHT,
            "torso_length": SDC.MED_HIP_LENGTH,
            "sleeve_length": SDC.SLEEVE_FULL,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "redirect_approve": "Get this pattern!",
        }

        with mock.patch(
            "customfit.sweaters.views.add_missing_measurements_views.SweaterIndividualGarmentParameters.make_from_patternspec",
            **{"side_effect": MissingMeasurement("waist_circ")}
        ):
            # Test: does the MissingMeasurements exception propogate all the way up?
            with self.assertRaises(MissingMeasurement):
                resp = self.client.post(design_url, data, follow=True)

    def test_bug_incompatible_design_inputs(self):
        # We used to only be able to support short sleeves when the design was already short-sleeved
        # and we used to only be able to have straight short-sleeves on designs.
        # We've removed them, so let's test every combination is possible

        self.login()

        design = SweaterDesignFactory(hip_edging_height=20)
        url = reverse("design_wizard:personalize", args=(design.slug,))
        response = self.client.post(
            url,
            {
                "name": "name",
                "body": self.body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "silhouette": SDC.SILHOUETTE_HOURGLASS,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
                "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            },
        )

        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(
            str(messages[0]).startswith(
                "Sorry, but the hip edging is extending past the waist."
            )
        )


class PersonalizeDesignViewTestIndividual(TestCase, PersonalizeDesignViewTestsMixin):
    def setUp(self):
        super(PersonalizeDesignViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)
        self.straight_body = SimpleBodyFactory(user=self.user)
        self.full_body = BodyFactory(user=self.user)
        self._set_up_designs()
        self.user2 = UserFactory()
        self.post_entries = {
            "name": "name",
            "body": self.body.id,
            "swatch": self.swatch.id,
            "torso_length": SDC.MED_HIP_LENGTH,
            "sleeve_length": SDC.SLEEVE_FULL,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
        }

    def tearDown(self):
        self._tear_down_designs()
        super(PersonalizeDesignViewTestIndividual, self).tearDown()
        self.user2.delete()

    def login(self):
        return self.client.force_login(self.user)

    def test_body_options(self):
        """
        Make sure that the dict which tells the front-end JS about body
        measurement availability conveys the right information.
        """

        # Indivdiual-user vesion: no BodyLinkages
        self.login()

        body1 = BodyFactory(user=self.user, cross_chest_distance=12)
        body2 = SimpleBodyFactory(user=self.user)
        body3 = BodyFactory(user=self.user, cross_chest_distance=None)
        body4 = BodyFactory(
            user=self.user, armpit_to_short_sleeve=None, armpit_to_elbow_sleeve=None
        )

        body_woman = FemaleBodyFactory(user=self.user)
        body_man = MaleBodyFactory(user=self.user)
        body_child = ChildBodyFactory(user=self.user)
        body_unstated = UnstatedTypeBodyFactory(user=self.user)

        straight_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_straight_allowed=True,
            silhouette_hourglass_allowed=False,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        straight_design.save()

        response = self._get_design_page(straight_design)

        body_options = response.context["body_options"]

        # Body types are represented correctly
        self.assertEqual(body_options[body_woman.pk]["type"], "woman")
        self.assertEqual(body_options[body_man.pk]["type"], "man")
        self.assertEqual(body_options[body_child.pk]["type"], "child")
        self.assertEqual(body_options[body_unstated.pk]["type"], "unstated")

    def test_all_bodies_shown(self):
        # Personalize page should show all bodies no matter what silhouette is in the design. (This wasn't always
        # the case)

        hourglass_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            silhouette_straight_allowed=False,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        straight_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_hourglass_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )

        hourglass_url = reverse(
            "design_wizard:personalize", kwargs={"design_slug": hourglass_design.slug}
        )
        straight_url = reverse(
            "design_wizard:personalize", kwargs={"design_slug": straight_design.slug}
        )

        self.login()

        resp = self.client.get(hourglass_url)
        self.assertEqual(
            set(resp.context["form"].fields["body"].queryset),
            set([self.body, self.straight_body, self.full_body]),
        )

        resp = self.client.get(straight_url)
        self.assertEqual(
            set(resp.context["form"].fields["body"].queryset),
            set([self.body, self.straight_body, self.full_body]),
        )

    def test_body_belongs_to_wrong_user(self):
        new_body = BodyFactory(user=self.user2)
        new_body.save()

        # new_body should not be provided as an option
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertContains(response, self.body.name)  # sanity check
        self.assertNotContains(response, new_body.name)

        # new_body should not be allowed in a POST
        self.post_entries["body"] = new_body.id
        response = self.client.post(
            self.personalize_url, self.post_entries, follow=False
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "body",
            ["Select a valid choice. That choice is not one of the available choices."],
        )

    def test_swatch_belongs_to_wrong_user(self):
        new_swatch = SwatchFactory(user=self.user2, name="new swatch")
        new_swatch.save()

        # new_swatch should not be provided as an option
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertContains(response, self.swatch.name)  # sanity check
        self.assertNotContains(response, new_swatch.name)

        # new_swatch should not be accepted in a POST
        self.post_entries["swatch"] = new_swatch.id
        response = self.client.post(
            self.personalize_url, self.post_entries, follow=False
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "swatch",
            ["Select a valid choice. That choice is not one of the available choices."],
        )

    def test_no_bodies(self):
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "before you can proceed")

        for body in Body.objects.filter(user=self.user):
            body.delete()
        response = self.client.get(self.personalize_url)
        self.assertContains(
            response,
            '<div id="hint_id_body" class="help-block">You need to <a href="/measurement/new/?next=%s">add at least one measurement set</a> before you can proceed.</div>'
            % self.personalize_url,
            html=True,
        )


@tag("selenium")
class PersonalizeViewFrontendTest(LiveServerTestCase):
    """
    Test the elements of the garment tweaking workflow that rely on JS.
    """

    maxDiff = None

    def setUp(self):
        super(PersonalizeViewFrontendTest, self).setUp()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)
        self.driver.implicitly_wait(2)
        # self.wait = WebDriverWait(self.driver, 5)

        self.user = UserFactory()

        self.male_body = MaleBodyFactory(user=self.user)
        self.female_body = FemaleBodyFactory(user=self.user)
        self.child_body = ChildBodyFactory(user=self.user)
        self.unstated_body = UnstatedTypeBodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)
        self.design = SweaterDesignFactory(
            silhouette_hourglass_allowed=True,
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=True,
            silhouette_half_hourglass_allowed=True,
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
        )

        # Log in
        force_login(self.user, self.driver, self.live_server_url)

        # Go to tweak page
        self._get(reverse("design_wizard:personalize", args=(self.design.slug,)))

    def tearDown(self):
        self.design.delete()
        self.male_body.delete()
        self.female_body.delete()
        self.child_body.delete()
        self.unstated_body.delete()
        self.user.delete()
        self.driver.quit()
        super(PersonalizeViewFrontendTest, self).tearDown()

    def _get(self, rel_url):
        """
        Perform an HTTP GET request.

        Selenium needs full, not relative, URLs, so we need to join the output
        of reverse() to the URL base in order to get() anywhere.
        """
        full_url = urljoin(self.live_server_url, rel_url)
        self.driver.get(full_url)

    def test_fit_menu_hourglass_silhouettes(self):

        silhouette_menu = Select(self.driver.find_element(By.ID, "id_silhouette"))
        body_menu = Select(self.driver.find_element(By.ID, "id_body"))
        fit_menu = Select(self.driver.find_element(By.ID, "id_garment_fit"))

        for silhouette_value in ["SILHOUETTE_HOURGLASS", "SILHOUETTE_HALFGLASS"]:

            silhouette_menu.select_by_value(silhouette_value)

            for body in [
                self.male_body,
                self.female_body,
                self.child_body,
                self.unstated_body,
            ]:
                body_menu.select_by_value(str(body.id))
                fit_options = fit_menu.options
                for option in fit_options:
                    value = option.get_attribute("value")
                    text = option.text
                    if not value:
                        self.assertEqual(text, "---------")
                        self.assertTrue(option.is_enabled())
                    else:
                        self.assertEqual(
                            option.is_enabled(), value in SDC.FIT_HOURGLASS, text
                        )

    def test_fit_menu_non_hourglass_silhouette(self):

        silhouette_menu = Select(self.driver.find_element(By.ID, "id_silhouette"))
        body_menu = Select(self.driver.find_element(By.ID, "id_body"))
        fit_menu = Select(self.driver.find_element(By.ID, "id_garment_fit"))

        for silhouette_value in [
            "SILHOUETTE_ALINE",
            "SILHOUETTE_TAPERED",
            "SILHOUETTE_STRAIGHT",
        ]:
            silhouette_menu.select_by_value(silhouette_value)

            # male body
            body_menu.select_by_value(str(self.male_body.id))
            fit_options = fit_menu.options
            for option in fit_options:
                value = option.get_attribute("value")
                if not value:
                    text = option.text
                    self.assertEqual(text, "---------")
                    self.assertTrue(option.is_enabled())
                else:
                    self.assertEqual(option.is_enabled(), value in SDC.FIT_MENS, text)

            # female body
            body_menu.select_by_value(str(self.female_body.id))
            fit_options = fit_menu.options
            for option in fit_options:
                value = option.get_attribute("value")
                if not value:
                    text = option.text
                    self.assertEqual(text, "---------")
                    self.assertTrue(option.is_enabled())
                else:
                    self.assertEqual(option.is_enabled(), value in SDC.FIT_WOMENS, text)

            # male body
            body_menu.select_by_value(str(self.child_body.id))
            fit_options = fit_menu.options
            for option in fit_options:
                value = option.get_attribute("value")
                if not value:
                    text = option.text
                    self.assertEqual(text, "---------")
                    self.assertTrue(option.is_enabled())
                else:
                    self.assertEqual(option.is_enabled(), value in SDC.FIT_CHILDS, text)

            # male body
            body_menu.select_by_value(str(self.unstated_body.id))
            fit_options = fit_menu.options
            for option in fit_options:
                value = option.get_attribute("value")
                if not value:
                    text = option.text
                    self.assertEqual(text, "---------")
                    self.assertTrue(option.is_enabled())
                else:
                    self.assertEqual(
                        option.is_enabled(),
                        value in SDC.FIT_MENS + SDC.FIT_WOMENS + SDC.FIT_CHILDS,
                        text,
                    )


class RedoCreateViewTests(TestCase):

    def setUp(self):
        super(RedoCreateViewTests, self).setUp()

        self.pattern = ApprovedSweaterPatternFactory()
        self.alice = self.pattern.user

    def url_of_pattern(self, pattern):
        return reverse("design_wizard:redo_start", kwargs={"pk": pattern.pk})

    # Visibility tests

    def test_can_see_redo_page(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertEqual(response.status_code, 200)

    def test_cant_see_redo_page_pattern_no_redo(self):
        # Kludge pattern into having been redone
        self.pattern.original_pieces = self.pattern.pieces
        self.pattern.save()

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertEqual(response.status_code, 403)

    def test_other_user_cannot_see_page(self):
        bob = UserFactory()
        self.client.force_login(bob)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertEqual(response.status_code, 403)

    # Content tests

    def test_initial_values(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        pspec = self.pattern.get_spec_source()

        self.assertEqual(initial_values["body"], pspec.body.pk)
        self.assertEqual(initial_values["garment_fit"], pspec.garment_fit)
        self.assertEqual(initial_values["torso_length"], pspec.torso_length)
        self.assertEqual(initial_values["sleeve_length"], pspec.sleeve_length)
        self.assertEqual(initial_values["neckline_depth"], pspec.neckline_depth)
        self.assertEqual(
            initial_values["neckline_depth_orientation"],
            pspec.neckline_depth_orientation,
        )

    def test_no_bodies_individual(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        # sanity check
        response = self.client.get(redo_url)
        self.assertNotContains(response, "before you can proceed")

        for body in Body.objects.filter(user=self.alice):
            body.archived = True
            body.save()
        response = self.client.get(redo_url)
        self.assertContains(
            response,
            '<div id="hint_id_body" class="help-block">You need to <a href="/measurement/new/?next=%s">add at least one measurement set</a> before you can proceed.</div>'
            % redo_url,
            html=True,
        )

    def test_no_swatches(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        # sanity check
        response = self.client.get(redo_url)
        self.assertNotContains(response, "before you can proceed")

        for swatch in Swatch.objects.filter(user=self.alice):
            swatch.archived = True
            swatch.save()
        response = self.client.get(redo_url)
        self.assertContains(
            response,
            '<div id="hint_id_swatch" class="help-block">You need to <a href="/swatch/new/?next=%s">add at least one gauge</a> before you can proceed.</div>'
            % redo_url,
            html=True,
        )

    def test_sleeves_present_for_sleeved_garments(self):
        # sanity check:
        self.assertTrue(self.pattern.has_sleeves())

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        goal_html = """<label for="id_sleeve_length" class="control-label  requiredField">
                Sleeve length<span class="asteriskField">*</span> </label>"""
        self.assertContains(response, goal_html, html=True)

    def test_sleeves_absent_for_vest_garments(self):

        vest_pattern = ApprovedSweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_VEST, user=self.alice)
        )
        # sanity check:
        self.assertFalse(vest_pattern.has_sleeves())

        self.client.force_login(vest_pattern.user)
        redo_url = self.url_of_pattern(vest_pattern)
        response = self.client.get(redo_url)
        self.assertNotContains(response, "sleeve length")
        self.assertNotContains(response, "Sleeve length")

    def test_imperial_user_get(self):
        self.alice.profile.display_imperial = True

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertContains(
            response, '<span class="input-group-addon">inches</span>', html=True
        )

        # initial_values = response.context['form'].initial
        # new_values = initial_values
        # new_values['neckline_depth'] = 3
        # new_values['neckline_depth_orientation'] = SDC.BELOW_SHOULDERS
        # # Since there are multiple submit buttons, we must specify the one
        # # we want in the POST data.
        # new_values[REDO_AND_APPROVE] = 'redo!'
        #
        # self.client.post(redo_url, data=new_values)
        # redo = Redo.objects.get(pattern=self.pattern)
        #
        # # Redo should have neckline depth of 3 inches below shoulders
        # self.assertEqual(redo.neckline_depth, 3)
        # self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    def test_metric_user_get(self):
        self.alice.profile.display_imperial = False
        self.alice.profile.save()

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertContains(
            response, '<span class="input-group-addon">cm</span>', html=True
        )

        # initial_values = response.context['form'].initial
        # new_values = initial_values
        # new_values['neckline_depth'] = 10 #cm
        # new_values['neckline_depth_orientation'] = SDC.BELOW_SHOULDERS
        # # Since there are multiple submit buttons, we must specify the one
        # # we want in the POST data.
        # new_values[REDO_AND_APPROVE] = 'redo!'
        #
        # self.client.post(redo_url, data=new_values)
        # redo = Redo.objects.get(pattern=self.pattern)
        #
        # # Redo should have neckline depth of 4 inches below shoulders
        # self.assertAlmostEqual(redo.neckline_depth, cm_to_inches(10), 2)
        # self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    # NOTE: Yes, these tests next two tests technically belong in test_garment. But it turns out that they required
    # a disproportionate amount of testing machinery to make work, so we're going to do them here
    def test_missing_measurements_summary(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "summary"}
        )
        self.assertRedirects(response, goal_url)

    def test_missing_measurements_tweak(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "tweak"}
        )
        self.assertRedirects(response, goal_url)


class RedoUpdateTests(TestCase):

    def setUp(self):

        self.alice = UserFactory()
        self.redo = SweaterRedoFactory(pattern__user=self.alice)
        self.url = reverse("design_wizard:redo_plus_missing", args=(self.redo.id,))
        self.client.force_login(self.alice)
        self.user2 = UserFactory()

    def test_redo_body_wrong_owner(self):
        self.redo.body.user = self.user2
        self.redo.body.save()
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(self.url)

    # Content tests

    def test_initial_values(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial

        self.assertEqual(initial_values["swatch"], self.redo.swatch.pk)
        self.assertEqual(initial_values["garment_fit"], self.redo.garment_fit)
        self.assertEqual(initial_values["torso_length"], self.redo.torso_length)
        self.assertEqual(initial_values["sleeve_length"], self.redo.sleeve_length)
        self.assertEqual(initial_values["neckline_depth"], self.redo.neckline_depth)
        self.assertEqual(
            initial_values["neckline_depth_orientation"],
            self.redo.neckline_depth_orientation,
        )

    def test_sleeves_present_for_sleeved_garments(self):
        # sanity check:
        self.assertTrue(self.redo.pattern.has_sleeves())

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        goal_html = """<label for="id_sleeve_length" class="control-label  requiredField">
                 Sleeve length<span class="asteriskField">*</span> </label>"""
        self.assertContains(response, goal_html, html=True)

    def test_sleeves_absent_for_vest_garments(self):
        vest_pattern = ApprovedSweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_VEST, user=self.alice)
        )
        # sanity check:
        self.assertFalse(vest_pattern.has_sleeves())

        redo = SweaterRedoFactory(
            pattern=vest_pattern, body=vest_pattern.body, swatch=vest_pattern.swatch
        )
        self.client.force_login(vest_pattern.user)
        redo_url = reverse("design_wizard:redo_plus_missing", args=(redo.id,))
        response = self.client.get(redo_url)
        self.assertNotContains(response, "sleeve length")
        self.assertNotContains(response, "Sleeve length")

    def test_imperial_user(self):
        self.alice.profile.display_imperial = True

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertContains(
            response, '<span class="input-group-addon">inches</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 3
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(self.url, data=new_values)
        self.redo.refresh_from_db()
        # Redo should have neckline depth of 3 inches below shoulders
        self.assertEqual(self.redo.neckline_depth, 3)
        self.assertEqual(self.redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    def test_metric_user(self):
        self.alice.profile.display_imperial = False
        self.alice.profile.save()

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertContains(
            response, '<span class="input-group-addon">cm</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 10  # cm
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        # Redo should have neckline depth of 4 inches below shoulders
        self.assertAlmostEqual(redo.neckline_depth, cm_to_inches(10), 2)
        self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    # NOTE: Yes, these tests next two tests technically belong in test_garment. But it turns out that they required
    # a disproportionate amount of testing machinery to make work, so we're going to do them here

    def test_missing_measurements_summary(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.redo.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "summary"}
        )
        self.assertRedirects(response, goal_url)

    def test_missing_measurements_tweak(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.redo.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "tweak"}
        )
        self.assertRedirects(response, goal_url)


class PersonalizeGradedDesignViewTests(TestCase):

    def setUp(self):
        super(PersonalizeGradedDesignViewTests, self).setUp()
        self.user = StaffFactory()
        self.design = SweaterDesignFactory(name="Bar")
        self.design.save()
        self.grade_set = GradeSetFactory()
        self.personalize_url = reverse(
            "graded_wizard:make_graded_pattern", args=(self.design.slug,)
        )

        self.post_entries = {
            "name": "name",
            "row_gauge": 80,
            "stitch_gauge": 80,
            "gradeset": self.grade_set.id,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_HOURGLASS,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "drop_shoulder_additional_armhole_depth": "",
            "sleeve_length": SDC.SLEEVE_FULL,
            "torso_length": SDC.MED_HIP_LENGTH,
        }

    def login(self):
        return self.client.force_login(self.user)

    def _get_design_page(self, design):
        url = reverse("graded_wizard:make_graded_pattern", args=(design.slug,))
        resp = self.client.get(url)
        return resp

    def test_get_page(self):
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertContains(response, self.design.name, status_code=200)
        self.assertContains(
            response,
            "<title>Customize your <em>graded</em>{0}</title>".format(self.design.name),
            html=True,
        )

    def test_options(self):
        self.login()

        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=True,
            silhouette_aline_allowed=True,
            silhouette_straight_allowed=True,
            silhouette_tapered_allowed=True,
        )

        response = self._get_design_page(design)
        form_fields = response.context["form"].fields
        sil_field = form_fields["silhouette"]
        self.assertIn(
            (SDC.SILHOUETTE_HOURGLASS, "Hourglass silhouette"), sil_field._choices
        )
        self.assertIn(
            (SDC.SILHOUETTE_HALF_HOURGLASS, "Half-hourglass silhouette"),
            sil_field._choices,
        )
        self.assertIn(
            (SDC.SILHOUETTE_STRAIGHT, "Straight silhouette"), sil_field._choices
        )
        self.assertIn((SDC.SILHOUETTE_ALINE, "A-line silhouette"), sil_field._choices)
        self.assertIn(
            (SDC.SILHOUETTE_TAPERED, "Tapered silhouette"), sil_field._choices
        )

        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            silhouette_half_hourglass_allowed=False,
            silhouette_aline_allowed=False,
            silhouette_straight_allowed=False,
            silhouette_tapered_allowed=True,
        )

        response = self._get_design_page(design)
        form_fields = response.context["form"].fields
        sil_field = form_fields["silhouette"]
        self.assertIn(
            (SDC.SILHOUETTE_HOURGLASS, "Hourglass silhouette"), sil_field._choices
        )
        self.assertNotIn(
            (SDC.SILHOUETTE_HALF_HOURGLASS, "Half-hourglass silhouette"),
            sil_field._choices,
        )
        self.assertNotIn(
            (SDC.SILHOUETTE_STRAIGHT, "Straight silhouette"), sil_field._choices
        )
        self.assertNotIn(
            (SDC.SILHOUETTE_ALINE, "A-line silhouette"), sil_field._choices
        )
        self.assertIn(
            (SDC.SILHOUETTE_TAPERED, "Tapered silhouette"), sil_field._choices
        )

    def test_initial_values_from_design(self):
        self.login()

        # Test that we can set silhouette through query parameter
        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            silhouette_hourglass_allowed=True,
            primary_construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            drop_shoulder_additional_armhole_depth=None,
        )

        response = self._get_design_page(design)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["silhouette"], SDC.SILHOUETTE_HOURGLASS)
        self.assertEqual(form_initial["construction"], SDC.CONSTRUCTION_SET_IN_SLEEVE)
        self.assertIsNone(form_initial["drop_shoulder_additional_armhole_depth"])

        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_ALINE,
            silhouette_aline_allowed=True,
            primary_construction=SDC.CONSTRUCTION_DROP_SHOULDER,
            construction_drop_shoulder_allowed=True,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        response = self._get_design_page(design)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["silhouette"], SDC.SILHOUETTE_ALINE)
        self.assertEqual(form_initial["construction"], SDC.CONSTRUCTION_DROP_SHOULDER)
        self.assertEqual(
            form_initial["drop_shoulder_additional_armhole_depth"],
            SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )

        design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_ALINE,
            silhouette_aline_allowed=True,
            primary_construction=SDC.CONSTRUCTION_SET_IN_SLEEVE,
            construction_drop_shoulder_allowed=True,
            drop_shoulder_additional_armhole_depth=SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE,
        )
        response = self._get_design_page(design)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["silhouette"], SDC.SILHOUETTE_ALINE)
        self.assertEqual(form_initial["construction"], SDC.CONSTRUCTION_SET_IN_SLEEVE)
        self.assertIsNone(form_initial["drop_shoulder_additional_armhole_depth"])

    def test_post(self):
        self.login()

        response = self.client.post(self.personalize_url, self.post_entries)
        self.assertEqual(response.status_code, 302)
        self.assertRegex(response["Location"], r"^/pattern/graded/\d+/$")

    def test_post2(self):
        self.login()

        response = self.client.post(
            self.personalize_url, self.post_entries, follow=True
        )
