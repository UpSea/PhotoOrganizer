from PyQt4 import QtCore, QtGui
from threading import Event as thread_Event
import sys


class ProgressDialog(QtGui.QDialog):
    """A generic progress dialog box that can be used to monitor the progress
    of an arbitrary number of processes. The processes will be executed in
    separate threads and their progress will be monitored and displayed by
    progress bars in the dialog.

    Arguments:
        -processes    Processes to execute (see specifications below)
        -title        (Optional) A title for the dialog window. Defaults to
                      "Progress"
        -closeDelay   (Optional) The number, of seconds to delay closing
                      after all processes are inactive. -1 if automatic close
                      is not desired.
        -updateDelay  (Optional) The update delay, in milliseconds (defaults to
                      50 ms)
        -parent       (Optional) The parent widget

    The processes must be an object or list of objects that contain the
    following attributes and methods:

        -status     A string that contains the status of the process. This will
                    be displayed above the progress bar, following the label
        -progress   An integer between 0 and 100 indicating the progress of the
                    process
        -active     A threading.Event that indicates whether or not the process
                    is active. Once all process are inactive, the dialog will
                    close.
        -work()     A method that does the work of the process. This will be
        -label      (Optional) A label identifying the process, differentiating
                    it from the other processes. If None or omitted, this part
                    of the status is left out.
        -cancel     A method that cancels the process
    """

    def __init__(self, processes, title=None, closeDelay=-1, updateDelay=50,
                 parent=None):
        super(ProgressDialog, self).__init__(parent)
        if isinstance(processes, list):
            self.processes = processes
        else:
            self.processes = [processes]
        self.closeDelay = closeDelay*1000
        self.updateDelay = updateDelay

        # Remove the context help button (Question mark on title bar)
        self.setWindowTitle(title or 'Progress')
        Qt = QtCore.Qt
        flags = ((Qt.Dialog | Qt.CustomizeWindowHint) | Qt.WindowTitleHint |
                 Qt.WindowCloseButtonHint & ~Qt.WindowContextHelpButtonHint)
        self.setWindowFlags(flags)
        self.setMinimumWidth(500)

        # Create list for threads and threaded objects
        self.rawThreads = []
        self.processThreads = []

        # Set up layout
        self.verticalLayout = QtGui.QVBoxLayout(self)
        self.widgetLayout = QtGui.QVBoxLayout()
        self.verticalLayout.addLayout(self.widgetLayout)
        self.progress_widgets = []
        for process in self.processes:
            label = getattr(process, 'label', None)
            pw = ProgressWidget(label)
            self.widgetLayout.addWidget(pw)
            self.progress_widgets.append(pw)
            self._createThread(process)
        vspace = QtGui.QSpacerItem(10, 10, QtGui.QSizePolicy.Minimum,
                                   QtGui.QSizePolicy.Expanding)
        self.verticalLayout.addItem(vspace)
        self.buttonCancel = QtGui.QPushButton('Cancel')
        self.verticalLayout.addWidget(self.buttonCancel)

        # Connect signals
        self.buttonCancel.clicked.connect(self.cancel)

    def showEvent(self, event):
        """Re-implemented to start the processes and update timer on show()"""
        super(ProgressDialog, self).showEvent(event)
        self._startThreads()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.updateDelay)

    def closeEvent(self, event):
        """Re-implemented to quit the process threads and wait for them to
        exit """
        # Quit the threads and wait for them to die
        for thread in self.rawThreads:
            thread.quit()
            thread.wait(1000)
        # Ensure that they are terminated, in the event of processes with no
        # cancel.
        for thread in self.rawThreads:
            thread.terminate()
        for thread in self.rawThreads:
            thread.wait(500)

    def _createThread(self, process):
        """Creates a thread for the given process"""
        thread = QtCore.QThread()
        self.rawThreads.append(thread)
        threadobj = GenericThread(process.work)
        threadobj.moveToThread(thread)
        threadobj.finished.connect(self.handleThreadOutput)
        threadobj.processError.connect(self.processErrorSlot)
        self.processThreads.append(threadobj)

    def _startThreads(self):
        """Start all the threads"""
        for procThrd in self.processThreads:
            procThrd.thread().start()
            procThrd.dowork.emit()

    def cancel(self):
        """Quit the processes and close the dialog"""
        for p in self.processes:
            if hasattr(p, 'cancel'):
                p.cancel()
        self.close()

    def update(self):
        """Update the progress display

        Makes sure that each process is still running. If so, updates the text
        and progress of the corresponding widget. If not, hides the progress
        bar and show as finished. If all processes are finished, the dialog
        is closed.
        """
        self._updateProgressWidgets()

        if not self.anyactive():
            self._updateProgressWidgets()
            self.timer.stop()
            self.buttonCancel.setText('Close')
            if self.closeDelay >= 0:
                QtCore.QTimer.singleShot(self.closeDelay, self.close)

    def _updateProgressWidgets(self):
        """ Do the work of updating the widgets """
        for dex, process in enumerate(self.processes):
            pw = self.progress_widgets[dex]
            pw.update(process.status, process.progress)
            if not process.active.isSet():
                pw.progress.hide()

    def anyactive(self):
        """Returns True if any process is active"""
        return any([t.active.isSet() for t in self.processes])

    def handleThreadOutput(self, out):
        """Slot for the finished signal of the process.

        Stores the output of the process to results
        """
        self.results = out
        if out:
            print '\nProcess Results:'
            import pprint
            pprint.pprint(out)

    def processErrorSlot(self, threadobj, exc):
        """Slot method to handle process errors"""
        dex = self.processThreads.index(threadobj)
        proc = self.processes[dex]
        proc.status = 'Process Failed: {}'.format(exc)
        proc.active.clear()


