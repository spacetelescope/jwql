#! /usr/bin/env python

'''
for script development, run extract_schema.p
'''

import extract_schema

s = extract_schema.Schema()
s.indir = "input/directory/"
s.outdir = "output/directory/"
self.mode = "NRC_IMAGE"
self.instrument = "NIRCAM"
s.create_tables()
