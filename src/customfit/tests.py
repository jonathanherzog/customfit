import datetime
import logging
import unittest.mock as mock
from urllib.parse import urljoin

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import (
    LiveServerTestCase,
    RequestFactory,
    TestCase,
    override_settings,
    tag,
)
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from seleniumlogin import force_login

import customfit.designs.helpers.design_choices as DC
import customfit.views
from customfit.designs.factories import DesignFactory
from customfit.designs.models import Collection, Design
from customfit.test_garment.factories import (
    TestApprovedIndividualPatternFactory,
    TestApprovedIndividualPatternWithBodyFactory,
)
from customfit.userauth.factories import StaffFactory, UserFactory

# Get an instance of a logger
logger = logging.getLogger(__name__)


class ViewHelperTests(TestCase):

    def test_get_designs(self):

        # Sanity-check
        self.assertFalse(Design.objects.exists())

        # Test when no promoted designs
        self.assertIsNone(customfit.views._get_designs(1))

        # Add some designs
        image = SimpleUploadedFile("image.jpg", b"contents")

        design1 = DesignFactory(visibility=DC.FEATURED, image=image)
        design1.save()

        design2 = DesignFactory(visibility=DC.FEATURED, image=image)
        design2.save()

        design3 = DesignFactory(visibility=DC.FEATURED, image=image)
        design3.save()

        # Add a collection
        collection_latest = Collection(name="latest")
        collection_latest.save()
        design4 = DesignFactory(
            visibility=DC.PUBLIC, image=image, collection=collection_latest
        )
        design4.save()

        design5 = DesignFactory(
            visibility=DC.PUBLIC, image=image, collection=collection_latest
        )
        design5.save()

        # Add a second, older collection
        collection_older = Collection(name="older")
        collection_older.save()
        collection_older.creation_date = (
            collection_latest.creation_date - datetime.timedelta(weeks=1)
        )
        collection_older.save()
        design6 = DesignFactory(
            visibility=DC.PUBLIC, image=image, collection=collection_older
        )
        design6.save()

        design7 = DesignFactory(
            visibility=DC.PUBLIC, image=image, collection=collection_older
        )
        design7.save()

        # Sanity-check set-up
        self.assertIn(collection_older, Collection.displayable.all())
        self.assertIn(collection_latest, Collection.displayable.all())
        self.assertEqual(Collection.displayable.latest(), collection_latest)

        # sanity-check the manager
        self.assertEqual(Design.currently_promoted.count(), 5)

        # If we ask for three promoted designs, we should get three
        # distinct ones. Check this multiple times to account for randomness
        for _ in range(100):
            three = customfit.views._get_designs(3)
            self.assertEqual(len(three), 3)
            self.assertNotEqual(three[0], three[1])
            self.assertNotEqual(three[0], three[2])
            self.assertNotEqual(three[1], three[2])
            for design in three:
                self.assertIn(
                    design,
                    [design1, design2, design3, design4, design5, design6, design7],
                )

        # If we ask for 1000 promoted designs, we should get 1000 with repeats,
        # but with the duplicates spaced as far apart as possible. Specifically,
        # we should test that all seven designs were used, and  no design is
        # repeated in the same consecutive seven entires
        lots = customfit.views._get_designs(1000)
        self.assertEqual(len(lots), 1000)
        self.assertEqual((len(set(lots))), 7)
        for index in range(0, 1000 - 7):
            self.assertNotEqual(lots[index], lots[index + 1])
            self.assertNotEqual(lots[index], lots[index + 2])
            self.assertNotEqual(lots[index], lots[index + 3])
            self.assertNotEqual(lots[index], lots[index + 4])
            self.assertNotEqual(lots[index], lots[index + 5])
            self.assertNotEqual(lots[index], lots[index + 6])


class StaffPageViewTests(TestCase):

    def tearDown(self):
        self.client.logout()

    def test_staff_page(self):

        staff_url = reverse("staff")
        redirect_url = reverse("admin:login") + "?next=/staff/"

        # staff page should not be visible to anonymous users. They will
        # be directed to the login page
        anon_response = self.client.get(staff_url)
        self.assertRedirects(anon_response, redirect_url)

        # staff page should not be visible to ordinary user
        user = UserFactory()
        user.save()
        self.client.force_login(user)
        user_response = self.client.get(staff_url)
        self.assertRedirects(anon_response, redirect_url)
        self.client.logout()
        user.delete()

        # Staff should be able to see it
        staff = StaffFactory()
        self.client.force_login(staff)
        staff_response = self.client.get(staff_url)
        self.assertContains(staff_response, "Staff Stuff")
        staff.delete()


