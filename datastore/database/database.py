""" A module for interacting with the photo database file """
import sqlite3
from datastore import FieldObjectContainer, FieldObject, Album, Photo
from PyQt4 import QtGui, QtCore
from io import BytesIO
from versions import convertCheck, convertVersion
from Dialogs import WarningDialog
from Tkconstants import YES


class PhotoDatabase(QtCore.QObject):
    """ A class for connecting to and querying a photo database

    Arguments:
        dbfile (str): (None) The path to the database file
    """

    newDatabase = QtCore.pyqtSignal()
    databaseChanged = QtCore.pyqtSignal()

    def __init__(self, dbfile=None, parent=None):
        super(PhotoDatabase, self).__init__(parent)
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
            idq = 'SELECT FieldId from TagFields WHERE Name == ?'
            CatId = con.execute(idq, (name,)).fetchone()
            if CatId is None:
                return
            dmq = ('DELETE FROM TagMap WHERE TagId IN '
                   '(SELECT TagId FROM Tags WHERE FieldId == ?)')
            con.execute(dmq, CatId)
            dtq = 'DELETE FROM Tags WHERE FieldId == ?'
            con.execute(dtq, CatId)
            dfq = 'DELETE FROM Fields WHERE Name == ?'
            con.execute(dfq, (name,))
        self.databaseChanged.emit()

    def getTableAsDict(self, table, con=None, onePer=True, dbfile=None):
        """ Get the values of a table as a list of dictionaries

        Arguments:
            onePer (bool): (True) If False, the output is one dictionary with
                the values of each column grouped in a list under the field key.
                Otherwise it is a list of dictionaries with column/value pairs
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

        q = 'INSERT INTO Tags (FieldId, Value) VALUES (?,?)'
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

        # Check the file
        st, convert, ver = convertCheck(dbfile)
        if not st:
            if ver == 0:
                return (False, 'Could not open {}'.format(dbfile))
            else:
                msg = ('This version of Photo Organizer is not '
                       'compatible with the database you chose ({}).')
                return (False, msg.format(ver))

        if convert:
            dlg = WarningDialog('Old Version', self.parent())
            dlg.setText('This file is an old version ({}) that needs to be '
                        'converted.\nA backup copy will be saved before '
                        'conversion.'.format(ver))
            dlg.setQuestionText('Do you want to continue?')
            yes = dlg.addButton(QtGui.QDialogButtonBox.Yes)
            dlg.addButton(QtGui.QDialogButtonBox.No)
            dlg.exec_()
            if dlg.clickedButton() == yes:
                st2 = convertVersion(dbfile)
                if not st2[0]:
                    return False, 'File Conversion Failed\n{}'.format(st2[1])
            else:
                return False, None

        with self.connect(dbfile) as con:
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
            tqry = 'SELECT Value FROM AllTags '+\
                   'WHERE FilId == ? and Field == ?'

            # Get the tag field names and their fields
            tfq = 'SELECT Name from TagFields'
            tagFields = [k[0] for k in con.execute(tfq)]

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

                for fieldName in tagFields:
                    # Get the tags and group with their fields
                    cur2.execute(tqry, [fileId, fieldName])
                    tagList = cur2.fetchall()
                    tags = '; '.join([t[0] for t in tagList])
                    updateValues(values, fieldName, tags)

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

    def updateAppData(self, **kwargs):
        """ Save database-specific settings

        Arguments:
            Any name/value pair(s) where name is a valid AppData column
        """
        if self.dbfile is None:
            return
        setCols = ','.join(['{}=?'.format(k) for k in kwargs.keys()])
        q = 'UPDATE AppData SET ' + setCols
        with self.connect() as con:
            con.execute(q, kwargs.values())

    def updateAlbum(self, album, fileIds, fieldnames):
        """ Update the database when user changes data

        Generally Called by the slot for the model's albumChanged signal.
        Arguments are what they are because of what that signal contains

        Arguments:
            album (Album): The album to which the database should be updated
            fileIds (list): A list of database file ids
            fieldnames (list): A list of field names
        """
        # Setup variables
        allFiles = [k.fileId for k in album]

        # Set up batch queries
        taggedUpdate = {'ids': [], 'vals': []}
        tags2insert = []
        mapParams1 = []

        delMapQ = "DELETE From TagMap WHERE FilId == ? AND "+\
                  "(SELECT lower(Value) FROM Tags as t WHERE "+\
                  "t.TagId == TagMap.TagId AND t.FieldId == ?) "+\
                  "NOT IN ({})"
        delMaps = []

        # Current fields and tags
        with self.connect() as con:
            # Get the tag fields by ID and Column
            fieldstr = ','.join([str('\''+k+'\'') for k in fieldnames])
            catQ = 'SELECT Name, FieldId from TagFields WHERE Name in (%s)' % fieldstr

            res = con.execute(catQ).fetchall()
            allCatDict = dict(res)
            catIds = allCatDict.values()

            # Get all tags for each category
            catstr = ','.join([str(k) for k in catIds])
            tagQ = 'SELECT FieldId, TagId, Value FROM Tags WHERE FieldId IN (%s)' % catstr
            alltags_before = con.execute(tagQ).fetchall()

        # Loop over each index in the range and prepare for database calls
        for fileId in fileIds:
            for field in fieldnames:
                # Get the index of the current cell
                row = allFiles.index(fileId)
                photo = album[row]
                if field == album.taggedField:
                    # Handle the "tagged" checkboxes
                    taggedUpdate['vals'].append(1 if photo[field] else 0)
                    taggedUpdate['ids'].append(fileId)
                else:
                    # Handle the tag cagetories
                    # Skip any field that isn't a tag category
                    if field not in allCatDict:
                        # Not a "category" field
                        continue
                    catId = allCatDict[field]

                    # Get the current tags, including changes, from the dataset
                    cur_tags = photo.tags(field)
                    existing = {k[2].lower(): k[1] for k in alltags_before
                                if k[0] == catId}
                    for tag in cur_tags:
                        if tag.strip() == '':
                            continue
                        cat_tag = (catId, tag)
                        if (tag.lower() not in existing and
                                cat_tag not in tags2insert):
                            # INSERT new tag
                            tags2insert.append(cat_tag)
                        mapParams1.append((fileId, (catId, tag.lower())))

                    # Set up to remove deleted tags in this category and file
                    params = ','.join(['?'] * len(cur_tags))
                    q = delMapQ.format(params)
                    delMaps.append((q, [fileId, catId] +
                                    [k.lower() for k in cur_tags]))

        # Update the tagged status and insert the new tags
        self.updateTagged(taggedUpdate['ids'], taggedUpdate['vals'])
        self.insertTags(tags2insert)
        with self.connect() as con:
            # Get the TagIds
            alltags_added = con.execute(tagQ).fetchall()
            tagIds = {(k[0], k[2].lower()): k[1] for k in alltags_added}
            mapParams = [(k[0], tagIds[k[1]]) for k in mapParams1]

            # Insert Tag mapping (ON CONFLICT IGNORE)
            tagMapQ = 'INSERT OR IGNORE INTO TagMap (FilId, TagId) VALUES (?,?)'
            con.executemany(tagMapQ, mapParams)

            # Delete removed tags
            for q, params in delMaps:
                con.execute(q, params)

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
