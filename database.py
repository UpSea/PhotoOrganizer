""" A module for interacting with the photo database file """
import sqlite3
from datastore import FieldObjectContainer, FieldObject, Album, Photo
from PyQt4 import QtGui, QtCore
from pkg_resources import parse_version
import re
from io import BytesIO


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

    def getTableAsDict(self, table, con=None, onePer=True, dbfile=None):
        """ Get the values of a table as a list of dictionaries

        Arguments:
            onePer (bool): (True) If False, the output is one dictionary with
                the values of each column grouped in a list under the field key
        """
        q = 'SELECT * FROM {}'.format(table)
        close = False if con else True
        con = con or self.connect(dbfile)
        try:
            cur = con.execute(q)
            values = [list(k) for k in cur]
            names = [k[0] for k in cur.description]
            if onePer:
                out = [dict(zip(names, v)) for v in values]
            else:
                values = map(list, zip(*values))
                out = dict(zip(names, values))
        except Exception as err:
            if close:
                con.close()
            raise err
        if close:
            con.close()
        return out

    def insertField(self, fieldobj):
        """ Insert a new field. Return the id of the new category

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

    def load(self, dbfile):
        """ Load a database file

        Returns:
            album (Album)
            geometry (read-write buffer): The main window geomerty as saved in
                the database
        """
        # Create the query strings
        qry = 'SELECT directory, filename, date, hash, thumbnail, FilId, '+\
              'tagged, datetime(importTimeUTC, "localtime") FROM File'
        try:
            con = self.connect(dbfile)
        except:
            return (False, 'Could not open {}'.format(dbfile))

        with con:
            q = 'SELECT AppFileVersion FROM AppData'
            try:
                version = con.execute(q).fetchone()[0]
            except:
                version = 0
            if compareRelease(version, '0.2') < 0:
                return (False, 'This version of Photo Organizer is not ' +
                        'compatible with the database you chose.', self)

            # Get the fields and create the new Album instance
            cur = con.execute('SELECT Name, Required, Editor, Editable, '+
                              'Name_Editable, Hidden, Filt , Tags FROM Fields')
            param_values = [list(k) for k in cur]
            params = [k[0].lower() for k in cur.description]
            vals = map(list, zip(*param_values))
            param_dicts = dict(zip(params, vals))
            album = Album(FieldObjectContainer(**param_dicts))
            fields = album.fields

            # Define the tag query string
            tqry = 'SELECT t.Value FROM File as f '+\
                   'JOIN TagMap as tm ON f.FilId == tm.FilId '+\
                   'JOIN Tags as t ON tm.TagId == t.TagId '+\
                   'JOIN Categories as c ON t.CatId == c.CatId '+\
                   'WHERE f.FilId == ? and c.Name == ?'

            # Get the categories and their fields
            categories = self.getTableAsDict('Categories', con, onePer=True)

            # Get the Photos and populate the Album
            cur2 = con.cursor()
            fileCur = con.execute(qry)
            k = 0
            for row in fileCur:
                k += 1
                directory = row[0]
                fname = row[1]
                date = row[2]
                hsh = row[3]
                data = row[4]
                fileId = row[5]
                tagged = bool(row[6])
                insertDate = row[7]
                fp = BytesIO(data)

                # Create the QPixmap from the byte array
                pix = QtGui.QPixmap()
                pix.loadFromData(fp.getvalue())
                thumb = QtGui.QIcon(pix)

                # Create the values list based on the order of fields
                def updateValues(values, name, val):
                    values[fields.index(name)] = val

                values = ['' for _ in fields]
                updateValues(values, 'Directory', directory)
                updateValues(values, 'File Name', fname)
                updateValues(values, 'Date', date)
                updateValues(values, 'Hash', str(hsh))
                updateValues(values, 'FileId', fileId)
                updateValues(values, 'Tagged', tagged)
                updateValues(values, 'Import Date', insertDate)

                for cat in categories:
                    # Get the tags and group with categories
                    catname = cat['Name']
                    cur2.execute(tqry, [fileId, catname])
                    tagList = cur2.fetchall()
                    tags = '; '.join([t[0] for t in tagList])
                    updateValues(values, catname, tags)

                album.append(Photo(fields, values, thumb))

            # Get the geometry
            q_geo = 'SELECT AlbumTableState from AppData'
            cur.execute(q_geo)
            geometry = cur.fetchone()[0]
        return album, geometry

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


if __name__ == "__main__":
    app = QtGui.QApplication([])
#     from create_database import create_database
    dbfile = 'asdf.pdb'
#     create_database(dbfile)
    db = PhotoDatabase(dbfile)
#     db.insertField(FieldObject('People'))
#     print db.getTableAsDict('Fields')
#     print db.getTableAsDict('Fields', onePer=False)

#     with db.connect() as con:
#         try:
#             con.execute('INSERT INTO Tags (CatId, Value) VALUES (1, "Evelyn")')
#         except sqlite3.IntegrityError:
#             print 'failed'

#     db.dropField('Joe')

    album = db.load(dbfile)

#     import pdb
#     pdb.set_trace()
