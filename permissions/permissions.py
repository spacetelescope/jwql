#! /usr/bin/env python
"""Permissions module for managing file permissions for jwql

This module provides jwql with functions to inspect and set file
permissions.

The module takes as input a path to a file or directory, checks
 whether the owner of the file is the jwql admin account, and if
 so, (1) set the permissions appropriately, and (2) set the
 group membership appropriately.

Authors
-------

    - Johannes Sahlmann

Use
---


TODO
----

    - support setting permissions for all files in a folder ?
    - write tests for setting group and managing directory permissions

"""

import os
import stat
import pwd
import grp

# for tests on dljwql:
# DEFAULT_OWNER = 'jwqladm'
# DEFAULT_GROUP = 'jwql_dev'

# for tests on on jsahlmann's machine:
DEFAULT_OWNER = 'jsahlmann'
DEFAULT_GROUP = r'STSCI\science'

# set the default mode for DEFAULT_OWNER
# see https://docs.python.org/3/library/stat.html#stat.S_ISUID
# DEFAULT_MODE = stat.S_IRWXU # equivalent to '?rwx------'
DEFAULT_MODE = stat.S_IRWXU | stat.S_IRGRP  # equivalent to '?rwxr-----'


def get_owner_string(pathname):
    """Return the owner of pathname in string representation

    :param pathname:
    :return:
    """

    file_statinfo = os.stat(pathname)
    ownerinfo = pwd.getpwuid(file_statinfo.st_uid)
    return ownerinfo.pw_name


def verify_path(pathname):
    """Check that pathname is either a directory or a file

    :param pathname: string
        directory or file to be inspected
    :return:
    """

    if (not os.path.isdir(pathname)) and (not os.path.isfile(pathname)):
        raise NotImplementedError('{} is not a valid path or filename'.format(pathname))


def show_permissions(pathname):
    """Verbose output showing group, user, and permission information for a directory or file

    :param pathname: string
            directory or file to be inspected
    :return:
    """

    verify_path(pathname)
    file_statinfo = os.stat(pathname)
    ownerinfo = pwd.getpwuid(file_statinfo.st_uid)
    groupinfo = grp.getgrgid(file_statinfo.st_gid)

    if os.path.isdir(pathname):
        info_string = 'directory'
    elif os.path.isfile(pathname):
        info_string = 'file'

    print('Inspecting {}: {}'.format(info_string, pathname))
    print('group {} = {}'.format(file_statinfo.st_gid, groupinfo.gr_name))
    print('owner {} = {}'.format(file_statinfo.st_uid, ownerinfo.pw_name))
    print('mode {} = {}'.format(file_statinfo.st_mode, stat.filemode(file_statinfo.st_mode)))
    print('')


def has_permissions(pathname, owner=DEFAULT_OWNER, mode=DEFAULT_MODE, group=DEFAULT_GROUP):
    """Returns boolean indicating whether pathname has the specified owner, permission,
    and group scheme

    :param pathname: string
    :param owner: string
    :param mode: int
    :param group: string
    :return:
    """

    verify_path(pathname)
    file_statinfo = os.stat(pathname)
    groupinfo = grp.getgrgid(file_statinfo.st_gid)

    # complement mode depending on whether input is file or directory
    if os.path.isfile(pathname):
        mode = mode | stat.S_IFREG
    elif os.path.isfile(pathname):
        mode = mode | stat.S_IFDIR

    if (get_owner_string(pathname) != owner) or (file_statinfo.st_mode != mode)\
            or (groupinfo.gr_name != group):
        return False

    return True

def set_permissions(pathname, owner=DEFAULT_OWNER, mode=DEFAULT_MODE, group=DEFAULT_GROUP,
                    verbose=True):
    """Set mode and group of the file/directory identfied by pathname,
    if and only if it is owned by owner

    :param pathname: string
    :param owner: string
    :param mode: int
    :param group: string
    :return:
    """

    if verbose:
        print('\nBefore:')
        show_permissions(pathname)

    if not has_permissions(pathname):
        if get_owner_string(pathname) == owner:
            os.chmod(pathname, mode)
            # change group but not owner
            os.chown(pathname, -1, grp.getgrnam(group).gr_gid)

    if verbose:
        print('After:')
        show_permissions(pathname)
