#!/usr/bin/python
# Original Author: Christopher Nyland
# Original Creation Date: 2012/09/14
"""
This __init__ file dynamically compiles all the UI files in its directory,
interrogates them for there class names. And then imports those class names
into this module.
"""
import os
import sys
import ast
import py_compile
from PyQt4 import uic

file_names = []


class ClassParser(ast.NodeVisitor):

    """ This class is used with the AST model to collect all the class names
    in a file

    """

    def __init__(self):
        self.class_names = []

    def parse(self, code):
        """ parser function

        This function is the actual parser of the code. Its input is the code
        to be parsed and is the one that calls the visitors for each part.
        It returns the class names
        """
        self.class_names = []
        tree = ast.parse(code)
        self.visit(tree)
        return self.class_names

    def visit_ClassDef(self, stmt):
        """ Visitor for class definitions """
        self.class_names.append(stmt.name)
        super(ClassParser, self).generic_visit(stmt)


def modname(ui_dir, ui_file):
    """ This is a rename mapping function for compileUiDir """
    out_dir = ui_dir
    out_file = ui_file.replace('.py', '_Ui.py')
#     out_file = '{0}'.format(ui_file)
    out_path = os.path.join(out_dir, out_file)
    file_names.append(out_path)
    return (out_dir, out_file)

if not hasattr(sys, '_MEIPASS'):
    parser = ClassParser()
    file_classes = {}

    # Create py files from ui files
    # file_names is passed around here as it is outside of each functions scope
    pth = os.path.split(__file__)[0]
    if not pth:
        pth = './'
    if [k for k in os.listdir(pth) if '.ui' in k]:
        uic.compileUiDir(pth, map=modname, execute=True)

    # Parse those py_ui files for the class names
    for File in file_names:
        with open(File, 'rb') as fid:
            code = fid.read()
        file_classes[File] = parser.parse(code)

    # Import the Classes
    # First split the file names to get the import modules then append those to the
    # package name in dot format. I the from list include the class names from the
    # AST parse above. Make the import into the local variable "_". Then move the
    # classes we want into the local name space with getattr.
    for File, k_list in file_classes.items():
        mod = os.path.splitext(os.path.split(File)[1])[0]
        import_stmt = "{}.{}".format(__package__, mod)
        _ = __import__(import_stmt, fromlist=k_list)
        for klass in k_list:
            locals()[klass] = getattr(_, klass)
