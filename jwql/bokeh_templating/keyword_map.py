"""A script to scrape the Bokeh package and collate dictionaries of
classes and functions.

The ``_parse_module`` function iterates over a module, and uses the
``inspect`` package to sort everything in the module's namespace (as
identified by ``inspect.getmembers``) into a dictionary of mappings
(requiring primarily keyword arguments) and sequences (requiring
primarily positional arguments).

Note that thhe files ``surface3d.py`` and ``surface3d.ts``, used to
create 3D surface plots, were downloaded from the Bokeh ``surface3d``
example.

Author
-------

    - Graham Kanarek

Use
---

    To access the Bokeh elements, the user should import as follows:

    ::

        from jwql.bokeh_templating.keyword_map import bokeh_sequences, bokeh_mappings

Dependencies
------------

    The user must have Bokeh installed.
"""

from bokeh import layouts, models, palettes, plotting, transform
from inspect import getmembers, isclass, isfunction

from .surface3d import Surface3d

bokeh_sequences = {}
bokeh_mappings = {"Surface3d": Surface3d}  # Note that abstract base classes *are* included


def _parse_module(module):
    """Sort the members of a module into dictionaries of functions
    (sequences) and classes (mappings)."""

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
    seqs, maps = _parse_module(module)
    bokeh_sequences.update(seqs)
    bokeh_mappings.update(maps)
