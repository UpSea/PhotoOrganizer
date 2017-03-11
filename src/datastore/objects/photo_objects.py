from fieldobjects import FieldObject, FieldObjectContainer
from collections import MutableSequence
from datetime import datetime
import re
import os.path
import traceback
import pdb

# Handle python versions
import sys
if sys.version_info < (3,):
    strobj = basestring
else:
    strobj = str


class Photo(dict):
    """ Base class for Photo Enties

    Arguments:
        fields (list[FieldObject]): (Optional) The fields (column headings)
        values (list[<>]):  (Optional) The values for each field. If provided,
            it should be the same length as values
        thumb (PIL.Image):  (Optional) The thumbnail image
        tagged (bool): Whether or not tagging has been completed
    """

    def __init__(self, fields=None, values=None, thumb=None):
        fields = fields or []
        assert isinstance(fields, (list, FieldObjectContainer))
        assert all([isinstance(k, FieldObject) for k in fields])
        values = ['' for _ in fields] if values is None else values
        self.thumb = thumb
        assert len(fields) == len(values)

        super(Photo, self).__init__(zip(fields, values))

    def __getitem__(self, key):
        if isinstance(key, FieldObject):
            return super(Photo, self).__getitem__(key)
        else:
            return super(Photo, self).__getitem__(self.field_by_name(key))

    def __repr__(self):
        return '<Photo: %s>' % dict.__repr__(self)

    def field_by_name(self, name):
        field_names = [k.name for k in self.keys()]
        if name not in field_names:
            raise ValueError('%s is not a valid field name' % name)
        dex = [i for i, x in enumerate(field_names) if x == name]
        if len(dex) != 1:
            raise ValueError('%s is the name of more than one field' % name)

        return self.keys()[dex[0]]

    def removeField(self, field):
        del self[field]

    def splitTags(self, tagStr):
        """ Return a list of strings from the given delimited string

        Arguments:
            tagStr (str): A , or ; delimited string of tags
        """
        return [k.strip() for k in re.split(';|,', tagStr) if k.strip() != '']

    def tags(self, field):
        """ Return the tags in a list  for the given field

        Arguments:
            field (FieldObject, str): The field object or name
        """
        return self.splitTags(self[field])

    @property
    def datetime(self):
        fieldnames = [k.name for k in self.keys()]
        dateField = Album.dateField
        date = self[dateField] if dateField in fieldnames else None
        if date:
            try:
                return datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError) as err:
                return

    @property
    def fileId(self):
        return self[Album.fileIdField]

    @property
    def filePath(self):
        return os.path.join(self[Album.directoryField],
                            self[Album.fileNameField])


class Album(MutableSequence):
    """A Photo container

    Arguments:
        fields (list[str], FieldObjectContainer):  (Optional) A list of
            field names or FieldObjectContainer.
        values (list[list[<>]]: (Optional) A list of lists. Each list is a list
            of objects. Each sublist should be the same length as fields.
    """

    dateField = 'Date'
    fileIdField = 'FileId'
    taggedField = 'Tagged'
    directoryField = 'Directory'
    fileNameField = 'File Name'

    def __init__(self, fields=None, values=None):
        fields = fields or []
        assert isinstance(fields, (list, FieldObjectContainer))
        self.initializeFields()

        # Ensure fieldobj is a FieldObjectContainer
        if isinstance(fields, list):
            for f in fields:
                if f in self.field_names:
                    raise ValueError('{} is a duplicate field name'.format(f))
                self._fields.append(FieldObject(f))
        else:
            usedfields = []
            for f in fields:
                # Replace existing fields
                if f.name in self.field_names:
                    dex = self.field_names.index(f.name)
                    self.fields[dex] = f
                    usedfields.append(f)
            for f in usedfields:
                fields.remove(f)
            self._fields.extend(fields)

        # Initialize entries
        self._entries = []

        # Create and store the entries
        values = values or []
        for v in values:
            self._entries.append(Photo(self._fields, v))

        # Set the counter for generic field names, accounting for any existing
        # fields with generic numbered names
        c = re.compile('Tag Field (\d+)')
        matches = map(c.match, [str(k) for k in fields])
        numbers = [int(k.groups()[0]) for k in matches if k]
        self._am_counter = max(numbers) + 1 if numbers else 1

    def __delitem__(self, key):
        del self._entries[key]

    def __getitem__(self, key):
        if isinstance(key, tuple):
            field = key[1]
            if isinstance(field, strobj):
                field = self.fields[field]
            return self[key[0]][field]
        else:
            # Key must be integer index
            return self._entries[key]

    def __len__(self):
        return len(self._entries)

    def __setitem__(self, key, value):
        entry = key[0]
        fdex = key[1]
        field = self._fields[fdex]
        self[entry][field] = value

    def insert(self, key, value):
        self._entries.insert(key, value)

    def append(self, value):
        self._entries.append(value)

    def index(self, value):
        return self._entries.index(value)

    def initializeFields(self):
        """ Initialize the default fields """
        fields = FieldObjectContainer()
        fdict = [{'name': 'Image', 'required': True, 'editable': False,
                  'name_editable': False},
                 {'name': self.taggedField, 'required': True,
                  'editor': FieldObject.CheckBoxEditor, 'name_editable': False},
                 {'name': 'File Name', 'required': True, 'editable': False,
                  'name_editable': False, 'filt': True},
                 {'name': self.dateField, 'required': True, 'editable': False,
                  'name_editable': False},
                 {'name': 'Import Date', 'required': True, 'editable': False,
                  'name_editable': False},
                 {'name': 'Hash', 'required': True, 'editable': False,
                  'name_editable': False, 'hidden': True},
                 {'name': 'FileId', 'required': False, 'editable': False,
                  'name_editable': False, 'hidden': True},
                 {'name': 'Directory', 'required': True, 'editable': False,
                  'name_editable': False}]
        for f in fdict:
            fields.append(FieldObject(**f))
        self._defaultFields = fields
        self._fields = fields

    def insertField(self, index=None, name=None):
        """ Insert a new field

        Arguments:
            index (int): (Defaults to end) The index at which to insert the
                field
            name (str): The name of the field
        """
        new_field = None
        # Check inputs
        if isinstance(name, FieldObject):
            new_field = name
            name = new_field.name
        if index is None:
            index = len(self._fields)

        # Create field name if none given
        if name is None:
            name = 'Tag Field {}'.format(self._am_counter)
            self._am_counter += 1

        # Check for duplicate field
        if name in self.field_names:
            raise ValueError('duplicate column name: {}'.format(name))

        # Create the new field object
        if new_field is None:
            new_field = FieldObject(name)

        # Insert the new field
        self._fields.insert(index, new_field)
        for entry in self._entries:
            entry[self._fields[index]] = ''

    def removeField(self, idx, force=False):
        name = self._fields[idx]
        if name.required and (not force):
            raise AlbumError('Cannot remove required field')
        else:
            self._fields.pop(idx)
            for entry in self:
                entry.removeField(name)

    @property
    def defaultFields(self):
        return self._defaultFields

    @property
    def fields(self):
        return self._fields

    @property
    def field_names(self):
        return [f.name for f in self._fields]


