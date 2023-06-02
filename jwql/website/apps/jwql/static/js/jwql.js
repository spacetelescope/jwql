/**
 * Various JS functions to support the JWQL web application.
 *
 * @author Lauren Chambers
 * @author Matthew Bourque
 * @author Brad Sappington
 * @author Bryan Hilbert
 * @author Maria Pena-Guerrero
 * @author Melanie Clarke
 */


 /**
 * Change the filetype for all displayed images
 * @param {String} type - The image type (e.g. "rate", "uncal", etc.)
 * @param {String} group_root - The rootname of the file group
 * @param {Dict} num_ints - A dictionary whose keys are suffix types and whose
 *                          values are the number of integrations with an associated
 *                          preview image for that suffix
 * @param {Dict} available_ints - A dictionary whose keys are suffix types and whose
 *                                values are the integration numbers of the available
 *                                jpgs for that suffix
 * @param {Dict} total_ints - A dictionary whose keys are suffix types and whose
 *                                values are the total number of integrations for that
 *                                filetype.
 * @param {String} inst - The instrument for the given file
 */
 function change_all_filetypes(type, group_root, num_ints, available_ints, total_ints, inst, detectors) {

    // Change the radio button to check the right filetype
    document.getElementById(type).checked = true;

    // Store the currently displayed suffix
    document.getElementById("view_file_type").setAttribute('data-current-suffix', type);

    // Clean the input parameters
    num_ints = clean_input_parameter(num_ints);
    num_ints = JSON.parse(num_ints);

    // Get the available integration jpg numbers
    available_ints = clean_input_parameter(available_ints);
    available_ints = JSON.parse(available_ints)[type];

    // Get the total number of integrations
    total_ints = clean_input_parameter(total_ints);
    total_ints = JSON.parse(total_ints);

    // Update the APT parameters
    var parsed_name = parse_filename(group_root);
    document.getElementById("proposal").innerHTML = parsed_name.proposal;
    document.getElementById("obs_id").innerHTML = parsed_name.obs_id;
    document.getElementById("visit_id").innerHTML = parsed_name.visit_id;

    var detector_list = detectors.split(',');
    for (let i = 0; i < detector_list.length; i++) {
        var detector = detector_list[i];

        // Update the filename lists
        var filename_option = document.getElementById(detector + "_filename");
        filename_option.value = inst + '/' + group_root + '_' + detector + '_' + type;
        filename_option.textContent = group_root + '_' + detector + '_' + type;

        // Show the appropriate image
        var img = document.getElementById("image_viewer_" + detector);
        var jpg_filepath = '/static/preview_images/' + parsed_name.program +
                           '/' + group_root + '_' + detector + '_' + type + '_integ0.jpg';
        img.src = jpg_filepath;
        img.alt = jpg_filepath;

        // Show/hide the viewer as appropriate
        show_viewer(detector, jpg_filepath);
    }

    // Reset the slider values
    reset_integration_slider(num_ints[type], total_ints[type])

    // Update the view/explore links for the new file type
    update_view_explore_link();
}


 /**
 * Change the filetype of the displayed image
 * @param {String} type - The image type (e.g. "rate", "uncal", etc.)
 * @param {String} file_root - The rootname of the file
 * @param {Dict} num_ints - A dictionary whose keys are suffix types and whose
 *                          values are the number of integrations with an associated
 *                          preview image for that suffix
 * @param {Dict} available_ints - A dictionary whose keys are suffix types and whose
 *                                values are the integration numbers of the available
 *                                jpgs for that suffix
 * @param {Dict} total_ints - A dictionary whose keys are suffix types and whose
 *                                values are the total number of integrations for that
 *                                filetype.
 * @param {String} inst - The instrument for the given file
 */
 function change_filetype(type, file_root, num_ints, available_ints, total_ints, inst) {

    // Change the radio button to check the right filetype
    document.getElementById(type).checked = true;

    // Store the currently displayed suffix
    document.getElementById("view_file_type").setAttribute('data-current-suffix', type);

    // Clean the input parameters
    num_ints = clean_input_parameter(num_ints);
    num_ints = JSON.parse(num_ints);

    // Get the available integration jpg numbers
    available_ints = clean_input_parameter(available_ints);
    available_ints = JSON.parse(available_ints)[type];

    // Get the total number of integrations
    total_ints = clean_input_parameter(total_ints);
    total_ints = JSON.parse(total_ints);

    // Propagate the text fields showing the filename and APT parameters
    var fits_filename = file_root + '_' + type;
    var parsed_name = parse_filename(file_root);

    document.getElementById("jpg_filename").innerHTML = file_root + '_' + type + '_integ0.jpg';
    document.getElementById("fits_filename").innerHTML = fits_filename + '.fits';
    document.getElementById("proposal").innerHTML = parsed_name.proposal;
    document.getElementById("obs_id").innerHTML = parsed_name.obs_id;
    document.getElementById("visit_id").innerHTML = parsed_name.visit_id;
    document.getElementById("detector").innerHTML = file_root.split('_')[3];

    // Show the appropriate image
    var img = document.getElementById("image_viewer");
    var jpg_filepath = '/static/preview_images/' + parsed_name.program + '/' + file_root + '_' + type + '_integ0.jpg';
    img.src = jpg_filepath;
    img.alt = jpg_filepath;
    // if previous image had error, remove error sizing
    img.classList.remove("thumbnail");

    // Reset the slider values
    reset_integration_slider(num_ints[type], total_ints[type])

    // Update the image exploration and header links
    document.getElementById("view_header").href = '/' + inst + '/' + file_root + '_' + type + '/header/';
    document.getElementById("explore_image").href = '/' + inst + '/' + file_root + '_' + type + '/explore_image/';
}


 /**
 * Change the integration number of the displayed image
 * @param {String} file_root - The rootname of the file
 * @param {Dict} num_ints - A dictionary whose keys are suffix types and whose
 *                          values are the number of integrations for that suffix
 * @param {Dict} available_ints - A dictionary whose keys are suffix types and whose
 *                                values are the integration numbers of the available
 *                                jpgs for that suffix
 * @param {String} method - How the integration change was initialized, either "button" or "slider"
 * @param {String} direction - The direction to switch to, either "left" (decrease) or "right" (increase).
 *                             Only relevant if method is "button".
 */
