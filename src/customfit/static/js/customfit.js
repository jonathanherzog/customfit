var $j = jQuery.noConflict();


/*
 * Customfit Javascript utils.
 */
var customfit = (function() {

    var PULLOVER = ['PULLOVER_VEST', 'PULLOVER_SLEEVED'];
    var CARDIGAN = ['CARDIGAN_VEST', 'CARDIGAN_SLEEVED'];
    var VEST = ['PULLOVER_VEST', 'CARDIGAN_VEST'];
    var SLEEVED = ['PULLOVER_SLEEVED', 'CARDIGAN_SLEEVED'];

    // Compilation classes
    var COMPILATION_CLASS = 'compilation-configured';
    var COMPILATION_LAYER_CLASS = 'compilation-layer';

    // Centimeters per inches
    var CM_PER_INCHES = 2.54;


    /**
     * Pluralize.
     */
    var pluralize = function(count, base, plural) {
        if (count == 1) {
            return base;
        } else if (count > 1) {
            if (plural) {
                return plural;
            } else {
                return base + 's';
            }
        } else {
            return base;
        }
    };

    /**
     * Include CSRF token.
     */
    var includeCSRF = function(data) {
        data['csrfmiddlewaretoken'] = $j.cookie('csrftoken');
        return data;
    };

    /**
     * Get the container div for the specified field.
     */
    var getField = function(field) {
        var fieldSelector = '';
        if (customfit['PREFIX'] != undefined) {
            fieldSelector = customfit['PREFIX'] + field;
        } else {
            fieldSelector = field;
        }
        fieldSelector = '#div_id_' + fieldSelector;
        var fieldDiv = $j(fieldSelector);

        var input = fieldDiv.find('input');
        var select = fieldDiv.find('select');

        var units = fieldDiv.find('.input-group-addon').html();

        var conversion = 1;
        if ( units == 'metres' ) {
            /* Rav provides yards; we should convert to meters. */
            conversion = 0.9144;
        }

        /**
         * Set the field's value.
         */
        fieldDiv.setValue = function(value) {
            /*
             * Select
             */

            if ( $j.isNumeric(value) ) {
                value = Math.round(value*conversion);                
            }

            if (select.length) {
                select.val(value);

            /*
             * Single input
             */
            } else if (input.length == 1) {
                input.val(value);

            /*
             * Radio
             */
            } else {
                input.prop('checked', false);
                input.find('[value="' + value + '"]').prop('checked', true);
            }
        };

        /**
         * Get the field's value.
         */
        fieldDiv.getValue = function() {
            /*
             * Select
             */
            if (select.length) {
                return select.val();

            /*
             * Single input
             */
            } else if (input.length == 1) {
                return input.val();

            /*
             * Radio
             */
            } else if (input.length > 1) {
                for (var i = 0; i < input.length; i++) {
                    var radio = $j(input[i]);
                    if (radio.prop('checked')) {
                        return radio.val();
                    }
                }
            }

            /*
             * Default
             */
            return customfit.defaults[field];
        };

        /**
         * Clean the field's value.
         */
        fieldDiv.cleanValue = function() {
            /*
             * Select
             */
            if (select.length) {
                select.val('');

            /*
             * Single input
             */
            } else if (input.length == 1) {
                input.val('');

            /*
             * Radio
             */
            } else if (input.length > 1) {
                for (var i = 0; i < input.length; i++) {
                    var radio = $j(input[i]);
                    radio.prop('checked', false);
                }
            }
        };
        fieldDiv.on('hideField', function() {
            fieldDiv.cleanValue();
        });

        /**
         * Add a setup callback.
         */
        fieldDiv.setupUpdate = function(callback) {
            /*
             * Show event
             */
            fieldDiv.on('showField', callback);

            // Select
            if (select.length) {
                select.change(callback);

            // Single input
            } else if (input.length == 1) {
                input.keydown(callback);

            // Radio
            } else if (input.length > 1) {
                input.click(callback);
            }
        };

        return fieldDiv;
    };

    /**
     * Get whether the array contains the specified value.
     */
    var contains = function(array, value) {
        for (var i = 0; i < array.length; i++) {
            if (array[i] == value) {
                return true;
            }
        }
        return false;
    };

    /**
     * Show dependent fields.
     */
    var showDependent = function(field, value, show, hide) {
        var fieldDiv = getField(field);

        var _showFields = [];
        var _hideFields = [];

        var i;
        var div;

        // Get fields to show
        for (i = 0; i < show.length; i++) {
            var _field = show[i];

            // Single field
            if (typeof _field == 'string') {
                div = getField(_field);
                div.hide();
                _showFields.push(div);

            // Nested dependency
            } else {
                div = getField(_field['field']);
                div.hide();
                _showFields.push(div);

                showDependent(_field['field'], _field['value'], _field['show'], _field['hide']);
            }
        }

        // Get fields to hide
        if (hide != undefined) {
            for (i = 0; i < hide.length; i++) {
                div = getField(hide[i]);
                div.show();
                _hideFields.push(div);
            }
        }

        /**
         * Show dependent fields.
         */
        function showFields() {
            for (i = 0; i < _showFields.length; i++) {
                _showFields[i].show().trigger('showField');

                // TODO: Put styling CSS inside a CSS file.
                if ($j(_showFields[i]).hasClass('control-group')) {
                    _showFields[i].css({'margin-bottom':'20px'});
                }
            }

            for (i = 0; i < _hideFields.length; i++) {
                _hideFields[i].hide().trigger('hideField');

                // TODO: Put styling CSS inside a CSS file.
                if ($j(_showFields[i]).hasClass('control-group')) {
                    _showFields[i].css({'margin-bottom':'0'});
                }
            }
        }

        /**
         * Hide dependent fields.
         */
        function hideFields() {
            for (i = 0; i < _showFields.length; i++) {
                _showFields[i].hide().trigger('hideField');

                // TODO: Put styling CSS inside a CSS file.
                if ($j(_showFields[i]).hasClass('control-group')) {
                    _showFields[i].css({'margin-bottom':'0'});
                }
            }

            for (i = 0; i < _hideFields.length; i++) {
                _hideFields[i].show().trigger('showField');

                // TODO: Put styling CSS inside a CSS file.
                if ($j(_showFields[i]).hasClass('control-group')) {
                    _showFields[i].css({'margin-bottom':'20px'});
                }
            }
        }

        /*
         * Setup update
         */
        var update = function() {
            var _show = false;
            var current = fieldDiv.getValue();

            if (typeof value == 'function') {
                _show = value(current);
            } else {
                _show = contains(value, current);
            }

            if (_show) {
                showFields();
            } else {
                hideFields();
            }
        };
        fieldDiv.setupUpdate(update);
        fieldDiv.on('hideField', function() {
            hideFields();
        });
        update();

        return update;
    };


    /*
     * Image compilation common styles.
     */

    var compilations = {};

    /**
     * Update compilation.
     */
    var overlay = function(compilation, field, mapping, context) {
        /*
         * Configure if required.
         */
        var container = null;
        var compilationElement = $j(compilation);

        if (compilations[compilation] == undefined) {
            var replacement = $j('<div></div>').attr('class', compilationElement.attr('class'));
            replacement.addClass(customfit.COMPILATION_CLASS);
            compilationElement.replaceWith(replacement);

            compilations[compilation] = replacement;
        }

        container = compilations[compilation];

        var fieldDiv = getField(field);

        var input = fieldDiv.find('input');
        var select = fieldDiv.find('select');

        /**
         * Detach layer.
         */
        function detach() {
            container.find('[data-for="' + field + '"]').remove();
        }

        /**
         * Attach layer.
         */
        function attach(source) {
            if (source != undefined) {
                var image = $j('<img data-for="' + field + '" src="' + source + '"/>');
                image.load(function() {
                    image.addClass(customfit.COMPILATION_LAYER_CLASS);
                    detach();
                    container.append(image);
                });
            }
        }

        /*
         * Setup update
         */
        var update = function() {
            var source = mapping[fieldDiv.getValue()];

            if (source == undefined) {
                source = mapping[undefined];
            }

            if (typeof source == 'function') {
                attach(source(context));
            } else {
                attach(source);
            }
        };
        fieldDiv.setupUpdate(update);
        fieldDiv.on('hideField', function() {
            detach();
        });
        update();

        return update;
    };

    /**
     * Round a value to the nearest multiple specified.
     */
    var nearest = function(value, multiple) {
        return Math.round(value * (1 / multiple)) / (1 / multiple);
    };

    /**
     * Represent a value with fraction entities.
     */
    var representFraction = function(value, fractionFormat) {
        var whole = parseInt(value);
        var fraction = value - whole;

        if (fractionFormat) {
            if (fraction == 0) {
                return '' + whole;
            } else {
                var result = '';

                if (fraction == 0.25) {
                    result += '&frac14;';
                } else if (fraction == 0.5) {
                    result += '&frac12;';
                } else if (fraction == 0.75) {
                    result += '&frac34;';
                }

                if (result.length == 0) {
                    return '' + value;
                } else {
                    if (whole == 0) {
                        return result;
                    } else {
                        return whole + ' ' + result;
                    }
                }
            }
        } else {
            if (fraction == 0) {
                return '' + whole;
            } else {
                return '' + value;
            }
        }
    };

    /**
     * Convert inches to centimeters.
     */
    var inchesToCM = function(value) {
        return value * CM_PER_INCHES;
    };

    /**
     * Format a measurement XX" / YYcm
     */
    var formatMeasurement = function(value) {
        var roundedInches = nearest(value, 0.25);
        var inchesText = representFraction(roundedInches, true);

        var centimeters = inchesToCM(value);
        var roundedCentimeters = nearest(centimeters, 0.5);
        var centimetersText = representFraction(roundedCentimeters, false);

        return inchesText + '" / ' + centimetersText + ' cm';
    };

    /**
     * Replace the specified fields with measurement fields.
     */
    var createMeasurementField = function(selector) {
        var fields = [];

        $j(selector).each(function() {
            var input = $j(this);

            if (parseFloat(input.val())) {
                input.attr('type', 'hidden');

                var label = $j('<span class="label label-measurement">' +
                              formatMeasurement(input.val()) + '</span>');
                var buttonPlus = $j('<span class="icon-button icon-plus-sign icon-2x"></span>');
                var buttonMinus = $j('<span class="icon-button icon-minus-sign icon-2x"></span>');

                input.after(label);
                input.after(buttonPlus);
                input.after(buttonMinus);

                buttonPlus.click(function() {
                    var currentValue = parseFloat(input.val());
                    var newValue = (currentValue + 0.25).toFixed(2);

                    var value = '' + newValue;
                    input.val(value);
                    label.html(formatMeasurement(value));
                });

                buttonMinus.click(function() {
                    var currentValue = parseFloat(input.val());
                    var newValue = (currentValue - 0.25).toFixed(2);

                    if (newValue > 0) {
                        var value = '' + newValue;
                        input.val(value);
                        label.html(formatMeasurement(value));
                    }
                });

                fields.push({
                    'input': input,
                    'label': label,
                    'buttonPlus': buttonPlus,
                    'buttonMinus': buttonMinus
                });
            }
        });

        return fields;
    };

    /**
     * Setup image radio.
     */
    var setupImageRadio = function(query) {
        $j(document).on('click', query, function(e) {
            e.preventDefault();
            e.stopPropagation();

            var image = $j(this);

            var parent = image.parent();

            do {
                var input = parent.find('input');

                if (input.length) {
                    input.prop('checked', true).click();
                    break;
                }

            } while ((parent = parent.parent()) != null);
        });
    };

    /**
     * Create a div containing name and thumbnail.
     */
    function getThumbnail(data) {
        var div = $j('<div></div>');

        div.addClass('photo-item');

        var thumbnailURL = data['thumbnail_url'];
        if (thumbnailURL) {
            div.append('<img src="' + thumbnailURL + '"></img>');
        }

        var photoURL = data['photo_url'];
        if (photoURL) {
            div.attr('data-photo-url', photoURL);
        }

        var name = data['name'];
        if (name) {
            div.append('<br/>' + data['name']);
        }


        return div;
    }

    /**
     * Create modal. Uses Bootstrap's modal plugin for modal management.
     */
    var createModal = function() {
        var modal = $j(' \
<div class="modal fade" id="cf_modal"> \
  <div class="modal-dialog"> \
    <div class="modal-content"> \
      <div class="modal-header"> \
        <button type="button" class="btn-customfit-outline pull-right" data-dismiss="modal" data-target="#cf_modal" aria-label="Close"><span aria-hidden="true">&times; Close</span></button> \
        <h4 class="modal-title" id="modal-title">Modal title</h4> \
      </div> \
      <div class="modal-body"> \
        <div id="modal-message"></div> \
        <div id="modal-results"></div> \
        <div id="modal-extras"></div> \
      </div> \
    </div><!-- /.modal-content --> \
  </div><!-- /.modal-dialog --> \
</div><!-- /.modal --> \
');

        modal.modal({show: false});
        $j('body').append(modal);

        /**
         * Show modal.
         */
        modal.showModal = function(callback) {
            $j('#cf_modal').modal('show');
        };

        /**
         * Hide modal.
         */
        modal.hideModal = function(callback) {
            $j('#cf_modal').modal('hide');
        };

        /**
         * Destroy modal.
         */
        modal.destroyModal = function() {
            modal.remove();
        };

        // Modal title
        var title = $j('#modal-title');
        modal.setTitle = function(text) {
            title.html(text);
        };

        // Modal results display
        var results = $j('#modal-results');
        modal.setResults = function(text) {
            results.html(text);
        };

        // Modal extra content display (e.g. paginators)
        var extras = $j('#modal-extras');
        modal.appendExtra = function(text) {
            extras.append(text);
        };

        // Modal message
        var message = $j('#modal-message');
        modal.setMessage = function(text) {
            message.html(text);
        };

        return modal;
    };

    /**
     * Create a generic photos modal.
     */
    var createPhotosModal = function(url, createURL, selector, title, onClick, onPhotoClick) {
        var photosModal = createModal();
        photosModal.setTitle(title);

        /*
         * Open modal action.
         */
        $j(document).on('click', selector, function(e) {
            e.preventDefault();
            e.stopPropagation();

            if (onClick) {
                onClick(e);
            }

            var button = $j(this);
            button.addClass('disabled');
            var objectId = button.data('object-id');

            photosModal.showModal();
            photosModal.on('modalHide', function() {
                button.removeClass('disabled');
            });


            var data = {};
            if (objectId) {
                data['object_id'] = objectId;
            }

            $j.get(url, data, function(response) {

                var results = $j('<div></div>');

                if (response['success']) {
                    var photos = response['photos'];
                    if (photos.length) {
                        var count = photos.length;
                        photosModal.setMessage(count + ' ' + pluralize(count, 'photo') + ' found.');

                        for (var i = 0; i < photos.length; i++) {
                            results.append(getThumbnail(photos[i]));
                        }
                        photosModal.setResults(results);
                    }
                } else {
                    photosModal.setMessage(response['message']);
                }
            });

            /*
             * Create photo action.
             */
            $j('#modal-results').on('click', '.photo-item', function(e) {
                e.preventDefault();
                e.stopPropagation();

                if (onPhotoClick) {
                    onPhotoClick(e);
                }

                var item = $j(this);
                var photoURL = item.data('photo-url');


                $j.post(createURL, includeCSRF({
                    'object_id': objectId,
                    'photo_url': photoURL
                }), function(response) {

                    if (response['success']) {
                        window.location.reload();
                    } else {
                        photosModal.setMessage(response['message']);
                    }
                });
            });
        });
    };

    /**
     * Setup design wizard dependencies.
     */
    var setupWizardDependencies = function() {
        // Sleeves and armholes
        customfit.showDependent('garment_type', customfit.SLEEVED,
                                ['sleeve_length', {
                                    'field': 'sleeve_shape',
                                    'value': ['SLEEVE_BELL'],
                                    'show': ['bell_type']
                                }, 'sleeve_edging_stitch', 'sleeve_edging_height'],
                                ['armhole_edging_stitch', 'armhole_edging_height']);

        // Buttons
        customfit.showDependent('garment_type', customfit.CARDIGAN,
                                ['button_band_allowance', 'button_band_edging_stitch',
                                 'button_band_edging_height', 'number_of_buttons'],
                                []);

        // Sleeve shape
        customfit.showDependent('sleeve_length',
                                ['SLEEVE_ELBOW', 'SLEEVE_THREEQUARTER', 'SLEEVE_FULL'],
                                ['sleeve_shape'], []);

        // Neckline
        var necklineStyle = customfit.getField('neckline_style');
        var updateNeckEdging = customfit.showDependent('garment_type', function(value) {
            return customfit.contains(customfit.CARDIGAN, value) && necklineStyle.getValue() == 'NECK_VEE';
        }, [], ['neck_edging_stitch', 'neck_edging_height']);
        necklineStyle.click(function() {
            updateNeckEdging();
        });
    };

    /**
     * Setup design wizard overlay.
     */
    var setupWizardOverlay = function(sources) {
        var compilation = customfit['COMPILATION'];
        var garmentTypeField = customfit.getField('garment_type');

        /*
         * Neckline style.
         */
        var updateNecklineStyle = customfit.overlay(compilation, 'neckline_style', {
            'NECK_VEE': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['V_PULLOVER_NECK'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['V_CARDI_NECK'];
                }
                return null;
            },
            'NECK_CREW': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['CREW_NECK_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['CREW_NECK_CARDI'];
                }
                return null;
            },
            'NECK_SCOOP': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['SCOOP_NECK_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['SCOOP_NECK_CARDI'];
                }
                return null;
            },
            'NECK_BOAT': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['BOAT_NECK_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['BOAT_NECK_CARDI'];
                }
                return null;
            },

            undefined: sources['TANK_NECK_PULLOVER']
        }, {});
        garmentTypeField.setupUpdate(updateNecklineStyle);

        /*
         * Sleeve length.
         */
        var updateSleeveLength = customfit.overlay(compilation, 'sleeve_length', {
            'SLEEVE_SHORT': sources['SHORT_SLEEVES'],
            'SLEEVE_ELBOW': sources['ELBOW_SLEEVES'],
            'SLEEVE_THREEQUARTER': sources['3_4_SLEEVES'],
            'SLEEVE_FULL': sources['LONG_SLEEVES'],

            undefined: sources['VEST_PULLOVER_CARDI']
        }, {});
        garmentTypeField.setupUpdate(updateSleeveLength);

        /*
         * Torso length.
         */
        var updateTorsoLength = customfit.overlay(compilation, 'torso_length', {
            'high_hip_length': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['HIGH_HIP_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['HIGH_HIP_CARDI'];
                }
                return null;
            },
            'med_hip_length': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['MID_HIP_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['MID_HIP_CARDI'];
                }
                return null;
            },
            'low_hip_length': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['LOW_HIP_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['LOW_HIP_CARDI'];
                }
                return null;
            },
            'tunic_length': function() {
                if (customfit.contains(customfit.PULLOVER, garmentTypeField.getValue())) {
                    return sources['TUNIC_PULLOVER'];
                } else if (customfit.contains(customfit.CARDIGAN, garmentTypeField.getValue())) {
                    return sources['TUNIC_CARDI'];
                }
                return null;
            },

            undefined: sources['MID_HIP_PULLOVER']
        }, {});
        garmentTypeField.setupUpdate(updateTorsoLength);
    };


    /*
     * Subpages.
     */
    var SCROLL_DELAY = 400;

    /**
     * Present subpage.
     */
    var presentSubpage = function(element) {
        element.show();
        $j('html, body').animate({
            scrollTop: element.offset().top
        }, SCROLL_DELAY);
    };

    /**
     * Enable subpages.
     */
    var enableSubpages = function() {
        $j('[data-subpage-initial]').each(function() {
            var div = $j(this);
            var initial = div.data('subpage-initial');

            $j.get(initial, function(response) {
                div.html(response);
            });
        });

        /*
         * Anchors.
         */
        $j(document).on('click', 'a[data-subpage]', function(e) {
            e.stopPropagation();
            e.preventDefault();

            var anchor = $j(this);

            var href = anchor.attr('href');
            var subpage = anchor.data('subpage');

            $j.get(href, function(response) {
                var div = $j(subpage);

                div.hide();
                div.html(response);
                div.find('[data-subpage]').attr('data-subpage-this', subpage).attr('data-subpage-href', href);
                presentSubpage(div);
                if (subpage == '#subpage-edit') {
                    customfit.setupSchematicEdit();                    
                }
            });
        });

        /*
         * Buttons.
         */
        $j(document).on('click', 'input[data-subpage]', function(e) {
            e.preventDefault();
            e.stopPropagation();

            var input = $j(this);
            var form = input.closest('form');
            var subpage = input.data('subpage');
            var subpageThis = input.data('subpage-this');
            var subpageHREF = input.data('subpage-href');

            input.val("The elves are working...");

            var formData = {};
            var serialized = form.serializeArray();
            for (var n = 0; n < serialized.length; n++) {
                formData[serialized[n]['name']] = serialized[n]['value'];
            }
            formData[input.attr('name')] = input.attr('name');

            $j.post(subpageHREF, formData, function(response) {
                var redirect = response['redirect'];
                var redirectSubpage = response['subpage'];

                if (redirect != undefined) {
                    if (redirectSubpage) {
                        $j.get(redirect, function(response) {
                            var div = $j(redirectSubpage);
                            div.html(response);
                            presentSubpage(div);
                            $j(subpageThis).slideUp();
                        });
                    } else {
                        window.location.href = redirect;
                    }

                } else {
                    var div = $j(subpageThis);
                    div.hide();
                    div.html(response);

                    var replacement = div.find('[data-subpage]');
                    replacement.attr('data-subpage-this', subpageThis);
                    replacement.attr('data-subpage-href', subpageHREF);

                    presentSubpage(div);
                }
            });
        });
    };

    /**
     * Setup the schematic edit page.
     */
    var setupSchematicEdit = function(enable) {
        var fields = customfit.createMeasurementField('input[type="number"]');

        var inputEnable = $j('#tweak');

        if (enable == undefined) {
            enable = (inputEnable.length == 0);
        }

        if (!enable) {
            var i;

            for (i = 0; i < fields.length; i++) {
                fields[i].buttonMinus.hide().width(0);
                fields[i].buttonPlus.hide().width(0);
            }

            var inputEdit = $j('input[name="edit"]');
            var inputPay = $j('input[name="pay"]');

            inputEdit.hide();
            inputPay.hide();

            inputEnable.click(function(e) {
                e.preventDefault();
                e.stopPropagation();

                $j(this).hide();

                for (i = 0; i < fields.length; i++) {
                    fields[i].buttonMinus.show().animate({'width': '25px'});
                    fields[i].buttonPlus.show().animate({'width': '25px'});
                }

                inputEdit.show();
                inputPay.show();
            });
        }
    };

    /**
     * Setup schematic merged page.
     */
    var setupSchematicMerged = function() {
        customfit.enableSubpages();
    };

    return {
        'PULLOVER': PULLOVER,
        'CARDIGAN': CARDIGAN,
        'VEST': VEST,
        'SLEEVED': SLEEVED,

        'CM_PER_INCHES': CM_PER_INCHES,

        // Compilation classes
        'COMPILATION_CLASS': COMPILATION_CLASS,
        'COMPILATION_LAYER_CLASS': COMPILATION_LAYER_CLASS,


        // Utils
        'pluralize': pluralize,
        'includeCSRF': includeCSRF,

        // Dependencies and overlay
        'getField': getField,
        'contains': contains,
        'showDependent': showDependent,
        'overlay': overlay,

        // Measurement formatting
        'nearest': nearest,
        'representFraction': representFraction,
        'inchesToCM': inchesToCM,
        'formatMeasurement': formatMeasurement,
        'createMeasurementField': createMeasurementField,

        // Image radios
        'setupImageRadio': setupImageRadio,

        // Modal
        'createModal': createModal,
        'createPhotosModal': createPhotosModal,

        // Design wizard setup
        'setupWizardDependencies': setupWizardDependencies,
        'setupWizardOverlay': setupWizardOverlay,

        // Subpages
        'presentSubpage': presentSubpage,
        'enableSubpages': enableSubpages,

        // Schematic pages
        'setupSchematicEdit': setupSchematicEdit,
        'setupSchematicMerged': setupSchematicMerged,
    }
})();
