# The James Webb Quicklook Application 

One Paragraph of project description goes here.

## Getting Started

### Prerequisites

It is highly suggested that users have a working installation of `anaconda` or `miniconda` for Python 3.6.  Downloads and installation instructions are  available here:

- [Miniconda](https://conda.io/miniconda.html)
- [Anaconda](https://www.continuum.io/downloads)

Following your installation of 'anaconda' or 'miniconda' we also require the following packages which you can add to your conda environment: 

git
flake8

Requirements for working in the ``jwql`` repository will be included in the `jwqldev` `conda` environment, which is included in our installation instructions below. Further package requirements will be provided for ``jwql`` by a `setup.py` script included in the git download. 

(Once we have more things we deem as prereqs for using and contributing to our project then we can add them here.) 

### Installation

You first need to install the current version of ``jwql``. The simplest way to do this is to go to the directory you want your version to be in and clone the repoistory there. Once you are in the directory you can do the following: 

```
git clone https://github.com/spacetelescope/jwql.git
```

## Environment Installation

Following the download of the `jwql` codes, users can then install the `jwqldev` `conda` environment via the `environment.yml` file, which contains all of the dependencies for the project:

```
cd jwql
conda env create -f environment.yml
```

We have further in-depth instructions on how to install your environtment at the following project wikipage: https://github.com/spacetelescope/jwql/wiki/Environment-Installation

## Contributing

There are two current pages to review before you begin contributing to the `jwql` development. The first is our [style guide](https://github.com/spacetelescope/jwql/blob/style-guide/style_guide/style_guide.md) and the second is our [suggested git workflow page](https://github.com/spacetelescope/jwql/wiki/git-GitHub-workflow-for-contributing/). 

The following is a bare bones example of a best work flow for contributing to the project. 

The usual roadmap that you will want to follow is to: 
1. Create a fork off of the `jwql` repository.
2. Make a local copy of your fork. 
3. Ensure your personal fork is pointing `upstream` properly. 
4. Create a branch on that personal fork. 
5. Make your software changes. 
6. Push that branch to the GitHub repository. 
7. Create a pull request for this branch. 
8. Assign a reviewr from the team for the pull request. 
9. Iterate with the reviewer over any needed changes until the reviewer accepts and merges your branch. 
10. Delete your local copy of your branch. 

We provide a more in-depth version of this best practices workflow at [this project wikipage](https://github.com/spacetelescope/jwql/wiki/git-GitHub-workflow-for-contributing/) with further explanation for each step.

### Git Ignore: 
It's a good idea to set up a .gitignore file to allow you to place file types that you don't want to upload to the git branch. 

For example, if you are testing your updates or codes in a jupyter notebook in the directory it's good practice to not upload that notebook. Therefore, you can create a `.gitignore` file in the directory and place ` *ipynb` in a line in that file. Then when you do a `git status` those file types will not show up as having changed and needing to be commited. 

Other examples of files you would want to add to your `.gitignore` file are: 
1.`*.fits` ?
2.`*.jpeg`?
3.?

## Authors - Current Development Team
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
