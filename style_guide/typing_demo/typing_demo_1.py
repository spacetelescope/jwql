#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mypy + typing demo for JWQL dev meeting 2018-1-3

Part 1: Intro
"""

import sys
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Tuple, Union

assert sys.version_info >= (3, 6)  # PEP 526 added variable annotations

an_integer: int = 1
a_float: float = 1.0
a_bool: bool = True
a_string: str = "jwql"
a_list: List[int] = [1]
a_set: Set[int] = {1, 2, 3}
a_dict: Dict[str, bool] = {"jwql": True}  # Have to specify both keys and values

# For python versions prior to 3.6, the variable annotation syntax uses comments:
#    annotated_variable = 1 # type: int

# Tuples are a little different - we can specify a type for each element of a
# tuple because they're immutable
a_heterogeneous_tuple: Tuple[int, bool] = (1, True)
an_empty_tuple: Tuple[()] = ()

# For heterogeneous non-tuples, use Union.
a_heterogeneous_list: List[Union[int, bool, str]] = [1, True, "jwql"]
a_heterogeneous_dict: Dict[Union[str, int], Union[bool, int]] = {"jwql": True, 1: 1}

# If a value can be None, use Optional
maybe_a_string: Optional[str] = "jwql" if not a_bool else None


# For functions, there's a similar annotation syntax
def a_generic_function(num: int) -> str:
    return f"You passed {num} to this completely generic function."


def two_arg_function(name: str, num: float = 0.0) -> None:
    print(f"Sorry {name}, this function won't return {num}")


# Function aliases and anonymous functions can also be annotated  with the
# same variable syntax

func_alias: Callable[[str, float], None] = two_arg_function
anon_func: Callable[[Any], int] = lambda x: 1


# Generators are just functions which return iterables:
def a_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


# NOT RECOMMENDED
my_metavar: "hey i'm metadata!" = "not metadata"
print(__annotations__["my_metavar"])


# Type annotations are stored in __annotations__, either as a local variable
# or as an object attribute.


def print_annotations(arg: Any) -> bool:
    if not hasattr(arg, "__annotations__"):
        print("Sorry, that argument doesn't have its own __annotations__.")
        return False
    print(arg.__annotations__)
    return bool(arg.__annotations__)


for name in ["an_integer", "a_generic_function", "two_arg_function", "func_alias", "anon_func", "a_generator"]:
    var = locals()[name]
    print(f"Annotations for {name}:")
    if not print_annotations(var):
        print("Instead, we'll check the local instance of __annotations__:")
        print(__annotations__[name])
