#! /usr/bin/env python

"""Obtains metadata associated with proposal id submitted by user. This information is displayed
on the proposal landing page.

Authors
-------
    Mees Fix, 2022

Use
---

    This script is intended to be run via daily cron job. It
    can also be run manually with:
    ::

        python ql_wfc3_get_proposal_status.py
"""

from bs4 import BeautifulSoup
import requests


def text_scrape(prop_id):
    """Scrapes the Proposal Information Page.

    Parameters
    ----------
    prop_id : int
        Proposal ID

    Returns
    -------
    program_meta : dict
        Dictionary containing information about program
    """

    # Generate url
    url = 'http://www.stsci.edu/cgi-bin/get-proposal-info?id=' + str(prop_id) + '&submit=Go&observatory=JWST'
    html = BeautifulSoup(requests.get(url).text, 'lxml')
    lines = html.findAll('p')
    lines = [str(line) for line in lines]
    
    program_meta = {}
    program_meta['prop_id'] = prop_id
    program_meta['phase_two'] = 'https://www.stsci.edu/jwst/phase2-public/{}.pdf'
    
    if prop_id[0] == '0':
        program_meta['phase_two'] = program_meta['phase_two'].format(prop_id[1:])
    else:
        program_meta['phase_two'] = program_meta['phase_two'].format(prop_id)

    links = html.findAll('a')
    proposal_type = links[0].contents[0]
    
    program_meta['prop_type'] = proposal_type

    # Scrape for titles/names/contact persons
    for line in lines:
        if 'Title' in line:
            start = line.find('</b>') + 4
            end = line.find('<', start)
            title = line[start:end]
            program_meta['title'] = title

        if 'Principal Investigator:' in line:
            start = line.find('</b>') + 4
            end = line.find('<', start)
            pi = line[start:end]
            program_meta['pi'] = pi

        if 'Program Coordinator' in line:
            start = line.find('</b>') + 4
            mid = line.find('<', start)
            end = line.find('>', mid) + 1
            pc = line[mid:end] + line[start:mid] + '</a>'
            program_meta['pc'] = pc

        if 'Contact Scientist' in line:
            start = line.find('</b>') + 4
            mid = line.find('<', start)
            end = line.find('>', mid) + 1
            cs = line[mid:end] + line[start:mid] + '</a>'
            program_meta['cs'] = cs

        if 'Program Status' in line:
            start = line.find('<b>Program Status:')
            end = line.find('</p>')
            ps = line[start:end]
            program_meta['ps'] = ps

    return program_meta
