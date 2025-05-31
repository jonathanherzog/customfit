from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Field, Fieldset, Layout, Submit
from django import forms
from django.core.exceptions import ValidationError

from customfit.helpers.math_helpers import (
    ROUND_ANY_DIRECTION,
    cm_to_inches,
    inches_to_cm,
    round,
)
from customfit.swatches.models import Gauge


class BaseCalculatorForm(forms.Form):

    # subclasses should redefine this
    HELP_TEXT = {}

    def __init__(self, *args, **kwargs):
        super(BaseCalculatorForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-xs-12 col-sm-4"
        self.helper.field_class = "col-xs-12 col-sm-4 hide-help-text"
        self.helper.add_input(
            Submit("submit-btn", "Compute", css_class="btn-customfit-action")
        )
        self.add_help_text(self.HELP_TEXT)

    def add_help_text(self, help_text):
        for field in self.fields:
            if field in help_text:
                self.fields[field].help_text = help_text[field]
                self.fields[field].label += '<span class="help-callout-circle">?</span>'
            else:
                self.helper[field].wrap(Div, css_class="no-help-text")


class ShapingPlacerCalculatorForm(BaseCalculatorForm):

    HELP_TEXT = {
        "starting_stitches": "number of stitches before you begin shaping",
        "ending_stitches": "number of stitches after all shaping is complete",
        "total_rows": "the maximum number of rows your shaping can take up",
        "stitches_per_shaping_row": "the number of stitches added or removed in each shaping row",
    }

    stitches_per_shaping_row_options = ((1, 1), (2, 2))
    starting_stitches = forms.IntegerField(
        label="starting stitch-count",
        min_value=1,
    )

    ending_stitches = forms.IntegerField(
        label="ending stitch-count",
        min_value=1,
    )

    total_rows = forms.IntegerField(
        label="rows available for shaping",
        min_value=1,
    )

    stitches_per_shaping_row = forms.TypedChoiceField(
        label="stitches increased/decreased on each shaping row",
        choices=stitches_per_shaping_row_options,
        coerce=int,
    )


class ButtonSpacingCalculatorForm(BaseCalculatorForm):

    HELP_TEXT = {
        "number_of_stitches": "Total number of stitches in the buttonhole section of the band. This will be the "
        "entire band for crew neck cardigans, e.g., but only the stitches before the neck "
        "shaping for a v-neck cardigan.",
        "number_of_buttons": "the number of buttons you'd like to place",
        "stitches_per_buttonhole": "the number of stitches used in the making of each buttonhole",
    }

    stitches_per_buttonhole_options = (
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5),
    )
    number_of_stitches = forms.IntegerField(
        label="total stitches in button band",
        min_value=1,
    )

    number_of_buttons = forms.IntegerField(
        label="number of buttons",
        min_value=1,
    )

    stitches_per_buttonhole = forms.TypedChoiceField(
        label="stitches in each buttonhole",
        choices=stitches_per_buttonhole_options,
        coerce=int,
    )