function change_integration(file_root, num_ints, available_ints, method, direction='right') {

    // Figure out the current image and integration
    var suffix = document.getElementById("view_file_type").getAttribute('data-current-suffix');
    var integration = Number(document.getElementById("slider_val").innerText) - 1;
    var program = parse_filename(file_root).program;

    // Find the total number of integrations for the current image
    num_ints = num_ints.replace(/'/g, '"');
    num_ints = JSON.parse(num_ints)[suffix];

    // Get the available integration jpg numbers and the current integration index
    available_ints = available_ints.replace(/'/g, '"');
    available_ints = JSON.parse(available_ints)[suffix];
    var current_index = available_ints.indexOf(integration);

    // Get the desired integration value
    var new_integration;
    var new_value;
    switch (method) {
        case "button":
            if ((integration == num_ints - 1 && direction == 'right')||
                (integration == 0 && direction == 'left')) {
                return;
            } else if (direction == 'right') {
                new_value = current_index + 1;
                new_integration = available_ints[new_value];
            } else if (direction == 'left') {
                new_value = current_index - 1;
                new_integration = available_ints[new_value];
            }
            break;
        case "slider":
            new_value = document.getElementById("slider_range").value - 1;
            new_integration = available_ints[new_value];
            break;
    }

    // Update which button are disabled based on the new integration
    if (new_integration == 0) {
        document.getElementById("int_after").disabled = false;
        document.getElementById("int_before").disabled = true;
    } else if (new_integration < available_ints[available_ints.length - 1]) {
        document.getElementById("int_after").disabled = false;
        document.getElementById("int_before").disabled = false;
    } else if (new_integration == available_ints[available_ints.length - 1]) {
        document.getElementById("int_after").disabled = true;
        document.getElementById("int_before").disabled = false;
    }

    var img_viewers = document.getElementsByClassName("image_preview_viewer");
    for (let i = 0; i < img_viewers.length; i++) {
        var img = img_viewers[i];

        var jpg_filename;
        var detector = img.getAttribute('data-detector');
        if (detector != null) {
            // exposure view
           jpg_filename = file_root + '_' + detector + '_' + suffix + '_integ' + new_integration + '.jpg';
        } else {
           // image view
           jpg_filename = file_root + '_' + suffix + '_integ' + new_integration + '.jpg';
           document.getElementById("jpg_filename").innerHTML = jpg_filename;
           // if previous image had error, remove error sizing
           img.classList.remove("thumbnail");
        }

        // Show the appropriate image
        var jpg_filepath = '/static/preview_images/' + program + '/' + jpg_filename;
        img.src = jpg_filepath;
        img.alt = jpg_filepath;

        // Show/hide the viewer as appropriate for the image
        if (detector != null) {
            show_viewer(detector, jpg_filepath);
        }
    }

    // Update the slider values
    document.getElementById("slider_range").value = new_value + 1;
    document.getElementById("slider_val").innerHTML = new_integration + 1;
}


/**
 * Clean garbage characters in input dictionary parameters passed as strings.
 * @param {String} param_value - The parameter value to clean
 * @returns {String} cleaned - The cleaned parameter value
 */
function clean_input_parameter(param_value) {
    param_value = param_value.replace(/&#39;/g, '"');
    param_value = param_value.replace(/'/g, '"');
    return param_value
}


/**
 * Determine whether the page is archive or unlooked
 * @param {String} instrument - The instrument of interest
 * @param {Integer} proposal - The proposal of interest
 */
function determine_page_title(instrument, proposal) {
    // Determine if the URL is 'archive' or 'unlooked'
    var url = document.URL;
    var url_split = url.split('/');
    var url_title = url_split[url_split.length - 2];
    var final_title;
    if (url_title == 'archive') {
        final_title = 'Archived ' + instrument + ' Images: Proposal ' + proposal
    } else if (url_title == 'unlooked') {
        final_title = 'Unlooked ' + instrument + ' Images';
    }

    // Update the titles accordingly
    if (typeof final_title !== 'undefined') {
        document.getElementById('title').innerHTML = final_title;
        if (document.title != final_title) {
            document.title = final_title;
        }
    }
}

/**
 * Determine whether the page is archive or unlooked
 * @param {String} instrument - The instrument of interest
 * @param {Integer} proposal - The proposal of interest
 * @param {Integer} observation - The observation number of interest
 */
function determine_page_title_obs(instrument, proposal, observation) {
    // Determine if the URL is 'archive' or 'unlooked'
    var url = document.URL;
    var url_split = url.split('/');
    var url_title = url_split[url_split.length - 3];
    var final_title;
    if (url_title == 'archive') {
        final_title = 'Archived ' + instrument + ' Images: Proposal ' + proposal + ', Observation ' + observation
    } else if (url_title == 'unlooked') {
        final_title = 'Unlooked ' + instrument + ' Images';
    } else if (isNaN(url_title) == false) {
        final_title = 'Archived ' + instrument + ' Images: Proposal ' + proposal + ', Observation ' + observation
    }

    // Update the titles accordingly
    if (typeof final_title !== 'undefined') {
        document.getElementById('title').innerHTML = final_title;
        if (document.title != final_title) {
            document.title = final_title;
        }
    }
}

/**
 * adds/removes disabled_section class and clears value
 * @param {string} element_id 
 * @param {boolean} set_disable 
 */
 function set_disabled_section (element_id, set_disable) {

    if (set_disable) {
        document.getElementById(element_id).classList.add("disabled_section");
    } else {
        document.getElementById(element_id).classList.remove("disabled_section");
    }
}
/**
 * Interprets number of integrations/groups for the selected extension and disables input for calculating difference accordingly
 * @param {Dict} integrations - A dictionary whose keys are extensions and whose
 *                              values are the number of integrations for that suffix
 * @param {Dict} groups - A dictionary whose keys are extensions and whose
 *                              values are the number of groups for that suffix
 */
function explore_image_update_enable_options(integrations, groups) {
    
    // Check nr of integrations and groups of currently selected extension
    var ext_name = get_radio_button_value("extension");

    // Clean the input parameters and get our integrations/groups for this extension
    var calc_difference = false;
    integrations = integrations.replace(/&#39;/g, '"');
    integrations = integrations.replace(/'/g, '"');
    integrations = JSON.parse(integrations)[ext_name];
    groups = groups.replace(/&#39;/g, '"');
    groups = groups.replace(/'/g, '"');
    groups = JSON.parse(groups)[ext_name];
    
    // Zero base our calculations
    integrations -= 1
    groups -=1

    // Set max values to those available
    document.getElementById("integration1").max = integrations;
    document.getElementById("integration2").max = integrations;
    document.getElementById("group1").max = groups;
    document.getElementById("group2").max = groups;
    
    
    // If multiple integrations or groups.  Allow difference calculations
    //          enable calculate_difference box
    //          enable subtrahend boxes
    if (integrations > 0 || groups > 0) {
        set_disabled_section("calcDifferenceForm", false);
        calc_difference = document.getElementById("calcDifference").checked;
        
    } else {
        document.getElementById("calcDifference").checked.value = false;
        set_disabled_section("calcDifferenceForm", true);
    }

    if (!calc_difference) {
        document.getElementById("integration2").value = null;
        document.getElementById("group2").value = null;
    }
    if (integrations < 1) {
        document.getElementById("integration1").value = null;
        document.getElementById("integration2").value = null;
    }
    if (groups < 1){
        document.getElementById("group1").value = null;
        document.getElementById("group2").value = null;
    }
    // Add/remove disable class to integration/group input if not multiple
    set_disabled_section("integrationInput1", (integrations < 1));
    set_disabled_section("groupInput1", (groups < 1));
    set_disabled_section("integrationInput2", (!calc_difference || integrations < 1));
    set_disabled_section("groupInput2", (!calc_difference || groups < 1));
    
}


/**
 * getCookie
 *      taken from https://docs.djangoproject.com/en/4.1/howto/csrf/
 * @param {String} name - The name of the cookie element you want to extract
 * @returns value - value of the extracted cookie element
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}


/**
 * get_radio_button_value
 * @param {String} element_name - The name of the radio buttons
 * @returns value - value of checked radio button
 */
function get_radio_button_value(element_name) {
    var element = document.getElementsByName(element_name);

    for(var i = 0; i < element.length; i++) {
        if(element[i].checked) {
            return element[i].value;
        }
    }
    return "";
}

/**
 * get_scaling_value
 * @param {String} element_id - The element id
 * @returns value - value of element id or "None" if empty or not a number
*/
function get_number_or_none(element_id) {

    var limit = document.getElementById(element_id).value;
    if (limit.length == 0 || isNaN(limit)) limit = "None";
    return limit;
}


/**
 * Group thumbnail display by exposure or file, save group type in session
 * @param {String} group_type - The group type
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function group_by_thumbnails(group_type, base_url) {

    // Update dropdown menu text and update thumbnails for current setting
    show_only('group', group_type, base_url);

    // Group divs to update display style
    var group_divs = document.getElementsByClassName("thumbnail-group");
    // Thumbnail links to update to group or image pages
    var thumbnail_links = document.getElementsByClassName("thumbnail-link");
    // Show count total and type to update
    var img_total = document.getElementById('img_total');
    var img_type = document.getElementById('img_type');
    var group_by = document.getElementById('group_by')

    if (group_type == 'Exposure') {
        img_total.innerText = group_by.getAttribute('data-ngroup');
        img_type.innerText = 'groups';
        for (let i = 0; i < group_divs.length; i++) {
            group_divs[i].classList.add('thumbnail-group-active');
            thumbnail_links[i].href = thumbnail_links[i].getAttribute('data-group-href');
        }
    } else {
        img_total.innerText = group_by.getAttribute('data-nfile');
        img_type.innerText = 'activities';
        for (let i = 0; i < group_divs.length; i++) {
            group_divs[i].classList.remove('thumbnail-group-active');
            thumbnail_links[i].href = thumbnail_links[i].getAttribute('data-image-href');
        }
    }

    $.ajax({
        url: base_url + '/ajax/image_group/',
        data: {
            'group_type': group_type
        },
        error : function(response) {
            console.log("session image group update failed");
        }
    });
}


/**
 * Hide an image viewer
 * @param {String} detector - The detector name for the image viewer
 */
function hide_file(detector) {
    var img = document.getElementById("image_viewer_" + detector);
    var div = document.getElementById(detector + "_view");
    var filename = document.getElementById(detector + "_filename");

    // Hide the image and div
    img.style.display = "none";
    div.style.display = "none";

    // Disable the associated filename unless there
    // are no previews available at all
    var fallback_shown = document.getElementById(detector + "_view_fallback");
    if (fallback_shown.style.display == "none") {
        filename.disabled = true;
    }

    // Update the view/explore link as needed
    update_view_explore_link();
}

/**
 * Show an image viewer
 * @param {String} detector - The detector name for the image viewer
 */
function unhide_file(detector) {
    var img = document.getElementById("image_viewer_" + detector);
    var div = document.getElementById(detector + "_view");
    var filename = document.getElementById(detector + "_filename");

    // Show the image and div
    img.style.display = "inline-block";
    div.style.display = "inline-block";

    // Hide the fallback image and div
    // These are never re-displayed: if any image loads for the detector,
    // they will not show up. This is intended to cover the case where FITS files
    // exist for the exposure, but no preview images have been generated yet.
    document.getElementById("fallback_image_viewer_" + detector).style.display = "none";
    document.getElementById(detector + "_view_fallback").style.display = "none";

    // Enable the associated filename
    filename.disabled = false;

    // Update the view/explore link as needed
    update_view_explore_link();
}


/**
 * Insert thumbnail images inside existing HTML img tags
 * @param {List} updates - A list of updates to make, as [thumbnail_id, jpg_path].
 */
function insert_thumbnail_images(updates) {
    // Update the thumbnail image source
    for (var i = 0; i < updates.length; i++) {
        var thumb_id = updates[i][0];
        var jpg_path = updates[i][1];
        set_thumbnail_image_source(thumb_id, jpg_path);
    }
}


/**
 * Check for a thumbnail image and add it to an img if it exists
 * @param {Integer} thumb_id - The ID number for the thumbnail img
 * @param {String} jpg_filepath - The image to show
 */
function set_thumbnail_image_source(thumb_id, jpg_path) {
    $.get(jpg_path, function() {
        var img = document.getElementById('thumbnail' + thumb_id);
        img.src = jpg_path;})
}


/**
 * Parse observation information from a JWST file name.
 * @param {String} filename - The file or group root name to parse
 * @returns {Object} parsed - Dictionary containing 'proposal', 'obs_id', 'visit_id', 'program'
 */
function parse_filename(root_name) {
    // eg. for root_name jw02589006001_04101_00001-seg001_nrs1:
    //   program = jw02589
    //   proposal = 02589
    //   obs_id = 006
    //   visit_id = 001

    // used for preview directories
    var program = root_name.slice(0,7);

    // used for observation description fields
    var proposal = root_name.slice(2, 7);
    var obs_id = root_name.slice(7, 10);
    var visit_id = root_name.slice(10, 13);

    const parsed_name = {program: program, proposal: proposal,
                         obs_id: obs_id, visit_id: visit_id};
    return parsed_name;
}


/**
 * Reset the integration slider for a new file
 * @param {Int} num_integration - The number of integration images available
 * @param {Int} total_integration - The total number of integrations to display
 */
function reset_integration_slider(num_integration, total_integration) {
    // Reset the slider values
    document.getElementById("slider_range").value = 1;
    document.getElementById("slider_range").max = num_integration;
    document.getElementById("slider_val").innerHTML = 1;
    document.getElementById("total_ints").innerHTML = total_integration;

    // Update the integration changing buttons
    if (num_integration > 1) {
        document.getElementById("int_after").disabled = false;
    } else {
        document.getElementById("int_after").disabled = true;
    }

    // Disable the "left" button, since this will be showing integ0
    document.getElementById("int_before").disabled = true;
}


/**
 * Check for a detector image and show or hide its viewer accordingly.
 * @param {String} detector - The detector name
 * @param {String} jpg_filepath - The image to show
 */
function show_viewer(detector, jpg_filepath) {
    $.get(jpg_filepath, function() {unhide_file(detector);})
    .fail(function() {hide_file(detector)});
}

/**
 * If an image is not found, replace with temporary image sized to thumbnail
 */
function image_error(image, makeThumbnail=false) {
    image.src = "/static/img/imagenotfound.png";
    /* Use thumbnail settings to keep it tidy */
    if (makeThumbnail) {
        image.className = "thumbnail";
    }
    return true;
}


/**
 * Perform a search of images and display the resulting thumbnails
 */
function search() {

    // Find all proposal elements
    var proposals = document.getElementsByClassName("proposal");

    // Determine the current search value
    var search_value = document.getElementById("search_box").value;

    // Determine whether or not to display each thumbnail
    var num_proposals_displayed = 0;
    for (var i = 0; i < proposals.length; i++) {
        // Evaluate if the proposal number matches the search
        var j = i + 1
        var prop_name = document.getElementById("proposal" + j).getAttribute('data-proposal')
        var prop_num = Number(prop_name)

        if (prop_name.startsWith(search_value) || prop_num.toString().startsWith(search_value)) {
            proposals[i].style.display = "inline-block";
            num_proposals_displayed++;
        } else {
            proposals[i].style.display = "none";
        }
    }

    // If there are no proposals to display, tell the user
    if (num_proposals_displayed == 0) {
        document.getElementById('no_proposals_msg').style.display = 'inline-block';
    } else {
        document.getElementById('no_proposals_msg').style.display = 'none';
    }

    // Update the count of how many images are being shown
    document.getElementById('img_shown').innerText = num_proposals_displayed;
}


/**
 * Limit the displayed thumbnails based on filter criteria
 * @param {String} filter_type - The filter type.
 * @param {Integer} value - The filter value
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function show_only(filter_type, value, base_url) {

    var filter_div = document.getElementById('filter_by');
    var dropdown_keys = filter_div.getAttribute('data-dropdown-key-list');
    var thumbnail_class = filter_div.getAttribute('data-thumbnail-class');

    // Get all filter options from {{dropdown_menus}} variable
    var all_filters = dropdown_keys.split(',');

    // Update dropdown menu text
    document.getElementById(filter_type + '_dropdownMenuButton').innerHTML = value;

    // Check for grouping setting for special handling
    var group_option = document.getElementById('group_dropdownMenuButton')
    var group = false;
    if (group_option != null) {
        group = (group_option.innerText == 'Exposure');
    }

    // Determine the current value for each filter
    var filter_values = [];
    for (var j = 0; j < all_filters.length; j++) {
        var filter_value = document.getElementById(all_filters[j] + '_dropdownMenuButton').innerHTML;
        filter_values.push(filter_value);
    }

    // Find all thumbnail elements
    var thumbnails = document.getElementsByClassName(thumbnail_class);

    // Determine whether or not to display each thumbnail
    var num_thumbnails_displayed = 0;
    var list_of_rootnames = "";
    var groups_shown = new Set();
    for (var i = 0; i < thumbnails.length; i++) {
        // Evaluate if the thumbnail meets all filter criteria
        var criteria = [];
        for (j = 0; j < all_filters.length; j++) {
            var filter_attribute = thumbnails[i].getAttribute('data-' + all_filters[j]);
            var criterion = (filter_values[j].indexOf('All '+ all_filters[j] + 's') >=0)
                         || (filter_attribute.includes(filter_values[j]));
            criteria.push(criterion);
        }

        // If data are grouped, check if a thumbnail for the group has already been displayed
        var show_group = true;
        if (group && groups_shown.has(thumbnails[i].getAttribute('data-group_root'))) {
            show_group = false;
        }

        // Only display if all criteria are met
        if (criteria.every(function(r){return r})) {
            // if group has already been shown, do not show thumbnail,
            // but do store the file root for navigation
            if (show_group) {
                thumbnails[i].style.display = "inline-block";
                num_thumbnails_displayed++;
                if (group) { groups_shown.add(thumbnails[i].getAttribute('data-group_root')); }
            } else {
                thumbnails[i].style.display = "none";
            }
            list_of_rootnames = list_of_rootnames +
                                thumbnails[i].getAttribute("data-file_root") +
                                '=' + thumbnails[i].getAttribute("data-exp_start") + ',';
        } else {
            thumbnails[i].style.display = "none";
        }
    }
    if (document.getElementById('no_thumbnails_msg') != null) {
        // If there are no thumbnails to display, tell the user
        if (num_thumbnails_displayed == 0) {
            document.getElementById('no_thumbnails_msg').style.display = 'inline-block';
        } else {
            document.getElementById('no_thumbnails_msg').style.display = 'none';
        }
    }

    // Update the count of how many images are being shown
    document.getElementById('img_shown').innerText = num_thumbnails_displayed;
    if (num_thumbnails_displayed) {
        // remove trailing ','.
        list_of_rootnames = list_of_rootnames.slice(0, -1);
        const csrftoken = getCookie('csrftoken');
        $.ajax({
            type: 'POST',
            url: base_url + '/ajax/navigate_filter/',
            headers: { "X-CSRFToken": csrftoken },
            data:{
                'navigate_dict': list_of_rootnames
            },
            error : function(response) {
                console.log("navigate_filter update failed");
            }
        });
    }
}


/**
 * Sort thumbnail display by proposal number
 * @param {String} sort_type - The sort type (e.g. "asc", "desc")
 */
function sort_by_proposals(sort_type) {
    // Update dropdown menu text
    document.getElementById('sort_dropdownMenuButton').innerHTML = sort_type;

    // Sort the thumbnails accordingly
    var props = $('div#proposal-array>div')
    if (sort_type == 'Ascending') {
        tinysort(props, {order:'asc'});
    } else if (sort_type == 'Descending') {
        tinysort(props, {order:'desc'});
    } else if (sort_type == 'Recent') {
        // Sort by the most recent Observation Start
        tinysort(props, {order:'desc', attr:'data-obs_time'});
    }
}


/**
 * Sort thumbnail display by a given sort type, save sort type in session for use in previous/next buttons
 * @param {String} sort_type - The sort type by file name
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function sort_by_thumbnails(sort_type, base_url) {

    // Update dropdown menu text
    document.getElementById('sort_dropdownMenuButton').innerHTML = sort_type;

    // Sort the thumbnails accordingly.  
    // Note: Because thumbnails will sort relating to their current order (when the exp_start is the same between thumbnails), we need to do multiple sorts to guarantee consistency.

    var thumbs = $('div#thumbnail-array>div')
    if (sort_type == 'Descending') {
        tinysort(thumbs, {attr:'data-file_root', order:'desc'});
    } else if (sort_type == 'Recent') {
        tinysort(thumbs, {attr:'data-exp_start', order:'desc'}, {attr:'data-file_root', order:'asc'});
    } else if (sort_type == 'Oldest') {
        tinysort(thumbs, {attr:'data-exp_start', order:'asc'}, {attr:'data-file_root', order:'asc'});
    } else {
        // Default to 'Ascending'
        tinysort(thumbs, {attr:'data-file_root', order:'asc'});
    }
    $.ajax({
        url: base_url + '/ajax/image_sort/',
        data: {
            'sort_type': sort_type
        },
        error : function(response) {
            console.log("session image sort update failed");
        }
    });
}


/**
 * Toggle a viewed button when pressed.  
 * Ajax call to update RootFileInfo model with toggled value
 * 
 * @param {String} file_root - The rootname of the file corresponding to the thumbnail
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function toggle_viewed(file_root, base_url) {
    // Toggle the button immediately so user isn't confused
    // (ajax result will confirm choice or fix on failure)
    var elem = document.getElementById("viewed");
    update_viewed_button(elem.value == "New" ? true : false);
    elem.disabled=true;
    
    // Ajax Call to update RootFileInfo model with "viewed" info
    $.ajax({
        url: base_url + '/ajax/viewed/' + file_root,
        success: function(data){
            // Update button with actual value (paranoia update, should not yield visible change)
            update_viewed_button(data["marked_viewed"]);
            elem.disabled=false;
        },
        error : function(response) {
            // If update fails put button back to original state
            update_viewed_button(elem.value == "New" ? false : true);
            elem.disabled=false;

        }
    });
}


/**
 * Set the viewed status for a group of files.
 * Ajax call to update RootFileInfo model with toggled value
 *
 * @param {String} group_root - The rootname of the exposure group
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function toggle_viewed_group(group_root, base_url) {
    // Toggle the button immediately so user isn't confused
    var elem = document.getElementById("viewed");
    var to_viewed = elem.value.includes('New');
    update_viewed_button(to_viewed, true);
    elem.disabled=true;

    // Ajax Call to update RootFileInfo model with "viewed" info
    $.ajax({
        url: base_url + '/ajax/viewed_group/' + group_root + '/' + (to_viewed ? 'viewed' : 'new'),
        success: function(data){
            // Update button with actual value (paranoia update, should not yield visible change)
            update_viewed_button(data["marked_viewed"], true);
            elem.disabled=false;
        },
        error : function(response) {
            // If update fails put button back to original state
            update_viewed_button(!to_viewed, true);
            elem.disabled=false;

        }
    });
}


/**
 * Download filtered data report
 * @param {String} inst - The instrument in use
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function download_report(inst, base_url) {
    var elem = document.getElementById('download_report_button');
    elem.disabled = true;

    // Get sort value
    var sort_option = document.getElementById('sort_dropdownMenuButton').innerText;
    var options = '?sort_as=' + sort_option.toLowerCase();

    // Get search value - use as proposal.startswith
    var search_value = document.getElementById("search_box").value;
    if (search_value != '') {
        options += '&proposal=' + search_value;
    }

    // Get all filter values
    var filter_div = document.getElementById('thumbnail-filter');
    var filters = filter_div.getElementsByClassName('dropdown-toggle');

    for (var i=0; i < filters.length; i++) {
        var name = filters[i].id.split('_dropdownMenuButton')[0];
        var status = filters[i].innerText.toLowerCase();
        if (!status.includes('all')) {
            options += '&' + name + '=' + status;
        }
    }
    var report_url = '/' + inst + '/report' + options;
    console.log('Redirecting to: ' + report_url);

    // Redirect to download content
    window.location = base_url + report_url;
    elem.disabled = false;
}

/**
 * Updates various components on the archive page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_archive_page(inst, base_url) {
    $.ajax({
        url: base_url + '/ajax/' + inst + '/archive/',
        success: function(data){

            // Update the number of proposals displayed
            var num_proposals = data.thumbnails.proposals.length;
            update_show_count(num_proposals, 'proposals')
            update_filter_options(data, base_url, 'proposal');

            // Add content to the proposal array div
            for (var i = 0; i < data.thumbnails.proposals.length; i++) {

                // Parse out useful variables
                var prop = data.thumbnails.proposals[i];
                var min_obsnum = data.min_obsnum[i];
                var thumb = data.thumbnails.thumbnail_paths[i];
                var n = data.thumbnails.num_files[i];
                var viewed = data.thumbnails.viewed[i];
                var exp_types = data.thumbnails.exp_types[i];
                var obs_time = data.thumbnails.obs_time[i];
                var cat_type = data.thumbnails.cat_types[i];

                // Build div content
                var content = '<div class="proposal text-center" data-look="' + viewed +
                              '" data-exp_type="' + exp_types + '" data-obs_time="' + obs_time +
                              '" data-cat_type="' + cat_type + '">';
                content += '<a href="/' + inst + '/archive/' + prop + '/obs' +
                           min_obsnum + '/" id="proposal' + (i + 1) + '" data-proposal="' + prop + '">';
                content += '<span class="helper"></span>'
                content += '<img src="/static/thumbnails/' + thumb +
                           '" alt="" title="Thumbnail for ' + prop +
                           '" width=100% style="max-height:100%">';
                content += '<div class="proposal-color-fill" ></div>';
                content += '<div class="proposal-info">';
                content += '<h3>' + prop + '</h3>';
                content += '<h6>' + n + ' Files</h6>';
                content += '</div></a></div>';

                // Add the content to the div
                $("#proposal-array")[0].innerHTML += content;

            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("proposal-array").style.display = "block";
            }
    }});
}


/**
 * Updates various components on the MSATA page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_msata_page(base_url) {
    $.ajax({
        url: base_url + '/ajax/nirspec/msata/',
        success: function(data){

            // Build div content
            var content = data["div"];
            content += data["script1"];
            content += data["script2"];

            /* Add the content to the div
            *    Note: <script> elements inserted via innerHTML are intentionally disabled/ignored by the browser.  Directly inserting script via jquery.
            */
            $('#ta_data').html(content);

            // Replace loading screen
            document.getElementById("loading").style.display = "none";
            document.getElementById("ta_data").style.display = "inline-block";
            document.getElementById('msata_fail').style.display = "none";
        },
        error : function(response) {
            document.getElementById("loading").style.display = "none";
            document.getElementById('msata_fail').style.display = "inline-block";
        }
    });
}


/**
 * Updates various components on the WATA page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_wata_page(base_url) {
    $.ajax({
        url: base_url + '/ajax/nirspec/wata/',
        success: function(data){

            // Build div content
            var content = data["div"];
            content += data["script1"];
            content += data["script2"];

            /* Add the content to the div
            *    Note: <script> elements inserted via innerHTML are intentionally disabled/ignored by the browser.  Directly inserting script via jquery.
            */
            $('#ta_data').html(content);

            // Replace loading screen
            document.getElementById("loading").style.display = "none";
            document.getElementById("ta_data").style.display = "inline-block";
            document.getElementById('wata_fail').style.display = "none";
        },
        error : function(response) {
            document.getElementById("loading").style.display = "none";
            document.getElementById('wata_fail').style.display = "inline-block";
        }
    });
}