class ProgressWidget(QtGui.QWidget):
    """Progress Widget:

    Contains status text and a progress bar. If label is given, status text is
    prefaced by this label and a colon (:). This is typically used to indicate
    the difference between multiple progress widgets in a single progress
    dialog. This way the text given to the update method doesn't have to contain
    this information each time.
    """
    def __init__(self, label=None, parent=None):
        super(ProgressWidget, self).__init__(parent)
        self.label = label

        # Setup layout
        verticalLayout = QtGui.QVBoxLayout(self)
        self.text = QtGui.QLabel(self)
        verticalLayout.addWidget(self.text)
        self.progress = QtGui.QProgressBar(self)
        verticalLayout.addWidget(self.progress)
        self.setLayout(verticalLayout)

    def update(self, text, progress):
        """Updates the progress widget

        Updates the text and progress bar with the label, if specified,
        the given text and and progress (0-100)
        """
        if self.label:
            self.text.setText('{}: {}'.format(self.label, text))
        else:
            self.text.setText(text)
        self.progress.setValue(progress)


class GenericThread(QtCore.QObject):
    """A generic object meant to be executed within  a QThread object.

    Pass a function an its arguments to the constructor, then use
    GenericThread.moveToThread() to move to a thread. Then emit
    GenericThread.dowork to start the process. Once complete, the output of
    the function will be emitted by GenericThread.finished
    """

    dowork = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(object)
    processError = QtCore.pyqtSignal(QtCore.QObject, object)

    def __init__(self, function, *args, **kwargs):
        super(GenericThread, self).__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs

        self.dowork.connect(self.work)

    @QtCore.pyqtSlot()
    def work(self):
        try:
            out = self.function(*self.args, **self.kwargs)
        except:
            self.processError.emit(self, sys.exc_info()[1])
            raise
        else:
            self.finished.emit(out)


class TestProcess(object):
    def __init__(self):
        super(TestProcess, self).__init__()

        self.status = ''
        self.progress = 44
        self.active = thread_Event()

        self.setup()

    def setup(self):
        self.static = 'Transferring {} ({} of {}) {} kB'

    def work(self):
        import time
        fname = 'A File'
        self.active.set()
        self.progress = 0
        self.status = self.static.format(fname, 1, 2, 1000)
        for k in range(100):
            time.sleep(0.05)
            self.progress = k
        self.progress = 100
        self.status = 'Process Complete'

        self.active.clear()
        return 'Process Complete'


if __name__ == "__main__":
    app = QtGui.QApplication([])
    process = TestProcess()
    dlg = ProgressDialog(process, 'Titlee', 2000)
    dlg.exec_()
