""" A module for interacting with the photo database file """
import sqlite3
from datastore import FieldObjectContainer, FieldObject


class PhotoDatabase(object):
    """ A class for connecting to and querying a photo database

    Arguments:
        dbfile (str): (None) The path to the database file
    """

    def __init__(self, dbfile=None):
        self.setDatabaseFile(dbfile)

    def connect(self, dbfile=None):
        """ Create a database connection """
        dbfile = dbfile or self.dbfile
        con = sqlite3.connect(dbfile)
        con.execute('pragma foreign_keys = 1')
        return con

    def setDatabaseFile(self, dbfile):
        """ Set the database file

        Arguments:
            dbfile (str): The path to the database file
        """
        self._dbfile = dbfile

    ###################
    #  Query Methods  #
    ###################

    def getTableAsDict(self, table, onePer=True):
        """ Get the values of a table as a list of dictionaries

        Arguments:
            onePer (bool): (True) If False, the output is one dictionary with
                the values of each column grouped in a list under the field key
        """
        q = 'SELECT * FROM {}'.format(table)
        with self.connect() as con:
            cur = con.execute(q)
            values = [list(k) for k in cur]
            names = [k[0] for k in cur.description]
            if onePer:
                return [dict(zip(names, v)) for v in values]
            else:
                values = map(list, zip(*values))
            return dict(zip(names, values))

    def insertField(self, fieldobj):
        """ Insert a new field """
        assert(isinstance(fieldobj, FieldObject))
        field_props = FieldObjectContainer.fieldProps
        props = ', '.join(field_props)
        i = 'INSERT INTO Fields ({}) VALUES (?,?,?,?,?,?,?)'.format(props)
        values = [fieldobj.name, fieldobj.required, fieldobj.editor,
                  fieldobj.editable, fieldobj.name_editable, fieldobj.hidden,
                  fieldobj.filter]
        c = 'INSERT INTO Categories (Name) VALUES (?)'
        with self.connect() as con:
            # Add the field
            con.execute(i, values)
            con.execute(c, (fieldobj.name,))

    @property
    def dbfile(self):
        return self._dbfile

if __name__ == "__main__":
#     from create_database import create_database
    dbfile = 'TestDb2.db'
#     create_database(dbfile)
    db = PhotoDatabase(dbfile)
#     db.insertField(FieldObject('People'))
    print db.getTableAsDict('Fields')
    print db.getTableAsDict('Fields', False)
