from PyQt4 import QtCore, QtGui
from UIFiles import Ui_TagEditor


class TagEditor(QtGui.QDialog, Ui_TagEditor):
    """ An image viewer """

    def __init__(self, db, parent=None):
        super(TagEditor, self).__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() &
                            (~QtCore.Qt.WindowContextHelpButtonHint))
        self.setWindowTitle('Edit Tags')
        self.buttonDelete.setHidden(True)

        self.db = db

        self.treeView.setMode(self.treeView.EditMode)
        self.treeView.header().setVisible(False)
        self.treeView.setDb(db)
        self.treeView.expandAll()

        # Signals and slots
        self.buttonRename.clicked.connect(self.on_rename)

    @QtCore.pyqtSlot()
    def on_rename(self):
        idx = self.treeView.selectedIndexes()[0]
        proxy = self.treeView.model()
        mi = proxy.mapToSource(idx)
        item = self.treeView.model().sourceModel().itemFromIndex(mi)
        if item.parent() is None:
            # This is a field
            return
        tagId = item.id

        name = QtGui.QInputDialog.getText(self, 'Rename Tag', 'New Tag Name',
                                          text=item.tag)[0]
        if not name:
            return
        self.db.renameTag(tagId, str(name))


if __name__ == "__main__":
    from datastore import PhotoDatabase
    app = QtGui.QApplication([])

    dbfile = '..\\Fresh5d.pdb'
    db = PhotoDatabase(dbfile)

    win = TagEditor(db)
    win.show()

    app.exec_()
