from PyQt4 import QtCore, QtGui
from UIFiles import Ui_BatchTag as batchTag_form


class BatchTag(QtGui.QDialog, batchTag_form):
    """ A dialog box for adding tags to a batch of photos

    Arguments:
        db (PhotoDatabase): (None) The database from which to acquire the tag
            list
    """

    def __init__(self, db=None, parent=None):
        super(BatchTag, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Batch Tag')

        # Remove help button from title bar
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint) |
                            QtCore.Qt.WindowTitleHint &~
                            QtCore.Qt.WindowCloseButtonHint)

        self.label.setText('Select Tags to Add to Selected Photos\n'
                           'Double Click <New ...> to create a new tag')
        self.treeView.setMode(self.treeView.TagMode)
        self.setDb(db)
        self.treeView.expandAll()

        # Set up signals
        self.checkMarkTagged.stateChanged.connect(self.on_markTagged)
        self.checkUnmarkTagged.stateChanged.connect(self.on_unmarkTagged)

    def on_markTagged(self, state):
        if state:
            self.checkUnmarkTagged.setChecked(QtCore.Qt.Unchecked)

    def on_unmarkTagged(self, state):
        if state:
            self.checkMarkTagged.setChecked(QtCore.Qt.Unchecked)

    def setDb(self, db):
        """ Set the Tag List's database

        Arguments:
            db (PhotoDatabase): The database from which to acquire the tag list
        """
        self.treeView.setDb(db)


if __name__ == "__main__":
    from datastore import PhotoDatabase
    app = QtGui.QApplication([])
    dbfile = 'Fresh.pdb'
    db = PhotoDatabase(dbfile)

    dlg = BatchTag(db)
    out = dlg.exec_()
    print out
    print dlg.treeView.getCheckedTagDict()
