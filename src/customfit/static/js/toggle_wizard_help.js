var $j = jQuery.noConflict();

$j(document).ready(function() {
    $j('label.control-label').each(function() {
        if($j(this).parents('.control-group').find('.help-block').length > 0) {
            $j(this).addClass('has-help');
        }
    });

    $j('label.control-label').click(function() {
        $j(this).parents('.control-group').find('.help-block').toggle();
    });
    
	// $j("[data-toggle=tooltip]").tooltip();
});


