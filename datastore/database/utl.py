from pkg_resources import parse_version
import re


def compareRelease(a, b):
    """Compares two release numbers. Returns 0 if versions are the same, -1 if
    the a is older than b and 1 if a is newer than b"""
    a = parse_version(re.sub('\(.*?\)', '', a))
    b = parse_version(re.sub('\(.*?\)', '', b))
    if a < b:
        return -1
    elif a == b:
        return 0
    else:
        return 1


def compareMinor(a, b):
    """Compare two release numbers to the Minor Revision (first two digits)

    Return 0 if versions are the same, -1 if a is older than b and 1 if a
    is newer.
    """
    a_parts = re.sub('\(.*?\)', '', a).split('.')
    b_parts = re.sub('\(.*?\)', '', b).split('.')
    A = '.'.join(a_parts[:2])
    B = '.'.join(b_parts[:2])
    return compareRelease(A, B)
