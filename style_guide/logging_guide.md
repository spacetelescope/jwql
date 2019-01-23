Logging Style Guide for `jwql`
=================================

This document serves as a style guide for adding logging to `jwql` software development.  Any requested contribution to the `jwql` code repository should be checked against this guide to ensure proper usage of logging functions, and any violation of this and the style guide should be fixed before the code is committed to
the `master` branch.  Please refer to the accompanying [`example.py`](https://github.com/spacetelescope/jwql/blob/master/style_guide/example.py) script for a example code that abides by the style guide and the logging guide.


Introduction
------------

To begin, all users that request to contribute to the `jwql` code repository should conform to the following logging guidelines. This is to ensure uniformity and ease of understanding various tools log files. This will help allow for monitoring scripts to properly function on current and future tools created.

The `logging_function.py` script can be found within the `jwql` code repository underneath the `utils` directory. Users can review that code for information on how our logging works, but should be able to setup their logging by following these suggestions without the need to investigate that source code. 


Logging Set-Up
--------------



What Must be Logged
-------------------



