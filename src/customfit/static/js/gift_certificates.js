var $j = jQuery.noConflict();

$j(document).ready(function() {
    var num_patterns = $j('#id_quantity_purchased');
    var display_total = $j('#display_total .price');
    var bonus_sweaters = $j('#display_total .bonus');
    var intRegex = /^\d+$/; // make sure they've entered an integer # of patterns
    num_patterns.blur(function() {
        var patterns = num_patterns.val();
        if(intRegex.test(patterns) && patterns > 0) {
            total_amount = (patterns*9.99).toFixed(2);
            /* Users get bulk discounts. These same discounts are hardcoded
               into design_wizard/models.py, so if you change them here, change
               them there too.
            */
            if(patterns < 4) {
                if(patterns==1) {
                    display_total.html('$' + total_amount + ' for 1 pattern');
                } else {
                    display_total.html('$' + total_amount + ' for ' + patterns + ' patterns.');
                }
                bonus_sweaters.html('');
            } else if(patterns < 7) {
                display_total.html('$' + total_amount + ' for ' + patterns + ' patterns.');
                bonus_sweaters.html("Plus, you'll get one free bonus pattern!");
            } else {
                display_total.html('$' + total_amount + ' for ' + patterns + ' patterns.');
                bonus_sweaters.html("Plus, you'll get three free bonus patterns!");
            }
        } else {
            // If somehow the user has not entered a positive integer
            // for the desired number of patterns, don't list bogus data.
            display_total.html('Please enter the number of patterns you want to purchase.')
            bonus_sweaters.html('');
        }
    });
});