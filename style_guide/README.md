`jwql` Style Guide
==================

This document serves as a style guide for all `jwql` software development.  Any requested contribution to the `jwql` code repository should be checked against this guide, and any violation of the guide should be fixed before the code is committed to
the `master` or `develop` branch.  Please refer to the accompanying [`example.py`](https://github.com/spacetelescope/jwql/blob/master/style_guide/example.py) script for an example of code that abides by this style guide.

Prerequisite Reading
--------------------

It is assumed that the reader of this style guide has read and is familiar with the following:

- The [PEP8 Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)
- The [PEP257 Docstring Conventions Style Guide](https://www.python.org/dev/peps/pep-0257/)
- The [`numpydoc` docstring convention](https://numpydoc.readthedocs.io/en/latest/format.html)


Workflow
--------

All software development for the `jwql` project should follow a continuous integration workflow, described in the [`git` & GitHub workflow for contributing](https://github.com/spacetelescope/jwql/wiki/git-%26-GitHub-workflow-for-contributing).  Before committing any code changes, use `flake8` to check the code against `PEP8` standards.  Also check that your code is conforming to this style guide.


Version Numbers and Tags
------------------------

Any changes pushed to the `master` branch should be tagged with a version number.  The version number convention is `x.y.z`, where

    x = The main version number.  Increase when making incompatible API changes.
    y = The feature number.  Increase when change contains a new feature with or without bug fixes.
    z = The hotfix number. Increase when change only contains bug fixes.


Security
--------

The following items should never be committed in the `jwql` source code or GitHub issues/pull requests:

- Account credentials of any kind (e.g. database usernames and passwords)
- Internal directory structures or filepaths
- Machine names
- Proprietary data

If `jwql` code needs to be aware of this information, it should be stored in a configuration file that is not part of the `jwql` repository.

Additionally, developers of this project should be mindful of application security risks, and should adhere to the [OWASP Top 10](https://www.owasp.org/images/7/72/OWASP_Top_10-2017_%28en%29.pdf.pdf) as well as possible.


`jwql`-specific Code Standards
------------------------------

`jwql` code shall adhere to the `PEP8` conventions save for the following exceptions:

 - Lines of code need not be restricted to 79 characters.  However, it is encouraged to break up obnoxiously long lines into several lines if it benefits the overall readability of the code

 Additionally, the code shall adhere to the following special guidelines:

 - Function and class definitions should be placed in alphabetical order in the module
 - It is encouraged to annotate variables and functions using the [`typing`](https://docs.python.org/3/library/typing.html) module (see [PEP 483](https://www.python.org/dev/peps/pep-0483/), [PEP 484](https://www.python.org/dev/peps/pep-0484/), and [PEP 526](https://www.python.org/dev/peps/pep-0526/)). In addition, it is recommended that code be type-checked using [`mypy`](http://mypy-lang.org/) before a pull request is submitted.


`jwql`-Specific Documentation Standards
---------------------------------------

`jwql` code shall adhere to the `PEP257` and `numpydoc` conventions.  The following are further recommendations:

- Each module should have at minimum a description, and `Authors` and `Use` sections.
- Each function/method should have at minimum a description, and `Parameters` (if necessary) and `Returns` (if necessary) sections.


`jwql`-Specific Logging Standards
---------------------------------
`jwql` employs standards for logging monitoring scripts.  See the [`logging guide`](https://github.com/spacetelescope/jwql/blob/develop/style_guide/logging_guide.md) for further details.


`jwql`-Specific Variable Value/Type Standards
---------------------------------------------

To the extent possible, `jwql` shall define frequently-used variable types/values consistently. A list of adopted standards is provided below:

- **JWST instrument names**: In all internal references and structures (e.g. dictionaries) instrument names shall be all lower-case strings, e.g. one of `fgs`, `miri`, `niriss`, `nircam`, `nirspec`. When variations are required for interfaces, e.g. `Nircam` for MAST, `NIRCam` or `NIRCAM` for SIAF, etc. these should be defined as dictionaries in [`jwql/utils/constants.py`](https://github.com/spacetelescope/jwql/blob/master/jwql/utils/constants.py) and imported from there.

- **Program/proposal identifiers**: JWST program IDs shall be stored and referred to internally as integers and parsed to strings only when needed. For example, the inputs `"001144"` and `"1144"` shall both be converted to an integer variable with value `1144`.


Accessibility in Development
----------------------------
`jwql` strives to create web pages and code that are as accessibile as possible for all users. See the [`accessibility guidelines`](https://github.com/spacetelescope/jwql/blob/develop/style_guide/accessibility_guidelines.md) page for further details.


Tools and Library Recommendations
---------------------------------

- `argparse` for parsing command line arguments
- `bokeh` for interactive plotting