/**
 * Updates various components on the thumbnails page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} file_root - The rootname of the file forresponding tot he instrument (e.g. "JW01473015001_04101_00001_MIRIMAGE")
 * @param {String} filetype - The type to be viewed (e.g. "cal" or "rate").
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {Boolean} do_opt_args - Flag to calculate and send optional arguments in URL
 */
 function update_explore_image_page(inst, file_root, filetype, base_url, do_opt_args=false) {

    /* if they exist set up the optional parameters before the ajax call*/
    var optional_params = "";
    if(do_opt_args) {
        // Reset loading
        document.getElementById("loading").style.display = "inline-block";
        document.getElementById("explore_image").style.display = "none";
        document.getElementById("explore_image_fail").style.display = "none";
        var calc_difference = document.getElementById("calcDifference").checked;

        // Get the arguments to update
        var scaling = get_radio_button_value("scaling");
        var low_lim = get_number_or_none("low_lim");
        var high_lim = get_number_or_none("high_lim");
        var ext_name = get_radio_button_value("extension");
        var int1_nr = get_number_or_none("integration1");
        var grp1_nr = get_number_or_none("group1");
        var int2_nr;
        var grp2_nr;
        if (calc_difference) {
            int2_nr = get_number_or_none("integration2");
            grp2_nr = get_number_or_none("group2");
        } else {
            int2_nr="None";
            grp2_nr="None";
        }
        optional_params = optional_params + "/scaling_" + scaling + "/low_" + low_lim + "/high_" + high_lim + "/ext_" + ext_name + "/int1_" + int1_nr + "/grp1_" + grp1_nr + "/int2_" + int2_nr + "/grp2_" + grp2_nr;
    }

    $.ajax({
        url: base_url + '/ajax/' + inst + '/' + file_root + '_' + filetype + '/explore_image' + optional_params,
        success: function(data){

            // Build div content
            var content = data["div"];
            content += data["script"];

            /* Add the content to the div
            *    Note: <script> elements inserted via innerHTML are intentionally disabled/ignored by the browser.  Directly inserting script via jquery.
            */
            $('#explore_image').html(content);

            // Replace loading screen
            document.getElementById("loading").style.display = "none";
            document.getElementById("explore_image").style.display = "inline-block";
            document.getElementById('explore_image_fail').style.display = "none";
        },
        error : function(response) {
            document.getElementById("loading").style.display = "none";
            document.getElementById('explore_image_fail').style.display = "inline-block";
        }
    });
}


