## What's Changed

1.2.3 (2024-01-26)
==================

Web Application
~~~~~~~~~~~~~~~
- Update Anomaly Names by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1435
- Bug fix for multiple query anomalies by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1442

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Moving monitor outputs used by the server to central storage by @york-stsci in https://github.com/spacetelescope/jwql/pull/1397
- Update Path for Claw and Background Monitor by @mfix in https://github.com/spacetelescope/jwql/pull/1444

1.2.2 (2024-01-11)
==================

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Increase MAST query limit by @ bhilbert4 in https://github.com/spacetelescope/jwql/pull/1427
- Hotfix: Crashing archive_database_update @ BradleySappington in https://github.com/spacetelescope/jwql/pull/1425


1.2.1 (2023-12-20)
==================

Web Application
~~~~~~~~~~~~~~~
- Visit Filter on query and archive thumbnails pages by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1412

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- NIRCam Claw Monitor by @bsunnquist in https://github.com/spacetelescope/jwql/pull/1152
- Stop storing absolute paths in the database by @york-stsci in https://github.com/spacetelescope/jwql/pull/1394


1.2.0 (2023-11-21)
==================

Web Application
~~~~~~~~~~~~~~~
- Hover over proposal thumbnails by @shanosborne in https://github.com/spacetelescope/jwql/pull/927
- Not found images replaced with default image by @BradleySappington in https://github.com/spacetelescope/jwql/pull/949
- Remove second set of colorbar tick labels from preview images by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/963
- Split program page by obsnum by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/948
- Interactive preview images by @BradleySappington in https://github.com/spacetelescope/jwql/pull/965
- Alert user to non-existant proposal number by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/994
- Fix bad thumbnails by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/997
- Explore by group type by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1000
- Default scaling params for preview images where all pix are NaN by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1006
- Explore int grp difference by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1020
- Add inst select home search by @mengesser in https://github.com/spacetelescope/jwql/pull/1010
- Allow proposal thumbnails to come from dark thumbnails by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1001
- Adding Next and Previous Buttons by @mfixstsci in https://github.com/spacetelescope/jwql/pull/978
- Build archive page from database by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1030
- Select anomaly name formatting by @rcooper295 in https://github.com/spacetelescope/jwql/pull/1053
- Implement "Viewed" Button and Filtering by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1049
- fixes for no data found on server by @penaguerrero in https://github.com/spacetelescope/jwql/pull/1042
- Filter archive page by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1065
- Exposure page: Default to show rate img, keep order of radio buttons constant by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1111
- Filter type by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1092
- Sort obs date by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1113
- added scattered light, light saber anomalies for niriss by @rcooper295 in https://github.com/spacetelescope/jwql/pull/1133
- Add new NIRCam anomalies by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1136
- Add Logging View by @mfixstsci in https://github.com/spacetelescope/jwql/pull/1080
- Remove bokeh templating from Dark monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1153
- Fix API view for filenames per proposal and preview images by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1046
- Create archive page asynchronously by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1203
- Adding sort by category by @mfixstsci in https://github.com/spacetelescope/jwql/pull/1155
- Improve bad pixel monitor plots by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1202
- List viewed/new status by instrument by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1197
- Display all detectors by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1213
- Remove bokeh templating from Bias Monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1230
- Reformat query page functionality by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1240
- Add download links to image pages by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1283
- Improve explore image by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1282
- Remove Bokeh Templating from Readnoise Monitor by @mfixstsci in https://github.com/spacetelescope/jwql/pull/1238
- Move Date Range selection to Query Page by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1396

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Make Readnoise Monitor less memory-intensive  by @bsunnquist in https://github.com/spacetelescope/jwql/pull/922
- Speed up MAST queries by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/942
- Lock python by @BradleySappington in https://github.com/spacetelescope/jwql/pull/955
- Reduce memory usage by the dark monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/908
- Fix clipping logic in preview image scaling by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1011
- Cosmic ray monitor (via mengesser:develop) by @bourque in https://github.com/spacetelescope/jwql/pull/700
- nirspec TA monitors: wata and msata by @penaguerrero in https://github.com/spacetelescope/jwql/pull/888
- allow per-instrument database table reset by @york-stsci in https://github.com/spacetelescope/jwql/pull/1031
- Celery monitors by @york-stsci in https://github.com/spacetelescope/jwql/pull/921
- Raise the upper limit on number of returned Mast entries by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1048
- Added chunked iteration to CR monitor by @york-stsci in https://github.com/spacetelescope/jwql/pull/1066
- Created a clone_tables script by @york-stsci in https://github.com/spacetelescope/jwql/pull/1059
- Add EDB telemetry monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/832
- Tweaks to mnemonics queried by the EDB monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1115
- Fix failing MIRI dark montior by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1129
- Unit test cleanup by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1167
- Catch missing obs in navigation data by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1206
- Update preview image generator to handle new NaN pixels by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1212
- drop support for Python 3.8 by @zacharyburnett in https://github.com/spacetelescope/jwql/pull/1249
- Adding Python 3.10 Support to Testing Matrix by @mfixstsci in https://github.com/spacetelescope/jwql/pull/1257
- Remove mast monitor by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1256
- Improve general JWQL queries by @melanieclarke in https://github.com/spacetelescope/jwql/pull/1281
- Prepare models for external postgres db by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1287
- Pipeline skip already run steps by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1262
- Include migrations in source control by @BradleySappington in https://github.com/spacetelescope/jwql/pull/1364
- Add step_args to calwebb_detector1_save_jump by @bhilbert4 in https://github.com/spacetelescope/jwql/pull/1358

