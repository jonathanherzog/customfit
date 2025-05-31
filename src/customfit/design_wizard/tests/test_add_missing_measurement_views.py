# -*- coding: utf-8 -*-

import logging

from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse

from customfit.bodies.factories import BodyFactory, SimpleBodyFactory
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.garment_parameters.factories import IndividualGarmentParameters
from customfit.swatches.factories import SwatchFactory
from customfit.test_garment.factories import (
    TestDesignWithBodyFactory,
    TestIndividualPatternWithBodyFactory,
    TestPatternSpecWithBodyFactory,
    TestRedoWithBodyFactory,
)
from customfit.test_garment.models import TestGarmentParametersWithBody
from customfit.userauth.factories import UserFactory

from .helpers import SessionTestingMixin

# Get an instance of a logger
logger = logging.getLogger(__name__)


class AddMissingMeasurementsPatternspecTestMixin(object):

    # Written as a mixin to keep py.test from running the tests in here directly, and not
    # only in sub-classes. (Nose, how I miss you...)
    #
    # Expects sub-classes to implement:
    #
    # * setUp, setting self.user, self.user2, self.body & self.swatch, and calling _set_up_designs()
    # * login()

    def _set_up_designs(self):

        self.design = TestDesignWithBodyFactory()
        self.url = reverse(
            "design_wizard:personalize", kwargs={"design_slug": self.design.slug}
        )

    def _get_final_url(self, response):
        """
        Gets the URL of (the final element in the redirect chain of) a response
        returned by a client.post() request. This function exists just to make
        the code more readable.
        """
        return response.redirect_chain[-1][0]

    # Tests of the AddMissingMeasurements page itself
    # --------------------------------------------------------------------------

    def test_add_missing_form_exists(self):
        """
        There is a form allowing users to add missing measurements, and it
        solicits exactly the missing set of measurements.
        """
        self.login()

        # sanity check-- these are the ones TestGarmentParams are defined to want
        self.assertIsNone(self.simple_body.elbow_circ)
        self.assertIsNone(self.simple_body.forearm_circ)
        self.assertIsNotNone(self.simple_body.bicep_circ)
        self.assertIsNotNone(self.simple_body.wrist_circ)

        data = {
            "user": self.user,
            "name": "foo",
            "body": self.simple_body,
            "swatch": self.swatch,
        }

        pspec = TestPatternSpecWithBodyFactory(**data)
        url = reverse(
            "design_wizard:missing", kwargs={"pk": pspec.pk, "action": "tweak"}
        )

        resp = self.client.get(url)

        # This catches only the missing measurements form; the use-defaults form
        # is coded straight into the template since it does not vary.
        form = resp.context["form"]

        self.assertEqual(set(form.fields), set(["elbow_circ", "forearm_circ"]))

    def test_add_missing_form_adds_measurements(self):
        """
        Submitting a valid add-missing form actually adds the submitted
        measurements to the body.
        """
        self.login()

        data = {
            "user": self.user,
            "name": "foo",
            "body": self.simple_body,
            "swatch": self.swatch,
        }

        pspec = TestPatternSpecWithBodyFactory(**data)
        url = reverse(
            "design_wizard:missing", kwargs={"pk": pspec.pk, "action": "tweak"}
        )

        resp = self.client.post(
            url,
            {
                "redirect_": "continue with these measurements",
                "elbow_circ": 10,
                "forearm_circ": 8,
            },
        )
        body = self.simple_body
        body.refresh_from_db()

        self.assertEqual(body.elbow_circ, 10)
        self.assertEqual(body.forearm_circ, 8)

    def test_add_missing_knows_metric(self):
        """
        Adding measurements in cm through the add-missing form works, too.
        """
        self.login()
        self.user.profile.display_imperial = False
        self.user.profile.save()

        data = {
            "user": self.user,
            "name": "foo",
            "body": self.simple_body,
            "swatch": self.swatch,
        }
        pspec = TestPatternSpecWithBodyFactory(**data)
        url = reverse(
            "design_wizard:missing", kwargs={"pk": pspec.pk, "action": "tweak"}
        )

        resp = self.client.post(
            url,
            {
                "redirect_approve": "continue with these measurements",
                "elbow_circ": 25.4,
                "forearm_circ": 25.4,
            },
        )

        body = self.simple_body
        body.refresh_from_db()

        self.assertAlmostEqual(body.elbow_circ, 10, places=1)
        self.assertAlmostEqual(body.forearm_circ, 10, places=1)

    def test_add_missing_requires_login(self):
        """
        If an anon user hits the AddMissingMeasurementsView, they are redirected
        to the login page.
        """
        pspec = TestPatternSpecWithBodyFactory(body=self.simple_body, user=self.user2)

        url = reverse("design_wizard:missing", kwargs={"pk": pspec.pk})

        # Anonymous user is redirected to the login page.
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 302)
        goal_url = reverse("userauth:login") + "?next=" + url
        self.assertRedirects(resp, goal_url, fetch_redirect_response=False)

    def test_with_design_origin(self):
        self.login()

        pspec = TestPatternSpecWithBodyFactory(
            user=self.user,
            body=self.body,
            swatch=self.swatch,
            design_origin=self.design,
        )
        add_missing_url = reverse(
            "design_wizard:missing", kwargs={"action": "summary", "pk": pspec.pk}
        )

        resp = self.client.get(add_missing_url)
        self.assertEqual(resp.status_code, 200)

    def test_no_design_origin(self):
        self.login()

        pspec = TestPatternSpecWithBodyFactory(
            user=self.user, body=self.body, swatch=self.swatch, design_origin=None
        )
        add_missing_url = reverse(
            "design_wizard:missing", kwargs={"action": "summary", "pk": pspec.pk}
        )

        resp = self.client.get(add_missing_url)
        self.assertEqual(resp.status_code, 200)


