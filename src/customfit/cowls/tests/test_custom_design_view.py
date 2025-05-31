import logging

from django.test import TestCase
from django.urls import reverse

from customfit.stitches.tests import StitchFactory
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.models import Swatch
from customfit.userauth.factories import UserFactory

from .. import helpers as CDC
from ..models import CowlPatternSpec

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
            "swatch": self.swatch.id,
            "circumference": CDC.COWL_CIRC_MEDIUM,
            "height": CDC.COWL_HEIGHT_AVERAGE,
            "main_stitch": self.stitch.id,
            "edging_stitch": self.stitch.id,
            "edging_stitch_height": 2,
            "cast_on_x_mod": 0,
            "cast_on_mod_y": 1,
        }

    def test_form(self):
        form = self._make_form(data=self.post_entries)
        assert form.is_valid(), form.errors

    def test_no_swatches(self):
        self.login()
        response = self.client.get(self.url)
        self.assertContains(response, self.swatch.name)

        Swatch.objects.filter(user=self.user).all().delete()
        response = self.client.get(self.url)
        goal_url = reverse("swatches:swatch_create_view")
        goal_html = (
            '<div id="hint_id_swatch" class="help-block">You need to <a href="%s?next=%s">add at least '
            "one gauge</a> before you can proceed.</div>" % (goal_url, self.url)
        )
        self.assertContains(response, goal_html, html=True)

    def test_post_ok(self):
        self.login()

        # sanity check
        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())

        response = self.client.post(self.url, self.post_entries, follow=False)

        self.assertEqual(CowlPatternSpec.objects.filter(user=self.user).count(), 1)
        pspec = CowlPatternSpec.objects.filter(user=self.user).get()
        self.assertEqual(pspec.name, self.post_entries["name"])
        self.assertEqual(pspec.circumference, self.post_entries["circumference"])
        self.assertEqual(pspec.height, self.post_entries["height"])
        self.assertEqual(
            pspec.edging_stitch_height, self.post_entries["edging_stitch_height"]
        )
        self.assertEqual(pspec.cast_on_x_mod, self.post_entries["cast_on_x_mod"])
        self.assertEqual(pspec.cast_on_mod_y, self.post_entries["cast_on_mod_y"])

        self.assertEqual(pspec.swatch, self.swatch)
        self.assertEqual(pspec.main_stitch, self.stitch)
        self.assertEqual(pspec.edging_stitch, self.stitch)

    def test_post_too_much_edging1(self):
        # sanity check
        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())

        self.login()
        self.post_entries["edging_stitch_height"] = 9
        response = self.client.post(self.url, self.post_entries, follow=False)
        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "Edging-height cannot be more than one-third the total/minimum height",
        )

    def test_post_too_much_edging2(self):
        # sanity check
        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())

        self.login()
        self.post_entries["height"] = CDC.COWL_HEIGHT_EXTRA_TALL
        self.post_entries["edging_stitch_height"] = 5
        response = self.client.post(self.url, self.post_entries, follow=False)

        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())
        form = response.context["form"]
        self.assertFormError(
            form,
            "edging_stitch_height",
            "Ensure this value is less than or equal to 4&quot;/10.5cm",
        )

    def test_too_little_edging(self):
        self.login()
        self.post_entries["edging_stitch_height"] = 0.01
        response = self.client.post(self.url, self.post_entries, follow=False)

        self.assertFalse(CowlPatternSpec.objects.filter(user=self.user).exists())
        form = response.context["form"]
        self.assertFormError(
            form,
            "edging_stitch_height",
            "Ensure this value is greater than or equal to \xc2&quot;/0.5cm",
        )

    def test_add_inches_to_drop_downs(self):
        self.login()
        response = self.client.get(self.url)

        goal_height_html = """
            <div id="div_id_height" class="form-group"> 
                <label for="id_height" class="control-label col-sm-4 col-xs-12 requiredField">Height<span class="asteriskField">*</span> </label> 
                <div class="controls col-sm-8 col-xs-12"> 
                <select name="height" required class="select form-control" id="id_height"> 
                    <option value="" selected>---------</option> 
                    <option value="cowl_height_short">short height (10&quot;/25.5 cm)</option> 
                    <option value="cowl_height_avg">average height (12&quot;/30.5 cm)</option> 
                    <option value="cowl_height_tall">tall height (16&quot;/40.5 cm)</option> 
                    <option value="cowl_height_xtall">extra tall height (20&quot;/51 cm)</option>
                </select> 
                </div> 
            </div>        
        """
        self.assertContains(response, goal_height_html, html=True)

        goal_circ_html = """
            <div id="div_id_circumference" class="form-group"> 
                <label for="id_circumference" class="control-label col-sm-4 col-xs-12 requiredField">Circumference<span class="asteriskField">*</span> </label> 
                <div class="controls col-sm-8 col-xs-12"> 
                    <select name="circumference" required class="select form-control" id="id_circumference"> 
                        <option value="" selected>---------</option> 
                        <option value="cowl_circ_xsmall">extra-small circumference (20&quot;/51 cm)</option> 
                        <option value="cowl_circ_small">small circumference (26&quot;/66 cm)</option> 
                        <option value="cowl_circ_medium">medium circumference (42&quot;/106.5 cm)</option> 
                        <option value="cowl_circ_large">large circumference (60&quot;/152.5 cm)</option>
                    </select> 
                </div> 
            </div>           
            """
        self.assertContains(response, goal_circ_html, html=True)


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
            kwargs={"garment": "cowls"},
        )

        self.user2 = UserFactory()

    def login(self):
        return self.client.force_login(self.user)

    def _make_form(self, data):
        from ..forms import CustomCowlDesignForm

        form = CustomCowlDesignForm(
            data=data,
            user=self.user,
            create_swatch_url=reverse("swatches:swatch_create_view"),
        )
        return form

    def test_get(self):
        self.login()
        response = self.client.get(self.url)
        self.assertContains(response, "<h2>Build your own pattern</h2>")
        self.assertContains(response, "Edging stitch")

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
