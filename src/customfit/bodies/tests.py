import copy
import logging

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.urls import resolve, reverse

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    convert_value_to_metric,
    inches_to_cm,
    round,
)
from customfit.helpers.user_constants import MAX_BODIES
from customfit.patterns.models import IndividualPattern
from customfit.test_garment.factories import (
    TestApprovedIndividualPatternWithBodyFactory,
    TestIndividualPatternWithBodyFactory,
    pattern_with_body_from_pspec_and_redo_kwargs,
)
from customfit.userauth.factories import MetricUserFactory, UserFactory

from .factories import (
    BodyFactory,
    ChildBodyFactory,
    FemaleBodyFactory,
    GradeFactory,
    GradeSetFactory,
    MaleBodyFactory,
    SimpleBodyFactory,
    UnstatedTypeBodyFactory,
    csv_bodies,
    get_csv_body,
)
from .forms import BodyCreateForm, BodyUpdateForm
from .models import ESSENTIAL_FIELDS, EXTRA_FIELDS, OPTIONAL_FIELDS, Body
from .views import BODY_SESSION_NAME

logger = logging.getLogger(__name__)


class BodyCreateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.metric_user = MetricUserFactory()

        self.bname = "body1"
        essentials = {
            "name": self.bname,
            "bust_circ": 41,
            "waist_circ": 32,
            "med_hip_circ": 40,
            "bicep_circ": 12,
            "wrist_circ": 6,
            "armhole_depth": 8,
            "armpit_to_med_hip": 16,
            "armpit_to_full_sleeve": 17,
            "body_type": "body_type_adult_woman",
        }

        extras = {
            "elbow_circ": 10,
            "forearm_circ": 10,
            "armpit_to_short_sleeve": 2,
            "armpit_to_elbow_sleeve": 6,
            "armpit_to_three_quarter_sleeve": 12,
            "inter_nipple_distance": 8,
            # this is probably dumb but we needed SOME measurement to
            # test form validation
            "cross_chest_distance": 10,
        }

        hourglass = {
            "upper_torso_circ": 38,
            "high_hip_circ": 37,
            "low_hip_circ": 42,
            "tunic_circ": 44,
            "armpit_to_waist": 9,
            "armpit_to_high_hip": 14,
            "armpit_to_low_hip": 18,
            "armpit_to_tunic": 21,
        }

        self.post_entries = copy.copy(essentials)
        self.post_entries.update(extras)
        self.post_entries.update(hourglass)

        self.post_metric_entries = {}
        for key, value in list(self.post_entries.items()):
            if isinstance(value, int) or isinstance(value, float):
                self.post_metric_entries[key] = float(value) * 2.54
            else:
                self.post_metric_entries[key] = value

        self.post_entries_essentials = essentials

    def tearDown(self):
        self.user.delete()
        self.metric_user.delete()
        super(BodyCreateViewTests, self).tearDown()

    def test_body_create_page(self):
        # tests that the BodyCreateView displays the expected HTML

        self.logged_in = self.client.force_login(self.user)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        response = self.client.get(reverse("bodies:body_create_view"))
        self.assertContains(response, "<h2>Create new measurements</h2>")

    def test_create_basic_body(self):
        """
        tests that the BodyCreateView displays and creates a body
        """
        self.logged_in = self.client.force_login(self.user)
        self.assertNotIn(BODY_SESSION_NAME, self.client.session)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        response = self.client.get(reverse("bodies:body_create_view"))
        self.assertEqual(
            response.status_code, 200, "create a body page does not display"
        )

        response = self.client.post(
            reverse("bodies:body_create_view"), self.post_entries
        )

        body = Body.objects.get(name=self.bname)
        self.assertIsNotNone(body, "there is no body with that name")
        self.assertEqual(body.user, self.user, "user not saved with body")
        self.assertEqual(body.name, self.bname, "name not saved with body")
        self.assertEqual(
            body.upper_torso_circ, 38, "upper_torso_circ not saved with body"
        )

        session = self.client.session
        self.assertEqual(session[BODY_SESSION_NAME], body.id)

    def test_body_must_have_name(self):
        self.logged_in = self.client.force_login(self.user)
        self.post_entries["name"] = ""
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        self.client.post(reverse("bodies:body_create_view"), self.post_entries)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "body should not save without a name",
        )

    def test_buttons_go_to_design_and_home_no_next_url(self):
        self.logged_in = self.client.force_login(self.user)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        response = self.client.get(reverse("bodies:body_create_view"))
        # Test presence of buttons
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_home" value="save and go to account home" '
            'class="btn btn-primary btn-customfit-outline" id="submit_to_home_1"/>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit_to_pattern_1"/>',
            html=True,
        )
        response = self.client.post(
            reverse("bodies:body_create_view"), self.post_entries, follow=True
        )
        self.assertRedirects(response, reverse("home_view"))
        self.post_entries["submit_to_pattern"] = "submit"
        response = self.client.post(
            reverse("bodies:body_create_view"), self.post_entries, follow=True
        )
        self.assertRedirects(response, reverse("design_wizard:choose_type"))

    def test_buttons_go_to_design_and_home_with_next_url(self):
        self.logged_in = self.client.force_login(self.user)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        url = reverse("bodies:body_create_view") + "?next=/some/url"
        response = self.client.get(url)
        # Test absence of standard buttons
        self.assertNotContains(
            response,
            '<input type="submit" name="submit_to_home" value="save and go to account home" '
            'class="btn btn-primary btn-customfit-outline" id="submit_to_home_1"/>',
            html=True,
        )
        self.assertNotContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit_to_pattern_1"/>',
            html=True,
        )
        # Test for the submit button
        self.assertNotContains(
            response,
            '<input type="submit" name="submit" value="save and go back to personalizing" '
            'class="btn btn-primary btn-customfit-outline" id="submit"/>',
            html=True,
        )

        response = self.client.post(url, self.post_entries, follow=False)
        self.assertRedirects(response, "/some/url", fetch_redirect_response=False)

    def test_converting_measurement_units(self):
        """
        Test that if the user is using metric it gets converted to imperial in
        the db.
        """
        self.client.force_login(self.metric_user)
        self.assertFalse(
            Body.objects.filter(user=self.metric_user).exists(),
            "there is already a body in the db...abort!",
        )
        self.client.post(reverse("bodies:body_create_view"), self.post_metric_entries)
        body = Body.objects.get(name=self.bname)
        self.assertNotEqual(
            body.upper_torso_circ,
            38 * 2.54,
            "upper torso circ should be 38*2.54cm, not inches.  It is stored as "
            "38*2.54 inches in the db.",
        )
        self.assertTrue(
            body.upper_torso_circ > 37,
            "upper torso circ should be > 37, instead is %f" % body.upper_torso_circ,
        )
        self.assertTrue(body.upper_torso_circ < 39, "upper torso circ should be < 39")

    def test_essentials_only_validates(self):
        """
        Ensure that the body creation form works if only essentials are posted.
        """
        self.client.force_login(self.user)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )

        response = self.client.post(
            reverse("bodies:body_create_view"),
            self.post_entries_essentials,
            follow=True,
        )
        self.assertRedirects(response, reverse("home_view"))

        body = Body.objects.get(name=self.bname)
        self.assertIsNotNone(body, "there is no body with that name")

    def test_hourglass_is_not_highlander(self):
        """
        There cannot be only one: if users submit one hourglass measurement,
        they must submit all hourglass measurements.
        """
        self.client.force_login(self.user)
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        inadequate_dict = copy.copy(self.post_entries)
        inadequate_dict["med_hip_circ"] = None

        form = BodyCreateForm(user=self.user, data=inadequate_dict)
        self.assertFalse(form.is_valid())

    def test_extras_can_be_piecemeal(self):
        """
        Users may submit incomplete extra measurement sets.
        """
        self.assertFalse(
            Body.objects.filter(user=self.user).exists(),
            "there is already a body in the db...abort!",
        )
        inadequate_dict = copy.copy(self.post_entries)
        inadequate_dict["forearm_circ"] = None

        form = BodyCreateForm(user=self.user, data=inadequate_dict)
        self.assertTrue(form.is_valid())

    def test_enforce_body_limit(self):

        # Sanity-check:
        self.assertFalse(
            Body.objects.filter(user=self.user).exists()
        )  # No bodies already

        # Generate the 10 allowed bodies:
        self.client.force_login(self.user)
        for i in range(10):
            this_post_entries = copy.copy(self.post_entries)
            this_post_entries["name"] = "body_%s" % i
            response = self.client.post(
                reverse("bodies:body_create_view"), this_post_entries
            )
            self.assertRedirects(response, reverse("home_view"))
            self.assertEqual(Body.objects.filter(user=self.user).count(), i + 1)

        # I shouldn't be able to make another one
        this_post_entries = copy.copy(self.post_entries)
        this_post_entries["name"] = "body_11"
        response = self.client.post(
            reverse("bodies:body_create_view"), this_post_entries, follow=True
        )
        self.assertEqual(Body.objects.filter(user=self.user).count(), 10)
        self.assertRedirects(response, reverse("bodies:body_list_view"))
        goal_msg = """
        <ul class="messages">
          <li class="alert alert-info warning">
              Whoops! You can&#39;t have more than 10 measurement sets at a time. You may delete
              existing measurement sets as long as you haven't created any patterns for them.
              There&#39;s a link at the bottom of each details page.
          </li>
         </ul>"""
        self.assertContains(response, goal_msg, html=True)

    def test_patterns(self):

        from customfit.test_garment.factories import (
            TestApprovedIndividualPatternWithBodyFactory,
            TestPatternSpecWithBodyFactory,
        )

        # Swatch used for original pattern, not redone
        p1 = TestApprovedIndividualPatternWithBodyFactory()
        user = p1.user
        body = p1.get_spec_source().body
        swatch = p1.get_spec_source().swatch

        pspec2 = TestPatternSpecWithBodyFactory(user=user, body=body, swatch=swatch)
        # body used for original pattern but NOT redone
        p2 = pattern_with_body_from_pspec_and_redo_kwargs(pspec2)
        # sanity check
        self.assertNotEqual(
            p2.pieces.schematic.individual_garment_parameters.redo.body, body
        )
        self.assertEqual(
            p2.original_pieces.schematic.individual_garment_parameters.pattern_spec.body,
            body,
        )

        pspec3 = TestPatternSpecWithBodyFactory(user=user, body=body, swatch=swatch)
        # Swatch used for original pattern AND redone
        p3 = pattern_with_body_from_pspec_and_redo_kwargs(pspec3, body=body)
        # sanity check
        self.assertEqual(
            p3.pieces.schematic.individual_garment_parameters.redo.body, body
        )
        self.assertEqual(
            p3.original_pieces.schematic.individual_garment_parameters.pattern_spec.body,
            body,
        )

        pspec4 = TestPatternSpecWithBodyFactory(user=user)
        # Swatch used niether for original pattern nor redone
        p4 = pattern_with_body_from_pspec_and_redo_kwargs(pspec4)
        # sanity check
        self.assertNotEqual(
            p4.pieces.schematic.individual_garment_parameters.redo.body, body
        )
        self.assertNotEqual(
            p4.original_pieces.schematic.individual_garment_parameters.pattern_spec.body,
            body,
        )

        pspec5 = TestPatternSpecWithBodyFactory(user=user, swatch=swatch)
        # Swatch used for redo but not original pattern
        p5 = pattern_with_body_from_pspec_and_redo_kwargs(pspec5, body=body)
        # sanity check
        self.assertEqual(
            p5.pieces.schematic.individual_garment_parameters.redo.body, body
        )
        self.assertNotEqual(
            p5.original_pieces.schematic.individual_garment_parameters.pattern_spec.body,
            body,
        )

        patterns_of_body = body.patterns

        self.assertIn(p1, patterns_of_body)
        self.assertNotIn(p2, patterns_of_body)
        self.assertIn(p3, patterns_of_body)
        self.assertNotIn(p4, patterns_of_body)
        self.assertIn(p5, patterns_of_body)


class BodyUpdateViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.metric_user = MetricUserFactory()

        self.bname = "body1"
        essentials = {
            "name": self.bname,
            "upper_torso_circ": 38,
            "bust_circ": 41,
            "waist_circ": 32,
            "med_hip_circ": 40,
            "bicep_circ": 12,
            "wrist_circ": 6,
            "armhole_depth": 8,
            "armpit_to_med_hip": 16,
            "armpit_to_full_sleeve": 17,
            "body_type": "body_type_adult_woman",
        }

        extras = {
            "elbow_circ": 10,
            "forearm_circ": 10,
            "armpit_to_short_sleeve": 2,
            "armpit_to_elbow_sleeve": 6,
            "armpit_to_three_quarter_sleeve": 12,
            "inter_nipple_distance": 8,
            # this is probably dumb but we needed SOME measurement to
            # test form validation
            "cross_chest_distance": 10,
        }

        hourglass = {
            "high_hip_circ": 37,
            "low_hip_circ": 42,
            "tunic_circ": 44,
            "armpit_to_waist": 9,
            "armpit_to_high_hip": 14,
            "armpit_to_low_hip": 18,
            "armpit_to_tunic": 21,
        }

        self.post_entries = copy.copy(essentials)
        self.post_entries.update(extras)
        self.post_entries.update(hourglass)

        self.post_metric_entries = {}
        metric_dict = copy.copy(essentials)
        metric_dict.update(extras)
        metric_dict.update(hourglass)
        for key, value in list(metric_dict.items()):
            if isinstance(value, int) or isinstance(value, float):
                self.post_metric_entries[key] = float(value) * 2.54
            else:
                self.post_metric_entries[key] = value

        self.post_entries_essentials = essentials

        self.body = Body.objects.create(user=self.user, **essentials)

    def tearDown(self):
        self.body.delete()
        self.user.delete()
        self.metric_user.delete()
        super(BodyUpdateViewTests, self).tearDown()

    def test_can_update_measurements(self):
        """
        Ensure that adding measurements saves them to the db.
        """
        form = BodyUpdateForm(
            user=self.user, instance=self.body, data=self.post_entries
        )
        form.save()
        self.assertEqual(self.body.high_hip_circ, 37)

    def test_update_does_not_overwrite(self):
        """
        Ensure that updating measurements does not change existing ones.
        """
        pre_dict = self.body.to_dict()

        form = BodyUpdateForm(
            user=self.user, instance=self.body, data=self.post_entries
        )
        form.save()

        post_dict = self.body.to_dict()

        assert all(
            item in list(post_dict.items())
            for item in list(pre_dict.items())
            if item[1] is not None
        )

    def test_hourglass_is_not_highlander(self):
        """
        There cannot be only one: if users submit one hourglass measurement,
        they must submit all hourglass measurements.
        """
        inadequate_dict = copy.copy(self.post_entries)
        inadequate_dict["med_hip_circ"] = None

        form = BodyUpdateForm(user=self.user, instance=self.body, data=inadequate_dict)
        self.assertFalse(form.is_valid())

    def test_extras_can_be_piecemeal(self):
        """
        Users may submit incomplete extra measurement sets.
        """
        for field in EXTRA_FIELDS:
            inadequate_dict = copy.copy(self.post_entries)
            inadequate_dict[field] = None

            form = BodyUpdateForm(
                user=self.user, instance=self.body, data=inadequate_dict
            )
            self.assertTrue(form.is_valid())

    def test_metric_initial_works(self):
        """
        Ensure that, if users prefer metric, initial body measurements
        displayed in the editing form are in metric.
        """
        self.body.user = self.metric_user
        self.body.save()

        form = BodyUpdateForm(user=self.metric_user, instance=self.body)

        for measurement, value in list(form.initial.items()):
            if isinstance(value, int) or isinstance(value, float):
                self.assertEqual(
                    form.initial[measurement],
                    round(
                        inches_to_cm(getattr(self.body, measurement)),
                        ROUND_ANY_DIRECTION,
                        0.5,
                    ),
                )

    def test_metric_update_works(self):
        """
        Ensure that, if users update bodies with metric units, they are saved
        in inches.
        """
        self.body.user = self.metric_user
        self.body.save()
        body_update_url = reverse("bodies:body_update_view", args=(self.body.id,))
        self.logged_in = self.client.force_login(self.metric_user)

        resp = self.client.post(body_update_url, self.post_metric_entries, follow=True)
        for measurement, value in list(self.post_entries.items()):
            if isinstance(value, float) or isinstance(value, int):
                body_value = getattr(self.body, measurement)
                if body_value:
                    self.assertAlmostEqual(
                        self.post_entries[measurement], body_value, places=1
                    )

    def test_buttons_go_to_review(self):
        self.logged_in = self.client.force_login(self.user)
        body_update_url = reverse("bodies:body_update_view", args=(self.body.id,))
        response = self.client.get(body_update_url)
        # Test presence of buttons
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_home" value="save and review" '
            'class="btn btn-primary btn-customfit-outline" id="submit_to_home_2"/>',
            html=True,
        )
        response = self.client.post(body_update_url, self.post_entries, follow=True)
        self.assertRedirects(
            response, reverse("bodies:body_detail_view", args=(self.body.id,))
        )

    def test_buttons_go_to_home(self):
        self.logged_in = self.client.force_login(self.user)
        body_update_url = reverse("bodies:body_update_view", args=(self.body.id,))
        response = self.client.get(body_update_url)
        # Test presence of buttons
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit_to_pattern_2"/>',
            html=True,
        )
        self.post_entries["submit_to_pattern"] = "submit"
        response = self.client.get(body_update_url)
        response = self.client.post(body_update_url, self.post_entries, follow=True)
        self.assertRedirects(response, reverse("design_wizard:choose_type"))

    def test_body_put_in_session(self):
        self.client.force_login(self.user)
        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

        body_update_url = reverse("bodies:body_update_view", args=(self.body.id,))
        response = self.client.post(body_update_url, self.post_entries, follow=True)

        session = self.client.session
        self.assertEqual(session[BODY_SESSION_NAME], self.body.id)


class BodyDeleteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.user2 = UserFactory()

    def tearDown(self):
        self.user.delete()
        self.user2.delete()
        super(BodyDeleteViewTest, self).tearDown()

    def set_up_body_with_pattern(self):
        ip = TestApprovedIndividualPatternWithBodyFactory.for_user(self.user)
        b = ip.get_spec_source().body
        return b, ip

    def test_get_no_patterns(self):
        body = BodyFactory()
        user = body.user
        self.client.force_login(user)
        b_delete_url = reverse("bodies:body_delete_view", args=(body.id,))
        response = self.client.get(b_delete_url)
        goal_html = (
            "<p>Deleting measurement sets <i>cannot be undone</i>. Once you delete %s, it's gone.</p>"
            % body.name
        )
        self.assertContains(response, goal_html, html=True)
        self.assertNotContains(
            response,
            "<p>(Don't worry; the patterns you've made from this measurement-set won't be deleted.)</p>",
            html=True,
        )

    def test_get_with_patterns(self):
        body, p = self.set_up_body_with_pattern()
        user = p.user
        self.client.force_login(user)
        b_delete_url = reverse("bodies:body_delete_view", args=(body.id,))
        response = self.client.get(b_delete_url)
        goal_html = (
            "<p>Deleting measurement sets <i>cannot be undone</i>. Once you delete %s, it's gone.</p>"
            % body.name
        )
        self.assertContains(response, goal_html, html=True)
        self.assertContains(
            response,
            "<p>(Don't worry; the patterns you've made from this measurement-set won't be deleted.)</p>",
            html=True,
        )

    def test_basic_deletion(self):
        """
        Ensures that we can delete a body.
        """
        self.client.force_login(self.user)
        b = BodyFactory(user=self.user)
        b.save()
        body_id = b.id
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))
        response = self.client.post(b_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "body did not delete; instead returned %s" % response.status_code,
        )
        self.assertFalse(Body.objects.filter(id=body_id).exists())

    def test_session_handling(self):
        self.client.force_login(self.user)
        b = BodyFactory(user=self.user)
        b.save()
        body_id = b.id
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))

        session = self.client.session
        session[BODY_SESSION_NAME] = body_id
        session.save()

        response = self.client.post(b_delete_url)

        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

    def test_session_handling_other_body(self):
        self.client.force_login(self.user)
        b = BodyFactory(user=self.user)
        b2 = BodyFactory(user=self.user)
        body_id = b.id
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))

        session = self.client.session
        session[BODY_SESSION_NAME] = b2.id
        session.save()

        response = self.client.post(b_delete_url)

        session = self.client.session
        self.assertEqual(session[BODY_SESSION_NAME], b2.id)

    def test_prohibited_not_yours(self):
        """
        Ensures that we can't delete a body that belongs to someone else.
        """
        self.client.force_login(self.user)
        b = BodyFactory(user=self.user2)
        b.save()
        body_id = b.id
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))
        response = self.client.post(b_delete_url)
        self.assertEqual(
            response.status_code,
            403,
            "expected 403 Forbidden; instead returned %s" % response.status_code,
        )
        self.assertTrue(Body.objects.filter(id=body_id).exists())

    def test_prohibited_has_patterns(self):
        """
        Ensures that we can't delete a body that has a pattern attached,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)
        b, ip = self.set_up_body_with_pattern()

        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(b_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "body did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the body and pattern still exist.
        self.assertTrue(Body.even_archived.filter(id=b.id).exists())
        self.assertTrue(IndividualPattern.live_patterns.filter(id=ip.id).exists())

    def test_prohibited_has_archived_patterns(self):
        """
        Ensures that we can't delete a body that has a pattern attached,
        even if archived,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)
        b, ip = self.set_up_body_with_pattern()

        ip.archived = True
        ip.save()

        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(b_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "body did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the body and pattern still exist.
        self.assertTrue(Body.even_archived.filter(id=b.id).exists())
        self.assertTrue(IndividualPattern.approved_patterns.filter(id=ip.id).exists())

    def test_prohibited_has_unapproved_patterns(self):
        """
        Ensures that we can't delete a body that has a pattern attached,
        even if unapproved,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)

        # Do everything in
        #
        #      b, ip = self.set_up_body_with_pattern()
        #
        # except make the Transaction
        ip = TestIndividualPatternWithBodyFactory.for_user(self.user)
        b = ip.get_spec_source().body

        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(b_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "body did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the body and pattern still exist.
        self.assertTrue(Body.even_archived.filter(id=b.id).exists())
        self.assertTrue(IndividualPattern.even_unapproved.filter(id=ip.id).exists())

    def test_faux_deletion_hides_body(self):
        self.client.force_login(self.user)
        b, ip = self.set_up_body_with_pattern()
        b.name = "Totally Unique Body Name"
        b.save()

        b_detail_url = reverse("bodies:body_detail_view", args=(b.id,))
        ip_detail_url = reverse("patterns:individualpattern_detail_view", args=(ip.id,))
        b_list_url = reverse("bodies:body_list_view")
        ip_list_url = reverse("patterns:individualpattern_list_view")

        # Confirm that the test is clean (body and pattern are present before
        # deletion)
        response = self.client.get(b_list_url)
        self.assertContains(response, "Totally Unique Body Name")
        self.assertContains(response, b_detail_url)
        response = self.client.get(ip_list_url)
        self.assertContains(response, ip.name)
        self.assertContains(response, ip_detail_url)

        # Post to the body deletion URL. Be sure to follow the redirect to
        # 'consume' the 'deletion successful' page.
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))
        self.client.post(b_delete_url, follow=True)

        # The body is not visible in the user's list of bodies.
        response = self.client.get(b_list_url)
        self.assertNotContains(response, "Totally Unique Body Name")
        self.assertNotContains(response, b_detail_url)

        # The pattern is visible in the user's list of patterns.
        response = self.client.get(ip_list_url)
        self.assertContains(response, ip.name)
        self.assertContains(response, ip_detail_url)

    def test_faux_deleted_bodies_do_not_count_against_max(self):
        self.client.force_login(self.user)

        # Make sure we start with zero bodies.
        for body in Body.even_archived.filter(user=self.user):
            body.delete()

        # Max the user out on bodies.
        i = 1
        while i < MAX_BODIES:
            b = BodyFactory(user=self.user)
            b.save()
            i += 1

        b, ip = self.set_up_body_with_pattern()

        # Verify that the user cannot create new bodies.
        self.assertEqual(Body.objects.filter(user=self.user).count(), 10)
        self.assertFalse(self.user.profile.can_create_new_bodies)

        # Faux-delete the body that has a pattern attached.
        b_delete_url = reverse("bodies:body_delete_view", args=(b.id,))
        _ = self.client.post(b_delete_url)

        # Verify that the user can create new bodies.
        self.assertEqual(Body.objects.filter(user=self.user).count(), 9)
        self.assertTrue(self.user.profile.can_create_new_bodies)


class BodyCopyViewTests(TestCase):

    def setUp(self):
        self.user = UserFactory()
        self.metric_user = MetricUserFactory()

        self.body = BodyFactory(user=self.user)
        self.url = reverse("bodies:body_copy_view", args=(self.body.pk,))

        self.metric_body = BodyFactory(user=self.metric_user)
        self.metric_url = reverse("bodies:body_copy_view", args=(self.metric_body.pk,))

    def tearDown(self):
        self.user.delete()
        self.metric_user.delete()
        super(BodyCopyViewTests, self).tearDown()

    def test_url_resolves(self):
        # Should not throw Resolver404
        response = resolve(self.url)

    def test_form_initial(self):
        """
        Initial form parameters should match those of the copied body,
        except with the name blank.
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        for k, v in list(response.context["form"].initial.items()):
            self.assertEqual(getattr(self.body, k), v)

    def test_form_initial_metric(self):
        """
        Initial form parameters should be those of the copied body but in
        cm (with a margin of error for rounding) if users prefer metric.
        """
        self.client.force_login(self.metric_user)
        response = self.client.get(self.metric_url)
        for k, v in list(response.context["form"].initial.items()):
            if isinstance(v, int) or isinstance(v, float):
                orig = getattr(self.body, k)
                self.assertEqual(round(orig * 2.54), v)
            else:
                self.assertEqual(getattr(self.body, k), v)

    def test_form_post_creates_body(self):
        """
        Form post should result in a new body, which matches the original
        for all measurements.
        """
        self.client.force_login(self.user)
        self.assertNotIn(BODY_SESSION_NAME, self.client.session)

        response = self.client.get(self.url)
        data = response.context["form"].initial
        body_name = "The Postman Always Rings Twice"
        data["name"] = body_name

        # If there's a "None" in here, the test client literally tries
        # to fill in "None" as a field value and then the form doesn't
        # post because it doesn't validate.
        final_data = {k: v for k, v in list(data.items()) if v}
        response = self.client.post(self.url, data=final_data)

        body = Body.objects.get(name=body_name)
        copyable_fields = ESSENTIAL_FIELDS + EXTRA_FIELDS + OPTIONAL_FIELDS
        copyable_fields.remove("name")

        for field in copyable_fields:
            self.assertEqual(getattr(body, field), getattr(self.body, field))

        session = self.client.session
        self.assertEqual(session[BODY_SESSION_NAME], body.id)

        body.delete()

    def test_form_post_changed_parameters(self):
        """
        If we change parameters before posting the form, those changed
        parameters should be reflected in the new body.
        """
        self.client.force_login(self.user)
        response = self.client.get(self.url)

        data = response.context["form"].initial
        body_name = "The Postman Always Rings Twice"
        data["name"] = body_name
        data["upper_torso_circ"] = data["upper_torso_circ"] + 1

        final_data = {k: v for k, v in list(data.items()) if v}
        response = self.client.post(self.url, data=final_data)

        body = Body.objects.get(name=body_name)
        copyable_fields = ESSENTIAL_FIELDS + EXTRA_FIELDS + OPTIONAL_FIELDS
        copyable_fields.remove("name")

        for field in copyable_fields:
            if field != "upper_torso_circ":
                self.assertEqual(getattr(body, field), getattr(self.body, field))

        self.assertEqual(body.upper_torso_circ, self.body.upper_torso_circ + 1)

        body.delete()

    def test_form_post_changed_parameters_metric(self):
        """
        If we post to the form in metric units, they should be converted
        appropriately to imperial in the saved body.
        """
        self.client.force_login(self.metric_user)
        response = self.client.get(self.metric_url)

        data = response.context["form"].initial
        body_name = "The Postman Always Rings Twice"
        data["name"] = body_name
        data["upper_torso_circ"] = data["upper_torso_circ"] + 1

        final_data = {k: v for k, v in list(data.items()) if v}
        response = self.client.post(self.metric_url, data=final_data)

        body = Body.objects.get(name=body_name)
        copyable_fields = ESSENTIAL_FIELDS + EXTRA_FIELDS + OPTIONAL_FIELDS
        copyable_fields.remove("name")

        for field in copyable_fields:
            if field != "upper_torso_circ":
                body_value = getattr(body, field)
                if isinstance(body_value, float) or isinstance(body_value, int):
                    self.assertEqual(
                        round(body_value), round(getattr(self.body, field))
                    )
                else:
                    self.assertEqual(body_value, getattr(self.body, field))

        self.assertEqual(
            round(body.upper_torso_circ), round(self.body.upper_torso_circ + 1)
        )

        body.delete()

    def test_access_permissions(self):
        """
        Users can only see the clone page if they own the cloned body.
        """
        self.client.force_login(self.user)
        response = self.client.get(self.metric_url)
        self.assertEqual(response.status_code, 403)

    def test_body_creation_permissions(self):
        """
        Users can only see the clone page if can_create_new_bodies is True.
        """
        # We've already verified that users CAN see the page, if above
        # tests pass, so we really only have to check that they CAN'T if
        # can_create_new_bodies is False.
        i = Body.objects.filter(user=self.user).count()
        while i <= MAX_BODIES:
            BodyFactory(name="body #%s" % i, user=self.user)
            i += 1

        self.assertFalse(self.user.profile.can_create_new_bodies)
        self.client.force_login(self.user)
        response = self.client.get(self.url, follow=True)
        self.assertRedirects(response, reverse("bodies:body_list_view"))

        goal_warning = """
            <li class="alert alert-info warning">
            Whoops! You can&#39;t have more than 10 measurement sets at a time. You may delete
            existing measurement sets as long as you haven\'t created any patterns for them.
            There&#39;s a link at the bottom of each details page.
            </li>
        """
        #        self.assertEqual(str(response), None)
        self.assertContains(response, goal_warning, html=True)

    def test_detail_page_shows_option(self):
        """
        People who aren't allowed to create new bodies don't see option on
        detail page; people who are, do
        """
        self.client.force_login(self.user)
        detail_url = reverse("bodies:body_detail_view", args=(self.body.pk,))
        response = self.client.get(detail_url)

        self.assertTrue(self.user.profile.can_create_new_bodies)
        self.assertContains(response, self.url)

        i = Body.objects.filter(user=self.user).count()
        while i <= MAX_BODIES:
            BodyFactory(name="body #%s" % i, user=self.user)
            i += 1

        # Re-fetch page to see changes
        response = self.client.get(detail_url)

        self.assertFalse(self.user.profile.can_create_new_bodies)
        self.assertNotContains(response, self.url)

    def test_buttons_go_to_design_and_home(self):
        self.logged_in = self.client.force_login(self.user)
        response = self.client.get(self.url)
        # Test presence of buttons
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_home" value="save and go to account home" '
            'class="btn btn-primary btn-customfit-outline" id="submit_to_home_1"/>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit_to_pattern_1"/>',
            html=True,
        )

        data = response.context["form"].initial
        body_name = "The Postman Always Rings Twice"
        data["name"] = body_name
        data["upper_torso_circ"] = data["upper_torso_circ"] + 1

        final_data = {k: v for k, v in list(data.items()) if v}

        response = self.client.post(self.url, final_data, follow=True)
        self.assertRedirects(response, reverse("home_view"))
        final_data["submit_to_pattern"] = "submit"
        response = self.client.post(self.url, final_data, follow=True)
        self.assertRedirects(response, reverse("design_wizard:choose_type"))


