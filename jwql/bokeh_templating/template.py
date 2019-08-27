#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jul 20 09:49:53 2018

@author: gkanarek
"""

import yaml
import os
from . import factory
from bokeh.embed import components


class BokehTemplateParserError(Exception):
    """
    A custom error for problems with parsing the interface files.
    """


class BokehTemplateEmbedError(Exception):
    """
    A custom error for problems with embedding components.
    """


class BokehTemplate(object):
    """
    This is the base class for creating Bokeh web apps using a YAML templating
    framework.
    """

    _mapping_factory = factory.mapping_factory
    _sequence_factory = factory.sequence_factory
    _figure_constructor = factory.figure_constructor
    _document_constructor = factory.document_constructor

    _embed = False

    def _self_constructor(self, loader, tag_suffix, node):
        """
        A multi_constructor for `!self` tag in the interface file.
        """
        yield eval("self" + tag_suffix, globals(), locals())

    def _register_default_constructors(self):
        for m in factory.mappings:
            yaml.add_constructor("!" + m + ":", self._mapping_factory(m))

        for s in factory.sequences:
            yaml.add_constructor("!" + s + ":", self._sequence_factory(s))

        yaml.add_constructor("!Figure:", self._figure_constructor)
        yaml.add_constructor("!Document:", self._document_constructor)
        yaml.add_multi_constructor(u"!self", self._self_constructor)

    def pre_init(self):
        """
        This should be implemented by the app subclass, to do any pre-
        initialization steps that it requires (setting defaults, loading
        data, etc).

        If this is not required, subclass should set `pre_init = None`
        in the class definition.
        """

        raise NotImplementedError

    def post_init(self):
        """
        This should be implemented by the app subclass, to do any post-
        initialization steps that the tool requires.

        If this is not required, subclass should set `post_init = None`
        in the class definition.
        """

        raise NotImplementedError

    def __init__(self):
        self._register_default_constructors()

        # Allow for pre-init stuff from the subclass.
        if self.pre_init is not None:
            self.pre_init()

        # Initialize attributes for YAML parsing
        self.formats = {}
        self.refs = {}
        self.document = None

        # Parse formatting string, if any, and the interface YAML file
        self.include_formatting()
        self.parse_interface()

        # Allow for post-init stuff from the subclass.
        if self.post_init is not None:
            self.post_init()

    def include_formatting(self):
        """
        This should simply be a dictionary of formatting keywords at the end.
        """
        if not self.format_string:
            return

        self.formats = yaml.load(self.format_string)

    def parse_interface(self):
        """
        This is the workhorse YAML parser, which creates the interface based
        on the layout file.

        `interface_file` is the path to the interface .yaml file to be parsed.
        """

        if not self.interface_file:
            raise NotImplementedError("Interface file required.")

        # Read the interface file into a string
        filepath = os.path.abspath(os.path.expanduser(self.interface_file))
        if not os.path.exists(filepath):
            raise BokehTemplateParserError("Interface file path does not exist.")
        with open(filepath) as f:
            interface = f.read()

        # First, let's make sure that there's a Document in here
        if not self._embed and '!Document' not in interface:
            raise BokehTemplateParserError("Interface file must contain a Document tag")

        # Now, since we've registered all the constructors, we can parse the
        # entire string with yaml. We don't need to assign the result to a
        # variable, since the constructors store everything in self.refs
        # (and self.document, for the document)

        self.full_stream = list(yaml.load_all(interface))

    def parse_string(self, yaml_string):
        return list(yaml.load_all(yaml_string))

    def embed(self, ref):
        element = self.refs.get(ref, None)
        if element is None:
            raise BokehTemplateEmbedError("Undefined component reference")
        return components(element)

    def register_sequence_constructor(self, tag, parse_func):
        if tag.startswith("!"):
            tag = tag[1:]

        def user_constructor(loader, node):
            value = loader.construct_sequence(node, deep=True)
            yield parse_func(value)
        user_constructor.__name__ = tag.lower() + "_constructor"
        yaml.add_constructor("!" + tag, user_constructor)

    def register_mapping_constructor(self, tag, parse_func):
        if tag.startswith("!"):
            tag = tag[1:]

        def user_constructor(loader, node):
            value = loader.construct_mapping(node, deep=True)
            yield parse_func(value)
        user_constructor.__name__ = tag.lower() + "_constructor"
        yaml.add_constructor("!" + tag, user_constructor)
