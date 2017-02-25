""" A module for interacting with the photo database file """
import sqlite3
from datastore import FieldObjectContainer, FieldObject
from PyQt4 import QtCore


class PhotoDatabase(QtCore.QObject):
    """ A class for connecting to and querying a photo database

    Arguments:
        dbfile (str): (None) The path to the database file
    """

    newDatabase = QtCore.pyqtSignal()
    databaseChanged = QtCore.pyqtSignal()

    def __init__(self, dbfile=None):
        super(PhotoDatabase, self).__init__()
        self.setDatabaseFile(dbfile)

    def connect(self, dbfile=None):
        """ Create a database connection """
        dbfile = dbfile or self.dbfile
        if dbfile is None:
            return
        con = sqlite3.connect(dbfile)
        con.execute('pragma foreign_keys = 1')
        return con

    def setDatabaseFile(self, dbfile):
        """ Set the database file

        Arguments:
            dbfile (str): The path to the database file
        """
        self._dbfile = dbfile
        if dbfile:
            self.newDatabase.emit()

    ###################
    #  Query Methods  #
    ###################

    def dropField(self, name):
        """ Drop a category from the database. All tags associated with that
        category will be removed

        Arguments:
            name (str): The name of the category to remove
        """
        with self.connect() as con:
            idq = 'SELECT CatId from Categories WHERE Name == ?'
            CatId = con.execute(idq, (name,)).fetchone()
            if CatId is None:
                return
            dmq = ('DELETE FROM TagMap WHERE TagId IN '
                   '(SELECT TagId FROM Tags WHERE CatId == ?)')
            con.execute(dmq, CatId)
            dtq = 'DELETE FROM Tags WHERE CatId == ?'
            con.execute(dtq, CatId)
            dfq = 'DELETE FROM Fields WHERE Name == ?'
            con.execute(dfq, (name,))
        self.databaseChanged.emit()

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
        """ Insert a new field. Return the id of the new catetory

        Arguments:
        """
        assert(isinstance(fieldobj, FieldObject))
        field_props = FieldObjectContainer.fieldProps
        props = ', '.join(field_props)
        params = ','.join(['?']*len(field_props))
        i = 'INSERT INTO Fields ({}) VALUES ({})'.format(props, params)
        values = [fieldobj.name, fieldobj.required, fieldobj.editor,
                  fieldobj.editable, fieldobj.name_editable, fieldobj.hidden,
                  fieldobj.filter, fieldobj.tags]
        with self.connect() as con:
            # Add the field
            newId = con.execute(i, values).lastrowid

        self.databaseChanged.emit()
        return newId

    def insertTags(self, catIds, tagValues=None):
        """ Insert a new tag. Return the id of the new tag

        Arguments
        """
        if tagValues is not None:
            if isinstance(catIds, int):
                catIds = [catIds]
            if isinstance(tagValues, basestring):
                tagValues = [tagValues]
            params = zip(catIds, tagValues)
        else:
            params = catIds

        q = 'INSERT INTO Tags (CatId, Value) VALUES (?,?)'
        with self.connect() as con:
            ids = []
            for param in params:
                try:
                    ids.append(con.execute(q, param).lastrowid)
                except sqlite3.IntegrityError:
                    # Probably failed unique constraint, ignore because tag
                    # already exists for cat
                    pass
        self.databaseChanged.emit()
        return ids

    def setFields(self, fields):
        """ Set the fields table to the given FieldContainerObjects

        Existing fields are updated, new fields are inserted and missing fields
        are deleted

        Arguments:
            fields (FieldObjectContainer)
        """
        field_props = fields.fieldProps
        props = ', '.join(field_props)
        params = ','.join(['?']*len(field_props))
        i = 'INSERT INTO Fields ({}) VALUES ({})'.format(props, params)
        with self.connect() as con:
            cur = con.execute('SELECT Name FROM Fields')
            dbfields = [k[0] for k in cur]
            uparams = ', '.join(['{} = ?'.format(k) for k in field_props])
            u = ('UPDATE Fields SET {} WHERE Name=?'.format(uparams))
            icommands = []
            ucommands = []
            for f in fields:
                values = [f.name, f.required, f.editor, f.editable,
                          f.name_editable, f.hidden, f.filter, f.tags]
                if f.name in dbfields:
                    ucommands.append(values+[f.name])
                else:
                    icommands.append(values)
            # Execute many for speed
            if icommands:
                con.executemany(i, icommands)
            if ucommands:
                con.executemany(u, ucommands)

            # Remove deleted fields
            df = [k for k in dbfields if k not in fields.names]
            dcommands = []
            for f in df:
                dcommands.append((f,))
            if dcommands:
                con.executemany('DELETE FROM Fields WHERE Name = ?', dcommands)
        self.databaseChanged.emit()

    def updateTagged(self, FileIds, tagged):
        """ Update the tagged status for the given files

        Arguments:
            FileIds ([int], int)
            tagged ([bool], bool)
        """
        if isinstance(FileIds, int):
            FileIds = [FileIds]
        if isinstance(tagged, bool):
            tagged = [tagged]

        q = 'UPDATE File SET Tagged = ? WHERE FilId == ?'
        with self.connect() as con:
            return con.executemany(q, zip(tagged, FileIds)).rowcount

    @property
    def dbfile(self):
        return self._dbfile


if __name__ == "__main__":
#     from create_database import create_database
    dbfile = 'FreshTrash.pdb'
#     create_database(dbfile)
    db = PhotoDatabase(dbfile)
#     db.insertField(FieldObject('People'))
#     print db.getTableAsDict('Fields')
#     print db.getTableAsDict('Fields', False)

#     with db.connect() as con:
#         try:
#             con.execute('INSERT INTO Tags (CatId, Value) VALUES (1, "Evelyn")')
#         except sqlite3.IntegrityError:
#             print 'failed'

    db.dropField('Joe')


#     import pdb
#     pdb.set_trace()
