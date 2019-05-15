import numpy as np
from setuptools import setup
from setuptools import find_packages

VERSION = '0.19.0'

AUTHORS = 'Matthew Bourque, Lauren Chambers, Misty Cracraft, Joe Filippazzo, Bryan Hilbert, '
AUTHORS += 'Graham Kanarek, Catherine Martlin, Johannes Sahlmann'

DESCRIPTION = 'The James Webb Space Telescope Quicklook Project'

REQUIRES = [
    'astropy',
    'astroquery>=0.3.9',
    'authlib',
    'bokeh>=1.0',
    'django>=2.0',
    'jinja2',
    'jwedb',
    'jwst',
    'matplotlib',
    'numpy',
    'numpydoc',
    'pandas',
    'psycopg2',
    'pysiaf',
    'pytest',
    'sphinx',
    'sqlalchemy',
    'stsci_rtd_theme'
]

setup(
    name='jwql',
    version=VERSION,
    description=DESCRIPTION,
    url='https://github.com/spacetelescope/jwql.git',
    author=AUTHORS,
    author_email='jwql@stsci.edu',
    license='BSD',
    keywords=['astronomy', 'python'],
    classifiers=['Programming Language :: Python'],
    packages=find_packages(),
    install_requires=REQUIRES,
    include_package_data=True,
    include_dirs=[np.get_include()],
)
