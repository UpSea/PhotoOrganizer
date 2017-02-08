# Original Author: Lucas McNinch
# Original Creation Date: 2017/02/06

from collections import MutableSequence

# Handle python versions
import sys
if sys.version_info < (3,):
    strobj = basestring
else:
    strobj = str


class FieldObject(object):
    """ An object used as a field key for a container dictionary

    Constructor Arguments:
        name (str):  The field name (how it will be displayed)
        required (bool):  (False) Whether or not the field is required
        editor (int):  The type of editor used for the field
        editable (bool):  (True) Whether or not the field is editable
        name_editable (bool):  (True) Whether or not the field name is editable
        hidden (bool):  (False) Whether or not the field is hidden
    """

    # Editor Enumeration
    LineEditEditor = 0
    ComboBoxEditor = 1
    CheckBoxEditor = 2
    DateEditEditor = 3

    def __init__(self, name, required=False, editor=LineEditEditor,
                 editable=True, name_editable=True, hidden=False, typ=str):
        self._name = name
        self.required = required
        self._editor = editor
        self._editable = editable
        self._hidden = hidden
        self.name_editable = name_editable
        self.type = typ

    def __repr__(self):
        return '<FieldObject: %s>' % self.name

    def __str__(self):
        return str(self.name)

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, value):
        self._editable = value

    @property
    def editor(self):
        return self._editor

    @editor.setter
    def editor(self, value):
        self._editor = value

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        self._hidden = bool(value)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        if self.name_editable:
            self._name = value
        else:
            raise ValueError("The name of this object cannot be set")


class FieldObjectContainer(MutableSequence):
    """ A container for field objects

    Constructor Arguments:
        fieldobjs (list[str], list[FieldObj]): ([]) A list of field objects or
            field names
        types (list[type]):  (Optional) A type for each field. Default type is
            str
    """

    def __init__(self, fieldobjs=None, types=None):
        if fieldobjs is None:
            self._fieldobjs = []
        else:
            all_objs = [isinstance(k, FieldObject)
                        for k in fieldobjs]
            all_str = [isinstance(k, str) for k in fieldobjs]
            if all(all_str):
                types = types or [str]*len(fieldobjs)
                self._fieldobjs = [FieldObject(k, typ=t) for k, t in
                                   zip(fieldobjs, types)]
            elif all(all_objs):
                self._fieldobjs = fieldobjs
            else:
                raise TypeError('Input fields must all be either '
                                'FieldObject instances or strings')

    def __getitem__(self, key):
        if issubclass(key.__class__, FieldObject):
            key = key.name
        if isinstance(key, strobj):
            for k in self._fieldobjs:
                if k.name == key:
                    return k
        else:
            return self._fieldobjs[key]

    def __setitem__(self, key, value):
        if isinstance(value, FieldObject):
            self._fieldobjs[key] = value
        else:
            self._fieldobjs[key] = FieldObject(str(value))

    def __delitem__(self, key):
        del self._fieldobjs[key]

    def __len__(self):
        return len(self._fieldobjs)

    def __repr__(self):
        str_list = [str(k) for k in self._fieldobjs]
        x = ', '.join(str_list)
        return ('[' + x + ']')

    def insert(self, index, value):
        """ Insert a new field

        Arguments:
            index (int)
            value (FieldObject, object): If an object is given, its str is used
                as the field name
        """
        if issubclass(value.__class__, FieldObject):
            self._fieldobjs.insert(index, value)
        else:
            self._fieldobjs.insert(index, FieldObject(str(value)))

    def index(self, value):
        """ Return the index of the given field

         Argument:
             index (str, FieldObject)
         """
        if isinstance(value, str):
            return self.names.index(value)
        else:
            return self._fieldobjs.index(value)

    @property
    def names(self):
        return [k.name for k in self._fieldobjs]


if __name__ == "__main__":
    import unittest

    class FieldObjectTests(unittest.TestCase):

        def setUp(self):
            self.field1 = FieldObject('field1')
            self.field2 = FieldObject('field2', editable=False,
                                      name_editable=False)
            self.container1 = FieldObjectContainer([self.field1, self.field2])
            self.container2 = FieldObjectContainer(['str1', 'str2'])

        def test_equals(self):
            self.assertTrue(self.field1 == self.field1)
            self.assertFalse(self.field1 == self.field2)

        def test_nequals(self):
            self.assertTrue(self.field1 != self.field2)
            self.assertFalse(self.field1 != self.field1)

        def test_exceptions(self):
            self.field1.name = 'newName'
            self.assertEqual(self.field1.name, 'newName')
            self.assertRaises(ValueError, setattr, self.field2, 'name', 'j')

        def test_container_construction(self):
            goodFields = [self.field1, self.field2]
            goodStrs = ['str1', 'str2']
            badField1 = ['str', self.field2]
            FieldObjectContainer(goodFields)
            FieldObjectContainer(goodStrs)
            self.assertRaises(TypeError, FieldObjectContainer, badField1)

        def test_getter(self):
            self.assertEqual(self.container1[0], self.field1)
            self.assertEqual(self.container1['field1'], self.field1)
            self.assertEqual(self.container1[self.field1], self.field1)

        def test_setter(self):
            newfield = FieldObject('newfield')
            self.container1[1] = newfield
            self.assertEqual(self.container1[0], self.field1)
            self.assertEqual(self.container1['newfield'], newfield)
            self.assertRaises(TypeError, self.container2['str1'])

        def test_deleter(self):
            del self.container1[0]
            self.assertEqual(self.container1[0], self.field2)
            self.assertEqual(len(self.container1), 1)

        def test_insert(self):
            self.container2.insert(1, self.field1)
            self.assertEqual(self.container2['field1'], self.field1)
            self.assertEqual(len(self.container2), 3)

        def test_index(self):
            self.assertEqual(self.container1.index(self.field2), 1)
            self.assertEqual(self.container1.index('field1'), 0)

    unittest.main()
