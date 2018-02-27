<p align="center">
  <img src="https://i.imgur.com/MwnjFVM.png" width="400"/>
</p>

# The James Webb Quicklook Application (`JWQL`)

The James Webb Quicklook Application (`JWQL`) is a database-driven web application and software repository for use by the JWST instrument teams.  The system is comprised of the following:
1. A network file system that stores all uncalibrated and calibrated data products on disk in a centrally-located area, accessible to instrument team members.
2. A relational database that stores observational metadata allowing for data discovery via relational queries.
3. A software library that provides an API to the filesystem and database and serves as a platform on which to build automated instrument calibration and monitoring tasks.
4. A web application that allows users to visually inspect new and archival JWST data as well as instrument-specific monitoring and calibration results.

## Prerequisites

It is highly suggested that users have a working installation of `anaconda` or `miniconda` for Python 3.6.  Downloads and installation instructions are  available here:

- [Miniconda](https://conda.io/miniconda.html)
- [Anaconda](https://www.continuum.io/downloads)

Requirements for contributing to the `jwql` package will be included in the `jwqldev` `conda` environment, which is included in our installation instructions below. Further package requirements will be provided for `jwql` by a `setup.py` script included in the repository.

## Package Installation

You first need to install the current version of `jwql`. The simplest way to do this is to go to the directory you want your copy of the repository to be in and clone the repoistory there. Once you are in the directory you can do the following:

```
git clone https://github.com/spacetelescope/jwql.git
cd jwql
python setup.py develop
```

## Environment Installation

Following the download of the `jwql` package, users can then install the `jwqldev` `conda` environment via the `environment.yml` file, which contains all of the dependencies for the project.  First, users should ensure that their version of `conda` is up to date:

```
conda update conda
```

Next, users should activate the `root` environment:

```
source activate root
```

Lastly, users can create the `jwqldev` environment via the `environment.yml` file:

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


## Git Ignore

The `jwql` repository also contains a file named `.gitignore` that indicates specific directories, files or file types that should not be commited to the repository.  Feel free to add additional lines to this file if you want to avoid committing anything.  Some examples may include `.fits` files, `.jpeg` files, or `.ipynb_checkpoints/`.

## Questions

Any questions about the `jwql` project or its software can be directed to `jwql@stsci.edu`.


## Current Development Team
- Matthew Bourque (INS)
- Lauren Chambers (INS)
- Misty Cracraft (INS)
- Joseph Filippazo (INS)
- Bryan Hilbert (INS)
- Graham Kanarek (INS)
- Catherine Martlin (INS)
- Sara Ogaz (OED)
- Johannes Sahlmann (INS)

## Acknowledgments:
- Anastasia Alexov (OED)
- Tracy Beck (INS)
- Francesca Boffi (INS)
- Rosa Diaz (INS)
- Van Dixon (INS)
- Tom Donaldson (OED)
- Michael Fox (DSMO)
- Scott Friedman (INS)
- Alex Fullerton (INS)
- Lisa Gardner (OED)
- Vera Gibbs (ITSD)
- Catherine Gosmeyer (INS)
- Phil Grant (ITSD)
- Dean Hines (INS)
- Sherrie Holfeltz (INS)
- Catherine Kaleida (OED)
- Mark Kyprianou (OED)
- Karen Levay (OED)
- Greg Masci (ITSD)
- Margaret Meixner (INS)
- Don Mueller (ITSD)
- Maria Antonia Nieto-Santisteban (OED)
- Lee Quick (OED)
- Anupinder Rai (ITSD)
- Matt Rendina (OED)
- Massimo Robberto (INS)
- Mary Romelfanger (OED)
- Arfon Smith (DSMO)
- Linda Smith (INS)
- Dave Unger (ITSD)
- Jeff Valenti (INS)
- Joe Zahn (ITSD)
