import logging
from unittest import skip
from urllib.parse import urljoin

from django.test import LiveServerTestCase, RequestFactory, TestCase, tag
from django.test.client import Client
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from seleniumlogin import force_login

from customfit.bodies.factories import BodyFactory
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.helpers.math_helpers import convert_value_to_metric
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ...factories import (
    ApprovedSweaterPatternFactory,
    SweaterIndividualGarmentParametersFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
)
from ...forms import (
    TWEAK_FIELDS,
    TweakSweaterIndividualGarmentParameters,
    TweakSweaterRedoIndividualGarmentParameters,
)
from ...helpers import sweater_design_choices as SDC
from ...models import SweaterIndividualGarmentParameters, SweaterRedo

# Get an instance of a logger
logger = logging.getLogger(__name__)


class TweakViewTestsMixin(object):

    # Written as a mixin to keep py.test from running the
    # tests in here directly, and not only in sub-classes. (Nose, how I miss
    # you...)
    #
    # Expects sub-classes to implement:
    #
    # * setUp, setting self.user, self.user2, self.client, and self.igp (owned
    #     by user1)
    # * login(), logging in as user1
    # * _make_igp(**kwargs), which take in kwargs appropriate for
    #     SweaterPatternSpecFactory and return a (saved) IGP

    # Helper functions
    # --------------------------------------------------------------------------

    def _tweak_url(self, igp):
        return reverse("design_wizard:tweak", args=(igp.id,))

    def _switch_to_metric(self):
        self.user.profile.display_imperial = False
        self.user.profile.save()

    def _get_tweak_page(self):
        tweak_url = self._tweak_url(self.igp)
        response = self.client.get(tweak_url)
        return response

    def _make_igp(self, **kwargs):
        kwargs["user"] = self.user
        kwargs["body"] = self.body
        kwargs["swatch"] = self.swatch
        ps = SweaterPatternSpecFactory(**kwargs)
        ps.save()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(self.user, ps)
        igp.save()
        return igp

    def _make_summary_url(self, igp):
        summary_url = reverse("design_wizard:summary", args=(igp.id,))
        return summary_url

    def _get_igp_data(self, metric=False):
        if metric:
            conversion = 2.54
        else:
            conversion = 1

        data = {}
        for field in TWEAK_FIELDS:
            data[field] = getattr(self.igp, field) * conversion
        data["shoulder_width"] = (
            0.5
            * (self.igp.back_cross_back_width - self.igp.back_neck_opening_width)
            * conversion
        )

        return data

    def _get_tweak_form_class(self):
        return TweakSweaterIndividualGarmentParameters

    # Checks on page permissions/visibility
    # --------------------------------------------------------------------------

    # def test_anonymous_users_cannot_see_tweak_page(self):
    #     """
    #     Anonymous users should be prompted to log in.
    #     """
    #     response = self._get_tweak_page()
    #     self.assertEqual(response.status_code, 302)
    #
    #
    # def test_users_cannot_see_tweak_page_for_unowned_igp(self):
    #     """
    #     username2 does not own self.igp, so should not be able to see content
    #     at self.tweak_url.
    #     """
    #     self.igp.user = self.user2
    #     self.igp.save()
    #     self.login()
    #     response = self._get_tweak_page()
    #     self.assertContains(response,
    #                         "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)
    #
    #
    # def test_users_can_see_tweak_page_for_own_igp(self):
    #     """
    #     Logged-in users can see the tweak page for their own IGP.
    #     (Note that there's no reason to restrict the path to take to get here,
    #     or whether the page is visible after they've purchased a sweater;
    #     there's nothing wrong with users revisiting old IGPs and possibly
    #     making new patterns from them.)
    #     """
    #     self.login()
    #     response = self._get_tweak_page()
    #     self.assertEqual(response.status_code, 200)
    #     self.assertContains(response, 'FIT RECOMMENDATIONS: SUMMARY')

    # Smoke tests: does the page contain expected elements
    # --------------------------------------------------------------------------

    def test_tweak_page_contains_pattern_name(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, self.igp.name)

    def test_tweak_page_contains_garment_fit(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, self.igp.fit_text)

    def test_tweak_page_contains_link_to_body(self):
        self.login()
        response = self._get_tweak_page()
        body_link = self.igp.body.get_absolute_url()
        self.assertContains(response, body_link)

    def test_tweak_page_contains_link_to_swatch(self):
        self.login()
        response = self._get_tweak_page()
        swatch_link = self.igp.swatch.get_absolute_url()
        self.assertContains(response, swatch_link)

    def test_tweak_page_contains_silhouette(self):
        self.login()
        for silhouette, desc in SDC.SILHOUETTE_CHOICES:
            fit = (
                SDC.FIT_HOURGLASS_AVERAGE
                if silhouette
                in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]
                else SDC.FIT_WOMENS_AVERAGE
            )
            self.igp = self._make_igp(silhouette=silhouette, garment_fit=fit)
            response = self._get_tweak_page()
            goal_html = '<p class="text-indent margin-top-0">%s</p>' % desc
            self.assertContains(response, goal_html, html=True)

    def test_tweak_page_contains_body_bust_size(self):
        """
        This is a smoke test to check that we're displaying measurements at
        all. In fact we should also be displaying additional body measurements;
        this test checks that we haven't entirely forgotten rather than looking
        for each one.
        """
        self.login()
        response = self._get_tweak_page()
        bust_measurement = self.igp.body.bust_circ
        self.assertContains(response, bust_measurement)

    def test_form_handled_metric_users(self):
        # Same smoke test as test_tweak_page_contains_body_bust_size,
        # but for metric users
        self.user.profile.display_imperial = False
        self.user.profile.save()

        self.login()
        response = self._get_tweak_page()
        bust_measurement_float = convert_value_to_metric(
            self.igp.body.bust_circ, "length"
        )  # 104.14cm
        goal_measurement = int(bust_measurement_float)  # rounding shortcut
        self.assertContains(response, goal_measurement)

    def test_tweak_page_contains_igp_bust_size(self):
        """
        As above, but checks for recommended garment measurement rather than
        original body bust size.
        """
        self.login()
        response = self._get_tweak_page()
        bust_measurement = self.igp.bust_circ_total
        self.assertContains(response, bust_measurement)

    # Test that the right form-fields show up under the right conditions
    # --------------------------------------------------------------------------

    def test_hourglass_fields(self):
        self.login()
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED, silhouette=SDC.SILHOUETTE_HOURGLASS
        )
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        required_fields = [
            "bust_width_front",
            "bust_width_back",
            "waist_width_front",
            "waist_width_back",
            "hip_width_front",
            "hip_width_back",
            "back_neck_opening_width",
            "shoulder_width",
            "armhole_depth",
            "below_armhole_straight",
            "front_neck_depth",
            "armpit_height",
            "waist_height_back",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

        banished_fields = [
            "back_cross_back_width",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_half_hourglass_fields(self):
        self.login()
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED, silhouette=SDC.SILHOUETTE_HALF_HOURGLASS
        )
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        required_fields = [
            "bust_width_front",
            "bust_width_back",
            "waist_width_front",
            "waist_width_back",
            "hip_width_front",
            "hip_width_back",
            "back_neck_opening_width",
            "shoulder_width",
            "armhole_depth",
            "below_armhole_straight",
            "front_neck_depth",
            "armpit_height",
            "waist_height_back",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

        banished_fields = [
            "back_cross_back_width",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_aline_fields(self):
        self.login()
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_ALINE,
        )
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url, follow=False)
        required_fields = [
            "bust_width_front",
            "bust_width_back",
            "hip_width_front",
            "hip_width_back",
            "back_neck_opening_width",
            "shoulder_width",
            "armhole_depth",
            "below_armhole_straight",
            "front_neck_depth",
            "armpit_height",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

        banished_fields = [
            "waist_width_front",
            "waist_width_back",
            "waist_height_back",
            "back_cross_back_width",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_tapered_fields(self):
        self.login()
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_TAPERED,
        )
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        required_fields = [
            "bust_width_front",
            "bust_width_back",
            "hip_width_front",
            "hip_width_back",
            "back_neck_opening_width",
            "shoulder_width",
            "armhole_depth",
            "below_armhole_straight",
            "front_neck_depth",
            "armpit_height",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

        banished_fields = [
            "waist_width_front",
            "waist_width_back",
            "waist_height_back",
            "back_cross_back_width",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_straight_fields(self):
        self.login()
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        required_fields = [
            "bust_width_front",
            "bust_width_back",
            "hip_width_front",
            "hip_width_back",
            "back_neck_opening_width",
            "shoulder_width",
            "armhole_depth",
            "front_neck_depth",
            "armpit_height",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

        banished_fields = [
            "waist_width_front",
            "waist_width_back",
            "below_armhole_straight",
            "waist_height_back",
            "back_cross_back_width",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_sleeved(self):
        self.login()
        igp = self._make_igp(garment_type=SDC.PULLOVER_SLEEVED)
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        required_fields = [
            "bicep_width",
            "sleeve_cast_on_width",
            "sleeve_to_armcap_start_height",
        ]
        for field_name in required_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertContains(response, field_id)

    def test_vest(self):
        self.login()
        igp = self._make_igp(garment_type=SDC.PULLOVER_VEST)
        tweak_url = self._tweak_url(igp)
        response = self.client.get(tweak_url)
        banished_fields = [
            "bicep_width",
            "sleeve_cast_on_width",
            "sleeve_to_armcap_start_height",
        ]
        for field_name in banished_fields:
            field_id = 'id="id_%s"' % field_name
            self.assertNotContains(response, field_id)

    def test_form_has_sleeve_elements(self):
        igp = self._make_igp(
            user=self.user,
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        tweak_url = self._tweak_url(igp)

        self.login()

        response = self.client.get(tweak_url)
        self.assertContains(response, 'id="id_sleeve_cast_on_width"')
        self.assertContains(response, 'id="id_sleeve_to_armcap_start_height"')
        self.assertContains(response, 'id="id_bicep_width"')

    def test_form_omits_sleeve_elements(self):
        igp = self._make_igp(
            user=self.user,
            garment_type=SDC.PULLOVER_VEST,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        tweak_url = self._tweak_url(igp)

        self.login()

        response = self.client.get(tweak_url)
        self.assertNotContains(response, 'id="id_sleeve_cast_on_width"')
        self.assertNotContains(response, 'id="id_sleeve_to_armcap_start_height"')
        self.assertNotContains(response, 'id="id_bicep_width"')

    # Validation checks
    # --------------------------------------------------------------------------

    # def test_error_igp_wrong_owner(self):
    #     self.igp.user = self.user2
    #     self.igp.save()
    #     self.login()
    #     response = self.client.get(self._tweak_url(self.igp))
    #     self.assertContains(response, "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)

    def test_error_igp_body_has_wrong_owner(self):
        self.igp.body.user = self.user2
        self.igp.body.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(self._tweak_url(self.igp))

    # def test_error_igp_swatch_has_wrong_owner(self):
    #     self.igp.swatch.user = self.user2
    #     self.igp.swatch.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         self.client.get(self._tweak_url(self.igp))

    # # Note: this test is shadowed in the Redo tests, below
    # def test_error_igp_patternspec_has_wrong_owner(self):
    #     self.igp.pattern_spec.user = self.user2
    #     self.igp.pattern_spec.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         self.client.get(self._tweak_url(self.igp))

    # # Functional checks: does the form do things we expect?
    # # --------------------------------------------------------------------------
    #
    # def test_form_submit_goes_to_summary_page(self):
    #     self.login()
    #     # We need some kind of valid data to submit; just resubmit
    #     # the existing IGP.
    #     data = self._get_igp_data()
    #
    #     response = self.client.post(self._tweak_url(self.igp), data, follow=True)
    #     self.assertRedirects(response, self._make_summary_url(self.igp))
    #

    # Bust shaping tweaks ------------------------------------------------------
    def test_can_compress_bust_shaping(self):
        self.login()
        data = self._get_igp_data()

        self.assertEqual(self.igp.below_armhole_straight, 1.5)

        data["below_armhole_straight"] = 4.0
        response = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.below_armhole_straight, 4.0)

    def test_can_compress_bust_shaping_metric(self):
        self.login()
        self._switch_to_metric()
        # Get data from IGP
        data = self._get_igp_data(metric=True)

        self.assertEqual(self.igp.below_armhole_straight, 1.5)

        data["below_armhole_straight"] = (
            10.0  # This should be interpreted as cm. 10cm = 4'', so should be allowed
        )
        response = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.below_armhole_straight, 10.0 / 2.54, 2)

    def test_can_expand_bust_shaping(self):
        self.login()
        # Get data from IGP
        data = self._get_igp_data()

        self.assertEqual(self.igp.below_armhole_straight, 1.5)

        data["below_armhole_straight"] = 1.0
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.below_armhole_straight, 1.0)

    def test_cant_expand_bust_shaping_too_much(self):
        self.login()
        # Get data from IGP
        data = self._get_igp_data()

        self.assertEqual(self.igp.below_armhole_straight, 1.5)

        data["below_armhole_straight"] = 6.0
        response = self.client.post(self._tweak_url(self.igp), data, follow=True)
        form = response.context["form"]
        self.assertFormError(
            form,
            "below_armhole_straight",
            ["This must be less than 5 inches / 12.7 cm"],
        )
        self.igp.refresh_from_db()
        self.assertEqual(self.igp.below_armhole_straight, 1.5)

    def test_bust_shaping_straight_design(self):
        # Test that clean_below_armhole_straight works/doesn't break for straight designs
        igp = self._make_igp(
            garment_type=SDC.PULLOVER_SLEEVED,
            garment_fit=SDC.FIT_WOMENS_AVERAGE,
            silhouette=SDC.SILHOUETTE_STRAIGHT,
        )
        tweak_url = self._tweak_url(igp)

        self.login()

        data = self._get_igp_data()

        del data["below_armhole_straight"]

        _ = self.client.post(self._tweak_url(igp), data, follow=True)
        self.igp.refresh_from_db()
        self.assertEqual(self.igp.below_armhole_straight, 1.5)

    # back shaping tweaks -----------------------------------------------
    def test_can_decrease_back_bust(self):
        """
        Decreasing the neck width should propagate to neck width and
        cross-chest in the IGP.
        """
        self.login()
        data = self._get_igp_data()

        # Verify assumptions.
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.bust_width_back, 19.625)

        data["bust_width_back"] = self.igp.back_cross_back_width - 1
        data["waist_width_back"] = data["bust_width_back"] - 1
        resp = self.client.post(self._tweak_url(self.igp), data, follow=True)
        form = resp.context["form"]
        self.assertFormError(
            form,
            None,
            "Need to leave 3.0 inches for armhole-shaping (currently leaving -1.0)",
        )

    # Cross-chest shaping tweaks -----------------------------------------------
    def test_can_decrease_neck_width(self):
        """
        Decreasing the neck width should propagate to neck width and
        cross-chest in the IGP.
        """
        self.login()
        data = self._get_igp_data()

        # Verify assumptions.
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["back_neck_opening_width"] = 6.0
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.back_neck_opening_width, 6.0)
        self.assertEqual(self.igp.back_cross_back_width, 13.0)

    def test_can_decrease_neck_width_metric(self):
        self.login()
        self._switch_to_metric()
        data = self._get_igp_data(metric=True)

        # Verify assumptions. (Note that IGP values are in inches even if post
        # data is in cm.)
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["back_neck_opening_width"] = 15.25
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.back_neck_opening_width, 6.0, delta=0.1)
        self.assertAlmostEqual(self.igp.back_cross_back_width, 13.0, delta=0.1)

    def test_can_increase_neck_width(self):
        self.login()
        data = self._get_igp_data()

        # Verify assumptions.
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["back_neck_opening_width"] = 8.0
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.back_neck_opening_width, 8.0)
        self.assertEqual(self.igp.back_cross_back_width, 15.0)

    def test_can_increase_neck_width_metric(self):
        self.login()
        self._switch_to_metric()
        data = self._get_igp_data(metric=True)

        # Verify assumptions. (Note that IGP values are in inches even if post
        # data is in cm.)
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["back_neck_opening_width"] = 20.25
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.back_neck_opening_width, 8.0, delta=0.1)
        self.assertAlmostEqual(self.igp.back_cross_back_width, 15.0, delta=0.1)

    def test_can_decrease_shoulder_width(self):
        """
        Decreasing the shoulder width should propagate to cross-chest in the
        IGP.
        """
        self.login()
        data = self._get_igp_data()

        # Verify assumptions.
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["shoulder_width"] = 3.0  # half-inch decrease
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)
        # Cross back should be a full inch smaller because each of 2 shoulders
        # has been decreased by half an inch.
        self.assertEqual(self.igp.back_cross_back_width, 13.0)

    def test_can_decrease_shoulder_width_metric(self):
        self.login()
        self._switch_to_metric()
        data = self._get_igp_data(metric=True)

        # Verify assumptions. (Note that IGP values are in inches even if post
        # data is in cm.)
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["shoulder_width"] = 7.6  # half-inch decrease
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        # Neck opening should not have changed, so we can assert equal rather
        # than almostequal.
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)
        self.assertAlmostEqual(self.igp.back_cross_back_width, 13.0, delta=0.1)

    def test_can_increase_shoulder_width(self):
        self.login()
        data = self._get_igp_data()

        # Verify assumptions.
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["shoulder_width"] = 4.0  # half-inch increase
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)
        self.assertEqual(self.igp.back_cross_back_width, 15.0)

    def test_can_increase_shoulder_width_metric(self):
        self.login()
        self._switch_to_metric()
        data = self._get_igp_data(metric=True)

        # Verify assumptions. (Note that IGP values are in inches even if post
        # data is in cm.)
        self.assertEqual(self.igp.back_cross_back_width, 14.0)
        self.assertEqual(self.igp.back_neck_opening_width, 7.0)

        data["shoulder_width"] = 10.2
        _ = self.client.post(self._tweak_url(self.igp), data, follow=True)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.back_neck_opening_width, 7.0)
        self.assertAlmostEqual(self.igp.back_cross_back_width, 15.0, delta=0.1)

    #


