#! /usr/bin/env python
"""Tests for the ``engineering_database`` module.

Authors
-------

    - Johannes Sahlmann


Use
---

    These tests can be run via the command line (omit the ``-s`` to
    suppress verbose output to ``stdout``):

    ::

        pytest -s test_edb_interface.py
"""

from astropy.time import Time
# from jwst.lib import engdb_tools
# from ..utils.engineering_database import query_single_mnemonic, get_all_mnemonics

mast_token = ''




from astroquery.mast import Mast
Mast.login(token=mast_token)

service="Mast.JwstEdb.Mnemonics"
params={}

uri = 'mast:jwstedb/SE_ZIMIRFPEA-20170213T223000-20170214T110000.csv'


mnemonic_name = 'SE_ZIMIRFPEA'
start_time = '2016-01-22 17:28:19'
end_time = '2018-01-22 18:46:04'
if 0:
    from urllib.request import urlopen, Request
    url = "https://mast.stsci.edu/api/v0.1/Download/file?uri={}".format(uri)
    request = Request(url)
    request.add_header('Authorization', 'token {}'.format(mast_token))
    response = urlopen(request)
    print(response.read())
    1/0
if 1:
    # get all mnemonics
    print('Get list of available mnemonics:')
    out = Mast.service_request_async(service, params)
    mnemonics = out[0].json()['data']
    print('Retrieved {} mnemonics'.format(len(mnemonics)))

    # #### Querying for a specific mnemonic
    print('get details of specific mnemonic:')
    service = "Mast.JwstEdb.Dictionary"
    params = {"mnemonic":"{}".format(mnemonic_name)}
    out = Mast.service_request_async(service, params)
    mnemonic = out[0].json()['data']
    print(mnemonic)

    # #### Querying for data
    print('Query data for specific mnemonic:')
    service = "Mast.JwstEdb.LoadData"
    params = {"input":"'{}, {}, {};'".format(mnemonic_name, start_time, end_time)}
    data = Mast.service_request_async(service, params)

    json_data = data[0].json()
    print(json_data['fields'])
    print('Query resulted in {} mnemonic samples'.format(data[0].json()['data'][0]['theCount']))
    1/0
# print(json_data['data'][0])


# #### Downloading a file
print('attempt file download')
# Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri=mast:jwstedb/SE_ZNIS-20150125T115331-20180919T020000.csv", "test.csv", cache=False)
# Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri=mast:jwstedb/SE_ZIFGSTCE-20150125T115331-20180919T020000.csv", "test.csv", cache=False)
Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri={}".format(uri), "test.csv", cache=False)
# Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri=mast:jwstedb/SA_ZADUCMDX-20150125T115331-20180919T020000.csv", "test.csv")
# Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri=mast:jwstedb/SA_ZADUCMDX-20160125T115331-20170919T020000.csv","test.csv")
# Mast._download_file(Mast._MAST_DOWNLOAD_URL + "?uri=mast:jwstedb/SA_ZADUCMDX-20160125T115331-20170919T020000.csv", "test.csv")
# Mast._download_file('https://mast.stsci.edu/api/v0.1/download/file/' + "?uri=mast:jwstedb/SA_ZADUCMDX-20160125T115331-20170919T020000.csv", "test.csv")
# Mast._download_file('https://mast.stsci.edu/portal/Download/jwstedb/SA_ZADUCMDX-20160125T115331-20170919T020000.csv', "test.csv")
1/0





def test_get_all_mnemonics():
    """Test the retrieval of all mnemonics."""
    print()
    all_mnemonics = get_all_mnemonics(verbose=True)
    assert len(all_mnemonics) > 1000


def test_query_single_mnemonic():
    """Test the query of a mnemonic over a given time range."""
    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    print()
    mnemonic = query_single_mnemonic(mnemonic_identifier, start_time, end_time, verbose=True)
    assert len(mnemonic.record_times) == len(mnemonic.record_values)


def test_engdb_tools_query_mnemonic():
    """Test the query of a mnemonic using the jwst.lib.engdb_tools module."""
    engdb = engdb_tools.ENGDB_Service()

    mnemonic_identifier = 'SA_ZFGOUTFOV'
    start_time = Time(2016.0, format='decimalyear')
    end_time = Time(2018.1, format='decimalyear')

    records = engdb.get_records(mnemonic_identifier, start_time, end_time)
    n_data_records = len(records['Data'])
    assert n_data_records == records['Count']
    print('\n', records)
    data = engdb.get_values(mnemonic_identifier, start_time, end_time, include_bracket_values=True)
    n_data_values = len(data)
    print(data)
    assert n_data_records == n_data_values


def test_engdb_tools_query_meta():
    """Test the query of a mnemonic meta data using the jwst.lib.engdb_tools module.."""
    engdb = engdb_tools.ENGDB_Service()

    mnemonic_identifier = 'SA_Z'

    # get meta data
    meta = engdb.get_meta(mnemonic=mnemonic_identifier)
    print(meta)
    assert mnemonic_identifier in meta['TlmMnemonics'][0]['TlmMnemonic']
    assert meta['Count'] > 1
