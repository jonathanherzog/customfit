import logging
import unittest.mock as mock

from django.test import RequestFactory, TestCase
from django.urls import reverse

from customfit.userauth.factories import UserFactory

from .. import helpers as CDC
from ..factories import (
    CowlIndividualGarmentParametersFactory,
    CowlPatternSpecFactory,
    CowlRedoFactory,
)
from ..models import CowlIndividualGarmentParameters
from ..views.summary_and_approve_views import (
    CowlRedoApproveView,
    CowlSummaryAndApproveView,
    make_IPP_from_IPS,
    make_IPS_from_IGP,
    make_pattern_from_IPP,
)

#
#


# Get an instance of a logger
logger = logging.getLogger(__name__)


class _ApproveViewGetTestBase(object):

    # Expects sub-classes to implement:
    #
    # * setUp and tearDown, defining self.igp, self.user, and self.user2
    # * login()
    # * _make_igp(**kwargs), which takes keywords for a PatternSpec and returns
    #     a (saved) IGP
    # * _make_url(igp) returns the relevant approve URL
    # * _test_error_response(response), which verifies that the view has
    #     returned the right text in the event of an error

    def test_get(self):
        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertEqual(response.status_code, 200)

    def test_pattern_name(self):
        # sanity check:
        self.assertIsNotNone(self.igp.name)
        self.assertNotEqual(self.igp.name, "")

        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertContains(
            response,
            '<p class="text-indent margin-top-0">%s</p>' % self.igp.name,
            html=True,
        )

    def test_no_details(self):
        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertNotContains(
            response, "<p>You can see more detail below.</p>", html=True
        )
        self.assertNotContains(
            response,
            '<p class="small">please note: schematic pictures are generic images for dimension location reference only</p>',
            html=True,
        )


class _ApproveViewGetTestIndividualMixin(object):

    def setUp(self):
        super(_ApproveViewGetTestIndividualMixin, self).setUp()
        self.user = UserFactory()
        self.igp = self._make_igp()
        self.user2 = UserFactory()

    def _test_response(self, response):
        return self._test_individual_response(response)

    def test_only_owner_can_purchase_pattern(self):
        self.client.logout()
        self.client.force_login(self.user2)

        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertEqual(response.status_code, 403)


class _ApprovePatternSpecViewGetTestMixin(object):

    def _make_url(self, igp):
        return reverse("design_wizard:summary", args=(igp.id,))

    def test_measurements(self):
        # sanity check
        self.assertEqual(self.igp.height, 12)
        self.assertEqual(self.igp.circumference, 42)

        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertContains(
            response,
            '<p class="margin-bottom-5"><strong>height:</strong></p>',
            html=True,
        )
        self.assertContains(
            response,
            '<p class="text-indent margin-top-0">12&quot;/30.5 cm</p>',
            html=True,
        )

        self.assertContains(
            response,
            '<p class="margin-bottom-5"><strong>circumference:</strong></p>',
            html=True,
        )
        self.assertContains(
            response,
            '<p class="text-indent margin-top-0">42&quot;/106.5 cm</p>',
            html=True,
        )


class _ApproveRedoViewTestMixin(object):

    def _make_url(self, igp):
        return reverse("design_wizard:redo_approve", args=(igp.id,))

    def test_measurements(self):
        # sanity check
        self.assertEqual(self.igp.height, 16)
        self.assertEqual(self.igp.circumference, 60)

        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertContains(
            response,
            '<p class="margin-bottom-5"><strong>height:</strong></p>',
            html=True,
        )
        self.assertContains(
            response,
            '<p class="text-indent margin-top-0">16&quot;/40.5 cm</p>',
            html=True,
        )

        self.assertContains(
            response,
            '<p class="margin-bottom-5"><strong>circumference:</strong></p>',
            html=True,
        )
        self.assertContains(
            response,
            '<p class="text-indent margin-top-0">60&quot;/152.5 cm</p>',
            html=True,
        )

    def test_post(self):
        self.login()
        url = self._make_url(self.igp)
        response = self.client.post(url)
        goal_url = reverse(
            "patterns:individualpattern_detail_view", args=(self.igp.redo.pattern.pk,)
        )
        self.assertRedirects(response, goal_url)


class ApprovePatternSpecIndividualTests(
    _ApproveViewGetTestIndividualMixin,
    _ApprovePatternSpecViewGetTestMixin,
    _ApproveViewGetTestBase,
    TestCase,
):

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):
        kwargs["user"] = kwargs.get("user", self.user)
        pattern_spec = CowlPatternSpecFactory(**kwargs)
        igp = CowlIndividualGarmentParametersFactory(
            user=kwargs["user"], pattern_spec=pattern_spec
        )
        return igp

    def _get_GET_response(self, *args, **kwargs):
        # Let's separate these tests from problems in the underlying renderer
        with mock.patch.object(
            CowlSummaryAndApproveView, "_test_can_render_pattern", return_value=None
        ):
            resp = self.client.get(*args, **kwargs)
            return resp

    def test_header(self):
        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertContains(response, "<h2>SUMMARY: FINISHED DIMENSIONS</h2>")


class ApproveRedoIndividualTests(
    _ApproveViewGetTestIndividualMixin,
    _ApproveRedoViewTestMixin,
    _ApproveViewGetTestBase,
    TestCase,
):

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):

        pspec_kwargs = {}
        redo_kwargs = {}
        for k, v in list(kwargs.items()):
            if k == "height":
                redo_kwargs[k] = v
                pspec_kwargs[k] = (
                    CDC.COWL_HEIGHT_AVERAGE
                    if v != CDC.COWL_HEIGHT_AVERAGE
                    else CDC.COWL_HEIGHT_TALL
                )
            elif k == "circumference":
                redo_kwargs[k] = v
                pspec_kwargs[k] = (
                    CDC.COWL_CIRC_LARGE
                    if v != CDC.COWL_CIRC_LARGE
                    else CDC.COWL_CIRC_MEDIUM
                )
            else:
                pspec_kwargs[k] = v

        if "user" not in pspec_kwargs:
            pspec_kwargs["user"] = self.user
        pspec = CowlPatternSpecFactory(**pspec_kwargs)
        redo = CowlRedoFactory.from_original_pspec(pspec, **redo_kwargs)
        igp = CowlIndividualGarmentParameters.make_from_redo(redo.pattern.user, redo)
        igp.save()
        return igp

    def _get_GET_response(self, *args, **kwargs):
        # Let's separate these tests from problems in the underlying renderer
        with mock.patch.object(
            CowlRedoApproveView, "_test_can_render_pattern", return_value=None
        ):
            resp = self.client.get(*args, **kwargs)
            return resp

    def test_header(self):
        self.login()
        url = self._make_url(self.igp)
        response = self._get_GET_response(url)
        self.assertContains(
            response, "<h2>SUMMARY: RECOMPUTED DIMENSIONS</h2>", html=True
        )


#
# Where are the POST tests? They're covered in design_wizard tests.
#
