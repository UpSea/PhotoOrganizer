import os
import sys


__release__ = '0.0.2'

organization = "McNinch Custom"
application = "PhotoOrganizer"


def resource_path(relative):
    """ Returns the path to the resource, whether running python or frozen
    executable """
    return os.path.join(getattr(sys, "_MEIPASS",
                                os.path.abspath(os.path.dirname(__file__))),
                        relative)
