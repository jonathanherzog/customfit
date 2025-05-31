# -*- coding: utf-8 -*-
import copy
import logging

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from customfit.bodies.factories import BodyFactory
from customfit.bodies.models import Body
from customfit.bodies.views import BODY_SESSION_NAME
from customfit.pattern_spec.models import PatternSpec
from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.models import Swatch
from customfit.userauth.factories import UserFactory

from ...factories import SweaterPatternSpecFactory
from ...forms import CARDIGAN, PULLOVER, SLEEVED, VEST
from ...helpers import sweater_design_choices as SDC

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
            "body": self.body.id,
            "swatch": self.swatch.id,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "silhouette": SDC.SILHOUETTE_HOURGLASS,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "garment_type_body": PULLOVER,
            "garment_type_sleeves": SLEEVED,
            "button_band_edging_stitch": self.stitch.id,
            "button_band_edging_height": 2,
            "button_band_allowance": 2,
            "number_of_buttons": 5,
            "neckline_style": SDC.NECK_VEE,
            "torso_length": SDC.HIGH_HIP_LENGTH,
            "neckline_width": SDC.NECK_NARROW,
            "neckline_depth": 1,
            "neckline_depth_orientation": SDC.BELOW_SHOULDERS,
            "hip_edging_stitch": self.stitch.id,
            "hip_edging_height": 2,
            "armhole_edging_stitch": self.stitch.id,
            "armhole_edging_height": 0.5,
            "sleeve_length": SDC.SLEEVE_THREEQUARTER,
            "sleeve_shape": SDC.SLEEVE_BELL,
            "bell_type": SDC.BELL_SLIGHT,
            "sleeve_edging_stitch": self.stitch.id,
            "sleeve_edging_height": 2,
            "neck_edging_stitch": self.stitch.id,
            "neck_edging_height": 1,
        }

    def test_form(self):
        form = self._make_form(data=self.post_entries)
        assert form.is_valid(), form.errors

    def test_missing_entries_pullover_sleeved(self):
        # We were getting problems with the custom-design form failing during
        # validation because missing entries would trigger exceptions
        # *other* than Validation error. This tests for those errors
        # for one specific type of sweater
        for k in list(self.post_entries.keys()):
            new_post_entries = copy.copy(self.post_entries)
            new_post_entries["garment_type"] = PULLOVER
            new_post_entries["garment_type_sleeves"] = SLEEVED
            new_post_entries[k] = None
            form = self._make_form(data=new_post_entries)
            # should not raise an exception
            form.is_valid()

    def test_missing_entries_cardigan_sleeved(self):
        # We were getting problems with the custom-design form failing during
        # validation because missing entries would trigger exceptions
        # *other* than Validation error. This tests for those errors
        # for one specific type of sweater
        for k in list(self.post_entries.keys()):
            new_post_entries = copy.copy(self.post_entries)
            new_post_entries["garment_type"] = CARDIGAN
            new_post_entries["garment_type_sleeves"] = SLEEVED
            new_post_entries[k] = None
            form = self._make_form(data=new_post_entries)
            # should not raise an exception
            form.is_valid()

    def test_missing_entries_pullover_vest(self):
        # We were getting problems with the custom-design form failing during
        # validation because missing entries would trigger exceptions
        # *other* than Validation error. This tests for those errors
        # for one specific type of sweater
        for k in list(self.post_entries.keys()):
            new_post_entries = copy.copy(self.post_entries)
            new_post_entries["garment_type"] = PULLOVER
            new_post_entries["garment_type_sleeves"] = VEST
            new_post_entries[k] = None
            form = self._make_form(data=new_post_entries)
            # should not raise an exception
            form.is_valid()

    def test_missing_entries_cardigan_vest(self):
        # We were getting problems with the custom-design form failing during
        # validation because missing entries would trigger exceptions
        # *other* than Validation error. This tests for those errors
        # for one specific type of sweater
        for k in list(self.post_entries.keys()):
            new_post_entries = copy.copy(self.post_entries)
            new_post_entries["garment_type"] = CARDIGAN
            new_post_entries["garment_type_sleeves"] = VEST
            new_post_entries[k] = None
            form = self._make_form(data=new_post_entries)
            # should not raise an exception
            form.is_valid()

    def test_missing_entries_drop_shoulder(self):
        self.login()
        new_post_entries = copy.copy(self.post_entries)
        new_post_entries["construction"] = SDC.CONSTRUCTION_DROP_SHOULDER
        new_post_entries["drop_shoulder_additional_armhole_depth"] = ""
        response = self.client.post(self.url, new_post_entries, follow=False)
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "Drop-shoulder sweaters need a valid drop-shoulder armhole depth",
        )

    def test_drop_shoulder_is_ignored(self):
        from ...models import SweaterIndividualGarmentParameters

        self.login()
        new_post_entries = copy.copy(self.post_entries)
        new_post_entries["construction"] = SDC.CONSTRUCTION_SET_IN_SLEEVE
        new_post_entries["drop_shoulder_additional_armhole_depth"] = (
            SDC.DROP_SHOULDER_ADDITIONAL_ARMHOLE_DEPTH_AVERAGE
        )

        response = self.client.post(self.url, new_post_entries, follow=False)
        self.assertEqual(response.status_code, 302)
        igp_id_str = response["Location"].split("/")[-2]
        igp_id = int(igp_id_str)
        igp = SweaterIndividualGarmentParameters.objects.get(id=igp_id)
        pspec = igp.get_spec_source()

        self.assertEqual(pspec.construction, SDC.CONSTRUCTION_SET_IN_SLEEVE)
        self.assertIsNone(pspec.drop_shoulder_additional_armhole_depth)

    def test_no_bodies(self):
        self.login()
        response = self.client.get(self.url)
        self.assertNotContains(response, "before you can proceed")

        Body.objects.filter(user=self.user).all().delete()
        response = self.client.get(self.url)
        url = reverse("bodies:body_create_view")
        goal_html = (
            '<div id="hint_id_body" class="help-block">You need to <a href="{url}?next={this_url}">add at least '
            "one measurement set</a> before you can proceed.</div>".format(
                url=url, this_url=self.url
            )
        )
        self.assertContains(response, goal_html, html=True)

    def test_no_swatches(self):
        self.login()
        response = self.client.get(self.url)
        self.assertNotContains(response, "before you can proceed")

        Swatch.objects.filter(user=self.user).all().delete()
        response = self.client.get(self.url)
        goal_url = reverse("swatches:swatch_create_view")
        goal_html = (
            '<div id="hint_id_swatch" class="help-block">You need to <a href="%s?next=%s">add at least '
            "one gauge</a> before you can proceed.</div>" % (goal_url, self.url)
        )
        self.assertContains(response, goal_html, html=True)

    def test_create_body_url(self):
        self.login()
        response = self.client.get(self.url)
        goal_html = (
            '<a href="/measurement/new/?next=%s">(or create a new one)</a>' % self.url
        )
        self.assertContains(response, goal_html)

    def test_create_swatch_url(self):
        self.login()
        response = self.client.get(self.url)
        goal_html = (
            '<a href="/swatch/new/?next=%s">(or create a new one)</a>' % self.url
        )
        self.assertContains(response, goal_html)

    def test_initial_body_from_session(self):
        self.login()

        # sanity check
        response = self.client.get(self.url)
        form_initial = response.context["form"].initial
        self.assertNotIn("body", form_initial)

        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.url)
        form_initial = response.context["form"].initial
        self.assertEqual(form_initial["body"], self.body)
        goal_html = '<option value="%d" selected="selected">%s</option>' % (
            self.body.id,
            self.body.name,
        )
        self.assertContains(response, goal_html, html=True)

    def test_form_clears_body_from_session(self):
        self.login()

        # user uses body from session
        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.url)

        response2 = self.client.post(
            self.url,
            {
                "name": "name",
                "body": self.body.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            },
        )

        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

        # user uses body not in session
        body2 = BodyFactory(user=self.user)
        session = self.client.session
        session[BODY_SESSION_NAME] = self.body.id
        session.save()
        response = self.client.get(self.url)

        response2 = self.client.post(
            self.url,
            {
                "name": "name",
                "body": body2.id,
                "swatch": self.swatch.id,
                "torso_length": SDC.MED_HIP_LENGTH,
                "sleeve_length": SDC.SLEEVE_FULL,
                "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            },
        )

        session = self.client.session
        self.assertNotIn(BODY_SESSION_NAME, session)

    def test_drop_shoulder_armhole_values_shown(self):
        self.login()
        response = self.client.get(self.url)
        goal_html = """
            <select name="drop_shoulder_additional_armhole_depth" 
                    class="select form-control" 
                    id="id_drop_shoulder_additional_armhole_depth"
                    aria-describedby="id_drop_shoulder_additional_armhole_depth_helptext"> 
            <option value="" selected>---------</option> 
            <option value="shallowdepth">shallow (¾&quot;/2 cm)</option> 
            <option value="averagedepth">average (1½&quot;/4 cm)</option> 
            <option value="deepdepth">deep (2½&quot;/6.5 cm)</option>
            </select>
        """
        self.assertContains(response, goal_html, html=True)

    def test_bug_handling_incompatible_design_inputs(self):
        self.login()
        new_post_entries = copy.copy(self.post_entries)
        new_post_entries["hip_edging_height"] = 20
        response = self.client.post(self.url, new_post_entries, follow=False)
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(
            str(messages[0]).startswith(
                "Sorry, but the hip edging is extending past the waist."
            )
        )


class CreateCustomDesignViewTestIndividual(TestCase, CreateCustomDesignViewTestMixin):

    def setUp(self):
        super(CreateCustomDesignViewTestIndividual, self).setUp()
        self.user = UserFactory()
        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)
        self.stitch = StitchFactory(user_visible=True)
        self.stitch.save()
        self.post_entries = self._create_post_entries()
        self.url = reverse(
            "design_wizard:custom_design_create_view_garment",
            kwargs={"garment": "sweaters"},
        )

        self.user2 = UserFactory()

    def tearDown(self):
        self.user2.delete()
        self.stitch.delete()
        super(CreateCustomDesignViewTestIndividual, self).tearDown()

    def login(self):
        return self.client.force_login(self.user)

    def _make_form(self, data):
        from ...forms import PatternSpecForm

        form = PatternSpecForm(
            data=data,
            user=self.user,
            create_body_url=reverse("bodies:body_create_view"),
            create_swatch_url=reverse("swatches:swatch_create_view"),
        )
        return form

    def test_body_belongs_to_wrong_user(self):
        new_body = BodyFactory(user=self.user2)
        new_body.save()

        # new_body should not be provided as an option
        self.login()
        response = self.client.get(self.url)
        self.assertContains(response, self.body.name)  # sanity check
        self.assertNotContains(response, new_body.name)

        # new_body should not be allowed in a POST
        self.post_entries["body"] = new_body.id
        response = self.client.post(self.url, self.post_entries, follow=False)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "body",
            ["Select a valid choice. That choice is not one of the available choices."],
        )

    def test_swatch_belongs_to_wrong_user(self):
        new_swatch = SwatchFactory(user=self.user2, name="new swatch")
        new_swatch.save()

        # new_swatch should not be provided as an option
        self.login()
        response = self.client.get(self.url)
        self.assertContains(response, self.swatch.name)  # sanity check
        self.assertNotContains(response, new_swatch.name)

        # new_swatch should not be accepted in a POST
        self.post_entries["swatch"] = new_swatch.id
        response = self.client.post(self.url, self.post_entries, follow=False)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "swatch",
            ["Select a valid choice. That choice is not one of the available choices."],
        )

    def test_no_swatches(self):
        self.login()
        response = self.client.get(self.url)
        self.assertNotContains(response, "before you can proceed")

        self.swatch.delete()
        response = self.client.get(self.url)
        self.assertContains(
            response,
            '<div id="hint_id_swatch" class="help-block">You need to <a href="/swatch/new/?next=%s">add at least one gauge</a> before you can proceed.</div>'
            % self.url,
            html=True,
        )


