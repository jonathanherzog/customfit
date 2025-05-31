import logging

from django.conf import settings
from django.views.generic import FormView
from django.views.generic.base import TemplateView

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    ROUND_DOWN,
    cm_to_inches,
    is_even,
    round,
)
from customfit.patterns.templatetags.pattern_conventions import (
    length_fmt,
    string_of_value,
)
from customfit.sweaters.models.pieces import (
    EdgeShapingResult,
    compute_armcap_shaping,
    compute_armhole_circumference,
)

from . import forms
from .helpers import SpacingResult

logger = logging.getLogger(__name__)


class CalculatorListView(TemplateView):
    template_name = "knitting_calculators/tool_list.html"


class BaseCalculatorView(FormView):

    # Subclasses must provide self.tool_name

    def render_to_response(self, context, **response_kwargs):
        context["tool_name"] = self.tool_name
        return super(BaseCalculatorView, self).render_to_response(
            context, **response_kwargs
        )


class ShapingPlacerCalculatorView(BaseCalculatorView):

    template_name = "knitting_calculators/shaping_calculator.html"
    form_class = forms.ShapingPlacerCalculatorForm
    tool_name = "Shaping Calculator"

    class TooFewRows(Exception):
        pass

    class ParityError(Exception):
        pass

    def get_shaping_result(self, form):

        stitch_count1 = form.cleaned_data["starting_stitches"]
        stitch_count2 = form.cleaned_data["ending_stitches"]
        total_rows = form.cleaned_data["total_rows"]
        stitches_per_shaping_row = form.cleaned_data["stitches_per_shaping_row"]

        # Sanity check 1: does the parity work out?
        if stitches_per_shaping_row == 2:
            # add/subtract two stitches per row? Then the difference between the
            # stitch_count must be even
            if not is_even(stitch_count1 - stitch_count2):
                raise self.ParityError

        # Sanity check 2: do we have enough rows?
        stitches_to_shape = abs(stitch_count1 - stitch_count2)
        min_rows_needed = stitches_to_shape / stitches_per_shaping_row
        if total_rows < min_rows_needed:
            raise self.TooFewRows

        # Having eliminated common error cases, let's do the shaping
        if stitches_per_shaping_row == 2:
            larger_stitches = max([stitch_count1, stitch_count2])
            smaller_stitches = min([stitch_count1, stitch_count2])
        else:
            assert form.cleaned_data["stitches_per_shaping_row"] == 1
            # The shaping calculator assumes we get to decrease/increase two stitches
            # per shaping row. But in this case, the user wants one increase/decrease
            # per shaping row. So we need to fool the shaping_calculator by doubling
            # the starting/ending counts
            larger_stitches = 2 * max([stitch_count1, stitch_count2])
            smaller_stitches = 2 * min([stitch_count1, stitch_count2])

        shaping_result = EdgeShapingResult.compute_shaping_partial(
            larger_stitches, smaller_stitches, total_rows
        )

        return shaping_result

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.
        context = {"form": form}
        try:
            shaping_result = self.get_shaping_result(form)
        except self.ParityError:
            context["shaping_error_message"] = (
                "We're sorry, but we can't shape an odd number of stitches at 2 "
                "stitches per row. Check your numbers and try again? If you think "
                "this message is in error, drop us a note at %s "
                "and let us know what you were trying to do."
                % settings.AHD_SUPPORT_EMAIL_BARE
            )
            context["show_knitting_instructions"] = False
            return self.render_to_response(context)
        except self.TooFewRows:
            context["shaping_error_message"] = (
                "We're sorry, but we can't compute the shaping: There are more shaping "
                "rows than total rows. Check your inputs, and try again? (If you "
                "think this message is in error, drop us a note at %s.)"
                % settings.AHD_SUPPORT_EMAIL_BARE
            )
            context["show_knitting_instructions"] = False
            return self.render_to_response(context)
        except:
            logger.exception(
                "Unable to compute shaping. Form's cleaned_data: %s", form.cleaned_data
            )
            raise
        else:

            if (shaping_result is None) or (not shaping_result.constraints_met):
                context["shaping_error_message"] = (
                    "We're sorry, but given your input we can't calculate the "
                    "shaping. Check your numbers and try again? If you think this "
                    "message is in error, drop us a note at %s "
                    "and let us know what you were trying to do."
                    % settings.AHD_SUPPORT_EMAIL_BARE
                )
                context["show_knitting_instructions"] = False
                logger.warning(
                    "Unable to compute shaping. Form's cleaned_data: %s",
                    form.cleaned_data,
                )
            else:
                num_shaping_rows = shaping_result.num_standard_shaping_rows
                inter_shaping_rows = shaping_result.rows_between_standard_shaping_rows
                if inter_shaping_rows is None:
                    inter_shaping_rows = 0
                total_rows = form.cleaned_data["total_rows"]

                # Compute the number of rows between first shaping row and last shaping row, including both
                num_shaping_repeats = num_shaping_rows - 1
                rows_in_shaping = sum(
                    [num_shaping_rows, inter_shaping_rows * num_shaping_repeats]
                )

                # Now, how many rows are left? Assign to beginning and end
                remaining_rows = total_rows - rows_in_shaping
                if num_shaping_rows == 0:
                    # Corner case: put all rows at the 'front'
                    rows_before_first_shaping_row = remaining_rows
                    rows_after_last_shaping_row = 0
                else:
                    rows_before_first_shaping_row = round(
                        remaining_rows / 2, ROUND_DOWN
                    )
                    rows_after_last_shaping_row = (
                        remaining_rows - rows_before_first_shaping_row
                    )

                # Decide whether to call them 'increases' or 'decreases'
                start_stitches = form.cleaned_data["starting_stitches"]
                ending_stitches = form.cleaned_data["ending_stitches"]
                shaping_word = (
                    "increase" if start_stitches < ending_stitches else "decrease"
                )

                context.update(
                    {
                        "show_knitting_instructions": True,
                        "num_shaping_rows": int(num_shaping_rows),
                        "num_shaping_repeats": int(num_shaping_repeats),
                        "rows_before_first_shaping_row": int(
                            rows_before_first_shaping_row
                        ),
                        "shaping_word": shaping_word,
                        "inter_shaping_rows": int(inter_shaping_rows),
                        "rows_after_last_shaping_row": int(rows_after_last_shaping_row),
                    }
                )

            return self.render_to_response(context)


