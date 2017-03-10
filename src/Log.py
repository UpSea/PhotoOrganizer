#!/usr/bin/python
# Original Author: Lucas McNinch
# Original Creation Date: 2014/11/04

from PyQt4 import QtGui, QtCore
import sys
import os
from UIFiles import Ui_ConsoleDisplay as uiclassf
from shared import __release__
from datetime import datetime
import subprocess


class EmittingStream(QtCore.QObject):
    """ Used to redirect the stdout or stderr streams via Qt signal """
    textWritten = QtCore.pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))


class LogWindow(QtGui.QDialog, uiclassf):
    """ A Text Edit window that redirects stdout and stderr for frozen
    applications without a console
    """

    isSet = False

    def __init__(self, logfile, parent=None):
        super(LogWindow, self).__init__(parent)
        self.setupUi(self)
        # Remove help button from title bar
        self.setWindowFlags(self.windowFlags() |
                            QtCore.Qt.WindowMinimizeButtonHint &
                            ~QtCore.Qt.WindowContextHelpButtonHint)

        self._newline = True
        self._logfile = logfile
        self._loglimit = 5000
        self.cleanupLogfile()

        # Signal Connections
        self.buttonOpenLog.clicked.connect(self.openLogSlot)

    def cleanupLogfile(self):
        """ Removes lines from the beginning of the log file to maintain a
        maximum file size """
        if os.path.exists(self._logfile):
            size = os.path.getsize(self._logfile)
            if size > self._loglimit:
                with open(self._logfile, 'r') as fid:
                    lines = fid.read().split('\n')
                with open(self._logfile, 'w') as fid:
                    fid.write('\n'.join(lines[-self._loglimit:]))
        # Create the file if it doesn't exist and indicate the new session
        r = __release__
        self.writeStdOut('--- New Photo Organizer {} Session ---\n'.format(r))
        self.textEdit.clear()

    def showAndRestore(self):
        """Show the dialog and restore if minimized"""
        self.show()
        self.setWindowState(QtCore.Qt.WindowActive)

    def setupOutput(self):
        """Redirects stdout and stderr"""
        if not self.isSet:
            sys.stdout = EmittingStream(textWritten=self.writeStdOut)
            sys.stderr = EmittingStream(textWritten=self.writeStdErr)
            self.isSet = True

    def resetOutput(self):
        """Resets stdout and stderr"""
        if self.isSet:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            self.isSet = False

    def writeStdOut(self, text):
        """Slot for stdout redirection"""
        self.writeStd(text, QtGui.QColor(190, 190, 190))

    def writeStdErr(self, text):
        """Slot for stderr redirection"""
        self.writeStd(text, QtGui.QColor('red'))

    def writeStd(self, text, color):
        """Write log info"""
        cursor = self.textEdit.textCursor()
        fmat = cursor.charFormat()
        fmat.setForeground(color)
        cursor.movePosition(QtGui.QTextCursor.End)
        with open(self._logfile, 'a') as fid:
            if self._newline:
                line = '{}: '.format(datetime.now())
                cursor.insertText(line, fmat)
                fid.write(line)
            cursor.insertText(text, fmat)
            fid.write(text)
        self._newline = text[-1] == '\n' if text else False
        self.textEdit.setTextCursor(cursor)
        self.textEdit.ensureCursorVisible()

    def openLogSlot(self):
        """Opens the log file"""
        subprocess.Popen('notepad "{}"'.format(self._logfile))

if __name__ == "__main__":
    app = QtGui.QApplication([])
    dlg = LogWindow('POLog.log')
    dlg.setupOutput()
    dlg.show()

    app.exec_()
