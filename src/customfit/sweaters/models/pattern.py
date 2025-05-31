import logging

from django.core.exceptions import ValidationError
from django.db import models

from customfit.bodies.models import Body
from customfit.patterns.models import GradedPattern, IndividualPattern, Redo

from ..helpers import sweater_design_choices as SDC
from ..renderers import (
    GradedSweaterPatternRendererWebFull,
    SweaterPatternCachePrefillRenderer,
    SweaterPatternRendererPdfAbridged,
    SweaterPatternRendererPdfFull,
    SweaterPatternRendererWebFull,
)
from .designs import (
    NecklineDepthField,
    NecklineDepthOrientationField,
    SleeveLengthField,
    TorsoLengthField,
)
from .patternspec import GarmentFitField

LOGGER = logging.getLogger(__name__)


class BaseSweaterPattern(models.Model):

    class Meta:
        abstract = True

    #
    # Ways to get associated objects.
    #

    def get_buttonband(self):
        assert self.has_button_band()
        return self.pieces.get_buttonband()

    def get_back_piece(self):
        return self.pieces.get_back_piece()

    def get_front_piece(self):
        return self.pieces.get_front_piece()

    def get_sleeve(self):
        return self.pieces.sleeve

    @property
    def gauge(self):
        return self.get_spec_source().gauge

    #
    # Garment type/property booleans.
    #

    def vee_neck(self):
        return self.pieces.vee_neck()

    def is_cardigan(self):
        return self.pieces.is_cardigan()

    def is_veeneck_cardigan(self):
        return self.pieces.is_veeneck_cardigan()

    def has_sleeves(self):
        return self.pieces.has_sleeves()

    def has_button_band(self):
        return self.pieces.has_button_band()

    def has_button_holes(self):
        return self.pieces.has_button_holes()

    #
    # Garment size & stitch count properties.
    #

    def total_neckline_pickup_stitches(self):
        return self.pieces.total_neckline_pickup_stitches()

    def total_finished_hip(self):
        return self.pieces.total_finished_hip()

    def total_finished_waist(self):
        return self.pieces.total_finished_waist()

    def total_finished_bust(self):
        return self.pieces.total_finished_bust()

    def neck_edging_height_in_rows(self):
        return self.pieces.neck_edging_height_in_rows()

    def cardigan_front_cast_on_stitches(self):
        return self.pieces.cardigan_front_cast_on_stitches()

    def total_armhole_stitches(self):
        return self.pieces.total_armhole_stitches()

    def pullover_front_cast_on_stitches(self):
        return self.pieces.pullover_front_cast_on_stitches()

    def back_cast_on_stitches(self):
        return self.pieces.back_cast_on_stitches()

    def total_cast_on_stitches(self):
        return self.pieces.total_cast_on_stitches()

    def seamless_sleeve_top_armcap(self):
        return self.pieces.seamless_sleeve_top_armcap()

    def seamless_sleeve_half_top_armcap(self):
        return self.pieces.seamless_sleeve_half_top_armcap()

    def seamless_sleeve_bottom(self):
        return self.pieces.seamless_sleeve_bottom()

    #
    # Images.
    #

    def get_back_schematic_image(self):
        return self.pieces.get_back_schematic_image()

    def get_sleeve_schematic_image(self):
        return self.pieces.get_sleeve_schematic_image()

    def get_front_schematic_image(self):
        return self.pieces.get_front_schematic_image()

    #
    # Misc.
    #

    @property
    def main_stitch(self):
        return self.get_spec_source().back_allover_stitch

    @property
    def fit_text(self):
        return self.pieces.fit_text()

    def bust_dart_params(self):
        return self.pieces.bust_dart_params()

    def get_schematic_display_context(self):
        """
        This generates the context needed to display schematic images. It's shared
        by design_wizard/views.py#SummaryAndApproveView and the pattern renderers.
        """
        back_piece = self.get_back_piece()
        front_piece = self.get_front_piece()
        sleeve = self.get_sleeve()
        context = {}

        context["back_schematic_image"] = self.get_back_schematic_image()
        context["front_schematic_image"] = self.get_front_schematic_image()
        context["sleeve_schematic_image"] = self.get_sleeve_schematic_image()

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~ Back dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~~

        # We use a list (of tuples) for this and other dimensions because we want
        # to present measurements in an order which 1) is consistent in different
        # parts of the site, and 2) matches the flow of measurements down the
        # schematic image. This will make it easier for users to skim and
        # understand schematic information.
        back_dimensions = []
        if back_piece.is_hourglass:
            back_dimensions.append(
                ("shoulder width", back_piece.actual_shoulder_stitch_width)
            )
            back_dimensions.append(("neck width", back_piece.actual_neck_opening_width))
            back_dimensions.append(("back bust width", back_piece.actual_bust))
            back_dimensions.append(("back waist width", back_piece.actual_waist))
            back_dimensions.append(("back hip width", back_piece.actual_hip))
            back_dimensions.append(("armhole depth", back_piece.actual_armhole_depth))
            back_dimensions.append(
                ("waist to armhole", back_piece.actual_waist_to_armhole)
            )
            back_dimensions.append(("hem to waist", back_piece.actual_hem_to_waist))
        elif back_piece.is_straight:
            back_dimensions.append(
                ("shoulder width", back_piece.actual_shoulder_stitch_width)
            )
            back_dimensions.append(("neck width", back_piece.actual_neck_opening_width))
            # Bust, waist, and hip widths are all the same for straight pieces,
            # so it doesn't matter which we use.
            back_dimensions.append(("back width", back_piece.actual_bust))
            back_dimensions.append(("armhole depth", back_piece.actual_armhole_depth))
            back_dimensions.append(("hem to armhole", back_piece.actual_hem_to_armhole))
        else:
            assert back_piece.is_aline or back_piece.is_tapered
            back_dimensions.append(
                ("shoulder width", back_piece.actual_shoulder_stitch_width)
            )
            back_dimensions.append(("neck width", back_piece.actual_neck_opening_width))
            back_dimensions.append(("back bust width", back_piece.actual_bust))
            back_dimensions.append(("back hip width", back_piece.actual_hip))
            back_dimensions.append(("armhole depth", back_piece.actual_armhole_depth))
            back_dimensions.append(("hem to armhole", back_piece.actual_hem_to_armhole))

        context["back_dimensions"] = back_dimensions

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~ Front dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~
        front_dimensions = []
        front_dimensions.append(("neck depth", front_piece.neckline.total_depth()))

        if front_piece.is_hourglass:
            front_dimensions.append(("front bust width", front_piece.actual_bust))
            front_dimensions.append(("front waist width", front_piece.actual_waist))
            front_dimensions.append(("front hip width", front_piece.actual_hip))
            front_dimensions.append(
                ("waist to armhole", front_piece.actual_waist_to_armhole)
            )
            front_dimensions.append(("hem to waist", front_piece.actual_hem_to_waist))

        elif front_piece.is_straight:
            front_dimensions.append(("front width", front_piece.actual_bust))
        else:
            assert front_piece.is_tapered or front_piece.is_aline
            front_dimensions.append(("front bust width", front_piece.actual_bust))
            front_dimensions.append(("front hip width", front_piece.actual_hip))
            front_dimensions.append(("hem to waist", front_piece.actual_hem_to_waist))

        context["front_dimensions"] = front_dimensions

        # ~~~~~~~~~~~~~~~~~~~~~~~~~ Sleeve dimensions ~~~~~~~~~~~~~~~~~~~~~~~~~
        if sleeve:
            sleeve_dimensions = []
            sleeve_dimensions.append(("bicep width", sleeve.actual_bicep))
            sleeve_dimensions.append(("cast on width", sleeve.actual_wrist))
            sleeve_dimensions.append(("length to armhole", sleeve.actual_wrist_to_cap))
            sleeve_dimensions.append(("cap height", sleeve.actual_armcap_heights))

            context["sleeve_dimensions"] = sleeve_dimensions

        return context


