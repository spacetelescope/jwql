#! /usr/bin/env python

'''
extract JWST schema from json files that come from 
the keyword dictionary 
(https://mast.stsci.edu/portal/Mashup/Clients/jwkeywords/index.html)


input:
instrument, mode
OR
top level schema filename?

output:
Tables containing header keyword, datatype.
One table for each fits extension of each level


Possible fits extensions:
_uncal.fits - level 1b
_rate.fits, - level 2a
_rateints.fits - level 2a
_cal.fits - level 2b
_calints.fits - level 2b
_i2d.fits - rectified cal images, resampled...so level 3
_s2d.fits - rectified or rectified + combined non-IFU slope data
_s3d.fits - 3d rectified (level2) or rectified and combined (level3) IFU data
_x1d.fits - 1d extracted spectra - level 3
_x1dints.fits - 1d extracted TSO spectra (from calints) level 3


top level schema files:
top.fgs.schema.json
top.guidestar.schema.json
top.miri.coron.schema.json
top.miri.imaging.schema.json
top.miri.lrs.schema.json
top.miri.mrs.schema.json
top.nircam.coron.schema.json
top.nircam.imaging.schema.json
top.nircam.wfsc.schema.json
top.nircam.wfss.schema.json
top.niriss.ami.schema.json
top.niriss.schema.json
top.niriss.sos.schema.json
top.niriss.wfss.schema.json
top.nirspec.fss.schema.json
top.nirspec.ifu.schema.json
top.nirspec.imaging.schema.json
top.nirspec.msa.schema.json
top.nirspec.wfsc.schema.json


All possible exposure types (from keyword 
dictionary, but where do these
ultimately come from?):
FGS_DARK, 
FGS_FOCUS, 
FGS_IMAGE, 
FGS_INTFLAT, 
FGS_SKYFLAT, 

MIR_IMAGE, 
MIR_TACQ, 
MIR_LYOT, 
MIR_4QPM, 
MIR_LRS-FIXEDSLIT, 
MIR_LRS-SLITLESS, 
MIR_MRS, 
MIR_DARK, 
MIR_FLATIMAGE, 
MIR_FLATMRS, 
MIR_CORONCAL, 

NIS_AMI, 
NIS_DARK, 
NIS_FOCUS, 
NIS_IMAGE, 
NIS_LAMP, 
NIS_SOSS, 
NIS_WFSS, 
NIS_TACQ, 
NIS_TACONFIRM, 

N/A, 
ANY, 

NRC_IMAGE, 
NRC_GRISM, 
NRC_TACQ, 
NRC_CORON, 
NRC_FOCUS, 
NRC_DARK, 
NRC_FLAT, 
NRC_LED, 
NRC_TSIMAGE, 
NRC_TSGRISM, 
NRC_TACONFIRM, 

NRS_AUTOFLAT, 
NRS_AUTOWAVE, 
NRS_BOTA, 
NRS_BRIGHTOBJ, 
NRS_CONFIRM, 
NRS_DARK, 
NRS_FIXEDSLIT, 
NRS_FOCUS, 
NRS_IFU, 
NRS_IMAGE, 
NRS_LAMP, 
NRS_MIMF, 
NRS_MSASPEC, 
NRS_TACONFIRM, 
NRS_TACQ, 
NRS_TASLIT, 

FGS_ID-IMAGE, 
FGS_ID-STACK, 
FGS_ACQ1, 
FGS_ACQ2, 
FGS_TRACK, 
FGS_FINEGUIDE
'''


import os
import copy
import json
from collections import OrderedDict
import numpy as np
from astropy.table import Table, vstack
from astropy.io import ascii

