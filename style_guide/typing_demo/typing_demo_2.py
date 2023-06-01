#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mypy + typing demo for JWQL dev meeting 2018-1-3

Part 2: More advanced techniques
"""

# ruff: noqa


from typing import (Iterable, Mapping, MutableMapping, Any, List,
                    Tuple, IO, ClassVar, NewType, Set, Union)
from astropy.io import fits
import numpy as np

# Use the above generic types for standard duck typing of functions, in the
# same way that you'd use abstract base classes


def needs_an_iterable(iterable_arg: Iterable[Any] = []) -> List[str]:
    return [str(x) for x in iterable_arg]


def dont_mutate(immut_dict: Mapping[Any, Any]) -> List[Tuple[Any, Any]]:
    return list(immut_dict.items())


def do_mutate(mut_dict: MutableMapping[Any, Any]) -> Set[Any]:
    mut_dict['jwql'] = True
    return set(mut_dict.keys())


# Variables can be annotated without initializing
stream: IO[str]
print(__annotations__['stream'])

# The IO type doesn't distinguish between reading, writing, or appending.
with open('demo.txt', 'w') as stream:
    for i in range(10):
        stream.write(f"{i}\n")

# Pre-annotation is also useful with conditional branches
conditional: str
if "jwql":
    conditional = "Yay!"
else:
    conditional = "Boo!"

# Data types from imported modules can be used just as easily as builtin types
an_array: np.ndarray = np.arange(10)
a_fits_header: fits.Header = fits.getheader("nirspec_irs2_nrs1_i_02.01.fits")


# Class attributes and methods can be annotated as well, and user-defined
# classes can be used to annotate other variables and functions.
class aClass(object):
    x: int = 0  # this is an instance variable with a default value
    y: ClassVar[List[int]]  # this is a class variable with no default value

    def __init__(self) -> None:  # doesn't return anything
        self.x = 1
        self.y = [2]
        # Can also annotate attributes in __init__
        self.z: np.float64 = np.float64(3.0)
        print(__annotations__)

    def result(self) -> np.float64:  # self shouldn't be annotated
        return x + np.array(self.y).sum() + self.z


print(aClass.__annotations__)
an_instance: aClass = aClass()
print(__annotations__["an_instance"])
print(an_instance.__annotations__)


# You can use forward references if you like defining things out of order
def preemptive_function(num: "Numberlike", user: "UserID") -> None:
    # Note that neither Numberlike or UserID have been defined.
    print(f"Y'know, {user}...")
    print(f"{num} should probably be some kind of number.")
    print("Just saying...")


# You can also define new types and type aliases
Numberlike = Union[int, float, np.float64]
UserID = NewType('UserID', str)

# Note that you can do anything with UserID that you can do with a string,
# and can pass a UserID to any function that would accept a string. However,
# operations on UserIDs will always result in strings, not UserIDs.
output = UserID('Gray') + UserID('Kanarek')
print(output)  # is of type string, not UserID.
