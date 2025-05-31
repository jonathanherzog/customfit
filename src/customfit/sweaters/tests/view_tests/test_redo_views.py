import logging
from urllib.parse import urljoin

from django.test import LiveServerTestCase, TestCase, tag
from django.urls import reverse
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from seleniumlogin import force_login

from customfit.bodies.factories import (
    ChildBodyFactory,
    FemaleBodyFactory,
    MaleBodyFactory,
    SimpleBodyFactory,
    UnstatedTypeBodyFactory,
)
from customfit.bodies.models import Body
from customfit.design_wizard.constants import REDO_AND_APPROVE, REDO_AND_TWEAK
from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.garment_parameters.models import IndividualGarmentParameters
from customfit.helpers.math_helpers import cm_to_inches
from customfit.patterns.models import Redo
from customfit.swatches.models import Swatch
from customfit.sweaters.factories import (
    ApprovedSweaterPatternFactory,
    SweaterPatternSpecFactory,
    SweaterRedoFactory,
)
from customfit.sweaters.helpers import sweater_design_choices as SDC
from customfit.userauth.factories import UserFactory

# Get an instance of a logger
logger = logging.getLogger(__name__)


class SweaterRedoCreateViewTests(TestCase):

    def setUp(self):
        super(SweaterRedoCreateViewTests, self).setUp()

        self.pattern = ApprovedSweaterPatternFactory()
        self.alice = self.pattern.user

    def url_of_pattern(self, pattern):

        return reverse("design_wizard:redo_start", kwargs={"pk": pattern.pk})

    # Visibility tests

    def test_can_see_redo_page(self):
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

    def test_no_swatches(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        # sanity check
        response = self.client.get(redo_url)
        self.assertNotContains(response, "before you can proceed")

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

    # Post tests
    def test_post_to_tweak(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] += 0.1

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        igp = IndividualGarmentParameters.objects.get(redo=redo)
        goal_url = reverse("design_wizard:redo_tweak", kwargs={"pk": igp.pk})
        self.assertRedirects(response, goal_url)

    # Post tests
    def test_post_to_approve(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        pspec = self.pattern.get_spec_source()
        new_values = initial_values
        new_values["neckline_depth"] += 0.1

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        igp = IndividualGarmentParameters.objects.get(redo=redo)
        goal_url = reverse("design_wizard:redo_approve", kwargs={"igp_id": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_imperial_user(self):
        self.alice.profile.display_imperial = True

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertContains(
            response, '<span class="input-group-addon">inches</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 3
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)

        # Redo should have neckline depth of 3 inches below shoulders
        self.assertEqual(redo.neckline_depth, 3)
        self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    def test_metric_user(self):
        self.alice.profile.display_imperial = False
        self.alice.profile.save()

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        self.assertContains(
            response, '<span class="input-group-addon">cm</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 10  # cm
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)

        # Redo should have neckline depth of 4 inches below shoulders
        self.assertAlmostEqual(redo.neckline_depth, cm_to_inches(10), 2)
        self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    # Content tests

    def test_initial_values(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        pspec = self.pattern.get_spec_source()

        self.assertEqual(initial_values["body"], pspec.body.pk)
        self.assertEqual(initial_values["swatch"], pspec.swatch.pk)
        self.assertEqual(initial_values["garment_fit"], pspec.garment_fit)
        self.assertEqual(initial_values["torso_length"], pspec.torso_length)
        self.assertEqual(initial_values["sleeve_length"], pspec.sleeve_length)
        self.assertEqual(initial_values["neckline_depth"], pspec.neckline_depth)
        self.assertEqual(
            initial_values["neckline_depth_orientation"],
            pspec.neckline_depth_orientation,
        )

    def test_no_bodies(self):
        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        # sanity check
        response = self.client.get(redo_url)
        self.assertNotContains(response, "before you can proceed")

        for body in Body.objects.filter(user=self.alice):
            body.archived = True
            body.save()
        response = self.client.get(redo_url)
        self.assertContains(
            response,
            '<div id="hint_id_body" class="help-block">You need to <a href="/measurement/new/?next=%s">add at least one measurement set</a> before you can proceed.</div>'
            % redo_url,
            html=True,
        )

    def test_sleeves_present_for_sleeved_garments(self):
        # sanity check:
        self.assertTrue(self.pattern.has_sleeves())

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        goal_html = """<label for="id_sleeve_length" class="control-label  requiredField">
                Sleeve length<span class="asteriskField">*</span> </label>"""
        self.assertContains(response, goal_html, html=True)

    def test_sleeves_absent_for_vest_garments(self):

        vest_pattern = ApprovedSweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_VEST, user=self.alice)
        )
        # sanity check:
        self.assertFalse(vest_pattern.has_sleeves())

        self.client.force_login(vest_pattern.user)
        redo_url = self.url_of_pattern(vest_pattern)
        response = self.client.get(redo_url)
        self.assertNotContains(response, "sleeve length")
        self.assertNotContains(response, "Sleeve length")

    def test_fit_script_shown(self):
        self.client.force_login(self.alice)
        for silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:
            hourglass_pattern = ApprovedSweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette,
                    garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
                    user=self.alice,
                )
            )
            redo_url = self.url_of_pattern(hourglass_pattern)
            response = self.client.get(redo_url)
            self.assertNotContains(response, "<!-- begin fit-compatibilty script -->")
            self.assertNotContains(response, "<!-- end fit-compatibilty script -->")

        for silhouette in [
            SDC.SILHOUETTE_STRAIGHT,
            SDC.SILHOUETTE_TAPERED,
            SDC.SILHOUETTE_ALINE,
        ]:
            non_hourglass_pattern = ApprovedSweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette,
                    garment_fit=SDC.FIT_WOMENS_AVERAGE,
                    user=self.alice,
                )
            )
            redo_url = self.url_of_pattern(non_hourglass_pattern)
            response = self.client.get(redo_url)
            self.assertContains(response, "<!-- begin fit-compatibilty script -->")
            self.assertContains(response, "<!-- end fit-compatibilty script -->")

    def test_correct_fits_shown(self):
        self.client.force_login(self.alice)
        for silhouette in [SDC.SILHOUETTE_HOURGLASS, SDC.SILHOUETTE_HALF_HOURGLASS]:
            hourglass_pattern = ApprovedSweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette,
                    garment_fit=SDC.FIT_HOURGLASS_AVERAGE,
                    user=self.alice,
                )
            )
            redo_url = self.url_of_pattern(hourglass_pattern)
            response = self.client.get(redo_url)
            self.assertNotContains(
                response,
                '<option value="FIT_WOMENS_TIGHT">Women&#39;s close fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_WOMENS_AVERAGE">Women&#39;s average fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_WOMENS_RELAXED">Women&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_WOMENS_OVERSIZED">Women&#39;s oversized fit</option>',
                html=True,
            )

            self.assertNotContains(
                response,
                '<option value="FIT_MENS_TIGHT">Men&#39;s close fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_MENS_AVERAGE">Men&#39;s average fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_MENS_RELAXED">Men&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_MENS_OVERSIZED">Men&#39;s oversized fit</option>',
                html=True,
            )

            self.assertNotContains(
                response,
                '<option value="FIT_CHILDS_TIGHT">Children&#39;s close fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_CHILDS_AVERAGE">Children&#39;s average fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_CHILDS_RELAXED">Children&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value="FIT_CHILDS_OVERSIZED">Children&#39;s oversized fit</option>',
                html=True,
            )

            self.assertContains(
                response,
                '<option value = "FIT_HOURGLASS_TIGHT" > Hourglass close fit </option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value = "FIT_HOURGLASS_AVERAGE" selected> Hourglass average fit </option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value = "FIT_HOURGLASS_RELAXED" > Hourglass relaxed fit </option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value = "FIT_HOURGLASS_OVERSIZED" > Hourglass oversized fit </option>',
                html=True,
            )

        for silhouette in [
            SDC.SILHOUETTE_STRAIGHT,
            SDC.SILHOUETTE_TAPERED,
            SDC.SILHOUETTE_ALINE,
        ]:
            non_hourglass_pattern = ApprovedSweaterPatternFactory.from_pspec(
                SweaterPatternSpecFactory(
                    silhouette=silhouette,
                    garment_fit=SDC.FIT_WOMENS_AVERAGE,
                    user=self.alice,
                )
            )
            redo_url = self.url_of_pattern(non_hourglass_pattern)
            response = self.client.get(redo_url)
            self.assertContains(
                response,
                '<option value="FIT_WOMENS_TIGHT">Women&#39;s close fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_WOMENS_AVERAGE" selected>Women&#39;s average fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_WOMENS_RELAXED">Women&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_WOMENS_OVERSIZED">Women&#39;s oversized fit</option>',
                html=True,
            )

            self.assertContains(
                response,
                '<option value="FIT_MENS_TIGHT">Men&#39;s close fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_MENS_AVERAGE">Men&#39;s average fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_MENS_RELAXED">Men&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_MENS_OVERSIZED">Men&#39;s oversized fit</option>',
                html=True,
            )

            self.assertContains(
                response,
                '<option value="FIT_CHILDS_TIGHT">Children&#39;s close fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_CHILDS_AVERAGE">Children&#39;s average fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_CHILDS_RELAXED">Children&#39;s relaxed fit</option>',
                html=True,
            )
            self.assertContains(
                response,
                '<option value="FIT_CHILDS_OVERSIZED">Children&#39;s oversized fit</option>',
                html=True,
            )

            self.assertNotContains(
                response,
                '<option value = "FIT_HOURGLASS_TIGHT" > Hourglass close fit </option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value = "FIT_HOURGLASS_AVERAGE"> Hourglass average fit </option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value = "FIT_HOURGLASS_RELAXED" > Hourglass relaxed fit </option>',
                html=True,
            )
            self.assertNotContains(
                response,
                '<option value = "FIT_HOURGLASS_OVERSIZED" > Hourglass oversized fit </option>',
                html=True,
            )

    def test_missing_measurements_summary(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "summary"}
        )
        self.assertRedirects(response, goal_url)

    def test_missing_measurements_tweak(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        redo_url = self.url_of_pattern(self.pattern)
        response = self.client.get(redo_url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(redo_url, data=new_values)
        redo = Redo.objects.get(pattern=self.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "tweak"}
        )
        self.assertRedirects(response, goal_url)


@tag("selenium")
class RedoCreateViewFrontendTest(LiveServerTestCase):

    def setUp(self):
        super(RedoCreateViewFrontendTest, self).setUp()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)

    def tearDown(self):
        self.driver.quit()
        super(RedoCreateViewFrontendTest, self).tearDown()

    def url_of_pattern(self, pattern):
        return reverse("design_wizard:redo_start", kwargs={"pk": pattern.pk})

    def test_fits_match_body(self):
        user = UserFactory()
        male_body = MaleBodyFactory(user=user)
        female_body = FemaleBodyFactory(user=user)
        child_body = ChildBodyFactory(user=user)
        unstated_body = UnstatedTypeBodyFactory(user=user)

        pattern = ApprovedSweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(
                user=user,
                silhouette=SDC.SILHOUETTE_STRAIGHT,
                garment_fit=SDC.FIT_WOMENS_AVERAGE,
            )
        )
        redo_url = urljoin(self.live_server_url, self.url_of_pattern(pattern))
        force_login(user, self.driver, self.live_server_url)
        self.driver.get(redo_url)

        # Get the drop-downs and options we need
        fit_dropdown_element = self.driver.find_element(By.ID, "id_garment_fit")
        fit_dropdown = Select(fit_dropdown_element)
        for option in fit_dropdown.options:
            option_value = option.get_attribute("value")
            if option_value == SDC.FIT_WOMENS_AVERAGE:
                womens_fit = option
            elif option_value == SDC.FIT_MENS_AVERAGE:
                mens_fit = option
            elif option_value == SDC.FIT_CHILDS_AVERAGE:
                childs_fit = option

        body_dropdown_element = self.driver.find_element(By.ID, "id_body")
        body_dropdown = Select(body_dropdown_element)

        # Select female body, check fits
        body_dropdown.select_by_value(str(female_body.id))
        self.assertTrue(womens_fit.is_enabled())
        self.assertFalse(mens_fit.is_enabled())
        self.assertFalse(childs_fit.is_enabled())

        # Select male body, check fits
        body_dropdown.select_by_value(str(male_body.id))
        self.assertFalse(womens_fit.is_enabled())
        self.assertTrue(mens_fit.is_enabled())
        self.assertFalse(childs_fit.is_enabled())

        # Select female body, check fits
        body_dropdown.select_by_value(str(child_body.id))
        self.assertFalse(womens_fit.is_enabled())
        self.assertFalse(mens_fit.is_enabled())
        self.assertTrue(childs_fit.is_enabled())

        # Select female body, check fits
        body_dropdown.select_by_value(str(unstated_body.id))
        self.assertTrue(womens_fit.is_enabled())
        self.assertTrue(mens_fit.is_enabled())
        self.assertTrue(childs_fit.is_enabled())


