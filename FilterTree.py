from PyQt4 import QtCore, QtGui
from datastore import PhotoDatabase
import pdb


class TagTreeView(QtGui.QTreeView):
    """ A Tree View for Tags """
    def __init__(self, parent=None):
        super(TagTreeView, self).__init__(parent)
        self.db = None
        self.con = None

    def __del__(self):
        """ Re-implemented to ensure the database connection is closed """
        if self.con:
            self.con.close()

    def addField(self, catId, catValue):
        """ Add a category item. Return the category item

        Arguments:
            catId (int)
            catValue (str): The name of the category
        """
        model = self.model().sourceModel()
        parent = QtGui.QStandardItem(catValue)
        parent.id = catId
        model.appendRow(parent)
        self.model().sort(0)
        return parent

    def addTag(self, cat, tagId, tagValue):
        """ Add a tag item to the given category item

        Arguments:
            cat (QStandardItem, int): The category to add the tag to. This can
                be either the category model item itself, or the category Id
            tagId (int): The ID of the tag to add
            tagValue (str): The tag value to add
        """
        # Get the parent item
        if isinstance(cat, QtGui.QStandardItem):
            parent = cat
        else:
            parent = self.model().sourceModel().catItemById(cat)

        # Create the new tag item and append parent
        child = QtGui.QStandardItem(tagValue)
        child.id = tagId
        child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
        child.setCheckState(QtCore.Qt.Unchecked)
        parent.appendRow(child)

    def dropField(self, name):
        """ Drop a field from the tree model """
        item = self.model().sourceModel().findItems(name)
        if len(item) != 1:
            msg = '{} fields with name {} found'
            raise ValueError(msg.format(len(item), name))
        self.model().sourceModel().removeRow(item[0].row())

    def setDb(self, db):
        """ Set the database object

        Arguments:
            db (PhotoDatabase)
        """
        self.db = db
        self.newConnection()

    def uncheckAll(self):
        """ Uncheck all items """
        model = self.model().sourceModel()
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

        tagQ = 'SELECT TagId, Value from Tags WHERE FieldId == ?'
        tags = {cat[1]: [k for k in con.execute(tagQ, (cat[0],))]
                for cat in cats}

        # Get the fields already in the tree
        model = self.model().sourceModel()
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
                alreadyTags = [str(parent.child(r).text()).lower()
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

        self.model().sort(0)

    @QtCore.pyqtSlot()
    def newConnection(self):
        self.con = self.db.connect()
        if self.con:
            self.model().sourceModel().con = self.con
            self.updateTree()


class TagItemModel(QtGui.QStandardItemModel):
    """ A Standard Item Model for Photo Tags """
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

    def getCheckedItems(self):
        """ Return the checked QStandardItems """
        checkedTags = []
        for catDex in range(self.rowCount()):
            catItem = self.item(catDex)
            for tagDex in range(catItem.rowCount()):
                tagItem = catItem.child(tagDex)
                if tagItem.checkState():
                    checkedTags.append(tagItem)
        return checkedTags

    def getCheckedTagIds(self):
        """ Return the tag ids for each checked tag """
        return [str(k.id) for k in self.getCheckedItems()]

    def getCheckedTagNames(self):
        """ Return the tag name for each checked tag """
        return [str(k.text()) for k in self.getCheckedItems()]

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
            sel = ('SELECT distinct(TagId) FROM AllTags '+
                   'WHERE FieldId == ? '+
                   'AND FilId in (SELECT FilId FROM '+
                   '(SELECT FilId, count(FilId) as cnt FROM TagMap '+
                   'WHERE TagId in ({}) '+
                   'GROUP BY FilId) '+
                   'WHERE cnt == ?)')
            params = [catId] + checkedTags + [len(checkedTags)]
            res = con.execute(sel.format(tagstr), params).fetchall()
            return map(lambda x: x[0], res)


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
        # Always accept parent items
        if not sourceParent.isValid():
            return True

        # Get the tag IDs to accept from the database for the given category
        cat = self.sourceModel().item(sourceParent.row())
        catId = cat.id
        acceptIds = self.sourceModel().getFilteredTags(catId)

        # Accept or don't
        if acceptIds is None or cat.child(sourceRow).id in acceptIds:
            return True
        return False

if __name__ == "__main__":
    dbfile = 'v0.2.pdb'
    dbfile = 'FreshTrash.pdb'
    db = PhotoDatabase(dbfile)

    app = QtGui.QApplication([])
    tree = TagTreeView()
    model = TagItemModel()
    proxy = TagFilterProxyModel()
    proxy.setSourceModel(model)
    model.dataChanged.connect(proxy.invalidate)
    tree.setModel(proxy)
    tree.setDb(db)
    tree.populateTree()
    tree.header().setVisible(False)

    tree.show()
    tree.resize(QtCore.QSize(370, 675))
    tree.expandAll()
#     app.processEvents()

#     import time
#     time.sleep(2)
#     tree.dropField('Project')

#     import pdb
#     pdb.set_trace()
#
#     app.exec_()
