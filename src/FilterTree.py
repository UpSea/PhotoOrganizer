from PyQt4 import QtCore, QtGui
from datastore import PhotoDatabase
import pdb


class TagTreeView(QtGui.QTreeView):
    """ A Tree View for Tags

    This view has 2 modes. FilterMode and TagMode. In FilterMode, the tag list
    is not editable and checking an item will filter the remaining tags. To
    detect changes and apply filters to other views, connect to
    TagTreeView.model().sourceModel().dataChanged.
    """

    FilterMode = 1
    TagMode = 2
    EditMode = 3

    def __init__(self, parent=None, mode=FilterMode):
        super(TagTreeView, self).__init__(parent)
        self.db = None
        self.con = None

        # Set up the model
        model = TagItemModel()
        proxy = TagFilterProxyModel(parent=self)
        proxy.setSourceModel(model)
        proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.setModel(proxy)
        model.sigNewTag.connect(self.on_newTag)

        # Set Mode
        self._mode = mode

    def __del__(self):
        """ Re-implemented to ensure the database connection is closed """
        if self.con:
            self.con.close()

    def addEmptyTag(self, cat):
        """ Add an editable empty tag for new tags creation

        Arguments:
            cat (QStandardItem, int): The category to add the tag to. This can
                be either the category model item itself, or the category Id
        """
        # Get the parent item
        if isinstance(cat, QtGui.QStandardItem):
            parent = cat
        else:
            parent = self.sourceModel.catItemById(cat)

        Qt = QtCore.Qt
        # Create the new tag item and append parent
        child = QtGui.QStandardItem('<New {}>'.format(parent.text()))
        child.id = None
        child.tag = None
        child.setFlags(Qt.ItemIsEnabled | Qt.ItemIsEditable)
        parent.appendRow(child)

    def addField(self, catId, catValue):
        """ Add a category item. Return the category item

        Arguments:
            catId (int)
            catValue (str): The name of the category
        """
        model = self.sourceModel
        parent = QtGui.QStandardItem(catValue)
        parent.id = catId
        model.appendRow(parent)
        self.model().sort(0)
        return parent

    def addTag(self, cat, tagId, tagValue, cnt=None):
        """ Add a tag item to the given category item

        Arguments:
            cat (QStandardItem, int): The category to add the tag to. This can
                be either the category model item itself, or the category Id
            tagId (int): The ID of the tag to add
            tagValue (str): The tag value to add
            cnt (int)
        """
        # Get the parent item
        if isinstance(cat, QtGui.QStandardItem):
            parent = cat
        else:
            parent = self.sourceModel.catItemById(cat)

        # Create the new tag item and append parent
        if cnt is not None and self.mode == self.EditMode:
            val = '%s (%d)' % (tagValue, cnt)
        else:
            val = tagValue
        child = QtGui.QStandardItem(val)
        child.id = tagId
        child.tag = tagValue
        flags = child.flags()
        if self.mode not in (self.EditMode,):
            flags |= QtCore.Qt.ItemIsUserCheckable
        child.setFlags(flags)
        if self.mode not in (self.EditMode,):
            child.setCheckState(QtCore.Qt.Unchecked)
        child.setEditable(False)
        parent.appendRow(child)

    def checkFileTags(self, fileId):
        """ Set the check state of all tags for the given file

        Arguments:
            fileId (int): The database file id of the file to check
        """
        if isinstance(fileId, int):
            fileId = [fileId]
        numfiles = len(fileId)
        # Get the tags from the database.
        tagIds = [id for k in fileId for id in self.db.tagsByFileId(k)]
        # Loop over each tag in each field in the list and set the check state
        # to match the database.
        for f in range(self.sourceModel.rowCount()):
            field = self.sourceModel.item(f)
            for p in range(field.rowCount()):
                fileItem = field.child(p)
                thisid = fileItem.id
                if tagIds.count(thisid) == numfiles:
                    fileItem.setCheckState(QtCore.Qt.Checked)
                elif fileItem.id in tagIds:
                    fileItem.setCheckState(QtCore.Qt.PartiallyChecked)
                elif fileItem.id is not None:
                    fileItem.setCheckState(QtCore.Qt.Unchecked)

    def dropField(self, name):
        """ Drop a field from the tree model """
        item = self.sourceModel.findItems(name)
        if len(item) != 1:
            msg = '{} fields with name {} found'
            raise ValueError(msg.format(len(item), name))
        self.sourceModel.removeRow(item[0].row())

    def getCheckedTagDict(self, checkState=QtCore.Qt.Checked, lower=False):
        """ Return a dictionary containing the checked tags as field/[tag]

        Arguments:
            checkState (Qt.CheckState): (Checked) The desired check state of
                output tags
            lower (bool): (False) Whether or not all output tags should be
                lower case
        """
        model = self.sourceModel
        # Get the items
        items = model.getItemsByCheckState(checkState)
        # Loop through all items and create the output dictionary
        out = {}
        for item in items:
            itemText = str(item.tag)
            fieldName = str(item.parent().text())
            if fieldName in out:
                out[fieldName].append(itemText)
            else:
                out[fieldName] = [itemText]

        if lower:
            out = {k: [c.lower() for c in v] for k, v in out.iteritems()}
        return out

    def getCheckedTagNames(self, lower=False):
        """ Return the tag name for each checked tag

        Arguments:
            lower (bool): (False) If True, the returned names will be lower
        """
        names = self.sourceModel.getCheckedTagNames()
        if lower:
            names = [k.lower() for k in names]
        return names

    def setMode(self, mode):
        """ Set the mode of the tree view

        Arguments:
            mode (int): TagTreeView.FilterMode or .Tag Mode
        """
        self._mode = mode

    def setDb(self, db):
        """ Set the database object

        Arguments:
            db (PhotoDatabase)
        """
        self.db = db
        self.db.databaseChanged.connect(self.updateTree)
        self.newConnection()

    def uncheckAll(self):
        """ Uncheck all items """
        model = self.sourceModel
        for p in range(model.rowCount()):
            parent = model.item(p)
            for c in range(parent.rowCount()):
                child = parent.child(c)
                child.setCheckState(False)

    @QtCore.pyqtSlot()
    def updateTree(self):
        """ Query the database for fields and update the tree"""
        con = self.con
        # Get the fields and tags
        catQ = 'SELECT FieldId, Name FROM TagFields'
        cats = con.execute(catQ).fetchall()
        cd = {c[1]: c[0] for c in cats}

        tagQ = ('SELECT t.TagId, Value, COUNT(tm.FilId) from Tags as t '
                'LEFT OUTER JOIN TagMap as tm '
                'ON t.TagId == tm.TagId WHERE FieldId == ? '
                'GROUP BY t.TagId')
        tags = {cat[1]: [k for k in con.execute(tagQ, (cat[0],))]
                for cat in cats}

        # Get the fields already in the tree
        model = self.sourceModel
        alreadyFields = [str(model.item(r).text()).lower() for r in range(model.rowCount())]

        # Remove deleted fields
        currentFields = [c[1].lower() for c in cats]
        for k in range(len(alreadyFields)-1, -1, -1):
            oldTag = alreadyFields[k]
            if oldTag not in currentFields:
                model.removeRow(k)

        # Create the items and add to model
        for cat in tags.keys():
            if cat.lower() in alreadyFields:
                parent = model.findItems(cat, QtCore.Qt.MatchFixedString)
                if len(parent) != 1:
                    msg = '{} tag fields names {} found'
                    raise ValueError(msg.format(len(parent), cat))
                parent = parent[0]
                alreadyTags = [str(parent.child(r).tag).lower()
                               for r in range(parent.rowCount())]

                # Remove deleted tags
                currentTags = [k[1].lower() for k in tags[cat]]
                for k in range(len(alreadyTags)-1, -1, -1):
                    oldTag = alreadyTags[k]
                    if oldTag not in currentTags:
                        parent.removeRow(k)
            else:
                # Add the new field
                parent = self.addField(cd[cat], cat)
                alreadyTags = []

            # Add new tags
            for tag in tags[cat]:
                if tag[1].lower() not in alreadyTags:
                    self.addTag(parent, *tag)
            self.addEmptyTag(parent)

        self.model().sort(0)

    @QtCore.pyqtSlot()
    def newConnection(self):
        """ Create and store a new database connection

        Slot for the database object's newConnection signal
        """
        self.con = self.db.connect()
        if self.con:
            self.sourceModel.con = self.con
            self.updateTree()

    @QtCore.pyqtSlot(int, str)
    def on_newTag(self, fieldId, name):
        """ Add a new tag

        Slot for the model's sigNewTag signal

        Arguments:
            fieldId (int): The field id for the field to which the new tag
                belongs
            name (str): The name of the new tag
        """
        ids = self.db.insertTags([fieldId], [str(name)])
        if ids:
            self.updateTree()
            item = self.sourceModel.itemById(ids[0], fieldId)
        else:
            item = self.sourceModel.itemByText(str(name), fieldId)

        if self.mode not in (self.EditMode,):
            item.setCheckState(QtCore.Qt.Checked)

    @property
    def mode(self):
        return self._mode

    @property
    def sourceModel(self):
        return self.model().sourceModel()


