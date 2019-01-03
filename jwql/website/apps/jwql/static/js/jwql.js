// JS function to determine what filetype to use for the thumbnail
function determine_filetype_for_thumbnail(thumbnail_dir, suffixes, i, file_root) {

    // Update the thumbnail to show the most processed filetype
    var img = document.getElementById('thumbnail'+i);
    if (suffixes.indexOf("cal") >= 0) {
        var jpg_path = thumbnail_dir + file_root.slice(0,7) + '/' + file_root + '_cal_integ0.thumb';
        img.src = jpg_path;
    } else if (suffixes.indexOf("rate") >= 0) {
        var jpg_path = thumbnail_dir + file_root.slice(0,7) + '/' + file_root + '_rate_integ0.thumb';
        img.src = jpg_path;
    } else if (suffixes.indexOf("uncal") >= 0) {
        var jpg_path = thumbnail_dir + file_root.slice(0,7) + '/' + file_root + '_uncal_integ0.thumb';
        img.src = jpg_path;
    }
};


// JS function to determine whether the page is archived or unlooked
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
    document.getElementById('title').innerHTML = final_title;
    if (document.title != final_title) {
        document.title = final_title;
    }
};


function search(n_proposals) {
    // Find all proposal elements
    var proposals = document.getElementsByClassName("proposal");

    // Determine the current search value
    var search_value = document.getElementById("search_box").value;

    // Determine whether or not to display each thumbnail
    var num_proposals_displayed = 0;
    for (i = 0; i < proposals.length; i++) {
        // Evaluate if the proposal number matches the search
        var j = i + 1
        var prop_name = document.getElementById("proposal" + j).getAttribute('proposal')


        if (prop_name.startsWith(search_value)) {
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


function show_only(filter_type, value, dropdown_keys, num_fileids) {
            // Get all filter options from {{dropdown_menus}} variable
            var all_filters = dropdown_keys.slice(10,dropdown_keys.length-1).replace(/&#39;/g, '"');
            var all_filters = JSON.parse(all_filters);

            // Update dropdown menu text
            document.getElementById(filter_type + '_dropdownMenuButton').innerHTML = value;

            // Find all thumbnail elements
            var thumbnails = document.getElementsByClassName("thumbnail");

            // Determine the current value for each filter
            var filter_values = [];
            for (j = 0; j < all_filters.length; j++) {
                var filter_value = document.getElementById(all_filters[j] + '_dropdownMenuButton').innerHTML;
                filter_values.push(filter_value);
            }

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