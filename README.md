<p align="center">
  <img src="logos/jwql_logo_full_transparent.png" width="400"/>
</p>

# The JWST Quicklook Application (`JWQL`)

[![Current Release](https://img.shields.io/github/release/spacetelescope/jwql.svg)](https://github.com/spacetelescope/jwql/releases/latest/)
[![PyPI - License](https://img.shields.io/pypi/l/Django.svg)](https://github.com/spacetelescope/jwql/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.7-blue.svg)](https://www.python.org/)
[![Build Status](https://github.com/spacetelescope/jwql/workflows/JWQL%20CI/badge.svg)](https://github.com/spacetelescope/jwql/actions)
[![Documentation Status](https://readthedocs.org/projects/jwql/badge/?version=latest)](https://jwql.readthedocs.io/en/latest/?badge=latest)
[![STScI](https://img.shields.io/badge/powered%20by-STScI-blue.svg?colorA=707170&colorB=3e8ddd&style=flat)](http://www.stsci.edu)
[![DOI](https://zenodo.org/badge/109727729.svg)](https://zenodo.org/badge/latestdoi/109727729)
[![codecov](https://codecov.io/gh/spacetelescope/jwql/branch/develop/graph/badge.svg)](https://codecov.io/gh/spacetelescope/jwql)


The JWST Quicklook Application (`JWQL`) is a database-driven web application and automation framework for use by the JWST instrument teams to monitor and trend the health, stability, and performance of the JWST instruments.  The system is comprised of the following:
1. A network file system that stores all uncalibrated and calibrated data products on disk in a centrally-located area, accessible to instrument team members (i.e. the MAST data cache)
2. A relational database that stores observational metadata allowing for data discovery via relational queries (MAST database API).
3. A software library that provides tools to support an automation framework in which to build automated instrument monitoring routines.
4. A web application that allows users to visually inspect new and archival JWST data as well as instrument-specific monitoring and performance results.

Official API documentation can be found on [ReadTheDocs](https://jwql.readthedocs.io)

The `jwql` application is available at [https://jwql.stsci.edu](https://jwql.stsci.edu).  Please note that the application is currently restricted to specific JWST instrument team members.

## Installation for Users

To install `jwql`, simply use `pip`:

```
pip install jwql
```

The section below describes a more detailed installation for users that wish to contribute to the `jwql` repository.

## Installation for Contributors

Getting `jwql` up and running on your own computer requires four steps, detailed below:
1. Cloning the GitHub repository
2. Installing the `conda`environment
3. Installing the python package
4. Setting up the configuration file

### Prerequisites

It is highly suggested that contributors have a working installation of `anaconda` or `miniconda` for Python 3.8.  Downloads and installation instructions are  available here:

- [Miniconda](https://conda.io/miniconda.html)
- [Anaconda](https://www.continuum.io/downloads)

Requirements for contributing to the `jwql` package will be included in the `jwql` `conda` environment, which is included in our installation instructions below. Further package requirements will be provided for `jwql` by a `setup.py` script included in the repository.

### Clone the `jwql` repo

You first need to clone the current version of `jwql`. The simplest way to do this is to go to the directory you want your copy of the repository to be in and clone the repository there. Once you are in the directory you can do the following:

```
git clone https://github.com/spacetelescope/jwql.git
cd jwql
```

or, if you would rather use `SSH` instead of `https`, type
```
git clone git@github.com:spacetelescope/jwql.git
cd jwql
```
instead, and then proceed as stated.

### Environment Installation

Following the download of the `jwql` repository, contributors can then install the `jwql` `conda` environment via the environment yaml file, which contains all of the dependencies for the project. First, if necessary, [install `conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html). Next, ensure that your version of `conda` is up to date:

```
conda update conda
```

Next, activate the `base` or `root` environment (depending on your version of `conda`):

```
source activate base/root
```

**Note:** If you have added a step activating conda to your default terminal/shell (e.g. the `.bashrc`, `.zshrc`, or `.profile` file) then you don't need to do the above step.

Lastly, create the `jwql` environment via one of the `environment.yml` files (currently `environment_python_3_8.yml`, for python 3.8, and `environment_python_3.9.yml`, for python 3.9, are supported by `jwql`):

```
conda env create -f environment_python_3_8.yml
```

or

```
conda env create -f environment_python_3_9.yml
```

### Configuration File

Much of the `jwql` software depends on the existence of a `config.json` file within the `jwql` directory.  This file contains data that may be unique to users and/or contain sensitive information.  Please see the [Config File wiki page](https://github.com/spacetelescope/jwql/wiki/Config-file) for instructions on how to provide this file.


## Citation

If you use `JWQL` for work/research presented in a publication (whether directly,
or as a dependency to another package), we recommend and encourage the following acknowledgment:

```
  This research made use of the open source Python package 'jwql' (Bourque et al, 2020).
```

where (Bourque et al, 2020) is a citation of the Zenodo record available using the DOI badge above. By using the `Export` box in the lower right corner of the Zenodo page, you can export the citation in the format most convenient for you.


## Software Contributions

There are two current pages to review before you begin contributing to the `jwql` development. The first is our [style guide](https://github.com/spacetelescope/jwql/blob/main/style_guide/README.md) and the second is our [suggested git workflow page](https://github.com/spacetelescope/jwql/wiki/git-&-GitHub-workflow-for-contributing), which contains an in-depth explanation of the workflow.

Contributors are also encouraged to check out the [Checklist for Contributors Guide](https://github.com/spacetelescope/jwql/wiki/Checklist-for-Contributors-and-Reviewers-of-Pull-Requests) to ensure the pull request contains all of the necessary changes.

The following is a bare-bones example of a best work flow for contributing to the project:

1. Create a fork off of the `spacetelescope` `jwql` repository.
2. Make a local clone of your fork.
3. Ensure your personal fork is [pointing `upstream` properly](https://docs.github.com/en/free-pro-team@latest/github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork).
4. Create a branch on that personal fork.
5. Make your software changes.
6. Push that branch to your personal GitHub repository (i.e. `origin`).
7. On the `spacetelescope` `jwql` repository, create a pull request that merges the branch into `spacetelescope:develop`.
8. Assign a reviewer from the team for the pull request.
9. Iterate with the reviewer over any needed changes until the reviewer accepts and merges your branch.
10. Delete your local copy of your branch.


## Issue Reporting / Feature Requests

Users who wish to report an issue or request a new feature may do so through the following channels:

1. Submit a new issue on GitHub (preferred method): https://github.com/spacetelescope/jwql/issues
2. Submit a new ticket on Jira: https://jira.stsci.edu/projects/JWQL/


## Code of Conduct

Users and contributors to the `jwql` repository should adhere to the [Code of Conduct](https://github.com/spacetelescope/jwql/blob/main/CODE_OF_CONDUCT.md).  Any issues or violations pertaining to the Code of Conduct should be brought to the attention of a `jwql` team member or to `jwql@stsci.edu`.

## Questions

Any questions about the `jwql` project or its software can be directed to `jwql@stsci.edu`.


## Current Development Team
- Bryan Hilbert (Project Manager, INS) [@bilhbert4](https://github.com/bhilbert4)
- Mees Fix (Technical Lead, INS) [@mfixstsci](https://github.com/mfixstsci)
- Misty Cracraft (INS) [@cracraft](https://github.com/cracraft)
- Mike Engesser (INS) [@mengesser](https://github.com/mengesser)
- Shannon Osborne (INS) [@shanosborne](https://github.com/shanosborne)
- Maria Pena-Guerrero [@penaguerrero](https://github.com/penaguerrero)
- Ben Sunnquist (INS) [@bsunnquist](https://github.com/bsunnquist)
- Brian York (INS) [@york-stsci](https://github.com/york-stsci)

## Past Development Team Members
- Matthew Bourque (INS) [@bourque](https://github.com/bourque)
- Lauren Chambers (INS) [@laurenmarietta](https://github.com/laurenmarietta)
- Joe Filippazzo (INS) [@hover2pi](https://github.com/hover2pi)
- Graham Kanarek (INS) [@gkanarek](https://github.com/gkanarek)
- Teagan King (INS) [@tnking97](https://github.com/tnking97)
- Sara Ogaz (DMD) [@SaOgaz](https://github.com/SaOgaz)
- Catherine Martlin (INS) [@catherine-martlin](https://github.com/catherine-martlin)
- Johannes Sahlmann (INS) [@Johannes-Sahlmann](https://github.com/johannes-sahlmann)


## Acknowledgments:
- Faith Abney (DMD)
- Joshua Alexander (DMD) [@obviousrebel](https://github.com/obviousrebel)
- Anastasia Alexov (DMD)
- Sara Anderson (DMD)
- Tracy Beck (INS)
- Francesca Boffi (INS) [@frboffi](https://github.com/frboffi)
- Clara Brasseur (DMD) [@ceb8](https://github.com/ceb8)
- Matthew Burger (DMD)
- Steven Crawford (DMD) [@stscicrawford](https://github.com/stscicrawford)
- James Davies (DMD) [@jdavies-st](https://github.com/jdavies-st)
- Rosa Diaz (INS) [@rizeladiaz](https://github.com/rizeladiaz)
- Van Dixon (INS)
- Larry Doering (ITSD)
- Tom Donaldson (DMD) [@tomdonaldson](https://github.com/tomdonaldson)
- Kim DuPrie (DMD)
- Jonathan Eisenhamer (DMD) [@stscieisenhamer](https://github.com/stscieisenhamer)
- Ben Falk (DMD) [@falkben](https://github.com/falkben)
- Ann Feild (OPO)
- Mike Fox (DSMO) [@mfox22](https://github.com/mfox22)
- Scott Friedman (INS)
- Alex Fullerton (INS) [@awfullerton](https://github.com/awfullerton)
- Macarena Garcia Marin (INS)
- Lisa Gardner (DMD)
- Vera Gibbs (ITSD)
- Catherine Gosmeyer (INS) [@cgosmeyer](https://github.com/cgosmeyer)
- Phil Grant (ITSD)
- Dean Hines (INS)
- Sherie Holfeltz (INS) [@stholfeltz](https://github.com/stholfeltz)
- Joe Hunkeler (DMD) [@jhunkeler](https://github.com/jhunkeler)
- Catherine Kaleida (DMD) [@ckaleida](https://github.com/ckaleida)
- Deborah Kenny (DMD)
- Jenn Kotler (DMD) [@jenneh](https://github.com/jenneh)
- Daniel Kühbacher (Goddard) [@DanielKuebi](https://github.com/DanielKuebi)
- Mark Kyprianou (DMD) [@mkyp](https://github.com/mkyp)
- Stephanie La Massa (INS)
- Matthew Lallo (INS)
- Karen Levay (DMD)
- Crystal Mannfolk (SCOPE) [@cmannfolk](https://github.com/cmannfolk)
- Greg Masci (ITSD)
- Jacob Matuskey (DMD) [@jmatuskey](https://github.com/jmatuskey)
- Margaret Meixner (INS)
- Christain Mesh (DMD) [@cam72cam](https://github.com/cam72cam)
- Prem Mishra (ITSD)
- Don Mueller (ITSD)
- Maria Antonia Nieto-Santisteban (SEITO)
- Brian O'Sullivan (INS)
- Joe Pollizzi (JWSTMO)
- Lee Quick (DMD)
- Anupinder Rai (ITSD)
- Matt Rendina (DMD) [@rendinam](https://github.com/rendinam)
- Massimo Robberto (INS) [@mrobberto](https://github.com/mrobberto)
- Mary Romelfanger (DMD)
- Elena Sabbi (INS)
- Bernie Shiao (DMD)
- Matthew Sienkiewicz (ITSD)
- Arfon Smith (DSMO) [@arfon](https://github.com/arfon)
- Linda Smith (INS)
- Patrick Taylor (ITSD)
- Dave Unger (ITSD)
- Jeff Valenti (JWSTMO) [@JeffValenti](https://github.com/JeffValenti)
- Jeff Wagner (ITSD)
- Thomas Walker (ITSD)
- Geoff Wallace (DMD)
- Lara Wilkinson (OPO)
- Alex Yermolaev (ITSD) [@alexyermolaev](https://github.com/alexyermolaev)
- Joe Zahn (ITSD)