class TagItemModel(QtGui.QStandardItemModel):
    """ A Standard Item Model for Photo Tags """

    sigNewTag = QtCore.pyqtSignal(int, str)

    def __init__(self, con=None, parent=None):
        super(TagItemModel, self).__init__(parent)
        self.con = con

    def catIds(self):
        """ Return a list of category ids """
        return [self.item(k).id for k in range(self.rowCount())]

    def catItemById(self, catId):
        """ Get a category item by its id

        Arguments:
            catId (int)
        """
        return self.item(self.catIds().index(catId))

    def itemById(self, Id, fieldId):
        """ Return the item for the given tag

        Arguments:
            Id (int): The tag id
            fieldId (int): The id of the field that contains the tag
        """
        parent = self.catItemById(fieldId)
        itemIds = [parent.child(k).id for k in range(parent.rowCount())]
        return parent.child(itemIds.index(Id))

    def itemByText(self, tagName, fieldId):
        """ Return the item with the given name in the given field

        Arguments:
            tagName (str): The name of the tag
            fielId (int): The id of the field that contains the tag
        """
        parent = self.catItemById(fieldId)
        itemText = [str(parent.child(k).tag).lower()
                    for k in range(parent.rowCount())]
        return parent.child(itemText.index(tagName.lower()))

    def getCheckedItems(self):
        """ Return the checked QStandardItems """
        return self.getItemsByCheckState(QtCore.Qt.Checked)

    def getPartiallyCheckedItems(self):
        """ Return the partially checked QStandardItems """
        return self.getItemsByCheckState(QtCore.Qt.PartiallyChecked)

    def getUncheckedItems(self):
        """ Return the unchecked QStandardItems """
        return self.getItemsByCheckState(QtCore.Qt.Unchecked)

    def getItemsByCheckState(self, checkState):
        """ Return the QStandardItems with the given checkState"""
        checkedTags = []
        for catDex in range(self.rowCount()):
            catItem = self.item(catDex)
            for tagDex in range(catItem.rowCount()):
                tagItem = catItem.child(tagDex)
                if tagItem.checkState() == checkState:
                    checkedTags.append(tagItem)
        return checkedTags

    def getCheckedTagIds(self):
        """ Return the tag ids for each checked tag """
        return [str(k.id) for k in self.getCheckedItems()]

    def getCheckedTagNames(self):
        """ Return the tag name for each checked tag """
        return [str(k.tag) for k in self.getCheckedItems()]

    def getFilteredTags(self, catId):
        """ Return the filtered tag ids for any tags in the given category

        Filter criteria is any tag that is associated with any file in the
        current filter set.

        Return None if there are no checked tags
        """
        con = self.con
        # Get the checked tag IDs
        checkedTags = self.getCheckedTagIds()
        if checkedTags:
            # Query for filtered tags
            tagstr = ','.join(['?']*len(checkedTags))
            # This query finds how many of the given tags are associated with
            # each file that has any of the tags. Those file ids are then used
            # to narrow the search for tag ids for a given field
            # I'm not sure I'm explaining that well
            sel = ('SELECT TagId, count(*) as cnt FROM AllTags '+
                   'WHERE FieldId == ? '+
                   'AND FilId in (SELECT FilId FROM '+
                   '(SELECT FilId, count(FilId) as cnt FROM TagMap '+
                   'WHERE TagId in ({}) '+
                   'GROUP BY FilId) '+
                   'WHERE cnt == ?) GROUP BY TagId')
            params = [catId] + checkedTags + [len(checkedTags)]
            res = con.execute(sel.format(tagstr), params).fetchall()
            return map(int, checkedTags) + map(lambda x: x[0], res)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """ Reimplemented to handle the empty tag used to create new tags """
        item = self.itemFromIndex(index)
        # ID of "Empty" tag is None
        if item.id is None:
            # Emit the new tag signal if the user changed the field
            strVal = str(value.toPyObject())
            if strVal != '' and strVal != item.text():
                parent = item.parent()
                catId = parent.id
                self.sigNewTag.emit(catId, strVal)
            return True
        return super(TagItemModel, self).setData(index, value, role)


