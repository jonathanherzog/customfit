import logging

from django.db import models

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    ROUND_UP,
    CompoundResult,
    is_even,
    round,
)
from customfit.patterns.renderers import PieceList
from customfit.pieces.models import AreaMixin, GradedPatternPieces, PatternPieces

from ...helpers import sweater_design_choices as SDC
from ...helpers.magic_constants import (
    BUST_DART_INSTRUCTION_HEIGHTS,
    BUST_DART_MARKER_ALLOWANCE,
)
from ...helpers.schematic_images import get_front_schematic_url
from ...helpers.secret_sauce import ease_tolerances as _ease_tolerances
from ...helpers.secret_sauce import rounding_directions as _rounding_directions
from ..schematics import (
    GradedCardiganSleevedSchematic,
    GradedCardiganVestSchematic,
    GradedSweaterFrontSchematic,
    GradedVestFrontSchematic,
)
from .back_pieces import GradedSweaterBack, GradedVestBack, SweaterBack, VestBack
from .front_pieces import (
    CardiganSleeved,
    CardiganVest,
    GradedCardiganSleeved,
    GradedCardiganVest,
    GradedSweaterFront,
    GradedVestFront,
    SweaterFront,
    VestFront,
)
from .sleeves import GradedSleeve, Sleeve

LOGGER = logging.getLogger(__name__)


class BaseSweaterPatternPieces(object):
    # subclasses should implement
    #
    # * get_spec_source

    def vee_neck(self):
        return self.get_spec_source().is_veeneck()

    def is_cardigan(self):
        return self.get_spec_source().is_cardigan()

    def is_veeneck_cardigan(self):
        return all([self.vee_neck(), self.is_cardigan()])

    def has_sleeves(self):
        return self.get_spec_source().has_sleeves()

    def has_button_band(self):
        if self.is_cardigan():
            pattern_spec = self.get_spec_source()
            if pattern_spec.button_band_edging_height is not None:
                if pattern_spec.button_band_edging_height > 0:
                    return True
        return False

    def has_button_holes(self):
        if self.has_button_band():
            pattern_spec = self.get_spec_source()
            if pattern_spec.number_of_buttons:
                if pattern_spec.number_of_buttons > 0:
                    return True
        return False

    def neck_edging_height_in_rows(self):
        pattern_spec = self.get_spec_source()
        neck_edging_height = pattern_spec.neck_edging_height
        gauge = pattern_spec.gauge
        rows = neck_edging_height * gauge.rows
        return int(round(rows, ROUND_UP))


