import logging
import re
from urllib.parse import urljoin

from django.test import LiveServerTestCase, RequestFactory, TestCase, tag
from django.test.client import Client
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from seleniumlogin import force_login

from customfit.bodies.factories import BodyFactory
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.patterns.models import Redo
from customfit.swatches.factories import SwatchFactory
from customfit.test_garment.factories import (
    TestApprovedIndividualPatternFactory,
    TestDesignFactory,
    TestIndividualGarmentParametersFactory,
    TestIndividualPatternFactory,
    TestPatternSpecFactory,
    TestRedoFactory,
    TestRedonePatternFactory,
)
from customfit.test_garment.forms import (
    TweakTestIndividualGarmentParameters,
    TweakTestRedoIndividualGarmentParameters,
)
from customfit.test_garment.models import TestGarmentParameters
from customfit.userauth.factories import UserFactory

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
    #     TestPatternSpecFactory and return a (saved) IGP

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
        ps = TestPatternSpecFactory(**kwargs)
        ps.save()
        igp = TestGarmentParameters.make_from_patternspec(self.user, ps)
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
        for field in ["test_field"]:
            data[field] = getattr(self.igp, field) * conversion

        return data

    def _get_tweak_form_class(self):
        return TweakTestIndividualGarmentParameters

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

    def test_tweak_page_contains_form(self):
        self.login()
        response = self._get_tweak_page()
        self.assertIsInstance(response.context["form"], self._get_tweak_form_class())

    def test_continue_links_to_approval(self):
        """
        This page should contain a link, styled like a customfit button, that
        links to the summary-and-approval page for this IGP.
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

    # Note: this test is shadowed in the Redo tests, below
    def test_cant_tweak_igp_of_approved_pattern_get(self):
        p = TestApprovedIndividualPatternFactory.from_us(
            user=self.user, swatch=self.igp.swatch
        )
        igp = p.pieces.schematic.individual_garment_parameters
        self.login()
        url = self._tweak_url(igp)
        response = self.client.get(url)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    # Note: this test is shadowed in the Redo tests, below
    def test_cant_tweak_igp_of_approved_pattern_post(self):
        p = TestApprovedIndividualPatternFactory.from_us(
            user=self.user, swatch=self.igp.swatch
        )
        igp = p.pieces.schematic.individual_garment_parameters
        self.login()
        data = self._get_igp_data()
        url = self._tweak_url(igp)
        response = self.client.post(url, data, follow=False)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

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

    # This test is shadowed in the Redo tests, below
    def test_no_design_origin(self):
        self.login()

        resp = self._get_tweak_page()
        self.assertEqual(resp.status_code, 200)

    # This test is shadowed in the Redo tests, below
    def test_design_origin(self):
        design = TestDesignFactory()
        spec_source = self.igp.get_spec_source()
        spec_source.design_origin = design
        spec_source.save()

        self.login()

        resp = self._get_tweak_page()
        self.assertEqual(resp.status_code, 200)


class TweakViewTestIndividual(TweakViewTestsMixin, TestCase):  # Individual

    def setUp(self):
        super(TweakViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.igp = TestIndividualGarmentParametersFactory(user=self.user)
        # self.igp.body.user = self.user
        # self.igp.body.save()
        # self.igp.swatch.user = self.user
        # self.igp.swatch.save()
        # self.igp.save()
        # self.igp.pattern_spec.user = self.user
        # self.igp.pattern_spec.save()
        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def _test_response(self, response):
        return self._test_individual_response(response)

    def _make_igp(self, **kwargs):
        kwargs["user"] = kwargs.get("user", self.user)
        kwargs["body"] = kwargs.get("body", BodyFactory(user=self.user))
        kwargs["swatch"] = kwargs.get("swatch", SwatchFactory(user=self.user))
        ps = TestPatternSpecFactory(**kwargs)
        ps.save()
        igp = IndividualGarmentParameters.make_from_patternspec(self.user, ps)
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

        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)

        self.igp = TestIndividualGarmentParametersFactory(user=self.user)
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


class RedoTweakViewTestsMixin(object):
    # Additional tests for the redo-tweak page, or tests that need to shadow those
    # in TweakViewTestsMixin, above

    def test_no_design_origin(self):
        self.login()

        self._get_tweak_page()
        resp = self._get_tweak_page()
        self.assertEqual(resp.status_code, 200)

    def test_design_origin(self):
        design = TestDesignFactory()
        spec_source = self.igp.get_spec_source()
        spec_source.design_origin = design
        spec_source.save()

        self.login()

        resp = self._get_tweak_page()
        self.assertEqual(resp.status_code, 200)

    def test_cant_tweak_igp_of_approved_pattern_get(self):
        p = TestRedonePatternFactory.from_us(user=self.user, swatch=self.igp.swatch)
        igp = p.pieces.schematic.individual_garment_parameters
        igp.redo.swatch = self.igp.swatch
        igp.redo.save()
        self.login()
        url = self._tweak_url(igp)
        response = self.client.get(url)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_cant_tweak_igp_of_approved_pattern_post(self):
        p = TestApprovedIndividualPatternFactory.from_us(
            user=self.user, swatch=self.igp.swatch
        )
        igp = p.pieces.schematic.individual_garment_parameters
        self.login()
        data = self._get_igp_data()
        url = self._tweak_url(igp)
        response = self.client.post(url, data, follow=False)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )


class RedoTweakViewTestsIndividual(RedoTweakViewTestsMixin, TweakViewTestIndividual):

    def setUp(self):
        self.pattern = TestApprovedIndividualPatternFactory()
        self.user = self.pattern.user

        pspec = self.pattern.get_spec_source()
        redo = TestRedoFactory(swatch=pspec.swatch, pattern=self.pattern)
        redo.save()
        redo_igp = TestGarmentParameters.make_from_redo(self.user, redo)
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
        pspec = TestPatternSpecFactory(**kwargs)
        pspec.save()
        p = TestIndividualPatternFactory.from_pspec(pspec)

        redo = Redo(
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
        igp = _make_IGP_from_redo(self.user, redo)
        igp.save()
        return igp

    def _tweak_url(self, igp):
        return reverse("design_wizard:redo_tweak", args=(igp.id,))

    def _make_summary_url(self, igp):
        summary_url = reverse("design_wizard:redo_approve", args=(self.igp.id,))
        return summary_url

    def _get_tweak_form_class(self):
        return TweakTestRedoIndividualGarmentParameters

    def _get_expected_header(self, igp):
        pattern_name = igp.redo.pattern.name
        return "<h2>Customize fit specifics for your %s redo</h2>" % pattern_name

    # #######################################################################################
    #
    # Shadowing tests of same name in superclasses
    #
    # #######################################################################################

    def test_error_igp_patternspec_has_wrong_owner(self):
        self.igp.redo.pattern.user = self.user2
        self.igp.redo.pattern.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(self._tweak_url(self.igp))