class ArmcapShapingCalculatorForm(BaseCalculatorForm):

    HELP_TEXT = {
        "stitch_count": "your stitch gauge over 4'' (10 cm)",
        "row_count": "your row gauge over 4'' (10 cm)",
        "first_armhole_bindoffs": "the number of stitches bound-off, on each side, at the start of the armhole shaping",
        "second_armhole_bindoffs": "the number of stitches bound-off, on each side, in second round of bindoffs - may be 0",
        "armhole_decreases": "the number of armhole decrease rows are worked every RS row",
        "armhole_depth_value": "total depth of the armhole, from start of bind-offs to shoulder",
        "armhole_depth_units": "unit used to specify armhole depth",
        "bicep_stitches": "total number of stitches in the bicep of your sleeve",
    }

    stitch_count = forms.FloatField(
        label='stitches per 4" (10cm)',
        min_value=1.0,
    )

    row_count = forms.FloatField(
        label='rows per 4" (10cm)',
        min_value=1.0,
    )

    first_armhole_bindoffs = forms.IntegerField(
        label="stitches bound off in initial armhole bindoffs (each side)", min_value=1
    )

    second_armhole_bindoffs = forms.IntegerField(
        label="additional stitches bound off in armhole (each side)", min_value=0
    )

    armhole_decreases = forms.IntegerField(
        label="number of every RS row decreases in armhole shaping", min_value=0
    )

    armhole_depth_value = forms.FloatField(label="total armhole depth", min_value=1)

    _INCHES = "inches"
    _CM = "cm"
    FOUR_INCHES = 4.0

    _armhole_depth_unit_choices = ((_INCHES, _INCHES), (_CM, _CM))

    armhole_depth_units = forms.ChoiceField(
        label="armhole depth units", choices=_armhole_depth_unit_choices
    )

    bicep_stitches = forms.IntegerField(
        label="number of stitches in bicep of sleeve", min_value=1
    )

    def get_gauge(self):
        cleaned_data = self.cleaned_data
        stitch_gauge = cleaned_data["stitch_count"] / self.FOUR_INCHES
        row_gauge = cleaned_data["row_count"] / self.FOUR_INCHES
        gauge = Gauge(stitch_gauge, row_gauge)
        return gauge

    def get_armhole_shaping(self):
        cleaned_data = self.cleaned_data
        armhole_x = cleaned_data["first_armhole_bindoffs"]
        armhole_y = cleaned_data["second_armhole_bindoffs"]
        armhole_z = cleaned_data["armhole_decreases"]
        return (armhole_x, armhole_y, armhole_z)

    def get_armhole_depth_in_inches(self):
        cleaned_data = self.cleaned_data
        if cleaned_data["armhole_depth_units"] == self._INCHES:
            return cleaned_data["armhole_depth_value"]
        else:
            depth_in_cm = cleaned_data["armhole_depth_value"]
            return cm_to_inches(depth_in_cm)

    def get_bicep_stitches(self):
        return self.cleaned_data["bicep_stitches"]