class AlbumError(BaseException):
    pass


if __name__ == "__main__":
    import unittest

    class PhotoTests(unittest.TestCase):

        def setUp(self):
            self.empty = Photo()
            self.field = FieldObject('Field1')
            self.field2 = FieldObject('Field2')
            self.field3 = FieldObject('IntField')
            self.dateField = FieldObject('Date')
            self.photo = Photo([self.field, self.field2, self.field3, self.dateField],
                               ['meta1', 'meta2', 1, '2017:01:01 00:00:01'])

        def test_constructor(self):
            self.assertRaises(AssertionError, Photo, ['field1', 'field2'])
            self.assertRaises(AssertionError, Photo, 'joe')

            self.assertEqual(self.empty.keys(), [])
            self.assertEqual(self.photo[self.field], 'meta1')
#             self.assertRaises(AssertionError, Photo, [self.field], [1])

        def test_removeField(self):
            self.photo.removeField(self.field)
            self.assertEqual(len(self.photo.keys()), 3)
            self.assertEqual(self.photo[self.field2], 'meta2')

        def test_getItem(self):
            self.assertEqual(self.photo['Field1'], 'meta1')

        def test_date(self):
            self.assertEqual(self.photo.datetime, datetime(2017, 1, 1, 0, 0, 1))

    class AlbumTest(unittest.TestCase):

        def setUp(self):
            self.emptyAlbum = Album()
            emptyvalues = [None]*len(self.emptyAlbum.fields)
            self.fields = ['int', 'str', 'bool']
            self.values = [emptyvalues + [1, 'a', True],
                           emptyvalues + [2, 'b', False]]
            self.Album = Album(self.fields, self.values)

        def test_constructor(self):
            Album(self.fields)

        def test_delete(self):
            del self.Album[0]
            self.assertEqual(len(self.Album), 1)

        def test_getitem(self):
            intField = self.Album.fields['int']
            self.assertEqual(self.Album[0][intField], 1)
            strField = self.Album.fields['str']
            self.assertEqual(self.Album[1, strField], 'b')

        def test_insert(self):
            emptyvalues = [None]*len(self.emptyAlbum.fields)
            photo = Photo(self.Album.fields, emptyvalues + [3, 'c', False])
            strField = self.Album.fields['str']
            self.Album.insert(1, photo)
            self.assertEqual(self.Album[1, strField], 'c')

        def test_duplicateField(self):
            dupfield = [FieldObject('Tagged', editor=3),
                        FieldObject('Hash', hidden=False),
                        FieldObject('Tags')]
            album = Album(FieldObjectContainer(dupfield))
            self.assertEqual(album.fields['Tagged'].editor, 3)
            self.assertEqual(album.fields['Hash'].hidden, False)
            self.assertEqual(album.fields['Tags'].editor, 0)

    unittest.main()
