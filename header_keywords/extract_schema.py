#! /usr/bin/env python

r"""Create lists of header keywords and datatypes for
each JWST filetype


Extract JWST schema from json files that come from
the keyword dictionary
(https://mast.stsci.edu/portal/Mashup/Clients/jwkeywords/index.html)
and place into text files containing header keywords and data types.
We want one text file for each instrument/detector/calibration level/
fits file extension combination.

For example, for a raw (uncalibrated) NIRCam imaging observation,
we want one text file that lists the header keywords in each
extension of the fits file:

PRIMARY
SCI
ZEROFRAME
GROUPDQ
GROUP
CHEBY



Input:
------
None from user
Dictionary of top level keyword dictionary schema files
associated with each JWST detector is set up in __init__

Output:
-------
Text files listing the header keywords associated with
each instrument/detector/calibration level/file extension
combination

Notes:
------
Possible detectors and associated
top-level schema files:
NRCA1, NRCA2, NRCA3, NRCA4, NRCALONG,
NRCB1, NRCB2, NRCB3, NRCB4, NRCBLONG:
      Same for all detectors
      top.nircam.coron.schema.json
      top.nircam.imaging.schema.json
      top.nircam.wfsc.schema.json
      top.nircam.wfss.schema.json

NRS1, NRS2:
      Same for all detectors
      top.nirspec.fss.schema.json
      top.nirspec.ifu.schema.json
      top.nirspec.imaging.schema.json
      top.nirspec.msa.schema.json
      top.nirspec.wfsc.schema.json

MIRIMAGE:
      top.miri.imaging.schema.json,
      top.miri.lrs.schema.json,
      top.miri.coron.schema.json
MIRIFULONG:
      top.miri.mrs.schema.json
MIRIFUSHORT:
      top.miri.mrs.schema.json

NIRISS, NIS:
      Same for both detectors
      top.niriss.ami.schema.json
      top.niriss.schema.json
      top.niriss.sos.schema.json
      top.niriss.wfss.schema.json

GUIDER1, GUIDER2:
      Same for both detectors
      top.fgs.schema.json


Authors:
--------

Bryan Hilbert
"""


import os
import copy
import shutil
import json
from collections import OrderedDict
import numpy as np
from astropy.table import Table, vstack, unique
from astropy.io import ascii


