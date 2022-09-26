/**
 * Various JS functions to support the JWQL web application.
 *
 * @author Lauren Chambers
 * @author Matthew Bourque
 * @author Brad Sappington
 * @author Bryan Hilbert
 * @author Maria Pena-Guerrero
 */

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

    // Clean the input parameters
    var num_ints = num_ints.replace(/&#39;/g, '"');
    var num_ints = num_ints.replace(/'/g, '"');
    var num_ints = JSON.parse(num_ints);

    // Get the available integration jpg numbers
    var available_ints = available_ints.replace(/&#39;/g, '"');
    var available_ints = available_ints.replace(/'/g, '"');
    var available_ints = JSON.parse(available_ints)[type];

    // Get the total number of integrations
    var total_ints = total_ints.replace(/&#39;/g, '"');
    var total_ints = total_ints.replace(/'/g, '"');
    var total_ints = JSON.parse(total_ints);

    // Propogate the text fields showing the filename and APT parameters
    var fits_filename = file_root + '_' + type;
    document.getElementById("jpg_filename").innerHTML = file_root + '_' + type + '_integ0.jpg';
    document.getElementById("fits_filename").innerHTML = fits_filename + '.fits';
    document.getElementById("proposal").innerHTML = file_root.slice(2,7);
    document.getElementById("obs_id").innerHTML = file_root.slice(7,10);
    document.getElementById("visit_id").innerHTML = file_root.slice(10,13);
    document.getElementById("detector").innerHTML = file_root.split('_')[3];

    // Show the appropriate image
    var img = document.getElementById("image_viewer");
    var jpg_filepath = '/static/preview_images/' + file_root.slice(0,7) + '/' + file_root + '_' + type + '_integ0.jpg';
    img.src = jpg_filepath;
    img.alt = jpg_filepath;
    // if previous image had error, remove error sizing
    img.classList.remove("thumbnail");

    // Reset the slider values
    document.getElementById("slider_range").value = 1;
    document.getElementById("slider_range").max = num_ints[type];
    document.getElementById("slider_val").innerHTML = 1;
    document.getElementById("total_ints").innerHTML = total_ints[type];

    // Update the integration changing buttons
    if (num_ints[type] > 1) {
        document.getElementById("int_after").disabled = false;
    } else {
        document.getElementById("int_after").disabled = true;
    }

    // Update the image download and header links
    // document.getElementById("download_fits").href = '/static/filesystem/' + file_root.slice(0,7) + '/' + fits_filename + '.fits';
    // document.getElementById("download_jpg").href = jpg_filepath;
    document.getElementById("view_header").href = '/' + inst + '/' + file_root + '_' + type + '/header/';
    document.getElementById("explore_image").href = '/' + inst + '/' + file_root + '_' + type + '/explore_image/';

    // Disable the "left" button, since this will be showing integ0
    document.getElementById("int_before").disabled = true;

};


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
function change_int(file_root, num_ints, available_ints, method, direction = 'right') {

    // Figure out the current image and integration
    var suffix = document.getElementById("jpg_filename").innerHTML.split('_');
    var integration = Number(suffix[suffix.length - 1].replace('.jpg','').replace('integ',''))
    var suffix = suffix[suffix.length - 2];
    var program = file_root.slice(0,7);

    // Find the total number of integrations for the current image
    var num_ints = num_ints.replace(/'/g, '"');
    var num_ints = JSON.parse(num_ints)[suffix];

    // Get the available integration jpg numbers and the current integration index
    var available_ints = available_ints.replace(/'/g, '"');
    var available_ints = JSON.parse(available_ints)[suffix];
    var current_index = available_ints.indexOf(integration);

    // Get the desired integration value
    switch (method) {
        case "button":
            if ((integration == num_ints - 1 && direction == 'right')||
                (integration == 0 && direction == 'left')) {
                return;
            } else if (direction == 'right') {
                new_integration = available_ints[current_index + 1]
            } else if (direction == 'left') {
                new_integration = available_ints[current_index - 1]
            }
            break;
        case "slider":
            new_integration = available_ints[document.getElementById("slider_range").value - 1];
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

    // Update the JPG filename
    var jpg_filename = file_root + '_' + suffix + '_integ' + new_integration + '.jpg'
    var jpg_filepath = '/static/preview_images/' + program + '/' + jpg_filename
    document.getElementById("jpg_filename").innerHTML = jpg_filename;

    // Show the appropriate image
    var img = document.getElementById("image_viewer")
    img.src = jpg_filepath;
    img.alt = jpg_filepath;

    // Update the jpg download link
    // document.getElementById("download_jpg").href = jpg_filepath;

    // Update the slider values
    document.getElementById("slider_range").value = new_integration + 1
    document.getElementById("slider_val").innerHTML = new_integration + 1
};


/**
 * Determine what filetype to use for a thumbnail
 * @param {String} thumbnail_dir - The path to the thumbnail directory
 * @param {List} suffixes - A list of available suffixes for the file of interest
 * @param {Integer} i - The index of the thumbnail
 * @param {String} file_root - The rootname of the file corresponding to the thumbnail
 */
function determine_filetype_for_thumbnail(thumbnail_dir, thumb_filename, i, file_root) {

    // Update the thumbnail filename
    var img = document.getElementById('thumbnail'+i);
    if (thumb_filename != 'none') {
        var jpg_path = thumbnail_dir + file_root.slice(0,7) + '/' + thumb_filename;
        img.src = jpg_path
    };

};


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
        };
    };
};

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
    var url_end = url_split[url_split.length - 1];
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
        };
    };
};

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
    ext_name = get_radio_button_value("extension");

    // Clean the input parameters and get our integrations/groups for this extension
    var calc_difference = false;
    var integrations = integrations.replace(/&#39;/g, '"');
    var integrations = integrations.replace(/'/g, '"');
    var integrations = JSON.parse(integrations)[ext_name];
    var groups = groups.replace(/&#39;/g, '"');
    var groups = groups.replace(/'/g, '"');
    var groups = JSON.parse(groups)[ext_name];
    
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
 * get_radio_button_value
 * @param {String} element_name - The name of the radio buttons
 * @returns value - value of checked radio button
 */
function get_radio_button_value(element_name) {
    var element = document.getElementsByName(element_name);

    for(i = 0; i < element.length; i++) {
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
    var n_proposals = document.getElementsByClassName("proposal").length;

    // Determine the current search value
    var search_value = document.getElementById("search_box").value;

    // Determine whether or not to display each thumbnail
    var num_proposals_displayed = 0;
    for (i = 0; i < proposals.length; i++) {
        // Evaluate if the proposal number matches the search
        var j = i + 1
        var prop_name = document.getElementById("proposal" + j).getAttribute('proposal')
        var prop_num = Number(prop_name)


        if (prop_name.startsWith(search_value) || prop_num.toString().startsWith(search_value)) {
            proposals[i].style.display = "inline-block";
            num_proposals_displayed++;
        } else {
            proposals[i].style.display = "none";
        }
    };

    // If there are no proposals to display, tell the user
    if (num_proposals_displayed == 0) {
        document.getElementById('no_proposals_msg').style.display = 'inline-block';
    } else {
        document.getElementById('no_proposals_msg').style.display = 'none';
    };

    // Update the count of how many images are being shown
    document.getElementById('img_show_count').innerHTML = 'Showing ' + num_proposals_displayed + '/' + n_proposals + ' proposals';
};


/**
 * Limit the displayed thumbnails based on filter criteria
 * @param {String} filter_type - The filter type.  Currently only "sort" is supported.
 * @param {Integer} value - The filter value
 * @param {List} dropdown_keys - A list of dropdown menu keys
 * @param {Integer} num_fileids - The number of files that are available to display
 */
function show_only(filter_type, value, dropdown_keys, num_fileids) {

    // Get all filter options from {{dropdown_menus}} variable
    var all_filters = dropdown_keys.split(',');

    // Update dropdown menu text
    document.getElementById(filter_type + '_dropdownMenuButton').innerHTML = value;

    // Determine the current value for each filter
    var filter_values = [];
    for (j = 0; j < all_filters.length; j++) {
        var filter_value = document.getElementById(all_filters[j] + '_dropdownMenuButton').innerHTML;
        filter_values.push(filter_value);
    }


    // Find all thumbnail elements
    var thumbnails = document.getElementsByClassName("thumbnail");

    // Determine whether or not to display each thumbnail
    var num_thumbnails_displayed = 0;
    for (i = 0; i < thumbnails.length; i++) {
        // Evaluate if the thumbnail meets all filter criteria
        var criteria = [];
        for (j = 0; j < all_filters.length; j++) {
            var criterion = (filter_values[j].indexOf('All '+ all_filters[j] + 's') >=0) || (thumbnails[i].getAttribute(all_filters[j]) == filter_values[j]);
            criteria.push(criterion);
        };

        // Only display if all filter criteria are met
        if (criteria.every(function(r){return r})) {
            thumbnails[i].style.display = "inline-block";
            num_thumbnails_displayed++;
        } else {
            thumbnails[i].style.display = "none";
        }
    };

    // If there are no thumbnails to display, tell the user
    if (num_thumbnails_displayed == 0) {
        document.getElementById('no_thumbnails_msg').style.display = 'inline-block';
    } else {
        document.getElementById('no_thumbnails_msg').style.display = 'none';
    };

    // Update the count of how many images are being shown
    document.getElementById('img_show_count').innerHTML = 'Showing ' + num_thumbnails_displayed + '/' + num_fileids + ' activities'
};

/**
 * Limit the displayed thumbnails based on filter criteria
 * @param {String} filter_type - The filter type.  Currently only "sort" is supported.
 * @param {Integer} value - The filter value
 * @param {List} dropdown_keys - A list of dropdown menu keys
 * @param {Integer} num_fileids - The number of files that are available to display
 */
function show_only(filter_type, value, dropdown_keys, num_fileids) {

    // Get all filter options from {{dropdown_menus}} variable
    var all_filters = dropdown_keys.split(',');

    // Update dropdown menu text
    document.getElementById(filter_type + '_dropdownMenuButton').innerHTML = value;

    // Determine the current value for each filter
    var filter_values = [];
    for (j = 0; j < all_filters.length; j++) {
        var filter_value = document.getElementById(all_filters[j] + '_dropdownMenuButton').innerHTML;
        filter_values.push(filter_value);
    }


    // Find all thumbnail elements
    var thumbnails = document.getElementsByClassName("thumbnail");

    // Determine whether or not to display each thumbnail
    var num_thumbnails_displayed = 0;
    for (i = 0; i < thumbnails.length; i++) {
        // Evaluate if the thumbnail meets all filter criteria
        var criteria = [];
        for (j = 0; j < all_filters.length; j++) {
            var criterion = (filter_values[j].indexOf('All '+ all_filters[j] + 's') >=0) 
                          || check_attribute_vs_filter(all_filters[j], thumbnails[i].getAttribute(all_filters[j]), filter_values[j]);
            criteria.push(criterion);
        };

        // Only display if all filter criteria are met
        if (criteria.every(function(r){return r})) {
            thumbnails[i].style.display = "inline-block";
            num_thumbnails_displayed++;
        } else {
            thumbnails[i].style.display = "none";
        }
    };

    // If there are no thumbnails to display, tell the user
    if (num_thumbnails_displayed == 0) {
        document.getElementById('no_thumbnails_msg').style.display = 'inline-block';
    } else {
        document.getElementById('no_thumbnails_msg').style.display = 'none';
    };

    // Update the count of how many images are being shown
    document.getElementById('img_show_count').innerHTML = 'Showing ' + num_thumbnails_displayed + '/' + num_fileids + ' activities'
};

/**
 * Limit the displayed thumbnails based on filter criteria
 * @param {String} filter_type - The filter type.
 * @param {String} attribute - HTML attribute to compare against filter
 * @param {String} filter_value - The filter value
 */
 function check_attribute_vs_filter(filter_type, attribute, filter_value) {

    // 'look' filter is boolean, convert selections to comparable attributes.
    // If different filter, just do a direct comparison
    if (filter_type == 'look') {
        if (filter_value == 'Viewed') {
            filter_value = "true";
        } else {
            filter_value = "false";
        }
    }
    return (attribute == filter_value);
    
};


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
    }
};


/**
 * Sort thumbnail display by a given sort type
 * @param {String} sort_type - The sort type (e.g. file_root", "exp_start")
 */
function sort_by_thumbnails(sort_type) {

    // Update dropdown menu text
    document.getElementById('sort_dropdownMenuButton').innerHTML = sort_type;

    // Sort the thumbnails accordingly
    var thumbs = $('div#thumbnail-array>div')
    if (sort_type == 'Name') {
        tinysort(thumbs, {attr:'file_root'});
    } else if (sort_type == 'Default') {
        tinysort(thumbs, {selector: 'img', attr:'id'});
    } else if (sort_type == 'Exposure Start Time') {
        tinysort(thumbs, {attr:'exp_start'});
    }
};


function toggle_viewed(file_root, base_url) {
    $.ajax({
        url: base_url + '/ajax/viewed/' + file_root,
        success: function(data){
            update_viewed_button(data["marked_viewed"])
    }});
}


/**
 * Updates various compnents on the archive page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_archive_page(inst, base_url) {
    $.ajax({
        url: base_url + '/ajax/' + inst + '/archive/',
        success: function(data){

            // Update the number of proposals displayed
            num_proposals = data.thumbnails.proposals.length;
            update_show_count(num_proposals, 'proposals')

            // Add content to the proposal array div
            for (var i = 0; i < data.thumbnails.proposals.length; i++) {

                // Parse out useful variables
                prop = data.thumbnails.proposals[i];
                min_obsnum = data.min_obsnum[i];
                thumb = data.thumbnails.thumbnail_paths[i];
                n = data.thumbnails.num_files[i];

                // Build div content
                content = '<div class="proposal text-center">';
                content += '<a href="/' + inst + '/archive/' + prop + '/obs' + min_obsnum + '/" id="proposal' + (i + 1) + '" proposal="' + prop + '"';
                content += '<span class="helper"></span>'
                content += '<img src="/static/thumbnails/' + thumb + '" alt="" title="Thumbnail for ' + prop + '" width=100%>';
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
            };
    }});
};


/**
 * Updates various compnents on the MSATA page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_msata_page(base_url) {
    $.ajax({
        url: base_url + '/ajax/nirspec/msata/',
        success: function(data){

            // Build div content
            content = data["div"];
            content += data["script"];

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
};


/**
 * Updates various compnents on the WATA page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_wata_page(base_url) {
    $.ajax({
        url: base_url + '/ajax/nirspec/wata/',
        success: function(data){

            // Build div content
            content = data["div"];
            content += data["script"];

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
};


/**
 * Updates various compnents on the thumbnails page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} file_root - The rootname of the file forresponding tot he instrument (e.g. "JW01473015001_04101_00001_MIRIMAGE")
 * @param {String} filetype - The type to be viewed (e.g. "cal" or "rate").
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {Boolean} do_opt_args - Flag to calculate and send optional arguments in URL
 */
 function update_explore_image_page(inst, file_root, filetype, base_url, do_opt_args=false) {

    /* if they exist set up the optional parameters before the ajax call*/
    optional_params = "";
    if(do_opt_args) {
        // Reset loading
        document.getElementById("loading").style.display = "inline-block";
        document.getElementById("explore_image").style.display = "none";
        document.getElementById("explore_image_fail").style.display = "none";
        calc_difference = document.getElementById("calcDifference").checked;

        // Get the arguments to update
        scaling = get_radio_button_value("scaling");
        low_lim = get_number_or_none("low_lim");
        high_lim = get_number_or_none("high_lim");
        ext_name = get_radio_button_value("extension");
        int1_nr = get_number_or_none("integration1");
        grp1_nr = get_number_or_none("group1");
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
            content = data["div"];
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
};

/**
 * Updates the thumbnail-filter div with filter options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 */
function update_filter_options(data) {
    content = 'Filter by:'
    for (var i = 0; i < Object.keys(data.dropdown_menus).length; i++) {
        // Parse out useful variables
        filter_type = Object.keys(data.dropdown_menus)[i];
        filter_options = Array.from(new Set(data.dropdown_menus[filter_type]));
        num_rootnames = Object.keys(data.file_data).length;
        dropdown_key_list = Object.keys(data.dropdown_menus);

        // Build div content
        content += '<div style="display: flex">';
        content += '<div class="mr-4">';
        content += '<div class="dropdown">';
        content += '<button class="btn btn-primary dropdown-toggle" type="button" id="' + filter_type + '_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false"> All ' + filter_type + 's </button>';
        content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
        content += '<a class="dropdown-item" href="#" onclick="show_only(\'' + filter_type + '\', \'All ' + filter_type + 's\', \'' + dropdown_key_list + '\',\'' + num_rootnames + '\');">All ' + filter_type + 's</a>';

        for (var j = 0; j < filter_options.length; j++) {
            content += '<a class="dropdown-item" href="#" onclick="show_only(\'' + filter_type + '\', \'' + filter_options[j] + '\', \'' + dropdown_key_list + '\', \'' + num_rootnames + '\');">' + filter_options[j] + '</a>';
        };

        content += '</div>';
        content += '</div></div>';
    };

    // Add the content to the div
    $("#thumbnail-filter")[0].innerHTML = content;
};

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
    };

    // Display the header selected
    var header_name_to_show = document.getElementById("header-display-name-extension" + extension);
    var header_table_to_show = document.getElementById("header-table-extension" + extension);
    header_name_to_show.style.display = 'inline';
    header_table_to_show.style.display = 'inline';

};

/**
 * Updates the obs-list div with observation number options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 * @param {String} inst - Instrument name
 * @param {String} prop - Proposal ID
 * @param {List} obslist - List of observation number strings
 */
function update_obs_options(data, inst, prop, obslist) {
    // Build div content
    content = 'Available observations:';
    content += '<div class="dropdown">';
    content += '<button class="btn btn-primary dropdown-toggle" type="button" id="obs_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Obs Nums</button>';
    content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
    for (var i = 0; i < data.obs_list.length; i++) {
        content += '<a class="dropdown-item" href="/' + inst + '/archive/' + prop + '/obs' + data.obs_list[i] + '/" > Obs' + data.obs_list[i] + '</a>';
    }
    content += '</div></div>';

    // Add the content to the div
    $("#obs-list")[0].innerHTML = content;
};

/**
 * Updates the img_show_count component
 * @param {Integer} count - The count to display
 * @param {String} type - The type of the count (e.g. "activities")
 */
function update_show_count(count, type) {
    content = 'Showing ' + count + '/' + count + ' ' + type;
    content += '<a href="https://jwst-pipeline.readthedocs.io/en/latest/jwst/data_products/science_products.html" target="_blank" style="color: black">';
    content += '<span class="help-tip mx-2">i</span></a>';
    $("#img_show_count")[0].innerHTML = content;
};

/**
 * Updates the thumbnail-sort div with sorting options
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 */
function update_sort_options(data) {

    // Build div content
    content = 'Sort by:';
    content += '<div class="dropdown">';
    content += '<button class="btn btn-primary dropdown-toggle" type="button" id="sort_dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Default</button>';
    content += '<div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Default\');">Default</a>';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Name\');">Name</a>';
    content += '<a class="dropdown-item" href="#" onclick="sort_by_thumbnails(\'Exposure Start Time\');">Exposure Start Time</a>';
    content += '</div></div>';

    // Add the content to the div
    $("#thumbnail-sort")[0].innerHTML = content;
};

/**
 * Updates the thumbnail-array div with interactive images of thumbnails
 * @param {Object} data - The data returned by the update_thumbnails_page AJAX method
 */
function update_thumbnail_array(data) {

      // Add content to the thumbail array div
    for (var i = 0; i < Object.keys(data.file_data).length; i++) {

        // Parse out useful variables
        rootname = Object.keys(data.file_data)[i];
        file = data.file_data[rootname];
        viewed = file.viewed;
        filename_dict = file.filename_dict;

        // Build div content
        if (data.inst!="all") {
            content = '<div class="thumbnail" instrument = ' + data.inst + ' detector="' + filename_dict.detector + '" proposal="' + filename_dict.program_id + '" file_root="' + rootname + '", exp_start="' + file.expstart + '" look="' + viewed + '">';
            content += '<a href="/' + data.inst + '/' + rootname + '/">';
        } else {
            content = '<div class="thumbnail" instrument = ' +filename_dict.instrument + ' detector="' + filename_dict.detector + '" proposal="' + filename_dict.program_id + '" file_root="' + rootname + '", exp_start="' + file.expstart + '" look="' + viewed + '">';
            content += '<a href="/' + filename_dict.instrument + '/' + rootname + '/">';
        }
        content += '<span class="helper"></span><img id="thumbnail' + i + '" onerror="image_error(this);">';
        content += '<div class="thumbnail-color-fill" ></div>';
        content += '<div class="thumbnail-info">';
        content += 'Proposal: ' + filename_dict.program_id + '<br>';
        content += 'Observation: ' + filename_dict.observation + '<br>';
        content += 'Visit: ' + filename_dict.visit + '<br>';
        content += 'Detector: ' + filename_dict.detector + '<br>';
        content += 'Exp_Start: ' + file.expstart_iso + '<br>';
        content += '</div></a></div>';

        // Add the content to the div
        $("#thumbnail-array")[0].innerHTML += content;

        // Add the appropriate image to the thumbnail
        determine_filetype_for_thumbnail('/static/thumbnails/' , file.thumbnail, i, rootname);
    };
};

/**
 * Updates various compnents on the thumbnails page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} proposal - The proposal number of interest (e.g. "88660")
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_thumbnails_page(inst, proposal, base_url) {
    $.ajax({
        url: base_url + '/ajax/' + inst + '/archive/' + proposal + '/',
        success: function(data){
            // Perform various updates to divs
            update_show_count(Object.keys(data.file_data).length, 'activities');
            update_thumbnail_array(data);
            update_filter_options(data);
            update_sort_options(data);

            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("thumbnail-array").style.display = "block";
        }});
};

/**
 * Updates various compnents on the thumbnails page
 * @param {String} inst - The instrument of interest (e.g. "FGS")
 * @param {String} proposal - The proposal number of interest (e.g. "88660")
 * @param {String} observation - The observation number within the proposal (e.g. "001")
 * @param {List} observation_list - List of all observations in this proposal
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 */
function update_thumbnails_per_observation_page(inst, proposal, observation, observation_list, base_url) {
    $.ajax({
        url: base_url + '/ajax/' + inst + '/archive/' + proposal + '/obs' + observation + '/',
        success: function(data){
            // Perform various updates to divs
            update_show_count(Object.keys(data.file_data).length, 'activities');
            update_thumbnail_array(data);
            update_obs_options(data, inst, proposal);
            update_filter_options(data);
            update_sort_options(data);

            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("thumbnail-array").style.display = "block";
        }});
};

/**
 * Updates various components on the thumbnails anomaly query page
 * @param {String} base_url - The base URL for gathering data from the AJAX view.
 * @param {List} rootnames
 */
function update_thumbnails_query_page(base_url) {
    $.ajax({
        url: base_url + '/ajax/query_submit/',
        success: function(data){
            // Perform various updates to divs
            update_show_count(Object.keys(data.file_data).length, 'activities');
            update_thumbnail_array(data);
            update_filter_options(data);
            update_sort_options(data);
            // Replace loading screen with the proposal array div
            document.getElementById("loading").style.display = "none";
            document.getElementById("thumbnail-array").style.display = "block";
        }});
};

function update_viewed_button(viewed) {
    var elem = document.getElementById("viewed");
    if (viewed) {
        elem.classList.add("btn-outline-primary")
        elem.value = "Viewed";
    } else {
        elem.classList.remove("btn-outline-primary")
        elem.value = "New";
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
};
