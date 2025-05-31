import logging

from django.test import TestCase, override_settings
from django.test.client import Client
from django.urls import reverse

import customfit.designs.helpers.design_choices as DC
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.helpers.math_helpers import cm_to_inches
from customfit.patterns.models import Redo
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.views import SWATCH_SESSION_NAME
from customfit.test_garment.factories import (
    TestApprovedIndividualPatternFactory,
    TestDesignFactory,
    TestPatternSpecFactory,
    TestRedoFactory,
)
from customfit.userauth.factories import StaffFactory, UserFactory

from ..constants import REDO_AND_APPROVE, REDO_AND_TWEAK

# Get an instance of a logger
logger = logging.getLogger(__name__)


class PersonalizeDesignViewTestsMixin(object):
    """
    Written as a mixin to keep py.test from running the tests in here directly,
    and not only in sub-classes. (Nose, how I miss you...)

    Expects sub-classes to implement:
    * setUp, which must in turn:
        * set self.user, self.body, self.simple_body, self.swatch, self.stitch
        * call _set_up_designs()
    * login()
    """

    def _set_up_designs(self):
        self.design = TestDesignFactory(name="Bar")
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

    def test_design_page_visibility(self):
        # Logged in users (who are not subscribers) should be able to visit the
        # pages of public and featured designs, but not limited or private

        # Log in as non-subscriber
        self.user = UserFactory()
        self.client.force_login(self.user)

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
                resp_status_code=resp.status_code,
                goal_status_code=status_code,
                design_name=design.name,
            ):
                self.assertEqual(resp.status_code, status_code)

        self.client.logout()

    def test_loggedin_user_does_sees_personalize_form(self):
        self.login()

        response = self.client.get(self.personalize_url)
        self.assertNotContains(response, "sign up")
        self.assertContains(response, 'Swatch<span class="asteriskField">*')

        response2 = self.client.post(
            self.personalize_url,
            {"name": "name", "stitch1": self.stitch.id, "swatch": self.swatch.id},
            follow=False,
        )
        self.assertEqual(response2.status_code, 302)
        self.assertRegex(response2["Location"], r"^/design/summary/\d+/$")

    def test_form_clears_swatch_from_session(self):
        self.login()

        # user uses swatch from session
        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        response = self.client.get(self.personalize_url)

        response2 = self.client.post(
            self.personalize_url, {"name": "name", "swatch": self.swatch.id}
        )

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)

        # user uses swatch not in session
        swatch2 = SwatchFactory(user=self.user)
        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        response = self.client.get(self.personalize_url)

        response2 = self.client.post(
            self.personalize_url, {"name": "name", "swatch": swatch2.id}
        )

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)


