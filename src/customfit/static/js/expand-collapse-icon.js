$j = jQuery.noConflict();
$j(document).ready(function(){
    $j('.collapse-toggle').click(function() {
        // when people click on the expand/collapse buttons, 
        // expand or collapse the sibling paragraph and swap the buttons
        $j(this).siblings('button').toggleClass('visible');
        $j(this).toggleClass('visible');
        $j(this).siblings('.long').toggleClass('expanded');
    });

    $j('.collapse-toggle.show-all').each(function() {
        // on page ready, show all expander buttons next to paragraphs
        // with overflow (but ONLY next to paragraphs with overflow)
        var local_list = $j(this).siblings('.long')[0];
        if (local_list.offsetWidth < local_list.scrollWidth) {
            $j(this).addClass('visible');
            $j(this).siblings('a').addClass('pull-right');
        }
    });
});
