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
import imagehash
from UIFiles import Ui_PicOrganizer as uiclassf
import sqlite3
import re
from datastore import AlbumModel, Album, Photo, FieldObjectContainer


class myWindow(QtGui.QMainWindow, uiclassf):
    """An application for filtering image data and thumbnails"""

    columns = ['Image', 'File Name', 'Date', 'Hash', 'Tags', 'FileId']
    types = [bool, str, str, str, str, int]
    editable = [True, False, False, False, True, False]
    hidden = [False, False, False, True, False, True]
    # Need to implement editable and hidden inputs to FieldObjectContainer
    fields = FieldObjectContainer(columns, types)

    def __init__(self, parent=None):
        super(myWindow, self).__init__(parent)
        self.setupUi(self)
        self.databaseFile = None

        # Set up the widgets
        self.slider.setRange(20, 400)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.on_sliderValueChanged)

        # Instantiate an empty dataset and model
        self.album = Album()
        self.model = AlbumModel(self.album)

        self.model.dataChanged.connect(self.on_dataChanged)
        self.proxy = QtGui.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(2)

        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setColumnHidden(self.columns.index('FileId'), True)

        # Signal Connections
        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.comboBox.currentIndexChanged.connect(self.on_comboBox_currentIndexChanged)

        # Set the horizontal header for a context menu
        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader.customContextMenuRequested.connect(self.on_headerContext_requested)

        self.verticalHeader = self.view.verticalHeader()

        # Set up combobox
        self.comboBox.addItems(self.columns[1:])
        self.comboBox.setCurrentIndex(1)

