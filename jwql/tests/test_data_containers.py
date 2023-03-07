#!/usr/bin/env python

"""Tests for the ``data_containers`` module in the ``jwql`` web
application.

Authors
-------

    - Matthew Bourque
    - Mees Fix
    - Bryan Hilbert
    - Bradley Sappington
    - Melanie Clarke

Use
---

    These tests can be run via the command line (omit the -s to
    suppress verbose output to stdout):

    ::

        pytest -s test_data_containers.py
"""

import glob
import os

import pytest

# Skip testing this module if on Github Actions
ON_GITHUB_ACTIONS = '/home/runner' in os.path.expanduser('~') or '/Users/runner' in os.path.expanduser('~')
from jwql.website.apps.jwql import data_containers

if not ON_GITHUB_ACTIONS:
    from jwql.utils.utils import get_config


def test_get_acknowledgements():
    """Tests the ``get_acknowledgements`` function."""

    acknowledgements = data_containers.get_acknowledgements()
    assert isinstance(acknowledgements, list)
    assert len(acknowledgements) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_all_proposals():
    """Tests the ``get_all_proposals`` function."""

    proposals = data_containers.get_all_proposals()
    assert isinstance(proposals, list)
    assert len(proposals) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_expstart():
    """Tests the ``get_expstart`` function."""

    expstart = data_containers.get_expstart('NIRCam', 'jw01068001001_02102_00001_nrcb1')
    assert isinstance(expstart, float)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_filenames_by_instrument():
    """Tests the ``get_filenames_by_instrument`` function."""

    filepaths = data_containers.get_filenames_by_instrument('NIRCam', '1068')
    assert isinstance(filepaths, list)
    assert len(filepaths) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_filenames_by_proposal():
    """Tests the ``get_filenames_by_proposal`` function."""
    pid = '2589'
    filenames = data_containers.get_filenames_by_proposal(pid)
    assert isinstance(filenames, list)
    assert len(filenames) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_filenames_by_rootname():
    """Tests the ``get_filenames_by_rootname`` function."""
    rname = 'jw02589006001_04101_00001-seg002_nrs2'
    filenames = data_containers.get_filenames_by_rootname(rname)
    assert isinstance(filenames, list)
    assert len(filenames) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
@pytest.mark.parametrize('pid,rname,success',
                         [('2589', None, True),
                          (None, 'jw02589006001_04101_00001-seg002_nrs2', True),
                          ('2589', 'jw02589006001_04101_00001-seg002_nrs2', True),
                          (None, None, False)])
def test_get_filesystem_filenames(pid, rname, success):
    """Tests the ``get_filesystem_filenames`` function."""
    filenames = data_containers.get_filesystem_filenames(
        proposal=pid, rootname=rname)
    assert isinstance(filenames, list)
    if not success:
        assert len(filenames) == 0
    else:
        assert len(filenames) > 0

        # check specific file_types
        fits_files = [f for f in filenames if f.endswith('.fits')]
        assert len(fits_files) < len(filenames)

        fits_filenames = data_containers.get_filesystem_filenames(
            proposal=pid, rootname=rname, file_types=['fits'])
        assert isinstance(fits_filenames, list)
        assert len(fits_filenames) > 0
        assert len(fits_filenames) == len(fits_files)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_filesystem_filenames_options():
    """Tests the ``get_filesystem_filenames`` function."""
    pid = '2589'

    # basenames only
    filenames = data_containers.get_filesystem_filenames(
        proposal=pid, full_path=False, file_types=['fits'])
    assert not os.path.isfile(filenames[0])

    # full path
    filenames = data_containers.get_filesystem_filenames(
        proposal=pid, full_path=True, file_types=['fits'])
    assert os.path.isfile(filenames[0])

    # sorted
    sorted_filenames = data_containers.get_filesystem_filenames(
        proposal=pid, sort_names=True, file_types=['fits'])
    unsorted_filenames = data_containers.get_filesystem_filenames(
        proposal=pid, sort_names=False, file_types=['fits'])
    assert sorted_filenames != unsorted_filenames
    assert sorted_filenames == sorted(unsorted_filenames)


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_header_info():
    """Tests the ``get_header_info`` function."""

    header = data_containers.get_header_info('jw01068001001_02102_00001_nrcb1', 'uncal')
    assert isinstance(header, dict)
    assert len(header) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_image_info():
    """Tests the ``get_image_info`` function."""

    image_info = data_containers.get_image_info('jw01068001001_02102_00001_nrcb1')

    assert isinstance(image_info, dict)

    keys = ['all_jpegs', 'suffixes', 'num_ints', 'all_files']
    for key in keys:
        assert key in image_info


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_instrument_proposals():
    """Tests the ``get_instrument_proposals`` function."""

    proposals = data_containers.get_instrument_proposals('Fgs')
    assert isinstance(proposals, list)
    assert len(proposals) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
