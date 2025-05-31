import copy
import urllib.parse

from django.test import LiveServerTestCase, TestCase, tag
from django.test.client import Client
from django.urls import reverse
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from seleniumlogin import force_login

from customfit.userauth.factories import (
    FriendAndFamilyFactory,
    StaffFactory,
    UserFactory,
)

from .forms import (
    ArmcapShapingCalculatorForm,
    GaugeCalculatorForm,
    PickupCalculatorForm,
)
from .helpers import SpacingResult


class ShapingPlacerCalculatorTests(TestCase):

    def setUp(self):
        # Make user, log in
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("calculators:shaping_calculator")

    def tearDown(self):
        self.user.delete()

    def post_data(
        self, starting_stitches, ending_stitches, total_rows, stitches_per_shaping_row
    ):
        self.client.get(self.url)
        post_data = {
            "starting_stitches": starting_stitches,
            "ending_stitches": ending_stitches,
            "total_rows": total_rows,
            "stitches_per_shaping_row": stitches_per_shaping_row,
        }
        response = self.client.post(self.url, post_data)
        return response

    def test_maker_can_get_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(
            response, "knitting_calculators/shaping_calculator.html"
        )
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Shaping Calculator</title>", html=True)

    def test_staff_can_get_page(self):
        user = StaffFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(
            response, "knitting_calculators/shaping_calculator.html"
        )
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Shaping Calculator</title>", html=True)

    def test_friend_can_get_page(self):
        user = FriendAndFamilyFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(
            response, "knitting_calculators/shaping_calculator.html"
        )
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Shaping Calculator</title>", html=True)

    def test_anon_cannot_get_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        this_calc_url = reverse("calculators:shaping_calculator")
        this_calc_path = urllib.parse.urlparse(this_calc_url).path
        goal_redirect_url = "%s?next=%s" % (reverse("userauth:login"), this_calc_path)
        self.assertRedirects(response, goal_redirect_url, fetch_redirect_response=False)

    def test_field_validation_integer_fields(self):
        self.client.get(self.url)
        base_data = {
            "starting_stitches": 50,
            "ending_stitches": 70,
            "total_rows": 100,
            "stitches_per_shaping_row": 1,
        }

        for field in ["starting_stitches", "ending_stitches", "total_rows"]:
            # The field must be present
            post_data = copy.copy(base_data)
            del post_data[field]
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, field, "This field is required.")

            # Values must be integers
            for bad_input in ["10.5", "-10.5", "hello"]:
                post_data = copy.copy(base_data)
                post_data[field] = bad_input
                response = self.client.post(self.url, post_data)
                form = response.context["form"]
                with self.subTest(bad_input=bad_input):
                    self.assertFormError(form, field, "Enter a whole number.")

            # Values must be non-negative
            for bad_input in ["0", "-1"]:
                post_data = copy.copy(base_data)
                post_data[field] = bad_input
                response = self.client.post(self.url, post_data)
                form = response.context["form"]
                self.assertFormError(
                    form, field, "Ensure this value is greater than or equal to 1."
                )

    def test_field_validation_stitches_per_decrease(self):
        self.client.get(self.url)
        field = "stitches_per_shaping_row"
        base_data = {
            "starting_stitches": 50,
            "ending_stitches": 70,
            "total_rows": 100,
            "stitches_per_shaping_row": 1,
        }

        # The stitches_per field must be present
        post_data = copy.copy(base_data)
        del post_data[field]
        response = self.client.post(self.url, post_data)
        form = response.context["form"]
        self.assertFormError(form, field, "This field is required.")

        # Values must be one of the given choices
        for bad_input in ["10.5", "-10.5", "hello", 0, 3]:
            post_data = copy.copy(base_data)
            post_data[field] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            with self.subTest(bad_input=bad_input):
                self.assertFormError(
                    form,
                    field,
                    "Select a valid choice. %s is not one of the available choices."
                    % bad_input,
                )

    def test_unshapable_inputs_too_few_rows(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self.post_data(50, 70, 1, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        self.assertIn("shaping_error_message", response.context)
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t compute the shaping: There are more shaping rows than total
                rows. Check your inputs, and try again? (If you think this message is in error, drop us a
                note at help@example.com.)
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_unshapable_inputs_parity_error(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self.post_data(50, 71, 100, 2)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        self.assertIn("shaping_error_message", response.context)
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t shape an odd number of stitches at 2 stitches per row.
                Check your numbers and try again? If you think this message is in error, drop us a note
                at help@example.com and let us know what you were trying to do.
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_can_post_increase_data(self):
        response = self.post_data(50, 70, 100, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 2 rows even</li>
                    <li>[Work increase row, work 4 rows even] 19 times, work increase row</li>
                    <li>Work 2 rows even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_can_post_decrease_data(self):
        response = self.post_data(70, 50, 100, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 2 rows even</li>
                    <li>[Work decrease row, work 4 rows even] 19 times, work decrease row</li>
                    <li>Work 2 rows even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_can_post_increase_data_two_stitches(self):
        response = self.post_data(50, 70, 100, 2)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>
                        [Work increase row, work 10 rows even] 9 times, work increase row
                    </li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_can_post_decrease_data_two_stitches(self):
        response = self.post_data(70, 50, 100, 2)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>[Work decrease row, work 10 rows even] 9 times, work decrease row</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case1(self):
        response = self.post_data(70, 70, 1, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 1 row even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case2(self):
        response = self.post_data(70, 70, 1, 2)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 1 row even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case3(self):
        response = self.post_data(70, 70, 10, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 10 rows even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case4(self):
        response = self.post_data(70, 71, 1, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work increase row</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case5(self):
        response = self.post_data(70, 75, 5, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work increase row 5 times</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case6(self):
        response = self.post_data(70, 71, 3, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 1 row even</li>
                    <li>Work increase row</li>
                    <li>Work 1 row even</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_corner_case7(self):
        response = self.post_data(70, 72, 5, 1)
        self.assertEqual(response.context["tool_name"], "Shaping Calculator")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work increase row, work 3 rows even, work increase row</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)


class ButtonholeSpacerCalculatorTests(TestCase):

    def setUp(self):
        # Make user, log in
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("calculators:buttonhole_calculator")

    def tearDown(self):
        self.user.delete()

    def _post_data(
        self, number_of_stitches, number_of_buttons, stitches_per_buttonhole
    ):
        self.client.get(self.url)
        post_data = {
            "number_of_stitches": number_of_stitches,
            "number_of_buttons": number_of_buttons,
            "stitches_per_buttonhole": stitches_per_buttonhole,
        }
        response = self.client.post(self.url, post_data)
        return response

    def test_maker_can_get_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/button_spacer.html")
        self.assertEqual(response.context["tool_name"], "Buttonhole Placer")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertNotIn("number_of_buttons", response.context)
        self.assertContains(response, "<title>Buttonhole Placer</title>", html=True)

    def test_staff_can_get_page(self):
        user = StaffFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/button_spacer.html")
        self.assertEqual(response.context["tool_name"], "Buttonhole Placer")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertNotIn("number_of_buttons", response.context)
        self.assertContains(response, "<title>Buttonhole Placer</title>", html=True)

    def test_friend_can_get_page(self):
        user = FriendAndFamilyFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/button_spacer.html")
        self.assertEqual(response.context["tool_name"], "Buttonhole Placer")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertNotIn("number_of_buttons", response.context)
        self.assertContains(response, "<title>Buttonhole Placer</title>", html=True)

    def test_anon_cannot_get_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        this_calc_url = reverse("calculators:buttonhole_calculator")
        this_calc_path = urllib.parse.urlparse(this_calc_url).path
        goal_redirect_url = "%s?next=%s" % (reverse("userauth:login"), this_calc_path)
        self.assertRedirects(response, goal_redirect_url, fetch_redirect_response=False)

    def test_can_post_increase_data(self):
        response = self._post_data(100, 5, 2)
        self.assertEqual(response.context["tool_name"], "Buttonhole Placer")
        goal_html = """
            <div id="id_instruction_text">
                <ul>
                    <li>Work 9 sts</li>
                    <li>[Work buttonhole over 2 sts, work 18 sts] 4 times</li>
                    <li>Work buttonhole over 2 sts</li>
                    <li>Work 9 sts</li>
                </ul>
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_unshapable_inputs(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self._post_data(5, 5, 2)
        self.assertEqual(response.context["tool_name"], "Buttonhole Placer")
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t compute the button spacing: There aren&#39;t enough total
                stitches to make the buttonholes. Check your inputs, and try again? (If you think this message is
                in error, drop us a note at help@example.com.)
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    #
    # Tests from the Knitter's Toolbox app:

    def test_buttonband_basic(self):
        response = self._post_data(60, 5, 2)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 5 sts</li>
                        <li>[Work buttonhole over 2 sts, work 10 sts] 4 times</li>
                        <li>Work buttonhole over 2 sts</li>
                        <li>Work 5 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_huge1(self):
        response = self._post_data(405, 5, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 40 sts</li>
                        <li>[Work buttonhole over 1 st, work 80 sts] 4 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 40 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_huge2(self):
        response = self._post_data(439, 39, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 10 sts</li>
                        <li>[Work buttonhole over 1 st, work 10 sts] 38 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 10 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_huge3(self):
        response = self._post_data(439, 40, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 4 sts</li>
                        <li>[Work buttonhole over 1 st, work 10 sts] 39 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 5 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_minimal(self):
        response = self._post_data(19, 9, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 1 st</li>
                        <li>[Work buttonhole over 1 st, work 1 st] 8 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 1 st</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good1(self):
        response = self._post_data(18, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 1 st</li>
                        <li>[Work buttonhole over 1 st, work 4 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 1 st</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good2(self):
        response = self._post_data(19, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 1 st</li>
                        <li>[Work buttonhole over 1 st, work 4 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 2 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good3(self):
        response = self._post_data(20, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 2 sts</li>
                        <li>[Work buttonhole over 1 st, work 4 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 2 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good4(self):
        response = self._post_data(21, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 2 sts</li>
                        <li>[Work buttonhole over 1 st, work 4 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 3 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good5(self):
        response = self._post_data(22, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 3 sts</li>
                        <li>[Work buttonhole over 1 st, work 4 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 3 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_good6(self):
        response = self._post_data(23, 4, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 2 sts</li>
                        <li>[Work buttonhole over 1 st, work 5 sts] 3 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 2 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_too_few_stitches_1(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self._post_data(10, 50, 2)
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t compute the button spacing: There aren&#39;t enough total
                stitches to make the buttonholes. Check your inputs, and try again? (If you think this message is
                in error, drop us a note at help@example.com.)
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_too_few_stitches_2(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self._post_data(10, 5, 1)
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t compute the button spacing: There aren&#39;t enough total
                stitches to make the buttonholes. Check your inputs, and try again? (If you think this message is
                in error, drop us a note at help@example.com.)
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_too_few_stitches_3(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self._post_data(10, 10, 1)
        goal_html = """
            <div>
                We&#39;re sorry, but we can&#39;t compute the button spacing: There aren&#39;t enough total
                stitches to make the buttonholes. Check your inputs, and try again? (If you think this message is
                in error, drop us a note at help@example.com.)
            </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_zero_buttons(self):
        response = self._post_data(10, 0, 1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "number_of_buttons",
            "Ensure this value is greater than or equal to 1.",
        )

    def test_bad_total_stitches1(self):
        response = self._post_data(0, 4, 1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "number_of_stitches",
            "Ensure this value is greater than or equal to 1.",
        )

    def test_bad_total_stitches2(self):
        response = self._post_data(-1, 4, 1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "number_of_stitches",
            "Ensure this value is greater than or equal to 1.",
        )

    def test_bad_total_stitches3(self):
        response = self._post_data("A", 4, 1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(form, "number_of_stitches", "Enter a whole number.")

    def test_bad_total_stitches4(self):
        response = self._post_data("", 4, 1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(form, "number_of_stitches", "This field is required.")

    def test_bad_stitches_per1(self):
        response = self._post_data(23, 4, 0)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "stitches_per_buttonhole",
            "Select a valid choice. 0 is not one of the available choices.",
        )

    def test_bad_stitches_per2(self):
        response = self._post_data(23, 4, -1)
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "stitches_per_buttonhole",
            "Select a valid choice. -1 is not one of the available choices.",
        )

    def test_bad_stitches_per3(self):
        response = self._post_data(23, 4, "a")
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(
            form,
            "stitches_per_buttonhole",
            "Select a valid choice. a is not one of the available choices.",
        )

    def test_bad_stitches_per4(self):
        response = self._post_data(23, 4, "")
        # Should not pass form validation
        form = response.context["form"]
        self.assertFormError(form, "stitches_per_buttonhole", "This field is required.")

    def test_buttonband_minimal_stitches1(self):
        response = self._post_data(19, 9, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 1 st</li>
                        <li>[Work buttonhole over 1 st, work 1 st] 8 times</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 1 st</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_buttonband_minimal_stitches2(self):
        response = self._post_data(3, 1, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 1 st</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 1 st</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_one_button(self):
        response = self._post_data(23, 1, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 11 sts</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 11 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)

    def test_two_buttons(self):
        response = self._post_data(23, 2, 1)
        goal_html = """
                <div id="id_instruction_text"><ul>
                        <li>Work 5 sts</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 11 sts</li>
                        <li>Work buttonhole over 1 st</li>
                        <li>Work 5 sts</li>
                </ul></div>"""
        self.assertContains(response, goal_html, html=True)


class ShapingResultTests(TestCase):

    def test1(self):
        sr = SpacingResult(439, 40, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 4)
        self.assertEqual(sr.units_after_last_event, 4)
        self.assertEqual(sr.units_between_events, 9)
        self.assertEqual(sr.extra_units, 40)

    #
    # Tests from Knitters Toolbox
    #

    def test_good_case1(self):
        sr = SpacingResult(20, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 0)

    def test_good_case2(self):
        sr = SpacingResult(21, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 1)

    def test_good_case3(self):
        sr = SpacingResult(22, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 2)

    def test_good_case4(self):
        sr = SpacingResult(23, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 3)

    def test_good_case5(self):
        sr = SpacingResult(24, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 1)

    def test_good_case6(self):
        sr = SpacingResult(25, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 2)

    def test_good_case7(self):
        sr = SpacingResult(26, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 3)

    def test_good_case8(self):
        sr = SpacingResult(27, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 4)

    def test_good_case9(self):
        sr = SpacingResult(28, 4, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 3)
        self.assertEqual(sr.units_after_last_event, 3)
        self.assertEqual(sr.units_between_events, 6)
        self.assertEqual(sr.extra_units, 0)

    def test_corner_case1(self):
        sr = SpacingResult(9, 1, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 4)
        self.assertEqual(sr.units_after_last_event, 4)
        self.assertEqual(sr.units_between_events, None)
        self.assertEqual(sr.extra_units, 0)

    def test_corner_case2(self):
        sr = SpacingResult(9, 9, 1)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 0)
        self.assertEqual(sr.extra_units, 0)

    def test_corner_case3(self):
        sr = SpacingResult(8, 2, 1, interval_before_first_event=0.0)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 2)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 0)

    def test_corner_case4(self):
        sr = SpacingResult(8, 2, 1, interval_after_last_event=0.0)
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 2)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 4)
        self.assertEqual(sr.extra_units, 0)

    def test_bookends1(self):
        sr = SpacingResult(
            20, 4, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 1)

    def test_bookends2(self):
        sr = SpacingResult(
            21, 4, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 5)
        self.assertEqual(sr.extra_units, 2)

    def test_bookends3(self):
        sr = SpacingResult(
            22, 4, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 6)
        self.assertEqual(sr.extra_units, 0)

    def test_bookends4(self):
        sr = SpacingResult(
            23, 4, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 6)
        self.assertEqual(sr.extra_units, 1)

    def test_bookends5(self):
        sr = SpacingResult(
            20, 2, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertEqual(sr.units_between_events, 18)
        self.assertEqual(sr.extra_units, 0)

    def test_bookends6(self):
        sr = SpacingResult(
            20, 1, 1, interval_before_first_event=0.0, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 9)
        self.assertEqual(sr.units_after_last_event, 9)
        self.assertIsNone(sr.units_between_events)
        self.assertEqual(sr.extra_units, 1)

    def test_bookends7(self):
        sr = SpacingResult(
            20, 1, 1, interval_before_first_event=0.0, interval_after_last_event=0.5
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 0)
        self.assertEqual(sr.units_after_last_event, 19)
        self.assertIsNone(sr.units_between_events)
        self.assertEqual(sr.extra_units, 0)

    def test_bookends8(self):
        sr = SpacingResult(
            20, 1, 1, interval_before_first_event=0.1, interval_after_last_event=0.0
        )
        self.assertTrue(sr.constraints_met)
        self.assertEqual(sr.units_before_first_event, 19)
        self.assertEqual(sr.units_after_last_event, 0)
        self.assertIsNone(sr.units_between_events)
        self.assertEqual(sr.extra_units, 0)

    def test_bad_case1(self):
        sr = SpacingResult(3, 4, 1)
        self.assertFalse(sr.constraints_met)
        self.assertIsNone(sr.units_before_first_event)
        self.assertIsNone(sr.units_after_last_event)
        self.assertIsNone(sr.units_between_events)
        self.assertIsNone(sr.extra_units)

    def test_bad_case2(self):
        with self.assertRaises(AssertionError):
            SpacingResult(0, 4, 1)

    def test_bad_case3(self):
        with self.assertRaises(AssertionError):
            SpacingResult(3, 0, 1)

    def test_bad_case4(self):
        with self.assertRaises(AssertionError):
            SpacingResult(3, 1, 0)

    def test_bad_case5(self):
        with self.assertRaises(AssertionError):
            SpacingResult(10, 2, 1, interval_before_first_event=-0.1)

    def test_bad_case6(self):
        with self.assertRaises(AssertionError):
            SpacingResult(10, 2, 0, interval_after_last_event=-0.1)

    def test_bad_case7(self):
        sr = SpacingResult(10, 4, 3)
        self.assertFalse(sr.constraints_met)
        self.assertIsNone(sr.units_before_first_event)
        self.assertIsNone(sr.units_after_last_event)
        self.assertIsNone(sr.units_between_events)
        self.assertIsNone(sr.extra_units)


class ArmcapShaperCalculatorTests(TestCase):

    def setUp(self):
        # Make user, log in
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("calculators:armcap_shaping")

    def tearDown(self):
        self.user.delete()

    def _post_data(
        self,
        stitch_count,
        row_count,
        first_armhole_bindoffs,
        second_armhole_bindoffs,
        armhole_decreases,
        armhole_depth_value,
        armhole_depth_units,
        bicep_stitches,
    ):
        self.client.get(self.url)
        post_data = {
            "stitch_count": stitch_count,
            "row_count": row_count,
            "first_armhole_bindoffs": first_armhole_bindoffs,
            "second_armhole_bindoffs": second_armhole_bindoffs,
            "armhole_decreases": armhole_decreases,
            "armhole_depth_value": armhole_depth_value,
            "armhole_depth_units": armhole_depth_units,
            "bicep_stitches": bicep_stitches,
        }
        response = self.client.post(self.url, post_data)
        return response

    def test_maker_can_get_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/armcap_shaper.html")
        self.assertEqual(response.context["tool_name"], "Sleeve Cap Generator")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertContains(response, "<title>Sleeve Cap Generator</title>", html=True)

    def test_staff_can_get_page(self):
        user = StaffFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/armcap_shaper.html")
        self.assertEqual(response.context["tool_name"], "Sleeve Cap Generator")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertContains(response, "<title>Sleeve Cap Generator</title>", html=True)

    def test_friend_can_get_page(self):
        user = FriendAndFamilyFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/armcap_shaper.html")
        self.assertEqual(response.context["tool_name"], "Sleeve Cap Generator")
        self.assertNotIn("spacing_error_message", response.context)
        self.assertContains(response, "<title>Sleeve Cap Generator</title>", html=True)

    def test_anon_cannot_get_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        this_calc_url = reverse("calculators:armcap_shaping")
        this_calc_path = urllib.parse.urlparse(this_calc_url).path
        goal_redirect_url = "%s?next=%s" % (reverse("userauth:login"), this_calc_path)
        self.assertRedirects(response, goal_redirect_url, fetch_redirect_response=False)

    def test_can_post_data(self):
        response = self._post_data(
            20, 16, 7, 4, 3, 7, ArmcapShapingCalculatorForm._INCHES, 80
        )
        self.assertEqual(response.context["tool_name"], "Sleeve Cap Generator")
        goal_html = """
        <div id="id_instruction_text">
            <p>
              BO 7 stitches at the beginning of the next 2 rows.
            </p>
            <p>
              BO 4 stitches at the beginning of the following
              2 rows. 58 stitches remain.
            </p>
            <p>
              Decrease 1 stitch at <em><strong>each end</strong></em> of
              every row 6 times. 46 stitches remain.
            </p>
            <p>
              BO 3 stitches at the beginning of the next 4 rows.
            </p>
            <p>
              BO final 34 stitches.
            </p>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_no_possible_answer(self):
        with self.settings(AHD_SUPPORT_EMAIL_BARE="help@example.com"):
            response = self._post_data(
                20, 16, 7, 4, 3, 1, ArmcapShapingCalculatorForm._INCHES, 80
            )
        self.assertEqual(response.context["tool_name"], "Sleeve Cap Generator")
        goal_html = """
        <div>
            We&#39;re sorry, but given your input we can&#39;t calculate the sleeve cap
            shaping. Check your numbers and try again? If you think this
            message is in error, drop us a note at help@example.com
            and let us know what you were trying to do.
        </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_template_bug(self):
        response = self._post_data(
            20, 16, 7, 4, 3, 7, ArmcapShapingCalculatorForm._INCHES, 80
        )
        self.assertEqual(response.context["armscye_x"], 7)
        self.assertEqual(response.context["armscye_y"], 4)
        self.assertEqual(
            response.context["pre_bead_game_stitch_count"], 80 - sum([7, 7, 4, 4])
        )
        goal_html = """
            <p>
              BO 4 stitches at the beginning of the following
              2 rows. 58 stitches remain.
            </p>
        """
        self.assertContains(response, goal_html, html=True)


class PickupCalculatorTests(TestCase):

    def setUp(self):
        # Make user, log in
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("calculators:pickup_calculator")

    def tearDown(self):
        self.user.delete()

    def post_data(
        self,
        stitch_gauge,
        row_gauge,
        edge_input_type,
        rows_on_edge="",
        edge_in_inches="",
        edge_in_cms="",
    ):
        self.client.get(self.url)
        post_data = {
            "stitch_gauge": stitch_gauge,
            "row_gauge": row_gauge,
            "edge_input_type": edge_input_type,
            "rows_on_edge": rows_on_edge,
            "edge_in_inches": edge_in_inches,
            "edge_in_cms": edge_in_cms,
        }
        response = self.client.post(self.url, post_data)
        return response

    def test_maker_can_get_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/pickup_calculator.html")
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Pickup Calculator</title>", html=True)

    def test_staff_can_get_page(self):
        user = StaffFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/pickup_calculator.html")
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Pickup Calculator</title>", html=True)

    def test_friend_can_get_page(self):
        user = FriendAndFamilyFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/pickup_calculator.html")
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Pickup Calculator</title>", html=True)

    def test_anon_cannot_get_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        this_calc_url = reverse("calculators:pickup_calculator")
        this_calc_path = urllib.parse.urlparse(this_calc_url).path
        goal_redirect_url = "%s?next=%s" % (reverse("userauth:login"), this_calc_path)
        self.assertRedirects(response, goal_redirect_url, fetch_redirect_response=False)

    def test_stitch_gauge_validation(self):
        self.client.get(self.url)

        # Test that we can post liminal values for stitch_gauge
        response = self.post_data(
            4.0, 12, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=100
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 33 stitches</li>
            <li>(approx 1 st out of every 3 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            52.0, 12, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=100
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 433 stitches</li>
            <li>(approx 9 sts out of every 2 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        # Check some bad inputs
        base_data = {
            "stitch_gauge": 10,
            "row_gauge": 10.0,
            "edge_input_type": PickupCalculatorForm.EDGE_INPUT_COUNT,
            "rows_on_edge": 100,
        }

        def check_get_error(bad_input, error):
            post_data = copy.copy(base_data)
            post_data["stitch_gauge"] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, "stitch_gauge", error)

        test_cases = [
            (-1, "Ensure this value is greater than or equal to 4.0."),
            (0, "Ensure this value is greater than or equal to 4.0."),
            (0.9, "Ensure this value is greater than or equal to 4.0."),
            (3.9, "Ensure this value is greater than or equal to 4.0."),
            (52.1, "Ensure this value is less than or equal to 52.0."),
            ("foo", "Enter a number."),
            ("", "This field is required."),
        ]

        for bad_input, err_msg in test_cases:
            check_get_error(bad_input, err_msg)

    def test_row_gauge_validation(self):
        self.client.get(self.url)

        # Test that we can post liminal values for stitch_gauge
        response = self.post_data(
            10.0, 4.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=100
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 250 stitches</li>
            <li>(approx 5 sts out of every 2 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            10.0, 64.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=100
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 16 stitches</li>
            <li>(approx 1 st out of every 6 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        # Check some bad inputs
        base_data = {
            "stitch_gauge": 10.0,
            "row_gauge": 10.0,
            "edge_input_type": PickupCalculatorForm.EDGE_INPUT_COUNT,
            "rows_on_edge": 100,
        }

        def check_get_error(bad_input, error):
            post_data = copy.copy(base_data)
            post_data["row_gauge"] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, "row_gauge", error)

        test_cases = [
            (-1, "Ensure this value is greater than or equal to 4.0."),
            (0, "Ensure this value is greater than or equal to 4.0."),
            (3.9, "Ensure this value is greater than or equal to 4.0."),
            (0.9, "Ensure this value is greater than or equal to 4.0."),
            (64.1, "Ensure this value is less than or equal to 64.0."),
            ("foo", "Enter a number."),
            ("", "This field is required."),
        ]

        for bad_input, err_msg in test_cases:
            check_get_error(bad_input, err_msg)

    def test_can_post_data_row_count(self):
        response = self.post_data(
            10, 12, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=100
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 83 stitches</li>
            <li>(approx 5 sts out of every 6 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_row_count_validation(self):
        self.client.get(self.url)

        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=10
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 10 stitches</li>
            <li> (approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=1000
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 1000 stitches</li>
            <li>(approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        # Check some bad inputs
        base_data = {
            "stitch_gauge": 10,
            "row_gauge": 10,
            "edge_input_type": PickupCalculatorForm.EDGE_INPUT_COUNT,
            "rows_on_edge": 100,
        }

        def check_get_error(bad_input, error):
            post_data = copy.copy(base_data)
            post_data["rows_on_edge"] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, "rows_on_edge", error)

        test_cases = [
            (-1, "Ensure this value is greater than or equal to 10."),
            (0, "Ensure this value is greater than or equal to 10."),
            (9, "Ensure this value is greater than or equal to 10."),
            (100.1, "Enter a whole number."),
            (1001, "Ensure this value is less than or equal to 1000."),
            ("foo", "Enter a whole number."),
            ("", "Please enter a value"),
        ]

        for bad_input, err_msg in test_cases:
            check_get_error(bad_input, err_msg)

    def test_can_post_data_row_inches(self):
        response = self.post_data(
            10, 12, PickupCalculatorForm.EDGE_INPUT_INCHES, edge_in_inches=33.33
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 83 stitches</li>
            <li>(approx 5 sts out of every 6 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_row_inches_validation(self):
        self.client.get(self.url)

        # Test that we can post liminal values for stitch_gauge
        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_INCHES, edge_in_inches=0.5
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 1 stitch</li>
            <li> (approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_INCHES, edge_in_inches=1000
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 2500 stitches</li>
            <li>(approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        # Check some bad inputs
        base_data = {
            "stitch_gauge": 10,
            "row_gauge": 10,
            "edge_input_type": PickupCalculatorForm.EDGE_INPUT_INCHES,
            "edge_in_inches": 10,
        }

        def check_get_error(bad_input, error):
            post_data = copy.copy(base_data)
            post_data["edge_in_inches"] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, "edge_in_inches", error)

        test_cases = [
            (-1, "Ensure this value is greater than or equal to 0.5."),
            (0, "Ensure this value is greater than or equal to 0.5."),
            (0.1, "Ensure this value is greater than or equal to 0.5."),
            (1001, "Ensure this value is less than or equal to 1000."),
            ("foo", "Enter a number."),
            ("", "Please enter a value"),
        ]

        for bad_input, err_msg in test_cases:
            check_get_error(bad_input, err_msg)

    def test_can_post_data_row_cms(self):
        response = self.post_data(
            10, 12, PickupCalculatorForm.EDGE_INPUT_CMS, edge_in_cms=83.33
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 83 stitches</li>
            <li>(approx 5 sts out of every 6 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

    def test_row_cms_validation(self):
        self.client.get(self.url)

        # Test that we can post liminal values for stitch_gauge
        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_CMS, edge_in_cms=1.0
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 1 stitch</li>
            <li> (approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            10.0, 10.0, PickupCalculatorForm.EDGE_INPUT_CMS, edge_in_cms=2500
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 2500 stitches</li>
            <li>(approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        # Check some bad inputs
        base_data = {
            "stitch_gauge": 10,
            "row_gauge": 10,
            "edge_input_type": PickupCalculatorForm.EDGE_INPUT_CMS,
            "edge_in_inches": 10,
        }

        def check_get_error(bad_input, error):
            post_data = copy.copy(base_data)
            post_data["edge_in_cms"] = bad_input
            response = self.client.post(self.url, post_data)
            form = response.context["form"]
            self.assertFormError(form, "edge_in_cms", error)

        test_cases = [
            (-1, "Ensure this value is greater than or equal to 1.0."),
            (0, "Ensure this value is greater than or equal to 1.0."),
            (0.9, "Ensure this value is greater than or equal to 1.0."),
            (2501, "Ensure this value is less than or equal to 2500."),
            ("foo", "Enter a number."),
            ("", "Please enter a value"),
        ]

        for bad_input, err_msg in test_cases:
            check_get_error(bad_input, err_msg)

    def test_extreme_cases(self):
        response = self.post_data(
            4.0, 4.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=10
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 10 stitches</li>
            <li>(approx 1 st every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            52.0, 4.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=10
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 130 stitches</li>
            <li>(approx 9 sts every row)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            4.0, 64.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=10
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 1 stitch</li>
            <li>(approx 1 st out of every 9 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)

        response = self.post_data(
            52.0, 64.0, PickupCalculatorForm.EDGE_INPUT_COUNT, rows_on_edge=10
        )
        self.assertEqual(response.context["tool_name"], "Pickup Calculator")
        goal_html = """
        <div id="id_instruction_text">
        <ul>
            <li>pick up 8 stitches</li>
            <li>(approx 4 sts out of every 5 rows)</li>
        </ul>
        </div>
        """
        self.assertContains(response, goal_html, html=True)


@tag("selenium")
class PickupCalculatorFrontEndTests(LiveServerTestCase):

    def _get(self, rel_url):
        """
        Perform an HTTP GET request.

        Selenium needs full, not relative, URLs, so we need to join the output
        of reverse() to the URL base in order to get() anywhere.
        """
        full_url = urllib.parse.urljoin(self.live_server_url, rel_url)
        self.driver.get(full_url)

    def setUp(self):
        self.url = reverse("calculators:pickup_calculator")
        self.user = UserFactory()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)
        self.driver.implicitly_wait(2)
        self.wait = WebDriverWait(self.driver, 5)

        # Log in
        force_login(self.user, self.driver, self.live_server_url)

        self._get(self.url)

        self.i_know_menu = Select(self.driver.find_element(By.ID, "id_edge_input_type"))

        self.rows_on_edge_field = self.driver.find_element(By.ID, "id_rows_on_edge")
        self.rows_on_edge_row = self.driver.find_element(By.ID, "id_rows_on_edge_row")

        self.rows_in_inches_field = self.driver.find_element(By.ID, "id_edge_in_inches")
        self.rows_in_inches_row = self.driver.find_element(
            By.ID, "id_edge_in_inches_row"
        )

        self.rows_in_cms_field = self.driver.find_element(By.ID, "id_edge_in_cms")
        self.rows_in_cms_row = self.driver.find_element(By.ID, "id_edge_in_cms_row")

        self.submit_button = self.driver.find_element(By.ID, "submit-id-submit-btn")

        self.stitch_gauge_field = self.driver.find_element(By.ID, "id_stitch_gauge")
        self.row_gauge_field = self.driver.find_element(By.ID, "id_row_gauge")

    def tearDown(self):
        self.driver.quit()
        super(PickupCalculatorFrontEndTests, self).tearDown()

    def test_get_calculator(self):
        self._get(self.url)

    def test_inital_setup(self):
        self.assertEqual(
            self.i_know_menu.first_selected_option.text, "the edge's length in inches"
        )
        self.assertTrue(self.rows_in_inches_field.is_displayed())
        self.assertTrue(self.rows_in_inches_row.is_displayed())
        self.assertFalse(self.rows_on_edge_field.is_displayed())
        self.assertFalse(self.rows_on_edge_row.is_displayed())
        self.assertFalse(self.rows_in_cms_field.is_displayed())
        self.assertFalse(self.rows_in_cms_row.is_displayed())

    def test_select_row_count(self):
        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_inches_row.id))
        )
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_cms_row.id))
        )

        self.assertTrue(self.rows_on_edge_field.is_displayed())
        self.assertTrue(self.rows_on_edge_row.is_displayed())
        self.assertFalse(self.rows_in_inches_field.is_displayed())
        self.assertFalse(self.rows_in_inches_row.is_displayed())
        self.assertFalse(self.rows_in_cms_field.is_displayed())
        self.assertFalse(self.rows_in_cms_row.is_displayed())

    def test_select_row_cms(self):
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_inches_row.id))
        )
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_on_edge_row.id))
        )

        self.assertFalse(self.rows_in_inches_field.is_displayed())
        self.assertFalse(self.rows_in_inches_row.is_displayed())
        self.assertFalse(self.rows_on_edge_field.is_displayed())
        self.assertFalse(self.rows_on_edge_row.is_displayed())
        self.assertTrue(self.rows_in_cms_field.is_displayed())
        self.assertTrue(self.rows_in_cms_row.is_displayed())

    def test_select_row_inches(self):
        # Select something else then come back
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_inches_row.id))
        )
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_on_edge_row.id))
        )
        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_inches_row.id))
        )
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_cms_row.id))
        )

        self.assertTrue(self.rows_in_inches_field.is_displayed())
        self.assertTrue(self.rows_in_inches_row.is_displayed())
        self.assertFalse(self.rows_on_edge_field.is_displayed())
        self.assertFalse(self.rows_on_edge_row.is_displayed())
        self.assertFalse(self.rows_in_cms_field.is_displayed())
        self.assertFalse(self.rows_in_cms_row.is_displayed())

    def test_row_count_voided(self):
        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.rows_on_edge_field.send_keys("-10")
        self.assertEqual(
            self.rows_on_edge_field.get_attribute("value"), "-10"
        )  # sanity check
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_on_edge_row.id))
        )
        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.assertEqual(self.rows_on_edge_field.get_attribute("value"), "")

    def test_inches_voided(self):
        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.rows_in_inches_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_inches_field.get_attribute("value"), "-10"
        )  # sanity check
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_inches_row.id))
        )
        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.assertEqual(self.rows_in_inches_field.get_attribute("value"), "")

    def test_row_count_voided(self):
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.rows_in_cms_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_cms_field.get_attribute("value"), "-10"
        )  # sanity check
        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(
            EC.invisibility_of_element_located((By.ID, self.rows_in_cms_row.id))
        )
        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.assertEqual(self.rows_in_cms_field.get_attribute("value"), "")

    def test_bad_input_doesnt_hurt_count(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.rows_in_cms_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_cms_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.rows_in_inches_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_inches_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.rows_on_edge_field.send_keys("100")

        self.stitch_gauge_field.send_keys("20")
        self.row_gauge_field.send_keys("20")
        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")

    def test_bad_input_doesnt_hurt_inches(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.rows_in_cms_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_cms_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.rows_on_edge_field.send_keys("-10")
        self.assertEqual(
            self.rows_on_edge_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.rows_in_inches_field.send_keys("100")

        self.stitch_gauge_field.send_keys("20")
        self.row_gauge_field.send_keys("20")
        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")

    def test_bad_input_doesnt_hurt_cms(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_know_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.rows_on_edge_row))
        self.rows_on_edge_field.send_keys("-10")
        self.assertEqual(
            self.rows_on_edge_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("INCHES")
        self.wait.until(EC.visibility_of(self.rows_in_inches_row))
        self.rows_in_inches_field.send_keys("-10")
        self.assertEqual(
            self.rows_in_inches_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_know_menu.select_by_value("CMS")
        self.wait.until(EC.visibility_of(self.rows_in_cms_row))
        self.rows_in_cms_field.send_keys("100")

        self.stitch_gauge_field.send_keys("20")
        self.row_gauge_field.send_keys("20")
        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")


class GaugeCalculatorTests(TestCase):

    def setUp(self):
        # Make user, log in
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("calculators:gauge_calculator")

    def tearDown(self):
        self.user.delete()

    def post_data(
        self,
        output_type="",
        length_value="",
        length_type="",
        count_value="",
        count_type="",
        gauge_value="",
        gauge_type="",
    ):
        self.client.get(self.url)
        post_data = {
            "output_type_requested": output_type,
            "length_value": length_value,
            "length_type": length_type,
            "count_value": count_value,
            "count_type": count_type,
            "gauge_value": gauge_value,
            "gauge_type": gauge_type,
        }
        response = self.client.post(self.url, post_data)
        return response

    def test_maker_can_get_page(self):
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/gauge_calculator.html")
        self.assertEqual(response.context["tool_name"], "Gauge Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Gauge Calculator</title>", html=True)

    def test_staff_can_get_page(self):
        user = StaffFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/gauge_calculator.html")
        self.assertEqual(response.context["tool_name"], "Gauge Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Gauge Calculator</title>", html=True)

    def test_friend_can_get_page(self):
        user = FriendAndFamilyFactory()
        self.client.force_login(user)
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "knitting_calculators/gauge_calculator.html")
        self.assertEqual(response.context["tool_name"], "Gauge Calculator")
        self.assertNotIn("shaping_error_message", response.context)
        self.assertNotIn("num_shaping_rows", response.context)
        self.assertContains(response, "<title>Gauge Calculator</title>", html=True)

    def test_anon_cannot_get_page(self):
        self.client.logout()
        response = self.client.get(self.url)
        this_calc_url = reverse("calculators:gauge_calculator")
        this_calc_path = urllib.parse.urlparse(this_calc_url).path
        goal_redirect_url = "%s?next=%s" % (reverse("userauth:login"), this_calc_path)
        self.assertRedirects(response, goal_redirect_url, fetch_redirect_response=False)

    def test_compute_length(self):
        vectors = [
            (
                10,
                GaugeCalculatorForm.STITCHES_PER_INCH,
                100,
                GaugeCalculatorForm.STITCHES,
            ),
            (
                40,
                GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
                100,
                GaugeCalculatorForm.STITCHES,
            ),
            (
                39.4,
                GaugeCalculatorForm.STITCHES_PER_10CMS,
                100,
                GaugeCalculatorForm.STITCHES,
            ),
            (10, GaugeCalculatorForm.ROWS_PER_INCH, 100, GaugeCalculatorForm.ROWS),
            (
                40,
                GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
                100,
                GaugeCalculatorForm.ROWS,
            ),
            (39.4, GaugeCalculatorForm.ROWS_PER_10CMS, 100, GaugeCalculatorForm.ROWS),
        ]
        for gv, gt, cv, ct in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_value=cv,
                count_type=ct,
                gauge_value=gv,
                gauge_type=gt,
            )
            goal_html = '<div id="id_instruction_text">10&quot;/25.5 cm</div>'
            self.assertContains(response, goal_html, html=True)

    def test_compute_gauge(self):
        vectors = [
            (10, GaugeCalculatorForm.INCHES, 100, GaugeCalculatorForm.STITCHES),
            (25.4, GaugeCalculatorForm.CMS, 100, GaugeCalculatorForm.STITCHES),
        ]
        for lv, lt, cv, ct in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=lv,
                length_type=lt,
                count_value=cv,
                count_type=ct,
            )
            goal_html = '<div id="id_instruction_text">10 sts per inch / 39.5 sts per 4&quot; (10 cm)</div>'
            self.assertContains(response, goal_html, html=True)

        vectors = [
            (10, GaugeCalculatorForm.INCHES, 100, GaugeCalculatorForm.ROWS),
            (25.4, GaugeCalculatorForm.CMS, 100, GaugeCalculatorForm.ROWS),
        ]
        for lv, lt, cv, ct in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=lv,
                length_type=lt,
                count_value=cv,
                count_type=ct,
            )
            goal_html = '<div id="id_instruction_text">10 rows per inch / 39.5 rows per 4&quot; (10 cm)</div>'
            self.assertContains(response, goal_html, html=True)

    def test_compute_count(self):
        vectors = [
            (10, GaugeCalculatorForm.INCHES, 10, GaugeCalculatorForm.STITCHES_PER_INCH),
            (
                10,
                GaugeCalculatorForm.INCHES,
                40,
                GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
            ),
            (
                25.4,
                GaugeCalculatorForm.CMS,
                39.4,
                GaugeCalculatorForm.STITCHES_PER_10CMS,
            ),
        ]
        for lv, lt, gv, gt in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.COUNT,
                length_value=lv,
                length_type=lt,
                gauge_value=gv,
                gauge_type=gt,
            )
            goal_html = '<div id="id_instruction_text">100 sts</div>'
            self.assertContains(response, goal_html, html=True)

        vectors = [
            (10, GaugeCalculatorForm.INCHES, 10, GaugeCalculatorForm.ROWS_PER_INCH),
            (
                10,
                GaugeCalculatorForm.INCHES,
                40,
                GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
            ),
            (25.4, GaugeCalculatorForm.CMS, 39.4, GaugeCalculatorForm.ROWS_PER_10CMS),
        ]
        for lv, lt, gv, gt in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.COUNT,
                length_value=lv,
                length_type=lt,
                gauge_value=gv,
                gauge_type=gt,
            )
            goal_html = '<div id="id_instruction_text">100 rows</div>'
            self.assertContains(response, goal_html, html=True)

    def test_missing_inputs_type(self):
        response = self.post_data(
            output_type="",
            length_value=10,
            length_type=GaugeCalculatorForm.INCHES,
            count_value=10,
            count_type=GaugeCalculatorForm.STITCHES,
            gauge_value=10,
            gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
        )
        form = response.context["form"]
        self.assertFormError(form, "output_type_requested", "This field is required.")

    def test_missing_input_counts(self):
        inputs = {
            "length_value": 10,
            "length_type": GaugeCalculatorForm.INCHES,
            "gauge_value": 10,
            "gauge_type": GaugeCalculatorForm.STITCHES_PER_INCH,
        }
        errors = [
            ("length_value", "Enter a number."),
            ("length_type", "Please choose an option"),
            ("gauge_value", "Enter a number."),
            ("gauge_type", "Please choose an option"),
        ]

        for field, msg in errors:
            post_data = copy.copy(inputs)
            post_data[field] = ""
            post_data["output_type"] = GaugeCalculatorForm.COUNT
            response = self.post_data(**post_data)
            form = response.context["form"]
            self.assertFormError(form, field, msg)
            form_errors = form.errors
            self.assertIn(field, form_errors)
            self.assertNotIn("count_value", form_errors)
            self.assertNotIn("count_type", form_errors)

    def test_missing_input_gauge(self):
        inputs = {
            "length_value": 10,
            "length_type": GaugeCalculatorForm.INCHES,
            "count_value": 10,
            "count_type": GaugeCalculatorForm.STITCHES,
        }
        errors = [
            ("length_value", "Enter a number."),
            ("length_type", "Please choose an option"),
            ("count_value", "Enter a number."),
            ("count_type", "Please choose an option"),
        ]

        for field, msg in errors:
            post_data = copy.copy(inputs)
            post_data[field] = ""
            post_data["output_type"] = GaugeCalculatorForm.GAUGE
            response = self.post_data(**post_data)
            form = response.context["form"]
            self.assertFormError(form, field, msg)
            form_errors = form.errors
            self.assertNotIn("gauge_value", form_errors)
            self.assertNotIn("gauge_type", form_errors)

    def test_missing_input_length(self):
        inputs = {
            "gauge_value": 10,
            "gauge_type": GaugeCalculatorForm.STITCHES_PER_INCH,
            "count_value": 10,
            "count_type": GaugeCalculatorForm.STITCHES,
        }
        errors = [
            ("gauge_value", "Enter a number."),
            ("gauge_type", "Please choose an option"),
            ("count_value", "Enter a number."),
            ("count_type", "Please choose an option"),
        ]

        for field, msg in errors:
            post_data = copy.copy(inputs)
            post_data[field] = ""
            post_data["output_type"] = GaugeCalculatorForm.LENGTH
            response = self.post_data(**post_data)
            form = response.context["form"]
            self.assertFormError(form, field, msg)
            form_errors = form.errors
            self.assertNotIn("length_value", form_errors)
            self.assertNotIn("length_type", form_errors)

    def test_incompatible_inputs_length(self):
        vectors = [
            (10, GaugeCalculatorForm.STITCHES_PER_INCH, 100, GaugeCalculatorForm.ROWS),
            (
                40,
                GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
                100,
                GaugeCalculatorForm.ROWS,
            ),
            (
                39.4,
                GaugeCalculatorForm.STITCHES_PER_10CMS,
                100,
                GaugeCalculatorForm.ROWS,
            ),
            (10, GaugeCalculatorForm.ROWS_PER_INCH, 100, GaugeCalculatorForm.STITCHES),
            (
                40,
                GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
                100,
                GaugeCalculatorForm.STITCHES,
            ),
            (
                39.4,
                GaugeCalculatorForm.ROWS_PER_10CMS,
                100,
                GaugeCalculatorForm.STITCHES,
            ),
        ]
        for gv, gt, cv, ct in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_value=cv,
                count_type=ct,
                gauge_value=gv,
                gauge_type=gt,
            )
            form = response.context["form"]
            self.assertFormError(
                form, None, "Please choose either stitches or rows (but not both)"
            )

    def test_incompatible_input_count(self):
        vectors = [
            (10, GaugeCalculatorForm.CMS, 10, GaugeCalculatorForm.STITCHES_PER_INCH),
            (
                10,
                GaugeCalculatorForm.CMS,
                40,
                GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
            ),
            (
                25.4,
                GaugeCalculatorForm.INCHES,
                39.4,
                GaugeCalculatorForm.STITCHES_PER_10CMS,
            ),
            (10, GaugeCalculatorForm.CMS, 10, GaugeCalculatorForm.ROWS_PER_INCH),
            (10, GaugeCalculatorForm.CMS, 40, GaugeCalculatorForm.ROWS_PER_FOUR_INCHES),
            (
                25.4,
                GaugeCalculatorForm.INCHES,
                39.4,
                GaugeCalculatorForm.ROWS_PER_10CMS,
            ),
        ]
        for lv, lt, gv, gt in vectors:
            response = self.post_data(
                output_type=GaugeCalculatorForm.COUNT,
                length_value=lv,
                length_type=lt,
                gauge_value=gv,
                gauge_type=gt,
            )
            form = response.context["form"]
            self.assertFormError(
                form, None, "Please choose either inches or cm (but not both)"
            )

    def test_count_validation(self):
        self.client.get(self.url)

        bad_count_values = [-1, 0, 1, 1001]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=bad_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "count_value", "Please enter a number between 2.0 and 1000.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=bad_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "count_value", "Please enter a number between 2.0 and 1000.0."
            )

        bad_count_values = ["a", ""]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=bad_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
            )
            form = response.context["form"]
            self.assertFormError(form, "count_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=bad_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
            )
            form = response.context["form"]
            self.assertFormError(form, "count_value", "Enter a number.")

        good_count_values = [2, 100, 100.5, 1000]
        for good_count_value in good_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=good_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=good_count_value,
                gauge_value=10,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)

    def test_count_per_inch_validation(self):
        self.client.get(self.url)

        bad_count_values = [-1, 0, 1, 14]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 2.0 and 13.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 2.0 and 13.0."
            )

        bad_count_values = ["a", ""]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")

        good_count_values = [2, 12, 10.5, 13]
        for good_count_value in good_count_values:

            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_INCH,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_INCH,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)

    def test_count_per_10cm_validation(self):
        self.client.get(self.url)

        bad_count_values = [-1, 0, 1, 7, 52.5, 53]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_10CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 7.5 and 52.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_10CMS,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 7.5 and 52.0."
            )

        bad_count_values = ["a", ""]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_10CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_10CMS,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")

        good_count_values = [7.5, 12, 10.5, 52.0, 52]
        for good_count_value in good_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_10CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_10CMS,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)

    def test_count_per_4in_validation(self):
        self.client.get(self.url)

        bad_count_values = [-1, 0, 1, 7, 52.5, 53]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 7.5 and 52.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "gauge_value", "Please enter a number between 7.5 and 52.0."
            )

        bad_count_values = ["a", ""]
        for bad_count_value in bad_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=bad_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "gauge_value", "Enter a number.")

        good_count_values = [7.5, 12, 10.5, 52.0, 52]
        for good_count_value in good_count_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.STITCHES_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.LENGTH,
                gauge_value=good_count_value,
                gauge_type=GaugeCalculatorForm.ROWS_PER_FOUR_INCHES,
                count_type=GaugeCalculatorForm.ROWS,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)

    def test_inches_validation(self):
        self.client.get(self.url)

        bad_length_values = [-1, 0, 0.5, 74.1, 100]
        for bad_length_value in bad_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "length_value", "Please enter a number between 1.0 and 74.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "length_value", "Please enter a number between 1.0 and 74.0."
            )

        bad_length_values = ["a", ""]
        for bad_length_value in bad_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "length_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            self.assertFormError(form, "length_value", "Enter a number.")

        good_length_values = [1, 10, 10.5, 74]
        for good_length_value in good_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=good_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=good_length_value,
                length_type=GaugeCalculatorForm.INCHES,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)

    def test_cms_validation(self):
        self.client.get(self.url)

        bad_length_values = [-1, 0, 0.5, 2, 2.4, 183.1, 1000]
        for bad_length_value in bad_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "length_value", "Please enter a number between 2.5 and 183.0."
            )
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(
                form, "length_value", "Please enter a number between 2.5 and 183.0."
            )

        bad_length_values = ["a", ""]
        for bad_length_value in bad_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "length_value", "Enter a number.")
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=bad_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFormError(form, "length_value", "Enter a number.")

        good_length_values = [2.5, 10, 10.5, 74, 183]
        for good_length_value in good_length_values:
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=good_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)
            response = self.post_data(
                output_type=GaugeCalculatorForm.GAUGE,
                length_value=good_length_value,
                length_type=GaugeCalculatorForm.CMS,
                count_type=GaugeCalculatorForm.STITCHES,
                count_value=10,
            )
            form = response.context["form"]
            self.assertFalse(form.errors)


