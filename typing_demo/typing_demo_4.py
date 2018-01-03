#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mypy + typing demo for JWQL dev meeting 2018-1-3

Part 4: Subtlety
"""

#Why do we care about this? Because errors can be subtle.

#A simple example!

def get_favorite_number():
    return input("What's your favorite number? ")

num = get_favorite_number()
print("Twice your favorite number is", num*2)
