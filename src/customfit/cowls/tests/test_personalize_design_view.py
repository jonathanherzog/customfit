import logging
from io import BytesIO

from django.conf import settings
from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

import customfit.designs.helpers.design_choices as DC
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.models import Swatch
from customfit.swatches.views import SWATCH_SESSION_NAME
from customfit.userauth.factories import StaffFactory, UserFactory

from ..factories import ApprovedCowlPatternFactory, CowlDesignFactory
from ..helpers import *
from ..models import CowlIndividualGarmentParameters

# Get an instance of a logger
logger = logging.getLogger(__name__)


class PersonalizeDesignViewTestIndividual(TestCase):

    def setUp(self):
        super(PersonalizeDesignViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.swatch = SwatchFactory(user=self.user)
        self._set_up_designs()
        self.user2 = UserFactory()
        self.post_entries = {
            "name": "name",
            "swatch": self.swatch.id,
            "circumference": COWL_CIRC_MEDIUM,
            "height": COWL_HEIGHT_AVERAGE,
        }

    def tearDown(self):
        self._tear_down_designs()
        super(PersonalizeDesignViewTestIndividual, self).tearDown()
        self.user2.delete()

    def login(self):
        return self.client.force_login(self.user)

    def _set_up_designs(self):
        self.design = CowlDesignFactory(name="Bar")
        self.design.save()
        self.personalize_url = reverse(
            "design_wizard:personalize", args=(self.design.slug,)
        )

    def _tear_down_designs(self):
        self.design.delete()

    def _get_design_page(self, design):
        url = reverse("design_wizard:personalize", args=(design.slug,))
        resp = self.client.get(url)
        return resp

    def test_get_personalize_page_slug(self):
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertContains(response, self.design.name, status_code=200)
        self.assertContains(
            response,
            "<title>Customize your {0}</title>".format(self.design.name),
            html=True,
        )

    def test_add_inches_to_drop_downs(self):
        self.login()
        response = self.client.get(self.personalize_url)

        # sanity check
        self.assertEqual(self.design.height, COWL_HEIGHT_AVERAGE)
        self.assertEqual(self.design.circumference, COWL_CIRC_MEDIUM)

        goal_height_html = """
            <div id="div_id_height" class="form-group"> 
                <label for="id_height" class="control-label  requiredField">
                    Height<span class="asteriskField">*</span> 
                </label> <div class="controls "> 
                <select name="height" required class="select form-control" id="id_height"> 
                    <option value="">---------</option> 
                    <option value="cowl_height_short">short height (10&quot;/25.5 cm)</option> 
                    <option value="cowl_height_avg" selected>average height (12&quot;/30.5 cm)</option> 
                    <option value="cowl_height_tall">tall height (16&quot;/40.5 cm)</option> 
                    <option value="cowl_height_xtall">extra tall height (20&quot;/51 cm)</option>
                </select> 
            </div>
            """
        self.assertContains(response, goal_height_html, html=True)

        goal_circ_html = """
            <div id="div_id_circumference" class="form-group"> 
                <label for="id_circumference" class="control-label  requiredField">
                    Circumference<span class="asteriskField">*</span> 
                </label> 
                <div class="controls "> 
                <select name="circumference" required class="select form-control" id="id_circumference"> 
                    <option value="">---------</option> 
                    <option value="cowl_circ_xsmall">extra-small circumference (20&quot;/51 cm)</option> 
                    <option value="cowl_circ_small">small circumference (26&quot;/66 cm)</option> 
                    <option value="cowl_circ_medium" selected>medium circumference (42&quot;/106.5 cm)</option> 
                    <option value="cowl_circ_large">large circumference (60&quot;/152.5 cm)</option>
                </select> 
            </div>           
            """
        self.assertContains(response, goal_circ_html, html=True)

    def test_design_page_visibility(self):
        # Logged in users should be able to visit the
        # pages of public and featured designs, but not limited or private

        self.login()

        private_design = CowlDesignFactory(name="Private design", visibility=DC.PRIVATE)
        limited_design = CowlDesignFactory(name="Limited design", visibility=DC.LIMITED)
        public_design = CowlDesignFactory(name="Public design", visibility=DC.PUBLIC)
        featured_design = CowlDesignFactory(
            name="Featured design", visibility=DC.FEATURED
        )

        private_design_basic = CowlDesignFactory(
            name="Private design basic", is_basic=True, visibility=DC.PRIVATE
        )
        limited_design_basic = CowlDesignFactory(
            name="Limited design basic", is_basic=True, visibility=DC.LIMITED
        )
        public_design_basic = CowlDesignFactory(
            name="Public design basic", is_basic=True, visibility=DC.PUBLIC
        )
        featured_design_basic = CowlDesignFactory(
            name="Featured design basic", is_basic=True, visibility=DC.FEATURED
        )

        design_code_pairs = [
            (private_design, 403),
            (limited_design, 403),
            (public_design, 200),
            (featured_design, 200),
            (private_design_basic, 403),
            (limited_design_basic, 403),
            (public_design_basic, 200),
            (featured_design_basic, 200),
        ]

        for design, status_code in design_code_pairs:
            url = reverse("design_wizard:personalize", args=(design.slug,))
            resp = self.client.get(url)
            with self.subTest(
                design=design.name,
                goal_status_code=status_code,
                actual_status_code=resp.status_code,
            ):
                self.assertEqual(resp.status_code, status_code)

        self.client.logout()

    def test_no_swatches(self):
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "before you can proceed")

        Swatch.objects.filter(user=self.user).all().delete()
        response = self.client.get(self.personalize_url)
        goal_url = reverse("swatches:swatch_create_view")
        goal_html = """
        <div id="hint_id_swatch" class="help-block">
        You need to <a href="%s?next=%s">add at least one gauge</a>
        before you can proceed.</div>""" % (
            goal_url,
            self.personalize_url,
        )
        self.assertContains(response, goal_html, html=True)

    def test_no_relevant_swatches(self):
        """
        Checks that the appropriate warning is thrown when the user has a
        swatch, but it's not suitable for the desired design.
        """
        self.login()

        repeats_stitch = StitchFactory(
            user_visible=True, repeats_x_mod=1, repeats_mod_y=4, is_allover_stitch=True
        )

        design = CowlDesignFactory(
            edging_stitch=repeats_stitch,
            main_stitch=repeats_stitch,
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

    def test_loggedin_user_does_sees_personalize_form(self):
        self.login()

        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "sign up")
        self.assertContains(response, 'gauge<span class="asteriskField">*')

        response2 = self.client.post(self.personalize_url, self.post_entries)

        self.assertEqual(response2.status_code, 302)
        self.assertRegex(response2["Location"], r"^/design/summary/\d+/$")

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
        self.design.main_stitch = new_stitch
        self.design.save()

        self.assertFalse(self.design.compatible_swatch(self.swatch))  # sanity check
        response = self.client.get(
            reverse("design_wizard:personalize", args=(self.design.slug,))
        )
        self.assertNotContains(response, self.swatch.name)

    def test_stitches_listed(self):
        # Test that we see the cable-stitches. Test added when we added cables
        cabled_design = CowlDesignFactory(
            main_stitch=StitchFactory(name="main stitch"),
            edging_stitch=StitchFactory(name="edging stitch"),
            panel_stitch=StitchFactory(name="panel stitch"),
            cable_stitch=StitchFactory(name="cable stitch"),
        )
        cabled_design.save()
        self.login()

        response = self._get_design_page(cabled_design)
        self.assertContains(response, "main stitch")
        self.assertContains(response, "edging stitch")
        self.assertContains(response, "panel stitch")
        self.assertContains(response, "cable stitch")
        cabled_design.delete()

    def test_create_swatch_url(self):
        self.login()
        response = self.client.get(self.personalize_url)
        goal_html = (
            '<a href="/swatch/new/?next=%s">(or create a new one)</a>'
            % self.personalize_url
        )
        self.assertContains(response, goal_html)

    def test_initial_values_from_session(self):
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

    def test_form_clears_swatch_from_session(self):
        self.login()

        # user uses swatch from session
        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        _ = self.client.get(self.personalize_url)

        _ = self.client.post(self.personalize_url, self.post_entries, follow=False)

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)

        # user uses swatch not in session
        swatch2 = SwatchFactory(user=self.user)
        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        _ = self.client.get(self.personalize_url)

        self.post_entries["swatch"] = swatch2.id
        _ = self.client.post(self.personalize_url, self.post_entries)

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)

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

    def test_no_swatches(self):
        self.login()
        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "before you can proceed")

        self.swatch.delete()
        response = self.client.get(self.personalize_url)
        self.assertContains(
            response,
            '<div id="hint_id_swatch" class="help-block">You need to <a href="/swatch/new/?next=%s">add at least one gauge</a> before you can proceed.</div>'
            % self.personalize_url,
            html=True,
        )


