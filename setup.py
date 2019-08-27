import numpy as np
from setuptools import setup
from setuptools import find_packages

VERSION = '0.22.0'

AUTHORS = 'Matthew Bourque, Misty Cracraft, Joe Filippazzo, Bryan Hilbert, '
AUTHORS += 'Graham Kanarek, Catherine Martlin, Johannes Sahlmann, Ben Sunnquist'

DESCRIPTION = 'The James Webb Space Telescope Quicklook Project'

REQUIRES = [
    'asdf>=2.3.3',
    'astropy>=3.2.1',
    'astroquery>=0.3.9',
    'authlib',
    'bokeh>=1.0',
    'codecov',
    'django>=2.0',
    'flake8',
    'inflection',
    'ipython',
    'jinja2',
    'jsonschema==2.6.0',
    'jwedb>=0.0.3',
    'jwst==0.13.0',
    'matplotlib',
    'numpy',
    'numpydoc',
    'pandas',
    'psycopg2',
    'pysiaf',
    'pytest',
    'pytest-cov',
    'scipy',
    'sphinx',
    'sqlalchemy',
    'stsci_rtd_theme',
    'twine'
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
