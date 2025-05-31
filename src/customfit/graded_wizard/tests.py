import datetime

from django.test import TestCase
from django.urls import reverse

import customfit.designs.helpers.design_choices as DC
from customfit.bodies.factories import GradeSetFactory
from customfit.stitches.tests import StitchFactory
from customfit.test_garment.factories import GradedTestPatternFactory, TestDesignFactory
from customfit.userauth.factories import StaffFactory, UserFactory


class AllDesignsViewTests(TestCase):

    def test_staff_required(self):
        # Anonymous
        self.client.logout()
        response = self.client.get(reverse("graded_wizard:choose_design"))
        self.assertEqual(response.status_code, 302)

        # regular user
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(reverse("graded_wizard:choose_design"))
        self.assertEqual(response.status_code, 302)

        # Staff
        self.client.logout()
        staff = StaffFactory()
        self.client.force_login(staff)
        response = self.client.get(reverse("graded_wizard:choose_design"))
        self.assertEqual(response.status_code, 200)

    def test_designs_listed(self):
        # Note that we create them out of order to test sorting in the page
        d1 = TestDesignFactory(name="design1", slug="design1")
        # Yes, even private designs should be listed
        d3 = TestDesignFactory(name="design3", slug="design3", visibility=DC.PRIVATE)
        d2 = TestDesignFactory(name="design2", slug="design2")

        staff = StaffFactory()
        self.client.force_login(staff)

        response = self.client.get(reverse("graded_wizard:choose_design"))
        url1 = reverse(
            "graded_wizard:make_graded_pattern", kwargs={"design_slug": d1.slug}
        )
        url2 = reverse(
            "graded_wizard:make_graded_pattern", kwargs={"design_slug": d2.slug}
        )
        url3 = reverse(
            "graded_wizard:make_graded_pattern", kwargs={"design_slug": d3.slug}
        )
        goal_html = """
        <ul>
        <li><a href="%s">design1</a></li>
        <li><a href="%s">design2</a></li>
        <li><a href="%s">design3</a></li>
        </ul>
        """ % (
            url1,
            url2,
            url3,
        )
        self.assertContains(response, goal_html, html=True)


class PersonalizeDesignViewTest(TestCase):
    def setUp(self):
        super(PersonalizeDesignViewTest, self).setUp()
        self.user = StaffFactory()
        self.stitch = StitchFactory()
        self.grade_set = GradeSetFactory(user=self.user)
        self.design = TestDesignFactory(name="Bar")
        self.personalize_url = reverse(
            "graded_wizard:make_graded_pattern", args=(self.design.slug,)
        )
        self.post_entries = {
            "name": "name",
            "grade_set": self.grade_set.pk,
            "row_gauge": 16,
            "stitch_gauge": 20,
            "stitch1": self.stitch.pk,
        }

    def login(self):
        return self.client.force_login(self.user)

    def _get_design_page(self, design):
        url = reverse("graded_wizard:make_graded_pattern", args=(design.slug,))
        resp = self.client.get(url)
        return resp

    def test_staff_required(self):
        # Anonymous
        self.client.logout()
        response = self.client.get(self.personalize_url)
        self.assertEqual(response.status_code, 302)

        # regular user
        user = UserFactory()
        self.client.force_login(user)
        response = self.client.get(self.personalize_url)
        self.assertEqual(response.status_code, 302)

        # Staff
        self.client.logout()
        staff = StaffFactory()
        self.client.force_login(staff)
        response = self.client.get(self.personalize_url)
        self.assertEqual(response.status_code, 200)

    def test_get_personalize_page_staff(self):
        self.login()
        response = self.client.get(self.personalize_url)
        print(response.content)
        self.assertContains(response, self.design.name, status_code=200)
        self.assertContains(
            response,
            "<title>Customize your <em>graded</em> {0}</title>".format(
                self.design.name
            ),
            html=True,
        )

    def test_design_page_visibility(self):

        # Staff should be able to personalize all designs, no matter what visibility
        self.login()

        private_design = TestDesignFactory(name="Private design", visibility=DC.PRIVATE)
        limited_design = TestDesignFactory(name="Limited design", visibility=DC.LIMITED)
        public_design = TestDesignFactory(name="Public design", visibility=DC.PUBLIC)
        featured_design = TestDesignFactory(
            name="Featured design", visibility=DC.FEATURED
        )

        private_design_basic = TestDesignFactory(
            name="Private design basic", is_basic=True, visibility=DC.PRIVATE
        )
        limited_design_basic = TestDesignFactory(
            name="Limited design basic", is_basic=True, visibility=DC.LIMITED
        )
        public_design_basic = TestDesignFactory(
            name="Public design basic", is_basic=True, visibility=DC.PUBLIC
        )
        featured_design_basic = TestDesignFactory(
            name="Featured design basic", is_basic=True, visibility=DC.FEATURED
        )

        designs = [
            private_design,
            limited_design,
            public_design,
            featured_design,
            private_design_basic,
            limited_design_basic,
            public_design_basic,
            featured_design_basic,
        ]

        for design in designs:
            resp = self._get_design_page(design)
            self.assertEqual(resp.status_code, 200, (design.name, resp.status_code))

    def test_staff_sees_personalize_form(self):
        self.login()

        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "sign up")
        self.assertContains(response, 'Stitch gauge<span class="asteriskField">*')

    def test_post(self):
        self.login()

        response = self.client.post(self.personalize_url, self.post_entries)
        self.assertEqual(response.status_code, 302)
        self.assertRegex(response["Location"], r"^/pattern/graded/\d+/$")

    def test_post_follow(self):
        self.login()

        response = self.client.post(
            self.personalize_url, self.post_entries, follow=True
        )
        self.assertEqual(response.status_code, 200)


class TestPatternListView(TestCase):

    def test_get(self):
        alice = StaffFactory()
        p1 = GradedTestPatternFactory(
            pieces__schematic__graded_garment_parameters__pattern_spec__user=alice,
            name="TestPatternListView.test_get.1",
            creation_date=datetime.datetime(2020, 5, 1),
        )
        p2 = GradedTestPatternFactory(
            pieces__schematic__graded_garment_parameters__pattern_spec__user=alice,
            name="TestPatternListView.test_get.2",
            creation_date=datetime.datetime(2020, 5, 2),
        )

        self.client.force_login(alice)
        url = reverse("graded_wizard:list_patterns")
        resp = self.client.get(url)

        goal_html = """
        <ul>
            <li><a href="%s">TestPatternListView.test_get.2</a></li>
            <li><a href="%s">TestPatternListView.test_get.1</a></li>
        </ul>
        """ % (
            p2.get_absolute_url(),
            p1.get_absolute_url(),
        )

        self.assertContains(resp, goal_html, html=True)
