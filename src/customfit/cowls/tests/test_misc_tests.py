from django.test import TestCase
from django.urls import reverse

from customfit.userauth.factories import UserFactory

from ..factories import CowlDesignFactory


class TestStitchListView(TestCase):

    def test_stitches_list_view(self):

        _ = CowlDesignFactory()
        url = reverse("stitch_models:stitch_list_view")
        user = UserFactory()
        self.client.force_login(user)
        self.client.get(url)