class TweakViewTestIndividual(TweakViewTestsMixin, TestCase):  # Individual

    def setUp(self):
        super(TweakViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.igp = SweaterIndividualGarmentParametersFactory(user=self.user)
        self.igp.body.user = self.user
        self.igp.body.save()
        self.igp.swatch.user = self.user
        self.igp.swatch.save()
        self.igp.save()
        self.igp.pattern_spec.user = self.user
        self.igp.pattern_spec.save()
        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def _test_response(self, response):
        return self._test_individual_response(response)

    def _make_igp(self, **kwargs):
        kwargs["user"] = kwargs.get("user", self.user)
        kwargs["body"] = kwargs.get("body", BodyFactory(user=self.user))
        kwargs["swatch"] = kwargs.get("swatch", SwatchFactory(user=self.user))
        ps = SweaterPatternSpecFactory(**kwargs)
        ps.save()
        igp = SweaterIndividualGarmentParameters.make_from_patternspec(self.user, ps)
        igp.save()
        return igp

    # def _get_expected_header(self, igp):
    #     return "<h2>Customize fit specifics</h2>"
    #
    #
    # def test_tweak_page_contains_header(self):
    #     self.login()
    #     response = self._get_tweak_page()
    #     self.assertContains(response, self._get_expected_header(self.igp), html = True)


@tag("selenium")
class TweakViewFrontendTest(LiveServerTestCase):
    """
    Test the elements of the garment tweaking workflow that rely on JS.
    """

    def setUp(self):
        super(TweakViewFrontendTest, self).setUp()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)

        self.user = UserFactory()

        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)

        self.igp = SweaterIndividualGarmentParametersFactory(user=self.user)
        self.igp.body.user = self.user
        self.igp.body.save()
        self.igp.swatch.user = self.user
        self.igp.swatch.save()
        self.igp.pattern_spec.user = self.user
        self.igp.pattern_spec.save()
        self.igp.save()

        # Log in
        force_login(self.user, self.driver, self.live_server_url)

        # Go to tweak page
        self._get(reverse("design_wizard:tweak", args=(self.igp.id,)))

    def tearDown(self):
        self.driver.quit()
        super(TweakViewFrontendTest, self).tearDown()

    def _get(self, rel_url):
        """
        Perform an HTTP GET request.

        Selenium needs full, not relative, URLs, so we need to join the output
        of reverse() to the URL base in order to get() anywhere.
        """
        full_url = urljoin(self.live_server_url, rel_url)
        self.driver.get(full_url)

    def _click_button(self, button):
        self.driver.execute_script("arguments[0].scrollIntoView(true);", button)
        button.click()

    def _switch_to_metric(self):
        self.user.profile.display_imperial = False
        self.user.profile.save()
        self._get(reverse("design_wizard:tweak", args=(self.igp.id,)))

    def _inner_circ_and_ease_test(self, step_amt, delta):
        # First, make sure the relevant total circs and eases (but ONLY
        # those) update the when you use the +/- icons.
        bust_circ = self.driver.find_elements(By.CLASS_NAME, "display_circ")[0]
        bust_ease = self.driver.find_elements(By.CLASS_NAME, "display_ease")[0]

        waist_circ = self.driver.find_elements(By.CLASS_NAME, "display_circ")[1]
        waist_ease = self.driver.find_elements(By.CLASS_NAME, "display_ease")[1]

        orig_bust_circ = bust_circ.get_attribute("innerHTML")
        orig_bust_ease = bust_ease.get_attribute("innerHTML")

        orig_waist_circ = waist_circ.get_attribute("innerHTML")
        orig_waist_ease = waist_ease.get_attribute("innerHTML")

        bust_plus = self.driver.find_element(
            By.ID, "glyphicon-div_id_bust_width_front-plus"
        )
        self._click_button(bust_plus)

        new_bust_circ = bust_circ.get_attribute("innerHTML")
        new_bust_ease = bust_ease.get_attribute("innerHTML")

        new_waist_circ = waist_circ.get_attribute("innerHTML")
        new_waist_ease = waist_ease.get_attribute("innerHTML")

        # We need to assertAlmostEqual, not assertEqual, because values may be
        # rounded.
        self.assertAlmostEqual(
            float(orig_bust_circ) + step_amt, float(new_bust_circ), delta=delta
        )
        self.assertAlmostEqual(
            float(orig_bust_ease) + step_amt, float(new_bust_ease), delta=delta
        )

        self.assertAlmostEqual(
            float(orig_waist_circ), float(new_waist_circ), delta=delta
        )
        self.assertAlmostEqual(
            float(orig_waist_ease), float(new_waist_ease), delta=delta
        )

        # We should also test that the auto-updating works when you edit form
        # fields directly, but selenium doesn't properly simulate the blur
        # event that triggers the script, and workarounds are buggy.

    def _inner_icon_test(self, step_amt, delta, direction):
        bust_front = self.driver.find_element(By.ID, "id_bust_width_front")
        bust_back = self.driver.find_element(By.ID, "id_bust_width_back")

        orig_value_front = bust_front.get_attribute("value")
        orig_value_back = bust_back.get_attribute("value")

        icon = self.driver.find_element(
            By.ID, "glyphicon-div_id_bust_width_front-" + direction
        )
        self._click_button(icon)

        new_value_front = bust_front.get_attribute("value")
        new_value_back = bust_back.get_attribute("value")

        self.assertAlmostEqual(
            float(orig_value_front) + step_amt, float(new_value_front), delta=delta
        )
        self.assertAlmostEqual(
            float(orig_value_back), float(new_value_back), delta=delta
        )

    def test_plus_icon_increases(self):
        """
        Ensure that clicking the + icon increases the corresponding field by
        0.25 (and does not alter other fields), when the user unit preference
        is imperial.
        """
        self._inner_icon_test(0.25, 0.1, "plus")

    def test_plus_icon_increases_metric(self):
        """
        Ensure that clicking the + icon increases the corresponding field by
        0.5 (and does not alter other fields), when the user unit preference
        is metric.
        """
        self._switch_to_metric()
        self._inner_icon_test(0.5, 0.1, "plus")

    def test_minus_icon_decreases(self):
        self._inner_icon_test(-0.25, 0.1, "minus")

    def test_minus_icon_decreases_metric(self):
        self._switch_to_metric()
        self._inner_icon_test(-0.5, 0.1, "minus")

    def test_circs_and_eases_auto_update(self):
        self._inner_circ_and_ease_test(0.25, 0.1)

    def test_circs_and_eases_auto_update_metric(self):
        self._switch_to_metric()
        self._inner_circ_and_ease_test(0.5, 0.1)

    def test_restore_button_restores(self):
        # Make a new version of the IGP, and remember the original value
        orig_value = self.igp.armhole_depth
        self.igp.armhole_depth += 0.25
        self.igp.save()

        # Reload the page
        self._get(reverse("design_wizard:tweak", args=(self.igp.id,)))

        # Make sure you see the new value
        armhole_depth = self.driver.find_element(By.ID, "id_armhole_depth")
        current_value = armhole_depth.get_attribute("value")
        self.assertEqual(str(current_value), str(self.igp.armhole_depth))
        self.assertNotEqual(current_value, orig_value)

        # Click the restore button and make sure you see the original value
        restore_button = self.driver.find_element(By.ID, "button-id-restore")
        self._click_button(restore_button)

        post_restore_value = armhole_depth.get_attribute("value")
        self.assertEqual(float(post_restore_value), float(orig_value))

    @skip("need to write")
    def test_hourglass_body_validation_custom(self):
        """
        We need to have a test that verifies that hourglass silhouettes are only
        available for bodies that have all hourglass measurements, but our JS
        tests have been failing so consistently that I'm not writing that test.
        Putting a placeholder here lest we fix JS testing at some point.
        """
        pass


