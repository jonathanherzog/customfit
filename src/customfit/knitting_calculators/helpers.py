# import cm_to_inches, inches_to_cm so that the rest of the app can find them in helpers
from customfit.helpers.math_helpers import ROUND_DOWN, round

# Import length_fmt, string_of_value so that the rest of the app can find it in helpers


class SpacingResult(object):

    def __init__(
        self,
        total_units,
        number_of_events,
        units_per_event,
        interval_before_first_event=0.5,
        interval_after_last_event=0.5,
    ):
        """
        Space events evenly among the total units, with 'units before the first event' approximately
        equal to (inter-event units * interval_before_first_event) and analagous to 'units after
        last event'.
        """

        assert total_units >= 1
        assert number_of_events >= 1
        assert units_per_event >= 1
        assert interval_after_last_event >= 0
        assert interval_before_first_event >= 0

        # Make first stab at result
        units_in_events = number_of_events * units_per_event
        remaining_units = total_units - units_in_events
        num_inter_event_intervals = number_of_events - 1
        num_intervals = sum(
            [
                num_inter_event_intervals,
                interval_before_first_event,
                interval_after_last_event,
            ]
        )
        if num_intervals == 0:
            # How could this be? If all of num_inter_event_intervals,
            # interval_after_last_event and interval_before_first_event
            # are all zero. And if num_inter_event_intervals is 0, them
            # number_of_events must be 1. Put the single event in the middle.
            interval_after_last_event = 0.5
            interval_before_first_event = 0.5
            num_intervals = 1.0

        units_per_interval = remaining_units / num_intervals

        # First, be conservative. Round everything down and see how many
        # units are left over
        units_before_first_event = round(
            interval_before_first_event * units_per_interval, ROUND_DOWN
        )
        units_after_last_event = round(
            interval_after_last_event * units_per_interval, ROUND_DOWN
        )
        extra_units = (
            remaining_units - units_before_first_event - units_after_last_event
        )

        if number_of_events > 1:
            units_between_events = round(units_per_interval, ROUND_DOWN)
            extra_units -= units_between_events * (number_of_events - 1)
        else:
            units_between_events = None

        # Did we round anything to zero? If so, use extra stitches to bring them up to 1 (if possible)
        if all(
            [
                units_before_first_event == 0,
                extra_units > 0,
                interval_before_first_event > 0,
            ]
        ):
            units_before_first_event += 1
            extra_units -= 1

        if all(
            [
                units_after_last_event == 0,
                extra_units > 0,
                interval_after_last_event > 0,
            ]
        ):
            units_after_last_event += 1
            extra_units -= 1

        if units_between_events is not None:
            if all(
                [extra_units > num_inter_event_intervals, units_between_events <= 0]
            ):
                units_between_events += 1
                extra_units -= num_inter_event_intervals

        # Now check that we have legal and valid values
        if not all(
            [
                units_before_first_event >= 0,
                units_after_last_event >= 0,
                extra_units >= 0,
                (
                    (units_between_events >= 0)
                    if units_between_events is not None
                    else True
                ),
            ]
        ):
            self.constraints_met = False
            self.units_after_last_event = None
            self.units_before_first_event = None
            self.units_between_events = None
            self.extra_units = None
        else:
            self.constraints_met = True
            self.units_after_last_event = units_after_last_event
            self.units_before_first_event = units_before_first_event
            self.units_between_events = units_between_events
            self.extra_units = extra_units
