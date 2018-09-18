#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mypy + typing demo for JWQL dev meeting 2018-1-3

Part 3: mypy for type checking

Many thanks to Tommy Tutone...
"""

from typing import NewType

#mypy can check for incorrectly-typed variables

bad_variable: str = 1 #no runtime error

#This can especially be useful when using pre-annotation, since types can be
#hinted before calculations, I/O, or other complex code determines its value.
jenny: str

#mypy can also check function arguments and return values
def ive_got_your_number(num: int) -> bool:
    if num == 867_5309:
        return True
    else:
        return "Jenny don't change your number"

ive_got_your_number("jenny") #no runtime error
ive_got_your_number(555_1212) #no runtime error

if ive_got_your_number(8675_309):
    jenny = 867_5309 #no runtime error
else:
    jenny = "Don't change your number"
    
#If for some reason you don't want a particular variable's type to be checked, 
#then use comment syntax and "ignore"
dummy = None # type: ignore # otherwise this will throw a mypy error!

#mypy can handle user-created types
UserID = NewType("UserID", str)

gray: UserID = UserID("Gray")
kanarek: UserID = "Kanarek" #no runtime error

user: UserID = gray + kanarek #no runtime error

def get_first_char(user: UserID) -> str:
    return user[0]

get_first_char(gray)
get_first_char("Gray") #no runtime error

    
#mypy can help you figure out the types of variables, if it's complicated to 
#find out beforehand
reveal_type(1)
