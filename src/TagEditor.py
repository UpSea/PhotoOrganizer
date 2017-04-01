from PyQt4 import QtCore, QtGui
from UIFiles import Ui_TagEditor


class TagEditor(QtGui.QDialog, Ui_TagEditor):
    """ An dialog for editing tag names """

    def __init__(self, model, parent=None):
        super(TagEditor, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() &
                            (~QtCore.Qt.WindowContextHelpButtonHint))
        self.setWindowTitle('Edit Tags')

        self.model = model

        self.treeView.setMode(self.treeView.EditMode)
        self.treeView.header().setVisible(False)
        self.treeView.setDb(model.dataset)
        self.treeView.expandAll()

        # Signals and slots
        self.buttonRename.clicked.connect(self.on_rename)
        self.buttonDelete.clicked.connect(self.on_delete)

    def getSelectedItem(self):
        """ Return the model item that is selected """
        idx = self.treeView.selectedIndexes()[0]
        proxy = self.treeView.model()
        mi = proxy.mapToSource(idx)
        item = self.treeView.model().sourceModel().itemFromIndex(mi)
        return item

    @QtCore.pyqtSlot()
    def on_delete(self):
        """ Delete the selected tag """
        item = self.getSelectedItem()
        if item.parent() is None:
            # This is a field
            return
        tagId = item.id
        self.model.deleteTag(tagId)

    @QtCore.pyqtSlot()
    def on_rename(self):
        """ Prompt user for new tag name and execute the rename """
        item = self.getSelectedItem()
        if item.parent() is None:
            # This is a field
            return
        tagId = item.id

        name = QtGui.QInputDialog.getText(self, 'Rename Tag', 'New Tag Name',
                                          text=item.tag)[0]
        if not name:
            return
        self.model.renameTag(tagId, str(name))


if __name__ == "__main__":
    from datastore import PhotoDatabase, AlbumModel
    app = QtGui.QApplication([])

    dbfile = '..\\Fresh5d.pdb'
    db = PhotoDatabase(dbfile)
    model = AlbumModel(db)

    win = TagEditor(model)
    win.show()

    app.exec_()
