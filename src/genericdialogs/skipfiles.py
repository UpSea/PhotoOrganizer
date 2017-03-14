#!/usr/bin/python
# Original Author: Lucas McNinch
# Original Creation Date: 2014/08/20
from PyQt4 import QtGui
from conflict import conflictDialog
import os.path


class skipFileDialog(conflictDialog):
    """A QMessageBox-like dialog box used to alert users of a file conflict or
    series of conflicts. Overwrite, skip and cancel buttons are available.

    After execution, if not canceled, the overwrite attribute will indicate
    whether or not skip or overwrite was clicked.
    """

    def __init__(self, title, File, moveType='Copy', parent=None):
        super(skipFileDialog, self).__init__(title, parent)
        self.setQuestionText('Do you want to overwrite?')

        # Add the buttons
        owr = '{} and Replace'.format(moveType)
        self.overwriteButton = QtGui.QCommandLinkButton(owr)
        desc = ('Replace the file in the destination folder with the file '
                'you are moving.')
        self.overwriteButton.setDescription(desc)
        self.addButton(self.overwriteButton, self.buttonBox.AcceptRole)

        skp = "Don't {}".format(moveType)
        self.skipButton = QtGui.QCommandLinkButton(skp)
        self.skipButton.setDescription('No files will be changed. Leave this '
                                       'file in the destination folder.')
        self.addButton(self.skipButton, self.buttonBox.AcceptRole)
        kp = '{}, but keep both files'.format(moveType)
        self.keepButton = QtGui.QCommandLinkButton(kp)
        self.keepButtonDescription = ()
        self.addButton(self.keepButton, self.buttonBox.AcceptRole)
        self.setDefaultButton(self.buttonCancel)

        self._setNewName(File)

        self._overwrite = None
        self._skip = None
        self._keepBoth = None
        self._canceled = None

    def _storeClickedButton(self, button):
        self._overwrite = button is self.overwriteButton
        self._skip = button is self.skipButton
        self._keepBoth = button is self.keepButton
        self._canceled = button is self.buttonCancel
        return super(skipFileDialog, self)._storeClickedButton(button)

    def _setNewName(self, oldfile):
        oldname = os.path.split(oldfile)[1]
        n, e = os.path.splitext(oldname)
        newname_str = '{} ({{}}){}'.format(n, e)
        fnum = 2
        newname = newname_str.format(fnum)
        while os.path.exists(newname):
            fnum += 1
            newname = newname_str.format(fnum)
        desc = 'The file you are copying will be renamed "{}"'
        self.keepButton.setDescription(desc.format(newname))
        self.newName = newname

    @property
    def overwrite(self):
        return self._overwrite

    @property
    def canceled(self):
        return self._canceled

    @property
    def skip(self):
        return self._skip

    @property
    def keep(self):
        return self._keepBoth

if __name__ == "__main__":
    app = QtGui.QApplication([])
    list_of_conflicts = [r'C:\path\file1.txt', r'C:\path\file2.txt', r'C:\path\file3.txt']
    removed = []
    newnames = []
    doAll = False
    for k, f in enumerate(list(list_of_conflicts)):
        remaining = len(list_of_conflicts) - 1
        if not doAll:
            msgBox = skipFileDialog('File(s) Exist', f)
            msg = 'File Exists:\n{}!'
            msgBox.setText(msg.format(f))
            if remaining > 0:
                msgBox.setCheckBoxValue(remaining)
            msgBox.checkBox.setChecked(k == 0)
            msgBox.exec_()
            doAll = msgBox.checkBox.isChecked()
        if msgBox.canceled:
            print 'Canceled'
            break
        if msgBox.skip:
            list_of_conflicts.remove(f)
            removed.append(f)
        if msgBox.keep:
            list_of_conflicts.remove(f)
            newnames.append((f, msgBox.newName))
    if not msgBox.canceled:
        print 'Overwritten:', list_of_conflicts
        print 'Skipped:', removed
        print 'Rename:', newnames