/**
 * Updates the thumbnail-filter div with filter options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {String} thumbnail_class - the class name of the thumbnails that will be filtered
 */
 function update_filter_options(data, base_url, thumbnail_class) {
    var dropdown_key_list = Object.keys(data.dropdown_menus);
    var content = '<div class="d-inline" id="filter_by" data-dropdown-key-list="' +
                  dropdown_key_list + '" data-thumbnail-class="' +
                  thumbnail_class + '">Filter by:</div>';

    for (var i = 0; i < Object.keys(data.dropdown_menus).length; i++) {
        // Parse out useful variables
        var filter_type = Object.keys(data.dropdown_menus)[i];
        var filter_options = Array.from(new Set(data.dropdown_menus[filter_type]));

        // Build div content
        content += '<div style="display: flex">';
        content += '<div class="mr-4">';
        content += '<div class="dropdown">';
        content += '<button class="btn btn-primary dropdown-toggle" type="button" id="' + filter_type + '_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"> All ' + filter_type + 's </button>';
        content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
        content += '<a class="dropdown-item" href="#" onclick="show_only(\'' + filter_type + '\', \'All ' + filter_type + 's\', \'' + base_url + '\');">All ' + filter_type + 's</a>';

        for (var j = 0; j < filter_options.length; j++) {
            content += '<a class="dropdown-item" href="#" onclick="show_only(\'' + filter_type + '\', \'' + filter_options[j] + '\', \'' + base_url + '\');">' + filter_options[j] + '</a>';
        }

        content += '</div>';
        content += '</div></div>';
    }

    // Add the content to the div
    $("#thumbnail-filter")[0].innerHTML = content;
}

