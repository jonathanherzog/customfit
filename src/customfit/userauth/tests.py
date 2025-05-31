import tempfile

import django.core.management
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.test.client import Client
from django.urls import reverse

from customfit.patterns.models import IndividualPattern
from customfit.test_garment.factories import TestApprovedIndividualPatternFactory

from .factories import FriendAndFamilyFactory, StaffFactory, UserFactory
from .forms import UserManagementForm


class TestManagementCommand(TestCase):

    def setUp(self):
        super(TestManagementCommand, self).setUp()
        for user in User.objects.all():
            user.delete()
        self.alice = UserFactory()
        self.bob = UserFactory()

    def test_find_username_collisions_no_collisions(self):
        f = tempfile.TemporaryFile(mode="w+")
        django.core.management.call_command("find_username_collisions", stdout=f)
        f.seek(0)
        output = f.read()
        self.assertEqual(output, "No collisions found")

    def test_find_username_collisions_yes_collisions(self):

        real_name = self.alice.username
        upper_name = real_name.upper()
        self.assertNotEqual(real_name, upper_name)

        real_email = self.alice.email
        other_email = "not" + real_email
        self.assertNotEqual(real_email, other_email)

        UserFactory(username=upper_name, email="not" + self.alice.email)

        f = tempfile.TemporaryFile(mode="w+")
        django.core.management.call_command("find_username_collisions", stdout=f)
        f.seek(0)
        output = f.read()
        possibility_format = "Found 1 collision:\n(%s: %s), (%s: %s)\n"
        possibility_tuple1 = (real_name, real_email, upper_name, other_email)
        possibility_tuple2 = (upper_name, other_email, real_name, real_email)
        possibility1 = possibility_format % possibility_tuple1
        possibility2 = possibility_format % possibility_tuple2
        self.assertIn(output, [possibility1, possibility2])


class TestProfileProperties(TestCase):
    """Put tests for profile properties here."""

    def test_has_archived_patterns(self):
        alice = UserFactory()
        patterns = IndividualPattern.approved_patterns.filter(user=alice)
        self.assertEqual(patterns.count(), 0)

        # Property should return False for users without any approved patterns
        self.assertFalse(alice.profile.has_archived_patterns)

        # Property should return False for users with approved patterns, but
        # no archived patterns
        live_pattern = TestApprovedIndividualPatternFactory.for_user(user=alice)
        self.assertTrue(live_pattern.approved)
        self.assertFalse(live_pattern.archived)
        self.assertFalse(alice.profile.has_archived_patterns)

        # Property should return True for users with both archived and
        # non-archived patterns
        archived_pattern = TestApprovedIndividualPatternFactory.for_user(user=alice)
        archived_pattern.archived = True
        archived_pattern.save()
        self.assertTrue(alice.profile.has_archived_patterns)

        # Property should return True for users with only archived patterns
        live_pattern.delete()
        self.assertTrue(alice.profile.has_archived_patterns)

        alice.delete()

    def test_properties_regular_user(self):
        alice = UserFactory()
        self.assertFalse(alice.profile.is_friend_or_family)
        alice.delete()

    def test_properties_friend_and_family(self):
        friend = FriendAndFamilyFactory()
        self.assertTrue(friend.profile.is_friend_or_family)
        friend.delete()

    def test_properties_staff_user(self):
        staff = StaffFactory()
        self.assertFalse(staff.profile.is_friend_or_family)
        staff.delete()


class ManageAccountTestIndividual(TestCase):

    def setUp(self):
        super(ManageAccountTestIndividual, self).setUp()
        self.user = UserFactory()

        self.client = Client()

    def tearDown(self):
        self.client.logout()
        self.user.delete()
        super(ManageAccountTestIndividual, self).tearDown()

    def test_context(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("userauth:manage_account"))

        # Now let's test the context
        context = response.context
        self.assertEqual(context["userform_url"], reverse("userauth:manage_account"))
        self.assertIsInstance(context["form"], UserManagementForm)


class InactiveUserViewTest(TestCase):

    def test_inactive_user_view(self):
        url = reverse("userauth:account_inactive")
        resp = self.client.get(url)

        self.assertContains(resp, "<title>Account inactive</title>", html=True)
        self.assertContains(resp, "<h2>Your account is inactive</h2>", html=True)
        goal_html = """<p>
    Your account seems to be inactive, or has been deactivated.
  </p>"""
        self.assertContains(resp, goal_html, html=True)


class LoginViewTest(TestCase):

    def test_user_can_log_in(self):
        user = UserFactory(username="alice", password="alice")
        url = reverse("userauth:login")

        # sanity-test
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        post_data = {"username": "alice", "password": "alice"}
        resp = self.client.post(url, data=post_data, follow=False)
        self.assertEqual(resp.status_code, 302)


class LogoutViewTest(TestCase):

    def test_user_can_logout(self):
        user = UserFactory(username="alice", password="alice")
        self.client.force_login(user)
        url = reverse("userauth:logout")

        resp = self.client.post(url, follow=False)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "You're logged out")