#     def populate(self, directory, calc_hash=False):
#         """Populate the table with images from directory
#
#         Arguments:
#         directory (str): The directory containing the desired image files
#         """
#         # Get the list of images with valid extensions
#         images = []
#         ext = [fmt.data().decode('utf-8')
#                for fmt in QtGui.QImageReader().supportedImageFormats()]
#         for extension in ext:
#             pattern = os.path.join(directory, '*.%s' % extension)
#             images.extend(glob(pattern))
#
#         # Loop over all images and add to the table
#         for k, path in enumerate(images[:4]):
#             # Read the scaled image into a byte array
#             im = Image.open(path)
#             exif = im._getexif()
#             hsh = imagehash.average_hash(im) if calc_hash else ''
#             date = exif[36867] if exif else "Unknown"
#             im.thumbnail((400, 400))
#             fp = BytesIO()
#             im.save(fp, 'png')
#
#             # Create the QPixmap from the byte array
#             pix = QtGui.QPixmap()
#             pix.loadFromData(fp.getvalue())
#
#             # Add the model items
#             imgItem = QtGui.QStandardItem()
#             imgItem.setData(QtGui.QIcon(pix), QtCore.Qt.DecorationRole)
#             self.model.setItem(k, 0, imgItem)
#             fname = os.path.split(path)[1]
#             self.model.setItem(k, 1, QtGui.QStandardItem(fname))
#             self.model.setItem(k, 2, QtGui.QStandardItem(date))
#             self.model.setItem(k, 3, QtGui.QStandardItem(str(hsh)))
#             self.view.resizeColumnToContents(k)
#             self.view.resizeRowToContents(k)
#
#             # Allow the application to stay responsive and show the progress
#             QtGui.QApplication.processEvents()

    def populateFromDatabase(self, dbfile):
        self.album = Album(self.fields)
        self.model.changeDataSet(self.album)
        self.databaseFile = dbfile
        qry = 'SELECT directory, filename, date, hash, thumbnail, '+\
              'FilId FROM File'
        with sqlite(dbfile) as con:
            cur = con.cursor()
            cur2 = con.cursor()
            cur.execute(qry)
            for row in cur:
                fname = row[1]
                date = row[2]
                hsh = row[3]
                data = row[4]
                fileId = row[5]
                fp = BytesIO(data)

                lqry = 'SELECT l.location FROM File as f '+\
                       'JOIN FileLoc as fl ON f.FilId == fl.FilId '+\
                       'JOIN Locations as l ON fl.LocId == l.LocId '+\
                       'WHERE f.FilId == ?'
                cur2.execute(lqry, [fileId])
                location = ', '.join([l[0] for l in cur2.fetchall()])

                # Create the QPixmap from the byte array
                pix = QtGui.QPixmap()
                pix.loadFromData(fp.getvalue())
                thumb = QtGui.QIcon(pix)

                values = ['', fname, date, str(hsh), location, fileId]
                self.model.insertRows(self.model.rowCount(), 0,
                                      Photo(self.fields, values, thumb))

                # Allow the application to stay responsive and show the progress
                QtGui.QApplication.processEvents()

        self.setWidthHeight()

    def setWidthHeight(self, size=None):
        """Set the width and height of the table columns/rows

        Width is set to the desired icon size, not actual size for consistency
        when images are filtered. Rows are always resized to contents.
        """
        size = size or self.iconSize
        self.view.setColumnWidth(0, size)
        self.verticalHeader.setDefaultSectionSize(size)
        self.verticalHeader.resizeSections(self.verticalHeader.Fixed)
        self.view.setIconSize(QtCore.QSize(size, size))

    def setFilter(self, pattern=None, column=None):
        """Set the table filter

        Arguments:
            pattern (str):  (None) The string to use in the regex filter. If
                none is given, it will be left as-is. If the empty string is
                given, it will be cleared.
            column (int): (None) The column to filter. If none is given, it
                will be left as-is
        """
        # Set the pattern
        if pattern is not None:
            self.lineEdit.setText(pattern)

        # Set the column
        if column is not None:
            self.comboBox.setCurrentIndex(column-1)

    def columnByName(self, name):
        cols = [k.lower() for k in self.columns]
        return cols.index(name.lower())

    @QtCore.pyqtSlot(int)
    def on_sliderValueChanged(self, size):
        """Resize the image thumbnails. Slot for the slider

        Arguments:
            size (int): The desired square size of the thumbnail in pixels
        """
        self.setWidthHeight(size)

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

        values = [str(self.model.data(self.model.index(row,
                  self.logicalIndex)).toPyObject())
                  for row in range(self.model.rowCount())]
        valuesUnique = sorted(list(set(values)))
        if '' in valuesUnique:
            valuesUnique.remove('')

        if not valuesUnique:
            return

        actionSort = QtGui.QAction("Sort", self)
        actionSort.triggered.connect(self.on_sort_triggered)
        self.menuValues.addAction(actionSort)
        self.menuValues.addSeparator()
        actionAll = QtGui.QAction("All", self)
        actionAll.triggered.connect(self.on_actionAll_triggered)
        self.menuValues.addAction(actionAll)
        self.menuValues.addSeparator()

        for actionName in valuesUnique:
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
        self.setFilter('', self.logicalIndex)

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
        self.setFilter(pattern, self.logicalIndex)

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

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_dataChanged(self, topLeft, bottomRight):
        if topLeft != bottomRight:
            raise ValueError('Not equipped to handle multiple rows/columns')
        col = self.fields.index('FileId')
        row = topLeft.row()
        fileId = self.model.data(self.model.index(row, col)).toInt()[0]
        # Get the new locations
        new_locs = [k.strip() for k in re.split(';|,', str(topLeft.data().toPyObject()))
                    if k.strip() != '']
        with sqlite(self.databaseFile) as con:
            cur = con.cursor()
            cur.execute('SELECT LocId, Location FROM Locations')
            existing = {k[1].lower(): k[0] for k in cur.fetchall()}
            for new_loc in new_locs:
                if new_loc.strip() == '':
                    continue
                if new_loc.lower() not in existing:
                    # INSERT new location
                    q = 'INSERT OR IGNORE INTO Locations (Location) VALUES (?)'
                    cur.execute(q, [new_loc])
                    locId = cur.lastrowid
                else:
                    locId = existing[new_loc.lower()]

                # Insert FileLoc mapping (ON CONFLICT IGNORE)
                q = 'INSERT OR IGNORE INTO FileLoc (FilId, LocId) VALUES (?,?)'
                cur.execute(q, [fileId, locId])

            # Remove deleted locations
            loc_literals = ['?'] * len(new_locs)
            params = ','.join(loc_literals)
            q = "DELETE From FileLoc WHERE FilId == ? AND "+\
                "(SELECT Location FROM Locations as l WHERE "+\
                "l.LocId == FileLoc.LocId) NOT IN ({})".format(params)
            cur.execute(q, [fileId] + new_locs)

            # Remove them unused tags
            q = 'DELETE FROM Locations WHERE LocId NOT IN '+\
                '(SELECT LocId FROM FileLoc)'
            cur.execute(q)
        self.proxy.invalidate()

    @property
    def iconSize(self):
        size = self.view.iconSize()
        return max(size.width(), size.height())


def sqlite(dbfile):
    con = sqlite3.connect(dbfile)
    con.execute('pragma foreign_keys = 1')
    return con


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    main = myWindow()
    main.resize(800, 600)
    main.show()

#     directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
#     main.populate(directory)
    main.populateFromDatabase('TestDb2.db')

    sys.exit(app.exec_())
