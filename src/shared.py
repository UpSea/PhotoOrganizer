import os
import sys
import re


__release__ = '0.5.1'

# These are used in the settings
organization = "McNinch Custom"
application = "PhotoOrganizer"

# This is the default installation directory
installDir = os.path.join(os.path.expanduser("~"), '.PhotoOrganizer')
trashDir = os.path.join(installDir, '.trash')
if not os.path.exists(trashDir):
    os.mkdir(trashDir)


def resource_path(relative):
    """ Returns the path to the resource, whether running python or frozen
    executable """
    return os.path.join(getattr(sys, "_MEIPASS",
                                os.path.abspath(os.path.dirname(__file__))),
                        relative)


def replace(text, rep):
    """ Replace all instances of multiple strings

    Arguments:
        text (str): The base string
        rep (dict): A dictionary where the keys() are the strings to replace,
            and the values are what to replace them with.
    """
    # use these three lines to do the replacement
    rep = dict((re.escape(k), v) for k, v in rep.iteritems())
    pattern = re.compile("|".join(rep.keys()))
    text = pattern.sub(lambda m: rep[re.escape(m.group(0))], text)
    return text

# Build Time Info
if hasattr(sys, '_MEIPASS'):
    frozen = True
    BUILD_INFO_FILE = os.path.join(sys._MEIPASS, 'build_info')
    if os.path.exists(BUILD_INFO_FILE):
        with open(BUILD_INFO_FILE, 'rb') as fid:
            BUILD_TIME = fid.readline()
            BUILD_INFO = fid.read()
    else:
        BUILD_TIME = "No Build Info"
else:
    frozen = False
    BUILD_TIME = "Running Python"