class AddMissingMeasurementsPatternspecTestIndividual(
    TestCase, AddMissingMeasurementsPatternspecTestMixin
):  # Individual

    def setUp(self):
        super(AddMissingMeasurementsPatternspecTestIndividual, self).setUp()
        self.user = UserFactory()
        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)
        self.simple_body = SimpleBodyFactory(user=self.user)
        self._set_up_designs()
        self.user2 = UserFactory()

        self.ps = TestPatternSpecWithBodyFactory(
            user=self.user, body=self.body, swatch=self.swatch
        )
        self.ps.save()

    def login(self):
        self.client.force_login(self.user)

    # Ownership consistency checks
    def test_patternspec_wrong_owner(self):
        self.ps.user = self.user2
        self.ps.save()
        url = reverse("design_wizard:missing", args=(self.ps.id,))
        self.login()
        response = self.client.get(url)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_patternspec_swatch_wrong_owner(self):
        self.ps.swatch.user = self.user2
        self.ps.swatch.save()
        url = reverse("design_wizard:missing", args=(self.ps.id,))
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            self.client.get(url)


class AddMissingMeasurementsRedoTestMixin(object):

    # Written as a mixin to keep py.test from running the tests in here directly, and not
    # only in sub-classes. (Nose, how I miss you...)
    #
    # Expects sub-classes to implement:
    #
    # * setUp, setting self.user, self.user2, self.redo, self.tweak_url, self.summary_url
    # * login()

    # Unfortuantely, it didn't make sense to factor out AddMissingMeasurementsTestMixin into
    # tests common to patternspec and redo. It was just too hard-coded to be about patternspec

    def _get_final_url(self, response):
        """
        Gets the URL of (the final element in the redirect chain of) a response
        returned by a client.post() request. This function exists just to make
        the code more readable.
        """
        return response.redirect_chain[-1][0]

    # Tests of workflow surrounding the AddMissingMeasurements page
    # --------------------------------------------------------------------------

    def test_submit_button_tweak(self):
        """
        The add-missing-measurements button remembers the user's choice of
        purchase vs tweak, too.
        """
        self.login()

        resp = self.client.get(self.tweak_url)
        # We have to actually get the button as it appears in the page,
        # because if we simply post data with redirect_approve or redirect_tweak,
        # we will trigger the correct response in the back end - but entirely
        # skip checking whether the user saw appropriate options!
        soup = BeautifulSoup(resp.content, "html5lib")
        inpt = soup.findAll(
            "input", attrs={"value": "continue with these measurements"}
        )[0]

        resp2 = self.client.post(
            self.tweak_url,
            {
                inpt.get("name"): "continue with these measurements",
                "elbow_circ": self.body.elbow_circ,
                "forearm_circ": self.body.forearm_circ,
            },
            follow=False,
        )

        new_igp = IndividualGarmentParameters.objects.filter(redo=self.redo).get()
        self.assertRedirects(
            resp2,
            reverse("design_wizard:redo_tweak", args=(new_igp.id,)),
            fetch_redirect_response=False,
        )

    def test_submit_button_approve(self):
        """
        The add-missing-measurements button remembers the user's choice of
        purchase vs tweak, too.
        """
        self.login()

        resp = self.client.get(self.summary_url)
        # We have to actually get the button as it appears in the page,
        # because if we simply post data with redirect_approve or redirect_tweak,
        # we will trigger the correct response in the back end - but entirely
        # skip checking whether the user saw appropriate options!
        soup = BeautifulSoup(resp.content, "html5lib")
        inpt = soup.findAll(
            "input", attrs={"value": "continue with these measurements"}
        )[0]

        resp2 = self.client.post(
            self.summary_url,
            {
                inpt.get("name"): "continue with these measurements",
                "elbow_circ": self.body.elbow_circ,
                "forearm_circ": self.body.forearm_circ,
            },
            follow=False,
        )

        new_igp = IndividualGarmentParameters.objects.filter(redo=self.redo).get()
        self.assertRedirects(
            resp2,
            reverse("design_wizard:redo_approve", args=(new_igp.id,)),
            fetch_redirect_response=False,
        )

    # Tests of the AddMissingMeasurements page itself
    # --------------------------------------------------------------------------

    def test_add_missing_form_exists(self):
        """
        There is a form allowing users to add missing measurements, and it
        solicits exactly the missing set of measurements.
        """
        self.login()

        resp = self.client.get(self.tweak_url)

        # This catches only the missing measurements form; the use-defaults form
        # is coded straight into the template since it does not vary.
        form = resp.context["form"]

        missing_fields = TestGarmentParametersWithBody.missing_body_fields(self.redo)

        self.assertEqual(set(form.fields), set(field.name for field in missing_fields))

    def test_add_missing_form_adds_measurements(self):
        """
        Submitting a valid add-missing form actually adds the submitted
        measurements to the body.
        """
        self.login()

        _ = self.client.post(
            self.summary_url,
            {
                "approve_redo": "continue with these measurements",
                "elbow_circ": 10,
                "forearm_circ": 10,
            },
        )
        body = self.simple_body
        body.refresh_from_db()

        self.assertEqual(body.elbow_circ, 10)
        self.assertEqual(body.forearm_circ, 10)

    def test_add_missing_knows_metric(self):
        """
        Adding measurements in cm through the add-missing form works, too.
        """
        self.login()
        self.user.profile.display_imperial = False
        self.user.profile.save()

        self.client.post(
            self.summary_url,
            {
                "approve_redo": "continue with these measurements",
                "elbow_circ": 25.4,
                "forearm_circ": 25.4,
            },
        )

        body = self.simple_body
        body.refresh_from_db()

        self.assertAlmostEqual(body.elbow_circ, 10, places=1)
        self.assertAlmostEqual(body.forearm_circ, 10, places=1)

    def test_get(self):
        self.login()

        add_missing_url = reverse(
            "design_wizard:redo_plus_missing", kwargs={"pk": self.redo.pk}
        )

        resp = self.client.get(add_missing_url)
        self.assertEqual(resp.status_code, 200)