/**
 * Updates the group-by-exposure div
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_group_options(data, base_url) {

    // Build div content
    var content = '<div class="d-inline" id="group_by" data-ngroup="' +
                  data.exp_groups.length + '" data-nfile="' +
                  Object.keys(data.file_data).length + '">Group by:<br></div>';
    content += '<button class="btn btn-primary dropdown-toggle" type="button" id="group_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">' + data.thumbnail_group + '</button>';
    content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
    content += '<a class="dropdown-item" href="#" onclick="group_by_thumbnails(\'Exposure\', \'' + base_url + '\');">Exposure</a>';
    content += '<a class="dropdown-item" href="#" onclick="group_by_thumbnails(\'File\', \'' + base_url + '\');">File</a>';
    content += '</div></div>';
    // Add the content to the div
    $("#group-by-exposure")[0].innerHTML = content;
}



/**
 * Change the header extension displayed
 * @param {String} extension - The extension of the header selected
  * @param {String} num_extensions - The total number of extensions
 */
function update_header_display(extension, num_extensions) {

    // Hide all headers
    for (var i = 0; i < num_extensions; i++) {
        var header_name = document.getElementById("header-display-name-extension" + i);
        var header_table = document.getElementById("header-table-extension" + i);
        header_name.style.display = 'none';
        header_table.style.display = 'none';
    }

    // Display the header selected
    var header_name_to_show = document.getElementById("header-display-name-extension" + extension);
    var header_table_to_show = document.getElementById("header-table-extension" + extension);
    header_name_to_show.style.display = 'inline';
    header_table_to_show.style.display = 'inline';

}