@tag("selenium")
class GaugeCalculatorFrontEndTests(LiveServerTestCase):

    def _get(self, rel_url):
        """
        Perform an HTTP GET request.

        Selenium needs full, not relative, URLs, so we need to join the output
        of reverse() to the URL base in order to get() anywhere.
        """
        full_url = urllib.parse.urljoin(self.live_server_url, rel_url)
        self.driver.get(full_url)

    def setUp(self):
        self.url = reverse("calculators:gauge_calculator")
        self.user = UserFactory()

        options = ChromeOptions()
        options.headless = True
        self.driver = WebDriver(options=options)
        self.driver.implicitly_wait(2)
        self.wait = WebDriverWait(self.driver, 5)

        # Log in
        force_login(self.user, self.driver, self.live_server_url)

        self._get(self.url)

        self.i_want_menu = Select(
            self.driver.find_element(By.ID, "id_output_type_requested")
        )

        self.length_field = self.driver.find_element(By.ID, "id_length_value")
        self.length_row = self.driver.find_element(By.ID, "length_row")

        self.count_field = self.driver.find_element(By.ID, "id_count_value")
        self.count_row = self.driver.find_element(By.ID, "count_row")

        self.gauge_field = self.driver.find_element(By.ID, "id_gauge_value")
        self.gauge_row = self.driver.find_element(By.ID, "gauge_row")

        self.submit_button = self.driver.find_element(By.ID, "submit-id-submit-btn")

    def tearDown(self):
        self.driver.quit()
        super(GaugeCalculatorFrontEndTests, self).tearDown()

    def test_get_calculator(self):
        self._get(self.url)

    def test_inital_setup(self):
        self.assertEqual(self.i_want_menu.first_selected_option.text, "size")
        self.assertTrue(self.count_field.is_displayed())
        self.assertTrue(self.count_row.is_displayed())
        self.assertFalse(self.length_field.is_displayed())
        self.assertFalse(self.length_row.is_displayed())
        self.assertTrue(self.gauge_field.is_displayed())
        self.assertTrue(self.gauge_row.is_displayed())

    def test_select_gauge(self):
        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.wait.until(EC.visibility_of(self.length_row))
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.gauge_row.id)))

        self.assertFalse(self.gauge_field.is_displayed())
        self.assertFalse(self.gauge_row.is_displayed())
        self.assertTrue(self.count_field.is_displayed())
        self.assertTrue(self.count_row.is_displayed())
        self.assertTrue(self.length_field.is_displayed())
        self.assertTrue(self.length_row.is_displayed())

    def test_select_count(self):
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.wait.until(EC.visibility_of(self.length_row))
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.count_row.id)))

        self.assertFalse(self.count_field.is_displayed())
        self.assertFalse(self.count_row.is_displayed())
        self.assertTrue(self.gauge_field.is_displayed())
        self.assertTrue(self.gauge_row.is_displayed())
        self.assertTrue(self.length_field.is_displayed())
        self.assertTrue(self.length_row.is_displayed())

    def test_select_length(self):
        # Select something else then select back
        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.wait.until(EC.visibility_of(self.length_row))
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.gauge_row.id)))

        self.i_want_menu.select_by_value("SIZE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.length_row.id)))

        self.assertFalse(self.length_field.is_displayed())
        self.assertFalse(self.length_row.is_displayed())
        self.assertTrue(self.count_field.is_displayed())
        self.assertTrue(self.count_row.is_displayed())
        self.assertTrue(self.gauge_field.is_displayed())
        self.assertTrue(self.gauge_row.is_displayed())

    def test_length_field_voided(self):
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.length_row))
        self.length_field.send_keys("-10")
        self.assertEqual(
            self.length_field.get_attribute("value"), "-10"
        )  # sanity check
        self.i_want_menu.select_by_value("SIZE")
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.length_row.id)))
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.length_row))
        self.assertEqual(self.length_field.get_attribute("value"), "")

    def test_count_field_voided(self):
        self.i_want_menu.select_by_value("SIZE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.count_field.send_keys("-10")
        self.assertEqual(self.count_field.get_attribute("value"), "-10")  # sanity check
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.length_row.id)))
        self.i_want_menu.select_by_value("SIZE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.assertEqual(self.count_field.get_attribute("value"), "")

    def test_gauge_field_voided(self):
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.gauge_field.send_keys("-10")
        self.assertEqual(self.gauge_field.get_attribute("value"), "-10")  # sanity check
        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.invisibility_of_element_located((By.ID, self.gauge_row.id)))
        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.assertEqual(self.gauge_field.get_attribute("value"), "")

    def test_bad_input_doesnt_hurt_length(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.visibility_of(self.length_row))
        self.length_field.send_keys("-10")
        self.assertEqual(
            self.length_field.get_attribute("value"), "-10"
        )  # sanity check

        self.i_want_menu.select_by_value("SIZE")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.gauge_field.send_keys("10")
        self.wait.until(EC.visibility_of(self.count_row))
        self.count_field.send_keys("10")

        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")

    def test_bad_input_doesnt_hurt_gauge(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.gauge_field.send_keys("-10")
        self.assertEqual(self.gauge_field.get_attribute("value"), "-10")  # sanity check

        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.count_field.send_keys("10")
        self.wait.until(EC.visibility_of(self.length_row))
        self.length_field.send_keys("10")

        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")

    def test_bad_input_doesnt_hurt_count(self):

        # sanity-check
        with self.assertRaises(NoSuchElementException):
            self.driver.find_element(By.ID, "id_instruction_text")

        self.i_want_menu.select_by_value("GAUGE")
        self.wait.until(EC.visibility_of(self.count_row))
        self.count_field.send_keys("-10")
        self.assertEqual(self.count_field.get_attribute("value"), "-10")  # sanity check

        self.i_want_menu.select_by_value("COUNT")
        self.wait.until(EC.visibility_of(self.gauge_row))
        self.gauge_field.send_keys("10")
        self.wait.until(EC.visibility_of(self.length_row))
        self.length_field.send_keys("10")

        self.submit_button.submit()

        # Should be no exception
        self.driver.find_element(By.ID, "id_instruction_text")

    #
    # def test_bad_input_doesnt_hurt_inches(self):
    #
    #     #sanity-check
    #     with self.assertRaises(NoSuchElementException):
    #         self.driver.find_element(By.ID,"id_instruction_text")
    #
    #     self.i_want_menu.select_by_value('CMS')
    #     self.wait.until(EC.visibility_of(self.gauge_row))
    #     self.gauge_field.send_keys("-10")
    #     self.assertEqual(self.gauge_field.get_attribute('value'), "-10") # sanity check
    #
    #     self.i_want_menu.select_by_value('COUNT')
    #     self.wait.until(EC.visibility_of(self.length_row))
    #     self.length_field.send_keys("-10")
    #     self.assertEqual(self.length_field.get_attribute('value'), "-10") # sanity check
    #
    #     self.i_want_menu.select_by_value('INCHES')
    #     self.wait.until(EC.visibility_of(self.count_row))
    #     self.count_field.send_keys("100")
    #
    #     self.stitch_gauge_field.send_keys("20")
    #     self.row_gauge_field.send_keys("20")
    #     self.submit_button.submit()
    #
    #     # Should be no exception
    #     self.driver.find_element(By.ID,"id_instruction_text")
    #
    # def test_bad_input_doesnt_hurt_cms(self):
    #
    #     #sanity-check
    #     with self.assertRaises(NoSuchElementException):
    #         self.driver.find_element(By.ID,"id_instruction_text")
    #
    #     self.i_want_menu.select_by_value('COUNT')
    #     self.wait.until(EC.visibility_of(self.length_row))
    #     self.length_field.send_keys("-10")
    #     self.assertEqual(self.length_field.get_attribute('value'), "-10") # sanity check
    #
    #     self.i_want_menu.select_by_value('INCHES')
    #     self.wait.until(EC.visibility_of(self.count_row))
    #     self.count_field.send_keys("-10")
    #     self.assertEqual(self.count_field.get_attribute('value'), "-10") # sanity check
    #
    #     self.i_want_menu.select_by_value('CMS')
    #     self.wait.until(EC.visibility_of(self.gauge_row))
    #     self.gauge_field.send_keys("100")
    #
    #     self.stitch_gauge_field.send_keys("20")
    #     self.row_gauge_field.send_keys("20")
    #     self.submit_button.submit()
    #
    #     # Should be no exception
    #     self.driver.find_element(By.ID,"id_instruction_text")
