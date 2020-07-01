"""
This module defines the ``BokehTemplate`` class, which can be subclassed
to create a Bokeh web app with a YAML templating file.


Author
-------

    - Graham Kanarek

Use
---

    The user should subclass the ``BokehTemplate`` class to create an
    app, as demonstrated in ``example.py``.

    (A full tutorial on developing Bokeh apps with ``BokehTemplate`` is
    forthcoming.)


Dependencies
------------

    The user must have Bokeh and PyYAML installed.
"""

import yaml
import os
from . import factory
from bokeh.embed import components
from inspect import signature


class BokehTemplate(object):
    """The base class for creating Bokeh web apps using a YAML
    templating framework.

    Attributes
    ----------
    _embed : bool
        A flag to indicate whether or not the individual widgets will be
        embedded in a webpage. If ``False``, the YAML interface file
        must include a !Document tag. Defaults to ``False``.
    document: obje
        The Bokeh Dpcument object (if any), equivalent to the result of
        calling ``curdoc()``.
    formats: dict
        A dictionary of widget formating specifications, parsed from
        ``format_string`` (if one exists).
    format_string: str
        A string of YAML formatting specifications, using the same
        syntax as the interface file, for Bokeh widgets. Note that
        formatting choices present in individual widget instances in the
        interface file override these.
    interface_file: str
        The path to the YAML interface file.
    refs : dict
        A dictionary of Bokeh objects which are given ``ref`` strings in
        the interface file. Use this to store and interact with the
        Bokeh data sources and widgets in callback methods.

    Methods
    -------
    ``_mapping_factory``, ``_sequence_factory``,
    ``_figure_constructor``, and ``_document_constructor`` are imported
    from ``bokeh_templating.factory``, used by the interface parser to
    construct Bokeh widgets.
    """

    # Each of these functions has a ``tool`` argument, which becomes ``self``
    # when they are stored as methods. This way, the YAML constructors can
    # store the Bokeh objects in the ``tool.ref`` dictionary, and can access
    # the formatting string, if any. See ``factory.py`` for more details.
    _mapping_factory = factory.mapping_factory
    _sequence_factory = factory.sequence_factory
    _figure_constructor = factory.figure_constructor
    _document_constructor = factory.document_constructor
    _embed = False
    document = None
    format_string = ""
    formats = {}
    interface_file = ""
    refs = {}

    def __init__(self, **kwargs):
        # Register the default constructors
        self._register_default_constructors()

        # Allow for pre-initialization code from the subclass.
        if self.pre_init is not None:
            if signature(self.pre_init).parameters:
                # If we try to call pre_init with keyword parameters when none
                # are included, it will throw an error; thus, we use inspect.signature
                self.pre_init(**kwargs)
            else:
                self.pre_init()

        # Initialize attributes for YAML parsing
        self.formats = {}
        self.refs = {}

        # Parse formatting string, if any, and the interface YAML file
        self._include_formatting()
        self._parse_interface()

        # Allow for post-init stuff from the subclass.
        if self.post_init is not None:
            self.post_init()

    def _include_formatting(self):
        """A utility function to parse the format string, if any."""
        if not self.format_string:
            return

        self.formats = yaml.load(self.format_string, Loader=yaml.Loader)

    def _parse_interface(self):
        """Parse the YAML interface file using the registered
        constructors
        """

        if not self.interface_file:
            raise NotImplementedError("Interface file required.")

        # Read the interface file into a string
        filepath = os.path.abspath(os.path.expanduser(self.interface_file))
        if not os.path.exists(filepath):
            raise BokehTemplateParserError("Interface file path does not exist.")
        with open(filepath) as f:
            interface = f.read()

        # If necessary, verify that the interface string contains !Document tag
        if not self._embed and '!Document' not in interface:
            raise BokehTemplateParserError("Interface file must contain a Document tag")

        # Now, since we've registered all the constructors, we can parse the
        # entire string with yaml. We don't need to assign the result to a
        # variable, since the constructors store everything in self.refs
        # (and self.document, for the document).
        try:
            yaml.load_all(interface)
        except yaml.YAMLError as exc:
            raise BokehTemplateParserError(exc)

    def _register_default_constructors(self):
        """Register all  the default constructors with
        ``yaml.add_constructor``.
        """
        for m in factory.mappings:
            yaml.add_constructor("!" + m + ":", self._mapping_factory(m))

        for s in factory.sequences:
            yaml.add_constructor("!" + s + ":", self._sequence_factory(s))

        yaml.add_constructor("!Figure:", self._figure_constructor)
        yaml.add_constructor("!Document:", self._document_constructor)
        yaml.add_multi_constructor(u"!self", self._self_constructor)

    def _self_constructor(self, loader, tag_suffix, node):
        """A multi_constructor for `!self` tag in the interface file."""
        yield eval("self" + tag_suffix, globals(), locals())

    def embed(self, ref):
        """A wrapper for ``bokeh.embed.components`` to return embeddable
        code for the given widget reference."""
        element = self.refs.get(ref, None)
        if element is None:
            raise BokehTemplateEmbedError("Undefined component reference")
        return components(element)

    @staticmethod
    def parse_string(yaml_string):
        """ A utility functon to parse any YAML string using the
        registered constructors. (Usually used for debugging.)"""
        return list(yaml.load_all(yaml_string))

    def post_init(self):
        """This should be implemented by the app subclass, to perform
        any post-initialization actions that the tool requires.

        If this is not required, the subclass should set
        `post_init = None` in the class definition.
        """

        raise NotImplementedError

    def pre_init(self, **kwargs):
        """This should be implemented by the app subclass, to perform
        any pre-initialization actions that it requires (setting
        defaults, loading data, etc). Note that positional arguments are
        not currently supported.

        If this is not required, the subclass should set
        `pre_init = None` in the class definition.
        """

        raise NotImplementedError

    @classmethod
    def register_sequence_constructor(cls, tag, parse_func):
        """
        Register a new sequence constructor with YAML.

        Parameters
        ----------
        tag : str
            The YAML tag string to be used for the constructor.
        parse_func: object
            The parsing function to be registered with YAML. This
            function should accept a multi-line string, and return a
            python object.

        Usage
        -----
        This classmethod should be used to register a new constructor
        *before* creating & instantiating a subclass of BokehTemplate :

        ::

            from bokeh_template import BokehTemplate
            BokehTemplate.register_sequence_constructor("my_tag", my_parser)

            class myTool(BokehTemplate):
                pass

            myTool()
        """
        if tag.startswith("!"):
            tag = tag[1:]

        def user_constructor(loader, node):
            value = loader.construct_sequence(node, deep=True)
            yield parse_func(value)
        user_constructor.__name__ = tag.lower() + "_constructor"
        yaml.add_constructor("!" + tag, user_constructor)

    @classmethod
    def register_mapping_constructor(cls, tag, parse_func):
        """
        Register a new mapping constructor with YAML.

        Parameters
        ----------
        tag : str
            The YAML tag string to be used for the constructor.
        parse_func: object
            The parsing function to be registered with YAML. This
            function should accept a multi-line string, and return a
            python object.

        Usage
        -----
        This classmethod should be used to register a new constructor
        *before* creating & instantiating a subclass of BokehTemplate :

        ::

            from bokeh_template import BokehTemplate
            BokehTemplate.register_mapping_constructor("my_tag", my_parser)

            class myTool(BokehTemplate):
                pass

            myTool()
        """
        if tag.startswith("!"):
            tag = tag[1:]

        def user_constructor(loader, node):
            value = loader.construct_mapping(node, deep=True)
            yield parse_func(value)
        user_constructor.__name__ = tag.lower() + "_constructor"
        yaml.add_constructor("!" + tag, user_constructor)


class BokehTemplateEmbedError(Exception):
    """A custom error for problems with embedding components."""


class BokehTemplateParserError(Exception):
    """A custom error for problems with parsing the interface files."""
