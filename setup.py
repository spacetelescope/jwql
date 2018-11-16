import numpy as np
from setuptools import setup
from setuptools import find_packages

VERSION = '0.4.0'

AUTHORS = 'Matthew Bourque, Sara Ogaz, Joe Filippazzo, Bryan Hilbert, Misty Cracraft, Graham Kanarek'
AUTHORS += 'Johannes Sahlmann, Lauren Chambers, Catherine Martlin'

REQUIRES = ['astroquery', 'bokeh==0.12.5', 'django==2.0.5', 'matplotlib', 'numpy', 'python-dateutil', 'sphinx', 'sphinx-automodapi', 'sqlalchemy']

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
