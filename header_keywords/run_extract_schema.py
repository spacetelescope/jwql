#! /usr/bin/env python

'''
for script development, run extract_schema.p
'''

import extract_schema

s = extract_schema.Schema()
s.indir = "input/directory/"
s.outdir = "output/directory/"
s.create_tables()
