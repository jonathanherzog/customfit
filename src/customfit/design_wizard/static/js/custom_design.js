// Some sweater design options are only available if the user has chosen particular
// design elements (e.g. button bands are only available for cardigans). This script
// manages the visibility of those options.
var $j = jQuery.noConflict();

$j(document).ready(function() {
    // Set up variables -------------------------------------------------------
    var garment_type_select = $j('#div_id_garment_type_body label');
    var button_band_options = $j('#button_band_options');

    // Neck
    var neck_edge_height = $j('#div_id_neck_edging_height');
    var neck_edge_stitch = $j('#div_id_neck_edging_stitch');
    var neck_choices = $j('#div_id_neckline_style');
    var vee_neck = $j('#id_neckline_style_1');

    // Sleeve & armhole
    var garment_sleeves_select = $j('#div_id_garment_type_sleeves label');
    var sleeve_details = $j('#sleeve_details');
    var sleeve_length_options = $j('#div_id_sleeve_length');
    var armhole_details = $j('#armhole_details');
    var armhole_header = $j('.armhole_header');
    var sleeve_header = $j('.sleeve_header');
    var sleeve_shape_select = $j('#div_id_sleeve_shape label');
    var bell_options = $j('#div_id_bell_type');
    var sleeve_shape_options = $j('#div_id_sleeve_shape');
    var sleeve_length_select = $j('#div_id_sleeve_length label');
    // Done with variable declaration ------------------------------------------


    // Show/hide button band details depending on whether it is a cardigan.
    garment_type_select.click(function() {
        // We have to grab this here rather than testing for garment_type
        // inside the function, because in that latter case we end up
        // grabbing the value attribute at the wrong time, so it has
        // the wrong value.
        var latest_garment_type = $j(this).children('input').attr('value');
        toggle_neckband(latest_garment_type);
        if ( latest_garment_type == 'cardigan' ) {
            button_band_options.show();
        } else {
            button_band_options.hide();
        }
    });


    // Remove neckline edging and height for v-neck cardigans,
    // as these options simply continue the buttonband.
    neck_choices.click(function () {
        var garment_type = $j('#div_id_garment_type_body label.active input').val();
        toggle_neckband(garment_type);
    });

    function toggle_neckband (garment_type) {

        if ( ( garment_type == 'cardigan' ) && ( vee_neck.prop('checked') ) ) {
            neck_edge_height.hide();
            neck_edge_stitch.hide();                
        } else {
            neck_edge_height.show();
            neck_edge_stitch.show();
        }
    }

    // Show sleeves or armholes depending on whether it is a vest.
    garment_sleeves_select.click(function() {
        var garment_sleeves = $j(this).children('input').attr('value');
        if ( garment_sleeves == 'sleeved' ) {
            sleeve_details.show();
            // It's important to toggle only the visibility and not the display
            // of this item because it needs to take up width in order to force
            // the armhole options to the right when sleeve options are not shown.
            sleeve_length_options.removeClass('invisible');
            armhole_details.hide();
            sleeve_header.show();
            armhole_header.hide();
        } else {
            sleeve_details.hide();
            sleeve_length_options.addClass('invisible');
            armhole_details.show();
            sleeve_header.hide();
            armhole_header.show();
        }
    });

    // Show/hide bell options depending on whether it has a bell sleeve.
    sleeve_shape_select.click(function() {
        var sleeve_shape = $j(this).children('input').attr('value');
        if ( sleeve_shape == 'SLEEVE_BELL' ) {
            bell_options.show();
        } else {
            bell_options.hide();
        }
    });

    // Show/hide sleeve shape depending on whether it is short sleeved.
    sleeve_length_select.click(function() {
        var sleeve_length = $j(this).children('input').attr('value');
        if ( sleeve_length == 'SLEEVE_SHORT' ) {
            sleeve_shape_options.hide();
            bell_options.hide();
        } else {
            sleeve_shape_options.show();
            if (sleeve_shape_options.find('.btn:last-child').hasClass('active')) {
                bell_options.show();                
            }
        }
    });

    // Initialize state.
    // We need to check to see if the cardigan or vest options are checked, because
    // they might be if the form is being returned with errors post-submission;
    // in that case, we need to show the corresponding form elements. Otherwise,
    // the defaults are correct.
    if ( $j('input[value="cardigan"]').prop('checked') ) {
        button_band_options.show();
        toggle_neckband('cardigan');
    } else {
        button_band_options.hide();        
        toggle_neckband(null);
    }

    if ( $j('input[value="vest"]').prop('checked') ) {
        sleeve_details.hide();
        sleeve_length_options.addClass('invisible');
        armhole_details.show();
        sleeve_header.hide();
        armhole_header.show();
    } else {
        sleeve_details.show();
        sleeve_length_options.removeClass('invisible');
        armhole_details.hide();
        sleeve_header.show();
        armhole_header.hide();
    }

    bell_options.hide();

    // When the form is being returned with errors, input boxes may be checked;
    // we need to be sure that parent labels are styled correctly to show as
    // pressed buttons or users won't see that we've remembered their choices.
    var selected_inputs = $j('input:checked');
    selected_inputs.parent('label.btn').addClass('active');


    // Users should be able to select an option by clicking on its image, not just
    // its label - that is, clicking an image should activate its associated input
    // and fire any click events bound to those inputs.
    // However, this should only work when the group hasn't been disabled (e.g.
    // because a body has a minimal set of measurements and therefore cannot
    // select alternate hem or sleeve lengths).
    $j('.control-group:not(.disabled) img').click(function() {
        var label = $j(this).siblings('label');
        console.log(label.attr('disabled'));
        if (!label.attr('disabled')) {
            label.trigger('click');
        }
    });
});
