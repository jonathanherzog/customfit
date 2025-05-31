import django.test
from django.core.exceptions import ValidationError
from django.urls import resolve, reverse

import customfit.designs.helpers.design_choices as DC
import customfit.sweaters.helpers.sweater_design_choices as SDC
from customfit.designs.factories import DesignerFactory
from customfit.stitches import models
from customfit.stitches.factories import StitchFactory
from customfit.sweaters.factories import SweaterDesignFactory


class RepeatsSpecTestCase(django.test.TestCase):

    def test_init_good(self):
        rs = models.RepeatsSpec()
        self.assertEqual(rs.x_mod, 0)
        self.assertEqual(rs.mod_y, 1)

        rs = models.RepeatsSpec(x_mod=3)
        self.assertEqual(rs.x_mod, 3)
        self.assertEqual(rs.mod_y, 1)

        rs = models.RepeatsSpec(mod_y=4)
        self.assertEqual(rs.x_mod, 0)
        self.assertEqual(rs.mod_y, 4)

        rs = models.RepeatsSpec(x_mod=2, mod_y=4)
        self.assertEqual(rs.x_mod, 2)
        self.assertEqual(rs.mod_y, 4)

        rs = models.RepeatsSpec(x_mod=None, mod_y=None)
        self.assertEqual(rs.x_mod, 0)
        self.assertEqual(rs.mod_y, 1)

    def test_init_bad(self):

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(x_mod=-1)

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(x_mod=0.5)

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(x_mod="1")

        with self.assertRaises(TypeError):
            models.RepeatsSpec(x_mod=[1])

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(mod_y=-1)

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(mod_y=0)

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(mod_y=0.5)

        with self.assertRaises(AssertionError):
            models.RepeatsSpec(mod_y="1")

        with self.assertRaises(TypeError):
            models.RepeatsSpec(mod_y=[1])

    def test_equals(self):

        default = models.RepeatsSpec()
        explicit_no_repeats = models.RepeatsSpec(x_mod=0, mod_y=1)

        repeats_a_1 = models.RepeatsSpec(x_mod=2, mod_y=3)
        repeats_a_2 = models.RepeatsSpec(x_mod=2, mod_y=3)

        repeats_b_1 = models.RepeatsSpec(x_mod=2, mod_y=4)
        repeats_b_2 = models.RepeatsSpec(x_mod=2, mod_y=4)

        self.assertEqual(default, explicit_no_repeats)
        self.assertEqual(explicit_no_repeats, default)
        self.assertNotEqual(default, repeats_a_1)
        self.assertNotEqual(default, repeats_b_1)

        self.assertNotEqual(repeats_a_1, explicit_no_repeats)
        self.assertNotEqual(repeats_a_1, default)
        self.assertEqual(repeats_a_1, repeats_a_2)
        self.assertNotEqual(repeats_a_1, repeats_b_1)

        self.assertNotEqual(repeats_b_1, explicit_no_repeats)
        self.assertNotEqual(repeats_b_1, default)
        self.assertNotEqual(repeats_b_1, repeats_a_1)
        self.assertEqual(repeats_b_1, repeats_b_2)

        self.assertNotEqual(default, None)


class StitchFactoryTest(django.test.TestCase):

    def test_factories(self):
        """
        Test that the factories work the way we expect them to.
        """
        # Plain stitch from factory
        stitch1 = StitchFactory(name="foo")
        self.assertEqual(stitch1.name, "foo")
        self.assertEqual(stitch1.repeats_x_mod, 0)
        self.assertEqual(stitch1.repeats_mod_y, 1)

        # Now, is the factory using get_or_create() under the hood?
        stitch2 = StitchFactory(name="foo")
        self.assertEqual(stitch1.id, stitch2.id)


