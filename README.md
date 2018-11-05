<p align="center">
  <img src="https://i.imgur.com/MwnjFVM.png" width="400"/>
</p>

# The JWST Quicklook Application (`JWQL`)

[![PyPI - License](https://img.shields.io/pypi/l/Django.svg)](https://github.com/spacetelescope/jwql/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6-blue.svg)](https://www.python.org/)
[![Build Status](https://ssbjenkins.stsci.edu/job/STScI/job/jwql/job/master/badge/icon)](https://ssbjenkins.stsci.edu/job/STScI/job/jwql/job/master/)
[![Documentation Status](https://readthedocs.org/projects/jwql/badge/?version=latest)](https://jwql.readthedocs.io/en/latest/?badge=latest)
[![STScI](https://img.shields.io/badge/powered%20by-STScI-blue.svg?colorA=707170&colorB=3e8ddd&style=flat)](http://www.stsci.edu)


The JWST Quicklook Application (`JWQL`) is a database-driven web application and automation framework for use by the JWST instrument teams to monitor and trend the health, stability, and performance of the JWST instruments.  The system is comprised of the following:
1. A network file system that stores all uncalibrated and calibrated data products on disk in a centrally-located area, accessible to instrument team members (MAST data cache)
2. A relational database that stores observational metadata allowing for data discovery via relational queries (MAST database API).
3. A software library that provides tools to support an automation framework in which to build automated instrument monitoring routines.
4. A web application that allows users to visually inspect new and archival JWST data as well as instrument-specific monitoring and performance results.

The `jwql` application is currently under heavy development.  The `1.0` release is expected in 2019.

## Prerequisites

It is highly suggested that contributors have a working installation of `anaconda` or `miniconda` for Python 3.6.  Downloads and installation instructions are  available here:

- [Miniconda](https://conda.io/miniconda.html)
- [Anaconda](https://www.continuum.io/downloads)

Requirements for contributing to the `jwql` package will be included in the `jwql` `conda` environment, which is included in our installation instructions below. Further package requirements will be provided for `jwql` by a `setup.py` script included in the repository.

## Package Installation

You first need to install the current version of `jwql`. The simplest way to do this is to go to the directory you want your copy of the repository to be in and clone the repoistory there. Once you are in the directory you can do the following:

```
git clone https://github.com/spacetelescope/jwql.git
cd jwql
python setup.py develop
```

or, if you would rather use `SSH` instead of `https`, type
```
git clone git@github.com:spacetelescope/jwql.git
cd jwql
python setup.py develop
```
instead, and then proceed as stated.

## Environment Installation

Following the download of the `jwql` package, contributors can then install the `jwql` `conda` environment via the `environment.yml` file, which contains all of the dependencies for the project.  First, one should ensure that their version of `conda` is up to date:

```
conda update conda
```

Next, one should activate the `base` environment:

```
source activate base
```

Lastly, one can create the `jwql` environment via the `environment.yml` file:

```
conda env create -f environment.yml
```


## Contributing

There are two current pages to review before you begin contributing to the `jwql` development. The first is our [style guide](https://github.com/spacetelescope/jwql/blob/master/style_guide/style_guide.md) and the second is our [suggested git workflow page](https://github.com/spacetelescope/jwql/wiki/git-&-GitHub-workflow-for-contributing), which contains an in-depth explanation of the workflow.

The following is a bare bones example of a best work flow for contributing to the project:

1. Create a fork off of the `spacetelescope` `jwql` repository.
2. Make a local clone of your fork.
3. Ensure your personal fork is pointing `upstream` properly.
4. Create a branch on that personal fork.
5. Make your software changes.
6. Push that branch to your personal GitHub repository (i.e. `origin`).
7. On the `spacetelescope` `jwql` repository, create a pull request that merges the branch into `spacetelescope:master`.
8. Assign a reviewer from the team for the pull request.
9. Iterate with the reviewer over any needed changes until the reviewer accepts and merges your branch.
10. Delete your local copy of your branch.


## Code of Conduct

Users and contributors to the `jwql` repository should adhere to the [Code of Conduct](https://github.com/spacetelescope/jwql/blob/master/CODE_OF_CONDUCT.md).  Any issues or violations pertaining to the Code of Conduct should be brought to the attention of a `jwql` team member or to `jwql@stsci.edu`.

## Questions

Any questions about the `jwql` project or its software can be directed to `jwql@stsci.edu`.


## Current Development Team
- Matthew Bourque (INS) [@bourque](https://github.com/bourque)
- Lauren Chambers (INS) [@laurenmarietta](https://github.com/laurenmarietta)
- Misty Cracraft (INS) [@cracraft](https://github.com/cracraft)
- Joe Filippazzo (INS) [@hover2pi](https://github.com/hover2pi)
- Bryan Hilbert (INS) [@bilhbert4](https://github.com/bhilbert4)
- Graham Kanarek (INS) [@gkanarek](https://github.com/gkanarek)
- Catherine Martlin (INS) [@catherine-martlin](https://github.com/catherine-martlin)
- Sara Ogaz (OED) [@SaOgaz](https://github.com/SaOgaz)
- Johannes Sahlmann (INS) [@Johannes-Sahlmann](https://github.com/johannes-sahlmann)

## Acknowledgments:
- Faith Abney (OED)
- Anastasia Alexov (OED)
- Sara Anderson (OED)
- Tracy Beck (INS)
- Francesca Boffi (INS) [@frboffi](https://github.com/frboffi)
- Clara Brasseur (OED) [@ceb8](https://github.com/ceb8)
- Matthew Burger (OED)
- Steven Crawford (OED) [@stscicrawford](https://github.com/stscicrawford)
- James Davies (OED) [@jdavies-st](https://github.com/jdavies-st)
- Rosa Diaz (INS) [@rizeladiaz](https://github.com/rizeladiaz)
- Van Dixon (INS)
- Tom Donaldson (OED) [@tomdonaldson](https://github.com/tomdonaldson)
- Mike Fox (DSMO) [@mfox22](https://github.com/mfox22)
- Scott Friedman (INS)
- Alex Fullerton (INS) [@awfullerton](https://github.com/awfullerton)
- Lisa Gardner (OED)
- Vera Gibbs (ITSD)
- Catherine Gosmeyer (INS) [@cgosmeyer](https://github.com/cgosmeyer)
- Phil Grant (ITSD)
- Dean Hines (INS)
- Sherie Holfeltz (INS) [@stholfeltz](https://github.com/stholfeltz)
- Joe Hunkeler (OED) [@jhunkeler](https://github.com/jhunkeler)
- Catherine Kaleida (OED)
- Mark Kyprianou (OED) [@mkyp](https://github.com/mkyp)
- Karen Levay (OED)
- Crystal Mannfolk (OED) [@cmannfolk](https://github.com/cmannfolk)
- Greg Masci (ITSD)
- Margaret Meixner (INS)
- Prem Mishra (ITSD)
- Don Mueller (ITSD)
- Maria Antonia Nieto-Santisteban (OED)
- Joe Pollizzi (JWSTMO)
- Lee Quick (OED)
- Anupinder Rai (ITSD)
- Matt Rendina (OED) [@rendinam](https://github.com/rendinam)
- Massimo Robberto (INS) [@mrobberto](https://github.com/mrobberto)
- Mary Romelfanger (OED)
- Bernie Shiao (OED)
- Matthew Sienkiewicz (ITSD)
- Arfon Smith (DSMO) [@arfon](https://github.com/arfon)
- Linda Smith (INS)
- Patrick Taylor (ITSD)
- Dave Unger (ITSD)
- Jeff Valenti (JWSTMO) [@JeffValenti](https://github.com/JeffValenti)
- Thomas Walker (ITSD)
- Geoff Wallace (OED)
- Lara Wilkinson (OPO)
- Alex Yermolaev (ITSD)
- Joe Zahn (ITSD)
