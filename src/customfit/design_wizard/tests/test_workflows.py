from django.test import TestCase
from django.urls import reverse

from customfit.patterns.models import IndividualPattern
from customfit.test_garment.factories import (
    TestDesignFactory,
    TestIndividualGarmentParametersFactory,
    TestRedoFactory,
)
from customfit.userauth.factories import UserFactory

from .helpers import SessionTestingMixin


class TestCrossDesignSessionHandling(TestCase):

    def test_can_switch_designs(self):
        # Test that the user can switch between designs without error
        design1 = TestDesignFactory()
        url1 = reverse("design_wizard:personalize", args=(design1.slug,))
        design2 = TestDesignFactory()
        url2 = reverse("design_wizard:personalize", args=(design2.slug,))
        user = UserFactory()

        self.client.force_login(user)

        resp = self.client.get(url1, follow=False)
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get(url2, follow=False)
        self.assertEqual(resp.status_code, 200)

    def test_can_make_pattern_then_start_on_next(self):
        # Test that the user can make one pattern then start on a second without
        # anything getting in the way.

        user = UserFactory()
        design = TestDesignFactory()
        self.client.force_login(user)

        igp = TestIndividualGarmentParametersFactory(user=user)
        url = reverse("design_wizard:summary", args=(igp.id,))
        _ = self.client.post(url)

        # Can we start personalizing the design?
        url1 = reverse("design_wizard:personalize", args=(design.slug,))
        resp = self.client.get(url1)
        self.assertEqual(resp.status_code, 200)


class TestTweakAndApproveScreenInteractions(TestCase):

    def _tweak_url(self, igp):
        return reverse("design_wizard:tweak", args=(igp.id,))

    def _approve_url(self, igp):
        return reverse("design_wizard:summary", args=(igp.id,))

    # We had a bug where if the user ever looked at the approve screen for an IGP, then
    # no amount of later tweaking on that IGP would change the resulting pattern.
    # Let's test that we fixed that.

    def test_can_tweak_after_approve_screen_patternspec(self):

        # sanity checks
        # ------------------

        # Make an IGP
        igp = TestIndividualGarmentParametersFactory()
        user = igp.get_spec_source().user
        self.client.force_login(user)

        # Look at the approve view, confirm some measurement
        approve_url1 = self._approve_url(igp)
        resp = self.client.get(approve_url1)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 2&quot;/5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # Approve the pattern, confirm that measurement
        resp = self.client.post(approve_url1, follow=True)
        pattern = IndividualPattern.objects.get(
            pieces__schematic__individual_garment_parameters=igp
        )
        goal_url = reverse("patterns:individualpattern_detail_view", args=(pattern.pk,))
        self.assertRedirects(resp, goal_url)
        self.assertEqual(pattern.pieces.test_piece.test_field, 2)

        self.client.logout()

        # Actual test
        # ------------
        # Make identical IGP
        igp2 = TestIndividualGarmentParametersFactory()
        user = igp2.get_spec_source().user
        self.client.force_login(user)

        # Look at the approve view, confirm some measurement
        approve_url2 = self._approve_url(igp2)
        resp = self.client.get(approve_url2)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 2&quot;/5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # go to the tweak screen, tweak that measurement
        tweak_url = self._tweak_url(igp2)
        resp = self.client.get(tweak_url)
        self.assertEqual(resp.status_code, 200)  # sanity check
        post_data = {"test_field": 3}
        resp = self.client.post(tweak_url, data=post_data, follow=True)
        self.assertRedirects(resp, approve_url2)

        # Check that the measurement has changed on the approve page
        resp = self.client.get(approve_url2)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 3&quot;/7.5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # Approve the pattern, confirm that measurement
        resp = self.client.post(approve_url2, follow=True)
        pattern = IndividualPattern.objects.get(
            pieces__schematic__individual_garment_parameters=igp2
        )
        goal_url = reverse("patterns:individualpattern_detail_view", args=(pattern.pk,))
        self.assertRedirects(resp, goal_url)
        self.assertEqual(pattern.pieces.test_piece.test_field, 3)

    def test_can_tweak_after_approve_screen_redo(self):

        # sanity checks
        # ------------------

        # Make an IGP
        redo = TestRedoFactory()
        user = redo.pattern.user
        igp = TestIndividualGarmentParametersFactory(
            pattern_spec=None, redo=redo, user=user
        )
        self.client.force_login(user)

        # Look at the approve view, confirm some measurement
        approve_url1 = self._approve_url(igp)
        resp = self.client.get(approve_url1)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 2&quot;/5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # Approve the pattern, confirm that measurement
        resp = self.client.post(approve_url1, follow=True)
        pattern = IndividualPattern.objects.get(
            pieces__schematic__individual_garment_parameters=igp
        )
        goal_url = reverse("patterns:individualpattern_detail_view", args=(pattern.pk,))
        self.assertRedirects(resp, goal_url)
        self.assertEqual(pattern.pieces.test_piece.test_field, 2)

        self.client.logout()

        # Actual test
        # ------------
        # Make identical IGP
        redo = TestRedoFactory()
        user = redo.pattern.user
        igp2 = TestIndividualGarmentParametersFactory(
            pattern_spec=None, redo=redo, user=user
        )
        self.client.force_login(user)

        # capture IDs for later testing
        orig_pattern = redo.pattern
        orig_pieces = redo.pattern.pieces
        orig_piece = redo.pattern.pieces.test_piece
        orig_schematic = redo.pattern.pieces.schematic
        orig_piece_schematic = redo.pattern.pieces.schematic.test_piece
        orig_igp = redo.pattern.pieces.schematic.individual_garment_parameters

        # Look at the approve view, confirm some measurement
        approve_url2 = self._approve_url(igp2)
        resp = self.client.get(approve_url2)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 2&quot;/5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # go to the tweak screen, tweak that measurement
        tweak_url = self._tweak_url(igp2)
        resp = self.client.get(tweak_url)
        self.assertEqual(resp.status_code, 200)  # sanity check
        post_data = {"test_field": 3}
        resp = self.client.post(tweak_url, data=post_data, follow=True)
        self.assertRedirects(resp, approve_url2)

        # Check that the measurement has changed on the approve page
        resp = self.client.get(approve_url2)
        self.assertEqual(resp.status_code, 200)  # sanity check
        goal_html = """
        <div class="row">
        <div class="col-xs-6 col-sm-6 col-lg-5">test length</div>
        <div class="col-xs-6 col-sm-6 col-lg-5"> 3&quot;/7.5 cm</div>
        </div>"""
        self.assertContains(resp, goal_html, html=True)

        # Approve the pattern, confirm that measurement
        resp = self.client.post(approve_url2, follow=True)
        pattern = IndividualPattern.objects.get(
            pieces__schematic__individual_garment_parameters=igp2
        )
        goal_url = reverse("patterns:individualpattern_detail_view", args=(pattern.pk,))
        self.assertRedirects(resp, goal_url)
        self.assertEqual(pattern.pieces.test_piece.test_field, 3)

        # confirm all old model-instances still there
        orig_pattern.refresh_from_db()
        orig_pieces.refresh_from_db()
        orig_piece.refresh_from_db()
        orig_schematic.refresh_from_db()
        orig_piece_schematic.refresh_from_db()
        orig_igp.refresh_from_db()
