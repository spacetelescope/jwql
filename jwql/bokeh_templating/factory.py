"""
This module defines YAML constructors and factory functions which are
used to create Bokeh objects parsed from YAML template files.

The ``mapping_factory`` and ``sequence_factory`` functions are used to
create a constructor function for each of the mappings (i.e., classes)
and sequences  (i.e., functions) included in the keyword map. The
``document_constructor`` and ``figure_constructor`` functions are
stand-alone constructors for the ``!Document`` and ``!Figure`` tag,
respectively.

Author
-------

    - Graham Kanarek

Use
---

    The functions in this file are not intended to be called by the user
    directly; users should subclass the ``BokehTemplate`` class found in
    ``template.py`` instead. However, they can be used as a model for
    creating new constructors for user-defined tags, which can then be
    registered using the `BokehTemplate.register_mapping_constructor``
    and `BokehTemplate.register_sequence_constructor`` classmethods.

Dependencies
------------

    The user must have Bokeh installed.
"""

from bokeh.io import curdoc

from .keyword_map import bokeh_mappings as mappings, bokeh_sequences as sequences

# Figures get their own constructor so we remove references to Figures from
# the keyword maps.
Figure = mappings.pop("Figure")
del sequences["figure"]


def mapping_factory(tool, element_type):
    """
    Create a mapping constructor for the given tool, used to parse the
    given element tag.

    Parameters
    ----------
    tool : BokehTemplate instance
      The web app class instance to which the constructor will be
      attached. This will become ``self`` when the factory is a method,
      and is used to both store the Bokeh objects in the
      ``BokehTemplate.refs`` dictionary, and allow for app-wide
      formatting choices via ``BokehTemplate.format_string``.

    element_type : str
      The Bokeh element name for which a constructor is desired. For
      example, an ``element_type`` of ``'Slider'`` will create a
      constructor for a Bokeh ``Slider`` widget, designated by the
      ``!Slider`` tag in the YAML template file.

    Usage
    -----
    See the ``BokehTemplate`` class implementation in ``template.py``
    for an example of how this function is used.
    """

    def mapping_constructor(loader, node): #docstring added below
        fmt = tool.formats.get(element_type, {})
        value = loader.construct_mapping(node, deep=True)
        ref = value.pop("ref", "")
        callback = value.pop("on_change", [])
        selection_callback = value.pop("selection_on_change", [])
        onclick = value.pop("on_click", None)
        fmt.update(value)
        # convert the "range" YAML keyword of a slider into something Bokeh can read
        if element_type == "Slider":
            fmt["start"], fmt["end"], fmt["step"] = fmt.pop("range", [0, 1, 0.1])

        # Many of these have hybrid signatures, with both positional and
        # keyword arguments, so we need to convert an "args" keyword into
        # positional arguments
        arg = fmt.pop("arg", None)
        if arg is not None:
            obj = mappings[element_type](*arg, **fmt)
        else:
            obj = mappings[element_type](**fmt)

        # Store the object in the tool's "refs" dictionary
        if ref:
            tool.refs[ref] = obj

        # Handle callbacks and on_clicks
        if callback:
            obj.on_change(*callback)
        if onclick:
            obj.on_click(onclick)
        if selection_callback:
            obj.selected.on_change(*selection_callback)

        yield obj

    mapping_constructor.__name__ = element_type.lower() + '_' + mapping_constructor.__name__
    mapping_constructor.__doc__ = """
        A YAML constructor for the ``{et}`` Bokeh object. This will create a ``{et}``
        object wherever the ``!{et}`` tag appears in the YAML template file.
        If a ``ref`` tag is specified, the object will then be stored in the
        ``BokehTemplate.refs`` dictionary.

        This constructor is used for mappings -- i.e., classes or functions
        which primarily have keyword arguments in their signatures. If
        positional arguments appear, they can be included in the YAML file
        with the `args` keyword.
        """.format(et=element_type)

    return mapping_constructor