class MeasurementsTest(TestCase):
    #
    # Well-formed / expected use-case tests
    #
    maxDiff = None

    def test_create_default_body(self):
        b = BodyFactory()
        b.full_clean()

    def test_sanity_check_csv_bodies(self):
        for b_name in list(csv_bodies.keys()):
            b = get_csv_body(b_name)
            b.full_clean()

    def test_to_dict(self):
        b = BodyFactory()
        generated_dict = b.to_dict()
        original_dict = copy.copy(generated_dict)
        self.assertIn("id", generated_dict)
        self.assertIn("user", generated_dict)
        self.assertIn("name", generated_dict)

        del generated_dict["user"]
        del generated_dict["id"]
        del generated_dict["name"]
        del generated_dict["featured_pic"]

        goal_dict = {
            "armpit_to_short_sleeve": 1,
            "low_hip_circ": 42,
            "high_hip_circ": 37,
            "upper_torso_circ": 38,
            "tunic_circ": 44,
            "armpit_to_elbow_sleeve": 6,
            "armpit_to_low_hip": 18,
            "armpit_to_tunic": 24,
            "bicep_circ": 12,
            "armpit_to_waist": 9,
            "forearm_circ": 10,
            "inter_nipple_distance": 8,
            "wrist_circ": 6,
            "med_hip_circ": 40,
            "armpit_to_three_quarter_sleeve": 12,
            "armhole_depth": 8,
            "armpit_to_high_hip": 14.5,
            "elbow_circ": 10,
            "waist_circ": 32,
            "armpit_to_med_hip": 16,
            "notes": "",
            "bust_circ": 41,
            "armpit_to_full_sleeve": 17.5,
            "body_type": "body_type_adult_woman",
            "cross_chest_distance": None,
            "archived": False,
        }
        self.assertDictEqual(generated_dict, goal_dict)

        user = b.user
        new_body = Body.from_dict(original_dict, user)
        new_body.full_clean()

    def test_save_default_body(self):
        b = BodyFactory()
        b.user.save()
        b.save()
        b.delete()

    def test_body_unicode(self):
        body = BodyFactory(name="Alice")
        self.assertEqual(body.__str__(), "Alice")

    # TODO: Does this belong here?
    def test_body_get_absolute_url(self):
        body = BodyFactory()
        body.save()
        url = "/measurement/%d/" % body.id
        self.assertEqual(body.get_absolute_url(), url)

    #
    # Error cases
    #

    def test_dimensions_bad_1(self):
        b = BodyFactory()
        b.armpit_to_elbow_sleeve = b.armpit_to_short_sleeve - 1
        self.assertRaises(ValidationError, b.clean)

    def test_single_size_bad_2(self):
        b = BodyFactory()
        b.armpit_to_three_quarter_sleeve = b.armpit_to_elbow_sleeve - 1
        self.assertRaises(ValidationError, b.clean)

    def test_single_size_bad_3(self):
        b = BodyFactory()
        b.armpit_to_full_sleeve = b.armpit_to_three_quarter_sleeve - 1
        self.assertRaises(ValidationError, b.clean)

    # test_single_size_bad_4 removed for being obsolete

    def test_single_size_bad_5(self):
        b = BodyFactory()
        b.wrist_circ = b.bicep_circ + 1
        self.assertRaises(ValidationError, b.clean)

    def test_single_size_bad_6(self):
        b = BodyFactory()
        b.armpit_to_med_hip = b.armpit_to_high_hip - 1
        self.assertRaises(ValidationError, b.clean)

    def test_single_size_bad_7(self):
        b = BodyFactory()
        b.armpit_to_low_hip = b.armpit_to_med_hip - 1
        self.assertRaises(ValidationError, b.clean)

    def test_single_size_bad_8(self):
        b = BodyFactory()
        b.armpit_to_tunic = b.armpit_to_low_hip - 1
        self.assertRaises(ValidationError, b.clean)

    #
    # Measurements properties on Body class
    #
    def test_essential_measurement_values(self):
        b = BodyFactory()
        result = list(b.essential_measurement_values)
        expected = [
            {"name": "full bust/chest", "value": 41},
            {"name": "waist circumference", "value": 32},
            {"name": "body circumference at average sweater hem", "value": 40},
            {"name": "armhole depth", "value": 8},
            {"name": "average sweater length from armhole to hem", "value": 16},
            {"name": "long sleeve length (from armhole to cuff)", "value": 17.5},
            {"name": "wrist circumference", "value": 6},
            {"name": "bicep circumference", "value": 12},
        ]
        self.assertEqual(result, expected)

    def test_essential_property_matches_field_list(self):
        """
        Because we hardcode the list of fields (in order to control the order,
        so that users will always see fields presented in the same order as on
        the measurement entry page), it's possible that the list of fields
        returned by the essentials measurement property could get out of sync
        with the actual list of essential fields, should we change that
        list. This test ensures that the output of essential_measurement_values
        is the same as the output of feeding ESSENTIAL_FIELDS (less name and
        body) directly into _measurement_sublist would have been.
        """
        b = BodyFactory()
        result = b.essential_measurement_values

        essential_fields = copy.copy(ESSENTIAL_FIELDS)
        essential_fields.remove("name")
        essential_fields.remove("body_type")
        essentials = b._measurement_sublist(essential_fields)
        self.assertTrue(all([x in essentials for x in result]))
        self.assertEqual(len(result), len(essentials))

    def test_extra_measurement_values(self):
        b = BodyFactory()
        result = b.extra_measurement_values
        expected = [
            {"name": "upper torso circumference", "value": 38},
            {"name": "elbow circumference", "value": 10},
            {"name": "forearm circumference", "value": 10},
            {"name": "short sleeve to armhole", "value": 1},
            {"name": "elbow sleeve to armhole", "value": 6},
            {"name": "3/4 sleeve to armhole", "value": 12},
            {"name": "waist (up) to armhole shaping", "value": 9},
            {"name": "short sweater length from armhole to hem", "value": 14.5},
            {"name": "body circumference at short sweater hem", "value": 37},
            {"name": "long sweater length from armhole to hem", "value": 18},
            {"name": "body circumference at long sweater hem", "value": 42},
            {"name": "tunic sweater length from armhole to hem", "value": 24},
            {"name": "body circumference at tunic sweater hem", "value": 44},
        ]
        self.assertEqual(result, expected)

    def test_extra_property_matches_field_list(self):
        b = BodyFactory()
        result = b.extra_measurement_values
        extras = b._measurement_sublist(EXTRA_FIELDS)
        self.assertTrue(all([x in extras for x in result]))
        self.assertEqual(len(result), len(extras))

    def test_optional_measurement_values(self):
        b = BodyFactory()
        result = b.optional_measurement_values
        expected = [
            {"name": "cross-chest distance", "value": None},
            {"name": "inter-nipple distance", "value": 8},
        ]
        self.assertEqual(result, expected)

    def test_optional_property_matches_field_list(self):
        b = BodyFactory()
        result = b.optional_measurement_values
        optionals = b._measurement_sublist(OPTIONAL_FIELDS)
        self.assertTrue(all([x in optionals for x in result]))
        self.assertEqual(len(result), len(optionals))

    def test_has_measurements_methods(self):
        b = BodyFactory()
        self.assertTrue(b.has_any_extra_measurements)
        self.assertTrue(b.has_all_extra_measurements)
        self.assertTrue(b.has_any_optional_measurements)

        sb = SimpleBodyFactory()

        self.assertFalse(sb.has_any_extra_measurements)
        self.assertFalse(sb.has_all_extra_measurements)
        self.assertFalse(sb.has_any_optional_measurements)

        sb2 = SimpleBodyFactory(
            inter_nipple_distance=8, armpit_to_elbow_sleeve=6, high_hip_circ=37
        )

        self.assertTrue(sb2.has_any_extra_measurements)
        self.assertFalse(sb.has_all_extra_measurements)
        self.assertTrue(sb2.has_any_optional_measurements)

    def test_remove_fields_and_clean(self):
        b = BodyFactory()

        # Can remove the optionals and the body should still clean
        for field in OPTIONAL_FIELDS:
            setattr(b, field, None)
            b.clean()

        # Can remove an extra and clean does not throw error
        for field in EXTRA_FIELDS:
            old_val = getattr(b, field)
            setattr(b, field, None)
            b.clean()
            setattr(b, field, old_val)

        # Can remove all extras clean works
        for field in EXTRA_FIELDS:
            setattr(b, field, None)
        b.clean()

        # Can remove any essential and full_clean() (not clean) should
        # throw error
        for field in ESSENTIAL_FIELDS:
            old_val = getattr(b, field)
            setattr(b, field, None)
            with self.assertRaises(ValidationError):
                b.full_clean()
            setattr(b, field, old_val)

    def test_body_type(self):
        man = MaleBodyFactory()
        self.assertEqual(man.body_type, Body.BODY_TYPE_ADULT_MAN)
        self.assertTrue(man.is_man)
        self.assertFalse(man.is_woman)
        self.assertFalse(man.is_child)
        self.assertFalse(man.is_unstated_type)

        woman = FemaleBodyFactory()
        self.assertEqual(woman.body_type, Body.BODY_TYPE_ADULT_WOMAN)
        self.assertFalse(woman.is_man)
        self.assertTrue(woman.is_woman)
        self.assertFalse(woman.is_child)
        self.assertFalse(woman.is_unstated_type)

        child = ChildBodyFactory()
        self.assertEqual(child.body_type, Body.BODY_TYPE_CHILD)
        self.assertFalse(child.is_man)
        self.assertFalse(child.is_woman)
        self.assertTrue(child.is_child)
        self.assertFalse(child.is_unstated_type)

        unstated = UnstatedTypeBodyFactory()
        self.assertEqual(unstated.body_type, Body.BODY_TYPE_UNSTATED)
        self.assertFalse(unstated.is_man)
        self.assertFalse(unstated.is_woman)
        self.assertFalse(unstated.is_child)
        self.assertTrue(unstated.is_unstated_type)