@pytest.mark.parametrize('keys,viewed,sort_as,exp_type,cat_type',
                         [(None, None, None, None, None),
                          (None, 'viewed', None, None, None),
                          (None, 'Viewed', None, None, None),
                          (None, 'new', None, None, None),
                          (None, 'New', None, None, None),
                          (None, None, None, 'NRS_MSATA', None),
                          # (None, None, None, None, 'CAL'),  # cat_type not implemented yet
                          (['expstart'], 'new', 'ascending', None, None),
                          (['expstart'], 'new', 'descending', None, None),
                          (['expstart'], 'new', 'recent', None, None),
                          ([], 'viewed', None, None, None),
                          ([], 'new', None, None, None),
                          ([], None, None, None, None),
                          (['proposal', 'obsnum', 'other',
                            'prop_id', 'expstart'], 'viewed', None, None, None),
                          (['proposal', 'obsnum', 'other',
                            'prop_id', 'expstart'], 'new', None, None, None),
                          (['proposal', 'obsnum', 'other',
                            'prop_id', 'expstart'], None, None, None, None)])
def test_get_instrument_looks(keys, viewed, sort_as, exp_type, cat_type):
    """Tests the ``get_instrument_looks`` function."""

    return_keys, looks = data_containers.get_instrument_looks(
        'nirspec', additional_keys=keys, look=viewed, sort_as=sort_as,
        exp_type=exp_type, cat_type=cat_type)
    assert isinstance(return_keys, list)
    assert isinstance(looks, list)

    # returned keys always contains at least root name
    assert len(return_keys) > 1
    assert 'root_name' in return_keys
    assert 'viewed' in return_keys

    # they may also contain some keys from the instrument
    # and any additional keys specified
    if keys is not None:
        assert len(return_keys) >= 1 + len(keys)

    # viewed depends on local database, so may or may not have results
    if not str(viewed).lower() == 'viewed':
        assert len(looks) > 0
        first_file = looks[0]
        assert first_file['root_name'] != ''
        assert isinstance(first_file['viewed'], bool)
        assert len(first_file) == len(return_keys)
        for key in return_keys:
            assert key in first_file

        last_file = looks[-1]
        if sort_as == 'ascending':
            assert last_file['root_name'] > first_file['root_name']
        elif sort_as == 'recent':
            assert last_file['expstart'] < first_file['expstart']
        else:
            assert last_file['root_name'] < first_file['root_name']


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_preview_images_by_proposal():
    """Tests the ``get_preview_images_by_proposal`` function."""

    preview_images = data_containers.get_preview_images_by_proposal('1033')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_preview_images_by_rootname():
    """Tests the ``get_preview_images_by_rootname`` function."""

    preview_images = data_containers.get_preview_images_by_rootname('jw02589001001_02101_00001-seg001_nis')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0

@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_proposals_by_category():
    """Tests the ``get_proposals_by_category`` function."""

    proposals_by_category = data_containers.get_proposals_by_category('fgs')
    assert isinstance(proposals_by_category, dict)
    assert len(proposals_by_category) > 0

