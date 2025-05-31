import copy

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse

from customfit.helpers.magic_constants import CM_PER_INCHES, YARDS_PER_METRE
from customfit.patterns.factories import (
    ApprovedPatternFactory,
    IndividualPatternFactory,
)
from customfit.patterns.models import IndividualPattern
from customfit.test_garment.factories import (
    TestApprovedIndividualPatternFactory,
    TestPatternSpecFactory,
    pattern_from_pspec_and_redo_kwargs,
)
from customfit.userauth.factories import MetricUserFactory, UserFactory

from .factories import SwatchFactory, csv_swatches, get_csv_swatch
from .models import UNKNOWN_STITCH_TYPE, Swatch
from .views import SWATCH_SESSION_NAME

##############################################################################
#
# Tests
#
##############################################################################


class SwatchCreateViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.metric_user = MetricUserFactory()
        self.sname = "swatch1"
        sstitches = 12
        sstitches_len = 4
        srows = 10
        srows_len = 4
        self.sneedle = "random text"
        self.post_entries = {
            "name": self.sname,
            "stitches_number": sstitches,
            "stitches_length": sstitches_len,
            "rows_number": srows,
            "rows_length": srows_len,
            "needle_size": self.sneedle,
        }
        self.post_metric_entries = {}
        for key, value in list(self.post_entries.items()):
            if isinstance(value, int) or isinstance(value, float):
                self.post_metric_entries[key] = float(value) * CM_PER_INCHES
            else:
                self.post_metric_entries[key] = value

    def test_swatch_create_page(self):
        # tests that the SwatchCreateView displays the expected HTML
        self.logged_in = self.client.force_login(self.user)
        response = self.client.get(reverse("swatches:swatch_create_view"))
        self.assertContains(response, "<h2>Your gauge</h2>")

    def test_create_basic_swatch(self):
        """
        tests that the SwatchCreateView displays and creates a swatch
        """
        self.logged_in = self.client.force_login(self.user)
        self.assertNotIn(SWATCH_SESSION_NAME, self.client.session)

        response = self.client.get(reverse("swatches:swatch_create_view"))
        self.assertEqual(
            response.status_code, 200, "create a swatch page does not display"
        )

        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries
        )
        swatch = Swatch.objects.get(name=self.sname)
        self.assertIsNotNone(swatch, "there is no swatch")
        self.assertEqual(swatch.user, self.user, "user not saved with swatch")
        self.assertEqual(swatch.name, self.sname, "name not saved with swatch")
        self.assertEqual(
            swatch.stitches_number, 12, "stitches_number not saved with swatch"
        )
        self.assertEqual(
            swatch.needle_size, self.sneedle, "needle_info not saved with swatch"
        )

        session = self.client.session
        self.assertEqual(session[SWATCH_SESSION_NAME], swatch.id)

    def test_swatch_must_have_name(self):
        self.logged_in = self.client.force_login(self.user)
        self.post_entries["name"] = ""
        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries
        )
        with self.assertRaises(Swatch.DoesNotExist):
            swatch = Swatch.objects.get(user=self.user)

    def test_swatch_must_have_stitches_number_gt_zero(self):
        self.logged_in = self.client.force_login(self.user)
        self.post_entries["stitches_number"] = 0
        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries
        )
        with self.assertRaises(Swatch.DoesNotExist):
            swatch = Swatch.objects.get(user=self.user)

    def test_submit_buttons_no_next_url(self):
        self.logged_in = self.client.force_login(self.user)
        response = self.client.get(reverse("swatches:swatch_create_view"))
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_home" value="Save and go to account home" '
            'class="btn btn-primary btn-customfit-outline" id="submit-to-home-1"/>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="Save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit-to-pattern-1"/>',
            html=True,
        )
        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries, follow=True
        )
        self.assertRedirects(response, reverse("home_view"))
        self.post_entries["submit_to_pattern"] = "submit"
        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries, follow=True
        )
        self.assertRedirects(response, reverse("design_wizard:choose_type"))

    def test_submit_buttons_with_next_url(self):
        self.logged_in = self.client.force_login(self.user)
        url = reverse("swatches:swatch_create_view") + "?next=/some/url"
        response = self.client.get(url)
        self.assertNotContains(
            response,
            '<input type="submit" name="submit_to_home" value="Save and go to account home" '
            'class="btn btn-primary btn-customfit-outline" id="submit-to-home-1"/>',
            html=True,
        )
        self.assertNotContains(
            response,
            '<input type="submit" name="submit_to_pattern" value="Save and make a pattern" '
            'class="btn btn-primary btn-customfit-action" id="submit-to-pattern-1"/>',
            html=True,
        )
        self.assertContains(
            response,
            '<input type="submit" name="submit" value="Save" '
            'class="btn btn-primary btn-customfit-action" id="submit-1"/>',
            html=True,
        )
        response = self.client.post(url, self.post_entries, follow=False)
        self.assertRedirects(response, "/some/url", fetch_redirect_response=False)

    def test_create_swatch_with_all_optional_parameters(self):
        self.logged_in = self.client.force_login(self.user)
        self.post_entries["yarn_maker"] = "Best Yarn Company"
        self.post_entries["yarn_name"] = "Yellow Yarn"
        self.post_entries["length_per_hank"] = 5
        self.post_entries["weight_per_hank"] = 5
        self.post_entries["full_swatch_width"] = 5
        self.post_entries["full_swatch_height"] = 5
        self.post_entries["full_swatch_weight"] = 5
        self.post_entries["notes"] = "This is the best yellow yarn ever!"
        response = self.client.post(
            reverse("swatches:swatch_create_view"), self.post_entries
        )
        swatch = Swatch.objects.get(name=self.sname)
        self.assertEqual(
            swatch.yarn_maker, "Best Yarn Company", "yarn maker not saved with swatch"
        )
        self.assertEqual(
            swatch.length_per_hank, 5, "length per hank not saved with swatch"
        )
        self.assertEqual(
            swatch.full_swatch_weight, 5, "full swatch weight not saved with swatch"
        )

    def test_converting_measurement_units(self):
        # test that if the user is using metric it gets converted to imperial in the db.
        self.logged_in = self.client.force_login(self.metric_user)
        post_metric_entries = copy.copy(self.post_entries)
        post_metric_entries["stitches_length"] = 10
        post_metric_entries["rows_length"] = 10
        post_metric_entries["full_swatch_width"] = 15

        response = self.client.post(
            reverse("swatches:swatch_create_view"), post_metric_entries
        )
        swatch = Swatch.objects.get(name=self.sname)

        self.assertAlmostEqual(swatch.full_swatch_width, 5.906, 2)

        self.assertEqual(swatch.stitches_number, self.post_entries["stitches_number"])
        self.assertEqual(swatch.rows_number, self.post_entries["rows_number"])

        # Test that the conversion to imperial was accurate
        self.assertAlmostEqual(swatch.stitches_length, 3.937007, 4)
        self.assertAlmostEqual(swatch.rows_length, 3.937007, 4)


