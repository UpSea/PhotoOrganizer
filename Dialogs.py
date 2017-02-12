from PyQt4 import QtCore, QtGui
from UIFiles import Ui_BatchTag as batchTag_form


class BatchTag(QtGui.QDialog, batchTag_form):
    """ A dialog box for adding tags to a batch of photos """

    def __init__(self, parent=None):
        super(BatchTag, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Batch Tag')

        # Remove help button from title bar
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint) |
                            QtCore.Qt.WindowTitleHint &~
                            QtCore.Qt.WindowCloseButtonHint)

        self.label.setText('Add tags separated by , or ;')


class WarningDialog(QtGui.QDialog):
    """A QMessageBox-like dialog box"""
    def __init__(self, title, parent=None):
        super(WarningDialog, self).__init__(parent)

        # Remove help button from title bar
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint) |
                            QtCore.Qt.WindowTitleHint &~
                            QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)

        verticalLayout = QtGui.QVBoxLayout(self)
        self.text = QtGui.QLabel(self)
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        self.text.setFont(font)
        verticalLayout.addWidget(self.text)

        self.editDetailedText = QtGui.QPlainTextEdit()
        self.editDetailedText.setLineWrapMode(self.editDetailedText.NoWrap)
        self.editDetailedText.setReadOnly(True)
        self.editDetailedText.setVisible(False)
        verticalLayout.addWidget(self.editDetailedText)

        self.editQuestionText = QtGui.QLabel(self)
        verticalLayout.addWidget(self.editQuestionText)

        self.buttonBox = QtGui.QDialogButtonBox(self)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.clicked.connect(self._storeClickedButton)
        verticalLayout.addWidget(self.buttonBox)

    def addButton(self, *args):
        """Adds a button to the button box. See docs for QDialogButtonBox"""
        button = self.buttonBox.addButton(*args)
        button.setCheckable(True)
        return button

    def _storeClickedButton(self, button):
        self._clickedButton = button

    def clickedButton(self):
        return self._clickedButton

    def setStandardButtons(self, *args):
        return self.buttonBox.setStandardButtons(*args)

    def setText(self, text):
        self.text.setText(text)

    def setQuestionText(self, text):
        self.editQuestionText.setText(text)

    def setDetailedText(self, text):
        self.editDetailedText.show()
        self.editDetailedText.setPlainText(text)


def warning_box(msg, parent=None):
    """Raise a modal warning box"""
    message_box = QtGui.QMessageBox(parent)
    message_box.setWindowTitle('Warning')
    message_box.setText(msg)
    message_box.setIcon(QtGui.QMessageBox.Warning)
    message_box.exec_()