class Schema():
    def __init__(self):
        modefiles = {}
        modefiles["NRC_IMAGE"] = "top.nircam.imaging.schema.json"
        modefiles["NRC_SLITLESS"] = "top.nircam.wfss.schema.json"
        modefiles["NRC_TACQ"] = "none"
        modefiles["NRC_CORON"] = "top.nircam.coron.schema.json"
        modefiles["NRC_FOCUS"] = "none"
        modefiles["NRC_DARK"] = "none"
        modefiles["NRC_FLAT"] = "none" 
        modefiles["NRC_LED"] = "none"
        modefiles["NRC_WFSC"] = "top.nircam.wfsc.schema.json"
        modefiles["FGS"] = "top.fgs.schema.json"
        modefiles["GUIDESTAR"] = "top.guidestar.schema.json"
        modefiles["MIR_LRS-FIXEDSLIT"] = "top.miri.lrs.schema.json"
        modefiles["MIR_LRS-SLITLESS"] = "top.miri.lrs.schema.json"
        modefiles["MIR_MRS"] = "top.miri.mrs.schema.json"
        modefiles["MIR_IMAGE"] = "top.miri.imaging.schema.json"
        modefiles["MIR_CORON"] = "top.miri.coron.schema.json"
        modefiles["NIRISS_IMAGE"] = "top.niriss.schema.json"
        modefiles["NIRISS_AMI"] = "top.niriss.ami.schema.json"
        modefiles["NIRISS_SOSS"] = "top.niriss.sos.schema.json"
        modefiles["NIRISS_WFSS"] = "top.niriss.wfss.schema.json"
        modefiles["NRS_MSASPEC"] = "top.nirspec.msa.schema.json"
        modefiles["NRS_FIXEDSLIT"] = "top.nirspec.fss.schema.json"
        modefiles["NRS_TASLIT"] = "none"
        modefiles["NRS_IFU"] = "top.nirspec.ifu.schema.json"
        modefiles["NRS_IMAGE"] = "top.nirspec.imaging.schema.json"
        modefiles["NRS_WFSC"] = "top.nirspec.wfsc.schema.json"
        
        self.indir = './'
        self.outdir = './'
        self.mode = "NRC_IMAGE"
        self.modefile = os.path.join(self.indir,modefiles[self.mode])
        self.instrument = 'NIRCAM'
        self.emptytable = Table(names=('Keyword','Datatype','HDU','Level'),dtype=('U8', 'U10', 'U10', 'U5'))

        
    def create_tables(self):
        '''MAIN FUNCTION'''
        # Create instrument and mode values of interest based on
        # the input filename
        #self.instrument, self.mode = self.get_mode_list(self.modefile)
        
        # Read in the top-level json file
        top_level = self.read_top_level_json(self.modefile)

        # Parse the dictionary and figure out which lower
        # level json files you need.
        schema_files = self.extract_schema_names(top_level)

        # Read in the lower level json files and create a table
        # of schema entries
        init = ['None','None','None','None']
        fulltab = copy.deepcopy(self.emptytable)
        fulltab.add_row(init)
        for sfile in schema_files:
            #print('')
            #print("#######################")
            #print("Working on file {}".format(sfile))
            #print("#######################")
            #print('')
            if 'core.ref_file.schema.json' not in sfile:
                s = self.read_json_file(os.path.join(self.indir,sfile))
            else:
                s = self.read_ref_file_json(os.path.join(self.indir,sfile))
            stab = self.schema_to_table(s)
            #print("FULLTAB BEFORE: {} lines".format(len(fulltab)))
            #print(fulltab)
            #print("STAB: {} lines".format(len(stab)))
            #print(stab)
            #print('')
            #print('')
            #print('')
            fulltab = vstack([fulltab,stab])
            #print("FULLTAB JOINED:")
            #print(fulltab)
            #print("STAB JOINED:")
            #print(stab)
        fulltab = fulltab[1:]

        # Now separate the full table into a separate
        # table for each level (1b, 2a, etc) / extension
        # combination
        all_lists = self.organize(fulltab)

        # Save lists to ascii files
        self.save_lists(all_lists)

        
    def extract_schema_names(self,topdict):
        '''Extract the names of lower-level schema files
        from the top-level dictionary'''
        allfiles = []
        for key in topdict:
            propdict = topdict[key]["properties"]
            for key2 in propdict:
                if key2 == "allOf":
                    flist = propdict["allOf"]
                    fname = [e["$ref"] for e in flist]
                        
                else:
                    fname = [propdict["$ref"]]
                allfiles += fname
        # Remove duplicates
        return list(set(allfiles))
        

    def get_mode_list(self,file):
        '''Use the input top level schema filename
        to determine the instrument and mode values
        of interest'''
        parts = file.split('.')
        instrument = parts[1]
        mode = parts[2]
        #NIRISS imaging file doesn't say 'imaging'
        if instrument == 'niriss' and mode == 'schema':
            mode = 'NIRISS_IMAGE'
        
            
    def organize(self,tab):
        '''Break the input master table for a
        given instrument/mode into separate tables
        for each level/file extension. Later levels
        need to include entries from eariler levels'''
        extensions = set(tab['HDU'].data)
        levels = set(tab['Level'].data)
        # More possible level values than output filetypes
        # Need to group levels together into the file level
        # at which they will first appear
        finallevels = {'1':['1','1A','1B'],'2A':['2','2A'],'2B':['2B'],'3':['3']}
        finallevels = OrderedDict(sorted(finallevels.items()))
        sep_tabs = {}
        for index,level in enumerate(finallevels):
            goodlevels = finallevels[level]
            goodindex = np.zeros(len(tab['Level']),dtype='bool')
            # Indexes for all entries that go with this level
            for l in goodlevels:
                good = tab['Level'] == l
                goodindex = [a or b for a,b in zip(goodindex,good)]
            goodlevel = tab[goodindex]
            for ext in extensions:
                good = ((goodlevel['HDU'] == ext))
                #print('xxxxxxxxxxxxxxxxxxxxxxx')
                #print(level,ext,np.sum(good))
                #print('xxxxxxxxxxxxxxxxxxxxxxx')
                sep_tabs[level+'_'+ext] = goodlevel[good]
                #print("outside cindex, ext, index, level are: {}, {}, {}".format(ext,index,level))
        #print(sep_tabs.keys())
        #print('')
        #print('')
        #for r in range(len(sep_tabs['2BSCI'])):
        #    print(sep_tabs['2BSCI'][r])
                # A given level needs to contain all the schema
                # from the previous levels in addition to the
                # new entries
                #for cindex in range(index-1,-1,-1):
                if index > 0:
                    keyval = list(finallevels.keys())[index-1]
                    keyval = keyval + '_' + ext
                    sep_tabs[level+'_'+ext] = vstack([sep_tabs[level+'_'+ext],sep_tabs[keyval]])
        return sep_tabs
    
        
    def read_json_file(self,file):
        '''Read in a json file and return as dictionary'''
        with open(file) as h:
            json_str = h.read()
            return json.loads(json_str)
    
    def read_top_level_json(self,file):
        '''Read in a top level schema file, corresponding
        to a given instrument/mode'''
        sch = self.read_json_file(file)
        return sch["properties"]["meta"]["properties"]

    
    def read_ref_file_json(self,file):
        '''Read in the ref_file schema file, which
        has a different format than the other basic
        schema files'''
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


    def save_lists(self,lists):
        '''save the list for each extension/level into a
        separate ascii file'''
        for key in lists:
            level,exten = key.split('_')
            topsplit = self.modefile.split('.')
            instr = topsplit[1]
            mode = topsplit[2]
            outfile = ('header_keywords_{}_{}_{}_{}.txt'
                       .format(instr,mode,level,exten))
            outfile = os.path.join(self.outdir,outfile)
            ascii.write(lists[key],outfile,overwrite=True)
            
    
    def schema_to_table(self,schema):
        '''Convert the input schema dictionary into
        a table containing only the information of interest'''
        tab = copy.deepcopy(self.emptytable)
        for key in schema:
            entry = schema[key]
            try:
                kw = entry['fits_keyword']
            except:
                print("No keyword entry:")
                print(entry)
                print('')
                print(schema)
            hdu = entry['fits_hdu'].upper()
            level = entry['level'].upper() #Starting from 1A...
            #Think of this as STARTING level
            #kw also present at later levels
            mode = entry['mode'] #can be list
            schmtype = entry['type'].lower()
            instrument = entry['si'] #can be list

            # Only keep the entry if it applies to the
            # instrument and mode requested
            if instrument == "Multiple":
                instrument = self.instrument
            if mode == "All":
                mode = self.mode
            if (self.instrument in instrument) and (self.mode in mode):
                row = [kw,schmtype,hdu,level]
                tab.add_row(row)
        return tab
                
