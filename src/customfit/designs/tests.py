import datetime
import itertools
import logging
import unittest.mock as mock
from io import BytesIO

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context
from django.test import TestCase
from django.test.client import Client
from django.urls import reverse
from PIL import Image

import customfit.designs.helpers.design_choices as DC
from customfit.swatches.factories import GaugeFactory
from customfit.userauth.factories import StaffFactory, UserFactory

from .factories import DesignerFactory, DesignFactory
from .models import AdditionalDesignElement, Collection, Design, RavelryUrlValidator

# Get an instance of a logger
logger = logging.getLogger(__name__)


class DesignerTests(TestCase):

    def test_clean(self):
        designer = DesignerFactory(primary_home_page=None, secondary_home_page="stuff")
        with self.assertRaises(ValidationError):
            designer.clean()


class RavelryUrlValidatorTests(TestCase):

    def setUp(self):
        self.validator = RavelryUrlValidator()

    def test_good_urls(self):
        url = "http://www.ravelry.com/designers/some-designer"
        self.validator(url)

        url = "https://www.ravelry.com/designers/some-designer"
        self.validator(url)

        url = "http://ravelry.com/designers/some-designer"
        self.validator(url)

        url = "https://ravelry.com/designers/some-designer"
        self.validator(url)

        url = "https://ravelry.com/designers/some-designer"
        self.validator(url)

        url = "https://baz.ravelry.com/foo/bar"
        self.validator(url)

        url = "https://RaVelRy.COm/foo/bar"
        self.validator(url)

    def test_bad_urls(self):

        url = "http://facebook.com/designers/some-designer"
        with self.assertRaises(ValidationError):
            self.validator(url)

        url = "http://.ravelry.com/designers/some-designer"
        with self.assertRaises(ValidationError):
            self.validator(url)

        url = "http://google.com"
        with self.assertRaises(ValidationError):
            self.validator(url)

        url = "www.ravelry.com/designers/some-designer"
        with self.assertRaises(ValidationError):
            self.validator(url)


class CollectionTests(TestCase):

    def test_displayable_manager(self):
        #
        # setup
        #
        private_design1 = DesignFactory(visibility=DC.PRIVATE)
        private_design2 = DesignFactory(visibility=DC.PRIVATE)
        private_design3 = DesignFactory(visibility=DC.PRIVATE)
        public_design1 = DesignFactory(visibility=DC.PUBLIC)
        public_design2 = DesignFactory(visibility=DC.PUBLIC)
        public_design3 = DesignFactory(visibility=DC.PUBLIC)

        collection1 = Collection(name="1")
        collection2 = Collection(name="2")
        collection3 = Collection(name="3")
        collection4 = Collection(name="4")
        collection1.save()
        collection2.save()
        collection3.save()
        collection4.save()

        # Collection 1 contains only private designs
        private_design1.collection = collection1
        private_design2.collection = collection1
        private_design1.save()
        private_design2.save()

        # Collection 2 contains only public designs
        private_design3.collection = collection2
        public_design1.collection = collection2
        private_design3.save()
        public_design1.save()

        # Collection 3 contains one public, one private design
        public_design2.collection = collection3
        public_design3.collection = collection3
        public_design2.save()
        public_design3.save()

        # Collection 4 has nothing in it at all. SO sad.

        #
        # Test
        #
        displayables = Collection.displayable.all()
        self.assertNotIn(collection1, displayables)
        self.assertIn(collection2, displayables)
        self.assertIn(collection3, displayables)
        self.assertNotIn(collection4, displayables)

        #
        # Tear down
        #
        private_design1.delete()
        private_design2.delete()
        private_design3.delete()
        public_design1.delete()
        public_design2.delete()
        public_design3.delete()
        collection1.delete()
        collection2.delete()
        collection3.delete()
        collection4.delete()

    def test_visible_designs(self):
        #
        # setup
        #
        collection = Collection()
        collection.save()
        private_design = DesignFactory(visibility=DC.PRIVATE, collection=collection)
        public_design = DesignFactory(visibility=DC.PUBLIC, collection=collection)
        limited_design = DesignFactory(visibility=DC.LIMITED, collection=collection)
        featured_design = DesignFactory(visibility=DC.FEATURED, collection=collection)
        private_design.save()
        public_design.save()
        limited_design.save()
        featured_design.save()

        #
        # Test
        #
        visibles = collection.visible_designs
        self.assertNotIn(private_design, visibles)
        self.assertNotIn(limited_design, visibles)
        self.assertIn(public_design, visibles)
        self.assertIn(featured_design, visibles)

        #
        # Tear down
        #
        private_design.delete()
        public_design.delete()
        limited_design.delete()
        featured_design.delete()
        collection.delete()


