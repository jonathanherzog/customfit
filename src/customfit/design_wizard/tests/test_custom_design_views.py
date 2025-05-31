import logging

from django.test import TestCase
from django.urls import reverse

from customfit.pattern_spec.models import PatternSpec
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.views import SWATCH_SESSION_NAME
from customfit.test_garment.factories import TestPatternSpecFactory
from customfit.userauth.factories import UserFactory

# Get an instance of a logger
logger = logging.getLogger(__name__)


class CreateCustomDesignViewTestMixin(object):

    # Written as a mixin to keep py.test from running the tests in here
    # directly, and not only in sub-classes. (Nose, how I miss you...)
    #
    # Expects sub-classes to implement:
    #
    #
    # * self.setUp(), setting self.body, self.swatch, self.client, self.stitch,
    #    and self.post_entries
    #    (_create_post_entries can be used for this last part),
    # * self.tearDown
    # * self.login()
    # * self._make_form(data), which returns a clean, bound form for modification.

    def _create_post_entries(self):
        return {
            "name": "design1",
            "stitch1": StitchFactory().id,
            "swatch": self.swatch.id,
            "test_length": 3.5,
        }

    def test_logging_in(self):
        self.login()
        response = self.client.get(
            reverse(
                "design_wizard:custom_design_create_view_garment",
                kwargs={"garment": "test_garment"},
            )
        )
        self.assertEqual(
            response.status_code,
            200,
            "custom design create view status code: %d" % response.status_code,
        )

    def test_post(self):
        self.login()
        response = self.client.post(self.url, self.post_entries, follow=False)

        # sanity check
        from customfit.garment_parameters.models import IndividualGarmentParameters

        self.assertEqual(
            IndividualGarmentParameters.objects.filter(user=self.user).count(), 1
        )
        igp = IndividualGarmentParameters.objects.get(user=self.user)
        goal_url = reverse("design_wizard:summary", args=(igp.id,))

        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_post_error(self):
        self.post_entries["test_length"] = ""
        self.login()
        url = reverse(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": "test_garment"},
        )
        response = self.client.post(url, self.post_entries, follow=False)
        self.assertContains(
            response, "Please correct the errors below", status_code=200
        )

    def test_form(self):
        form = self._make_form(data=self.post_entries)
        assert form.is_valid(), form.errors

    def test_initial_swatch_from_session(self):
        self.login()

        # sanity check
        response = self.client.get(self.url)
        form_initial = response.context["form"].initial
        self.assertNotIn("swatch", form_initial)

        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        response = self.client.get(self.url)
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
        response = self.client.get(self.url)

        response2 = self.client.post(
            self.url, {"name": "name", "swatch": self.swatch.id}
        )

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)

        # user uses swatch not in session
        swatch2 = SwatchFactory(user=self.user)
        session = self.client.session
        session[SWATCH_SESSION_NAME] = self.swatch.id
        session.save()
        response = self.client.get(self.url)

        response2 = self.client.post(self.url, {"name": "name", "swatch": swatch2.id})

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)


class CreateCustomDesignViewTestIndividual(TestCase, CreateCustomDesignViewTestMixin):

    def setUp(self):
        super(CreateCustomDesignViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.swatch = SwatchFactory(user=self.user)
        self.stitch = StitchFactory(user_visible=True)
        self.stitch.save()
        self.post_entries = self._create_post_entries()
        self.url = reverse(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": "test_garment"},
        )

        self.user2 = UserFactory()

    def tearDown(self):
        self.user2.delete()
        self.stitch.delete()
        super(CreateCustomDesignViewTestIndividual, self).tearDown()

    def login(self):
        return self.client.force_login(self.user)

    def _make_form(self, data):
        from customfit.test_garment.forms import TestPatternSpecFormIndividual

        form = TestPatternSpecFormIndividual(data=data, user=self.user)
        return form


class CustomPlusMissingViewTest(TestCase):

    def setUp(self):
        super(CustomPlusMissingViewTest, self).setUp()
        self.user = UserFactory()
        self.swatch = SwatchFactory(user=self.user)
        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def test_custom_plus_patternspec_wrong_user(self):
        """
        If a user tries to access the personalize design page for a patternspec
        that isn't theirs, they get PermissionDenied.
        """
        pspec = TestPatternSpecFactory(user=self.user2)

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "test_garment"},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(custom_url)
        self.assertEqual(resp.status_code, 403)
        pspec.delete()

    def test_custom_plus_patternspec_right_user(self):
        """
        If a user tries to access the personalize design page for a patternspec
        that IS theirs, the form is initialized with their data.
        """
        # The dicts will be too long to debug without this statement.

        self.login()
        stitch = StitchFactory()
        pspec = TestPatternSpecFactory(
            user=self.user,
            name="namename",
            swatch=self.swatch,
            stitch1=stitch,
            test_length=4.0,
        )

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "test_garment"},
        )

        resp = self.client.get(custom_url)

        # form_data = {}
        #
        # for field in resp.context['form'].initial:
        #     initial = resp.context['form'].initial[field]
        #     # Convert unicode emitted by Django forms to string forms that match
        #     # our design_choices, where applicable.
        #     if type(initial) == unicode:
        #         form_data[field] = initial.encode('utf-8')
        #     else:
        #         form_data[field] = initial

        processed_data = resp.context["form"].initial
        expected_data = {
            "swatch": self.swatch.pk,
            "name": "namename",
            "stitch1": stitch.pk,
            "test_length": 4.0,
        }
        self.assertEqual(processed_data, expected_data)

    def test_change_patternspec_imperial(self):

        stitch = StitchFactory()
        pspec = TestPatternSpecFactory(
            user=self.user, swatch=self.swatch, stitch1=stitch, test_length=5.0
        )
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "test_garment"},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(custom_url)
        self.assertEqual(resp.context["form"].initial["test_length"], 5.0)

        new_values = resp.context["form"].initial
        new_values["test_length"] = 7
        new_values["redirect_approve"] = "Get this pattern!"

        self.client.post(custom_url, data=new_values, follow=False)

        pspec.refresh_from_db()
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)
        self.assertEqual(pspec.test_length, 7)

    def test_change_patternspec_metric(self):
        self.user.profile.display_imperial = False
        self.user.profile.save()

        stitch = StitchFactory()
        pspec = TestPatternSpecFactory(
            user=self.user, swatch=self.swatch, stitch1=stitch, test_length=5.0
        )
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "test_garment"},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(custom_url)

        new_values = resp.context["form"].initial
        new_values["test_length"] = 6 * 2.54
        new_values["redirect_approve"] = "Get this pattern!"

        self.client.post(custom_url, data=new_values, follow=False)

        pspec.refresh_from_db()
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)
        self.assertAlmostEqual(pspec.test_length, 6, 2)