class PersonalizeDesignViewTestAnonymous(TestCase):

    def setUp(self):
        self.client = Client()
        self.design = CowlDesignFactory()
        self.design.save()
        self.personalize_url = reverse(
            "design_wizard:personalize", args=(self.design.slug,)
        )
        self.swatch = SwatchFactory()

    def test_anonymous_user_does_not_see_personalize_form(self):
        response = self.client.get(self.personalize_url)
        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_cannot_post_personalize_form(self):

        with self.settings(ALLOWED_HOSTS=['somehost']):
            response = self.client.post(
                self.personalize_url,
                {
                    "name": "name",
                    "bodych": self.swatch.id,
                    "circumference": COWL_CIRC_MEDIUM,
                    "height": COWL_HEIGHT_AVERAGE,
                },
                follow=False,
                SERVER_NAME="somehost",
            )
        goal_url = settings.LOGIN_URL + "?next=" + self.personalize_url
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_design_page_visibility(self):

        private_design = CowlDesignFactory(name="Private design", visibility=DC.PRIVATE)
        limited_design = CowlDesignFactory(name="Limited design", visibility=DC.LIMITED)
        public_design = CowlDesignFactory(name="Public design", visibility=DC.PUBLIC)
        featured_design = CowlDesignFactory(
            name="Featured design", visibility=DC.FEATURED
        )

        private_design_basic = CowlDesignFactory(
            name="Private design basic", is_basic=True, visibility=DC.PRIVATE
        )
        limited_design_basic = CowlDesignFactory(
            name="Limited design basic", is_basic=True, visibility=DC.LIMITED
        )
        public_design_basic = CowlDesignFactory(
            name="Public design basic", is_basic=True, visibility=DC.PUBLIC
        )
        featured_design_basic = CowlDesignFactory(
            name="Featured design basic", is_basic=True, visibility=DC.FEATURED
        )

        # Log in as non-subscriber
        self.client.logout()
        design_code_pairs = [
            (private_design, 302),
            (limited_design, 302),
            (public_design, 302),
            (featured_design, 302),
            (private_design_basic, 302),
            (limited_design_basic, 302),
            (public_design_basic, 302),
            (featured_design_basic, 302),
        ]
        for design, status_code in design_code_pairs:
            with self.subTest(design=design, status_code=status_code):
                resp = self.client.get(
                    reverse("design_wizard:personalize", args=[design.slug])
                )
                self.assertEqual(resp.status_code, status_code, design.name)

        self.client.logout()


