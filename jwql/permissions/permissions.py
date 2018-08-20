#! /usr/bin/env python
"""Permissions module for managing file permissions for ``jwql``.

This module provides ``jwql`` with functions to inspect and set file
permissions.

The module takes as input a path to a file or directory, checks whether
the owner of the file is the ``jwql`` admin account, and if so, (1) set
the permissions appropriately, and (2) set the group membership
appropriately.

Authors
-------

    - Johannes Sahlmann

Use
---

    This module can be imported and used with

    ::

        from jwql.permissions import permissions
        permissions.set_permissions(pathname)

    Required arguments:

    ``pathname`` - Directory or file for which the default permissions
    should be set

Notes
-----

    Permissions are set and read using the stat module, see
    https://docs.python.org/3/library/stat.html

    Below is a list with the relevant stat attribute names, integer,
    octal, and string representations.

    ::

        stat_key stat_mode stat_mode_octal stat_mode_string
        -------- --------- --------------- ----------------
        S_IFPORT         0             0o0       ?---------
        S_IFDOOR         0             0o0       ?---------
         S_IXOTH         1             0o1       ?--------x
         S_IWOTH         2             0o2       ?-------w-
         S_IROTH         4             0o4       ?------r--
         S_IRWXO         7             0o7       ?------rwx
         S_IXGRP         8            0o10       ?-----x---
         S_IWGRP        16            0o20       ?----w----
         S_IRGRP        32            0o40       ?---r-----
         S_IRWXG        56            0o70       ?---rwx---
         S_IEXEC        64           0o100       ?--x------
         S_IXUSR        64           0o100       ?--x------
         S_IWUSR       128           0o200       ?-w-------
        S_IWRITE       128           0o200       ?-w-------
         S_IREAD       256           0o400       ?r--------
         S_IRUSR       256           0o400       ?r--------
         S_IRWXU       448           0o700       ?rwx------
         S_ISVTX       512          0o1000       ?--------T
         S_ISGID      1024          0o2000       ?-----S---
         S_ISUID      2048          0o4000       ?--S------
         S_IFIFO      4096             0o0       p---------
         S_IFCHR      8192             0o0       c---------
         S_IFDIR     16384             0o0       d---------
         S_IFBLK     24576             0o0       b---------
         S_IFREG     32768             0o0       ----------
         S_IFLNK     40960             0o0       l---------
        S_IFSOCK     49152             0o0       s---------
         S_IFWHT     57344             0o0       w---------
"""

import grp
import os
import pwd
import stat

# owner and group names for JWQL project
DEFAULT_OWNER = 'jwqladm'
DEFAULT_GROUP = 'jwql_dev'

# set the default mode for DEFAULT_OWNER
DEFAULT_MODE = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP # equivalent to '?rwxr-x---'

def get_group_string(pathname):
    """Return the group of ``pathname`` in string representation.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected.

    Returns
    -------
    group_name : str
        String representation of the group.
    """
    file_statinfo = os.stat(pathname)
    groupinfo = grp.getgrgid(file_statinfo.st_gid)
    group_name = groupinfo.gr_name
    return group_name


def get_owner_string(pathname):
    """Return the owner of ``pathname`` in string representation.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected

    Returns
    -------
    owner_name : str
        String representation of the owner.
    """
    file_statinfo = os.stat(pathname)
    ownerinfo = pwd.getpwuid(file_statinfo.st_uid)
    owner_name = ownerinfo.pw_name
    return owner_name


def has_permissions(pathname, owner=DEFAULT_OWNER, mode=DEFAULT_MODE, group=DEFAULT_GROUP):
    """Return boolean indicating whether ``pathname`` has the specified
    owner, permission, and group scheme.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected
    owner : str
        String representation of the owner
    mode : int
        Integer representation of the permission mode, compatible
        with ``os.stat`` output
    group : str
        String representation of the group

    Returns
    -------
    boolean : bool
    """
    verify_path(pathname)
    file_statinfo = os.stat(pathname)
    groupinfo = grp.getgrgid(file_statinfo.st_gid)

    # complement mode depending on whether input is file or directory
    if os.path.isfile(pathname):
        mode = mode | stat.S_IFREG
    elif os.path.isdir(pathname):
        mode = mode | stat.S_IFDIR

    if (get_owner_string(pathname) != owner) or (file_statinfo.st_mode != mode)\
            or (groupinfo.gr_name != group):
        return False

    return True


def set_permissions(pathname, owner=DEFAULT_OWNER, mode=DEFAULT_MODE, group=DEFAULT_GROUP, verbose=False):
    """Set mode and group of the file/directory identfied by
    ``pathname``, if and only if it is owned by ``owner``.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected
    owner : str
        String representation of the owner
    mode : int
        Integer representation of the permission mode, compatible with
        ``os.stat`` output
    group : str
        String representation of the group
    verbose : bool
        Boolean indicating whether verbose output is requested
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


def show_permissions(pathname):
    """Verbose output showing group, user, and permission information
    for a directory or file.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected
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


def verify_path(pathname):
    """Verify that pathname is either a directory or a file. If not, an
    error is raised.

    Parameters
    ----------
    pathname : str
        Directory or file to be inspected
    """
    if (not os.path.isdir(pathname)) and (not os.path.isfile(pathname)):
        raise NotImplementedError('{} is not a valid path or filename'.format(pathname))
