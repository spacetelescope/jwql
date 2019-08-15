#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 19 09:54:47 2018

@author: gkanarek
"""

from bokeh import layouts, models, palettes, plotting, transform
from inspect import getmembers, isclass, isfunction

from .bokeh_surface import Surface3d

bokeh_sequences = {}
bokeh_mappings = {"Surface3d": Surface3d}  # Note that abstract base classes *are* included


def parse_module(module):
    test = lambda nm, mem: (not nm.startswith("_")) and (module.__name__ in mem.__module__)
    seqs = {nm: mem for nm, mem in getmembers(module, isfunction) if test(nm, mem)}
    maps = {nm: mem for nm, mem in getmembers(module, isclass) if test(nm, mem)}
    # these need to be mappings
    if 'gridplot' in seqs:
        maps['gridplot'] = seqs.pop('gridplot')
    if 'Donut' in seqs:
        maps['Donut'] = seqs.pop('Donut')
    return (seqs, maps)


for module in [models, plotting, layouts, palettes, transform]:
    seqs, maps = parse_module(module)
    bokeh_sequences.update(seqs)
    bokeh_mappings.update(maps)
