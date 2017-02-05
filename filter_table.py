"""
An application for filtering image data and thumbnails

Filter Table based on:
http://stackoverflow.com/questions/14068823/how-to-create-filters-for-qtableview-in-pyqt
Image in standard item partially based on:
https://forum.qt.io/topic/62180/resizing-image-to-display-in-tableview
and
http://pythoncentral.io/pyside-pyqt-tutorial-the-qlistwidget/
"""
from PyQt4 import QtCore, QtGui
import os.path
from glob import glob
from PIL import Image
from io import BytesIO


class myWindow(QtGui.QMainWindow):
    """An application for filtering image data and thumbnails"""

    def __init__(self, parent=None):
        super(myWindow, self).__init__(parent)
        # Initialize and configure the widgets
        self.centralwidget = QtGui.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self.label = QtGui.QLabel(self.centralwidget)
        self.label.setText("Regex Filter")

        self.lineEdit = QtGui.QLineEdit(self.centralwidget)

        self.comboBox = QtGui.QComboBox(self.centralwidget)
        self.comboBox.addItems(["Column 1", "Column 2"])
        self.comboBox.setCurrentIndex(1)

        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.slider.setRange(20, 400)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.setIconSize)

        self.model = QtGui.QStandardItemModel(self)
        self.proxy = QtGui.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(2)

        self.view = QtGui.QTableView(self.centralwidget)
        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)

        # Lay out the widgets
        self.gridLayout = QtGui.QGridLayout(self.centralwidget)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.comboBox, 0, 2, 1, 1)
        self.gridLayout.addWidget(self.slider, 0, 3, 1, 1)
        self.gridLayout.addWidget(self.view, 1, 0, 1, 4)

        # Signal Connections
        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.comboBox.currentIndexChanged.connect(self.on_comboBox_currentIndexChanged)

        # Set the horizontal header for a context menu
        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader.customContextMenuRequested.connect(self.on_headerContext_requested)

    def populate(self, directory):
        """Populate the table with images from directory

        Arguments:
        directory (str): The directory containing the desired image files
        """
        # Get the list of images with valid extensions
        images = []
        ext = [fmt.data().decode('utf-8')
               for fmt in QtGui.QImageReader().supportedImageFormats()]
        for extension in ext:
            pattern = os.path.join(directory, '*.%s' % extension)
            images.extend(glob(pattern))

        # Loop over all images and add to the table
        for k, path in enumerate(images):
            # Read the scaled image into a byte array
            im = Image.open(path)
            exif = im._getexif()
            date = exif[36867] if exif else "Unknown"
            im.thumbnail((400, 400))
            fp = BytesIO()
            im.save(fp, 'png')

            # Create the QPixmap from the byte array
            pix = QtGui.QPixmap()
            pix.loadFromData(fp.getvalue())

            # Add the model items
            imgItem = QtGui.QStandardItem()
            imgItem.setData(QtGui.QIcon(pix), QtCore.Qt.DecorationRole)
            self.model.setItem(k, 0, imgItem)
            fname = os.path.split(path)[1]
            self.model.setItem(k, 1, QtGui.QStandardItem(fname))
            self.model.setItem(k, 2, QtGui.QStandardItem(date))
            self.view.resizeColumnToContents(k)
            self.view.resizeRowToContents(k)

            # Allow the application to stay responsive and show the progress
            QtGui.QApplication.processEvents()

        # Resize the rows and columns
        self.setWidthHeight()

    def setWidthHeight(self):
        """Set the width and height of the table columns/rows

        Width is set to the desired icon size, not actual size for consistency
        when images are filtered. Rows are always resized to contents.
        """
        self.view.setColumnWidth(0, self.iconSize)
        self.view.resizeRowsToContents()

    @QtCore.pyqtSlot(int)
    def setIconSize(self, size):
        """Resize the image thumbnails. Slot for the slider

        Arguments:
            size (int): The desired square size of the thumbnail in pixles
        """
        self.view.setIconSize(QtCore.QSize(size, size))
        self.setWidthHeight()

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_headerContext_requested(self, point):
        """Set up context menu for column filter.

        Slot for the horizontal header

        Arguments:
            point (QPoint): The relative position of the mouse when clicked
        """
        logicalIndex = self.horizontalHeader.logicalIndexAt(point)
        if logicalIndex < 0:
            return
        self.logicalIndex = logicalIndex
        self.menuValues = QtGui.QMenu(self)
        self.signalMapper = QtCore.QSignalMapper(self)

        valuesUnique = [self.model.item(row, self.logicalIndex).text()
                        for row in range(self.model.rowCount())]

        actionSort = QtGui.QAction("Sort", self)
        actionSort.triggered.connect(self.on_sort_triggered)
        self.menuValues.addAction(actionSort)
        self.menuValues.addSeparator()
        actionAll = QtGui.QAction("All", self)
        actionAll.triggered.connect(self.on_actionAll_triggered)
        self.menuValues.addAction(actionAll)
        self.menuValues.addSeparator()

        for actionName in sorted(list(set(valuesUnique))):
            action = QtGui.QAction(actionName, self)
            self.signalMapper.setMapping(action, actionName)
            action.triggered.connect(self.signalMapper.map)
            self.menuValues.addAction(action)

        self.signalMapper.mapped[str].connect(self.on_signalMapper_mapped)

        self.menuValues.exec_(self.horizontalHeader.mapToGlobal(point))

    @QtCore.pyqtSlot()
    def on_actionAll_triggered(self):
        """Remove filter for the column that was clicked

        Slot for the context menu action
        """
        filterColumn = self.logicalIndex
        filterString = QtCore.QRegExp("", QtCore.Qt.CaseInsensitive,
                                      QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(filterString)
        self.setComboIndex(filterColumn)
        self.setWidthHeight()
        self.lineEdit.setText('')

    @QtCore.pyqtSlot()
    def on_sort_triggered(self):
        """Sort by the clicked column"""
        so = {QtCore.Qt.AscendingOrder: QtCore.Qt.DescendingOrder,
              QtCore.Qt.DescendingOrder: QtCore.Qt.AscendingOrder}
        self.view.sortByColumn(self.logicalIndex,
                               so[self.horizontalHeader.sortIndicatorOrder()])

    @QtCore.pyqtSlot(str)
    def on_signalMapper_mapped(self, pattern):
        """Set the filter for the column that was clicked

        Slot for the context menu action signal mapper

        Arguments:
            pattern (str): The pattern for the regular expression
        """
        filterColumn = self.logicalIndex
        filterString = QtCore.QRegExp(pattern,
                                      QtCore.Qt.CaseSensitive,
                                      QtCore.QRegExp.FixedString)

        self.proxy.setFilterRegExp(filterString)
        self.setComboIndex(filterColumn)
        self.lineEdit.setText(pattern)
        self.setWidthHeight()

    @QtCore.pyqtSlot(str)
    def on_lineEdit_textChanged(self, pattern):
        """Set the filter

        Slot for the line edit

        Arguments:
            pattern (str): The pattern for the regular expression
        """
        search = QtCore.QRegExp(pattern,
                                QtCore.Qt.CaseInsensitive,
                                QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(search)
        self.setWidthHeight()

    @QtCore.pyqtSlot(int)
    def on_comboBox_currentIndexChanged(self, index):
        """Set the column to filter

        Slot for the comboBox

        Arguments:
            index (int): The column to be indexed (minus one)
        """
        self.proxy.setFilterKeyColumn(index+1)
        self.setWidthHeight()

    def setComboIndex(self, column):
        """Change the comboBox and filter key column

        Arguments:
            column (int): The column to filter (Combo box will be set to column
                minus 1
        """
        self.proxy.setFilterKeyColumn(column)
        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentIndex(column-1)
        self.comboBox.blockSignals(False)

    @property
    def iconSize(self):
        size = self.view.iconSize()
        return max(size.width(), size.height())


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    main = myWindow()
    main.resize(800, 600)
    main.show()

    directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
    main.populate(directory)

    sys.exit(app.exec_())