class StitchTestCase(django.test.TestCase):

    #
    # Well-formed / expected-use tests
    #

    def test_factory(self):
        StitchFactory.build()
        StitchFactory()

    def test_clean_validation(self):

        stitch1 = StitchFactory.build(repeats_mod_y=0)
        with self.assertRaises(ValidationError):
            stitch1.full_clean()

        stitch2 = StitchFactory.build(repeats_mod_y=-1)
        with self.assertRaises(ValidationError):
            stitch2.full_clean()

        stitch3 = StitchFactory.build(repeats_x_mod=-1)
        with self.assertRaises(ValidationError):
            stitch3.full_clean()

    def test_str(self):
        name = "test name"
        st = StitchFactory.build(name=name)
        string = "%s" % st
        self.assertEqual(string, name)

    def test_patterntext(self):
        name = "test name"
        st = StitchFactory.build(name=name)
        self.assertEqual(st.patterntext, name)

        patterntext = "patterntext"
        st = StitchFactory.build(name=name, _patterntext=patterntext)
        self.assertEqual(st.patterntext, patterntext)

    def test_use_repeats(self):
        stitch1 = StitchFactory.build()
        self.assertFalse(stitch1.use_repeats)

        stitch2 = StitchFactory.build(repeats_x_mod=0, repeats_mod_y=1)
        self.assertFalse(stitch2.use_repeats)

        stitch3 = StitchFactory.build(repeats_x_mod=1)
        self.assertTrue(stitch3.use_repeats)

        stitch4 = StitchFactory.build(repeats_mod_y=2)
        self.assertTrue(stitch4.use_repeats)

    def test_is_compatible(self):

        no_repeats = StitchFactory.build()

        repeats_a_stitch1 = StitchFactory.build(repeats_x_mod=2, repeats_mod_y=2)

        repeats_a_stitch2 = StitchFactory.build(repeats_x_mod=2, repeats_mod_y=2)

        repeats_b_stitch = StitchFactory.build(repeats_x_mod=2, repeats_mod_y=4)

        self.assertTrue(no_repeats.is_compatible(None))
        self.assertTrue(no_repeats.is_compatible(repeats_a_stitch1))
        self.assertTrue(no_repeats.is_compatible(repeats_b_stitch))

        self.assertTrue(repeats_a_stitch1.is_compatible(None))
        self.assertTrue(repeats_a_stitch1.is_compatible(no_repeats))
        self.assertTrue(repeats_a_stitch1.is_compatible(repeats_a_stitch2))
        self.assertFalse(repeats_a_stitch1.is_compatible(repeats_b_stitch))

        self.assertTrue(repeats_b_stitch.is_compatible(None))
        self.assertTrue(repeats_b_stitch.is_compatible(no_repeats))
        self.assertFalse(repeats_b_stitch.is_compatible(repeats_a_stitch2))

    def test_get_absolute_url(self):
        st = StitchFactory()
        goal_url = "/stitches/%s" % st.pk
        self.assertEqual(st.get_absolute_url(), goal_url)

    def test_get_repeats_spec(self):
        stitch1 = StitchFactory.build()
        self.assertFalse(stitch1.use_repeats)

        stitch2 = StitchFactory.build(repeats_x_mod=0, repeats_mod_y=1)
        self.assertFalse(stitch2.use_repeats)

        stitch3 = StitchFactory.build(repeats_x_mod=1)
        self.assertTrue(stitch3.use_repeats)

        stitch4 = StitchFactory.build(repeats_mod_y=2)
        self.assertTrue(stitch4.use_repeats)

    def test_model_managers(self):

        edge_stitch = StitchFactory(
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=False,
            is_panel_stitch=False,
            user_visible=True,
        )

        allover_stitch = StitchFactory(
            is_waist_hem_stitch=False,
            is_sleeve_hem_stitch=False,
            is_neckline_hem_stitch=False,
            is_armhole_hem_stitch=False,
            is_buttonband_hem_stitch=False,
            is_allover_stitch=True,
            is_panel_stitch=True,
            user_visible=True,
        )

        private_stitch = StitchFactory(
            is_waist_hem_stitch=True,
            is_sleeve_hem_stitch=True,
            is_neckline_hem_stitch=True,
            is_armhole_hem_stitch=True,
            is_buttonband_hem_stitch=True,
            is_allover_stitch=True,
            is_panel_stitch=True,
            user_visible=False,
        )

        # Default manager
        self.assertIn(edge_stitch, models.Stitch.objects.all())
        self.assertIn(allover_stitch, models.Stitch.objects.all())
        self.assertIn(private_stitch, models.Stitch.objects.all())

        # Waist hem
        self.assertIn(edge_stitch, models.Stitch.public_waist_hem_stitches.all())
        self.assertNotIn(allover_stitch, models.Stitch.public_waist_hem_stitches.all())
        self.assertNotIn(private_stitch, models.Stitch.public_waist_hem_stitches.all())

        # sleeve hem
        self.assertIn(edge_stitch, models.Stitch.public_sleeve_hem_stitches.all())
        self.assertNotIn(allover_stitch, models.Stitch.public_sleeve_hem_stitches.all())
        self.assertNotIn(private_stitch, models.Stitch.public_sleeve_hem_stitches.all())

        # Neckline hem
        self.assertIn(edge_stitch, models.Stitch.public_neckline_hem_stitches.all())
        self.assertNotIn(
            allover_stitch, models.Stitch.public_neckline_hem_stitches.all()
        )
        self.assertNotIn(
            private_stitch, models.Stitch.public_neckline_hem_stitches.all()
        )

        # Armhole hem
        self.assertIn(edge_stitch, models.Stitch.public_armhole_hem_stitches.all())
        self.assertNotIn(
            allover_stitch, models.Stitch.public_armhole_hem_stitches.all()
        )
        self.assertNotIn(
            private_stitch, models.Stitch.public_armhole_hem_stitches.all()
        )

        # Waist hem
        self.assertIn(edge_stitch, models.Stitch.public_buttonband_hem_stitches.all())
        self.assertNotIn(
            allover_stitch, models.Stitch.public_buttonband_hem_stitches.all()
        )
        self.assertNotIn(
            private_stitch, models.Stitch.public_buttonband_hem_stitches.all()
        )

        # Allover stitch
        self.assertNotIn(edge_stitch, models.Stitch.public_allover_stitches.all())
        self.assertIn(allover_stitch, models.Stitch.public_allover_stitches.all())
        self.assertNotIn(private_stitch, models.Stitch.public_allover_stitches.all())

        # Panels
        self.assertNotIn(edge_stitch, models.Stitch.public_panel_stitches.all())
        self.assertIn(allover_stitch, models.Stitch.public_panel_stitches.all())
        self.assertNotIn(private_stitch, models.Stitch.public_panel_stitches.all())

        private_stitch.delete()
        edge_stitch.delete()
        allover_stitch.delete()


