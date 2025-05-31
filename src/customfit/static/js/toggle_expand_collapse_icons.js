var $j = jQuery.noConflict();

$j(document).ready(function() {
    $j("button[data-toggle='collapse']").click(function() {
        $j(this).children("i").toggleClass("icon-plus");
        $j(this).children("i").toggleClass("icon-minus");
    });
});