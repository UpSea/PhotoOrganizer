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

    def setDb(self, db):
        """ Set the Tag List's database

        Arguments:
            db (PhotoDatabase): The database from which to acquire the tag list
        """
        self.treeView.setDb(db)

    def getCheckedTags(self):
        """
        Return a dictionary containing the checked tags as field/[tag]
        """
        checkedItems = self.treeView.getCheckedItems()
        out = {}
        for item in checkedItems:
            field = str(item.parent().text())
            tag = str(item.text())
            if field in out:
                out[field].append(tag)
            else:
                out[field] = [tag]
        return out


if __name__ == "__main__":
    from datastore import PhotoDatabase
    app = QtGui.QApplication([])
    dbfile = 'Fresh.pdb'
    db = PhotoDatabase(dbfile)

    dlg = BatchTag(db)
    out = dlg.exec_()
    print out
    print dlg.getCheckedTags()