class CustomPlusMissingViewTest(TestCase):

    def setUp(self):
        super(CustomPlusMissingViewTest, self).setUp()
        self.user = UserFactory()
        self.body = BodyFactory(user=self.user)
        self.swatch = SwatchFactory(user=self.user)
        self.user2 = UserFactory()

    def login(self):
        self.client.force_login(self.user)

    def test_custom_plus_patternspec_right_user(self):
        """
        If a user tries to access the personalize design page for a patternspec
        that IS theirs, the form is initialized with their data.
        """
        # The dicts will be too long to debug without this statement.
        self.maxDiff = None

        self.login()
        hip_stitch = StitchFactory(name="1x1 Ribbing")
        neck_stitch = StitchFactory(name="1x1 Ribbing")
        sleeve_stitch = StitchFactory(name="1x1 Ribbing")
        pspec = SweaterPatternSpecFactory(
            user=self.user,
            name="namename",
            body=self.body,
            swatch=self.swatch,
            design_origin=None,
            torso_length=SDC.HIGH_HIP_LENGTH,
            sleeve_length=SDC.SLEEVE_ELBOW,
            garment_fit=SDC.FIT_MENS_OVERSIZED,
            hip_edging_stitch=hip_stitch,
            sleeve_edging_stitch=sleeve_stitch,
            neck_edging_stitch=neck_stitch,
        )

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "sweaters"},
        )

        resp = self.client.get(custom_url)

        form_data = {}

        for field in resp.context["form"].initial:
            initial = resp.context["form"].initial[field]
            form_data[field] = initial

        # The following fields are not exposed by the custom design page.
        excluded_fields = [
            "back_allover_stitch",
            "back_waist_shaping_only",
            "button_band_allowance_percentage",
            "neckline_other_val_percentage",
            "creation_date",
            "design_origin",
            "front_allover_stitch",
            "garment_type",
            "id",
            "panel_stitch",
            "pattern_credits",
            "sleeve_allover_stitch",
            "back_cable_stitch",
            "back_cable_extra_stitches",
            "front_cable_stitch",
            "front_cable_extra_stitches",
            "sleeve_cable_stitch",
            "sleeve_cable_extra_stitches",
            "sleeve_cable_extra_stitches_caston_only",
        ]

        processed_data = {
            field: form_data[field]
            for field in form_data
            if field not in excluded_fields
        }

        expected_data = {
            "sleeve_length": SDC.SLEEVE_ELBOW,
            "torso_length": SDC.HIGH_HIP_LENGTH,
            "garment_fit": SDC.FIT_MENS_OVERSIZED,
            "body": self.body.id,
            "swatch": self.swatch.pk,
            "name": "namename",
            # defaults
            "garment_type_body": PULLOVER,
            "garment_type_sleeves": SLEEVED,
            "sleeve_shape": SDC.SLEEVE_TAPERED,
            "neckline_style": SDC.NECK_VEE,
            "neckline_width": SDC.NECK_AVERAGE,
            "neckline_depth": 6.0,
            "neckline_depth_orientation": SDC.BELOW_SHOULDERS,
            "hip_edging_stitch": hip_stitch.id,
            "hip_edging_height": 1.5,
            "sleeve_edging_stitch": sleeve_stitch.id,
            "sleeve_edging_height": 0.5,
            "neck_edging_stitch": neck_stitch.id,
            "neck_edging_height": 1.0,
            "number_of_buttons": None,
            "button_band_allowance": None,
            "button_band_edging_stitch": None,
            "button_band_edging_height": None,
            "bell_type": None,
            "armhole_edging_stitch": None,
            "armhole_edging_height": None,
            "silhouette": SDC.SILHOUETTE_HOURGLASS,
            "construction": SDC.CONSTRUCTION_SET_IN_SLEEVE,
            "drop_shoulder_additional_armhole_depth": None,
        }
        self.assertEqual(processed_data, expected_data)

    def test_change_patternspec_imperial(self):

        hip_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        neck_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        sleeve_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        pspec = SweaterPatternSpecFactory(
            user=self.user,
            swatch=self.swatch,
            neckline_depth=6,
            body=self.body,
            hip_edging_stitch=hip_stitch,
            sleeve_edging_stitch=sleeve_stitch,
            neck_edging_stitch=neck_stitch,
        )
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "sweaters"},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(custom_url)
        self.assertEqual(resp.context["form"].initial["neckline_depth"], 6)

        new_values = resp.context["form"].initial
        new_values["neckline_depth"] = 7
        new_values["neck_edging_stitch"] = neck_stitch.id
        new_values["sleeve_edging_stitch"] = sleeve_stitch.id
        new_values["hip_edging_stitch"] = hip_stitch.id
        del new_values["armhole_edging_height"]
        del new_values["armhole_edging_stitch"]
        del new_values["bell_type"]
        del new_values["button_band_allowance"]
        del new_values["button_band_edging_height"]
        del new_values["button_band_edging_stitch"]
        del new_values["number_of_buttons"]
        del new_values["drop_shoulder_additional_armhole_depth"]
        new_values["redirect_approve"] = "Get this pattern!"

        self.client.post(custom_url, data=new_values, follow=False)

        pspec.refresh_from_db()
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)
        self.assertEqual(pspec.neckline_depth, 7)

    def test_change_patternspec_metric(self):
        self.user.profile.display_imperial = False
        self.user.profile.save()

        hip_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        neck_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        sleeve_stitch = StitchFactory(name="1x1 Ribbing", user_visible=True)
        pspec = SweaterPatternSpecFactory(
            user=self.user,
            swatch=self.swatch,
            neckline_depth=6,
            body=self.body,
            hip_edging_stitch=hip_stitch,
            sleeve_edging_stitch=sleeve_stitch,
            neck_edging_stitch=neck_stitch,
        )
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)

        custom_url = reverse(
            "design_wizard:custom_design_plus_missing_garment",
            kwargs={"pk": pspec.pk, "garment": "sweaters"},
        )

        self.login()  # logs in user 1

        # See above comment about PermissionDenied and leopards
        resp = self.client.get(custom_url)
        self.assertEqual(resp.context["form"].initial["neckline_depth"], 15.24)

        new_values = resp.context["form"].initial
        new_values["neckline_depth"] = 18
        new_values["neck_edging_stitch"] = neck_stitch.id
        new_values["sleeve_edging_stitch"] = sleeve_stitch.id
        new_values["hip_edging_stitch"] = hip_stitch.id
        del new_values["armhole_edging_height"]
        del new_values["armhole_edging_stitch"]
        del new_values["bell_type"]
        del new_values["button_band_allowance"]
        del new_values["button_band_edging_height"]
        del new_values["button_band_edging_stitch"]
        del new_values["number_of_buttons"]
        del new_values["drop_shoulder_additional_armhole_depth"]

        new_values["redirect_approve"] = "Get this pattern!"

        self.client.post(custom_url, data=new_values, follow=False)

        pspec.refresh_from_db()
        self.assertEqual(PatternSpec.objects.filter(user=self.user).count(), 1)
        self.assertAlmostEqual(pspec.neckline_depth, 7.086, 2)