class SweaterRedoUpdateTests(TestCase):

    def setUp(self):

        self.redo = SweaterRedoFactory()
        self.alice = self.redo.user
        self.url = reverse("design_wizard:redo_plus_missing", args=(self.redo.id,))
        self.client.force_login(self.alice)
        self.user2 = UserFactory()

    # Test accessibility

    def test_can_see_redo_page(self):
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

    # Post tests

    def test_post_to_tweak(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] += 0.1

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
        self.assertRedirects(response, goal_url)

        # Post tests

    def test_post_to_approve(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] += 0.1

        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(self.url, data=new_values)
        self.redo.refresh_from_db()
        igp = IndividualGarmentParameters.objects.get(redo=self.redo)
        goal_url = reverse("design_wizard:redo_approve", kwargs={"igp_id": igp.pk})
        self.assertRedirects(response, goal_url, fetch_redirect_response=False)

    def test_imperial_user(self):
        self.alice.profile.display_imperial = True

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertContains(
            response, '<span class="input-group-addon">inches</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 3
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(self.url, data=new_values)
        self.redo.refresh_from_db()
        # Redo should have neckline depth of 3 inches below shoulders
        self.assertEqual(self.redo.neckline_depth, 3)
        self.assertEqual(self.redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    def test_metric_user(self):
        self.alice.profile.display_imperial = False
        self.alice.profile.save()

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        self.assertContains(
            response, '<span class="input-group-addon">cm</span>', html=True
        )

        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["neckline_depth"] = 10  # cm
        new_values["neckline_depth_orientation"] = SDC.BELOW_SHOULDERS
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        # Redo should have neckline depth of 4 inches below shoulders
        self.assertAlmostEqual(redo.neckline_depth, cm_to_inches(10), 2)
        self.assertEqual(redo.neckline_depth_orientation, SDC.BELOW_SHOULDERS)

    def test_body_wrong_owner(self):
        self.redo.body.user = self.user2
        self.redo.body.save()
        self.client.force_login(self.alice)
        with self.assertRaises(OwnershipInconsistency):
            response = self.client.get(self.url)

    # Content tests

    def test_initial_values(self):
        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial

        self.assertEqual(initial_values["body"], self.redo.body.pk)
        self.assertEqual(initial_values["swatch"], self.redo.swatch.pk)
        self.assertEqual(initial_values["garment_fit"], self.redo.garment_fit)
        self.assertEqual(initial_values["torso_length"], self.redo.torso_length)
        self.assertEqual(initial_values["sleeve_length"], self.redo.sleeve_length)
        self.assertEqual(initial_values["neckline_depth"], self.redo.neckline_depth)
        self.assertEqual(
            initial_values["neckline_depth_orientation"],
            self.redo.neckline_depth_orientation,
        )

    def test_sleeves_present_for_sleeved_garments(self):
        # sanity check:
        self.assertTrue(self.redo.pattern.has_sleeves())

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        goal_html = """<label for="id_sleeve_length" class="control-label  requiredField">
                 Sleeve length<span class="asteriskField">*</span> </label>"""
        self.assertContains(response, goal_html, html=True)

    def test_sleeves_absent_for_vest_garments(self):
        vest_pattern = ApprovedSweaterPatternFactory.from_pspec(
            SweaterPatternSpecFactory(garment_type=SDC.PULLOVER_VEST, user=self.alice)
        )
        # sanity check:
        self.assertFalse(vest_pattern.has_sleeves())

        redo = SweaterRedoFactory(
            pattern=vest_pattern, body=vest_pattern.body, swatch=vest_pattern.swatch
        )
        self.client.force_login(vest_pattern.user)
        redo_url = reverse("design_wizard:redo_plus_missing", args=(redo.id,))
        response = self.client.get(redo_url)
        self.assertNotContains(response, "sleeve length")
        self.assertNotContains(response, "Sleeve length")

    def test_missing_measurements_summary(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.redo.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_APPROVE] = "redo!"

        response = self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "summary"}
        )
        self.assertRedirects(response, goal_url)

    def test_missing_measurements_tweak(self):
        # Sanity-check: the pattern is hourglass, right?
        org_patternspec = self.redo.pattern.get_spec_source()
        self.assertTrue(org_patternspec.is_hourglass)

        simple_body = SimpleBodyFactory(user=self.alice)

        self.client.force_login(self.alice)
        response = self.client.get(self.url)
        initial_values = response.context["form"].initial
        new_values = initial_values
        new_values["body"] = simple_body.pk
        # Since there are multiple submit buttons, we must specify the one
        # we want in the POST data.
        new_values[REDO_AND_TWEAK] = "customize fit specifics"

        response = self.client.post(self.url, data=new_values)
        redo = Redo.objects.get(pattern=self.redo.pattern)
        goal_url = reverse(
            "design_wizard:missing_redo", kwargs={"pk": redo.pk, "action": "tweak"}
        )
        self.assertRedirects(response, goal_url)

    def test_redo_changes_patterntext(self):

        # Now that we're caching patterntext, we need to make sure redo clears the cache
        p = ApprovedSweaterPatternFactory()
        user = p.user
        self.client.force_login(user)

        patterntext_url = reverse(
            "patterns:individualpattern_detail_view", args=(p.pk,)
        )
        orig_response = self.client.get(patterntext_url)
        self.assertEqual(orig_response.status_code, 200)  # sanity check

        orig_htmls = [
            "<li>Hourglass average fit</li>",
            """
            <p>CO 98 stitches using long tail cast-on or other cast-on method of your choice. 
            Work even in 1x1 Ribbing for 1\xbd&quot;/4 cm (10 rows from beginning),
            ending with a WS row.</p>
            """,
            """
            <p>CO 45 stitches using long tail or other cast-on method of your choice. 
            Work even in 1x1 Ribbing for \xbd&quot;/1.5 cm (4 rows), ending with a WS row.</p>
            """,
            """
            <div class="row">
            <div class="col-xs-6 col-sm-6 col-lg-5">back hip width</div>
            <div class="col-xs-6 col-sm-6 col-lg-5">19\xbd&quot;/50 cm</div>
            </div>""",
        ]
        for orig_html in orig_htmls:
            # Sanity check orign patterntext
            self.assertContains(orig_response, orig_html, html=True)

        # Now, redo the pattern
        # use same swatch
        swatch = p.get_spec_source().swatch
        # increase test_length
        redo_data = {
            "swatch": p.get_spec_source().swatch.id,
            "body": p.get_spec_source().body.id,
            "garment_fit": SDC.FIT_HOURGLASS_OVERSIZED,
            "torso_length": p.get_spec_source().torso_length,
            "sleeve_length": p.get_spec_source().sleeve_length,
            "neckline_depth": p.get_spec_source().neckline_depth,
            "neckline_depth_orientation": p.get_spec_source().neckline_depth_orientation,
        }
        do_redo_page = reverse("design_wizard:redo_start", args=(p.pk,))
        resp = self.client.post(do_redo_page, data=redo_data, follow=True)

        # Approve the pattern
        approve_url = resp.redirect_chain[-1][0]
        approve_resp = self.client.post(approve_url, follow=True)

        detail_view_url = approve_resp.redirect_chain[-1][0]
        new_patterntext_resp = self.client.get(detail_view_url)
        for orig_html in orig_htmls:
            # Sanity check orign patterntext
            self.assertNotContains(new_patterntext_resp, orig_html, html=True)

        new_htmls = [
            "<li>Hourglass oversized fit</li>",
            """
            <p>CO 114 stitches using long tail cast-on or other cast-on method of your choice. 
            Work even in 1x1 Ribbing for 1\xbd&quot;/4 cm (10 rows from beginning),
            ending with a WS row.</p>
            """,
            """
            <p>CO 50 stitches using long tail or other cast-on method of your choice. 
            Work even in 1x1 Ribbing for \xbd&quot;/1.5 cm (4 rows), ending with a WS row.</p>
            """,
            """
            <div class="row">
            <div class="col-xs-6 col-sm-6 col-lg-5">back hip width</div>
            <div class="col-xs-6 col-sm-6 col-lg-5">22\xbe&quot;/58 cm</div>
            </div>""",
        ]
        for new_html in new_htmls:
            # Sanity check orign patterntext
            self.assertContains(new_patterntext_resp, new_html, html=True)
