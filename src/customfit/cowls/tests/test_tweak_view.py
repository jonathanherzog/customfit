import logging
import re
from urllib.parse import urljoin

from django.test import LiveServerTestCase, RequestFactory, TestCase, tag
from django.test.client import Client
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from seleniumlogin import force_login

from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.helpers.magic_constants import CM_PER_INCHES, FLOATING_POINT_NOISE
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from .. import helpers as CDC
from ..factories import (
    ApprovedCowlPatternFactory,
    CowlDesignFactory,
    CowlIndividualGarmentParametersFactory,
    CowlPatternSpecFactory,
    CowlRedoFactory,
)
from ..forms import (
    TweakCowlIndividualGarmentParameters,
    TweakCowlRedoIndividualGarmentParameters,
)
from ..models import CowlIndividualGarmentParameters

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
    #     CowlPatternSpecFactory and return a (saved) IGP

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
        kwargs["swatch"] = self.swatch
        ps = CowlPatternSpecFactory(**kwargs)
        ps.save()
        igp = CowlIndividualGarmentParameters.make_from_patternspec(ps.user, ps)
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
        for field in TweakCowlIndividualGarmentParameters._meta.fields:
            data[field] = getattr(self.igp, field) * conversion
        return data

    def _get_tweak_form_class(self):
        return TweakCowlIndividualGarmentParameters

    # Checks on page permissions/visibility
    # --------------------------------------------------------------------------

    def test_anonymous_users_cannot_see_tweak_page(self):
        """
        Anonymous users should be prompted to log in.
        """
        response = self._get_tweak_page()
        self.assertEqual(response.status_code, 302)

    def test_users_cannot_see_tweak_page_for_unowned_igp(self):
        """
        username2 does not own self.igp, so should not be able to see content
        at self.tweak_url.
        """
        self.igp.user = self.user2
        self.igp.save()
        self.login()
        response = self._get_tweak_page()
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_users_can_see_tweak_page_for_own_igp(self):
        """
        Logged-in users can see the tweak page for their own IGP.
        (Note that there's no reason to restrict the path to take to get here,
        or whether the page is visible after they've purchased a sweater;
        there's nothing wrong with users revisiting old IGPs and possibly
        making new patterns from them.)
        """
        self.login()
        response = self._get_tweak_page()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SIZING RECOMMENDATIONS: SUMMARY")

    # Smoke tests: does the page contain expected elements
    # --------------------------------------------------------------------------

    def test_tweak_page_contains_pattern_name(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, self.igp.name)

    def test_tweak_page_contains_cowl_height_text(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, "average height")

    def test_tweak_page_contains_cowl_height_inches(self):
        self.login()
        response = self._get_tweak_page()
        goal_html = """
            <tr>
            <td class="text-right pad-right">Height</td>
            <td>12&quot;/30.5 cm</td>
          </tr>"""
        self.assertContains(response, goal_html, html=True)

    def test_tweak_page_contains_cowl_cert_inches(self):
        self.login()
        response = self._get_tweak_page()
        goal_html = """
            <tr>
            <td class="text-right pad-right">circumference</td>
            <td>42&quot;/106.5 cm</td>
          </tr>"""
        self.assertContains(response, goal_html, html=True)

    def test_tweak_page_contains_cowl_circ(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, "medium circumference")

    def test_tweak_page_contains_link_to_swatch(self):
        self.login()
        response = self._get_tweak_page()
        swatch_link = self.igp.swatch.get_absolute_url()
        swatch_name = self.igp.swatch.name
        goal_html = '<a href="%s">%s</a>' % (swatch_link, swatch_name)
        self.assertContains(response, goal_html)

    # Test the measurements summary

    def test_sizing_summary(self):

        # sanity checks
        self.assertEqual(self.igp.height, 12)
        self.assertEqual(self.igp.circumference, 42)

        self.login()
        response = self._get_tweak_page()
        goal_html = """
        <tbody>
          <tr>
            <td class="text-right pad-right">Height</td>
            <td>12&quot;/30.5 cm</td>
          </tr>
          <tr>
            <td class="text-right pad-right">circumference</td>
            <td>42&quot;/106.5 cm</td>
          </tr>
        </tbody>"""
        self.assertContains(response, goal_html, html=True)

    # Test simple parts of the page

    def test_tweak_page_contains_form(self):
        self.login()
        response = self._get_tweak_page()
        self.assertIsInstance(response.context["form"], self._get_tweak_form_class())

    def test_continue_links_to_summary(self):
        """
        This page should contain a link, styled like a customfit button, that
        links to the summary page for this IGP.
        """
        self.login()
        response = self._get_tweak_page()
        summary_url = self._make_summary_url(self.igp)
        button_html = (
            r"<a.*class=[\'\"].*btn-customfit.*href=[\'\"]%s[\'\"]" % summary_url
        )
        button_html2 = (
            r"<a.*href=[\'\"]%s[\'\"].*class=[\'\"].*btn-customfit" % summary_url
        )

        # It really doesn't matter if the link element declares the href first
        # or the class first, so as long as one of these assertions passes,
        # we're fine.
        assert re.search(button_html, response.rendered_content) or re.search(
            button_html2, response.rendered_content
        )

    # Validation checks
    # --------------------------------------------------------------------------

    def test_error_igp_wrong_owner(self):
        self.igp.user = self.user2
        self.igp.save()
        self.login()
        response = self.client.get(self._tweak_url(self.igp))
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_error_igp_swatch_has_wrong_owner(self):
        self.igp.swatch.user = self.user2
        self.igp.swatch.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(self._tweak_url(self.igp))

    # Note: this test is shadowed in the Redo tests, below
    def test_error_igp_patternspec_has_wrong_owner(self):
        self.igp.pattern_spec.user = self.user2
        self.igp.pattern_spec.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(self._tweak_url(self.igp))

    # Functional checks: does the form do things we expect?
    # --------------------------------------------------------------------------

    def test_form_submit_goes_to_summary_page(self):
        self.login()
        # We need some kind of valid data to submit; just resubmit
        # the existing IGP.
        data = self._get_igp_data()

        response = self.client.post(self._tweak_url(self.igp), data, follow=False)
        self.assertRedirects(
            response, self._make_summary_url(self.igp), fetch_redirect_response=False
        )

    def test_change_height(self):
        self.login()
        data = self._get_igp_data()

        self.assertEqual(self.igp.height, 12)

        data["height"] = 15.5
        response = self.client.post(self._tweak_url(self.igp), data, follow=False)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.height, 15.5)

    def test_change_height_metric(self):

        self._switch_to_metric()

        self.login()
        data = self._get_igp_data()

        self.assertEqual(self.igp.height, 12)

        data["height"] = 15.5 * CM_PER_INCHES
        _ = self.client.post(self._tweak_url(self.igp), data, follow=False)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.height, 15.5, delta=FLOATING_POINT_NOISE)

    def test_change_circ(self):

        self.login()
        data = self._get_igp_data()

        self.assertEqual(self.igp.circumference, 42)

        data["circumference"] = 39.5
        _ = self.client.post(self._tweak_url(self.igp), data, follow=False)

        self.igp.refresh_from_db()
        self.assertEqual(self.igp.circumference, 39.5)

    def test_change_circ_metric(self):
        self._switch_to_metric()

        self.login()
        data = self._get_igp_data()

        self.assertEqual(self.igp.circumference, 42)

        data["circumference"] = 39.5 * CM_PER_INCHES
        _ = self.client.post(self._tweak_url(self.igp), data, follow=False)

        self.igp.refresh_from_db()
        self.assertAlmostEqual(self.igp.circumference, 39.5, FLOATING_POINT_NOISE)