class TagFilterProxyModel(QtGui.QSortFilterProxyModel):
    """ A proxy model to filter the Tag Tree View based on selections """

    def __init__(self, parent=None):
        super(TagFilterProxyModel, self).__init__(parent)

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """ Re-implemented to apply the row filter

        Arguments:
            sourceRow (int): The row in question
            sourceParent (QModelIndex): The index of the row's parent.
        """
        # Don't filter in Tag Mode
        if self.parent().mode in (TagTreeView.TagMode, TagTreeView.EditMode):
            return True

        # Always accept parent items
        if not sourceParent.isValid():
            return True

        # Get the tag IDs to accept from the database for the given category
        cat = self.sourceModel().itemFromIndex(sourceParent)
        catId = cat.id
        acceptIds = self.sourceModel().getFilteredTags(catId)

        # Don't accept the empty row in Filter Mode
        item = cat.child(sourceRow)
        if item.id is None:
            return False

        # Accept or don't
        if acceptIds is None or item.id in acceptIds:
            return True
        return False

    def lessThan(self, leftIndex, rightIndex):
        """ Re-implemented to ensure the "New Tag" item is always at the bottom
        """
        left = self.sourceModel().itemFromIndex(leftIndex)
        right = self.sourceModel().itemFromIndex(rightIndex)
        if left.id is None:
            return False
        if right.id is None:
            return True
        return super(TagFilterProxyModel, self).lessThan(leftIndex, rightIndex)


if __name__ == "__main__":
#     dbfile = '..\\v0.5.pdb'
    dbfile = '..\\Fresh5d.pdb'
    app = QtGui.QApplication([])
    db = PhotoDatabase(dbfile)

#     tree = TagTreeView(mode=TagTreeView.TagMode)
#     tree = TagTreeView(mode=TagTreeView.FilterMode)
    tree = TagTreeView(mode=TagTreeView.EditMode)
    proxy = tree.model()
    model = proxy.sourceModel()
    # Only  needed here. Photo's slot calls invalidate
    model.dataChanged.connect(proxy.invalidate)
    tree.setDb(db)
    tree.header().setVisible(False)

    tree.show()
    tree.resize(QtCore.QSize(370, 675))
    tree.expandAll()
#     tree.checkFileTags(1)
#     app.processEvents()

#     print tree.getCheckedTagDict(lower=True)
#     tree.checkFileTags([1, 3])

#     import time
#     time.sleep(2)
#     tree.dropField('Project')

#     import pdb
#     pdb.set_trace()
#
    app.exec_()
