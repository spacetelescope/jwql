#! /usr/bin/env python

"""
This module is a collection of plotting functions that may be used
across the ``jwql`` application.

Authors:
--------

    - Joe Filippazzo

Use:
----

    This module can be use as follows:

    ::

        from jwql.utils import plotting
        from pandas import DataFrame
        data = DataFrame({'meow': {'foo': 12, 'bar': 23, 'baz': 2},
                          'mix': {'foo': 45, 'bar': 31, 'baz': 23},
                          'deliver': {'foo': 62, 'bar': 20, 'baz': 9}})
        data = data.reset_index()
        plt = plotting.bar_chart(data, 'index')
"""

from bokeh.models import ColumnDataSource, FactorRange, HoverTool
from bokeh.palettes import Category20c
from bokeh.plotting import figure
from bokeh.transform import factor_cmap


def bar_chart(dataframe, groupcol, datacols=None, **kwargs):
    """Create a pie chart from a Pandas DataFrame

    Parameters
    ----------
    dataframe : pandas.DataFrame
        A dataframe of values
    groupcol : str
        The name of the column with the group labels
    datacol : str, sequence (optional)
        The name or list of names of the column containing the data.
        In None, uses all columns except **groupcol**

    Returns
    -------
    plt : obj
        The generated bokeh.figure object
    """
    
    # Get the groups
    groups = list(dataframe[groupcol])

    # Get the datacols
    if datacols is None:
        datacols = [col for col in list(dataframe.columns) if col != groupcol]

    # Make a dictionary of the groups and data
    data = {'groups': groups}
    for col in datacols:
        data.update({col: list(dataframe[col])})

    # hstack it
    x = [(group, datacol) for group in groups for datacol in datacols]
    counts = sum(zip(*[data[col] for col in datacols]), ())
    colors = max(3, len(datacols))
    source = ColumnDataSource(data=dict(x=x, counts=counts))

    # Make the figure
    hover = HoverTool(tooltips=[('count', '@counts')])
    plt = figure(x_range=FactorRange(*x), plot_height=250, tools=[hover],
                 **kwargs)
    plt.vbar(x='x', top='counts', width=0.9, source=source, line_color="white",
             fill_color=factor_cmap('x', palette=Category20c[colors],
                                    factors=datacols, start=1, end=2))

    # Formatting
    plt.y_range.start = 0
    plt.x_range.range_padding = 0.1
    plt.xaxis.major_label_orientation = 1
    plt.xgrid.grid_line_color = None

    return plt