class SwatchUpdateViewTest(TestCase):
    def setUp(self):
        self.client = Client()

        # Set up users
        self.user = UserFactory()
        self.metric_user = MetricUserFactory()

        # Set up swatch parameters
        self.sname = "swatch1"
        self.sstitches = 12
        self.sstitches_len = 4
        self.srows = 10
        self.srows_len = 4
        self.sneedle = "random text"
        self.post_entries = {
            "name": self.sname,
            "stitches_number": self.sstitches,
            "stitches_length": self.sstitches_len,
            "rows_number": self.srows,
            "rows_length": self.srows_len,
            "needle_size": self.sneedle,
            "user": self.user,
        }
        swatch = Swatch.objects.create(**self.post_entries)
        swatch.save()
        self.swatch = swatch
        self.swatch_update_url = reverse(
            "swatches:swatch_update_view", args=(swatch.pk,)
        )

        # Set up metric parameters
        self.post_metric_entries = {}
        for key, value in list(self.post_entries.items()):
            if isinstance(value, int) or isinstance(value, float):
                self.post_metric_entries[key] = float(value) * CM_PER_INCHES
            else:
                self.post_metric_entries[key] = value

        # We use post_entries, not post_metric_entries, to create the
        # swatch, since using create() means we're speaking directly
        # in database units, not running through any sort of conversion.
        metric_swatch = Swatch.objects.create(**self.post_entries)
        metric_swatch.user = self.metric_user
        metric_swatch.save()
        self.metric_swatch = metric_swatch
        self.metric_update_url = reverse(
            "swatches:swatch_update_view", args=(metric_swatch.pk,)
        )

    def test_update_basic_swatch_displays(self):
        """
        Test that SwatchUpdateView displays the expected swatch.
        """
        _ = self.client.force_login(self.user)
        response = self.client.get(self.swatch_update_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.sname)

    def test_update_basic_swatch_updates(self):
        """
        Test that SwatchUpdateView updates swatch parameters.
        """
        _ = self.client.force_login(self.user)
        self.assertNotIn(SWATCH_SESSION_NAME, self.client.session)

        swatch_pk = self.swatch.pk

        response = self.client.get(self.swatch_update_url)
        form = response.context["form"]
        params = {k: v for k, v in list(form.initial.items()) if v}
        params.update({"needle_size": "new text", "weight_per_hank": 75})

        response = self.client.post(self.swatch_update_url, params)

        # We need to explicitly get the object from the db to force
        # its properties to refresh.
        swatch = Swatch.objects.get(pk=swatch_pk)

        # Check that parameters that should not have changed, didn't
        self.assertEqual(swatch.name, self.sname)
        self.assertEqual(swatch.stitches_length, self.sstitches_len)
        self.assertEqual(swatch.rows_number, self.srows)
        self.assertEqual(swatch.rows_length, self.srows_len)
        self.assertEqual(swatch.stitches_number, self.sstitches)

        # Check that parameters that should have changed, did
        self.assertEqual(swatch.needle_size, "new text")
        self.assertEqual(swatch.weight_per_hank, 75)

        session = self.client.session
        self.assertEqual(session[SWATCH_SESSION_NAME], self.swatch.id)

    def test_converting_measurement_units(self):
        """
        Test that if the user is using metric it gets converted to imperial
        in the db.
        """
        _ = self.client.force_login(self.metric_user)

        # Get nonempty existing form values and augment them with new values
        # for some of the editable fields
        response = self.client.get(self.metric_update_url)
        form = response.context["form"]
        params = {k: v for k, v in list(form.initial.items()) if v}
        params.update(
            {
                "length_per_hank": 300,  # in metres, should become yds
                "full_swatch_width": 15,
            }
        )  # in cm, should become in

        response = self.client.post(self.metric_update_url, params)
        swatch = Swatch.objects.get(pk=self.metric_swatch.pk)

        self.assertAlmostEqual(swatch.length_per_hank, 300 * YARDS_PER_METRE)
        self.assertAlmostEqual(swatch.full_swatch_width, 15 / CM_PER_INCHES)

    def test_display_metric_units(self):
        """
        Test that if the user is using metric it gets displayed as metric in
        the edit form (even though it is stored as imperial in the db).
        """
        pass


