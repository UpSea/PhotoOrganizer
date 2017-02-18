from PyQt4 import QtCore, QtGui
import os
import pdb


class PhotoTable(QtGui.QTableView):
    """ A table to display photos and their metadata

    This table implements a context menu with functions for interacting with
    and manipulating the photos and their tags
    """

    def __init__(self, parent=None):
        super(PhotoTable, self).__init__(parent)

        # Set the horizontal header's context menu
        self.horizontalHeader().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.on_headerContext_requested)
        self.horizontalHeader().setMovable(True)

    def contextMenuEvent(self, event):
        """ Reimplemented context menu event handler

        Arguments:
            event (QContextMenuEvent)
        """
        self.mouse_point = event.pos()
        menu = QtGui.QMenu(self)
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

        menu.exec_(self.horizontalHeader().mapToGlobal(point))

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


if __name__ == "__main__":
    app = QtGui.QApplication([])
    view = PhotoTable()

    view.show()
    app.exec_()