class AddMissingMeasurementsRedoTestIndividual(
    TestCase, AddMissingMeasurementsRedoTestMixin
):  # Individual

    def setUp(self):
        super(AddMissingMeasurementsRedoTestIndividual, self).setUp()
        self.user = UserFactory()
        self.body = BodyFactory(user=self.user)
        self.simple_body = SimpleBodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)

        self.user2 = UserFactory()

        self.pattern = TestIndividualPatternWithBodyFactory.for_user(self.user)
        pspec = self.pattern.get_spec_source()
        self.redo = TestRedoWithBodyFactory.from_original_pspec(
            pspec, swatch=self.swatch, body=self.simple_body
        )
        self.assertEqual(self.redo.pattern.user, self.user)
        self.assertEqual(self.redo.pattern.get_spec_source().user, self.user)
        self.tweak_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": self.redo.id, "action": "tweak"}
        )
        self.summary_url = reverse(
            "design_wizard:missing_redo",
            kwargs={"pk": self.redo.id, "action": "summary"},
        )

    def login(self):
        return self.client.force_login(self.user)

    # Ownership consistency checks
    def test_pattern_wrong_owner(self):
        self.redo.pattern.user = self.user2
        self.redo.pattern.save()
        self.login()
        response = self.client.get(self.summary_url)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_swatch_wrong_owner(self):
        self.redo.swatch.user = self.user2
        self.redo.swatch.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(self.summary_url)
