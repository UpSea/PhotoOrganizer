import os
import sys
import re


__release__ = '0.3.1'

organization = "McNinch Custom"
application = "PhotoOrganizer"


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