class RedoTweakViewTestsMixin(object):
    # Additional tests for the redo-tweak page, or tests that need to shadow those
    # in TweakViewTestsMixin, above
    pass


class RedoTweakViewTestsIndividual(RedoTweakViewTestsMixin, TweakViewTestIndividual):

    def setUp(self):
        self.pattern = ApprovedSweaterPatternFactory()
        self.user = self.pattern.user

        pspec = self.pattern.get_spec_source()
        redo = SweaterRedo(
            body=pspec.body,
            swatch=pspec.swatch,
            garment_fit=pspec.garment_fit,
            torso_length=pspec.torso_length,
            sleeve_length=pspec.sleeve_length,
            neckline_depth=pspec.neckline_depth,
            neckline_depth_orientation=pspec.neckline_depth_orientation,
            pattern=self.pattern,
        )
        redo.save()
        redo_igp = SweaterIndividualGarmentParameters.make_from_redo(self.user, redo)
        redo_igp.save()
        self.igp = redo_igp

        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):
        kwargs["user"] = kwargs.get("user", self.user)
        user = kwargs["user"]
        kwargs["body"] = kwargs.get("body", BodyFactory(user=self.user))
        kwargs["swatch"] = kwargs.get("swatch", SwatchFactory(user=self.user))
        pspec = SweaterPatternSpecFactory(**kwargs)
        pspec.save()
        p = SweaterPatternFactory.from_pspec(pspec)

        redo = SweaterRedo(
            body=pspec.body,
            swatch=pspec.swatch,
            garment_fit=pspec.garment_fit,
            torso_length=pspec.torso_length,
            sleeve_length=pspec.sleeve_length,
            neckline_depth=pspec.neckline_depth,
            neckline_depth_orientation=pspec.neckline_depth_orientation,
            pattern=p,
        )
        redo.save()
        igp = SweaterIndividualGarmentParameters.make_from_redo(self.user, redo)
        igp.save()
        return igp

    def _tweak_url(self, igp):
        return reverse("design_wizard:redo_tweak", args=(igp.id,))

    def _make_summary_url(self, igp):
        summary_url = reverse("design_wizard:redo_approve", args=(self.igp.id,))
        return summary_url

    def _get_tweak_form_class(self):
        return TweakSweaterRedoIndividualGarmentParameters

    def _get_expected_header(self, igp):
        pattern_name = igp.redo.pattern.name
        return "<h2>Customize fit specifics for your %s redo</h2>" % pattern_name

    # #######################################################################################
    #
    # Shadowing tests of same name in superclasses
    #
    # #######################################################################################

    #
    #
    # def test_error_igp_patternspec_has_wrong_owner(self):
    #     self.igp.redo.pattern.user = self.user2
    #     self.igp.redo.pattern.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         self.client.get(self._tweak_url(self.igp))