class PickupCalculatorForm(BaseCalculatorForm):

    HELP_TEXT = {}

    MAX_STITCH_GAUGE = 52.0
    MIN_STITCH_GAUGE = 4.0
    stitch_gauge = forms.FloatField(
        label='stitches per 4" (10cm)',
        min_value=MIN_STITCH_GAUGE,
        max_value=MAX_STITCH_GAUGE,
    )

    MAX_ROW_GAUGE = 64.0
    MIN_ROW_GAUGE = 4.0
    row_gauge = forms.FloatField(
        label='rows per 4" (10cm)',
        min_value=MIN_ROW_GAUGE,
        max_value=MAX_ROW_GAUGE,
    )

    EDGE_INPUT_INCHES = "INCHES"
    EDGE_INPUT_CMS = "CMS"
    EDGE_INPUT_COUNT = "COUNT"
    EDGE_INPUT_OPTIONS = [
        (EDGE_INPUT_INCHES, "the edge's length in inches"),
        (EDGE_INPUT_CMS, "the edge's length in cm"),
        (EDGE_INPUT_COUNT, "the number of rows along the edge"),
    ]
    edge_input_type = forms.ChoiceField(
        label="I know...",
        choices=EDGE_INPUT_OPTIONS,
        initial=EDGE_INPUT_INCHES,  # If you ever change this, you should also change which field start (in)visible
        # See __init__
    )

    MAX_EDGE_ROWS = 1000
    MIN_EDGE_ROWS = 10
    rows_on_edge = forms.IntegerField(
        label="number of rows on edge",
        required=False,
        min_value=MIN_EDGE_ROWS,
        max_value=MAX_EDGE_ROWS,
    )

    MAX_EDGE_INCHES = 1000
    MIN_EDGE_INCHES = 0.5
    edge_in_inches = forms.FloatField(
        label="length of edge (in inches)",
        required=False,
        min_value=MIN_EDGE_INCHES,
        max_value=MAX_EDGE_INCHES,
    )

    MAX_EDGE_CMS = 2500
    MIN_EDGE_CMS = 1.0
    edge_in_cms = forms.FloatField(
        label="length of edge (in cm)",
        required=False,
        min_value=MIN_EDGE_CMS,
        max_value=MAX_EDGE_CMS,
    )

    RANGES = {
        "rows_on_edge": (MIN_EDGE_ROWS, MAX_EDGE_ROWS),
        "edge_in_inches": (MIN_EDGE_INCHES, MAX_EDGE_INCHES),
        "edge_in_cms": (MIN_EDGE_CMS, MAX_EDGE_CMS),
    }

    def clean(self):
        super(PickupCalculatorForm, self).clean()

        if "edge_input_type" in self.cleaned_data:

            # First, a helper function
            def _test_field_present(field_name):
                # Remember-- clean() gets called even if there are problems with field-level
                # validation. Hence, we can't assume that cleaned_data has values for the
                # relevant fields.
                if not self.cleaned_data.get(field_name, False) and not (
                    field_name in self.errors
                ):
                    self.add_error(
                        field_name,
                        ValidationError("Please enter a value", code="required"),
                    )  # code taken from Django source
                else:
                    # Let the field-level validation ensure that the value is a number in range
                    pass

            # Now, the validation
            edge_input_type = self.cleaned_data["edge_input_type"]
            if edge_input_type == self.EDGE_INPUT_COUNT:
                # We don't care about errors in the other two input types
                self.errors.pop("edge_in_inches", None)
                self.errors.pop("edge_in_cms", None)
                _test_field_present("rows_on_edge")
            elif edge_input_type == self.EDGE_INPUT_INCHES:
                self.errors.pop("rows_on_edge", None)
                self.errors.pop("edge_in_cms", None)
                _test_field_present("edge_in_inches")
            else:
                assert edge_input_type == self.EDGE_INPUT_CMS
                self.errors.pop("edge_in_inches", None)
                self.errors.pop("rows_on_edge", None)
                _test_field_present("edge_in_cms")

    def get_stitch_gauge(self):
        return self.cleaned_data["stitch_gauge"]

    def get_row_gauge(self):
        return self.cleaned_data["row_gauge"]

    def get_rows_on_edge(self):
        edge_length_type = self.cleaned_data["edge_input_type"]
        if edge_length_type == self.EDGE_INPUT_COUNT:
            return self.cleaned_data["rows_on_edge"]
        else:
            gauge = self.get_row_gauge()
            if edge_length_type == self.EDGE_INPUT_INCHES:
                inches = self.cleaned_data["edge_in_inches"]
                row_count_float = (inches / 4.0) * gauge
            else:
                assert edge_length_type == self.EDGE_INPUT_CMS
                cms = self.cleaned_data["edge_in_cms"]
                row_count_float = (cms / 10.0) * gauge
            row_count = round(row_count_float, ROUND_ANY_DIRECTION)
            return int(row_count)

    def __init__(self, *args, **kwargs):
        super(BaseCalculatorForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.label_class = "col-xs-12 col-sm-4"
        self.helper.field_class = "col-xs-12 col-sm-4"
        self.helper.form_show_errors = True
        self.helper.layout = Layout(
            "stitch_gauge",
            "row_gauge",
            "edge_input_type",
            Div(
                "rows_on_edge",
                style="display:none;",  # This assumes that the initial edge_input_type choice is inches
                css_id="id_rows_on_edge_row",
            ),
            Div("edge_in_inches", css_id="id_edge_in_inches_row"),
            Div(
                "edge_in_cms",
                style="display:none;",  # This assumes that the initial edge_input_type choice is inches
                css_id="id_edge_in_cms_row",
            ),
        )
        self.helper.add_input(
            Submit("submit-btn", "Compute", css_class="btn-customfit-action")
        )
        self.add_help_text(self.HELP_TEXT)


class GaugeCalculatorForm(BaseCalculatorForm):

    HELP_TEXT = {}

    INCHES = "INCHES"
    MAX_INCHES = 74.0
    MIN_INCHES = 1.0

    CMS = "CMS"
    MAX_CM = 183.0
    MIN_CM = 2.5

    LENGTH_OPTIONS = [
        (INCHES, "inches"),
        (CMS, "cm"),
    ]

    ROWS = "ROWS"
    STITCHES = "STITCHES"

    MIN_COUNT = 2.0
    MAX_COUNT = 1000.0

    COUNT_OPTIONS = [
        (ROWS, "rows"),
        (STITCHES, "stitches"),
    ]

    ROWS_PER_INCH = "ROWS_PER_INCH"
    ROWS_PER_FOUR_INCHES = "ROWS_PER_FOUR_INCHES"
    ROWS_PER_10CMS = "ROWS_PER_10CM"
    STITCHES_PER_INCH = "STITCHES_PER_INCH"
    STITCHES_PER_FOUR_INCHES = "STITCHES_PER_FOUR_INCHES"
    STITCHES_PER_10CMS = "STITCHES_PER_10CM"

    MAX_COUNT_PER_INCH = 13.0
    MIN_COUNT_PER_INCH = 2.0

    MAX_COUNT_PER_FOUR_INCHES = 52.0
    MIN_COUNT_PER_FOUR_INCHES = 7.5

    MAX_COUNT_PER_10CM = 52.0
    MIN_COUNT_PER_10CM = 7.5

    GAUGE_OPTIONS = [
        (ROWS_PER_INCH, "rows per inch"),
        (ROWS_PER_FOUR_INCHES, "rows per 4 inches"),
        (ROWS_PER_10CMS, "rows per 10cm"),
        (STITCHES_PER_INCH, "stitches per inch"),
        (STITCHES_PER_FOUR_INCHES, "stitches per 4 inches"),
        (STITCHES_PER_10CMS, "stitches per 10cm"),
    ]

    RANGES = {
        ROWS_PER_INCH: (MIN_COUNT_PER_INCH, MAX_COUNT_PER_INCH),
        ROWS_PER_FOUR_INCHES: (MIN_COUNT_PER_FOUR_INCHES, MAX_COUNT_PER_FOUR_INCHES),
        ROWS_PER_10CMS: (MIN_COUNT_PER_10CM, MAX_COUNT_PER_10CM),
        STITCHES_PER_INCH: (MIN_COUNT_PER_INCH, MAX_COUNT_PER_INCH),
        STITCHES_PER_FOUR_INCHES: (
            MIN_COUNT_PER_FOUR_INCHES,
            MAX_COUNT_PER_FOUR_INCHES,
        ),
        STITCHES_PER_10CMS: (MIN_COUNT_PER_10CM, MAX_COUNT_PER_10CM),
        ROWS: (MIN_COUNT, MAX_COUNT),
        STITCHES: (MIN_COUNT, MAX_COUNT),
        INCHES: (MIN_INCHES, MAX_INCHES),
        CMS: (MIN_CM, MAX_CM),
    }

    LENGTH = "SIZE"
    GAUGE = "GAUGE"
    COUNT = "COUNT"
    OUTPUT_OPTIONS = [(LENGTH, "size"), (GAUGE, "gauge"), (COUNT, "count")]

    output_type_requested = forms.ChoiceField(
        choices=OUTPUT_OPTIONS,
        # Note: if you ever change this, you should also change the field-row start out with
        # hidden (display:none;) in __init__.
        initial=LENGTH,
    )

    length_value = forms.FloatField(
        # No validators-- see clean()
        required=False
    )

    length_type = forms.ChoiceField(
        choices=LENGTH_OPTIONS, initial=INCHES, required=False
    )

    count_value = forms.FloatField(
        # No validators-- see clean()
        required=False
    )

    count_type = forms.ChoiceField(
        choices=COUNT_OPTIONS, initial=STITCHES, required=False
    )

    gauge_value = forms.FloatField(
        # No validators-- see clean()
        required=False
    )

    gauge_type = forms.ChoiceField(
        choices=GAUGE_OPTIONS, initial=STITCHES_PER_INCH, required=False
    )

    def __init__(self, *args, **kwargs):
        super(BaseCalculatorForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_class = "form-horizontal"
        self.helper.form_show_labels = False
        self.helper.field_class = "col-sm-5 col-xs-12"
        self.helper.field_template = (
            "knitting_calculators/gauge_crispy_field_template.html"
        )
        self.helper.layout = Layout(
            Div(
                Div(HTML("I want to know my:"), css_class="col-sm-2 col-xs-12"),
                Field("output_type_requested", css_id="output_type_selector"),
                css_class="form-group row",
            ),
            Div(
                Div(HTML("known length:"), css_class="col-sm-2 col-xs-12"),
                "length_value",
                "length_type",
                css_class="form-group row",
                style="display:none;",  # This assumes that the form starts out with 'LENGTH' as the initial choice
                css_id="length_row",
            ),
            Div(
                Div(HTML("known count:"), css_class="col-sm-2 col-xs-12"),
                "count_value",
                "count_type",
                css_class="form-group row",
                css_id="count_row",
            ),
            Div(
                Div(HTML("known gauge:"), css_class="col-sm-2 col-xs-12"),
                "gauge_value",
                "gauge_type",
                css_class="form-group row",
                css_id="gauge_row",
            ),
        )
        self.helper.add_input(
            Submit("submit-btn", "Compute", css_class="btn-customfit-action")
        )
        self.add_help_text(self.HELP_TEXT)

    def get_output_type(self):
        return self.cleaned_data["output_type_requested"]

    def _get_gauge_type(self):
        return self.cleaned_data["gauge_type"]

    def _get_gauge_value(self):
        return self.cleaned_data["gauge_value"]

    def _get_count_type(self):
        return self.cleaned_data["count_type"]

    def _get_count_value(self):
        return self.cleaned_data["count_value"]

    def _get_length_type(self):
        return self.cleaned_data["length_type"]

    def _get_length_value(self):
        return self.cleaned_data["length_value"]

    def clean(self):

        super(GaugeCalculatorForm, self).clean()

        # Form validation is a little tricky. We don't want to validate the 'length' fields
        # when being asked to compute a length, for example. And when we do want to validate
        # the length input, the legal values depend on whether it's supposed to be inches or
        # cms. So, we need to move validation from field-level to form level.

        # First, a helper function
        def _test_field_in_range(val_field_name, type_field_name):
            # Remember-- clean() gets called even if there are problems with field-level
            # validation. Hence, we can't assume that cleaned_data has values for the
            # relevant fields.

            # For this next case, since it's a 'choice' field, we can assume that
            # *if* cleaned_data has an entry for the field, it's either "" or a valid choice
            if not self.cleaned_data.get(type_field_name, ""):
                self.add_error(
                    type_field_name,
                    ValidationError("Please choose an option", code="required"),
                )  # code taken from Django source

            if (val_field_name not in self.cleaned_data) and (
                val_field_name not in self.errors
            ):
                self.add_error(
                    val_field_name,
                    ValidationError("Please enter a value", code="required"),
                )  # code taken from Django source

            if (val_field_name in self.cleaned_data) and (
                type_field_name in self.cleaned_data
            ):
                field_val = self.cleaned_data[val_field_name]
                field_type = self.cleaned_data[type_field_name]

                (min_val, max_val) = self.RANGES[field_type]

                if field_val is None:
                    self.add_error(val_field_name, ValidationError("Enter a number."))

                elif not (min_val <= field_val <= max_val):
                    self.add_error(
                        val_field_name,
                        ValidationError(
                            "Please enter a number between %(min_value)s and %(max_value)s.",
                            params={"min_value": min_val, "max_value": max_val},
                            code="value_out_of_range",
                        ),
                    )

        # We can't assume that the user has selected an output type. If they don't, there will be
        # a field-level error raised, but this function gets called anyway. So we need to gracefully handle
        # its absence
        if "output_type_requested" in self.cleaned_data:
            output_requested = self.get_output_type()

            # First, let's check that values are in valid ranges

            if output_requested == self.LENGTH:
                # validate the length fields
                self.errors.pop("length_value", None)
                self.errors.pop("length_type", None)
                _test_field_in_range("gauge_value", "gauge_type")
                _test_field_in_range("count_value", "count_type")

            elif output_requested == self.GAUGE:
                # validate the gauge fields
                self.errors.pop("gauge_value", None)
                self.errors.pop("gauge_type", None)
                _test_field_in_range("length_value", "length_type")
                _test_field_in_range("count_value", "count_type")

            else:
                assert output_requested == self.COUNT
                # validate the count fields
                self.errors.pop("count_value", None)
                self.errors.pop("count_type", None)
                _test_field_in_range("gauge_value", "gauge_type")
                _test_field_in_range("length_value", "length_type")

            # Now, let's check that the user was consistent in their units.

            STITCH_ROW_MISMATCH_MESSAGE = (
                "Please choose either stitches or rows (but not both)"
            )
            INCH_CM_MISMATCH_MESSAGE = (
                "Please choose either inches or cm (but not both)"
            )
            if output_requested == self.LENGTH:

                if ("count_type" in self.cleaned_data) and (
                    "gauge_type" in self.cleaned_data
                ):
                    if self._get_count_type() == self.STITCHES:
                        if self._get_gauge_type() not in [
                            self.STITCHES_PER_10CMS,
                            self.STITCHES_PER_INCH,
                            self.STITCHES_PER_FOUR_INCHES,
                        ]:
                            self.add_error(
                                None,
                                ValidationError(
                                    STITCH_ROW_MISMATCH_MESSAGE, code="unit_mismatch"
                                ),
                            )
                    else:
                        assert self._get_count_type() == self.ROWS
                        if self._get_gauge_type() not in [
                            self.ROWS_PER_10CMS,
                            self.ROWS_PER_INCH,
                            self.ROWS_PER_FOUR_INCHES,
                        ]:
                            self.add_error(
                                None,
                                ValidationError(
                                    STITCH_ROW_MISMATCH_MESSAGE, code="unit_mismatch"
                                ),
                            )

            elif output_requested == self.COUNT:

                # Mathematically, we can easily accept one input in CM and the other in inches. But
                # a mismatch almost certainly indicates an error on the user's part
                if ("length_type" in self.cleaned_data) and (
                    "gauge_type" in self.cleaned_data
                ):
                    if self._get_length_type() == self.INCHES:
                        if self._get_gauge_type() not in [
                            self.ROWS_PER_INCH,
                            self.ROWS_PER_FOUR_INCHES,
                            self.STITCHES_PER_INCH,
                            self.STITCHES_PER_FOUR_INCHES,
                        ]:
                            self.add_error(
                                None,
                                ValidationError(
                                    INCH_CM_MISMATCH_MESSAGE, code="unit_mismatch"
                                ),
                            )
                    else:
                        assert self._get_length_type() == self.CMS
                        if self._get_gauge_type() not in [
                            self.ROWS_PER_10CMS,
                            self.STITCHES_PER_10CMS,
                        ]:
                            self.add_error(
                                None,
                                ValidationError(
                                    INCH_CM_MISMATCH_MESSAGE, code="unit_mismatch"
                                ),
                            )

            else:
                assert output_requested == self.GAUGE
                # All combinations are valid
                pass

    def get_gauge_per_inch(self):
        gauge_type = self._get_gauge_type()

        if gauge_type in [self.STITCHES_PER_INCH, self.ROWS_PER_INCH]:
            return self._get_gauge_value()
        elif gauge_type in [self.STITCHES_PER_10CMS, self.ROWS_PER_10CMS]:
            return inches_to_cm(self._get_gauge_value() / 10.0)
        else:
            assert gauge_type in [
                self.STITCHES_PER_FOUR_INCHES,
                self.ROWS_PER_FOUR_INCHES,
            ]
            return self._get_gauge_value() / 4.0

    def get_length_in_inches(self):
        length_type = self._get_length_type()

        if length_type == self.INCHES:
            return self._get_length_value()
        else:
            assert length_type == self.CMS
            return cm_to_inches(self._get_length_value())

    def get_count(self):
        return self._get_count_value()

    def get_count_units(self):
        output_type = self.get_output_type()
        if output_type == self.LENGTH:
            return None
        elif output_type == self.COUNT:
            if self._get_gauge_type() in [
                self.STITCHES_PER_10CMS,
                self.STITCHES_PER_INCH,
                self.STITCHES_PER_FOUR_INCHES,
            ]:
                return self.STITCHES
            else:
                assert self._get_gauge_type() in [
                    self.ROWS_PER_10CMS,
                    self.ROWS_PER_INCH,
                    self.ROWS_PER_FOUR_INCHES,
                ]
                return self.ROWS
        else:
            assert output_type == self.GAUGE
            return self._get_count_type()

    def calculate_result(self):
        to_find = self.get_output_type()

        if to_find == self.COUNT:
            rate = self.get_gauge_per_inch()
            length = self.get_length_in_inches()
            return rate * length
        elif to_find == self.LENGTH:
            rate = self.get_gauge_per_inch()
            count = self.get_count()
            return count / rate
        else:
            assert to_find == self.GAUGE
            length = self.get_length_in_inches()
            count = self.get_count()
            return count / length
