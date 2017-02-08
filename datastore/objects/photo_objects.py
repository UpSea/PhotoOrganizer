from fieldobjects import FieldObject, FieldObjectContainer
from collections import MutableSequence

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
            it should be the same length as values and its contents should have
            the type specified by the corresponding FieldObject
        thumb (PIL.Image):  (Optional) The thumbnail image
        tagged (bool): Whether or not tagging has been completed
    """

    def __init__(self, fields=None, values=None, thumb=None, tagged=False):
        fields = fields or []
        assert isinstance(fields, (list, FieldObjectContainer))
        assert all([isinstance(k, FieldObject) for k in fields])
        values = values or [k.type() for k in fields]
        self.thumb = thumb
        self.tagged = tagged
        assert len(fields) == len(values)

        # Make sure types match
#         assert(all([type(v) == f.type for v, f in zip(values, fields)]))

        super(Photo, self).__init__(zip(fields, values))

    def removeField(self, field):
        del self[field]

    def __repr__(self):
        return '<Photo: %s>' % dict.__repr__(self)


class Album(MutableSequence):
    """A Photo container

    Arguments:
        fields (list[str]):  (Optional) A list of field names
        values (list[list[<>]]: (Optional) A list of lists. Each list is a list
            of objects of the type() defined by the corresponding field. Each
            sublist should be the same length as fields. If types is not
            provided, they must be strings (or will be the str representation
            of what is given)
        types (list[type]):  (Optional) The data type for each field
    """

    def __init__(self, fields=None, values=None, types=None):
        fields = fields or []
        assert isinstance(fields, (list, FieldObjectContainer))
        types = types or [str]*len(fields)
        assert(isinstance(types, list))
        assert(all([isinstance(k, type) for k in types]))

        if isinstance(fields, list):
            fieldobj = FieldObjectContainer(fields, types)
        else:
            fieldobj = fields

        self._fields = fieldobj
        self._entries = []

        values = values or []
        for v in values:
            self._entries.append(Photo(self._fields, v))

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

    @property
    def fields(self):
        return self._fields

    @property
    def field_names(self):
        return [f.name for f in self._fields]


if __name__ == "__main__":
    import unittest

    class PhotoTests(unittest.TestCase):

        def setUp(self):
            self.empty = Photo()
            self.field = FieldObject('Field1')
            self.field2 = FieldObject('Field2')
            self.field3 = FieldObject('IntField', typ=int)
            self.photo = Photo([self.field, self.field2, self.field3],
                               ['meta1', 'meta2', 1])

        def test_constructor(self):
            self.assertRaises(AssertionError, Photo, ['field1', 'field2'])
            self.assertRaises(AssertionError, Photo, 'joe')

            self.assertEqual(self.empty.keys(), [])
            self.assertEqual(self.photo[self.field], 'meta1')
#             self.assertRaises(AssertionError, Photo, [self.field], [1])

        def test_removeField(self):
            self.photo.removeField(self.field)
            self.assertEqual(len(self.photo.keys()), 2)
            self.assertEqual(self.photo[self.field2], 'meta2')

    class AlbumTest(unittest.TestCase):

        def setUp(self):
            self.fields = ['int', 'str', 'bool']
            self.values = [[1, 'a', True], [2, 'b', False]]
            self.types = [int, str, bool]
            self.Album = Album(self.fields, self.values, self.types)

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
            photo = Photo(self.Album.fields, [3, 'c', False])
            strField = self.Album.fields['str']
            self.Album.insert(1, photo)
            self.assertEqual(self.Album[1, strField], 'c')

    unittest.main()