class Schema():
    def __init__(self):
        """Create necessary dictionaries"""
        # self.modefiles lists the top level schema files
        # associated with each detector
        self.modefiles = {}
        self.modefiles['nrca1'] = ['top.nircam.imaging.schema.json',
                                   'top.nircam.wfss.schema.json',
                                   'top.nircam.wfsc.schema.json',
                                   'top.nircam.coron.schema.json']
        self.modefiles['nrs1'] = ['top.nirspec.imaging.schema.json',
                                  'top.nirspec.ifu.schema.json',
                                  'top.nirspec.msa.schema.json',
                                  'top.nirspec.wfsc.schema.json',
                                  'top.nirspec.fss.schema.json']
        self.modefiles['mirimage'] = ['top.miri.imaging.schema.json',
                                      'top.miri.lrs.schema.json',
                                      'top.miri.coron.schema.json']
        self.modefiles['mirifushort'] = ['top.miri.mrs.schema.json']
        self.modefiles['mirifulong'] = ['top.miri.mrs.schema.json']
        self.modefiles['niriss'] = ['top.niriss.schema.json',
                                    'top.niriss.sos.schema.json',
                                    'top.niriss.wfss.schema.json',
                                    'top.niriss.ami.schema.json']
        self.modefiles['guider1'] = ['top.fgs.schema.json']

        # self.repeats lists the detectors which have identical schema
        self.repeats = {}
        self.repeats['nrca1'] = ['nrca2', 'nrca3', 'nrca4', 'nrcalong',
                                 'nrcb1', 'nrcb2', 'nrcb3', 'nrcb4',
                                 'nrcblong']
        self.repeats['nrs1'] = ['nrs2']
        self.repeats['niriss'] = ['nis']
        self.repeats['guider1'] = ['guider2']

        self.indir = './'
        self.outdir = './'
        self.emptytable = Table(names=('Keyword', 'Datatype', 'HDU', 'Level'),
                                dtype=('U8', 'U10', 'U10', 'U5'))

    def copy_repeat_lists(self, input_files, detector):
        """Create copies of the input header tables for all
        detectors listed in self.repeat

        Arguments:
        ----------
        input_files -- List of header keyword files to be copied
        detector -- Detector for which the files will be copied

        Returns:
        --------
        Nothing
        """
        for rep_det in self.repeats[detector]:
            for ifile in input_files:
                indir, infile = os.path.split(ifile)
                cpfile = infile.replace(detector, rep_det)
                copyfile = os.path.join(indir, cpfile)
                print("Copying {} to {}".format(infile, cpfile))
                shutil.copy2(ifile, copyfile)

    def create_tables(self):
        """MAIN FUNCTION: create header keyword tables"""
        # Create table for each detector in self.modefiles
        for det in self.modefiles:
            print("Working on detector {}".format(det))
            topfiles = self.modefiles[det]
            self.instrument = topfiles[0].split('.')[1].upper()

            # For each top level file, find the lower-level
            # schema files, read in, and add to a master table
            det_tab = copy.deepcopy(self.emptytable)
            for top_level in topfiles:
                toptab = self.toptab(os.path.join(self.indir, top_level))
                det_tab = vstack([det_tab, toptab])
            det_tab = det_tab[1:]

            # Remove duplicate entries that can come from
            # using multiple top-level schema files
            det_tab = unique(det_tab, keys=['Keyword', 'Datatype',
                                            'HDU', 'Level'])

            # Now separate the full table into a separate
            # table for each level (1b, 2a, etc) / extension
            # combination
            all_lists = self.organize(det_tab)

            # Save lists to ascii files
            output_files = self.save_lists(all_lists, self.instrument, det)

            # Now create copies of the tables for all
            # detectors listed in self.repeat
            if det in self.repeats.keys():
                self.copy_repeat_lists(output_files, det)

    def extract_schema_names(self, topdict):
        """Extract the names of lower-level schema files
        from the top-level dictionary

        Arguments:
        ----------
        topdict -- Dictionary from a top-level schema file

        Returns:
        --------
        List of lower level schema filenames contained in topdict
        """
        allfiles = []
        for key in topdict:
            propdict = topdict[key]["properties"]
            for key2 in propdict:
                if key2 == "allOf":
                    flist = propdict["allOf"]
                    fname = [e["$ref"].strip() for e in flist]
                else:
                    fname = [propdict["$ref"].strip()]
                allfiles += fname
        # Remove duplicates
        return list(set(allfiles))

    def organize(self, tab):
        """Break the input master table for a
        given instrument/mode into separate tables
        for each level/file extension. Later levels
        need to include entries from eariler levels

        Arguments:
        ----------
        tab -- Table containig all header keywords for all
        calibration levels and file extensions for a given
        detector

        Returns:
        --------
        Dictionary of tables containing the same information
        in tab, with a separate table for each file extension
        and calibration level
        """
        extensions = set(tab['HDU'].data)
        # More possible level values than output filetypes
        # Need to group levels together into the file level
        # at which they will first appear
        finallevels = {'1': ['1', '1A', '1B'], '2A': ['2', '2A'],
                       '2B': ['2B'], '3': ['3']}
        finallevels = OrderedDict(sorted(finallevels.items()))
        sep_tabs = {}
        for index, level in enumerate(finallevels):
            goodlevels = finallevels[level]
            goodindex = np.zeros(len(tab['Level']), dtype='bool')
            # Indexes for all entries that go with this level
            for l in goodlevels:
                good = tab['Level'] == l
                goodindex = [a or b for a, b in zip(goodindex, good)]
            goodlevel = tab[goodindex]
            for ext in extensions:
                good = ((goodlevel['HDU'] == ext))
                sep_tabs[level+'_'+ext] = goodlevel[good]
                # For levels later than 1, append the keywords
                # from the previous calibration level
                if index > 0:
                    keyval = list(finallevels.keys())[index-1]
                    keyval = keyval + '_' + ext
                    sep_tabs[level+'_'+ext] = vstack([sep_tabs[level+'_'+ext],
                                                      sep_tabs[keyval]])
        return sep_tabs

    def read_json_file(self, file):
        """Read in a json file and return as dictionary

        Arguments:
        ----------
        file -- Name of json file to be read in

        Returns:
        --------
        Nested dictionary of file contents
        """
        with open(file) as h:
            json_str = h.read()
            return json.loads(json_str)

    def read_top_level_json(self, file):
        """Read in a top level schema file, corresponding
        to a given instrument/mode

        Arguments:
        ----------
        file -- Name of json file to be read in

        Returns:
        --------
        Nested dictionary of file contents
        """
        sch = self.read_json_file(file)
        return sch["properties"]["meta"]["properties"]

    def read_ref_file_json(self, file):
        """Read in the ref_file schema file, which
        has a different format than the other basic
        schema files

        Arguments:
        ----------
        file -- Name of json file to be read in

        Returns:
        --------
        Nested dictionary of file contents
        """
        full_dict = {}
        sch = self.read_json_file(file)
        for key in sch:
            psection = sch[key]["properties"]
            if "name" in psection.keys():
                subsection = psection["name"]
                full_dict[key] = subsection
            else:
                for key2 in psection:
                    full_dict[key+'_'+key2] = psection[key2]
        return full_dict

    def save_lists(self, lists, instr, detector):
        """Save the list for each extension/level into a
        separate ascii file

        Arguments:
        ----------
        lists -- List of astropy Tables containing header 
        keywords for each file extension and calibration level

        instr -- Name of the instrument for which the tables 
        apply (e.g. "NIRCAM")

        detector -- Name of the detector for which the tables
        apply (e.g. "NRCA1")

        Returns:
        --------
        Nothing
        """
        outfiles = []
        for key in lists:
            level, exten = key.split('_')
            outfile = ('header_keywords_{}_{}_{}_{}.txt'
                       .format(instr, detector, level, exten))
            outfile = os.path.join(self.outdir, outfile)
            outfiles.append(outfile)
            ascii.write(lists[key], outfile, format='no_header',
                        include_names=['Keyword', 'Datatype'], delimiter=',',
                        overwrite=True)
        return outfiles

    def schema_to_table(self, schema):
        """Convert the input schema dictionary into
        a table containing only the information of interest

        Arguments:
        ----------
        schema -- Nested dictionary from json file

        Returns:
        --------
        Astropy table containing only the name,
        datatype, file extension, and calibration level
        for each header keyword
        """
        tab = copy.deepcopy(self.emptytable)

        # Values in the "si" field that imply the keyword
        # is used for more than one instrument
        mult_insts = ["Multiple", "", "ALL"]

        for key in schema:
            entry = schema[key]
            try:
                kw = entry['fits_keyword']
            except:
                continue
                print("No keyword entry:")
                print(entry)
                print('')
                print(schema)
            hdu = entry['fits_hdu'].upper()
            level = entry['level'].upper()
            # Think of this as STARTING level
            # kw also present at later levels
            schmtype = entry['type'].lower()
            instrument = entry['si']

            # Only keep the entry if it applies to the
            # instrument and mode requested
            if instrument in mult_insts:
                instrument = self.instrument
            if (self.instrument in instrument):
                row = [kw, schmtype, hdu, level]
                tab.add_row(row)
        return tab

    def toptab(self, topfile):
        """From a top level schema file, find the lower-level
        schema files, read in, and create a table

        Arguments:
        ----------
        topfile -- Name of a top-level JWST keyword dictionary
        schema file (e.g. "top.nircam.imaging.schema.json")

        Returns:
        --------
        An astropy Table containing all of the header keyword
        information contained in the top level file as well as
        the lower level files listed in the top level file
        """

        # Read in the top-level json file
        top_level = self.read_top_level_json(topfile)

        # Parse the dictionary and figure out which lower
        # level json files you need.
        schema_files = self.extract_schema_names(top_level)

        # Read in the lower level json files and create a table
        # of schema entries
        init = ['None', 'None', 'None', 'None']
        fulltab = copy.deepcopy(self.emptytable)
        fulltab.add_row(init)
        for sfile in schema_files:
            if 'core.ref_file.schema.json' not in sfile:
                s = self.read_json_file(os.path.join(self.indir, sfile))
            else:
                s = self.read_ref_file_json(os.path.join(self.indir, sfile))
            stab = self.schema_to_table(s)
            fulltab = vstack([fulltab, stab])
        return fulltab[1:]