class SwatchDeleteViewTest(TestCase):
    def setUp(self):
        super(SwatchDeleteViewTest, self).setUp()
        self.client = Client()
        self.user = UserFactory()
        self.user2 = UserFactory()

    def set_up_swatch_with_pattern(self):
        # A pattern must have a successful transaction to be approved.
        # Only approved patterns block deletion.
        ip = TestApprovedIndividualPatternFactory.for_user(self.user)
        s = ip.swatch
        return s, ip

    def test_get_no_patterns(self):
        self.client.force_login(self.user)
        s = SwatchFactory()
        s.user = self.user
        s.save()
        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        response = self.client.get(s_delete_url)
        self.assertNotContains(
            response,
            "<p>(Don't worry; the patterns you've made from this gauge won't be deleted.)</p>",
            html=True,
        )

    def test_get_with_patterns(self):
        p = TestApprovedIndividualPatternFactory()
        swatch = p.get_spec_source().swatch
        user = p.user
        self.client.force_login(user)
        s_delete_url = reverse("swatches:swatch_delete_view", args=(swatch.id,))
        response = self.client.get(s_delete_url)
        self.assertContains(
            response,
            "<p>(Don't worry; the patterns you've made from this gauge won't be deleted.)</p>",
            html=True,
        )

    def test_basic_deletion(self):
        """
        Ensures that we can delete a swatch.
        """
        self.client.force_login(self.user)
        s = SwatchFactory()
        s.user = self.user
        s.save()
        swatch_id = s.id
        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        response = self.client.post(s_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "swatch did not delete; instead returned %s" % response.status_code,
        )
        self.assertFalse(Swatch.objects.filter(id=swatch_id).exists())

    def test_session_handling(self):
        self.client.force_login(self.user)
        s = SwatchFactory(user=self.user)

        session = self.client.session
        session[SWATCH_SESSION_NAME] = s.id
        session.save()

        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        response = self.client.post(s_delete_url)

        session = self.client.session
        self.assertNotIn(SWATCH_SESSION_NAME, session)

    def test_session_handling_other_swatch(self):
        self.client.force_login(self.user)
        s = SwatchFactory(user=self.user)
        s2 = SwatchFactory(user=self.user)

        session = self.client.session
        session[SWATCH_SESSION_NAME] = s2.id
        session.save()

        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        response = self.client.post(s_delete_url)

        session = self.client.session
        self.assertEqual(session[SWATCH_SESSION_NAME], s2.id)

    def test_prohibited_not_yours(self):
        """
        Ensures that we can't delete a swatch that belongs to someone else.
        """
        self.client.force_login(self.user)
        s = SwatchFactory()
        s.user = self.user2
        s.save()
        swatch_id = s.id
        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        response = self.client.post(s_delete_url)
        self.assertEqual(
            response.status_code,
            403,
            "expected 403 Forbidden; instead returned %s" % response.status_code,
        )
        self.assertTrue(Swatch.objects.filter(id=swatch_id).exists())

    def test_prohibited_has_patterns(self):
        """
        Ensures that we can't delete a swatch that has a pattern attached,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)
        s, ip = self.set_up_swatch_with_pattern()

        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(s_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "swatch did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the swatch and pattern still exist.
        self.assertTrue(Swatch.even_archived.filter(id=s.id).exists())
        self.assertTrue(IndividualPattern.approved_patterns.filter(id=ip.id).exists())

    def test_prohibited_has_archived_patterns(self):
        """
        Ensures that we can't delete a swatch that has a pattern attached,
        even if the pattern is archived,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)
        s, ip = self.set_up_swatch_with_pattern()

        ip.archived = True
        ip.save()

        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(s_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "swatch did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the swatch and pattern still exist.
        self.assertTrue(Swatch.even_archived.filter(id=s.id).exists())
        self.assertTrue(IndividualPattern.approved_patterns.filter(id=ip.id).exists())

    def test_prohibited_has_unapproved_patterns(self):
        """
        Ensures that we can't delete a swatch that has a pattern attached,
        even if the pattern is unapproved,
        and attempting to delete it does not delete its pattern.
        """
        self.client.force_login(self.user)

        # Do all of
        #
        #      s, ip = self.set_up_swatch_with_pattern()
        #
        # except make the Transaction
        ip = TestApprovedIndividualPatternFactory.for_user(self.user)
        s = ip.swatch

        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))

        # Posting to the delete URL returns a successful HTTP response.
        response = self.client.post(s_delete_url)
        self.assertEqual(
            response.status_code,
            302,
            "swatch did not faux-delete; instead returned %s" % response.status_code,
        )

        # However, the swatch and pattern still exist.
        self.assertTrue(Swatch.even_archived.filter(id=s.id).exists())
        self.assertTrue(IndividualPattern.even_unapproved.filter(id=ip.id).exists())

    def test_faux_deletion_hides_swatch(self):
        self.client.force_login(self.user)
        s, ip = self.set_up_swatch_with_pattern()
        s.name = "Totally Unique Swatch Name"
        s.save()

        s_detail_url = reverse("swatches:swatch_detail_view", args=(s.id,))
        ip_detail_url = reverse("patterns:individualpattern_detail_view", args=(ip.id,))
        s_delete_url = reverse("swatches:swatch_delete_view", args=(s.id,))
        s_list_url = reverse("swatches:swatch_list_view")
        ip_list_url = reverse("patterns:individualpattern_list_view")

        # Make sure the test is clean (swatch is visible before deletion)
        response = self.client.get(s_list_url)
        self.assertContains(response, "Totally Unique Swatch Name")
        self.assertContains(response, s_detail_url)
        response = self.client.get(ip_list_url)
        self.assertContains(response, ip.name)
        self.assertContains(response, ip_detail_url)

        # Post to the swatch deletion URL.
        self.client.post(s_delete_url, follow=True)

        # The swatch is not visible in the user's list of swatches.
        response = self.client.get(s_list_url)
        self.assertNotContains(response, "Totally Unique Swatch Name")
        self.assertNotContains(response, s_detail_url)

        # The pattern is visible in the user's list of patterns.
        response = self.client.get(ip_list_url)
        self.assertContains(response, ip.name)
        self.assertContains(response, ip_detail_url)