/**
 * Updates the obs-list div with observation number options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 * @param {String} inst - Instrument name
 * @param {String} prop - Proposal ID
 * @param {List} obslist - List of observation number strings
 */
function update_obs_options(data, inst, prop, observation) {
    // Build div content
    var content = 'Available observations:';
    content += '<div class="dropdown">';
    content += '<button class="btn btn-primary dropdown-toggle" type="button" id="obs_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Obs' + observation + '</button>';
    content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
    for (var i = 0; i < data.obs_list.length; i++) {
        content += '<a class="dropdown-item" href="/' + inst + '/archive/' + prop + '/obs' + data.obs_list[i] + '/" > Obs' + data.obs_list[i] + '</a>';
    }
    content += '</div></div>';

    // Add the content to the div
    $("#obs-list")[0].innerHTML = content;
}

/**
 * Updates the img_show_count component
 * @param {Integer} count - The count to display
 * @param {String} type - The type of the count (e.g. "activities")
 */
function update_show_count(count, type) {
    var content = 'Showing <a id="img_shown">' + count + '</a> / <a id="img_total">' + count + '</a> <a id="img_type">' + type + '</a>';
    content += '<a href="https://jwst-pipeline.readthedocs.io/en/latest/jwst/data_products/science_products.html" target="_blank" style="color: black">';
    content += '<span class="help-tip mx-2">i</span></a>';
    $("#img_show_count")[0].innerHTML = content;
}

