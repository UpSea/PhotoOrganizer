from PyQt4 import QtCore, QtGui
from UIFiles import Ui_BatchTag as batchTag_form


class BatchTag(QtGui.QDialog, batchTag_form):
    """ A dialog box for adding tags to a batch of photos

    Arguments:
        fields ([str]): (None) A list of field names
    """

    def __init__(self, fields=None, parent=None):
        super(BatchTag, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Batch Tag')

        # Remove help button from title bar
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint) |
                            QtCore.Qt.WindowTitleHint &~
                            QtCore.Qt.WindowCloseButtonHint)

        self.label.setText('Add tags separated by , or ;')
        self.edits = {}

        if fields:
            map(self.addField, fields)

    def addField(self, name):
        """ Add a line edit with the given name

        Arguments:
            name (str): The name of the field
        """
        hlayout = QtGui.QHBoxLayout()
        label = QtGui.QLabel(name)
        hlayout.addWidget(label)
        edit = QtGui.QLineEdit()
        hlayout.addWidget(edit)
        self.layoutEdits.addLayout(hlayout)
        self.edits[name] = edit


if __name__ == "__main__":
    app = QtGui.QApplication([])

    dlg = BatchTag()
    dlg.addField('People', ['Luke', 'Mom', 'Kami', 'Hal', 'Phil'])
    dlg.exec_()
    print dlg.edits['People'].text()
