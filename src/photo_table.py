from PyQt4 import QtCore, QtGui
import os
import pdb


class PhotoTable(QtGui.QTableView):
    """ A table to display photos and their metadata

    This table implements a context menu with functions for interacting with
    and manipulating the photos and their tags
    """

    newFieldSig = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(PhotoTable, self).__init__(parent)

        # Set the horizontal header's context menu
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.on_headerContext_requested)
        self.horizontalHeader().setMovable(True)

        # Add the batch tag action
        self.actionBatchTag = QtGui.QAction('&Group Tag Selection', self)
        self.actionBatchTag.setShortcut('Ctrl+G')

    def contextMenuEvent(self, event):
        """ Reimplemented context menu event handler

        Arguments:
            event (QContextMenuEvent)
        """
        self.mouse_point = event.pos()
        menu = QtGui.QMenu(self)

        # Add the open in explorer action
        actionOpen = QtGui.QAction('Show in Explorer', self)
        menu.addAction(actionOpen)

        # Set up the signal mapper
        sm = QtCore.QSignalMapper(self)
        sm.mapped[QtCore.QString].connect(self.on_showExplorerMapper)

        # Get the selected rows
        indexes = [self.model().mapToSource(k) for k in self.selectedIndexes()]
        rows = set([k.row() for k in indexes])

        # Get the directories
        album = self.model().dataset
        directories = set([album[r, 'Directory'] for r in rows])

        # Set up the menu action and signal connection(s)
        if len(directories) == 1:
            sm.setMapping(actionOpen, next(iter(directories)))
            actionOpen.triggered.connect(sm.map)
        else:
            dmen = QtGui.QMenu('SubMenu', menu)
            actionOpen.setMenu(dmen)
            for d in directories:
                action = QtGui.QAction(d, dmen)
                sm.setMapping(action, d)
                action.triggered.connect(sm.map)
                dmen.addAction(action)

        # Add the batch tag action
        menu.addAction(self.actionBatchTag)

        menu.exec_(self.mapToGlobal(event.pos()))

    def rehideColumns(self):
        """ Hide/Unhide columns based on field's hidden property """
        # Get the hidden property for each field
        fields = self.model().sourceModel().dataset.fields
        hide = [k.hidden for k in fields]

        # Use header's setSectionHidden. Hopefully this won't go wonky randomly
        # when proxy model is invalidated
        hh = self.horizontalHeader()
        for k, v in enumerate(hide):
            hh.setSectionHidden(k, v)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_headerContext_requested(self, point):
        """Set up context menu for column filter.

        Slot for the horizontal header

        Arguments:
            point (QPoint): The relative position of the mouse when clicked
        """
        logicalIndex = self.horizontalHeader().logicalIndexAt(point)
        if logicalIndex < 0:
            return
        self.logicalIndex = logicalIndex
        menu = QtGui.QMenu(self)

        actionSort = QtGui.QAction("Sort", self)
        actionSort.triggered.connect(self.on_sort_triggered)
        menu.addAction(actionSort)

        menu.addSeparator()

        # Add new field action
        actionNewField = QtGui.QAction('New Field', menu)
        actionNewField.triggered.connect(self.newFieldSig.emit)
        menu.addAction(actionNewField)

        # Add the hide field action
        actionHide = QtGui.QAction('Hide Field(s)', self)
        actionHide.triggered.connect(self.on_hideField)
        menu.addAction(actionHide)

        # Add the unhide menu
        hiddenFields = [k.name for k in
                        self.model().dataset.fields if k.hidden]
        if hiddenFields:
            # Initialize signal mapper
            sm = QtCore.QSignalMapper(self)
            sm.mapped[QtCore.QString].connect(self.on_unhide)

            # Create the parent action
            unhideAction = QtGui.QAction("Unhide", menu)
            menu.addAction(unhideAction)
            hmenu = QtGui.QMenu('HiddenFields', self)
            unhideAction.setMenu(hmenu)

            # Add the submenu actions
            for h in hiddenFields:
                a = QtGui.QAction(h, hmenu)
                sm.setMapping(a, h)
                a.triggered.connect(sm.map)
                hmenu.addAction(a)

        menu.exec_(self.horizontalHeader().mapToGlobal(point))

    @QtCore.pyqtSlot()
    def on_hideField(self):
        """ Hide the selected columns """
        self.horizontalHeader().setSectionHidden(self.logicalIndex, True)
        self.model().dataset.fields[self.logicalIndex].hidden = True

    @QtCore.pyqtSlot()
    def on_sort_triggered(self):
        """Sort by the clicked column"""
        so = {QtCore.Qt.AscendingOrder: QtCore.Qt.DescendingOrder,
              QtCore.Qt.DescendingOrder: QtCore.Qt.AscendingOrder}
        self.sortByColumn(self.logicalIndex,
                          so[self.horizontalHeader().sortIndicatorOrder()])

    @QtCore.pyqtSlot(QtCore.QString)
    def on_showExplorerMapper(self, directory):
        """ Open the given directory in Windows Explorer

        Slot for the context menu action signal mapper

        Arguments:
            directory (QString)
        """
        os.startfile(directory)

    @QtCore.pyqtSlot(QtCore.QString)
    def on_unhide(self, fieldname):
        """ Unhide the given field

        Slot for unhide signal mapper

        Arguments:
            fieldname (QString)
        """
        album = self.model().dataset
        coldex = album.fields.index(str(fieldname))
        self.horizontalHeader().setSectionHidden(coldex, False)
        album.fields[coldex].hidden = False


if __name__ == "__main__":
    app = QtGui.QApplication([])
    view = PhotoTable()

    view.show()
    app.exec_()
