from PyQt4 import QtCore, QtGui
from database import PhotoDatabase


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

    def populateTree(self):
        """
        Populate the tree model with tags and categories from the database
        """
        con = self.con
        # Get the categories and tags
        catQ = 'SELECT CatId, Name FROM Categories'
        cats = con.execute(catQ).fetchall()
        cd = {c[1]: c[0] for c in cats}

        tagQ = 'SELECT TagId, Value from Tags WHERE CatId == ?'
        tags = {cat[1]: [k for k in con.execute(tagQ, (cat[0],))]
                for cat in cats}

        # Create the items and add to model
        for cat in sorted(tags.keys()):
            parent = QtGui.QStandardItem(cat)
            parent.id = cd[cat]
            # parent.setFlags(parent.flags() | QtCore.Qt.ItemIsTristate |
                            # QtCore.Qt.ItemIsUserCheckable)
            # parent.setCheckState(0)
            for tag in tags[cat]:
                child = QtGui.QStandardItem(tag[1])
                child.id = tag[0]
                child.setFlags(child.flags() | QtCore.Qt.ItemIsUserCheckable)
                child.setCheckState(QtCore.Qt.Unchecked)
                parent.appendRow(child)
            self.model().sourceModel().appendRow(parent)

    def setDb(self, db):
        """ Set the database object

        Arguments:
            db (PhotoDatabase)
        """
        self.db = db
        self.con = db.connect()
        self.model().sourceModel().con = self.con


class TagItemModel(QtGui.QStandardItemModel):
    """ A Standard Item Model for Photo Tags """
    def __init__(self, con=None, parent=None):
        super(TagItemModel, self).__init__(parent)
        self.con = con

    def getCheckedTagIds(self):
        """ Return the tag ids for each checked tag """
        return [str(k.id) for k in self.getCheckedItems()]

    def getCheckedTagNames(self):
        """ Return the tag name for each checked tag """
        return [str(k.text()) for k in self.getCheckedItems()]

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
            sel = ('SELECT distinct(t.TagId) FROM Tags as t '+
                   'JOIN TagMap as tm ON t.TagId == tm.TagId '+
                   'WHERE t.CatId == ? '+
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

    app.exec_()
