import numpy as np
from setuptools import setup
from setuptools import find_packages


VERSION = '0.4.0'

AUTHORS = 'Matthew Bourque, Sara Ogaz, Joe Filippazzo, Bryan Hilbert, Misty Cracraft, Graham Kanarek'
AUTHORS += 'Johannes Sahlmann, Lauren Chambers, Catherine Martlin'


def get_requires():
    """Reads in the ``environment.yml`` file to determine the value of
    the ``install_requires`` parameter.

    Returns
    -------
    requires : list
        The list of requirements.
    """

    # Read in the environment file
    with open('environment.yml') as f:
        environment_file = f.readlines()

    # Determine where list of dependencies begin
    index = 0
    for line in environment_file:
        index += 1
        if 'dependencies:' in line:
            break
    dependencies = environment_file[index:]

    # Remove excluded libraries
    exclude_list = ['pip:', 'python', 'postgresql']
    for library in exclude_list:
        dependencies = [item for item in dependencies if library not in item]

    # Parse out the remaining library names
    requires = [item.split('=')[0].split()[-1] for item in dependencies]

    return requires


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
    install_requires=get_requires(),
    include_package_data=True,
    include_dirs=[np.get_include()],
    )
