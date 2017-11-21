Python Code Style Guide for `jwql`
=================================

This document serves as a style guide for all `jwql` software development.  Any requested contribution to the `jwql` code repository should be checked against this guide, and any violoation of the guide should be fixed before the code is committed to
the `master` branch.  Please refer to the accompanying `example.py` script for a example code that abides by this style guide.

Prerequisite Reading
--------------------

It is assumed that the reader of this style guide has read and is familiar with the following:

- The [PEP8 Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- The [PEP257 Docstring Conventions Style Guide](https://www.python.org/dev/peps/pep-0257/)
- The [`numpydoc` docstring convention](https://github.com/numpy/numpy/blob/master/doc/HOWTO_DOCUMENT.rst.txt)


Workflow
--------

All software development for the `jwql` project should follow a continuious integration workflow which resembles the following:

1. Open a GitHub issue - The GitHub issue should have an adequate description of the proposed feature, bug, or question.  Any appropriate individuals should be assinged to the issue, and a label(s), project(s) and/or milestone(s) should be tagged.
2. Create a branch in which to perform the software development.  Branch names should be short but descriptive (e.g. `new-database-table` or `fix-ingest-algorithm`) and not too generic (e.g. `bug-fix`).  Also consistent use of hyphens is encouraged.
3. Before commiting any code changes, use `flake8` to check the code against `PEP8` standards.  Also check that your code is conforming to this style guide.
4. Commit changes to the branch and push the branch to the remote repository.
5. Create a new pull request that compares the new branch to the target branch (usually `master`, unless one is branching off of another branch).
6. Request a reviewer on the pull request.
7. The reviewer checks the pull request against this style guide and proposes changes if necessary.
8. The author and reviewer iterate on changes until everyone is satisfied.
9. The reviewer accepts the pull request, merges the branch, and deletes the branch unless asked not to.
10. The author comments on the original GitHub issue with link to appropriate pull request and closes the issue if satisfied.


Version Numbers and Tags
------------------------

Any changes pushed to the `master` branch should be tagged with a version number.  The version number convention is `x.y.z`, where

    x = The main version number.  Increase when making incompatible API changes.
    y = The feature number.  Increase when change contains a new feature with or without bug fixes.
    z = The hotfix number. Increase when change only contains bug fixes.


`jwql`-specific Code Standards
------------------------------

`jwql` code shall adhere to the `PEP8` conventions save for the following exceptions:

 - Lines of code need not to be restricted to 79 characters.  However, it is encouraged to break up obnoxiously long lines into several lines if it benefits the overall readability of the code
 -


`jwql`-Specific Documentation Standards
---------------------------------------

`jwql` code shall adhere to the `PEP257` and `numpydoc` conventions.  The following are further reccomendations:

- Each module should have at minimum a description, `Authors`, `Use`, and `Dependencies` seciton.
- Each function/method should have at minimum a description, `Parameters` (if necessary), and `Returns` (if necessary) sections
-