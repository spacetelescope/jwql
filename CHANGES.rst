0.17.0 (2019-02-05)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a wiki page for how to do a software release
- Added a wiki page with a checklist for contributors and reviewers
- Added a wiki page about the web server
- Defined specific variable value/type standards for JWST instruments and program/proposal identifiers in the Style Guide

Web Application
~~~~~~~~~~~~~~~
- Added authentication to all pages using the ``auth.mast`` service provided by the Archive Services Branch
- Implemented AJAX requests to load the ``thumbnails.html`` and ``archive.html`` pages
- Used regular expressions to restrict URLs
- Updated permissions in ``nginx`` settings to fix bug where dashboard page would not display
- Added a loading widget while thumbnails compile

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~
- Added interface with the JWST DMS engineering database: ``utils.engineering_database``
- Expanded ``utils.filename_parser`` to handle time series and DMS stage 3 file names
- Consolidated important constants in new ``utils.constants`` module


0.16.0 (2018-12-17)
===================

This is the first release of the new release procedures of ``jwql``.  The development team is now developing in release-driven sprints, so future releases will be less frequent, but with more changes

Changes since the ``0.15.3`` release include:

- Various updates and additions to the ``jwql`` ``conda`` environment:
    - Updated ``bokeh`` to version 1.0
    - Updated ``django`` to fix security issues
    - Added ``pandas`` as a dependency
- Various updates and additions to the project and API documentation:
    - Added a project description in the API docs
    - Added web app API docs
- Various changes to the web application:
    - Made changes to the code to get it working on the web development server
    - Added several REST API services
    - Added API documentation button to the navbar and anded link to API documentation in the ``about`` page
    - Added instrument-specific documentation button to the instrument landing pages
    - Replaced ``monitor_mast`` donut charts with bar charts
    - Removed dashboard and database query buttons from homepage
    - Added form to homepage that allows user to view preview images for a given rootname or proposal number
    - Changed URL patters to allow for separation between nominal web app and REST API service
    - Added ``monitor_cron_jobs`` monitor that builds and renders a table displaying ``cron`` job execution status
- Various changes to the ``jwql`` repository:
    - Added badges to the ``README``
    - Configured ``pyup`` service for the ``jwql`` repository via ``.pyup.yml`` file
    - Added a separate ``requirement.txt`` file to keep track of requirements needed by ReadTheDocs and the ``pyup`` service
    - Added various ``jwql`` presentations in separate ``presentations/`` directory
- Other various code changes:
    - Changed ``logging_functions.py`` to be more conservative on when to write log files to the production area
    - Added ``plotting.py`` module (and supporting unit tests), which stores various plotting-related functions


0.15.3
======

- Added ``.readthedocs.yml``, which configures the ``jwql`` project documentation with ReadtheDocs


0.15.2
======

- Reorganized the ``jwql`` repository into a structure that better incorporates instrument-specific monitoring scripts


0.15.1
======

- Added ``.pep8speaks.yml``, which configures the ``pep8speaks`` service for the ``jwql`` repository


0.15.0
======

- Added ``monitor_template.py``, which serves as a template with examples for instrument-specific monitors that we may write one day


0.14.1
======

- Moved all of the ``jwql`` web app code into the ``jwql`` package proper


0.14.0
======

- Added a feature to ``generate_preview_images`` and ``preview_image`` that creates mosaicked preview images for NIRCam when applicable


0.13.1
======

- Changed the way ``monitor_mast`` and ``monitor_filesystem`` ``bokeh`` plots are saved and displayed in the web application, from using ``html`` to using embedded ``boken`` components
- Added some logging to ``monitor_filesystem`` and ``monitor_mast``


0.13.0
======

- Added ``database_interface.py`` and supporting documentation; this module enables the creation and maintenance of database tables in the ``jwqldb`` ``postgresql`` database
- Added the ``anomalies`` table in ``database_interface.py``


0.12.2
======

- Fixed some minor formatting issues with the ``sphinx`` docs for ``monitor_filesystem`` and ``monitor_mast``


0.12.1
======

- Added ``ipython`` to the ``jwql`` environment


0.12.0
======

- Added a prototype of the ``django`` web application via the ``website/`` directory


0.11.6
======

- Added the ``jwql`` code of conduct


0.11.5
======

- Changes to ``monitor_filesystem``, namely adding ``sphinx`` docs and adding a plot that shows the total file sizes and counts broken down by instrument


0.11.4
======

- Renamed instances of ``dbmonitor`` to ``monitor_mast`` to be more consistent with ``monitor_filesystem``


0.11.3
======

- Removed the ``_static`` file from the ``html_static_paths`` parameters in the ``conf.py`` of the ``sphinx`` docs to avoid unnecessary warnings when trying to build the ``sphinx`` docs


0.11.2
======

- Changed the default value for the ``verbose`` option from ``True`` to ``False`` in ``permissions.set_permissions``


0.11.1
======

- Added unit tests for ``preview_images.py``


0.11.0
======

- Added ``logging.logging_functions.py``, which provides a way to log the execution of modules


0.10.4
======

- Added an update to the version of ``django`` for use by the web application


0.10.3
======

- Fixed the ``Jenkinsfile`` to use ``name`` for ``build_mode``


0.10.2
======

- Changed ``setup.py`` to adhere to ``PEP-8`` standards


0.10.1
======

- Added ``sphinx`` API documentation for ``db_monitor.py`` and ``test_db_monitor.py``


0.10.0
======

- Added ``monitor_filesystem.py``, which provides stats files and ``bokeh`` plots that describe the content of the MAST data cache


0.9.0
=====

- Added ``db_monitor.py`` and supporting tests; this module creates ``bokeh`` plots and returns tables to describe the contents of the MAST database


0.8.0
=====

- Added the ``generate_preview_images`` module, which generates preview images and thumbnails for all files in the filesystem


0.7.2
=====

- Added a new ``jupyter`` notebook that identifies keywords that are in the MAST skipped list and also exist in the headers of multiple extensions


0.7.1
=====

- Changed the structure of the API docs, separating the modules into their own ``.rst`` files


0.7.0
=====

- Added a ``filename_parser`` function in a ``utils.py`` module that returns a dictionary of elements contained in a given JWST filename


0.6.0
=====

- Added API documentation build using ``sphinx``; the documentation is located in the ``docs`` directory


0.5.0
=====

- Added ``permissions.py`` and ``test_permissions.py``, which are modules to help manage file and directory permissions


0.4.1
=====

- Changed the ``README`` to describe how to clone the ``jwql`` repository using two-factor authentication/``sftp``


0.4.0
=====

- Added ``preview_image.py``, a module for generating a preview image for a given JWST observation


0.3.0
=====

- Added package structure to the ``jwql`` repository, making it an installable package


0.2.0
=====

- Added a ``README`` file that describes how to install and contribute to the ``jwql`` repository
- Added an ``environment.yml`` file that contains the ``jwqldev`` environment


0.1.0
=====

- Added the ``jwql`` style guide.