class PersonalizeDesignViewTestIndividual(TestCase, PersonalizeDesignViewTestsMixin):
    def setUp(self):
        super(PersonalizeDesignViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.swatch = SwatchFactory(user=self.user)
        self.stitch = StitchFactory()
        self._set_up_designs()
        self.user2 = UserFactory()
        self.post_entries = {"name": "name", "swatch": self.swatch.id}

    def tearDown(self):
        self._tear_down_designs()
        super(PersonalizeDesignViewTestIndividual, self).tearDown()
        self.user2.delete()

    def login(self):
        return self.client.force_login(self.user)


class PersonalizeDesignViewTestAnonymous(TestCase):

    def setUp(self):
        self.client = Client()
        self.design = TestDesignFactory()
        self.design.save()
        self.personalize_url = reverse(
            "design_wizard:personalize", args=(self.design.slug,)
        )
        self.swatch = SwatchFactory()

    def test_anonymous_user_gets_redirected(self):
        response = self.client.get(self.personalize_url)
        self.assertRedirects(
            response,
            reverse("userauth:login") + "?next=" + self.personalize_url,
            fetch_redirect_response=False,
        )

    def test_design_page_visibility(self):
        # Anonymous users should be able to visit the
        # pages of public and featured designs, but not limited or private

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
            resp = self.client.get(
                reverse("design_wizard:personalize", args=[design.slug])
            )
            with self.subTest(
                resp_status_code=resp.status_code,
                goal_status_code=status_code,
                design_name=design.name,
            ):
                self.assertEqual(resp.status_code, status_code, design.name)

        self.client.logout()


class PersonalizeDesignViewTestStaff(TestCase):

    def test_design_page_visibility_staff(self):
        # staff should be able to visit the pages of all designs

        # Log in as subscriber
        user = StaffFactory()
        self.client.force_login(user)

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

        self.pattern = TestApprovedIndividualPatternFactory()
        self.alice = self.pattern.user
        self.swatch = self.pattern.get_spec_source().swatch

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

    # def test_initial_values(self):
    #     self.client.force_login(self.alice)
    #     redo_url = self.url_of_pattern(self.pattern)
    #     response = self.client.get(redo_url)
    #     initial_values = response.context['form'].initial
    #     pspec = self.pattern.get_spec_source()
    #
    #     self.assertEqual(initial_values['swatch'], pspec.swatch.pk)

    # def test_no_swatches(self):
    #     self.client.force_login(self.alice)
    #     redo_url = self.url_of_pattern(self.pattern)
    #     # sanity check
    #     response = self.client.get(redo_url)
    #     self.assertNotContains(response, "before you can proceed")
    #
    #     for swatch in Swatch.objects.filter(user=self.alice):
    #         swatch.archived = True
    #         swatch.save()
    #     response = self.client.get(redo_url)
    #     self.assertContains(response,
    #                         '<p id="hint_id_swatch" class="help-block">You need to <a href="/swatch/new/?next=%s">add at least one gauge</a> before you can proceed.</p>' % redo_url,
    #                         html=True)

    # Post tests
    def test_post_to_tweak(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["swatch"] = self.swatch.id
        new_values["test_length"] = 2

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        igp = IndividualGarmentParameters.objects.get(redo=redo)
        goal_url = reverse("design_wizard:redo_tweak", kwargs={"pk": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    # Post tests
    def test_post_to_approve(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        pspec = self.pattern.get_spec_source()
        new_values = initial_values
        new_values["test_length"] = 2
        new_values["swatch"] = self.swatch.id

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        igp = IndividualGarmentParameters.objects.get(redo=redo)
        goal_url = reverse("design_wizard:redo_approve", kwargs={"igp_id": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_imperial_user_post(self):
        self.alice.profile.display_imperial = True

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        # self.assertContains(response,
        #                     '<span class="input-group-addon">inches</span>',
        #                     html=True)

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["test_length"] = 3
        new_values["swatch"] = self.swatch.id
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)

        # Redo should have test_length of 3
        self.assertEqual(redo.test_length, 3)

    def test_metric_user_post(self):
        self.alice.profile.display_imperial = False
        self.alice.profile.save()

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        # self.assertContains(response,
        #                     '<span class="input-group-addon">cm</span>',
        #                     html=True)

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["test_length"] = 10  # cm
        new_values["swatch"] = self.swatch.id
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)

        # Redo should have neckline depth of 4
        self.assertAlmostEqual(redo.test_length, cm_to_inches(10), 2)

    # NOTE: Yes, these tests technically belong here. But it turns out that they required
    # a disproportionate amount of testing machinery to make work, so we're going to rely on
    # their counterparts in the sweater tests to test this functionality.
    # def test_missing_measurements_summary(self):
    #
    #     simple_body = SimpleBodyFactory(user=self.alice)
    #     pattern = TestApprovedIndividualPatternWithBodyFactory.for_user(self.alice)
    #
    #     self.client.force_login(self.alice)
    #     redo_url = self.url_of_pattern(pattern)
    #     response = self.client.get(redo_url)
    #     initial_values = response.context['form'].initial
    #     new_values = initial_values
    #     new_values['body'] = simple_body.pk
    #     # Since there are multiple submit buttons, we must specify the one
    #     # we want in the POST data.
    #     new_values[REDO_AND_APPROVE] = 'redo!'
    #
    #     response = self.client.post(redo_url, data=new_values)
    #     redo = Redo.objects.get(pattern=pattern)
    #     goal_url = reverse('design_wizard:missing_redo', kwargs={'pk': redo.pk, 'action': 'summary'})
    #     self.assertRedirects(response, goal_url, fetch_redirect_response=False)
    #
    #
    # def test_missing_measurements_tweak(self):
    #
    #     simple_body = SimpleBodyFactory(user=self.alice)
    #     pattern = TestApprovedIndividualPatternWithBodyFactory.for_user(self.alice)
    #
    #     self.client.force_login(self.alice)
    #     redo_url = self.url_of_pattern(pattern)
    #     response = self.client.get(redo_url)
    #     initial_values = response.context['form'].initial
    #     new_values = initial_values
    #     new_values['body'] = simple_body.pk
    #     # Since there are multiple submit buttons, we must specify the one
    #     # we want in the POST data.
    #     new_values[REDO_AND_TWEAK] = 'customize fit specifics'
    #
    #     response = self.client.post(redo_url, data=new_values)
    #     redo = Redo.objects.get(pattern=pattern)
    #     goal_url = reverse('design_wizard:missing_redo', kwargs={'pk': redo.pk, 'action': 'tweak'})
    #     self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    # def test_only_customer_swatches_shown(self):
    #     self.client.force_login(self.store.owner)
    #     self.put_knitter_in_session(self.store.knitter1)
    #     redo_url = self.url_of_pattern(self.store_pattern)
    #     response = self.client.get(redo_url)
    #     self.assertEqual(set(response.context['form'].fields['swatch'].queryset),
    #                      set([self.store.swatch]))


class RedoUpdateTests(TestCase):

    def setUp(self):

        self.redo = TestRedoFactory()
        self.alice = self.redo.user
        self.url = reverse("design_wizard:redo_plus_missing", args=(self.redo.id,))
        self.client.force_login(self.alice)
        self.user2 = UserFactory()

    def put_knitter_in_session(self, knitter):
        s = self.client.session
        s[KNITTER_SESSION_NAME] = knitter.id
        s.save()

    # Test accessibility

    def test_can_see_redo_page_indivdiual(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_cant_see_redo_page_pattern_no_redo(self):
        # Kludge pattern into having been redone
        self.pattern = self.redo.pattern
        self.pattern.original_pieces = self.pattern.pieces
        self.pattern.save()

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_anon_cannot_see_redo_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        goal_url = reverse("userauth:login") + "?next=" + self.url
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_other_user_cannot_see_page(self):
        bob = UserFactory()
        self.client.force_login(bob)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    # Individual Ownership consistency checks
    def test_pattern_wrong_owner(self):
        self.redo.pattern.user = self.user2
        self.redo.pattern.save()
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertContains(
            response,
            "<p>Sorry, but you don't have permission to view this content.</p>",
            status_code=403,
            html=True,
        )

    def test_swatch_wrong_owner(self):
        self.redo.swatch.user = self.user2
        self.redo.swatch.save()
        self.client.force_login(self.alice)
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(self.url)

    # Content tests

    def test_initial_values(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial

        self.assertEqual(initial_values["swatch"], self.redo.swatch.pk)

    # Post tests

    def test_post_to_tweak(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        self.assertEqual(
            IndividualGarmentParameters.objects.filter(redo=self.redo).count(), 0
        )
        response = self.client.post(self.url, data=new_values)
        self.redo.refresh_from_db()
        igp = IndividualGarmentParameters.objects.get(redo=self.redo)
        goal_url = reverse("design_wizard:redo_tweak", kwargs={"pk": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

        # Post tests

    def test_post_to_approve(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(self.url, data=new_values)
        self.redo.refresh_from_db()
        igp = IndividualGarmentParameters.objects.get(redo=self.redo)
        goal_url = reverse("design_wizard:redo_approve", kwargs={"igp_id": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    # NOTE: Yes, these tests technically belong here. But it turns out that they required
    # a disproportionate amount of testing machinery to make work, so we're going to rely on
    # their counterparts in the sweater tests to test this functionality.
    # def test_missing_measurements_summary(self):
    #
    # def test_missing_measurements_summary(self):
    #     # Sanity-check: the pattern is hourglass, right?
    #     org_patternspec = self.redo.pattern.get_spec_source()
    #     self.assertTrue(org_patternspec.is_hourglass)
    #
    #     simple_body = SimpleBodyFactory(user=self.alice)
    #
    #     self.client.force_login(self.alice)
    #     response = self.client.get(self.url)
    #     initial_values = response.context['form'].initial
    #     new_values = initial_values
    #     new_values['body'] = simple_body.pk
    #     # Since there are multiple submit buttons, we must specify the one
    #     # we want in the POST data.
    #     new_values[REDO_AND_APPROVE] = 'redo!'
    #
    #     response = self.client.post(self.url, data=new_values)
    #     redo = Redo.objects.get(pattern = self.redo.pattern)
    #     goal_url = reverse('design_wizard:missing_redo', kwargs={'pk': redo.pk, 'action': 'summary'})
    #     self.assertRedirects(response, goal_url)
    #
    # def test_missing_measurements_tweak(self):
    #     # Sanity-check: the pattern is hourglass, right?
    #     org_patternspec = self.redo.pattern.get_spec_source()
    #     self.assertTrue(org_patternspec.is_hourglass)
    #
    #     simple_body = SimpleBodyFactory(user=self.alice)
    #
    #     self.client.force_login(self.alice)
    #     response = self.client.get(self.url)
    #     initial_values = response.context['form'].initial
    #     new_values = initial_values
    #     new_values['body'] = simple_body.pk
    #     # Since there are multiple submit buttons, we must specify the one
    #     # we want in the POST data.
    #     new_values[REDO_AND_TWEAK] = 'customize fit specifics'
    #
    #     response = self.client.post(self.url, data=new_values)
    #     redo = Redo.objects.get(pattern = self.redo.pattern)
    #     goal_url = reverse('design_wizard:missing_redo', kwargs={'pk': redo.pk, 'action': 'tweak'})
    #     self.assertRedirects(response, goal_url)


class TestPersonalizePlusMissingViews(TestCase):

    def setUp(self):
        super(TestPersonalizePlusMissingViews, self).setUp()
        self.user = UserFactory()
        self.swatch = SwatchFactory(user=self.user)
        self.design = TestDesignFactory()
        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def test_personalize_plus_patternspec_wrong_user(self):
        """
        If a user tries to access the personalize design page for a patternspec
        that isn't theirs, they get PermissionDenied.
        """
        pspec = TestPatternSpecFactory(user=self.user2, design_origin=self.design)

        personalize_url = reverse(
            "design_wizard:personalize_plus_missing",
            kwargs={"design_slug": self.design.slug, "pk": pspec.pk},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(personalize_url)
        self.assertEqual(resp.status_code, 403)

    def test_personalize_plus_patternspec_right_user(self):
        """
        If a user tries to access the personalize design page for a patternspec
        that IS theirs, the form is initialized with their data.
        """
        self.login()
        stitch1 = StitchFactory(name="Stitch1")
        pspec = TestPatternSpecFactory(
            user=self.user,
            name="namename",
            swatch=self.swatch,
            design_origin=self.design,
            stitch1=stitch1,
        )

        personalize_url = reverse(
            "design_wizard:personalize_plus_missing",
            kwargs={"design_slug": self.design.slug, "pk": pspec.pk},
        )

        resp = self.client.get(personalize_url)

        form_data = {}
        for field in resp.context["form"].fields:
            initial = resp.context["form"].initial[field]
            form_data[field] = initial

        expected_data = {
            "swatch": self.swatch.id,
            "stitch1": stitch1.id,
            "name": "namename",
        }
        self.assertEqual(form_data, expected_data)