@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_proposal_info():
    """Tests the ``get_proposal_info`` function."""

    filepaths = glob.glob(os.path.join(get_config()['filesystem'], 'jw01068', '*.fits'))
    proposal_info = data_containers.get_proposal_info(filepaths)

    assert isinstance(proposal_info, dict)

    keys = ['num_proposals', 'proposals', 'thumbnail_paths', 'num_files']
    for key in keys:
        assert key in proposal_info


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_thumbnails_by_proposal():
    """Tests the ``get_thumbnails_by_proposal`` function."""

    preview_images = data_containers.get_thumbnails_by_proposal('01033')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_get_thumbnail_by_rootname():
    """Tests the ``get_thumbnail_by_rootname`` function."""

    preview_images = data_containers.get_thumbnail_by_rootname('jw02589001001_02101_00001-seg001_nis')
    assert isinstance(preview_images, str)
    assert len(preview_images) > 0
    assert preview_images != 'none'
    preview_images = data_containers.get_thumbnail_by_rootname('invalid_rootname')
    assert isinstance(preview_images, str)
    assert len(preview_images) > 0
    assert preview_images == 'none'


def test_mast_query_by_rootname():
    """Tests the ``mast_query_by_rootname`` function."""
    instrument = 'NIRCam'
    rootname1 = 'jw02767002001_02103_00005_nrcb4'
    dict_stuff = data_containers.mast_query_by_rootname(instrument, rootname1)
    defaults = dict(filter=dict_stuff.get('filter', ''),
                    detector=dict_stuff.get('detector', ''),
                    exp_type=dict_stuff.get('exp_type', ''),
                    read_pat=dict_stuff.get('readpatt', ''),
                    grating=dict_stuff.get('grating', ''),
                    patt_num=dict_stuff.get('patt_num', 0),
                    aperture=dict_stuff.get('apername', ''),
                    subarray=dict_stuff.get('subarray', ''),
                    pupil=dict_stuff.get('pupil', ''))
    assert isinstance(defaults, dict)

    rootname2 = 'jw02084001001_04103_00001-seg003_nrca3'
    dict_stuff = data_containers.mast_query_by_rootname(instrument, rootname2)
    defaults = dict(filter=dict_stuff.get('filter', ''),
                    detector=dict_stuff.get('detector', ''),
                    exp_type=dict_stuff.get('exp_type', ''),
                    read_pat=dict_stuff.get('readpatt', ''),
                    grating=dict_stuff.get('grating', ''),
                    patt_num=dict_stuff.get('patt_num', 0),
                    aperture=dict_stuff.get('apername', ''),
                    subarray=dict_stuff.get('subarray', ''),
                    pupil=dict_stuff.get('pupil', ''))
    assert isinstance(defaults, dict)

    instrument2 = 'FGS'
    rootname3 = 'jw01029003001_06201_00001_guider2'
    dict_stuff = data_containers.mast_query_by_rootname(instrument2, rootname3)
    defaults = dict(filter=dict_stuff.get('filter', ''),
                    detector=dict_stuff.get('detector', ''),
                    exp_type=dict_stuff.get('exp_type', ''),
                    read_pat=dict_stuff.get('readpatt', ''),
                    grating=dict_stuff.get('grating', ''),
                    patt_num=dict_stuff.get('patt_num', 0),
                    aperture=dict_stuff.get('apername', ''),
                    subarray=dict_stuff.get('subarray', ''),
                    pupil=dict_stuff.get('pupil', ''))
    assert isinstance(defaults, dict)



@pytest.mark.skipif(ON_GITHUB_ACTIONS, reason='Requires access to central storage.')
def test_thumbnails_ajax():
    """Tests the ``get_thumbnails_ajax`` function."""

    thumbnail_dict = data_containers.thumbnails_ajax('NIRCam', '1068')

    assert isinstance(thumbnail_dict, dict)

    keys = ['inst', 'file_data', 'tools', 'dropdown_menus', 'prop']
    for key in keys:
        assert key in thumbnail_dict