/**
 * Updates the thumbnail-sort div with sorting options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_sort_options(data, base_url) {

    // Build div content
    var content = 'Sort by:';
    content += '<div class="dropdown">';
    content += '<button class="btn btn-primary dropdown-toggle" type="button" id="sort_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">' + data.thumbnail_sort + '</button>';
    content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Ascending\', \'' + base_url + '\');">Ascending</a>';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Descending\', \'' + base_url + '\');">Descending</a>';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Recent\', \'' + base_url + '\');">Recent</a>';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Oldest\', \'' + base_url + '\');">Oldest</a>';
    content += '</div></div>';

    // Add the content to the div
    $("#thumbnail-sort")[0].innerHTML = content;
}

/**
 * Updates the thumbnail-array div with interactive images of thumbnails
 * @param {Object} data - The data returned by the update_thumbnails_per_observation_page/update_thumbnails_query_page AJAX methods
 */
function update_thumbnail_array(data) {

    // Add content to the thumbnail array div
    var thumbnail_content = "";
    var image_updates = [];
    for (var i = 0; i < Object.keys(data.file_data).length; i++) {
        
        // Parse out useful variables
        var rootname = Object.keys(data.file_data)[i];
        var file = data.file_data[rootname];
        var viewed = file.viewed;
        var exp_type = file.exp_type;
        var filename_dict = file.filename_dict;

        // Build div content
        var instrument;
        if (data.inst != "all") {
            instrument = data.inst;
        } else {
            instrument = filename_dict.instrument;
        }
        var content = '<div class="thumbnail" data-instrument="' + instrument +
                      '" data-detector="' + filename_dict.detector + '" data-proposal="' + filename_dict.program_id +
                      '" data-file_root="' + rootname + '" data-group_root="' + filename_dict.group_root +
                      '" data-exp_start="' + file.expstart + '" data-look="' + viewed + '" data-exp_type="' + exp_type + '">';
        content += '<div class="thumbnail-group">'
        content += '<a class="thumbnail-link" href="#" data-image-href="/' +
                   instrument + '/' + rootname + '/" data-group-href="/' +
                   instrument + '/exposure/' + filename_dict.group_root +  '">';
        content += '<span class="helper"></span>'

        // Make sure thumbnail img always has a src and alt
        content += '<img id="thumbnail' + i +
                   '" src="/static/img/default_thumb.png" ' +
                   'alt="Thumbnail for file ' + rootname + '">';
        content += '<div class="thumbnail-color-fill" ></div>';
        content += '<div class="thumbnail-info">';
        content += 'Proposal: ' + filename_dict.program_id + '<br>';
        content += 'Observation: ' + filename_dict.observation + '<br>';
        content += 'Visit: ' + filename_dict.visit + '<br>';
        content += 'Detector: ' + filename_dict.detector + '<br>';
        content += 'Exp_Start: ' + file.expstart_iso + '<br>';
        content += '</div></a></div></div>';

        // Add the content to the div
        thumbnail_content += content;

        // Add the appropriate image to the thumbnail
        if (file.thumbnail != 'none') {
            var jpg_path = '/static/thumbnails/' + parse_filename(rootname).program +
                           '/' + file.thumbnail;
            image_updates.push([i, jpg_path]);
        }
    }
    $("#thumbnail-array")[0].innerHTML = thumbnail_content;
    insert_thumbnail_images(image_updates);
}

