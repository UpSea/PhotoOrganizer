from PyQt4 import QtCore, QtGui


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
        index = self.indexAt(event.pos())
        sindex = self.model().mapToSource(index)
        print self.model().data(index)

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
        menuValues = QtGui.QMenu(self)

        actionSort = QtGui.QAction("Sort", self)
        actionSort.triggered.connect(self.on_sort_triggered)
        menuValues.addAction(actionSort)

        menuValues.exec_(self.horizontalHeader().mapToGlobal(point))

    @QtCore.pyqtSlot()
    def on_sort_triggered(self):
        """Sort by the clicked column"""
        so = {QtCore.Qt.AscendingOrder: QtCore.Qt.DescendingOrder,
              QtCore.Qt.DescendingOrder: QtCore.Qt.AscendingOrder}
        self.sortByColumn(self.logicalIndex,
                          so[self.horizontalHeader().sortIndicatorOrder()])

if __name__ == "__main__":
    app = QtGui.QApplication([])
    view = PhotoTable()

    view.show()
    app.exec_()