class ButtonSpacingCalculator(BaseCalculatorView):

    template_name = "knitting_calculators/button_spacer.html"
    form_class = forms.ButtonSpacingCalculatorForm
    tool_name = "Buttonhole Placer"

    # Note: you'll find logic like that of this view in sweaters.models.pieces.finishing.ButtonBand.
    # The use case of that class and this view are different enough, however, for it to
    # make sense for the code-bases to be kept entirely separate.

    class TooFewStitches(Exception):
        pass

    def compute_spacing(
        self, number_of_stitches, stitches_per_buttonhole, number_of_buttons
    ):

        # Quick sanity check for a common error case that we can handle: not enough stitches
        min_stitches_needed = sum(
            [
                stitches_per_buttonhole
                * number_of_buttons,  # Stitches in the holes themselves
                number_of_buttons + 1,  # at least one stitch before and after each hole
            ]
        )
        if number_of_stitches < min_stitches_needed:
            raise self.TooFewStitches

        # Having eliminated common error case, let's do the shaping
        spacing_result = SpacingResult(
            number_of_stitches, number_of_buttons, stitches_per_buttonhole
        )

        if not spacing_result.constraints_met:
            return None
        else:
            extra_stitches = spacing_result.extra_units
            stitches_between_buttonholes = spacing_result.units_between_events
            num_inter_button_intervals = number_of_buttons - 1
            if extra_stitches >= num_inter_button_intervals:
                if stitches_between_buttonholes is None:
                    stitches_between_buttonholes = 1
                else:
                    stitches_between_buttonholes += 1
                extra_stitches -= num_inter_button_intervals

            extra_first_stitches = round(extra_stitches / 2.0, ROUND_DOWN)
            extra_final_stitches = extra_stitches - extra_first_stitches
            initial_stitches = sum(
                [spacing_result.units_before_first_event, extra_first_stitches]
            )
            final_stitches = sum(
                [spacing_result.units_after_last_event, extra_final_stitches]
            )

            if any(
                [
                    initial_stitches <= 0,
                    stitches_between_buttonholes <= 0,
                    final_stitches <= 0,
                ]
            ):
                return None
            else:
                return (initial_stitches, stitches_between_buttonholes, final_stitches)

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.

        stitches_per_buttonhole = form.cleaned_data["stitches_per_buttonhole"]
        number_of_buttons = form.cleaned_data["number_of_buttons"]
        number_of_stitches = form.cleaned_data["number_of_stitches"]
        number_of_repeats = number_of_buttons - 1

        context = {"form": form}

        try:
            spacing_result = self.compute_spacing(
                number_of_stitches, stitches_per_buttonhole, number_of_buttons
            )
        except self.TooFewStitches:
            context["spacing_error_message"] = (
                "We're sorry, but we can't compute the button spacing: "
                "There aren't enough total stitches to make the buttonholes. "
                "Check your inputs, and try again? (If you think this message is "
                "in error, drop us a note at %s.)" % settings.AHD_SUPPORT_EMAIL_BARE
            )
            context["show_knitting_instructions"] = False
            return self.render_to_response(context)

        except:
            logger.exception(
                "Problem computing button spacing. The form's cleaned_data: ",
                form.cleaned_data,
            )
            raise

        else:
            if spacing_result is None:

                context["spacing_error_message"] = (
                    "We're sorry, but given your input we can't calculate the button "
                    "spacing. Check your numbers and try again? If you think this "
                    "message is in error, drop us a note at %s "
                    "and let us know what you were trying to do."
                    % settings.AHD_SUPPORT_EMAIL_BARE
                )
                context["show_knitting_instructions"] = False
                logger.warning(
                    "Problem computing button spacing. The form's cleaned_data: ",
                    form.cleaned_data,
                )
            else:
                (initial_stitches, stitches_between_buttonholes, final_stitches) = (
                    spacing_result
                )

                context.update(
                    {
                        "show_knitting_instructions": True,
                        "number_of_buttons": int(number_of_buttons),
                        "initial_stitches": int(initial_stitches),
                        "stitches_per_buttonhole": int(stitches_per_buttonhole),
                        "stitches_between_buttonholes": int(
                            stitches_between_buttonholes
                        ),
                        "number_of_repeats": int(number_of_repeats),
                        "final_stitches": int(final_stitches),
                    }
                )

            return self.render_to_response(context)