class SweaterAreaMixin(AreaMixin, BaseSweaterPatternPieces):

    # sub-classes should implement:
    #
    # sweater_front
    # vest_front
    # sweater_back
    # vest_back
    # sleeve
    # cardgian_vest
    # cardigan_sleeved
    # get_spec_source()

    def sub_pieces(self):
        pre_sub_pieces = [
            self.sweater_back,
            self.sweater_front,
            self.vest_back,
            self.vest_front,
            self.sleeve,
            self.cardigan_vest,
            self.cardigan_sleeved,
        ]
        return [x for x in pre_sub_pieces if x is not None]

    def total_neckline_pickup_stitches(self):

        return_me = 0

        if self.sweater_back:
            return_me += self.sweater_back.neckline.stitches_to_pick_up()
        else:
            return_me += self.vest_back.neckline.stitches_to_pick_up()

        if self.sweater_front:
            return_me += self.sweater_front.neckline.stitches_to_pick_up()
        elif self.vest_front:
            return_me += self.vest_front.neckline.stitches_to_pick_up()
        elif self.cardigan_sleeved:
            return_me += self.cardigan_sleeved.total_neckline_stitches_to_pick_up()
        else:
            return_me += self.cardigan_vest.total_neckline_stitches_to_pick_up()

        return int(return_me)

    def total_armhole_stitches(self):
        if self.sweater_back:
            armhole_circ = 2 * self.sweater_back.actual_armhole_circumference
        else:
            armhole_circ = 2 * self.vest_back.actual_armhole_circumference

        gauge = self.get_spec_source().gauge
        stitches = int(round(armhole_circ * gauge.stitches, ROUND_ANY_DIRECTION))
        return stitches

    def get_buttonband(self):
        if self.is_veeneck_cardigan():
            neck_stitches = self.total_neckline_pickup_stitches()
            if self.cardigan_sleeved:
                return self.cardigan_sleeved.make_veeneck_buttonband(neck_stitches)
            else:
                return self.cardigan_vest.make_veeneck_buttonband(neck_stitches)
        else:
            if self.cardigan_sleeved:
                return self.cardigan_sleeved.make_buttonband()
            else:
                return self.cardigan_vest.make_buttonband()

    def _neck_trim_area(self):
        pattern_spec = self.get_spec_source()
        gauge = pattern_spec.gauge
        neck_height = self.neck_edging_height_in_rows() / gauge.rows
        neck_width = self.total_neckline_pickup_stitches() / gauge.stitches
        return neck_height * neck_width

    def _armhole_trim_area(self):
        """
        Return area of armhole trim, for both sides.
        :return:
        """
        pattern_spec = self.get_spec_source()
        gauge = pattern_spec.gauge
        if self.get_spec_source().is_vest():
            trim_width = self.total_armhole_stitches() / gauge.stitches
            trim_height = pattern_spec.armhole_edging_height
            if trim_height is not None:
                return trim_width * trim_height * 2
            else:
                return 0
        else:
            None

    def _trim_area(self):
        return_me = 0

        # neck and buttonband
        if self.is_veeneck_cardigan():
            if self.has_button_band():
                bb = self.get_buttonband()
                return_me += bb.area()
        else:
            if self.has_button_band():
                bb = self.get_buttonband()
                return_me += bb.area()

            return_me += self._neck_trim_area()

        # armhole trim
        if self.get_spec_source().is_vest():
            return_me += self._armhole_trim_area()

        return return_me


