// hijack a link with class "hijax" to show its content in a lightbox instead
// allows for ajaxy presentation of things like download links in a way that
// degrades gracefully for non-js users
var $j = jQuery.noConflict();

$j(document).ready(function() {
    $j("#content").on("click", "a.hijax", function(event) {
        event.preventDefault();
		$j("#lightbox").load($j(this).attr("href") + " #lightbox_content", function() {
            // position div vertically relative to top of viewport, to ensure visibility
            // regardless of where on the page the user clicked to activate it
            var marginTop = window.pageYOffset;
            $j('#lightbox_expandable').css({'margin-top': marginTop, 'padding-top': '35px'});
		});
		
		// replaces the generic "details" lightbox header with page title
		$j("#lightbox_expandable .modal-header h3").load($j(this).attr("href") + " h2");
		
		// fade-out rest of page elements on expand
		$j('#content, .navbar').css({"opacity": "0.07"});
		$j('#lightbox_expandable').css({'position': 'absolute'});
		$j('#lightbox_expandable').fadeTo("slow", 1);
	});
	
	// fade-in normal page elements on collapse
	$j('#about_collapser').on("click", function(){
		$j('#content, .navbar').fadeTo("slow", 1);
		$j('#lightbox_expandable').css({"display": "none"});
	});
	
});