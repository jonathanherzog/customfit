    // Show/hide measurement help when people click on measurement names.
    var $j = jQuery.noConflict();
    var labels = $j('label');

    $j(document).ready(function() {
      labels.click(function() {
        var help_text = $j(this).siblings('.controls').children('.help-block');
        help_text.toggle();
      });
    });
