#!/usr/bin/env python

"""Tests for the ``data_containers`` module in the ``jwql`` web
application.

Authors
-------

    - Matthew Bourque

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

# Skip testing this module if on Jenkins
ON_JENKINS = '/home/jenkins' in os.path.expanduser('~')
try:
    from jwql.website.apps.jwql import data_containers
    from jwql.utils.utils import get_config
except:
    pass


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_acknowledgements():
    """Tests the ``get_acknowledgements`` function."""

    acknowledgements = data_containers.get_acknowledgements()
    assert isinstance(acknowledgements, list)
    assert len(acknowledgements) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_all_proposals():
    """Tests the ``get_all_proposals`` function."""

    proposals = data_containers.get_all_proposals()
    assert isinstance(proposals, list)
    assert len(proposals) > 0


@pytest.mark.xfail
def test_get_dashboard_components():
    """Tests the ``get_dashboard_components`` function."""

    dashboard_components, dashboard_html = data_containers.get_dashboard_components()
    assert isinstance(dashboard_components, dict)
    assert isinstance(dashboard_html, dict)
    assert len(dashboard_components) > 0
    assert len(dashboard_html) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_expstart():
    """Tests the ``get_expstart`` function."""

    expstart = data_containers.get_expstart('jw86700006001_02101_00006_guider1')
    assert isinstance(expstart, float)


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_filenames_by_instrument():
    """Tests the ``get_filenames_by_instrument`` function."""

    filepaths = data_containers.get_filenames_by_instrument('FGS')
    assert isinstance(filepaths, list)
    assert len(filepaths) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_filenames_by_proposal():
    """Tests the ``get_filenames_by_proposal`` function."""

    filenames = data_containers.get_filenames_by_proposal('88600')
    assert isinstance(filenames, list)
    assert len(filenames) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_filenames_by_rootname():
    """Tests the ``get_filenames_by_rootname`` function."""

    filenames = data_containers.get_filenames_by_rootname('jw86600008001_02101_00007_guider2')
    assert isinstance(filenames, list)
    assert len(filenames) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_header_info():
    """Tests the ``get_header_info`` function."""

    header = data_containers.get_header_info('jw86600008001_02101_00007_guider2_uncal.fits')
    assert isinstance(header, str)
    assert len(header) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_image_info():
    """Tests the ``get_image_info`` function."""

    image_info = data_containers.get_image_info('jw86600008001_02101_00007_guider2', False)

    assert isinstance(image_info, dict)

    keys = ['all_jpegs', 'suffixes', 'num_ints', 'all_files']
    for key in keys:
        assert key in image_info


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_instrument_proposals():
    """Tests the ``get_instrument_proposals`` function."""

    proposals = data_containers.get_instrument_proposals('Fgs')
    assert isinstance(proposals, list)
    assert len(proposals) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_preview_images_by_instrument():
    """Tests the ``get_preview_images_by_instrument`` function."""

    preview_images = data_containers.get_preview_images_by_instrument('fgs')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_preview_images_by_proposal():
    """Tests the ``get_preview_images_by_proposal`` function."""

    preview_images = data_containers.get_preview_images_by_proposal('88600')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_preview_images_by_rootname():
    """Tests the ``get_preview_images_by_rootname`` function."""

    preview_images = data_containers.get_preview_images_by_rootname('jw86600008001_02101_00007_guider2')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_proposal_info():
    """Tests the ``get_proposal_info`` function."""

    filepaths = glob.glob(os.path.join(get_config()['filesystem'], 'jw88600', '*.fits'))
    proposal_info = data_containers.get_proposal_info(filepaths)

    assert isinstance(proposal_info, dict)

    keys = ['num_proposals', 'proposals', 'thumbnail_paths', 'num_files']
    for key in keys:
        assert key in proposal_info


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_thumbnails_by_instrument():
    """Tests the ``get_thumbnails_by_instrument`` function."""

    preview_images = data_containers.get_thumbnails_by_instrument('fgs')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_thumbnails_by_proposal():
    """Tests the ``get_thumbnails_by_proposal`` function."""

    preview_images = data_containers.get_thumbnails_by_proposal('88600')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_get_thumbnails_by_rootname():
    """Tests the ``get_thumbnails_by_rootname`` function."""

    preview_images = data_containers.get_thumbnails_by_rootname('jw86600008001_02101_00007_guider2')
    assert isinstance(preview_images, list)
    assert len(preview_images) > 0


@pytest.mark.skipif(ON_JENKINS, reason='Requires access to central storage.')
def test_thumbnails_ajax():
    """Tests the ``get_thumbnails_ajax`` function."""

    thumbnail_dict = data_containers.thumbnails_ajax('FGS')

    assert isinstance(thumbnail_dict, dict)

    keys = ['inst', 'file_data', 'tools', 'dropdown_menus', 'prop']
    for key in keys:
        assert key in thumbnail_dict
