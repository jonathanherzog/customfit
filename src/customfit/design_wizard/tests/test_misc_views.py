# -*- coding: utf-8 -*-

import datetime
import logging

from django.test import TestCase
from django.urls import reverse

import customfit.designs.helpers.design_choices as DC
from customfit.designs.factories import DesignFactory
from customfit.designs.models import Collection
from customfit.userauth.factories import UserFactory

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ChooseDesignTypeViewTest(TestCase):  # Individual
    """
    Verifies that choose type displays only for logged in users
    """

    def setUp(self):
        super(ChooseDesignTypeViewTest, self).setUp()
        self.user = UserFactory()

    def tearDown(self):
        self.user.delete()
        super(ChooseDesignTypeViewTest, self).tearDown()

    def login(self):
        return self.client.force_login(self.user)

    def test_not_logged_in_redirects(self):
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertEqual(response.status_code, 302)

    def test_logged_in_displays(self):
        self.login()
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertEqual(response.status_code, 200)

    def test_collections_behave(self):
        # We were getting wierd errors when the latest collection had no
        # visible designs. Let's test that it now does the right thing.

        # we will need this later
        one_week = datetime.timedelta(weeks=1)

        # Sanity-test:
        self.assertFalse(Collection.objects.exists())
        self.login()

        # Does the page omit mention of collections when no collections exist?
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertNotContains(response, "The latest collection")
        self.assertNotContains(response, "see all collections")

        # Does the page omit mention of collections when no visible collections
        # exist?
        collection1 = Collection(name="1")
        collection1.save()
        design1 = DesignFactory(visibility=DC.PRIVATE, collection=collection1)
        design1.save()
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertNotContains(response, "The latest collection")
        self.assertNotContains(response, "see all collections")

        # Does the page mention collections when a visible collection exists?
        # (note that we need to force the value of creation_date to ensure that
        # latest() will act as expected during unit tests
        collection2 = Collection(name="2")
        collection2.save()
        collection2.creation_date = collection1.creation_date + one_week
        collection2.save()
        design2 = DesignFactory(visibility=DC.PUBLIC, collection=collection2)
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertEqual(Collection.objects.latest(), collection2)  # sanity check
        self.assertContains(response, "The latest collection")
        self.assertContains(response, "see all collections")
        self.assertContains(response, design2.name)

        # Does the page continue to mention collections when a visible
        # collection exists, even if the latest is not visible? Note that we
        # need to set creation_date manually to ensure that latest() will
        # work as expected during unit test
        collection3 = Collection(name="3")
        collection3.save()
        collection3.creation_date = collection2.creation_date + one_week
        collection3.save()
        design3 = DesignFactory(visibility=DC.PRIVATE, collection=collection3)
        design3.save()
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertEqual(Collection.objects.latest(), collection3)  # sanity check
        self.assertContains(response, "The latest collection")
        self.assertContains(response, "see all collections")
        self.assertContains(response, design2.name)

    def test_make_your_own(self):
        self.login()
        response = self.client.get(reverse("design_wizard:choose_type"))
        self.assertContains(response, "<h2>Build your own design</h2>")
        self.assertContains(
            response,
            """
                <a href="/design/custom/sweaters/">
                    <img src="/static/img/byo-sweater-image.png" class="choose-design-hero">
                    <p>Make your own sweater</p>
                </a>""",
        )
        self.assertContains(
            response,
            """
                <a href="/design/custom/cowls/">
                    <img src="/static/img/byo-cowl-image.png" class="choose-design-hero">
                    <p>Make your own cowl</p>
                </a>""",
        )
