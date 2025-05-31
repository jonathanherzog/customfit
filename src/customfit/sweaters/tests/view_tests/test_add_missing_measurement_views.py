# -*- coding: utf-8 -*-

import logging
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from django.test import TestCase
from django.urls import reverse

from customfit.bodies.factories import BodyFactory, SimpleBodyFactory
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.swatches.factories import SwatchFactory
from customfit.userauth.factories import UserFactory

from ...factories import (
    SweaterDesignFactory,
    SweaterPatternFactory,
    SweaterPatternSpecFactory,
    SweaterRedoFactory,
    VestDesignFactory,
)
from ...helpers import sweater_design_choices as SDC

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

        self.hourglass_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_HOURGLASS,
            # silhouette_hourglass_allowed=True,
            silhouette_straight_allowed=False,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        self.straight_design = SweaterDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_hourglass_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )
        self.straight_vest_design = VestDesignFactory(
            primary_silhouette=SDC.SILHOUETTE_STRAIGHT,
            silhouette_hourglass_allowed=False,
            silhouette_straight_allowed=True,
            silhouette_aline_allowed=False,
            silhouette_tapered_allowed=False,
        )

        self.hourglass_url = reverse(
            "design_wizard:personalize",
            kwargs={"design_slug": self.hourglass_design.slug},
        )
        self.straight_url = reverse(
            "design_wizard:personalize",
            kwargs={"design_slug": self.straight_design.slug},
        )
        self.straight_vest_url = reverse(
            "design_wizard:personalize",
            kwargs={"design_slug": self.straight_vest_design.slug},
        )

    def _get_final_url(self, response):
        """
        Gets the URL of (the final element in the redirect chain of) a response
        returned by a client.post() request. This function exists just to make
        the code more readable.
        """
        return response.redirect_chain[-1][0]

    # Tests of workflow surrounding the AddMissingMeasurements page
    # --------------------------------------------------------------------------

    # In theory, this test is testing general-purpose logic. But the machinery
    # we would need to test it with test_garment is just too much to be worth
    # it. So we're testing it in sweaters instead.
    def test_add_missing_page_remembers_original_goal(self):
        """
        The add-missing-measurements button remembers the user's choice of
        purchase vs tweak, too.
        """
        self.login()

        data = {
            "name": "foo",
            "body": self.simple_body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_WOMENS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_STRAIGHT,
            "sleeve_length": SDC.SLEEVE_ELBOW,
            "torso_length": SDC.MED_HIP_LENGTH,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "redirect_approve": "Get this pattern!",
        }

        resp = self.client.post(self.straight_url, data, follow=True)

        # We have to actually get the button as it appears in the page,
        # because if we simply post data with redirect_approve or redirect_tweak,
        # we will trigger the correct response in the back end - but entirely
        # skip checking whether the user saw appropriate options!
        soup = BeautifulSoup(resp.content, "html5lib")
        inpt = soup.findAll(
            "input", attrs={"value": "continue with these measurements"}
        )[0]

        resp2 = self.client.post(
            self._get_final_url(resp),
            {
                inpt.get("name"): "continue with these measurements",
                "armpit_to_elbow_sleeve": 6,
                "elbow_circ": 10,
            },
            follow=True,
        )

        resp_path = urlparse(self._get_final_url(resp2)).path
        self.assertTrue(resp_path.startswith("/design/summary"))

        data = {
            "name": "foo",
            "body": self.simple_body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_WOMENS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_STRAIGHT,
            "sleeve_length": SDC.SLEEVE_THREEQUARTER,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "torso_length": SDC.MED_HIP_LENGTH,
            "redirect_tweak": "customize fit specifics",
        }

        resp = self.client.post(self.straight_url, data, follow=True)

        soup = BeautifulSoup(resp.content, "html5lib")
        inpt = soup.findAll(
            "input", attrs={"value": "continue with these measurements"}
        )[0]

        resp2 = self.client.post(
            self._get_final_url(resp),
            {
                inpt.get("name"): "continue with these measurements",
                "armpit_to_three_quarter_sleeve": 10,
                "forearm_circ": 10,
            },
            follow=True,
        )

        resp_path = urlparse(self._get_final_url(resp2)).path
        self.assertTrue(resp_path.startswith("/design/tweak"))


class AddMissingMeasurementsPatternspecTestIndividual(
    TestCase, AddMissingMeasurementsPatternspecTestMixin
):  # Individual

    def setUp(self):
        super(AddMissingMeasurementsPatternspecTestIndividual, self).setUp()
        self.ps = SweaterPatternSpecFactory()
        self.user = self.ps.user
        self.body = self.ps.body
        self.swatch = self.ps.swatch
        self.simple_body = SimpleBodyFactory(user=self.user)
        self._set_up_designs()
        self.user2 = UserFactory()

        self.ps.save()

    def login(self):
        self.client.force_login(self.user)

    # # Ownership consistency checks
    # def test_patternspec_wrong_owner(self):
    #     self.ps.user = self.user2
    #     self.ps.save()
    #     url = reverse("design_wizard:missing", args=(self.ps.id,))
    #     self.login()
    #     response = self.client.get(url)
    #     self.assertContains(response,
    #                         "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)

    def test_patternspec_body_wrong_owner(self):
        self.ps.body.user = self.user2
        self.ps.body.save()
        url = reverse("design_wizard:missing", args=(self.ps.id,))
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(url)

    #
    # def test_patternspec_swatch_wrong_owner(self):
    #     self.ps.swatch.user = self.user2
    #     self.ps.swatch.save()
    #     url = reverse("design_wizard:missing", args=(self.ps.id,))
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         self.client.get(url)


class AddMissingMeasurementsRedoTestMixin(object):
    pass


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

        self.pattern = SweaterPatternFactory.for_user(self.user)
        pspec = self.pattern.get_spec_source()
        self.redo = SweaterRedoFactory.from_original_pspec(
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

    # # Ownership consistency checks
    # def test_pattern_wrong_owner(self):
    #     self.redo.pattern.user = self.user2
    #     self.redo.pattern.save()
    #     self.login()
    #     response = self.client.get(self.summary_url)
    #     self.assertContains(response,
    #                         "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)

    def test_body_wrong_owner(self):
        self.redo.body.user = self.user2
        self.redo.body.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(self.summary_url)

    # def test_swatch_wrong_owner(self):
    #     self.redo.swatch.user = self.user2
    #     self.redo.swatch.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         response = self.client.get(self.summary_url)
    #