class SweaterPatternPieces(SweaterAreaMixin, PatternPieces):

    sweater_back = models.OneToOneField(
        SweaterBack, null=True, blank=True, on_delete=models.CASCADE
    )
    sweater_front = models.OneToOneField(
        SweaterFront, null=True, blank=True, on_delete=models.CASCADE
    )
    vest_back = models.OneToOneField(
        VestBack, null=True, blank=True, on_delete=models.CASCADE
    )
    vest_front = models.OneToOneField(
        VestFront, null=True, blank=True, on_delete=models.CASCADE
    )
    sleeve = models.OneToOneField(
        Sleeve, null=True, blank=True, on_delete=models.CASCADE
    )
    cardigan_vest = models.OneToOneField(
        CardiganVest, null=True, blank=True, on_delete=models.CASCADE
    )
    cardigan_sleeved = models.OneToOneField(
        CardiganSleeved, null=True, blank=True, on_delete=models.CASCADE
    )

    def get_back_piece(self):
        if self.sweater_back:
            return self.sweater_back
        else:
            return self.vest_back

    def get_front_piece(self):
        if self.sweater_front:
            return self.sweater_front
        elif self.vest_front:
            return self.vest_front
        elif self.cardigan_sleeved:
            return self.cardigan_sleeved
        else:
            return self.cardigan_vest

    def total_finished_hip(self):

        return_me = 0

        if self.sweater_back:
            return_me += self.sweater_back.actual_hip
        else:
            return_me += self.vest_back.actual_hip

        if self.sweater_front:
            return_me += self.sweater_front.actual_hip
        elif self.vest_front:
            return_me += self.vest_front.actual_hip
        elif self.cardigan_vest:
            return_me += self.cardigan_vest.total_front_finished_hip
        else:
            return_me += self.cardigan_sleeved.total_front_finished_hip

        return return_me

    def total_finished_waist(self):

        # Note: can be None
        summands = []

        if self.sweater_back:

            summands.append(self.sweater_back.actual_waist)
        else:
            summands.append(self.vest_back.actual_waist)

        if self.sweater_front:
            summands.append(self.sweater_front.actual_waist)
        elif self.vest_front:
            summands.append(self.vest_front.actual_waist)
        elif self.cardigan_vest:
            summands.append(self.cardigan_vest.total_front_finished_waist)
        else:
            summands.append(self.cardigan_sleeved.total_front_finished_waist)

        if None in summands:
            return None
        else:
            return sum(summands)

    def total_finished_bust(self):

        return_me = 0

        if self.sweater_back:
            return_me += self.sweater_back.actual_bust
        else:
            return_me += self.vest_back.actual_bust

        if self.sweater_front:
            return_me += self.sweater_front.actual_bust
        elif self.vest_front:
            return_me += self.vest_front.actual_bust
        elif self.cardigan_vest:
            return_me += self.cardigan_vest.total_front_finished_bust
        else:
            return_me += self.cardigan_sleeved.total_front_finished_bust

        return return_me

    def cardigan_front_cast_on_stitches(self):
        # Should NOT be the total across both pieces
        if self.cardigan_sleeved:
            return self.cardigan_sleeved.cast_ons
        elif self.cardigan_vest:
            return self.cardigan_vest.cast_ons
        else:
            return None

    def pullover_front_cast_on_stitches(self):
        if self.sweater_front:
            return self.sweater_front.cast_ons
        else:
            return self.vest_front.cast_ons

    def back_cast_on_stitches(self):
        if self.sweater_back:
            return self.sweater_back.cast_ons
        else:
            return self.vest_back.cast_ons

    def total_cast_on_stitches(self):
        return_me = 0

        if self.sweater_back:
            return_me += self.sweater_back.cast_ons
        else:
            return_me += self.vest_back.cast_ons

        if self.sweater_front:
            return_me += self.sweater_front.cast_ons
        elif self.vest_front:
            return_me += self.vest_front.cast_ons
        elif self.cardigan_sleeved:
            return_me += self.cardigan_sleeved.total_front_cast_ons
        else:  # self.cardigan_vest
            return_me += self.cardigan_vest.total_front_cast_ons

        return return_me

    def seamless_sleeve_top_armcap(self):
        armscye_c = self.sleeve.armscye_c
        armscye_d = self.sleeve.armscye_d

        return armscye_c + (4 * armscye_d)

    def seamless_sleeve_half_top_armcap(self):
        return int(round(self.seamless_sleeve_top_armcap() / 2, ROUND_DOWN))

    def seamless_sleeve_bottom(self):
        if self.sweater_back:
            backpiece = self.sweater_back
        else:
            backpiece = self.vest_back
        return 2 * (backpiece.armhole_x + backpiece.armhole_y)

    #
    # Images.
    #

    @property
    def construction(self):
        return self.schematic.construction

    def get_back_schematic_image(self):
        back_schematic = self.schematic.get_back_piece()
        return back_schematic.get_schematic_image()

    def get_sleeve_schematic_image(self):
        sleeve_schematic = self.schematic.get_sleeve_piece()
        if sleeve_schematic:
            return sleeve_schematic.get_schematic_image()
        else:
            return None

    def get_front_schematic_image(self):
        # This one is a little more complicated. If the front piece has an
        # empty() neckline, then  we should use piece.EMPTY_NECK_IMAGE instead.
        # Note that currently, this can only happen for cardigans.
        front_schematic = self.schematic.get_front_piece()
        front_piece = self.get_front_piece()
        if front_piece.neckline.empty():
            assert self.is_cardigan()
            construction = self.construction
            if front_piece.is_straight:
                silhouette = SDC.SILHOUETTE_STRAIGHT
            elif front_piece.is_hourglass:
                silhouette = SDC.SILHOUETTE_HOURGLASS
            elif front_piece.is_aline:
                silhouette = SDC.SILHOUETTE_ALINE
            else:
                assert front_piece.is_tapered
                silhouette = SDC.SILHOUETTE_TAPERED
            return get_front_schematic_url(
                silhouette, None, construction, cardigan=True, empty=True
            )

        else:
            return front_schematic.get_schematic_image()

    @property
    def fit_text(self):
        return self.get_spec_source().fit_patterntext

    def bust_dart_params(self):
        """
        Returns a (possibly-empty) list of tuples:
            (height_in_inches, stitches_between_wraps,
            height_in_rows, half_num_wraps)
        The number of wraps is equal to the height_in_rows, which should
        be the height_in_inches in rows, rounded up to even.

        The list may be empty if the body does not have an inter-nipple
        distance, or the garment is not an hourglass disign
        """

        # first, take care of some corner cases:
        if any(
            [
                not self.get_spec_source().is_hourglass,
                self.get_spec_source().body.inter_nipple_distance is None,
            ]
        ):
            return []

        param_list = []
        pattern_spec = self.get_spec_source()
        gauge = pattern_spec.swatch.get_gauge()

        if self.sweater_front:
            bust_stitches = self.sweater_front._bust_stitches_internal_use
        elif self.vest_front:
            bust_stitches = self.vest_front._bust_stitches_internal_use
        elif self.cardigan_sleeved:
            bust_stitches = sum(
                [
                    2 * self.cardigan_sleeved._bust_stitches_internal_use,
                    self.cardigan_sleeved.actual_button_band_stitches,
                ]
            )
        else:  # self.cardigan_vest
            bust_stitches = sum(
                [
                    2 * self.cardigan_vest._bust_stitches_internal_use,
                    self.cardigan_vest.actual_button_band_stitches,
                ]
            )

        inter_nipple = pattern_spec.body.inter_nipple_distance
        inner_dart_width = inter_nipple + BUST_DART_MARKER_ALLOWANCE

        if is_even(bust_stitches):
            inner_dart_stitches = round(
                inner_dart_width * gauge.stitches, ROUND_ANY_DIRECTION, 2, 0
            )
        else:
            inner_dart_stitches = round(
                inner_dart_width * gauge.stitches, ROUND_ANY_DIRECTION, 2, 1
            )

        stitches_for_wraps = bust_stitches - inner_dart_stitches

        assert is_even(stitches_for_wraps)

        wrap_stitches_per_side = stitches_for_wraps / 2

        heights_in_inches = BUST_DART_INSTRUCTION_HEIGHTS
        for height in heights_in_inches:

            height_in_rows = int(round(height * gauge.rows, ROUND_UP, 2))
            half_num_wraps = int(height_in_rows / 2)

            fenceposted_wraps_per_side = (height_in_rows / 2) - 1

            if fenceposted_wraps_per_side > 0:
                stitches_between_wraps = int(
                    round(
                        wrap_stitches_per_side / fenceposted_wraps_per_side, ROUND_DOWN
                    )
                )

                params = (
                    height,
                    stitches_between_wraps,
                    height_in_rows,
                    half_num_wraps,
                )
                param_list.append(params)

        return param_list

    @classmethod
    def make_from_individual_pieced_schematic(cls, ips):
        parameters = {"schematic": ips}

        spec_source = ips.individual_garment_parameters.get_spec_source()
        swatch = spec_source.swatch
        fit = spec_source.garment_fit
        roundings = _rounding_directions[fit]
        ease_tolerances = _ease_tolerances[fit]

        # individual_pieced_schematic guarantees at least one of the following
        # will be provided: sweaterback and vestback

        if ips.sweater_back is not None:

            sb = SweaterBack.make(swatch, ips.sweater_back, roundings, ease_tolerances)
            parameters["sweater_back"] = sb

            if ips.sweater_front is not None:
                sf = SweaterFront.make(
                    sb, swatch, ips.sweater_front, roundings, ease_tolerances
                )

                parameters["sweater_front"] = sf

            if ips.sleeve is not None:
                sl = Sleeve.make(
                    swatch, ips.sleeve, roundings, ease_tolerances, sb, spec_source
                )

                parameters["sleeve"] = sl

            if ips.cardigan_sleeved is not None:
                cs = CardiganSleeved.make(
                    sb, swatch, ips.cardigan_sleeved, roundings, ease_tolerances
                )

                parameters["cardigan_sleeved"] = cs

        if ips.vest_back is not None:

            vb = VestBack.make(swatch, ips.vest_back, roundings, ease_tolerances)
            parameters["vest_back"] = vb

            if ips.vest_front is not None:
                vf = VestFront.make(
                    vb, swatch, ips.vest_front, roundings, ease_tolerances
                )
                parameters["vest_front"] = vf

            if ips.cardigan_vest is not None:
                cv = CardiganVest.make(
                    vb, swatch, ips.cardigan_vest, roundings, ease_tolerances
                )
                parameters["cardigan_vest"] = cv

        instance = cls(**parameters)

        # We are doing this get_buttonband solely to give ourselves the chance
        # to throw an exception (which calling functions are responsible for
        # handling).
        # Otherwise we may inadvertently sell the user a sweater that we cannot
        # actually construct; there are edge cases where it is possible to
        # construct the rest of the sweater (meaning we would get through the
        # pattern wizard without error and sell the pattern) but not to
        # construct the buttonband (meaning we would throw an error during
        # rendering).
        # Yes, we are actually inconsistent in our underscore use. Whoops.
        if instance.has_button_band():
            instance.get_buttonband()

        return instance


