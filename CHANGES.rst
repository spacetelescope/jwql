0.15.3
======

- Introduces `.readthedocs.yml`, which configures the `jwql` project documentation with ReadtheDocs


0.15.2
======

- Reorganizes the `jwql` repository into a structure that better incorporates instrument-specific monitoring scripts


0.15.1
======

- Adds `.pep8speaks.yml`, which configures the `pep8speaks` service for the `jwql` repository


0.15.0
======

- Adds `monitor_template.py`, which serves as a template with examples for instrument-specific monitors that we may write one day


0.14.1
======

- Moves all of the `jwql` web app code into the `jwql` package proper


0.14.0
======

- Adds a feature to `generate_preview_images` and `preview_image` that creates mosaicked preview images for NIRCam when applicable


0.13.1
======

- Changes to the way `monitor_mast` and `monitor_filesystem` `bokeh` plots are saved and displayed in the web application, from using `html` to using embedded `boken` components
- Adds some logging to `monitor_filesystem` and `monitor_mast`


0.13.0
======

- Adds `database_interface.py` and supporting documentation; this module enables the creation and maintenance of database tables in the `jwqldb` `postgresql` database
- Adds the `anomalies` table in `database_interface.py`


0.12.2
======

- Fixes some minor formatting issues with the `sphinx` docs for `monitor_filesystem` and `monitor_mast`


0.12.1
======

- Adds `ipython` to the `jwql` environment


0.12.0
======

- Adds a prototype of the `django` web application via the `website/` directory


0.11.6
======

- Adds the `jwql` code of conduct


0.11.5
======

- Some changes to `monitor_filesystem`, namely adding `sphinx` docs and adding a plot that shows the total file sizes and counts broken down by instrument


0.11.4
======

- Renames instances of `dbmonitor` to `monitor_mast` to be more consistent with `monitor_filesystem`


0.11.3
======

- This release removes the `_static` file from the `html_static_paths` parameters in the `conf.py` of the `sphinx` docs to avoid unnecessary warnings when trying to build the `sphinx` docs


0.11.2
======

- Changes the default value for the `verbose` option from `True` to `False` in `permissions.set_permissions`


0.11.1
======

- Adds unit tests for `preview_images.py`


0.11.0
======

- Adds `logging.logging_functions.py`, which provides a way to log the execution of modules


0.10.4
======

- Adds an update to the version of `django` for use by the web application


0.10.3
======

- Fixes the `Jenkinsfile` to use `name` for `build_mode`


0.10.2
======

- Brings `setup.py` up to `PEP-8` standards


0.10.1
======

- Adds `sphinx` API documentation for `db_monitor.py` and `test_db_monitor.py`


0.10.0
======

- Adds `monitor_filesystem.py`, which provides stats files and `bokeh` plots that describe the content of the MAST data cache


0.9.0
=====

- Adds `db_monitor.py` and supporting tests; this module creates `bokeh` plots and returns tables to describe the contents of the MAST database


0.8.0
=====

- Adds the `generate_preview_images` module, which generates preview images and thumbnails for all files in the filesystem


0.7.2
=====

- Adds a new `jupyter` notebook that identifies keywords that are in the MAST skipped list and also exist in the headers of multiple extensions


0.7.1
=====

- Changes the structure of the API docs, separating the modules into their own `.rst` files


0.7.0
=====

- Adds a `filename_parser` function in a `utils.py` module that returns a dictionary of elements contained in a given JWST filename


0.6.0
=====

- Adds API documentation build using `sphinx`; the documentation is located in the `docs` directory


0.5.0
=====

- Adds `permissions.py` and `test_permissions.py`, which are modules to help manage file and directory permissions


0.4.1
=====

- Hotfix to the `README` to describe how to clone the `jwql` repository using two-factor authentication/`sftp`


0.4.0
=====

- Adds `preview_image.py`, a module for generating a preview image for a given JWST observation


0.3.0
=====

- Adds package structure to the `jwql` repository, making it an installable package


0.2.0
=====

- Adds a `README` file that describes how to install and contribute to the `jwql` repository
- Adds an `environment.yml` file that contains the `jwqldev` environment


0.1.0
=====

- Adds the `jwql` style guide.