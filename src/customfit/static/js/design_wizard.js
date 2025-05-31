/*
 * Reveal the initially hidden neckline_depth_orientation field on the Neckline
 * step of Design Wizard.
 * This field is initially hidden because it was found to be confusing for inexperienced
 * knitters
 */

$j = jQuery.noConflict();

function showNecklineOptionFields() {
    // animate revealing the field, to make it easier for user to see what's
    // happening
    customfit.getField('neckline_depth_orientation').show(500);
}

$j(document).ready(function() {
    $j('#showNecklineOptions').click(function(){
	showNecklineOptionFields();
	return false;
    });
    $j('#showNecklineOptionsHelp').click(function(){
	showNecklineOptionFields();
	return false;
    });
});
