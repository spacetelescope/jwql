import numpy as np
from setuptools import setup
from setuptools import find_packages

VERSION = '1.1.0'

AUTHORS = 'Matthew Bourque, Lauren Chambers, Misty Cracraft, Mike Engesser, Mees Fix, Joe Filippazzo, Bryan Hilbert, '
AUTHORS += 'Graham Kanarek, Teagan King, Catherine Martlin, Shannon Osborne, Maria Pena-Guerrero, Johannes Sahlmann, '
AUTHORS += 'Ben Sunnquist, Brian York'

DESCRIPTION = 'The James Webb Space Telescope Quicklook Project'

REQUIRES = [
    'asdf>=2.3.3',
    'astropy>=3.2.1',
    'astroquery>=0.3.9',
    'bandit',
    'bokeh',
    'codecov',
    'crds',
    'cryptography',
    'django<=3.1.7',
    'flake8',
    'inflection',
    'ipython',
    'jinja2',
    'jsonschema',
    'jwedb>=0.0.3',
    'jwst',
    'jwst_reffiles',
    'matplotlib',
    'nodejs',
    'numpy',
    'numpydoc',
    'pandas',
    'psycopg2',
    'pysiaf',
    'pytest',
    'pytest-cov',
    'scipy',
    'sphinx',
    'sphinx_rtd_theme',
    'sqlalchemy',
    'stdatamodels',
    'stsci_rtd_theme',
    'twine',
    'wtforms'
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