--Full Changelog--: https://github.com/spacetelescope/jwql/compare/1.1.0...1.2.0

Unreleased
==========

Web Application
~~~~~~~~~~~~~~~

- Dark and Bad Pixel Monitors delete unnecessary outputs to save disk space (#933)


1.1.1 (2022-04-05)
==================

- Correction of bad wheel file in version 1.1.0


1.1.0 (2022-04-04)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Adding RTD Requirements file and yml
- Updated JDOX links so they don't produce 404 errors
- Updates to About page


Web Application
~~~~~~~~~~~~~~~

- Speed up Webapp loading
- Stripped code for creating mosaic preview images
- Ignoring unuseful pipeline products
- Updated feature desciption on EDB page
- Closed all open sessions to db explicitly
- Fix/Modify Integration Number slider
- Switch filesystem and astroquery.mast to point to OPS
- Updates to BANDIT CI
- Made plotting limits robust to missing data
- Removing reliance on jwst-dms-edb
- Updated MIRI Readout Patterns
- Updated "Filter By" Dropdown in Archive View
- Plot non-numerical mnemonic dataset


``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Removed python 3.7 support
- Added python 3.9 environment
- Updated README to reflect changes in environment files.


1.0.0 (2021-10-05)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Included documentation describing the algorithms used for instrument monitors
- Included templates for bug reports and feature requests as well as a link to submit issues on the ``home`` page
- Included ``Documentation`` option on instrument drop down menu in the navigation bar


Web Application
~~~~~~~~~~~~~~~

- All relevant instruments (NIRCam, NIRISS, NIRSpec) are incorporated into the Bias Monitor
- The generalized pipeline function from ``pipeline_tools.py`` is used for image calibration
- For exposures containing multiple integrations, created thumbnail image for only a single ingtegration
- Implemented tests for all Monitor webpages


``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Modified filesystem to reflect MAST-like organizational structure
- Implemented application security tools into GitHub Actions builds
- Switched filesystem to use latest DMS build
- Improved configuration file handling


Bug Fixes
---------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Include API Docs for all modules, classes, and functions in ReadTheDocs


Web Application
~~~~~~~~~~~~~~~

- Included various fixes and improvements suggested during stakeholder demonstrations
- Fixed ``View Image``, ``View Proposal``, and ``View Header`` buttons
- Updated dashboard such that ``NULL`` Monitor Status values were fixed
- Updated options that users can select for general image queries
- Eliminated pop-up warning when viewing fits file headers in the web app
- Removed login button on homepage and supporting authentication code and replaced with SSO authentication


``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed Dark Monitor failure due to dither point keyword values in data
- Addressed Dark Monitor failure with data including 64-bit integers
- Resolved the NIRSpec amp boundary issue
- Fixed missing reference file error handling with latest DMS build in Readnoise Monitor
- Ensured Dark, Bias, and Readnoise Monitors complete successfully with latest DMS build
- Included read persmissions for database tables
- Performed flake8 sweep of the code repository
- Updated software to support the latest versions of ``bokeh`` and ``pysiaf``
- Removed dependencies on the astroconda channel



0.26.0 (2021-03-30)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Included badges for GitHub Actions in ``README.md``
- Replaced Jenkins support with GitHub Actions for CI testing
- Removed Python 3.6 support


Web Application
~~~~~~~~~~~~~~~

- Allow local developers to bypass ``auth.mast`` authentication
- Added cosmic ray monitor, unit test code, and relevant database files
- Removed unsupported options including image anomalies, unlooked images and monitors that haven't been implemented
- Improved loading times for web app archive pages by generating a representative thumbnail with ``generate_proposal_thumbnail.py``, using ``astroquery.Mast`` rather than scraping filesystem, adding optional checks that file paths exist
- Implemented JWQL Dashboard View

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Updated the call to the JWST pipeline RSCD step
- Added GitHub Actions


Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Improved loading times of readnoise monitor webpage
- Fixed broken bokeh CDN links

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Dark monitor exits gracefully when there are not enough files in the filesystem
- Fixed filename parsing for WFS&C and AMI products
- Adjusted generation of preview images such that images are created for all file types
- Update ops naming convention in log directory



0.25.0 (2020-12-31)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added project citation information to ``README``, along with a Zenodo badge
- Added API Documentation for ``bokeh`` templating software

Web Application
~~~~~~~~~~~~~~~

- Reorganized and made aesthetic improvements to instrument landing pages to be more user-friendly
- Enabled more dynamic search options and aesthetic improvements for anomaly query webpage
- Added web app view for displaying a particular table of the ``jwqldb`` database
- Added webpage for displaying Bias Monitor results with ``bokeh`` plots

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Changed ``utils.credentials.py`` to always authenticate a MAST user with a user-identified token in the ``config.json`` file, instead of using a cached token, which was sometimes causes errors
- Updated software to support the latest versions of ``django`` and ``bokeh``
- Removed ``affected_tables`` column of ``monitor`` database table, as it stored redundant information
- Updated the Readnoise Monitor to work for all JWST instruments


Bug Fixes
---------


Web Application
~~~~~~~~~~~~~~~

- Fixed bug in Readnoise Monitor webpage that was causing the web app and ``jwql`` database to hang

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed bug that was causing the ``test_amplifier_info()`` test in ``test_instrument_properties.py`` to fail; truth values were updated to reflect a change in the format of the returned dictionaries from the ``amplifier_info()`` function
- Fixed bug in ``get_header_info()`` that was causing ``test_data_containers.py`` to fail; the function expected the filename without the FITS extension, and the returned header info is in a dictionary (not a string)
- Fixed bug in ``test_utils.py``, and changed ``utils.py`` to make it robust in matching upper and lowercase detector names
- Updated ``utils.instrument_properties`` fix MIRI amplifier bounds calculation when omitting reference pixels


0.24.0 (2020-10-20)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added API documentation for Bias, Bad Pixel, and Readnoise Monitors

Web Application
~~~~~~~~~~~~~~~

- Added webpage that describes how to use the JWQL web app API
- Added webpage that enables a user to query the ``jwqldb`` database contents
- Enabled more search options and aesthetic improvements for anomaly query webpage
- Added webpage for displaying Readnoise Monitor results with ``bokeh`` plots
- Added webpage for displaying Bad Pixel Monitor results with ``bokeh`` plots

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Added support for Python versions 3.7 and 3.8
- Added unit tests for Readnoise Monitor
- Added unit tests for Bias Monitor
- Added unit tests for Bad Pixel Monitor
- Added unit tests for ``bokeh`` templating library


Bug Fixes
---------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Updated broken links to JWST instrument JDox pages

Web Application
~~~~~~~~~~~~~~~

- Fixed various issues that was cuasing authentication through ``auth.mast`` to fail

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed bug that was causing Dark Monitor to crash on recently added apertures from ``pysiaf``
- Fixed several bugs in ``bokeh`` templating library
- Fixed bug that was causing unit tests for ``permissions.py`` to fail
- Fixed bug that was causing ``most_recent_search`` function in Dark Monitor to fail


0.23.0 (2020-07-01)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The ``jwql_web_app`` PowerPoint presentation has been updated
- The bokeh templating software now has full API documentation
- Updated ``README`` and About webpage to reflect changes to development team members

Web Application
~~~~~~~~~~~~~~~

- Added webpage to view FITS headers of each extension for a given dataset
- Added webpage for displaying Dark Monitor results with ``bokeh`` plots
- Added webpage for viewing contents of a given JWQL database table
- Added webpage for querying and displaying anomaly results
- Added slider bar for easily navigating through integrations in preview image display
- The list of anomalies one can flag in a preview image is now instrument specific


``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- The ``jwql-3.6`` conda environment now uses the ``astroconda`` channel instead of ``astroconda-dev``
- Added Bias Monitor module, which currently monitors the bias levels for NIRCam
- Added Readnoise Monitor module, which monitors readnoise for all instruments except FGS
- Added Bad Pixel Monitor module, which tracks bad pixels for all instruments
- Cron job logs now include a print out of the complete ``conda`` environment being used


Bug Fixes
---------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Fixed broken link to ``numpydoc`` docstring convention in Style Guide


0.22.0 (2019-08-26)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added slides from July 2019 TIPS presentation to ``presentations/`` directory


``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Updated dark monitor to support all five JWST instruments, instead of only NIRCam
- Changed the ``jwql-3.5`` and ``jwql-3.6`` conda environments to be more simple and to work on Linux distributions
- Added library code for creating instrument monitoring ``bokeh`` plots with new ``bokeh`` templating software


Bug Fixes
---------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Fixed various bugs that were causing the ``sphinx`` API documentation to crash on ReadTheDocs


0.21.0 (2019-07-23)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Updated ``README`` to include instructions on package installation via ``pip``.

Web Application
~~~~~~~~~~~~~~~

- Updated all webpages to conform to Web Application Accessibility Guidelines.
- Upgraded to ``django`` version 2.2.
- ``bokeh`` is now imported in ``base`` template so that the version being used is consistent across all HTML templates.

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- The ``jwql`` package is now available on PyPI (https://pypi.org/project/jwql/) and installable via ``pip``.
- Updated Jenkins configuration file to include in-line comments and descriptions.
- Added ``utils`` function to validate the ``config.json`` file during import of ``jwql`` package.
- Added support for monitoring contents of the ``jwql`` central storage area in the filesystem monitor.


Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Fixed position error of JWQL version display in footer.

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed spelling error in dark monitor database column names.
- Fixed dark monitor to avoid processing files that are not in the filesystem.


0.20.0 (2019-06-05)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Updated the notebook exemplifying how to perform an engineering database (EDB) telemetry query.
- Updated the README for the ``style_guide`` directory.

Web Application
~~~~~~~~~~~~~~~

- Added form on preview image pages to allow users to submit image anomalies.
- Added buttons for users to download the results of EDB telemetry queries as CSV files.
- Enabled users to search for or navigate to program numbers without requiring leading zeros (i.e. "756" is now treated equivalently to "00756").
- Enabled authentication for EDB queries via the web login (rather than requiring authentication information to be present in the configuration file).
- Added custom 404 pages.
- Added adaptive redirect feature so that users are not sent back to the homepage after login.
- Added more descriptive errors if a user tries to run the web application without filling out the proper fields in the configuration file.

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Replaced all EDB interface code within ``jwql`` with the new ``jwedb`` `package<https://github.com/spacetelescope/jwst-dms-edb>`_.
- Fully incorporated Python 3.5 testing into the Jenkins test suite.

Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Fixed bug in which dashboard page would throw an error.
- Fixed incorrect dashboard axis labels.


0.19.0 (2019-04-19)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added guidelines to the style guide for logging the execution of instrument monitors
- Added example usage of logging in the ``example.py`` module

Web Application
~~~~~~~~~~~~~~~

- Modified various web app views to enable faster loading times
- Modified archive and preview image views to only display data for an authenticated user
- Added views for MIRI and NIRSpec Data Trending Monitors, which monitors the behavior of select MIRI and NIRSpec Engineering Database mnemonics over time

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Added Dark Monitor module, which monitors the dark current and hot pixel populations for each JWST instrument
- Added software for producing MIRI and NIRSpec Data Trending Monitors (described above)
- Modified ``generate_preview_images`` module to support the creation of preview images for stage 3 data products
- Refactored ``monitor_filesystem`` to utilize PostgreSQL database tables to store archive filesystem statistics
- Configured ``codecov`` for the project.  The project homepage can be found at https://codecov.io/gh/spacetelescope/jwql
- Modified ``logging_functions`` module to enable dev, test, and production logging environments
- Added convenience decorator to ``logging_functions`` module to time the execution of a function or method
- Modified ``monitor_cron_jobs`` module to make use of updated ``logging_functions``

Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Fixed API views to only return the basenames of file paths, instead of full directory names

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed ``logging_functions`` module to properly parse new format of ``INSTALL_REQUIRES`` dependency in ``setup.py`` for logging system dependencies and their versions
- Fixed ``Jenkinsfile`` to not allow for one failed unit test in Jenkins builds


0.18.0 (2019-03-14)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Added instructions in ``README`` that details how to supply the required ``config.json`` configuration file
- Updated installation instructions in ``README`` to be more comprehensive
- Updated API docs for JavaScript functions in web app

Web Application
~~~~~~~~~~~~~~~

- Added a webpage for interacting with the JWST Engineering Database (EDB), including searching for available mneumonics and plotting mneumonic time series data
- Added ``context_processors`` module that provides functions that define context inherent to all views
- Added display of package version in footer
- Moved all JavaScript functions in HTML templates into the ``jwql.js`` module
- Modified links to external webpages to open in new tab

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Added ``__version__`` package attribute
- Updated ``install_requires`` in ``setup.py`` to adhere to best practices
- Added template branch and supporting documentation for how to contribute a new webpage in the ``jwql`` web application
- Added custom error message if required ``config.json`` configuration file is missing
- Updated ``database_interface`` module to dynamically create tables to store instrument monitoring data from user-supplied table definition files
- Added Jupyter notebook that describes how to integrate ``auth.mast`` service in a ``djang``` web application
- Updated ``utils.filename_parser`` function to handle stage 2C and guider filenames
- Updated ``utils.filename_parser`` function to always provide an ``instrument`` key, as needed by several webpages within the web app
- Added separate file suffix type lists in ``constants.py`` module
- Added ``reset_database`` module that resets and rebuilds a database provided by the ``connection_string`` key in the ``config.json`` configuration file
- Added ``pytest`` results file in order to fix Jenkins CI builds

Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Fixed navbar padding
- Fixed broken instrument logos on homepage

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~

- Fixed ``monitor_mast`` module to actually be command-line executable


0.17.0 (2019-02-05)
===================

New Features
------------

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a wiki page for how to do a software release
- Added a wiki page with a checklist for contributors and reviewers of pull requests
- Added a wiki page about how the web server is configured
- Defined specific variable value/type standards for JWST instruments and program/proposal identifiers in the Style Guide

Web Application
~~~~~~~~~~~~~~~
- Added authentication to all pages using the ``auth.mast`` service provided by the Archive Services Branch
- Implemented AJAX requests to load the ``thumbnails.html`` and ``archive.html`` pages
- Used regular expressions to restrict URLs to specific patterns
- Added a loading widget while thumbnails compile

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~
- Added interface with the JWST DMS engineering database: ``utils.engineering_database``
- Expanded ``utils.filename_parser`` to handle time series and DMS stage 3 file names
- Consolidated important constants in new ``utils.constants`` module

Bug Fixes
---------

Web Application
~~~~~~~~~~~~~~~

- Updated permissions in ``nginx`` settings to fix bug where dashboard page would not display


0.16.0 (2018-12-17)
===================

This is the first release of the new release procedures of ``jwql``.  The development team is now developing in release-driven sprints, so future releases will be less frequent, but with more changes

Changes since the ``0.15.3`` release include:

New Features
------------

``jwql`` ``conda`` Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Updated ``bokeh`` to version 1.0
- Updated ``django`` to fix security issues
- Added ``pandas`` as a dependency

Project & API Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~~~
- Added a project description in the API docs
- Added web app API docs

Web Application
~~~~~~~~~~~~~~~
- Made changes to the code to get it working on the web development server
- Added several REST API services
- Added API documentation button to the navbar and anded link to API documentation in the ``about`` page
- Added instrument-specific documentation button to the instrument landing pages
- Replaced ``monitor_mast`` donut charts with bar charts
- Removed dashboard and database query buttons from homepage
- Added form to homepage that allows user to view preview images for a given rootname or proposal number
- Changed URL patters to allow for separation between nominal web app and REST API service
- Added ``monitor_cron_jobs`` monitor that builds and renders a table displaying ``cron`` job execution status

``jwql`` Repository
~~~~~~~~~~~~~~~~~~~
- Added badges to the ``README``
- Configured ``pyup`` service for the ``jwql`` repository via ``.pyup.yml`` file
- Added a separate ``requirement.txt`` file to keep track of requirements needed by ReadTheDocs and the ``pyup`` service
- Added various ``jwql`` presentations in separate ``presentations/`` directory

Other Changes
~~~~~~~~~~~~~
- Changed ``logging_functions.py`` to be more conservative on when to write log files to the production area
- Added ``plotting.py`` module (and supporting unit tests), which stores various plotting-related functions


0.15.3 (2018-09-18)
===================

- Added ``.readthedocs.yml``, which configures the ``jwql`` project documentation with ReadtheDocs


0.15.2 (2018-09-11)
===================

- Reorganized the ``jwql`` repository into a structure that better incorporates instrument-specific monitoring scripts


0.15.1 (2018-09-10)
===================

- Added ``.pep8speaks.yml``, which configures the ``pep8speaks`` service for the ``jwql`` repository


0.15.0 (2018-08-29)
===================

- Added ``monitor_template.py``, which serves as a template with examples for instrument-specific monitors that we may write one day


0.14.1 (2018-08-28)
===================

- Moved all of the ``jwql`` web app code into the ``jwql`` package proper


0.14.0 (2018-08-27)
===================

- Added a feature to ``generate_preview_images`` and ``preview_image`` that creates mosaicked preview images for NIRCam when applicable


0.13.1 (2018-08-24)
===================

- Changed the way ``monitor_mast`` and ``monitor_filesystem`` ``bokeh`` plots are saved and displayed in the web application, from using ``html`` to using embedded ``boken`` components
- Added some logging to ``monitor_filesystem`` and ``monitor_mast``


0.13.0 (2018-08-23)
===================

- Added ``database_interface.py`` and supporting documentation; this module enables the creation and maintenance of database tables in the ``jwqldb`` ``postgresql`` database
- Added the ``anomalies`` table in ``database_interface.py``


0.12.2 (2018-08-22)
===================

- Fixed some minor formatting issues with the ``sphinx`` docs for ``monitor_filesystem`` and ``monitor_mast``


0.12.1 (2018-08-20)
===================

- Added ``ipython`` to the ``jwql`` environment


0.12.0 (2018-08-16)
===================

- Added a prototype of the ``django`` web application via the ``website/`` directory


0.11.6 (2018-07-31)
===================

- Added the ``jwql`` code of conduct


0.11.5 (2018-07-24)
===================

- Changes to ``monitor_filesystem``, namely adding ``sphinx`` docs and adding a plot that shows the total file sizes and counts broken down by instrument


0.11.4 (2018-07-10)
===================

- Renamed instances of ``dbmonitor`` to ``monitor_mast`` to be more consistent with ``monitor_filesystem``


0.11.3 (2018-07-10)
===================

- Removed the ``_static`` file from the ``html_static_paths`` parameters in the ``conf.py`` of the ``sphinx`` docs to avoid unnecessary warnings when trying to build the ``sphinx`` docs


0.11.2 (2018-06-22)
===================

- Changed the default value for the ``verbose`` option from ``True`` to ``False`` in ``permissions.set_permissions``


0.11.1 (2018-06-22)
===================

- Added unit tests for ``preview_images.py``


0.11.0 (2018-06-22)
===================

- Added ``logging.logging_functions.py``, which provides a way to log the execution of modules


0.10.4 (2018-06-22)
===================

- Added an update to the version of ``django`` for use by the web application


0.10.3 (2018-06-22)
===================

- Fixed the ``Jenkinsfile`` to use ``name`` for ``build_mode``


0.10.2 (2018-06-14)
===================

- Changed ``setup.py`` to adhere to ``PEP-8`` standards


0.10.1 (2018-06-02)
===================

- Added ``sphinx`` API documentation for ``db_monitor.py`` and ``test_db_monitor.py``


0.10.0 (2018-05-31)
===================

- Added ``monitor_filesystem.py``, which provides stats files and ``bokeh`` plots that describe the content of the MAST data cache


0.9.0 (2018-05-31)
==================

- Added ``db_monitor.py`` and supporting tests; this module creates ``bokeh`` plots and returns tables to describe the contents of the MAST database


0.8.0 (2018-05-15)
==================

- Added the ``generate_preview_images`` module, which generates preview images and thumbnails for all files in the filesystem


0.7.2 (2018-05-14)
==================

- Added a new ``jupyter`` notebook that identifies keywords that are in the MAST skipped list and also exist in the headers of multiple extensions


0.7.1 (2018-05-04)
==================

- Changed the structure of the API docs, separating the modules into their own ``.rst`` files


0.7.0 (2018-04-19)
==================

- Added a ``filename_parser`` function in a ``utils.py`` module that returns a dictionary of elements contained in a given JWST filename


0.6.0 (2018-04-17)
==================

- Added API documentation build using ``sphinx``; the documentation is located in the ``docs`` directory


0.5.0 (2018-04-02)
==================

- Added ``permissions.py`` and ``test_permissions.py``, which are modules to help manage file and directory permissions


0.4.1 (2018-03-30)
==================

- Changed the ``README`` to describe how to clone the ``jwql`` repository using two-factor authentication/``sftp``


0.4.0 (2018-03-28)
==================

- Added ``preview_image.py``, a module for generating a preview image for a given JWST observation


0.3.0 (2018-03-28)
==================

- Added package structure to the ``jwql`` repository, making it an installable package


0.2.0 (2018-02-20)
==================

- Added a ``README`` file that describes how to install and contribute to the ``jwql`` repository
- Added an ``environment.yml`` file that contains the ``jwqldev`` environment


0.1.0 (2018-01-31)
==================

- Added the ``jwql`` style guide.
