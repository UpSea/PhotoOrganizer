#!/usr/bin/python
# Original Author: Lucas McNinch
# Original Creation Date: 2014/08/20
from PyQt4 import QtCore, QtGui
from UIFiles import Ui_ConflictDialog


class conflictDialog(QtGui.QDialog, Ui_ConflictDialog):
    """A QMessageBox-like dialog box used to alert users of a conflict or
    series of conflicts. Variable number of buttons can be added, and the
    clicked button is given by clickedButton().

    A checkbox giving the user the option to resolve all conflicts the same way
    can be displayed by setCheckBoxValue(v). If v evaulates False, the checkbox
    is hidden. Check the state of the checkbox by calling checkBox.isChecked().
    """
    def __init__(self, title, parent=None):
        super(conflictDialog, self).__init__(parent)
        self.setupUi(self)
        pal = self.frame.palette()
        pal.setColor(QtGui.QPalette.Background, QtCore.Qt.white)
        self.frame.setPalette(pal)
        self.frame.setAutoFillBackground(True)

        # Remove help button from title bar
        self.setWindowFlags((QtCore.Qt.Dialog |
                             QtCore.Qt.CustomizeWindowHint) |
                            QtCore.Qt.WindowTitleHint &~
                            QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle(title)

        self.buttonBox.clicked.connect(self._storeClickedButton)
        self.buttonCancel.clicked.connect(self._canceled)

        self._checkBoxStatic = 'Do this for the next {} conflicts'
        self.checkBox.setChecked(True)
        self.setCheckBoxValue('')

    def addButton(self, *args):
        """Adds a button to the button box. See docs for QDialogButtonBox"""
        button = self.buttonBox.addButton(*args)
        return button

    def _storeClickedButton(self, button):
        self._clickedButton = button

    def _canceled(self):
        self._storeClickedButton(self.buttonCancel)

    def clickedButton(self):
        """Returns the button that was clicked"""
        return self._clickedButton

    def setText(self, text):
        """Set the notification text of the dialog. This is BOLD."""
        self.text.setText(text)

    def setQuestionText(self, text):
        """Set the question or prompt text"""
        self.questionText.setText(text)

    def setDefaultButton(self, button):
        """Set the default button of the dialog"""
        button.setDefault(True)

    def setCheckBoxValue(self, v):
        """Set the number of conflicts and show the checkbox"""
        if v:
            self.checkBox.setVisible(True)
            self.checkBox.setText(self._checkBoxStatic.format(v))
        else:
            self.checkBox.setVisible(False)


if __name__ == "__main__":
    app = QtGui.QApplication([])
    list_of_conflicts = range(1, 11)
    removed = []
    doAll = False
    msgBox = conflictDialog('Conflict')
    overwriteButton = QtGui.QCommandLinkButton('Move and Replace')
    overwriteButton.setDescription('Replace the file in the destination folder with the file you are moving:')
    msgBox.addButton(overwriteButton, msgBox.buttonBox.AcceptRole)
    skipButton = msgBox.addButton(QtGui.QCommandLinkButton('Skip'),
                                  msgBox.buttonBox.NoRole)
    msgBox.setDefaultButton(msgBox.buttonCancel)
    msgBox.setQuestionText('Do you want to overwrite?')

    for k, f in enumerate(list(list_of_conflicts)):
        remaining = len(list_of_conflicts) - k
        if not doAll:
            msg = 'Conflict: {}!'
            msgBox.setText(msg.format(f))
            if remaining > 1:
                msgBox.setCheckBoxValue(remaining)
            msgBox.checkBox.setChecked(k == 0)
            msgBox.exec_()
            clickedButton = msgBox.clickedButton()
            doAll = msgBox.checkBox.isChecked()
        if clickedButton == skipButton:
            list_of_conflicts.remove(f)
            removed.append(f)
        if clickedButton == msgBox.buttonCancel:
            break
    print 'Kept:', list_of_conflicts
    print 'Removed:', removed