class SweaterPattern(BaseSweaterPattern, IndividualPattern):

    @classmethod
    def make_from_individual_pattern_pieces(cls, user, ipp):
        parameters = {"user": user, "name": ipp.schematic.name, "pieces": ipp}

        instance = cls(**parameters)
        return instance

    @property
    def body(self):
        return self.pieces.schematic.individual_garment_parameters.body

    abridged_pdf_renderer_class = SweaterPatternRendererPdfAbridged
    full_pdf_renderer_class = SweaterPatternRendererPdfFull
    web_renderer_class = SweaterPatternRendererWebFull

    def get_back_pieces(self):
        return [self.pieces.get_back_piece()]

    def get_front_pieces(self):
        return [self.pieces.get_front_piece()]

    def get_sleeves(self):
        return [self.pieces.sleeve]


class GradedSweaterPattern(BaseSweaterPattern, GradedPattern):

    @classmethod
    def make_from_graded_pattern_pieces(cls, gpp):
        parameters = {"name": gpp.schematic.name, "pieces": gpp}

        instance = cls(**parameters)
        return instance

    abridged_pdf_renderer_class = None
    full_pdf_renderer_class = None
    web_renderer_class = GradedSweaterPatternRendererWebFull

    def grade_list_for_pattern_summary(self):
        return self.pieces.grade_list_for_pattern_summary()

    def get_back_pieces(self):
        return self.pieces.get_back_pieces()

    def get_front_pieces(self):
        return self.pieces.get_front_pieces()

    def get_sleeves(self):
        return self.pieces.sleeves