class StitchViewTestCase(django.test.TestCase):

    def setUp(self):
        self.stitch = StitchFactory(name="Mossy Cabled Rib Lace", user_visible=True)
        self.stitch.short_description = "Visible from space"
        self.stitch.notes = "*k1 p2 r3 g5, rep from *"
        self.stitch.save()
        self.client = django.test.client.Client()

    def test_list_page_renders(self):
        """
        Anon user goes to the front page and it is rendered with
        StitchListView
        """
        url = reverse("stitch_models:stitch_list_view")
        found = resolve(url)
        self.assertEqual(found.view_name, "stitch_models:stitch_list_view")

    def test_detail_page_renders(self):
        """
        Anon user goes to the detail page for a stitch and it is rendered with
        StitchListView
        """
        url = reverse("stitch_models:stitch_detail_view", args=(self.stitch.pk,))
        found = resolve(url)
        self.assertEqual(found.view_name, "stitch_models:stitch_detail_view")

    def test_list_page_contains_stitch_info(self):
        url = reverse("stitch_models:stitch_list_view")
        response = self.client.get(url)
        self.assertContains(response, "Mossy Cabled Rib Lace")
        self.assertContains(response, "Visible from space")

    def test_detail_page_contains_stitch_info(self):
        url = reverse("stitch_models:stitch_detail_view", args=(self.stitch.pk,))
        response = self.client.get(url)
        self.assertContains(response, "Mossy Cabled Rib Lace")
        self.assertContains(response, "Visible from space")
        self.assertContains(response, "*k1 p2 r3 g5, rep from *")

    def test_get_public_designs(self):
        """
        `get_public_designs` should return everything that is visible
        to any (non-staff) user.
        """
        # This import didn't work up top. Something must be circular somewhere.

        designer = DesignerFactory()

        design1 = SweaterDesignFactory(
            back_allover_stitch=self.stitch, designer=designer
        )
        design2 = SweaterDesignFactory(
            back_allover_stitch=self.stitch, designer=designer, visibility=DC.PRIVATE
        )
        design3 = SweaterDesignFactory(
            back_allover_stitch=self.stitch, designer=designer, visibility=DC.LIMITED
        )
        design4 = SweaterDesignFactory(
            back_allover_stitch=self.stitch, designer=designer, visibility=DC.FEATURED
        )
        designs = self.stitch.get_public_designs()
        self.assertIn(design1, designs)
        self.assertNotIn(design2, designs)
        self.assertIn(design3, designs)
        self.assertIn(design4, designs)
