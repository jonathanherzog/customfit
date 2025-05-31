var $j = jQuery.noConflict();

// Warn users about potentially unworkable (but acceptable-to-the-database)
// inputs.
$j(document).ready(function() {

    var bust_circ_warning = $j('#bust_circ_warning');
    var bust_circ_field = $j('#id_bust_circ');

    var cross_chest_warning = $j('#cross_chest_warning');
    var cross_chest_input = $j('#id_cross_chest_distance');
    var upper_torso_input = $j('#id_upper_torso_circ');

    var armpit_to_waist_warning = $j('#armpit_to_waist_warning');
    var armpit_to_waist_input = $j('#id_armpit_to_waist')
    var armpit_to_high_hip_input = $j('#id_armpit_to_high_hip')
    var armpit_to_med_hip_input = $j('#id_armpit_to_med_hip')

    // If they're using cm, we'll need to convert to inches before
    // checking validity. Read the units box appended to relevant
    // fields to determine units.
    var conversion = 1;
    var unit_holder = cross_chest_input.siblings('.input-group-addon');
    if ( unit_holder.html().indexOf('cm') >= 0 ) {
        conversion = 2.54;
    }

    /* Cross chest validation
    --------------------------------------------------------------------------- */

    function check_cross_chest () {
        // As long as these values exist, we do not need to confirm that
        // they are valid numbers, because the Bootstrap form has
        // already done that for us. parseFloat will not break if the
        // fields are blank.
        var cross_chest_number = parseFloat(cross_chest_input.val());
        var upper_torso_number = parseFloat(upper_torso_input.val());
        var show_warning = false;

        if (upper_torso_number > 0) {
            if ( cross_chest_number > ( upper_torso_number / 2 ) - 2.5) {
                show_warning = true;
            }
        }

        if (cross_chest_number/conversion >= 17) {
            show_warning = true;
        }

        if (show_warning) {
            cross_chest_warning.show();
        } else {
            cross_chest_warning.hide();
        }
    }

    // We need to check any time relevant inputs change, because the gauge warnings
    // for cross-chest are based on the relationship between inputs.
    cross_chest_input.blur(function () {
        check_cross_chest();
    });

    upper_torso_input.blur(function () {
        check_cross_chest();
    });

    /* Bust circ validation
    --------------------------------------------------------------------------- */

    bust_circ_field.blur(function () {
      var bust_circ = parseFloat(bust_circ_field.val());

      // Use exact same numbers displayed in warning, based on detected
      // unit preference, rather than converting inches to cm and risking
      // showing the warning when their input value is not covered by
      // the warning.
      if ( conversion == 2.54 ) {
        var minimum = 59;
      } else {
        var minimum = 23;
      }


      if ( bust_circ < minimum ) {
        bust_circ_warning.show();
      } else {
        bust_circ_warning.hide();
      }
    });


    /* Armhole-to-waist validation
    --------------------------------------------------------------------------- */
    function check_armhole_to_waist () {
        // As long as these values exist, we do not need to confirm that
        // they are valid numbers, because the Bootstrap form has
        // already done that for us. parseFloat will not break if the
        // fields are blank.
        var armpit_to_waist_number = parseFloat(armpit_to_waist_input.val());
        var armpit_to_high_hip_number = parseFloat(armpit_to_high_hip_input.val());
        var armpit_to_med_hip_number = parseFloat(armpit_to_med_hip_input.val());

        var show_warning = false;
        var highest_hip_number

        if ( armpit_to_waist_number > 0 ) {
            // armpit-to-waist is defined

            // Get the larger of the two relevant hem-lengths.
            // Note that we don't need to go below mid-hip as mid-hip is defined
            if (armpit_to_high_hip_number > 0) {
                highest_hip_number = armpit_to_high_hip_number;
            } else {
                highest_hip_number = armpit_to_med_hip_number;
            }

            // Decide whether to show the warning
            if (armpit_to_waist_number > (highest_hip_number - 3)) {
                show_warning = true;
            }
        }


        if (show_warning) {
            armpit_to_waist_warning.show();
        } else {
            armpit_to_waist_warning.hide();
        }
    }

    // We need to check any time relevant inputs change, because the gauge warnings
    // for cross-chest are based on the relationship between inputs.
    armpit_to_waist_input.blur(function () {
        check_armhole_to_waist();
    });

    armpit_to_high_hip_input.blur(function () {
        check_armhole_to_waist();
    });

    armpit_to_med_hip_input.blur(function () {
        check_armhole_to_waist();
    });



    /* Initial state
    --------------------------------------------------------------------------- */

    bust_circ_warning.hide();
    armpit_to_waist_warning.hide();
    cross_chest_warning.hide();
});