class SwatchMethodTests(TestCase):
    """these test the methods on the Swatch model"""

    def test_SwatchFactory(self):
        swatch = SwatchFactory()
        swatch.full_clean()

    def test_create_delete_csv_swatches(self):
        # Sanity-test: run through all the swatches in the csv file
        for swatch_name in list(csv_swatches.keys()):
            s = get_csv_swatch(swatch_name)
            s.full_clean()

    def test_to_dict(self):
        swatch = SwatchFactory(
            name="test_to_dict swatch", yarn_maker="test_to_dict maker"
        )
        generated_dict = swatch.to_dict()
        original_dict = generated_dict

        for field in ["id", "user", "featured_pic"]:
            self.assertIn(field, generated_dict)
            del generated_dict[field]

        goal_dict = {
            "stitches_per_repeat": None,
            "stitches_length": 1,
            "rows_number": 7,
            "name": "test_to_dict swatch",
            "additional_stitches": None,
            "full_swatch_width": 5.25,
            "yarn_maker": "test_to_dict maker",
            "notes": "",
            "full_swatch_weight": 19,
            "length_per_hank": 220,
            "yarn_name": "Cascade",
            "full_swatch_height": 7.75,
            "use_repeats": False,
            "stitches_number": 5,
            "needle_size": "My favorites!",
            "weight_per_hank": 100,
            "rows_length": 1,
            "archived": False,
        }
        self.assertDictEqual(generated_dict, goal_dict)

        user = UserFactory()

        new_swatch = Swatch.from_dict(original_dict, user)
        new_swatch.full_clean()

    def test_get_stitch1(self):
        swatch = SwatchFactory()
        swatch_stitch = swatch.get_stitch()

        self.assertEqual(swatch_stitch.repeats_x_mod, 0)
        self.assertEqual(swatch_stitch.repeats_mod_y, 1)
        self.assertEqual(swatch_stitch.stitch_type, UNKNOWN_STITCH_TYPE)
        self.assertEqual(swatch_stitch.is_allover_stitch, True)

        self.assertFalse(swatch_stitch.user_visible)
        self.assertFalse(swatch_stitch.is_waist_hem_stitch)
        self.assertFalse(swatch_stitch.is_sleeve_hem_stitch)
        self.assertFalse(swatch_stitch.is_neckline_hem_stitch)
        self.assertFalse(swatch_stitch.is_armhole_hem_stitch)
        self.assertFalse(swatch_stitch.is_buttonband_hem_stitch)
        self.assertFalse(swatch_stitch.is_panel_stitch)
        self.assertFalse(swatch_stitch.is_waist_hem_stitch)
        self.assertFalse(swatch_stitch.chart)
        self.assertFalse(swatch_stitch.photo)

        self.assertIsNone(swatch_stitch._patterntext)
        self.assertIsNone(swatch_stitch.notes)
        self.assertIsNone(swatch_stitch._waist_hem_stitch_template)
        self.assertIsNone(swatch_stitch._sleeve_hem_template)
        self.assertIsNone(swatch_stitch._trim_armhole_template)
        self.assertIsNone(swatch_stitch._trim_neckline_template)
        self.assertIsNone(swatch_stitch._button_band_template)
        self.assertIsNone(swatch_stitch._button_band_veeneck_template)
        self.assertIsNone(swatch_stitch.extra_finishing_instructions)

    def test_get_stitch2(self):
        swatch = SwatchFactory(
            use_repeats=True, stitches_per_repeat=7, additional_stitches=3
        )
        swatch_stitch = swatch.get_stitch()

        self.assertEqual(swatch_stitch.repeats_x_mod, 3)
        self.assertEqual(swatch_stitch.repeats_mod_y, 7)
        self.assertEqual(swatch_stitch.stitch_type, UNKNOWN_STITCH_TYPE)
        self.assertEqual(swatch_stitch.is_allover_stitch, True)

        self.assertFalse(swatch_stitch.user_visible)
        self.assertFalse(swatch_stitch.is_waist_hem_stitch)
        self.assertFalse(swatch_stitch.is_sleeve_hem_stitch)
        self.assertFalse(swatch_stitch.is_neckline_hem_stitch)
        self.assertFalse(swatch_stitch.is_armhole_hem_stitch)
        self.assertFalse(swatch_stitch.is_buttonband_hem_stitch)
        self.assertFalse(swatch_stitch.is_panel_stitch)
        self.assertFalse(swatch_stitch.is_waist_hem_stitch)
        self.assertFalse(swatch_stitch.chart)
        self.assertFalse(swatch_stitch.photo)

        self.assertIsNone(swatch_stitch._patterntext)
        self.assertIsNone(swatch_stitch.notes)
        self.assertIsNone(swatch_stitch._waist_hem_stitch_template)
        self.assertIsNone(swatch_stitch._sleeve_hem_template)
        self.assertIsNone(swatch_stitch._trim_armhole_template)
        self.assertIsNone(swatch_stitch._trim_neckline_template)
        self.assertIsNone(swatch_stitch._button_band_template)
        self.assertIsNone(swatch_stitch._button_band_veeneck_template)
        self.assertIsNone(swatch_stitch.extra_finishing_instructions)

    def test_save_delete_swatch(self):
        swatch = SwatchFactory()
        swatch.save()
        swatch.delete()

    def test_unicode(self):
        sw = SwatchFactory(name="test_unicode swatch")
        self.assertEqual(sw.__str__(), "test_unicode swatch")

    # TODO: write test for get_gauge()

    # TODO: should this really live somewhere else?
    def test_get_url(self):
        sw = SwatchFactory()
        url = "/swatch/%d/" % sw.id
        self.assertEqual(sw.get_absolute_url(), url)

    def test_get_gauge(self):
        sw = SwatchFactory()
        g = sw.get_gauge()
        self.assertEqual(g.stitches, 5)
        self.assertEqual(g.rows, 7)

    def test_patterns(self):

        from customfit.pattern_spec.factories import PatternSpecFactory
        from customfit.patterns.factories import ApprovedPatternFactory

        # Swatch used for original pattern, not redone
        p1 = TestApprovedIndividualPatternFactory()
        user = p1.user
        swatch = p1.get_spec_source().swatch

        pspec2 = TestPatternSpecFactory(user=user, swatch=swatch)
        # Swatch used for original pattern but NOT redone
        p2 = pattern_from_pspec_and_redo_kwargs(pspec2)
        # sanity check
        self.assertNotEqual(
            p2.pieces.schematic.individual_garment_parameters.redo.swatch, swatch
        )
        self.assertEqual(
            p2.original_pieces.schematic.individual_garment_parameters.pattern_spec.swatch,
            swatch,
        )

        pspec3 = TestPatternSpecFactory(user=user, swatch=swatch)
        # Swatch used for original pattern AND redone
        p3 = pattern_from_pspec_and_redo_kwargs(pspec3, swatch=swatch)
        # sanity check
        self.assertEqual(
            p3.pieces.schematic.individual_garment_parameters.redo.swatch, swatch
        )
        self.assertEqual(
            p3.original_pieces.schematic.individual_garment_parameters.pattern_spec.swatch,
            swatch,
        )

        pspec4 = TestPatternSpecFactory(user=user)
        # Swatch used niether for original pattern nor redone
        p4 = pattern_from_pspec_and_redo_kwargs(pspec4)
        # sanity check
        self.assertNotEqual(
            p4.pieces.schematic.individual_garment_parameters.redo.swatch, swatch
        )
        self.assertNotEqual(
            p4.original_pieces.schematic.individual_garment_parameters.pattern_spec.swatch,
            swatch,
        )

        pspec5 = TestPatternSpecFactory(user=user)
        # Swatch used for redo but not original pattern
        p5 = pattern_from_pspec_and_redo_kwargs(pspec5, swatch=swatch)
        # sanity check
        self.assertEqual(
            p5.pieces.schematic.individual_garment_parameters.redo.swatch, swatch
        )
        self.assertNotEqual(
            p5.original_pieces.schematic.individual_garment_parameters.pattern_spec.swatch,
            swatch,
        )

        patterns_of_swatch = swatch.patterns

        self.assertIn(p1, patterns_of_swatch)
        self.assertNotIn(p2, patterns_of_swatch)
        self.assertIn(p3, patterns_of_swatch)
        self.assertNotIn(p4, patterns_of_swatch)
        self.assertIn(p5, patterns_of_swatch)

    #
    # Error cases
    #

    def test_swatch_broken_1(self):
        swatch_broken = SwatchFactory(
            name="default with repeats",
            use_repeats=True,
            #                                      stitches_per_repeat = 4,
            additional_stitches=1,
        )
        self.assertRaises(ValidationError, swatch_broken.full_clean)

    def test_swatch_broken_2(self):
        swatch_broken = SwatchFactory(
            name="default with repeats",
            use_repeats=True,
            stitches_per_repeat=4,
            #                                      additional_stitches = 1
        )
        self.assertRaises(ValidationError, swatch_broken.full_clean)

    # These really test the fields rather than the models
    def test_swatch_broken_7(self):
        swatch_broken = SwatchFactory(stitches_length=0)
        self.assertRaises(ValidationError, swatch_broken.full_clean)

    def test_swatch_broken_8(self):
        swatch_broken = SwatchFactory(stitches_length=-1)
        self.assertRaises(ValidationError, swatch_broken.full_clean)

    def test_weight_valid(self):
        swatch = SwatchFactory(
            full_swatch_weight=19, full_swatch_height=7.75, full_swatch_width=5.25
        )
        self.assertAlmostEqual(swatch.area_to_weight(10), 4.6697, 1)

    def test_weight_invalid(self):
        swatch = SwatchFactory(
            full_swatch_weight=None, full_swatch_height=7.75, full_swatch_width=5.25
        )
        self.assertIsNone(swatch.area_to_weight(10))

        swatch = SwatchFactory(
            full_swatch_weight=19, full_swatch_height=None, full_swatch_width=5.25
        )
        self.assertIsNone(swatch.area_to_weight(10))

        swatch = SwatchFactory(
            full_swatch_weight=19, full_swatch_height=7.75, full_swatch_width=None
        )
        self.assertIsNone(swatch.area_to_weight(10))

    def test_hanks_valid(self):
        swatch = SwatchFactory(
            full_swatch_weight=19,
            weight_per_hank=100,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_hanks(1000), 4.6697, 2)

    def test_hanks_invalid(self):
        swatch = SwatchFactory(
            full_swatch_weight=None,
            weight_per_hank=100,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertIsNone(swatch.area_to_hanks(1000))

        swatch = SwatchFactory(
            full_swatch_weight=19,
            weight_per_hank=None,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertIsNone(swatch.area_to_hanks(1000))

        swatch = SwatchFactory(
            full_swatch_weight=19,
            weight_per_hank=100,
            full_swatch_height=None,
            full_swatch_width=5.25,
        )
        self.assertIsNone(swatch.area_to_hanks(1000))

        swatch = SwatchFactory(
            full_swatch_weight=19,
            weight_per_hank=100,
            full_swatch_height=7.75,
            full_swatch_width=None,
        )
        self.assertIsNone(swatch.area_to_hanks(1000))

    def test_hanks_precise(self):
        swatch = SwatchFactory(
            full_swatch_weight=19,
            stitches_length=1,
            stitches_number=5,
            weight_per_hank=100,
            length_per_hank=220,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 1027.334, 1)
        self.assertTrue(swatch.area_to_yards_of_yarn(1000)[1])

    def test_hanks_imprecise(self):
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            full_swatch_weight=None,
            weight_per_hank=100,
            length_per_hank=220,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 992.295, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])

        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            full_swatch_weight=19,
            weight_per_hank=None,
            length_per_hank=220,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 992.295, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])

        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            full_swatch_weight=19,
            weight_per_hank=100,
            length_per_hank=None,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 992.295, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])

        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            full_swatch_weight=19,
            weight_per_hank=100,
            length_per_hank=220,
            full_swatch_height=None,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 992.295, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])

        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=5,
            full_swatch_weight=19,
            weight_per_hank=100,
            length_per_hank=220,
            full_swatch_height=7.75,
            full_swatch_width=None,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 992.295, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])

    def test_chunky_yarn(self):
        # Make sure we handle chunky yarns ok.

        # If we have full swatch area and weight, then the chunkiness of the yarn shouldn't matter--
        # return a precise estimate
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=2,
            full_swatch_weight=19,
            weight_per_hank=100,
            length_per_hank=220,
            full_swatch_height=7.75,
            full_swatch_width=5.25,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 1027.3425, 1)
        self.assertTrue(swatch.area_to_yards_of_yarn(1000)[1])

        # If we don't have full swatch information, then we should still be able to estimate yardage, even
        # if the yarn us super bulky
        swatch = SwatchFactory(
            stitches_length=1,
            stitches_number=2,
            full_swatch_weight=None,
            weight_per_hank=None,
            length_per_hank=None,
            full_swatch_height=None,
            full_swatch_width=None,
        )
        self.assertAlmostEqual(swatch.area_to_yards_of_yarn(1000)[0], 500, 1)
        self.assertFalse(swatch.area_to_yards_of_yarn(1000)[1])


class GaugeTestCase(TestCase):

    def test_no_repeats(self):
        sw = SwatchFactory(
            stitches_length=2.5, stitches_number=12.5, rows_length=3, rows_number=21
        )
        g = sw.get_gauge()
        self.assertEqual(g.stitches, 5)
        self.assertEqual(g.rows, 7)
        self.assertFalse(g.use_repeats)
        self.assertIsNone(g.x_mod)
        self.assertIsNone(g.mod_y)

    def test_repeats(self):
        sw = SwatchFactory(
            stitches_length=2.5,
            stitches_number=15,
            rows_length=3,
            rows_number=24,
            use_repeats=True,
            stitches_per_repeat=6,
            additional_stitches=0,
        )
        g = sw.get_gauge()
        self.assertEqual(g.stitches, 6)
        self.assertEqual(g.rows, 8)
        self.assertTrue(g.use_repeats)
        self.assertEqual(g.x_mod, 0)
        self.assertEqual(g.mod_y, 6)


class SwatchDetailViewTests(TestCase):
    pass