class AllCollectionsViewTests(TestCase):

    longMessage = True

    def test_collections_page(self):
        """
        If AllCollectionsView and SilhouetteView aren't in the right order in
        urls.py, when users go to /designs/collections, SilhouetteView will look
        for a silhouette named 'collections' and we will be sad.
        """
        collections_url = reverse("designs:all_collections")
        client = Client()
        response = client.get(collections_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Our ever-growing list of collections.", response.rendered_content
        )


class AllDesignsViewTests(TestCase):

    def test_make_your_own(self):
        response = self.client.get(reverse("designs:all_designs"))
        self.assertContains(response, "<h2>Build your own design</h2>")
        self.assertContains(
            response,
            """
                <a href="/design/custom/sweaters/">
                    <img src="/static/img/byo-sweater-image.png" class="choose-design-hero">
                    <p>Make your own sweater</p>
                </a>""",
        )
        self.assertContains(
            response,
            """
                <a href="/design/custom/cowls/">
                    <img src="/static/img/byo-cowl-image.png" class="choose-design-hero">
                    <p>Make your own cowl</p>
                </a>""",
        )


class DesignModelTests(TestCase):

    pass


class DesignBaseMethodTests(TestCase):

    pass


class DesignMethodTests(TestCase):

    def _get_image_check_response(self, image_path):
        """
        Get an image from a path (relative to STATIC) and check
        that the response is OK.
        """
        full_path = settings.STATIC_URL + image_path
        response = self.client.get(full_path)
        msg = full_path + " (This usually means you need to run collectstatic.)"
        self.assertEqual(response.status_code, 200, msg)

    def test_visibility(self):
        private_design = DesignFactory(visibility=DC.PRIVATE)
        limited_design = DesignFactory(visibility=DC.LIMITED)
        public_design = DesignFactory(visibility=DC.PUBLIC)
        featured_design = DesignFactory(visibility=DC.FEATURED)

        normal_user = UserFactory()
        self.assertFalse(private_design.is_visible_to_user(normal_user))
        self.assertFalse(limited_design.is_visible_to_user(normal_user))
        self.assertTrue(public_design.is_visible_to_user(normal_user))
        self.assertTrue(featured_design.is_visible_to_user(normal_user))

        staff = StaffFactory()
        self.assertTrue(private_design.is_visible_to_user(staff))
        self.assertTrue(limited_design.is_visible_to_user(staff))
        self.assertTrue(public_design.is_visible_to_user(staff))
        self.assertTrue(featured_design.is_visible_to_user(staff))

    def test_public_visibilty(self):
        private_design = DesignFactory(visibility=DC.PRIVATE)
        limited_design = DesignFactory(visibility=DC.LIMITED)
        public_design = DesignFactory(visibility=DC.PUBLIC)
        featured_design = DesignFactory(visibility=DC.FEATURED)

        self.assertFalse(private_design.is_visible_to_public())
        self.assertFalse(limited_design.is_visible_to_public())
        self.assertTrue(public_design.is_visible_to_public())
        self.assertTrue(featured_design.is_visible_to_public())

    def test_get_purchase_url(self):
        design_no_leading_slash = DesignFactory(purchase_url="purchase/url/foo")

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com"):
            self.assertEqual(
                design_no_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com/"):
            self.assertEqual(
                design_no_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com/path/"):
            self.assertEqual(
                design_no_leading_slash.get_full_purchase_url(),
                "http://example.com/path/purchase/url/foo",
            )

        design_leading_slash = DesignFactory(purchase_url="/purchase/url/foo")

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com"):
            self.assertEqual(
                design_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com/"):
            self.assertEqual(
                design_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )

        # NOTE THE GOTCHAS HERE
        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com/path/"):
            self.assertEqual(
                design_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )

        with self.settings(AHD_WC_PRODUCTS_BASE_URL="http://example.com/path"):
            self.assertEqual(
                design_leading_slash.get_full_purchase_url(),
                "http://example.com/purchase/url/foo",
            )


class DesignManagerTestsWithCollections(TestCase):

    def setUp(self):
        # Sanity-check
        self.assertFalse(Design.objects.exists())
        self.assertFalse(Collection.objects.exists())

        # Create all combinations, store in dict
        image = SimpleUploadedFile("image.jpg", b"contents")

        self.old_collection = Collection(name="old")
        self.old_collection.save()
        self.new_collection = Collection(name="new")
        self.new_collection.save()
        self.new_collection.creation_date = (
            self.old_collection.creation_date + datetime.timedelta(weeks=1)
        )
        self.new_collection.save()
        # Make sure we agree with the database about which is the 'latest'
        # collectiion
        self.assertEqual(Collection.objects.latest(), self.new_collection)

        self.designs = {}
        combinations = itertools.product(
            [DC.PRIVATE, DC.LIMITED, DC.PUBLIC, DC.FEATURED],
            [image, None],
            [self.old_collection, self.new_collection, None],
            [True, False],  # is_basec
        )
        for combination in combinations:
            (visibility, image, collection, is_basic) = combination
            design = DesignFactory(
                image=image,
                collection=collection,
                visibility=visibility,
                is_basic=is_basic,
            )
            design.save()
            self.designs[combination] = design

    def tearDown(self):
        for design in list(self.designs.values()):
            design.delete()
        self.old_collection.delete()
        self.new_collection.delete()

    def _assert_sorted_by_name(self, design_list):
        sorted_by_name = sorted(design_list, key=lambda design: design.name)
        self.assertEqual(design_list, sorted_by_name)

    def test_listable_manager(self):
        listables = list(Design.listable.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, _, _) = combination
            if all(
                [image is not None, visibility in [DC.LIMITED, DC.PUBLIC, DC.FEATURED]]
            ):
                self.assertIn(design, listables)
            else:
                self.assertNotIn(design, listables)

        # How many listable patterns should there be?
        # * 3 valid options for visibility,
        # * 1 valid option for image,
        # * 3 Valid options for collection
        # * 2 valid options for is_basic
        self.assertEqual(len(listables), 3 * 1 * 3 * 2)

        self._assert_sorted_by_name(listables)

    def test_basics_manager(self):
        basics = list(Design.basic.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, _, is_basic) = combination
            if all(
                [
                    image is not None,
                    visibility in [DC.LIMITED, DC.PUBLIC, DC.FEATURED],
                    is_basic == True,
                ]
            ):
                self.assertIn(design, basics)
            else:
                self.assertNotIn(design, basics)

        # How many listable patterns should there be?
        # * 3 valid options for visibility,
        # * 1 valid option for image,
        # * 3 Valid options for collection
        # * 1 valid options for is_basic
        self.assertEqual(len(basics), 3 * 1 * 3 * 1)

        self._assert_sorted_by_name(basics)

    def test_nonbasics_manager(self):
        nonbasics = list(Design.designed.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, _, is_basic) = combination
            if all(
                [
                    image is not None,
                    visibility in [DC.LIMITED, DC.PUBLIC, DC.FEATURED],
                    is_basic == False,
                ]
            ):
                self.assertIn(design, nonbasics)
            else:
                self.assertNotIn(design, nonbasics)

        # How many listable patterns should there be?
        # * 3 valid options for visibility,
        # * 1 valid option for image,
        # * 3 Valid options for collection
        # * 1 valid options for is_basic
        self.assertEqual(len(nonbasics), 3 * 1 * 3 * 1)

        self._assert_sorted_by_name(nonbasics)

    def test_promoted_manager(self):
        promoted = list(Design.currently_promoted.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, collection, is_basic) = combination
            if all(
                [
                    image is not None,
                    visibility in [DC.LIMITED, DC.PUBLIC, DC.FEATURED],
                    (visibility == DC.FEATURED or collection == self.new_collection),
                ]
            ):
                self.assertIn(design, promoted)
            else:
                self.assertNotIn(design, promoted)

        # How many listable patterns should there be?
        # * 1 valid option for image,
        # * 2 valid options for is_basic
        # * If in latest collection, three options for visibility
        # * If not in latest collection, 1 option for visibility
        self.assertEqual(len(promoted), 2 * 1 * (3 + (2 * 1)))

        self._assert_sorted_by_name(promoted)

    def test_featured_manager(self):
        featured = list(Design.featured.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, _, is_basic) = combination
            if all([image is not None, visibility == DC.FEATURED]):
                self.assertIn(design, featured)
            else:
                self.assertNotIn(design, featured)

        # How many listable patterns should there be?
        # * 1 valid options for visibility,
        # * 1 valid option for image,
        # * 3 Valid options for collection
        # * 2 valid options for is_basic
        self.assertEqual(len(featured), 1 * 1 * 3 * 2)

        self._assert_sorted_by_name(featured)


class DesignManagerTestsNoCollections(TestCase):

    def setUp(self):
        # Sanity-check
        self.assertFalse(Design.objects.exists())
        self.assertFalse(Collection.objects.exists())

        # Create all combinations, store in dict
        image = SimpleUploadedFile("image.jpg", b"contents")

        self.designs = {}
        combinations = itertools.product(
            [DC.PRIVATE, DC.LIMITED, DC.PUBLIC, DC.FEATURED],
            [image, None],
            [True, False],  # is_basec
        )
        for combination in combinations:
            (visibility, image, is_basic) = combination
            design = DesignFactory(
                image=image, collection=None, visibility=visibility, is_basic=is_basic
            )
            design.save()
            self.designs[combination] = design

    def tearDown(self):
        for design in list(self.designs.values()):
            design.delete()

    def _assert_sorted_by_name(self, design_list):
        sorted_by_name = sorted(design_list, key=lambda design: design.name)
        self.assertEqual(design_list, sorted_by_name)

    def test_promoted_manager(self):
        promoted = list(Design.currently_promoted.all())
        for combination, design in list(self.designs.items()):
            (visibility, image, is_basic) = combination
            if all([image is not None, visibility == DC.FEATURED]):
                self.assertIn(design, promoted)
            else:
                self.assertNotIn(design, promoted)

        # How many listable patterns should there be?
        # * 1 valid option for image,
        # * 2 valid options for is_basic
        # * 1 valid option for visibility
        self.assertEqual(len(promoted), 2 * 1 * 1)

        self._assert_sorted_by_name(promoted)


class AdditionalElementsTestsBase(object):
    def test_common_validation(self):
        # validation-- control group
        good_input = [
            (3.5, AdditionalDesignElement.HEIGHT_IN_INCHES),
            (0.5, AdditionalDesignElement.HEIGHT_IN_INCHES),
            (3.0, AdditionalDesignElement.HEIGHT_IN_ROWS),
            (1, AdditionalDesignElement.HEIGHT_IN_ROWS),
            (1, AdditionalDesignElement.HEIGHT_NO_END),
        ]
        for hv, ht in good_input:
            el = self.factory(height_value=hv, height_type=ht)
            el.full_clean()

        # Now test validation:
        bad_input = [
            (0, AdditionalDesignElement.HEIGHT_IN_INCHES),
            (-1.5, AdditionalDesignElement.HEIGHT_IN_INCHES),
            (0, AdditionalDesignElement.HEIGHT_IN_ROWS),
            (2.5, AdditionalDesignElement.HEIGHT_IN_ROWS),
            (-1, AdditionalDesignElement.HEIGHT_IN_ROWS),
            (-1, AdditionalDesignElement.HEIGHT_NO_END),
        ]
        for hv, ht in bad_input:
            el = self.factory(height_value=hv, height_type=ht)
            with self.assertRaises(ValidationError):
                el.full_clean()

    def test_height_in_rows(self):
        gauge = GaugeFactory(rows=5)

        el = self.factory(
            height_value=1, height_type=AdditionalDesignElement.HEIGHT_IN_ROWS
        )
        self.assertEqual(el.height_in_rows(gauge), 1)

        el = self.factory(
            height_value=2, height_type=AdditionalDesignElement.HEIGHT_IN_INCHES
        )
        self.assertEqual(el.height_in_rows(gauge), 10)

        el = self.factory(
            height_value=3, height_type=AdditionalDesignElement.HEIGHT_IN_INCHES
        )
        self.assertEqual(
            el.height_in_rows(gauge), 16
        )  # Note the rounding to even number

        el = self.factory(
            height_value=0.1, height_type=AdditionalDesignElement.HEIGHT_IN_INCHES
        )
        self.assertEqual(el.height_in_rows(gauge), 2)  # Note the rounding up to 2

        el = self.factory(
            height_value=0.1, height_type=AdditionalDesignElement.HEIGHT_NO_END
        )
        self.assertEqual(el.height_in_rows(gauge), float("inf"))

    def test_interrupts_others(self):
        el = self.factory(overlap_behavior=AdditionalDesignElement.OVERLAP_INSTRUCTIONS)
        self.assertTrue(el.interrupts_others())

        el = self.factory(
            overlap_behavior=AdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL
        )
        self.assertFalse(el.interrupts_others())

        el = self.factory(overlap_behavior=AdditionalDesignElement.OVERLAP_START_ONLY)
        self.assertTrue(el.interrupts_others())

    def test_warn_if_interrupted(self):
        el = self.factory(overlap_behavior=AdditionalDesignElement.OVERLAP_INSTRUCTIONS)
        self.assertTrue(el.warn_if_interrupted())

        el = self.factory(
            overlap_behavior=AdditionalDesignElement.OVERLAP_PURELY_INFORMATIONAL
        )
        self.assertFalse(el.warn_if_interrupted())

        el = self.factory(overlap_behavior=AdditionalDesignElement.OVERLAP_START_ONLY)
        self.assertFalse(el.warn_if_interrupted())

    def test_get_template(self):
        name = "test_get_template template"
        content = "test_get_template content {{ foo }}"
        el = self.factory(name=name, template__content=content)
        tmpl = el.get_template()
        self.assertEqual(tmpl.name, name)
        output = tmpl.render(Context({"foo": "bar"}))
        goal_output = "test_get_template content bar"
        self.assertEqual(goal_output, output)
