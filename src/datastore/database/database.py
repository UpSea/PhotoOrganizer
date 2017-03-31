""" A module for interacting with the photo database file """
from PyQt4 import QtGui, QtCore
from create_database import create_database
from datastore import FieldObjectContainer, FieldObject, Album, Photo
from Dialogs import WarningDialog, warning_box
from io import BytesIO
import os.path
import re
import sqlite3
from versions import convertCheck, convertVersion


class PhotoDatabase(QtCore.QObject):
    """ A class for connecting to and querying a photo database

    Arguments:
        dbfile (str): (None) The path to the database file
    """

    sigNewDatabase = QtCore.pyqtSignal()
    databaseChanged = QtCore.pyqtSignal()

    def __init__(self, dbfile=None, parent=None):
        super(PhotoDatabase, self).__init__(parent)
        self._dbfile = None
        if dbfile and os.path.exists(dbfile):
            # Open an existing database
            st, album = self.load(dbfile) #Note look into combining album field initialization with ours
            if not st:
                if album:
                    # There was an error
                    warning_box(album) # Probably move this to the caller
                self.album = Album()
            else:
                self.album = album
                self.setDatabaseFile(dbfile)
                self.setFields(album.fields)
        else:
            # Create new database
            self.album = Album()
            if dbfile:
                create_database(dbfile)
                self.setDatabaseFile(dbfile)
                self.setFields(self.album.fields)

    def closeDatabase(self):
        """ Close the existing database """
        self._dbfile = None
        self.album = Album()

    def connect(self, dbfile=None):
        """ Create a database connection """
        dbfile = dbfile or self.dbfile
        if dbfile is None:
            return
        con = sqlite3.connect(dbfile)
        con.execute('pragma foreign_keys = 1')
        return con

    def newDatabase(self, dbfile):
        """ Create new database """
        # Create new database
        self.album = Album()
        create_database(dbfile)
        self.setDatabaseFile(dbfile)
        self.setFields(self.album.fields)
        return True, ''

    def setDatabaseFile(self, dbfile):
        """ Set the database file

        Arguments:
            dbfile (str): The path to the database file
        """
        self._dbfile = dbfile
        if dbfile:
            self.sigNewDatabase.emit()

    ###################
    #  Query Methods  #
    ###################

    def deleteFile(self, filId):
        """ Delete the file with the given id and its associated tag mappings

        Arguments:
            filId (int): The database file id to be deleted
        """
        with self.connect() as con:
            q1 = 'DELETE FROM TagMap WHERE FilId == ?'
            cur = con.execute(q1, (filId,))

            q2 = 'DELETE FROM File WHERE FilId == ?'
            cur.execute(q2, (filId,))

        dex = [k.fileId for k in self.album].index(filId)
        self.album.pop(dex)

    def dropField(self, idx, force=False):
        """ Drop a category from the database. All tags associated with that
        category will be removed

        Arguments:
            name (str): The name of the category to remove
        """
        # Check if field is required
        field = self.fields[idx]
        if field.required and (not force):
            raise DatabaseError('Cannot remove required field')

        # Remove the referencing tag maps, tags and fields from DB
        with self.connect() as con:
            idq = 'SELECT FieldId from TagFields WHERE Name == ?'
            CatId = con.execute(idq, (field.name,)).fetchone()
            if CatId is None:
                return
            dmq = ('DELETE FROM TagMap WHERE TagId IN '
                   '(SELECT TagId FROM Tags WHERE FieldId == ?)')
            con.execute(dmq, CatId)
            dtq = 'DELETE FROM Tags WHERE FieldId == ?'
            con.execute(dtq, CatId)
            dfq = 'DELETE FROM Fields WHERE Name == ?'
            con.execute(dfq, (field.name,))
        self.databaseChanged.emit()

        # Remove the field from the album
        self.album.removeField(idx)

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

    def geometry(self):
        """ Return the header geometry stored in the database """
        with self.connect() as con:
            # Get the geometry
            q_geo = 'SELECT AlbumTableState from AppData'
            cur = con.execute(q_geo)
            return cur.fetchone()[0]

    def icon2Blob(self, icon):
        """ Convert the thumbnail Icon to an Sqlite3 blob for insertion into DB

        Arguments:
            icon (QIcon)
        """
        if icon:
            pixmap = icon.pixmap(icon.availableSizes()[0])
            buff = QtCore.QBuffer()
            buff.open(QtCore.QIODevice.ReadWrite)
            pixmap.save(buff, 'png')
            return sqlite3.Binary(buff.data())

    def insertField(self, index=None, name=None):
        """ Insert a new field. Return the id of the new category

        Arguments:
            index (int): (None) The index at which to insert the new field.
                Defaults to the end.
            name (FieldObject): (None) The field to add to the database.
                Default is a generic numbered field with default properties.
        """
        # Set up
        new_field = None
        # Check inputs
        if isinstance(name, FieldObject):
            new_field = name
            name = new_field.name
        if index is None:
            index = len(self.fields)

        # Create field name if none given
        if name is None:
            name = 'Tag Field {}'.format(self.nextDefaultField())

        # Check for duplicate field
        if name in self.field_names:
            raise ValueError('duplicate column name: {}'.format(name))

        # Create the new field object
        if new_field is None:
            new_field = FieldObject(name)

        # Insert the field into the DB
        assert(isinstance(new_field, FieldObject))
        field_props = FieldObjectContainer.fieldProps
        props = ', '.join(field_props.keys())
        params = ','.join(['?']*len(field_props))
        i = 'INSERT INTO Fields ({}) VALUES ({})'.format(props, params)
        values = [getattr(new_field, v) for v in field_props.values()]

        with self.connect() as con:
            # Add the field
            newId = con.execute(i, values).lastrowid
        self.databaseChanged.emit()

        # Insert the field into the album
        # This is after the database insertion in the event of an error
        self.fields.insert(index, new_field)
        for entry in self.album._entries:
            entry[self.fields[index]] = ''

        return newId

    def insertFile(self, photo, idx=None):
        """ Insert a photo into the database from a photo object

        Arguments:
            photo (Photo): The photo object to be inserted
        """
        # Create the thumbnail blob
        thumb = self.icon2Blob(photo.thumb)

        # Get the default columns and values
        #much like the field properties, need to find something cleaner
        fields = ['tagged', 'filename', 'directory', 'filedate', 'hash',
                  'thumbnail']
        date = photo.datetime or photo.date
        values = [photo.tagged, photo.fileName, photo.directory, date,
                  photo.hash, thumb]

        with self.connect() as con:
            if photo.fileId in (None, ''):
                # Let the database fill in the FileID and Import Time
                fieldStr = ','.join(fields)
                parStr = ','.join(['?']*len(fields))
                iqry = 'INSERT INTO File ({}) VALUES ({})'.format(fieldStr, parStr)
                cur = con.execute(iqry, values)
                filId = cur.lastrowid

                # Set the photo's file id and import time
                photo[self.fields[Album.fileIdField]] = filId
                impQry = 'SELECT importTimeUTC FROM File WHERE FilId == ?'
                cur = cur.execute(impQry, (filId,))
                photo[self.fields[Album.importDateField]] = cur.fetchone()[0]
            else:
                # The photo already has a file id and import time
                fields += ['FilId', 'importTimeUTC']
                values += [int(photo.fileId), photo.importDate]

                fieldStr = ','.join(fields)
                parStr = ','.join(['?']*len(fields))
                iqry = 'INSERT INTO File ({}) VALUES ({})'.format(fieldStr, parStr)
                cur = con.execute(iqry, values)

            # Add the tag mappings
            pTagFields = [k for k in photo if k.tags]
            if pTagFields:
                tfq = 'SELECT FieldId from Fields WHERE Name == ?'
                tq = 'SELECT TagId FROM Tags WHERE FieldId == ? AND Value == ?'
                tmq = 'INSERT INTO TagMap (FilId, TagId) VALUES (?,?)'
                tmps = []
                for field in pTagFields:
                    # Get the field id
                    fieldId = con.execute(tfq, (field.name,)).fetchone()[0]

                    tags = photo.tags(field)
                    for tag in tags:
                        # Get the tag id
                        tagId = con.execute(tq, (fieldId, tag)).fetchone()[0]
                        # INSERT the tag map
                        tmps.append((photo.fileId, tagId))
                con.executemany(tmq, tmps)

        # Put this here in case queries fail
        if idx is None:
            idx = len(self.album)
        self.album.insert(idx, photo)

    def insertTags(self, fieldIds, tagValues=None):
        """ Insert a new tag. Return the id of the new tag. Return a list of
        IDs for the inserted tags.

        Arguments:
            fieldIds (int, [int], [(int, str)]: The database ID(s) of the
                field(s) to which the tags should be added. This can also be a
                list of tuples containing each fieldId and tagValue pair, in
                which case, the next argument should be None
            tagValues (str, [str]): (None) The tag(s) that correspond to the
                given fields.
        """
        if tagValues is not None:
            if isinstance(fieldIds, int):
                fieldIds = [fieldIds]
            if isinstance(tagValues, basestring):
                tagValues = [tagValues]
            params = zip(fieldIds, tagValues)
        else:
            params = fieldIds

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
        qry = 'SELECT directory, filename, filedate, hash, thumbnail, FilId, '+\
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
            dlg.setText('{}\nThis file is an old version ({}) that needs to be '
                        'converted.\nA backup copy will be saved before '
                        'conversion.'.format(dbfile, ver))
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

        return True, album

    def nextDefaultField(self):
        """ Return the next numbered default field name """
        # Account for any existing fields with generic numbered names
        c = re.compile('Tag Field (\d+)')
        matches = map(c.match, [str(k) for k in self.fields])
        numbers = [int(k.groups()[0]) for k in matches if k]
        return max(numbers) + 1 if numbers else 1

    def openDatabase(self, dbfile):
        """ Open a new database """
        st, album = self.load(dbfile)
        if not st:
            return st, album
        self.album = album
        self._dbfile = dbfile
        self.sigNewDatabase.emit()
        return True, ''

    def pop(self, idx):
        filId = self.album[idx].fileId
        self.deleteFile(filId)

    def renameTag(self, tagId, newName):
        """ Rename a tag

        Arguments:
            tagId (int): The db id of the tag to rename
            newName (str): The new tag name
        """
        # Rename the tag in the database
        q = 'SELECT Value, FieldId FROM Tags WHERE TagId == ?'
        qf = 'SELECT Name from Fields WHERE FieldId == ?'
        qu = 'UPDATE Tags SET Value = ? WHERE TagId == ?'
        with self.connect() as con:
            oldName, fieldname = con.execute(q, (tagId,)).fetchone()
            field = con.execute(qf, (fieldname,)).fetchone()[0]
            con.execute(qu, (newName, tagId))
        self.databaseChanged.emit()

        # Update the photo objects
        for photo in self.album:
            photo[field] = photo[field].replace(oldName, newName)

    def setFields(self, fields):
        """ Set the fields table to the given FieldContainerObjects

        Existing fields are updated, new fields are inserted and missing fields
        are deleted

        Arguments:
            fields (FieldObjectContainer)
        """
        field_props = FieldObjectContainer.fieldProps
        props = ', '.join(field_props.keys())
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
                values = [getattr(f, v) for v in field_props.values()]
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

    def tagsByFileId(self, fileId):
        """ Return a list of Tag IDs that are applied to the given photo

        Arguments:
            fileId (int): The database ID of the photo
        """
        q = ('SELECT t.TagId FROM TagMap as tm JOIN Tags as t ON '
             't.TagId == tm.TagId WHERE tm.FilId == ?')
        with self.connect() as con:
            res = con.execute(q, (fileId,))
            return [k[0] for k in res]

    def tagById(self, tagId):
        """ Return the tag and field names for the given tag id

        Arguments:
            tagId (int): The db id of the tag
        """
        q = 'SELECT value, field FROM TagList WHERE TagId == ?'
        with self.connect() as con:
            return con.execute(q, (tagId,)).fetchone()

    def setThumb(self, fileId, thumb):
        """ Set the thumbnail blob in the database

        Arguments:
            fileId (int): The file id to set the thumbnail
            thumb (QIcon): The thumbnail saved in the Photo object
        """
        blob = self.icon2Blob(thumb)
        q = 'UPDATE File SET thumbnail = ? WHERE FilId == ?'
        with self.connect() as con:
            con.execute(q, (blob, fileId))

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

    def updateAlbum(self, fileIds, fieldnames):
        """ Update the database when user changes data

        Generally Called by the slot for the model's albumChanged signal.
        Arguments are what they are because of what that signal contains

        Arguments:
            fileIds (list): A list of database file ids
            fieldnames (list): A list of field names
        """
        # Setup variables
        album = self.album
        allFiles = [k.fileId for k in album]

        # Set up batch queries
        taggedUpdate = {'ids': [], 'vals': []}
        tags2insert = []
        mapParams1 = []

        delMapQ = "DELETE From TagMap WHERE FilId == ? AND "+\
                  "(SELECT FieldId FROM Tags as t "+\
                  "WHERE t.TagId == TagMap.TagId) == ? AND "+\
                  "(SELECT lower(Value) FROM Tags as t WHERE "+\
                  "t.TagId == TagMap.TagId) "+\
                  "NOT IN ({})"
        delMaps = []

        # Current fields and tags
        with self.connect() as con:
            # Get the tag fields to update as dict by Name and ID
            fieldstr = ','.join([str('\''+k+'\'') for k in fieldnames])
            catQ = 'SELECT Name, FieldId from TagFields WHERE Name in (%s)' % fieldstr

            res = con.execute(catQ).fetchall()
            allCatDict = dict(res)
            catIds = allCatDict.values()

            # Get all tags for each FileId and category to update
            catstr = ','.join([str(k) for k in catIds])
            tagQ = 'SELECT FieldId, TagId, Value FROM Tags WHERE FieldId IN (%s)' % catstr
            alltags_before = con.execute(tagQ).fetchall()

        # Loop over each file and field and prepare for parameters for db query
        for fileId in fileIds:
            for field in fieldnames:
                # Get the current Photo object
                row = allFiles.index(fileId)
                photo = album[row]
                # Tag or checkbox?
                if field == album.taggedField:
                    # Handle the "tagged" checkboxes
                    taggedUpdate['vals'].append(1 if photo[field] else 0)
                    taggedUpdate['ids'].append(fileId)
                else:
                    # Handle the tag categories
                    # Skip any field that isn't a tag category
                    if field not in allCatDict:
                        # Not a "category" field
                        continue
                    catId = allCatDict[field]

                    # Get the current tags, including changes, from the dataset
                    cur_tags = photo.tags(field)
                    existing = {k[2].lower(): k[1] for k in alltags_before
                                if k[0] == catId}
                    # For each tag determine if it exists altogether and insert
                    # the tag-to-file mapping
                    for tag in cur_tags:
                        if tag.strip() == '':
                            continue
                        cat_tag = (catId, tag)
                        if (tag.lower() not in existing and
                                cat_tag not in tags2insert):
                            # INSERT new tag
                            tags2insert.append(cat_tag)
                        # Store the mapping. We don't care if the mapping
                        # exists, the query will ignore duplicates.
                        mapParams1.append((fileId, (catId, tag.lower())))

                    # Set up to remove deleted tags in this category and file
                    params = ','.join(['?'] * len(cur_tags))
                    q = delMapQ.format(params)
                    delMaps.append((q, [fileId, catId] +
                                    [k.lower() for k in cur_tags]))

        # Update the tagged status and insert the new tags
        self.updateTagged(taggedUpdate['ids'], taggedUpdate['vals'])
        self.insertTags(tags2insert)
        # Map the tags to files and delete removed mappings
        with self.connect() as con:
            # Get the TagIds for the tag mappings
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
        """ Update the tagged status for the given files. Return the rowcount

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

    #################
    # Album Methods #
    #################

    def __getitem__(self, key):
        return self.album[key]

    def __setitem__(self, key, value):
        entry, fdex = key
        # Set photo data
        self.album[entry, fdex] = value
        # Update database
        self.updateAlbum([self.album[entry].fileId], [self.fields[fdex].name])

    ################
    #  Properties  #
    ################

    def __len__(self):
        return len(self.album._entries)

    @property
    def dbfile(self):
        return self._dbfile

    def index(self, key):
        return self.album.index(key)

    @property
    def fields(self):
        return self.album.fields

    @property
    def field_names(self):
        return self.album.field_names

    @property
    def taggedField(self):
        return self.album.taggedField


class DatabaseError(BaseException):
    pass
