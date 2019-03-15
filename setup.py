import numpy as np
from setuptools import setup
from setuptools import find_packages

VERSION = '0.18.0'

AUTHORS = 'Matthew Bourque, Sara Ogaz, Joe Filippazzo, Bryan Hilbert, Misty Cracraft, '
AUTHORS += 'Graham Kanarek, Johannes Sahlmann, Lauren Chambers, Catherine Martlin'

REQUIRES = ['astropy',
            'astroquery>=0.3.9',
            'authlib',
            'bokeh>=1.0',
            'django>=2.0',
            'jinja2',
            'jwst',
            'matplotlib',
            'numpy',
            'numpydoc',
            'pandas',
            'psycopg2',
            'pytest',
            'sphinx',
            'sqlalchemy',
            'stsci_rtd_theme']

setup(
    name='jwql',
    version=VERSION,
    description='The JWST Quicklook Project',
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