class ArmcapShapingCalculatorView(BaseCalculatorView):

    template_name = "knitting_calculators/armcap_shaper.html"
    form_class = forms.ArmcapShapingCalculatorForm
    tool_name = "Sleeve Cap Generator"

    def form_valid(self, form):
        # This method is called when valid form data has been POSTed.
        # It should return an HttpResponse.

        gauge = form.get_gauge()
        armhole_shaping = form.get_armhole_shaping()
        armhole_depth_inches = form.get_armhole_depth_in_inches()
        bicep_stitches = form.get_bicep_stitches()

        context = {"form": form}

        try:
            (armhole_x, armhole_y, armhole_z) = armhole_shaping

            # compute_armscye_circumference return the circ for just one piece, so we need
            # to double it to get the full circumference of the armhole.
            armhole_circumference = 2 * compute_armhole_circumference(
                gauge, armhole_x, armhole_y, armhole_z, armhole_depth_inches
            )
            armcap_shaping = compute_armcap_shaping(
                gauge, armhole_x, armhole_y, armhole_circumference, bicep_stitches
            )
        except:
            # Note that we return a response even when there's an exception. The armcap-shaper is
            # so vulnerable to bad inputs that we actually expect this to be common. We can't simply
            # return a 500 error for something this common -- we need to handle it. But let's log
            # it for later analysis.
            logger.exception(
                "Exception raised while computing armcap shaping. The form's cleaned_data: ",
                form.cleaned_data,
            )
            context["shaping_error_message"] = (
                "We're sorry, but given your input we can't calculate the sleeve cap "
                "shaping. Check your numbers and try again? If you think this "
                "message is in error, drop us a note at %s "
                "and let us know what you were trying to do."
                % settings.AHD_SUPPORT_EMAIL_BARE
            )
            context["show_knitting_instructions"] = False
        else:
            # Currently, if compute_armcap_shaping doesn't throw an exception then it must return
            # a result. So we don't bother with return-result validation here, like we do in other
            # calculators. (This needs to be revisited if the API for compute_armcap_shaping ever
            # changes.)
            pre_bead_game_stitch_count = sum(
                [
                    bicep_stitches,
                    -2 * armcap_shaping.armscye_x,
                    -2 * armcap_shaping.armscye_y,
                ]
            )
            post_bead_game_stitch_count = pre_bead_game_stitch_count - (
                2
                * sum(
                    [
                        armcap_shaping.one_count_beads,
                        armcap_shaping.two_count_beads,
                        armcap_shaping.four_count_beads,
                        armcap_shaping.six_count_beads,
                    ]
                )
            )

            context["show_knitting_instructions"] = True
            context["armscye_x"] = armcap_shaping.armscye_x
            context["armscye_y"] = armcap_shaping.armscye_y
            context["six_count_beads"] = armcap_shaping.six_count_beads
            context["four_count_beads"] = armcap_shaping.four_count_beads
            context["two_count_beads"] = armcap_shaping.two_count_beads
            context["one_count_beads"] = armcap_shaping.one_count_beads
            context["armscye_d"] = armcap_shaping.armscye_d
            context["armscye_c"] = armcap_shaping.armscye_c

            context["post_bead_game_stitch_count"] = post_bead_game_stitch_count
            context["pre_bead_game_stitch_count"] = pre_bead_game_stitch_count

        # Note that we return a response even when there's an exception. See above
        return self.render_to_response(context)


