import logging
from unittest import skip

from django.test import RequestFactory, TestCase
from django.test.client import Client
from django.urls import reverse

from customfit.design_wizard.exceptions import OwnershipInconsistency
from customfit.design_wizard.tests.helpers import _fix_length_formatting
from customfit.stitches.tests import StitchFactory
from customfit.userauth.factories import UserFactory

from ...factories import (
    SweaterIndividualGarmentParametersFactory,
    SweaterPatternSpecFactory,
    SweaterRedoFactory,
)
from ...helpers import sweater_design_choices as SDC
from ...models import SweaterIndividualGarmentParameters
from ...views.helpers import (
    _make_IPP_from_IPS,
    _make_IPS_from_IGP,
    _make_pattern_from_IPP,
)

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
    # * _make_pattern(igp) which turns the IGP into a (maybe saved) pattern
    # * _test_error_response(response), which verifies that the view has
    #     returned the right text in the event of an error

    def test_garment_dimensions_in_page(self):
        """
        Make sure the users see the expected set of garment dimensions.
        """

        # First, two helper functions

        # a helper function:

        def get_fields(p):
            back_piece = p.get_back_piece()
            front_piece = p.get_front_piece()
            sleeve = p.get_sleeve()

            back_fields = [
                ("shoulder width", back_piece.actual_shoulder_stitch_width),
                ("neck width", back_piece.actual_neck_opening_width),
                ("back bust width", back_piece.actual_bust),
                ("back waist width", back_piece.actual_waist),
                ("back hip width", back_piece.actual_hip),
                ("armhole depth", back_piece.actual_armhole_depth),
                ("waist to armhole", back_piece.actual_waist_to_armhole),
                ("hem to waist", back_piece.actual_hem_to_waist),
            ]

            front_fields = [
                ("neck depth", front_piece.neckline.total_depth()),
                ("front bust width", front_piece.actual_bust),
                ("front waist width", front_piece.actual_waist),
                ("front hip width", front_piece.actual_hip),
                ("waist to armhole", front_piece.actual_waist_to_armhole),
                ("hem to waist", front_piece.actual_hem_to_waist),
            ]

            if sleeve:
                sleeve_fields = [
                    ("bicep width", sleeve.actual_bicep),
                    ("cast on width", sleeve.actual_wrist),
                    ("length to armhole ", sleeve.actual_wrist_to_cap),
                    ("cap height", sleeve.actual_armcap_heights),
                ]
            else:
                sleeve_fields = [
                    ("bicep width", None),
                    ("cast on width", None),
                    ("length to armhole ", None),
                    ("cap height", None),
                ]

            return [front_fields, back_fields, sleeve_fields]

        # And another helper function
        def test_fields(field_lists, response):
            for field_list in field_lists:
                for name, value in field_list:
                    if value is not None:
                        length_str = _fix_length_formatting(value)
                        goal_html = """
                                <div class="row">
                                <div class="col-xs-6 col-sm-6 col-lg-5">
                                    %s
                                </div>
                                <div class="col-xs-6 col-sm-6 col-lg-5">
                                    %s
                                </div>
                                </div>""" % (
                            name,
                            length_str,
                        )
                        self.assertContains(
                            response, goal_html, msg_prefix=name, html=True
                        )
                    else:
                        non_goal_html = (
                            """
                            <div class="col-xs-6 col-sm-6 col-lg-5">
                                    %s
                            </div>"""
                            % name
                        )

                        self.assertNotContains(
                            response, non_goal_html, msg_prefix=name, html=True
                        )

        # Now, the default design (has sleeves).
        self.login()
        url = self._make_url(self.igp)
        response = self.client.get(url)

        pattern = self._make_pattern(self.igp)
        field_lists = get_fields(pattern)
        test_fields(field_lists, response)

        # Now check sleeveless garments.
        data = {
            "name": "Default individual design",
            "garment_type": SDC.PULLOVER_VEST,
            "neckline_style": SDC.NECK_VEE,
            "garment_fit": SDC.FIT_HOURGLASS_AVERAGE,
            "torso_length": SDC.MED_HIP_LENGTH,
            "neckline_width": SDC.NECK_AVERAGE,
            "neckline_depth": 6,
            "neckline_depth_orientation": SDC.BELOW_SHOULDERS,
            "hip_edging_height": 1.5,
            "hip_edging_stitch": StitchFactory(name="1x1 Ribbing"),
            "neck_edging_stitch": StitchFactory(name="1x1 Ribbing"),
            "neck_edging_height": 1,
            "sleeve_length": None,
            "sleeve_edging_height": None,
            "sleeve_edging_stitch": None,
            "armhole_edging_stitch": StitchFactory(name="1x1 Ribbing"),
            "armhole_edging_height": 1,
            "button_band_edging_stitch": None,
            "button_band_edging_height": None,
            "button_band_allowance": None,
            "number_of_buttons": None,
            "back_allover_stitch": StitchFactory(name="Stockinette"),
            "front_allover_stitch": StitchFactory(name="Other Stitch"),
            "sleeve_allover_stitch": StitchFactory(name="Sugar Cube Stitch"),
        }
        vest_igp = self._make_igp(**data)

        url = self._make_url(vest_igp)
        response = self.client.get(url)
        pattern = self._make_pattern(vest_igp)
        field_lists = get_fields(pattern)
        test_fields(field_lists, response)

    def test_pullover_sleeved_designs(self):

        self.login()
        user = self.user
        silhouette_fit_combos = [
            (SDC.SILHOUETTE_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
            (SDC.SILHOUETTE_STRAIGHT, SDC.FIT_WOMENS_AVERAGE),
            (SDC.SILHOUETTE_HALF_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
        ]
        for silhouette, fit in silhouette_fit_combos:
            this_run = {
                "user": user,
                "silhouette": silhouette,
                "garment_fit": fit,
                "garment_type": SDC.PULLOVER_SLEEVED,
            }

            igp = self._make_igp(**this_run)
            ps = igp.get_spec_source()
            url = self._make_url(igp)
            response = self.client.get(url)
            self.assertContains(response, ps.name)

    def test_pullover_vest_designs(self):

        self.login()
        user = self.user
        silhouette_fit_combos = [
            (SDC.SILHOUETTE_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
            (SDC.SILHOUETTE_STRAIGHT, SDC.FIT_WOMENS_AVERAGE),
            (SDC.SILHOUETTE_HALF_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
        ]
        for silhouette, fit in silhouette_fit_combos:
            this_run = {
                "user": user,
                "silhouette": silhouette,
                "garment_fit": fit,
                "garment_type": SDC.PULLOVER_VEST,
                "armhole_edging_height": 1,
                "armhole_edging_stitch": StitchFactory(name="1x1 Ribbing"),
            }

            igp = self._make_igp(**this_run)
            ps = igp.get_spec_source()
            url = self._make_url(igp)
            response = self.client.get(url)
            self.assertContains(response, ps.name)

    def test_cardigan_sleeved_designs(self):

        self.login()
        user = self.user
        silhouette_fit_combos = [
            (SDC.SILHOUETTE_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
            (SDC.SILHOUETTE_STRAIGHT, SDC.FIT_WOMENS_AVERAGE),
            (SDC.SILHOUETTE_HALF_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
        ]
        for silhouette, fit in silhouette_fit_combos:
            this_run = {
                "user": user,
                "silhouette": silhouette,
                "button_band_edging_height": 1,
                "button_band_edging_stitch": StitchFactory(name="1x1 Ribbing"),
                "button_band_allowance": 1,
                "number_of_buttons": 5,
                "garment_fit": fit,
                "garment_type": SDC.CARDIGAN_SLEEVED,
            }

            igp = self._make_igp(**this_run)
            ps = igp.get_spec_source()
            url = self._make_url(igp)
            response = self.client.get(url)
            self.assertContains(response, ps.name)

    def test_cardigan_vest_designs(self):

        self.login()
        user = self.user
        silhouette_fit_combos = [
            (SDC.SILHOUETTE_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
            (SDC.SILHOUETTE_STRAIGHT, SDC.FIT_WOMENS_AVERAGE),
            (SDC.SILHOUETTE_HALF_HOURGLASS, SDC.FIT_HOURGLASS_AVERAGE),
        ]
        for silhouette, fit in silhouette_fit_combos:
            this_run = {
                "user": user,
                "silhouette": silhouette,
                "button_band_edging_height": 1,
                "button_band_edging_stitch": StitchFactory(name="1x1 Ribbing"),
                "button_band_allowance": 1,
                "number_of_buttons": 5,
                "garment_fit": fit,
                "garment_type": SDC.CARDIGAN_VEST,
                "armhole_edging_height": 1,
                "armhole_edging_stitch": StitchFactory(name="1x1 Ribbing"),
            }

            igp = self._make_igp(**this_run)
            ps = igp.get_spec_source()
            url = self._make_url(igp)
            response = self.client.get(url)
            self.assertContains(response, ps.name)

    # def test_error_igp_wrong_owner(self):
    #     self.igp.user = self.user2
    #     self.igp.save()
    #     self.login()
    #     url = self._make_url(self.igp)
    #     response = self.client.get(url)
    #     self.assertContains(response, "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)
    #

    def test_error_igp_body_has_wrong_owner(self):
        self.igp.body.user = self.user2
        self.igp.body.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            url = self._make_url(self.igp)
            self.client.get(url)

    # def test_error_igp_swatch_has_wrong_owner(self):
    #     self.igp.swatch.user = self.user2
    #     self.igp.swatch.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         url = self._make_url(self.igp)
    #         self.client.get(url)


class _ApproveViewGetTestIndividualMixin(object):

    def setUp(self):
        super(_ApproveViewGetTestIndividualMixin, self).setUp()
        self.user = UserFactory()
        self.igp = self._make_igp()
        self.user2 = UserFactory()

    def _test_response(self, response):
        return self._test_individual_response(response)


class _ApprovePatternSpecViewGetTestMixin(object):

    def _make_url(self, igp):
        return reverse("design_wizard:summary", args=(igp.id,))

    def _make_pattern(self, igp):
        user = igp.get_spec_source().user
        ips = _make_IPS_from_IGP(user, igp)
        ipp = _make_IPP_from_IPS(ips)
        pattern = _make_pattern_from_IPP(user, ipp)
        return pattern


class _ApproveRedoViewGetTestMixin(object):

    def _make_url(self, igp):
        return reverse("design_wizard:redo_approve", args=(igp.id,))

    def _make_pattern(self, igp):
        user = igp.get_spec_source().user
        ips = _make_IPS_from_IGP(user, igp)
        ipp = _make_IPP_from_IPS(ips)
        pattern = igp.get_spec_source().pattern
        pattern.update_with_new_pieces(ipp)
        return pattern


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
        pattern_spec = SweaterPatternSpecFactory(**kwargs)
        igp = SweaterIndividualGarmentParametersFactory(
            user=kwargs["user"], pattern_spec=pattern_spec
        )
        return igp


class ApproveRedoIndividualTests(
    _ApproveViewGetTestIndividualMixin,
    _ApproveRedoViewGetTestMixin,
    _ApproveViewGetTestBase,
    TestCase,
):

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):

        silhouette = kwargs.get("silhouette", None)
        pspec_kwargs = {}
        redo_kwargs = {}
        for k, v in list(kwargs.items()):
            if k == "garment_fit":
                redo_kwargs["garment_fit"] = v
                if silhouette in [
                    SDC.SILHOUETTE_HOURGLASS,
                    SDC.SILHOUETTE_HALF_HOURGLASS,
                    None,
                ]:
                    pspec_kwargs["garment_fit"] = (
                        SDC.FIT_HOURGLASS_AVERAGE
                        if v != SDC.FIT_HOURGLASS_AVERAGE
                        else SDC.FIT_HOURGLASS_RELAXED
                    )
                else:
                    pspec_kwargs["garment_fit"] = (
                        SDC.FIT_WOMENS_AVERAGE
                        if v != SDC.FIT_WOMENS_AVERAGE
                        else SDC.FIT_WOMENS_RELAXED
                    )

            elif k == "torso_length":
                redo_kwargs["torso_length"] = v
                pspec_kwargs["torso_length"] = (
                    SDC.MED_HIP_LENGTH
                    if v != SDC.MED_HIP_LENGTH
                    else SDC.LOW_HIP_LENGTH
                )
            elif k == "sleeve_length":
                redo_kwargs["sleeve_length"] = v
                pspec_kwargs["sleeve_length"] = (
                    SDC.SLEEVE_FULL if v != SDC.SLEEVE_FULL else SDC.SLEEVE_THREEQUARTER
                )
            elif k == "neckline_depth":
                redo_kwargs["neckline_depth"] = v
                pspec_kwargs["neckline_depth"] = 6 if v != 6 else 5
            elif k == "neckline_depth_orientation":
                redo_kwargs["neckline_depth_orientation"] = v
                pspec_kwargs["neckline_depth_orientation"] = (
                    SDC.BELOW_SHOULDERS
                    if v != SDC.BELOW_SHOULDERS
                    else SDC.BELOW_ARMPIT
                )
            else:
                pspec_kwargs[k] = v

        if "user" not in pspec_kwargs:
            pspec_kwargs["user"] = self.user
        pspec = SweaterPatternSpecFactory(**pspec_kwargs)
        redo = SweaterRedoFactory.from_original_pspec(pspec, **redo_kwargs)
        igp = SweaterIndividualGarmentParameters.make_from_redo(redo.pattern.user, redo)
        igp.save()
        return igp

    # def test_header(self):
    #     self.login()
    #     url = self._make_url(self.igp)
    #     response = self.client.get(url)
    #
    #     self.assertContains(response, '<h2>SUMMARY: RECOMPUTED DIMENSIONS</h2>', html=True)
    #


class _ApproveViewPostTestBase(object):

    # Expects sub-classes to implement:
    #
    # * setUp and tearDown, defining self.igp, self.user, and self.user2
    # * login()
    # * _make_url(igp) returns the relevant approve URL

    # ANY OF THESE?
    # * _make_igp(**kwargs), which takes keywords for a PatternSpec and returns
    #     a (saved) IGP
    # * _make_pattern(igp) which turns the IGP into a (maybe saved) pattern
    # * _test_error_response(response), which verifies that the view has
    #     returned the right text in the event of an error

    # def test_error_igp_wrong_owner(self):
    #     self.igp.user = self.user2
    #     self.igp.save()
    #     self.login()
    #     url = self._make_url(self.igp)
    #     response = self.client.post(url)
    #     self.assertContains(response, "<p>Sorry, but you don't have permission to view this content.</p>",
    #                         status_code = 403, html=True)

    def test_error_igp_body_has_wrong_owner(self):
        self.igp.body.user = self.user2
        self.igp.body.save()
        self.login()
        with self.assertRaises(OwnershipInconsistency):
            url = self._make_url(self.igp)
            self.client.post(url)

    # def test_error_igp_swatch_has_wrong_owner(self):
    #     self.igp.swatch.user = self.user2
    #     self.igp.swatch.save()
    #     self.login()
    #     with self.assertRaises(OwnershipInconsistency):
    #         url = self._make_url(self.igp)
    #         self.client.post(url)

    def test_myo_pattern_bug_regression(self):
        spec_source = self.igp.get_spec_source()
        spec_source.design_origin = None
        spec_source.save()
        self.login()
        url = self._make_url(self.igp)
        self.client.post(url)


class _ApproveViewPostTestIndividualMixin(object):

    def setUp(self):
        super(_ApproveViewPostTestIndividualMixin, self).setUp()
        self.user = UserFactory()
        self.igp = self._make_igp()
        self.user2 = UserFactory()


class _ApproveViewPostPatternSpecTestMixin(object):

    def _make_url(self, igp):
        return reverse("design_wizard:summary", args=(igp.id,))


class _ApproveViewPostRedoTestMixin(object):

    def _make_post_data(self):
        post_data = {}
        return post_data

    def _make_url(self, igp):
        return reverse("design_wizard:redo_approve", args=(igp.id,))


class ApproveViewPostPatternSpecIndividualTests(
    _ApproveViewPostTestIndividualMixin,
    _ApproveViewPostPatternSpecTestMixin,
    _ApproveViewPostTestBase,
    TestCase,
):

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):
        new_kwargs = {"pattern_spec__" + k: v for (k, v) in list(kwargs.items())}
        igp = SweaterIndividualGarmentParametersFactory(user=self.user, **new_kwargs)
        return igp


class ApproveViewPostRedoIndividualTests(
    _ApproveViewPostTestIndividualMixin,
    _ApproveViewPostRedoTestMixin,
    _ApproveViewPostTestBase,
    TestCase,
):

    def login(self):
        self.client.force_login(self.user)

    def _make_igp(self, **kwargs):

        silhouette = kwargs.get("silhouette", None)
        pspec_kwargs = {}
        redo_kwargs = {}
        for k, v in list(kwargs.items()):
            if k == "garment_fit":
                redo_kwargs["garment_fit"] = v
                if silhouette in [
                    SDC.SILHOUETTE_HOURGLASS,
                    SDC.SILHOUETTE_HALF_HOURGLASS,
                    None,
                ]:
                    pspec_kwargs["garment_fit"] = (
                        SDC.FIT_HOURGLASS_AVERAGE
                        if v != SDC.FIT_HOURGLASS_AVERAGE
                        else SDC.FIT_HOURGLASS_RELAXED
                    )
                else:
                    pspec_kwargs["garment_fit"] = (
                        SDC.FIT_WOMENS_AVERAGE
                        if v != SDC.FIT_WOMENS_AVERAGE
                        else SDC.FIT_WOMENS_RELAXED
                    )

            elif k == "torso_length":
                redo_kwargs["torso_length"] = v
                pspec_kwargs["torso_length"] = (
                    SDC.MED_HIP_LENGTH
                    if v != SDC.MED_HIP_LENGTH
                    else SDC.LOW_HIP_LENGTH
                )
            elif k == "sleeve_length":
                redo_kwargs["sleeve_length"] = v
                pspec_kwargs["sleeve_length"] = (
                    SDC.SLEEVE_FULL if v != SDC.SLEEVE_FULL else SDC.SLEEVE_THREEQUARTER
                )
            elif k == "neckline_depth":
                redo_kwargs["neckline_depth"] = v
                pspec_kwargs["neckline_depth"] = 6 if v != 6 else 5
            elif k == "neckline_depth_orientation":
                redo_kwargs["neckline_depth_orientation"] = v
                pspec_kwargs["neckline_depth_orientation"] = (
                    SDC.BELOW_SHOULDERS
                    if v != SDC.BELOW_SHOULDERS
                    else SDC.BELOW_ARMPIT
                )
            else:
                pspec_kwargs[k] = v

        if "user" not in pspec_kwargs:
            pspec_kwargs["user"] = self.user
        pspec = SweaterPatternSpecFactory(**pspec_kwargs)
        redo = SweaterRedoFactory.from_original_pspec(pspec, **redo_kwargs)
        igp = SweaterIndividualGarmentParameters.make_from_redo(redo.pattern.user, redo)
        igp.save()
        return igp