/**
 * Read and submit the form for archive date ranges.
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function submit_date_range_form(inst, base_url, group) {

    var start_date = document.getElementById("start_date_range").value;
    var stop_date = document.getElementById("stop_date_range").value;

    if (!start_date) {
        alert("You must enter a Start Date/Time");
    }  else if (!stop_date) {
        alert("You must enter a Stop Date/Time");
    } else if (start_date >= stop_date) {
        alert("Start Time must be earlier than Stop Time");
    } else {
        document.getElementById("loading").style.display = "block";
        document.getElementById("thumbnail-array").style.display = "none";
        document.getElementById("no_thumbnails_msg").style.display = "none";
        $.ajax({
            url: base_url + '/ajax/' + inst + '/archive_date_range/start_date_' + start_date + '/stop_date_' + stop_date,
            success: function(data){
                var show_thumbs = true;
                var num_thumbnails = Object.keys(data.file_data).length;
                // verify we want to continue with results
                if (num_thumbnails > 1000) {
                    show_thumbs = false;
                    alert("Returning " + num_thumbnails + " images reduce your date/time range for page to load correctly");
                }
                if (show_thumbs) {
                    // Handle DIV updates
                    // Clear our existing array
                    $("#thumbnail-array")[0].innerHTML = "";
                    if (num_thumbnails > 0) {
                        update_show_count(num_thumbnails, 'activities');
                        update_thumbnail_array(data);
                        update_filter_options(data, base_url, 'thumbnail');
                        update_group_options(data, base_url);
                        update_sort_options(data, base_url);

                        // Do initial sort and group to match sort button display
                        group_by_thumbnails(group, base_url);
                        sort_by_thumbnails(data.thumbnail_sort, base_url);

                        // Replace loading screen with the proposal array div
                        document.getElementById("loading").style.display = "none";
                        document.getElementById("thumbnail-array").style.display = "block";
                        document.getElementById("no_thumbnails_msg").style.display = "none";
                    } else {
                        show_thumbs = false;
                    }
                } 
                if (!show_thumbs) {
                    document.getElementById("loading").style.display = "none";
                    document.getElementById("no_thumbnails_msg").style.display = "inline-block";
                }

            },
            error : function(response) {
                document.getElementById("loading").style.display = "none";
                document.getElementById("thumbnail-array").style.display = "none";
                document.getElementById("no_thumbnails_msg").style.display = "inline-block";
    
            }
        });
    }
}


/**
 * Updates various components on the thumbnails page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} proposal - The proposal number of interest (e.g. "88660")
 * @param {String} observation - The observation number within the proposal (e.g. "001")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {String} sort - Sort method string saved in session data image_sort
 * @param {String} group - Group method string saved in session data image_group
 */
function update_thumbnails_per_observation_page(inst, proposal, observation, base_url, sort, group) {
    $.ajax({
        url: base_url + '/ajax/' + inst + '/archive/' + proposal + '/obs' + observation + '/',
        success: function(data){
            // Perform various updates to divs
            var num_thumbnails = Object.keys(data.file_data).length;
            update_show_count(num_thumbnails, 'activities');
            update_thumbnail_array(data);
            update_obs_options(data, inst, proposal, observation);
            update_filter_options(data, base_url, 'thumbnail');
            update_group_options(data, base_url);
            update_sort_options(data, base_url);

            // Do initial sort and group to match sort button display
            group_by_thumbnails(group, base_url);
            sort_by_thumbnails(sort, base_url);

            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("thumbnail-array").style.display = "block";
        }});
}

/**
 * Updates various components on the thumbnails anomaly query page
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {String} sort - Sort method string saved in session data image_sort
 */
function update_thumbnails_query_page(base_url, sort, group) {
    $.ajax({
        url: base_url + '/ajax/query_submit/',
        success: function(data){
            // Perform various updates to divs
            var num_thumbnails = Object.keys(data.file_data).length;
            update_show_count(num_thumbnails, 'activities');
            update_thumbnail_array(data);
            update_filter_options(data, base_url, 'thumbnail');
            update_group_options(data, base_url);
            update_sort_options(data, base_url);

            // Do initial sort and group to match sort button display
            group_by_thumbnails(group, base_url);
            sort_by_thumbnails(sort, base_url);

            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("thumbnail-array").style.display = "block";
        }});
}


/**
 * Construct the URL for viewing/exploring a selected image on the exposure page
 */
function update_view_explore_link() {
    var types = ['header', 'explore_image'];
    for (var i = 0; i < types.length; i++) {
        var type = types[i];
        var file_selected = document.getElementById('fits_file_select');
        var link_button = document.getElementById(type);

        // Disable the button if the file isn't available
        if (file_selected.options[file_selected.selectedIndex].disabled) {
            link_button.href = '#';
            link_button.classList.add('disabled_button');
        } else {
            // Update the link to the current setting
            link_button.href = '/' + file_selected.value + '/' + type + '/';
            link_button.classList.remove('disabled_button');
        }
    }
}


function update_viewed_button(viewed, group=false) {
    var elem = document.getElementById("viewed");
    if (viewed) {
        elem.classList.add("btn-outline-primary")
        if (group) {
            elem.value = "Viewed Group";
        } else {
            elem.value = "Viewed";
        }
    } else {
        elem.classList.remove("btn-outline-primary")
        if (group) {
            elem.value = "New Group";
        } else {
            elem.value = "New";
        }
    }
}

/**
 * Construct the URL corresponding to a specific GitHub release
 * @param {String} version_string - The x.y.z version number
 */
function version_url(version_string) {
    var a_line = 'Running <a href="https://github.com/spacetelescope/jwql/releases/tag/';
    a_line += version_string;
    a_line += '">JWQL v' + version_string + '</a>';
    return a_line;
}