class SimpleMeasurementsTest(TestCase):

    #
    # Well-formed / expected use-case tests
    #
    maxDiff = None

    def test_create_default_body(self):
        b = SimpleBodyFactory()
        b.full_clean()

    def test_to_dict(self):
        b = SimpleBodyFactory()
        generated_dict = b.to_dict()
        original_dict = copy.copy(generated_dict)
        self.assertIn("id", generated_dict)
        self.assertIn("user", generated_dict)
        self.assertIn("name", generated_dict)

        del generated_dict["user"]
        del generated_dict["id"]
        del generated_dict["name"]
        del generated_dict["featured_pic"]

        goal_dict = {
            "armpit_to_short_sleeve": None,
            "low_hip_circ": None,
            "high_hip_circ": None,
            "upper_torso_circ": None,
            "tunic_circ": None,
            "armpit_to_elbow_sleeve": None,
            "armpit_to_low_hip": None,
            "armpit_to_tunic": None,
            "bicep_circ": 12,
            "armpit_to_waist": None,
            "forearm_circ": None,
            "inter_nipple_distance": None,
            "wrist_circ": 6,
            "med_hip_circ": 40,
            "armpit_to_three_quarter_sleeve": None,
            "armhole_depth": 8,
            "armpit_to_high_hip": None,
            "elbow_circ": None,
            "waist_circ": 32,
            "armpit_to_med_hip": 16,
            "notes": "",
            "bust_circ": 41,
            "armpit_to_full_sleeve": 17.5,
            "body_type": "body_type_unstated",
            "cross_chest_distance": None,
            "archived": False,
        }
        self.assertDictEqual(generated_dict, goal_dict)

        user = b.user
        new_body = Body.from_dict(original_dict, user)
        new_body.full_clean()

    def test_save_default_body(self):
        b = SimpleBodyFactory()
        b.user.save()
        b.save()
        b.delete()