class IndividualHomePageTest(TestCase):

    def setUp(self):
        super(IndividualHomePageTest, self).setUp()
        self.user = UserFactory()

    def tearDown(self):
        self.user.delete()
        super(IndividualHomePageTest, self).tearDown()

    def test_home_view_new(self):
        self.client.force_login(self.user)
        home_url = reverse("home_view")
        response = self.client.get(home_url)
        self.assertTemplateUsed(response, "knitter_home.html")
        context = response.context
        self.assertIn("measure_url", context)
        self.assertEqual(context["measure_url"], reverse("bodies:body_create_view"))
        self.assertIn("swatch_url", context)
        self.assertEqual(context["swatch_url"], reverse("swatches:swatch_create_view"))
        self.assertIn("knit_url", context)
        self.assertEqual(
            context["knit_url"], reverse("patterns:individualpattern_list_view")
        )

    def test_home_view_has_objects_with_body(self):

        self.client.force_login(self.user)
        home_url = reverse("home_view")

        pattern = TestApprovedIndividualPatternWithBodyFactory.for_user(self.user)
        response = self.client.get(home_url)
        self.assertTemplateUsed(response, "knitter_home.html")
        context = response.context
        self.assertIn("measure_url", context)
        self.assertEqual(context["measure_url"], reverse("bodies:body_list_view"))
        self.assertIn("swatch_url", context)
        self.assertEqual(context["swatch_url"], reverse("swatches:swatch_list_view"))
        self.assertIn("knit_url", context)
        self.assertEqual(
            context["knit_url"], reverse("patterns:individualpattern_list_view")
        )

    def test_home_view_has_objects_no_body(self):

        self.client.force_login(self.user)
        home_url = reverse("home_view")

        pattern = TestApprovedIndividualPatternFactory.for_user(self.user)
        response = self.client.get(home_url)
        self.assertTemplateUsed(response, "knitter_home.html")
        context = response.context
        self.assertIn("measure_url", context)
        self.assertIn("swatch_url", context)
        self.assertEqual(context["swatch_url"], reverse("swatches:swatch_list_view"))
        self.assertIn("knit_url", context)
        self.assertEqual(
            context["knit_url"], reverse("patterns:individualpattern_list_view")
        )

        self.assertEqual(context["measure_url"], reverse("bodies:body_create_view"))


class AwesomeViewTest(TestCase):

    def test_anon_visibility(self):
        # Test that the page is visible to anonymous users
        urls_to_test = [reverse("awesome")]
        for url in urls_to_test:
            self.client.logout()
            response = self.client.get(url, follow=False)
            self.assertEqual(response.status_code, 200, url)


@tag("selenium")
class ErrorPageTests(LiveServerTestCase):

    # Becuase of the way the Django test client is written, we need to test
    # the 500 page with selenium. (The test client will merely pass on the underlying
    # exception.

    def setUp(self):
        super(ErrorPageTests, self).setUp()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)

        self.user = StaffFactory()

        # Log in
        force_login(self.user, self.driver, self.live_server_url)

        error_url = reverse("force_error_page")
        self.full_url = ull_url = urljoin(self.live_server_url, error_url)

    def tearDown(self):
        self.driver.quit()
        super(ErrorPageTests, self).tearDown()

    def test_error_page(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="foo@example.com"):
            self.driver.get(self.full_url)
        html = self.driver.page_source
        self.assertInHTML("<p>Something went wrong!</p>", html)


class RobotsTxtTests(TestCase):

    def test_can_get_robots_txt1(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")

    def test_can_get_robots_txt2(self):
        response = self.client.get("/robots.txt/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")


class TestCeleryAccessToCache(TestCase):

    def test_check_cache(self):
        self.user = StaffFactory()
        self.client.force_login(self.user)
        test_url = reverse("test_cache_view")
        response = self.client.get(test_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<p>Success!</p>", html=True)