class GradedSweaterPatternPieces(BaseSweaterPatternPieces, GradedPatternPieces):

    def get_pattern_class(self):
        from ..pattern import GradedSweaterPattern

        return GradedSweaterPattern

    @classmethod
    def make_from_schematic(cls, graded_construction_schematic):
        return_me = cls()
        return_me.schematic = graded_construction_schematic
        return_me.save()

        spec_source = graded_construction_schematic.get_spec_source()
        fit = spec_source.garment_fit
        roundings = _rounding_directions[fit]
        ease_tolerances = _ease_tolerances[fit]

        for sb_sch in graded_construction_schematic.sweater_back_schematics:
            sb = GradedSweaterBack.make(return_me, sb_sch, roundings, ease_tolerances)

            try:
                sf_sch = graded_construction_schematic.sweater_front_schematics.get(
                    GradedSweaterFrontSchematic___gp_grade__grade=sb_sch.gp_grade.grade
                )
                front_piece = GradedSweaterFront.make(
                    sf_sch, sb, roundings, ease_tolerances
                )
                bust_circ = sb.actual_bust + front_piece.actual_bust
            except GradedSweaterFrontSchematic.DoesNotExist:
                cs_sch = graded_construction_schematic.cardigan_sleeved_schematics.get(
                    GradedCardiganSleevedSchematic___gp_grade__grade=sb_sch.gp_grade.grade
                )
                front_piece = GradedCardiganSleeved.make(
                    cs_sch, sb, roundings, ease_tolerances
                )
                bust_circ = sb.actual_bust + front_piece.total_front_finished_bust

            # If you ever change the computation of sort_key, change GradedHBPM.finished_full_bust
            # and GradedCardgian.finsihed_full_bust
            sb.sort_key = bust_circ
            sb.full_clean()
            sb.save()
            front_piece.sort_key = bust_circ
            front_piece.full_clean()
            front_piece.save()

            # Must come after the front-piece creation and sort-key re-computation so that
            # sleeves inherit the final sort-key from the backs
            sl_sch = graded_construction_schematic.sleeve_schematics.get(
                GradedSleeveSchematic___gp_grade__grade=sb_sch.gp_grade.grade
            )
            sleeve = GradedSleeve.make(
                sl_sch, sb, roundings, ease_tolerances, spec_source
            )
            sleeve.full_clean()
            sleeve.save()

        for vb_sch in graded_construction_schematic.vest_back_schematics:
            vb = GradedVestBack.make(return_me, vb_sch, roundings, ease_tolerances)

            try:
                vf = graded_construction_schematic.vest_front_schematics.get(
                    GradedVestFrontSchematic___gp_grade__grade=vb_sch.gp_grade.grade
                )
                front_piece = GradedVestFront.make(vf, vb, roundings, ease_tolerances)
                bust_circ = vb.actual_bust + front_piece.actual_bust
            except GradedVestFrontSchematic.DoesNotExist:
                cv = graded_construction_schematic.cardigan_vest_schematics.get(
                    GradedCardiganVestSchematic___gp_grade__grade=vb_sch.gp_grade.grade
                )
                front_piece = GradedCardiganVest.make(
                    cv, vb, roundings, ease_tolerances
                )
                bust_circ = vb.actual_bust + front_piece.total_front_finished_bust

            # If you ever change the computation of sort_key, change GradedHBPM.finished_full_bust
            # and GradedCardgian.finsihed_full_bust
            vb.sort_key = bust_circ
            vb.full_clean()
            vb.save()
            front_piece.sort_key = bust_circ
            front_piece.full_clean()
            front_piece.save()

        return return_me

    # For the following: no need to sort-- GradedPatternPiece's are automatically
    # sorted by sort_key

    @property
    def sweater_backs(self):
        return GradedSweaterBack.objects.filter(graded_pattern_pieces=self).all()

    @property
    def sweater_fronts(self):
        return GradedSweaterFront.objects.filter(graded_pattern_pieces=self).all()

    @property
    def vest_backs(self):
        return GradedVestBack.objects.filter(graded_pattern_pieces=self).all()

    @property
    def vest_fronts(self):
        return GradedVestFront.objects.filter(graded_pattern_pieces=self).all()

    @property
    def sleeves(self):
        return GradedSleeve.objects.filter(graded_pattern_pieces=self).all()

    @property
    def cardigan_vests(self):
        return GradedCardiganVest.objects.filter(graded_pattern_pieces=self).all()

    @property
    def cardigan_sleeveds(self):
        return GradedCardiganSleeved.objects.filter(graded_pattern_pieces=self).all()

    def get_back_pieces(self):
        if self.sweater_backs:
            return self.sweater_backs
        else:
            return self.vest_backs

    def get_front_pieces(self):
        if self.sweater_fronts:
            return self.sweater_fronts
        elif self.vest_fronts:
            return self.vest_fronts
        elif self.cardigan_sleeveds:
            return self.cardigan_sleeveds
        else:
            return self.cardigan_vests

    def has_sleeves(self):
        return bool(self.sleeves)

    def grade_list_for_pattern_summary(self):
        back_pieces = self.sweater_backs if self.sweater_backs else self.vest_backs
        grades = [bp.finished_full_bust for bp in back_pieces]
        return grades

    def _make_grades(self):
        if self.sweater_backs:
            sorted_pre_dicts = [
                (sb, {"sweater_back": sb, "vest_back": None})
                for sb in self.sweater_backs
            ]
        else:
            sorted_pre_dicts = [
                (vb, {"sweater_back": None, "vest_back": vb}) for vb in self.vest_backs
            ]

        return_me = []

        for back_piece, new_dict in sorted_pre_dicts:

            grade = back_piece.schematic.gp_grade.grade

            try:
                sf = GradedSweaterFront.objects.filter(
                    graded_pattern_pieces=self, schematic__gp_grade__grade=grade
                ).get()
                new_dict["sweater_front"] = sf
            except GradedSweaterFront.DoesNotExist:
                new_dict["sweater_front"] = None

            try:
                vf = GradedVestFront.objects.filter(
                    graded_pattern_pieces=self, schematic__gp_grade__grade=grade
                ).get()
                new_dict["vest_front"] = vf
            except GradedVestFront.DoesNotExist:
                new_dict["vest_front"] = None

            try:
                sl = GradedSleeve.objects.filter(
                    graded_pattern_pieces=self, schematic__gp_grade__grade=grade
                ).get()
                new_dict["sleeve"] = sl
            except GradedSleeve.DoesNotExist:
                new_dict["sleeve"] = None

            try:
                cv = GradedCardiganVest.objects.filter(
                    graded_pattern_pieces=self, schematic__gp_grade__grade=grade
                ).get()
                new_dict["cardigan_vest"] = cv
            except GradedCardiganVest.DoesNotExist:
                new_dict["cardigan_vest"] = None

            try:
                cs = GradedCardiganSleeved.objects.filter(
                    graded_pattern_pieces=self, schematic__gp_grade__grade=grade
                ).get()
                new_dict["cardigan_sleeved"] = cs
            except GradedCardiganSleeved.DoesNotExist:
                new_dict["cardigan_sleeved"] = None

            # santiy-check the grades
            assert (
                new_dict["sweater_back"] is not None
                or new_dict["vest_back"] is not None
            )
            if new_dict["sweater_back"] is not None:
                assert new_dict["sleeve"] is not None
                assert (
                    new_dict["vest_front"] is None and new_dict["cardigan_vest"] is None
                )
                # exactly one should be None
                assert (new_dict["sweater_front"] is None) != (
                    new_dict["cardigan_sleeved"] is None
                )
            else:
                assert new_dict["sleeve"] is None
                assert (
                    new_dict["sweater_front"] is None
                    and new_dict["cardigan_sleeved"] is None
                )
                # exactly one should be None
                assert (new_dict["vest_front"] is None) != (
                    new_dict["cardigan_vest"] is None
                )

            return_me.append(new_dict)

        return return_me

    def area_list(self):

        # first, a helper_class
        class _SweaterGradeAreaMixin(SweaterAreaMixin):

            def __init__(
                self,
                spec_source,
                *args,
                sweater_back=None,
                sweater_front=None,
                vest_back=None,
                vest_front=None,
                sleeve=None,
                cardigan_vest=None,
                cardigan_sleeved=None,
                **kwargs
            ):
                super(_SweaterGradeAreaMixin, self).__init__(*args, **kwargs)
                self.sweater_back = sweater_back
                self.sweater_front = sweater_front
                self.vest_back = vest_back
                self.vest_front = vest_front
                self.sleeve = sleeve
                self.cardigan_vest = cardigan_vest
                self.cardigan_sleeved = cardigan_sleeved
                self.spec_source = spec_source

            def get_spec_source(self):
                return self.spec_source

        # Now, build grades
        spec_source = self.get_spec_source()
        grades = self._make_grades()
        return_me = []
        for grade_dict in grades:
            sgam = _SweaterGradeAreaMixin(spec_source, **grade_dict)
            area = sgam.area()
            return_me.append(area)
        return return_me

    def _map_across_pieces(self, piece_list, f):
        return CompoundResult([f(p) for p in piece_list])

    def _sum_across_pieces(self, pullover_f, cardi_f):
        if self.sweater_backs:
            back_list = self._map_across_pieces(self.sweater_backs, pullover_f)
        else:
            back_list = self._map_across_pieces(self.vest_backs, pullover_f)

        if self.sweater_fronts:
            front_list = self._map_across_pieces(self.sweater_fronts, pullover_f)
        elif self.vest_fronts:
            front_list = self._map_across_pieces(self.vest_fronts, pullover_f)
        elif self.cardigan_sleeveds:
            front_list = self._map_across_pieces(self.cardigan_sleeveds, cardi_f)
        else:
            front_list = self._map_across_pieces(self.cardigan_vests, cardi_f)

        return_me = [x + y for (x, y) in zip(back_list, front_list)]
        return return_me

    def total_neckline_pickup_stitches(self):
        return_me = self._sum_across_pieces(
            lambda p: p.neckline.stitches_to_pick_up(),
            lambda p: p.total_neckline_stitches_to_pick_up(),
        )
        return CompoundResult(return_me)

    def total_armhole_stitches(self):
        circs = self._sum_across_pieces(
            lambda p: p.actual_armhole_circumference,
            lambda p: p.actual_armhole_circumference,
        )

        gauge = self.get_spec_source().gauge
        stitches = CompoundResult(
            int(round(circ * gauge.stitches, ROUND_ANY_DIRECTION)) for circ in circs
        )
        return stitches

    def get_buttonband(self):
        if self.is_veeneck_cardigan():
            button_bands = []
            fronts = (
                self.cardigan_sleeveds
                if self.cardigan_sleeveds
                else self.cardigan_vests
            )
            backs = self.sweater_backs if self.sweater_backs else self.vest_backs

            for front, back in zip(fronts, backs):
                neckline_stitches = sum(
                    [
                        back.neckline.stitches_to_pick_up(),
                        front.total_neckline_stitches_to_pick_up(),
                    ]
                )
                bb = front.make_veeneck_buttonband(neckline_stitches)
                button_bands.append(bb)

            return PieceList(button_bands)

        else:
            if self.cardigan_sleeveds:
                return PieceList(cs.make_buttonband() for cs in self.cardigan_sleeveds)
            else:
                return PieceList(cv.make_buttonband() for cv in self.cardigan_vests)

    # Invariants
    # Body pieces all have bust increases, or don't. Same for waist increases
    # Cannot mix-and-match piece-types. Allowed combos:
    #   * sweater back, front, sleeve
    #   * vest back, front
    #   * sweater back, cardi_sleeved, sleeve
    #   * vest back, cardi vest front