class SweaterRedo(Redo):

    body = models.ForeignKey(Body, on_delete=models.CASCADE)
    garment_fit = GarmentFitField()
    torso_length = TorsoLengthField()
    sleeve_length = SleeveLengthField()
    neckline_depth = NecklineDepthField()
    neckline_depth_orientation = NecklineDepthOrientationField()

    def clean(self):
        super(Redo, self).clean()

        if self.has_sleeves():
            if self.sleeve_length is None:
                raise ValidationError(
                    {"sleeve_length": "Please select a sleeve length"}
                )
        else:
            if self.sleeve_length is not None:
                raise ValidationError({"sleeve_length": "Please leave blank for vests"})

        if self.is_hourglass or self.is_half_hourglass:
            if self.garment_fit not in SDC.FIT_HOURGLASS:
                raise ValidationError(
                    "Hourglass/half-hourglass garments need hourglass fit"
                )
        else:
            if self.garment_fit in SDC.FIT_HOURGLASS:
                raise ValidationError(
                    "Non-hourglass/half-hourglass garments cannot use hourglass fits"
                )

    def get_igp_class(self):
        from .garment_parameters import SweaterIndividualGarmentParameters

        return SweaterIndividualGarmentParameters

    # Methods copied from either DesignBase or PatternSpec so as to shadow the
    # same-named methods from the original PatternSpec. See __getattr__ below.

    def fit_patterntext(self):
        # Note: get_garment_fit_display() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_garment_fit_display()

    def neckline_depth_orientation_patterntext(self):
        # Note: get_neckline_depth_orientation_display() created
        # automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_neckline_depth_orientation_display()

    def torso_length_patterntext(self):
        # Note: get_torso_length_isplay() created automatically by Django
        # See http://dustindavis.me/django-tip-get_field_display.html
        return self.get_torso_length_display()

    def sleeve_length_patterntext(self):
        if not self.has_sleeves():
            return None
        else:
            return self.get_sleeve_length_display()

    def sleeve_length_patterntext_short_form(self):
        if not self.has_sleeves():
            return None
        else:
            return SDC.SLEEVE_LENGTH_SHORT_FORMS[self.sleeve_length]
