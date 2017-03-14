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
        filt (bool): (False) Whether or not to apply the regex filter to this
            field
        tags (bool): (False) Whether or not the field contains tags
    """

    # Editor Enumeration
    LineEditEditor = 0
    ComboBoxEditor = 1
    CheckBoxEditor = 2
    DateEditEditor = 3

    def __init__(self, name, required=False, editor=LineEditEditor,
                 editable=True, name_editable=True, hidden=False,
                 filt=False, tags=False):
        self._name = name
        self.required = required
        self._editor = editor
        self._editable = editable
        self._hidden = hidden
        self.name_editable = name_editable
        self.filter = filt
        self.tags = tags

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

    If fields is given as a list of FieldObjects, all other inputs are assumed
    to be defined within the FieldObjects already and are therefore ignored.

    Constructor Arguments:
        name (list[str], list[FieldObj]): ([]) A list of field objects or
            field names
        required (list[bool]): ([False]) A list indicating whether each field
            is required
        editor (list[FieldObject.EditorType]): A list containing the type of
            editor for each field. Use FieldObject.<editor type>
        editable (list[bool]): ([True]) A list indicating whether each field is
            editable or not
        name_editable (list[bool]): ([True]) A list indicating whether each
            field name is editable
        hidden (list[bool]): ([False]) A list indicating whether each field is
            hidden
        filt (list[bool]): ([False]) A list indicating whether each field
            should be included in the regex filter
        tags (list[bool]): (False) Whether or not the field contains tags
    """

    # Define a list of properties for use when storing to database
    # In the future, this could be used with **kwargs and a simpler way of
    # Assigning properties
    # Keys are database columns, values are field property names
    fieldProps = {'Name': 'name', 'Required': 'required', 'Editor': 'editor',
                  'Editable': 'editable', 'Name_Editable': 'name_editable',
                  'Hidden': 'hidden', 'Filt': 'filter', 'Tags': 'tags'}

    def __init__(self, name=None, required=None, editor=None,
                 editable=None, name_editable=None, hidden=None,
                 filt=None, tags=None):
        def makeBool(lst):
            if lst is not None:
                return [bool(k) for k in lst]
        if name is None:
            self._fieldobjs = []
        else:
            # Make sure all fields are of the same type
            all_objs = [isinstance(k, FieldObject)
                        for k in name]
            all_str = [isinstance(k, basestring) for k in name]
            if all(all_str):
                # Create field objects from string inputs
                nfields = len(name)
                editor = editor or [None]*nfields
                required = makeBool(required) or [False]*nfields
                editable = makeBool(editable) or [True]*nfields
                name_editable = makeBool(name_editable) or [True]*nfields
                hidden = makeBool(hidden) or [False]*nfields
                filts = makeBool(filt) or [False]*nfields
                tags = makeBool(tags) or [False]*nfields
                inputs = zip(name, required, editor, editable,
                             name_editable, hidden, filts, tags)
                self._fieldobjs = [FieldObject(*args) for args in inputs]
            elif all(all_objs):
                # Store the input list
                self._fieldobjs = name
            else:
                raise TypeError('Input fields must all be either '
                                'FieldObject instances or strings')

    def __add__(self, other):
        assert(isinstance(other, FieldObjectContainer))
        assert(all([isinstance(k, FieldObject) for k in other]))
        return self._fieldobjs + other._fieldobjs

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

    def insert(self, index, value, **kwargs):
        """ Insert a new field

        Arguments:
            index (int)
            value (FieldObject, object): If anything other than a Field Object
                is given, its str is used as the field name and all other
                properties are let default.
        """
        if issubclass(value.__class__, FieldObject):
            self._fieldobjs.insert(index, value)
        else:
            self._fieldobjs.insert(index, FieldObject(str(value), **kwargs))

    def append(self, value, **kwargs):
        """ Append a new field

        Arguments:
            value (FieldObject, obj): The FieldObject to append. If anything
                other than a FieldObject is given, its str is used as the field
                name and all other properties are left default.
        """
        if issubclass(value.__class__, FieldObject):
            self._fieldobjs.append(value)
        else:
            self._fieldobjs.append(FieldObject(str(value), **kwargs)) #Need to document

    def extend(self, values):
        MutableSequence.extend(self._fieldobjs, values)

    def index(self, value):
        """ Return the index of the given field

         Argument:
             index (str, FieldObject)
         """
        if isinstance(value, basestring):
            return self.names.index(value)
        else:
            return self._fieldobjs.index(value)

    def remove(self, value):
        if isinstance(value, basestring):
            value = self[value]
        self._fieldobjs.remove(value)

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

        def test_add_extend(self):
            tagfield = FieldObject('Tags', filt=True)
            self.container1.extend(FieldObjectContainer([tagfield]))
            self.assertEqual(self.container1[-1], tagfield)
            tmp = self.container2 + FieldObjectContainer([tagfield])
            self.assertEqual(tmp[-1], tagfield)


    unittest.main()