class PersonalizeDesignViewTestStaff(TestCase):

    def test_design_page_visibility_staff(self):
        # staff should be able to visit the pages of all designs

        # Log in as subscriber
        user = StaffFactory()
        self.client.force_login(user)

        private_design = CowlDesignFactory(name="Private design", visibility=DC.PRIVATE)
        limited_design = CowlDesignFactory(name="Limited design", visibility=DC.LIMITED)
        public_design = CowlDesignFactory(name="Public design", visibility=DC.PUBLIC)
        featured_design = CowlDesignFactory(
            name="Featured design", visibility=DC.FEATURED
        )

        private_design_basic = CowlDesignFactory(
            name="Private design basic", is_basic=True, visibility=DC.PRIVATE
        )
        limited_design_basic = CowlDesignFactory(
            name="Limited design basic", is_basic=True, visibility=DC.LIMITED
        )
        public_design_basic = CowlDesignFactory(
            name="Public design basic", is_basic=True, visibility=DC.PUBLIC
        )
        featured_design_basic = CowlDesignFactory(
            name="Featured design basic", is_basic=True, visibility=DC.FEATURED
        )

        design_code_pairs = [
            (private_design, 200),
            (limited_design, 200),
            (public_design, 200),
            (featured_design, 200),
            (private_design_basic, 200),
            (limited_design_basic, 200),
            (public_design_basic, 200),
            (featured_design_basic, 200),
        ]

        for design, status_code in design_code_pairs:
            resp = self.client.get(
                reverse("design_wizard:personalize", args=[design.slug])
            )
            self.assertEqual(resp.status_code, status_code)

        self.client.logout()


class RedoCreateViewTests(TestCase):

    def setUp(self):
        super(RedoCreateViewTests, self).setUp()

        self.pattern = ApprovedCowlPatternFactory()
        self.alice = self.pattern.user

    def url_of_pattern(self, pattern):
        return reverse("design_wizard:redo_start", kwargs={"pk": pattern.pk})

    def put_knitter_in_session(self, knitter):
        s = self.client.session
        s[KNITTER_SESSION_NAME] = knitter.id
        s.save()

    # Visibility tests

    def test_can_see_redo_page_indivdiual(self):
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

    def test_anon_cannot_see_redo_page(self):
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        goal_url = reverse("userauth:login") + "?next=" + redo_url
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

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

        self.assertEqual(initial_values["swatch"], pspec.swatch.pk)
        self.assertEqual(initial_values["height"], pspec.height)
        self.assertEqual(initial_values["circumference"], pspec.circumference)

    def test_no_swatches(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        # sanity check
        response = self.client.get(redo_url)
        self.assertContains(response, "<h2>Re-do your pattern</h2>", html=True)

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

    def test_post(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        redo_data = {
            "swatch": self.pattern.swatch.id,
            "circumference": COWL_CIRC_SMALL,
            "height": COWL_HEIGHT_AVERAGE,
        }
        response = self.client.post(redo_url, data=redo_data, follow=True)
        igp = CowlIndividualGarmentParameters.objects.filter(
            redo__pattern=self.pattern
        ).get()
        self.assertRedirects(
            response, reverse("design_wizard:redo_approve", args=(igp.id,))
        )


class PersonalizeGradedDesignViewTests(TestCase):

    def setUp(self):
        super(PersonalizeGradedDesignViewTests, self).setUp()
        self.user = StaffFactory()
        self.design = CowlDesignFactory(name="Bar")
        self.design.save()
        self.personalize_url = reverse(
            "graded_wizard:make_graded_pattern", args=(self.design.slug,)
        )

        self.post_entries = {"name": "name", "row_gauge": 17, "stitch_gauge": 20}

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

    def test_post(self):
        self.login()

        response = self.client.post(self.personalize_url, self.post_entries)
        self.assertEqual(response.status_code, 302)
        self.assertRegex(response["Location"], r"^/pattern/graded/\d+/$")