class PickupCalculatorView(BaseCalculatorView):

    template_name = "knitting_calculators/pickup_calculator.html"
    form_class = forms.PickupCalculatorForm
    tool_name = "Pickup Calculator"

    def form_valid(self, form):
        context = {"form": form}
        context["show_knitting_instructions"] = True
        stitch_gauge = form.get_stitch_gauge()
        row_gauge = form.get_row_gauge()
        row_count = form.get_rows_on_edge()
        stitch_count_float = float(stitch_gauge) * float(row_count) / float(row_gauge)
        context["stitches_to_pick_up"] = int(
            round(stitch_count_float, ROUND_ANY_DIRECTION)
        )
        (stitch_pickup_rate, row_pickup_rate) = self._estimate_pickup_rate(
            stitch_count_float, row_count
        )
        context["stitch_pickup_rate"] = stitch_pickup_rate
        context["row_pickup_rate"] = row_pickup_rate
        return self.render_to_response(context)

    def _estimate_pickup_rate(self, stitch_count, row_count):
        stitches_to_rows = float(stitch_count) / float(row_count)
        best_x = 1
        best_y = 1
        best_dist = abs((float(best_x) / float(best_y)) - stitches_to_rows)
        for curr_x in range(1, 10):
            for curr_y in range(1, 10):
                curr_proportion = float(curr_x) / float(curr_y)
                curr_dist = abs(curr_proportion - stitches_to_rows)
                if curr_dist < best_dist:
                    best_x = curr_x
                    best_y = curr_y
                    best_dist = curr_dist
        return (best_x, best_y)

    def render_to_response(self, context, **response_kwargs):
        context["inches_string"] = self.form_class.EDGE_INPUT_INCHES
        context["count_string"] = self.form_class.EDGE_INPUT_COUNT
        context["cms_string"] = self.form_class.EDGE_INPUT_CMS
        return super(PickupCalculatorView, self).render_to_response(
            context, **response_kwargs
        )


class GaugeCalculatorView(BaseCalculatorView):
    template_name = "knitting_calculators/gauge_calculator.html"
    form_class = forms.GaugeCalculatorForm
    tool_name = "Gauge Calculator"

    def form_valid(self, form):
        context = {"form": form, "show_knitting_instructions": True}
        output_value = form.calculate_result()
        output_type = form.get_output_type()

        if output_type == form.LENGTH:
            output_str = length_fmt(output_value)
        elif output_type == form.COUNT:
            output_value_int = int(round(output_value, ROUND_ANY_DIRECTION))
            count_type = "sts" if form.get_count_units() == form.STITCHES else "rows"
            output_str = "%s %s" % (output_value_int, count_type)
        else:
            assert output_type == form.GAUGE
            count_per_10cm = 10 * cm_to_inches(output_value)
            rounded_imperial_output = round(
                output_value, ROUND_ANY_DIRECTION, multiple=0.25
            )
            rounded_metric_output = round(
                count_per_10cm, ROUND_ANY_DIRECTION, multiple=0.5
            )
            imperial_str = string_of_value(rounded_imperial_output, True)
            metric_str = string_of_value(rounded_metric_output, False)
            count_type = "sts" if form.get_count_units() == form.STITCHES else "rows"
            output_str = '%s %s per inch / %s %s per 4" (10 cm)' % (
                imperial_str,
                count_type,
                metric_str,
                count_type,
            )

        context["instructions"] = output_str
        return self.render_to_response(context)

    def render_to_response(self, context, **response_kwargs):
        context["length_string"] = self.form_class.LENGTH
        context["count_string"] = self.form_class.COUNT
        context["gauge_string"] = self.form_class.GAUGE
        return super(GaugeCalculatorView, self).render_to_response(
            context, **response_kwargs
        )
