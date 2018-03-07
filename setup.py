import numpy as np
from setuptools import setup
from setuptools import find_packages

AUTHORS = 'Matthew Bourque, Sara Ogaz, Joe Filippazzo, Bryan Hilbert, Misty Cracraft, Graham Kanarek'
AUTHORS += 'Johannes Sahlmann, Lauren Chambers'

setup(
    name = 'jwql',
    description = 'The JWST Quicklook Project',
    url = 'https://github.com/spacetelescope/jwql.git',
    author = AUTHORS,
    keywords = ['astronomy'],
    classifiers = ['Programming Language :: Python'],
    packages = find_packages(),
    install_requires = ['astropy', 'numpy', 'matplotlib'],
    version = 0.0,
    include_package_data=True,
    include_dirs = [np.get_include()],
    )