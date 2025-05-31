import os.path
import urllib.parse
from io import BytesIO
from unittest import skip

from django.core.files.storage import default_storage
from django.test import LiveServerTestCase, TestCase, tag
from django.test.client import Client
from django.urls import reverse
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import (
    invisibility_of_element_located,
    visibility_of_element_located,
)
from selenium.webdriver.support.ui import WebDriverWait

from customfit.bodies.factories import BodyFactory
from customfit.bodies.models import Body
from customfit.design_wizard.models import Transaction
from customfit.patterns.models import IndividualPattern
from customfit.swatches.factories import SwatchFactory
from customfit.swatches.models import Swatch
from customfit.test_garment.factories import TestApprovedIndividualPatternFactory
from customfit.userauth.factories import UserFactory

from .factories import (
    create_body_picture,
    create_individual_pattern_picture,
    create_swatch_picture,
)
from .models import get_image_path


def create_transaction(pattern, user):
    # patterns need associated transactions to be approved
    transaction = Transaction()
    transaction.pattern = pattern
    transaction.user = user
    transaction.amount = 0.00
    transaction.approved = True
    transaction.save()
    return transaction


"""
Picture uploading tests.
"""


class PictureUploadCase(TestCase):
    def setUp(self):
        super(PictureUploadCase, self).setUp()
        self.client = Client()
        self.user = UserFactory()
        self.user2 = UserFactory()
        self.body2 = BodyFactory(user=self.user2)

    def tearDown(self):
        super(PictureUploadCase, self).tearDown()
        self.user.delete()
        self.user2.delete()

    def login(self):
        """
        Logs the user in
        """
        self.client.force_login(self.user)


class BodyPictureUploadCase(PictureUploadCase):
    def setUp(self):
        super(BodyPictureUploadCase, self).setUp()
        self.body = BodyFactory(user=self.user)
        self.body2 = BodyFactory(user=self.user2)

    def test_view_permissions(self):
        """
        Users can see the upload view for body pics iff they own that body.
        """
        self.login()
        response = self.client.get(
            reverse("uploads:body_picture_upload", args=(self.body2.id,))
        )
        self.assertEqual(
            response.status_code,
            403,
            "User trying to view someone else's body gets status code %s instead of 403"
            % response.status_code,
        )
        response = self.client.get(
            reverse("uploads:body_picture_upload", args=(self.body.id,))
        )
        self.assertEqual(
            response.status_code,
            200,
            "User trying to view own body gets status code %s instead of 200"
            % response.status_code,
        )

    def test_file_deletion(self):
        """
        Deleting a BodyPicture removes its associated imagefile from the storage,
        but does NOT remove the associated body.
        """
        bp = create_body_picture(self.body)
        name = bp.picture.name
        bp.delete()
        self.assertFalse(
            default_storage.exists(name),
            "Deleting a BodyPicture did not delete its image file",
        )
        self.assertTrue(
            Body.objects.get(id=self.body.id),
            "Deleting a BodyPicture also deleted its associated Body",
        )


class SwatchPictureUploadCase(PictureUploadCase):
    def setUp(self):
        super(SwatchPictureUploadCase, self).setUp()
        self.swatch = SwatchFactory(user=self.user)
        self.swatch2 = SwatchFactory(user=self.user2)

    def test_view_permissions(self):
        """
        Users can see the upload view for swatch pics iff they own that swatch.
        """
        self.login()
        response = self.client.get(
            reverse("uploads:swatch_picture_upload", args=(self.swatch2.id,))
        )
        self.assertEqual(
            response.status_code,
            403,
            "User trying to view someone else's swatch gets status code %s instead of 403"
            % response.status_code,
        )
        response = self.client.get(
            reverse("uploads:swatch_picture_upload", args=(self.swatch.id,))
        )
        self.assertEqual(
            response.status_code,
            200,
            "User trying to view own swatch gets status code %s instead of 200"
            % response.status_code,
        )

    def test_file_deletion(self):
        """
        Deleting a SwatchPicture removes its associated imagefile from the storage,
        but does NOT remove the associated swatch.
        """
        sp = create_swatch_picture(self.swatch)
        name = sp.picture.name
        sp.delete()
        self.assertFalse(
            default_storage.exists(name),
            "Deleting a SwatchPicture did not delete its image file",
        )
        self.assertTrue(
            Swatch.objects.get(id=self.swatch.id),
            "Deleting a SwatchPicture also deleted its associated Swatch",
        )

    def test_post(self):
        yarn_path = os.path.join(os.path.dirname(__file__), "test_assets/yarn.jpg")
        url = reverse("uploads:swatch_picture_upload", args=(self.swatch.id,))
        with open(yarn_path, mode="rb") as yarn_f:
            self.login()
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)  # sanity_check
            response = self.client.post(url, {"picture": yarn_f})
            self.assertEqual(response.status_code, 302)


class IndividualPatternPictureUploadCase(PictureUploadCase):
    def setUp(self):
        super(IndividualPatternPictureUploadCase, self).setUp()
        self.pattern = TestApprovedIndividualPatternFactory.for_user(self.user)
        self.pattern2 = TestApprovedIndividualPatternFactory.for_user(self.user2)

        self.transaction = self.pattern.transactions.get()
        self.transaction2 = self.pattern2.transactions.get()

    def test_view_permissions(self):
        """
        Users can see upload view for pattern pics iff they own that pattern.
        """
        self.login()
        response = self.client.get(
            reverse(
                "uploads:individual_pattern_picture_upload", args=(self.pattern2.id,)
            )
        )
        self.assertEqual(
            response.status_code,
            403,
            "User trying to view someone else's pattern gets status code %s instead of 403"
            % response.status_code,
        )
        response = self.client.get(
            reverse(
                "uploads:individual_pattern_picture_upload", args=(self.pattern.id,)
            )
        )
        self.assertEqual(
            response.status_code,
            200,
            "User trying to view own pattern gets status code %s instead of 200"
            % response.status_code,
        )

    def test_file_deletion(self):
        """
        Deleting a IndividualPatternPicture removes its associated imagefile from
        the storage, but does NOT remove the associated pattern.
        """
        ip = create_individual_pattern_picture(self.pattern)
        name = ip.picture.name
        ip.delete()
        self.assertFalse(
            default_storage.exists(name),
            "Deleting an IndividualPatternPicture did not delete its image file",
        )
        self.assertTrue(
            IndividualPattern.even_unapproved.get(id=self.pattern.id),
            "Deleting a IndividualPatternPicture also deleted its associated IndividualPattern",
        )


class GetImagePathTests(PictureUploadCase):

    def setUp(self):
        super(GetImagePathTests, self).setUp()
        self.body = BodyFactory(user=self.user)
        self.bp = create_body_picture(self.body)

    def test_get_image_path_test_just_characters(self):
        # stuff
        self.user.username = "alice"
        self.user.save()
        path_str = get_image_path(self.bp, "filename.jpg")
        # use python library to separate path_str in to list of directories (os.path)
        dir_list = path_str.split("/")
        self.assertEqual(dir_list[0], "alice")

    def test_get_image_path_test_at_sign(self):

        self.user.username = "user@example.com"
        self.user.save()
        path_str = get_image_path(self.bp, "filename.jpg")
        # use python library to separate path_str in to list of directories (os.path)
        dir_list = path_str.split("/")
        self.assertEqual(dir_list[0], "user@example.com")