class TweakViewTestIndividual(TweakViewTestsMixin, TestCase):  # Individual

    def setUp(self):
        super(TweakViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.igp = CowlIndividualGarmentParametersFactory(user=self.user)
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
        kwargs["swatch"] = kwargs.get("swatch", SwatchFactory(user=self.user))
        ps = CowlPatternSpecFactory(**kwargs)
        ps.save()
        igp = CowlIndividualGarmentParameters.make_from_patternspec(self.user, ps)
        igp.save()
        return igp

    def _get_expected_header(self, igp):
        return "<h2>Customize sizing specifics</h2>"

    def test_tweak_page_contains_header(self):
        self.login()
        response = self._get_tweak_page()
        self.assertContains(response, self._get_expected_header(self.igp), html=True)


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
        self.driver.implicitly_wait(2)

        self.user = UserFactory()

        self.swatch = SwatchFactory(user=self.user)

        self.igp = CowlIndividualGarmentParametersFactory(
            user=self.user,
            pattern_spec__swatch=self.swatch,
            pattern_spec__user=self.user,
        )

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

    def _inner_icon_test(self, step_amt, delta, direction):
        height = self.driver.find_element(By.ID, "id_height")
        circ = self.driver.find_element(By.ID, "id_circumference")

        orig_value_height = height.get_attribute("value")
        orig_value_circ = circ.get_attribute("value")

        # press height button
        icon = self.driver.find_element(By.ID, "glyphicon-div_id_height-" + direction)
        self._click_button(icon)

        # Height should have changed, circ not

        new_value_height = height.get_attribute("value")
        new_value_circ = circ.get_attribute("value")

        self.assertAlmostEqual(
            float(orig_value_height) + step_amt, float(new_value_height), delta=delta
        )
        self.assertEqual(new_value_circ, orig_value_circ)

        # press circ button
        icon = self.driver.find_element(
            By.ID, "glyphicon-div_id_circumference-" + direction
        )
        self._click_button(icon)

        # height and circ should have both changed

        new_value_height = height.get_attribute("value")
        new_value_circ = circ.get_attribute("value")

        self.assertAlmostEqual(
            float(orig_value_height) + step_amt, float(new_value_height), delta=delta
        )
        self.assertAlmostEqual(
            float(orig_value_circ) + step_amt, float(new_value_circ), delta=delta
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

    def test_restore_button_restores(self):
        # Make a new version of the IGP, and remember the original value
        orig_value = self.igp.height
        self.igp.height += 0.25
        self.igp.save()

        # Reload the page
        self._get(reverse("design_wizard:tweak", args=(self.igp.id,)))

        # Make sure you see the new value
        height = self.driver.find_element(By.ID, "id_height")
        current_value = height.get_attribute("value")
        self.assertEqual(str(current_value), str(self.igp.height))
        self.assertNotEqual(current_value, orig_value)

        # Click the restore button and make sure you see the original value
        restore_button = self.driver.find_element(By.ID, "button-id-restore")
        self._click_button(restore_button)

        post_restore_value = height.get_attribute("value")
        self.assertEqual(float(post_restore_value), float(orig_value))


class RedoTweakViewTestsIndividual(TweakViewTestIndividual):

    def setUp(self):
        self.pattern = ApprovedCowlPatternFactory()
        self.user = self.pattern.user

        pspec = self.pattern.get_spec_source()
        redo = CowlRedoFactory(
            swatch=pspec.swatch,
            circumference=CDC.COWL_CIRC_MEDIUM,
            height=CDC.COWL_HEIGHT_AVERAGE,
            pattern=self.pattern,
        )
        redo.save()
        redo_igp = CowlIndividualGarmentParameters.make_from_redo(self.user, redo)
        redo_igp.save()
        self.igp = redo_igp

        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    # def _make_igp(self, **kwargs):
    #     kwargs['user'] = kwargs.get('user', self.user)
    #     user = kwargs['user']
    #     kwargs['body'] = kwargs.get('body', BodyFactory(user = self.user))
    #     kwargs['swatch'] = kwargs.get('swatch', SwatchFactory(user = self.user))
    #     pspec = CowlPatternSpecFactory(**kwargs)
    #     pspec.save()
    #     p = .from_pspec(pspec)
    #
    #     redo = Redo(body = pspec.body,
    #                 swatch = pspec.swatch,
    #                 garment_fit = pspec.garment_fit,
    #                 torso_length = pspec.torso_length,
    #                 sleeve_length = pspec.sleeve_length,
    #                 neckline_depth = pspec.neckline_depth,
    #                 neckline_depth_orientation = pspec.neckline_depth_orientation,
    #                 pattern = p)
    #     redo.save()
    #     igp = make_IGP_from_redo(self.user, redo)
    #     igp.save()
    #     return igp

    def _tweak_url(self, igp):
        return reverse("design_wizard:redo_tweak", args=(igp.id,))

    def _make_summary_url(self, igp):
        summary_url = reverse("design_wizard:redo_approve", args=(self.igp.id,))
        return summary_url

    def _get_tweak_form_class(self):
        return TweakCowlRedoIndividualGarmentParameters

    def _get_expected_header(self, igp):
        pattern_name = igp.redo.pattern.name
        return "<h2>Customize fit specifics for your %s redo</h2>" % pattern_name

    #     # #######################################################################################
    #     #
    #     # Shadowing tests of same name in superclasses
    #     #
    #     # #######################################################################################

    def test_error_igp_patternspec_has_wrong_owner(self):
        self.igp.redo.pattern.user = self.user2
        self.igp.redo.pattern.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(self._tweak_url(self.igp))