def sequence_factory(tool, element_type):
    """ Create a sequence constructor for the given tool, used to parse
    the given element tag.

    Parameters
    ----------
    tool : BokehTemplate instance
      The web app class instance to which the constructor will be
      attached. This will become ``self`` when the factory is a method,
      and is used to both store the Bokeh objects in the
      ``BokehTemplate.refs`` dictionary, and allow for app-wide
      formatting choices via ``BokehTemplate.format_string``.

    element_type : str
      The Bokeh element name for which a constructor is desired. For
      example, an ``element_type`` of ``'Slider'`` will create a
      constructor for a Bokeh ``Slider`` widget, designated by the
      ``!Slider`` tag in the YAML template file.

    Usage
    -----
    See the ``BokehTemplate`` class implementation in ``template.py``
    for an example of how this function is used.
    """

    def sequence_constructor(loader, node):
        fmt = tool.formats.get(element_type, {})
        value = loader.construct_sequence(node, deep=True)
        obj = sequences[element_type](*value, **fmt)
        yield obj

    sequence_constructor.__name__ = element_type.lower() + '_' + sequence_constructor.__name__
    sequence_constructor.__doc__ = """
        A YAML constructor for the ``{et}`` Bokeh object. This will create a ``{et}``
        object wherever the ``!{et}`` tag appears in the YAML template file.
        If a ``ref`` tag is specified, the object will then be stored in the
        ``BokehTemplate.refs`` dictionary.

        This constructor is used for sequences -- i.e., classes or functions
        which have only positional arguments in their signatures (which for
        Bokeh is only functions, no classes).
        """.format(et=element_type)

    return sequence_constructor


# These constructors need more specialized treatment

def document_constructor(tool, loader, node):
    """ A YAML constructor for the Bokeh document, which is grabbed via
    the Bokeh ``curdoc()`` function. When laying out a Bokeh document
    with a YAML template, the ``!Document`` tag should be used as the
    top-level tag in the layout.
    """

    layout = loader.construct_sequence(node, deep=True)
    for element in layout:
        curdoc().add_root(element)
    tool.document = curdoc()
    yield tool.document


def figure_constructor(tool, loader, node):
    """ A YAML constructor for Bokeh Figure objects, which are
    complicated enough to require their own (non-factory) constructor.
    Each ``!Figure`` tag in the YAML template file will be turned into a
    ``Figure`` object via this constructor (once it's been registered by
    the ``BokehTemplate`` class).
    """

    fig = loader.construct_mapping(node, deep=True)
    fmt = tool.formats.get('Figure', {})

    elements = fig.pop('elements', [])
    cmds = []
    ref = fig.pop("ref", "")
    callback = fig.pop("on_change", [])
    axis = tool.formats.get("Axis", {})
    axis.update(fig.pop("axis", {}))

    for key in fig:
        val = fig[key]
        if key in ['text', 'add_tools', 'js_on_event']:
            cmds.append((key, val))
        else:
            fmt[key] = val

    figure = Figure(**fmt)

    for key, cmd in cmds:
        if key == 'add_tools':
            figure.add_tools(*cmd)
        elif key == 'text':
            figure.text(*cmd.pop('loc'), **cmd)
        elif key == 'js_on_event':
            for event in cmd:
                figure.js_on_event(*event)

    for element in elements:
        key = element.pop('kind')
        shape = {'line': ('Line', figure.line),
                 'circle': ('Circle', figure.circle),
                 'diamond': ('Diamond', figure.diamond),
                 'triangle': ('Triangle', figure.triangle),
                 'square': ('Square', figure.square),
                 'asterisk': ('Asterisk', figure.asterisk),
                 'x': ('XGlyph', figure.x),
                 'vbar': ('VBar', figure.vbar)}
        if key in shape:
            fmt_key, glyph = shape[key]
            shape_fmt = tool.formats.get(fmt_key, {})
            shape_fmt.update(element)
            x = shape_fmt.pop('x', 'x')
            y = shape_fmt.pop('y', 'y')
            glyph(x, y, **shape_fmt)
        elif key == 'rect':
            rect_fmt = tool.formats.get('Rect', {})
            rect_fmt.update(element)
            figure.rect('rx', 'ry', 'rw', 'rh', **rect_fmt)
        elif key == 'quad':
            quad_fmt = tool.formats.get('Quad', {})
            quad_fmt.update(element)
            figure.quad(**quad_fmt)
        elif key == 'image':
            image_fmt = tool.formats.get('Image', {})
            image_fmt.update(element)
            arg = image_fmt.pop("image", None)
            figure.image(arg, **image_fmt)
        elif key == 'image_rgba':
            image_fmt = tool.formats.get('ImageRGBA', {})
            image_fmt.update(element)
            arg = image_fmt.pop("image", None)
            figure.image_rgba(arg, **image_fmt)
        elif key == 'multi_line':
            multi_fmt = tool.formats.get('MultiLine', {})
            multi_fmt.update(element)
            figure.multi_line(**multi_fmt)
        elif key == 'layout':
            obj = element.pop('obj', None)
            figure.add_layout(obj, **element)

    for attr, val in axis.items():
        # change axis attributes, hopefully
        setattr(figure.axis, attr, val)

    if ref:
        tool.refs[ref] = figure
    if callback:
        figure.on_change(*callback)

    yield figure
