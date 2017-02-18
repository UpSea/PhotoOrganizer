""" A module for interacting with the photo database file """
import sqlite3


class PhotoDatabase(object):
    """ A class for connecting to and querying a photo database

    Arguments:
        dbfile (str): (None) The path to the database file
    """

    def __init__(self, dbfile=None):
        self.setDatabaseFile(dbfile)

    def connect(self):
        """ Create a database connection """
        con = sqlite3.connect(self.dbfile)
        con.execute('pragma foreign_keys = 1')
        return con

    def setDatabaseFile(self, dbfile):
        """ Set the database file

        Arguments:
            dbfile (str): The path to the database file
        """
        self._dbfile = dbfile

#     def insertField(self):

    @property
    def dbfile(self):
        return self._dbfile
