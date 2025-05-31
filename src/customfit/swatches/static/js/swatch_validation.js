var $j = jQuery.noConflict();

$j(document).ready(function() {
    var sts_warning_tiny = $j('#sts_warning_tiny');
    var sts_warning_big = $j('#sts_warning_big');
    var rows_warning_tiny = $j('#rows_warning_tiny');
    var rows_warning_big = $j('#rows_warning_big');

    var sts_number_field = $j('#id_stitches_number');

    var sts_length_field = $j('#id_stitches_length');
    var rows_number_field = $j('#id_rows_number');
    var rows_length_field = $j('#id_rows_length');

    var sts_inputs = sts_number_field.add(sts_length_field)
    var rows_inputs = rows_number_field.add(rows_length_field);

    // If they're using cm, convert to inches before checking validity.
    // Read the units box appended to relevant fields to determine
    // units.
    var conversion = 1;
    var unit_holder = $j('#id_stitches_length').siblings('.input-group-addon');
    if ( unit_holder.html().indexOf('cm') >= 0 ) {
        conversion = 2.54;
    }

    // We need to check any time inputs change, because the gauge warnings
    // are based on the relationship between inputs.
    sts_inputs.blur(function () {

        // As long as these values exist, we do not need to confirm that
        // they are valid numbers, because the Bootstrap form has
        // already done that for us.
        // We do not need to worry about the case where a length is zero;
        // dividing by this zero will return Infinity, which will trigger
        // the associated warning box. Subsequent form validation will
        // reject the zero value.
        var sts_number = sts_number_field.val();
        var sts_length = sts_length_field.val();

        if (sts_number && sts_length ) {

            var check_sts = parseFloat(sts_number)*conversion/parseFloat(sts_length);
            console.log(check_sts);
            if ( check_sts > 10 ) {
                sts_warning_tiny.show();
                sts_warning_big.hide();
            } else if ( check_sts < 2 ) {
                sts_warning_tiny.hide();
                sts_warning_big.show();
            } else {
                sts_warning_tiny.hide();
                sts_warning_big.hide();                
            }
        }
    });

    rows_inputs.blur(function () {
        var rows_number = rows_number_field.val();
        var rows_length = rows_length_field.val();

        if ( rows_number && rows_length ) {

            var check_rows = parseFloat(rows_number)*conversion/parseFloat(rows_length);

            if ( check_rows > 15 ) {
                rows_warning_tiny.show()
                rows_warning_big.hide()
            } else if ( check_rows < 3 ) {
                rows_warning_tiny.hide()
                rows_warning_big.show()
            } else {
                rows_warning_tiny.hide()
                rows_warning_big.hide()
            }
        }

    });
});