class BodyDetailViewTests(TestCase):
    pass


class BodyDetailPdfViewTests(TestCase):

    def _make_url(self, body):
        return reverse(
            "bodies:body_detail_view_pdf",
            args=[
                body.id,
            ],
        )

    def test_user_can_get_pdf(self):
        user = UserFactory()
        body = BodyFactory(user=user, name="test body 1")
        self.client.force_login(user)
        url = self._make_url(body)

        detail_view_resp = self.client.get(
            reverse(
                "bodies:body_detail_view",
                args=[
                    body.id,
                ],
            )
        )
        self.assertContains(
            detail_view_resp,
            """
                            <a href="%s" class="btn-customfit-outline">Download as PDF</a>
                            """
            % url,
            html=True,
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Disposition"], 'attachment; filename="test-body-1.pdf"'
        )


class GradeTests(TestCase):

    def test_factory(self):
        grade = GradeFactory()
        grade.clean()
        # Note that the grade-set has other grades, too.
        self.assertEqual(grade.grade_set.grades.count(), 6)

    def test_body_type(self):
        grade = GradeFactory(grade_set__body_type=Body.BODY_TYPE_CHILD)
        self.assertEqual(grade.body_type, Body.BODY_TYPE_CHILD)


class GradeSetTests(TestCase):

    def test_factory(self):
        gs = GradeSetFactory()
        self.assertEqual(gs.grades.count(), 5)
