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
from shared import resource_path
import os.path
from glob import glob
from PIL import Image
from io import BytesIO
import imagehash
from UIFiles import Ui_PicOrganizer as uiclassf
import sqlite3
import re
from datastore import (AlbumModel, Album, Photo, FieldObjectContainer,
                       FieldObject, AlbumDelegate, AlbumSortFilterModel)
from PhotoViewer import ImageViewer
from Dialogs import WarningDialog, warning_box
from create_database import create_database


class myWindow(QtGui.QMainWindow, uiclassf):
    """An application for filtering image data and thumbnails"""

    columns = ['Image', 'Tagged', 'File Name', 'Date', 'Hash', 'FileId',
               'Tags', 'Directory']
    required = [True, True, True, True, True, True, False, True]
    editor = [None, FieldObject.CheckBoxEditor, None, None, None, None,
              FieldObject.LineEditEditor, None]
    editable = [False, True, False, False, False, False, True, False]
    name_editable=[False, False, False, False, False, False, True, False]
    hidden = [False, False, False, False, True, True, False, False]
    types = [str, bool, str, str, str, int, str, str]
    fields = FieldObjectContainer(columns, required, editor, editable,
                                  name_editable, hidden, types)

    def __init__(self, parent=None):
        super(myWindow, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Photo Organizer')
        self.databaseFile = None
        self.mainWidget.setHidden(True)
        self.view.setHidden(True)

        # Set up the widgets
        self.slider.setRange(20, 400)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.on_sliderValueChanged)

        # Add icons
        newicon = QtGui.QIcon(resource_path(r'icons\New.ico'))
        self.actionNewDatabase.setIcon(newicon)
        openicon = QtGui.QIcon(resource_path(r'icons\Open.ico'))
        self.actionOpenDatabase.setIcon(openicon)

        # Instantiate an empty dataset and model
        self.album = Album(self.fields)
        self.model = AlbumModel(self.album)

        self.model.dataChanged.connect(self.on_dataChanged)
        self.proxy = AlbumSortFilterModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(2)

        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setColumnHidden(self.columns.index('FileId'), True)
        self.view.setItemDelegate(AlbumDelegate())

        # Signal Connections
        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.view.doubleClicked.connect(self.on_doubleClick)
        self.actionImportFolder.triggered.connect(self.on_importFolder)
        self.actionNewDatabase.triggered.connect(self.on_newDatabase)
        self.actionOpenDatabase.triggered.connect(self.on_openDatabase)

        # Set the horizontal header for a context menu
        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.horizontalHeader.customContextMenuRequested.connect(self.on_headerContext_requested)

        self.verticalHeader = self.view.verticalHeader()

        # Set view to hide columns
        self.view.rehideColumns()

        # Create the image viewer window
        self.imageViewer = ImageViewer()

    def importFolder(self, directory, dbfile):
        """Populate the table with images from directory

        Arguments:
        directory (str): The directory containing the desired image files
        dbfile (str):    The path to the database file to be populated
        """
        # Get the list of images with valid extensions
        images = []
        for extension in QtGui.QImageReader().supportedImageFormats():
            pattern = os.path.join(directory, '*.%s' % str(extension))
            images.extend(glob(pattern))

        iqry = 'INSERT INTO File (filename, directory, date, hash, ' + \
               'thumbnail) VALUES (?,?,?,?,?)'
        exHash = [(k['File Name'], k['Hash']) for k in self.album]
        exFiles = [os.path.join(k['Directory'], k['File Name'])
                   for k in self.album]
        with sqlite3.connect(dbfile) as con:
            con.text_factory = str
            con.execute('PRAGMA foreign_keys = 1')
            cur = con.cursor()
            # Loop over all images and add to the table
            changeDir = []
            for k, path in enumerate(images):
                # See if this file is already in the database
                if path in exFiles:
                    continue

                # Split off the filename
                fname = os.path.split(path)[1]

                # Read the scaled image into a byte array
                im = Image.open(path)
                exif = im._getexif()
                hsh = imagehash.average_hash(im)
                if (fname, str(hsh)) in exHash:
                    changeDir.append(path)
                    continue
                date = exif[36867] if exif else "Unknown"
                sz = 400
                im.thumbnail((sz, sz))
                fp = BytesIO()
                im.save(fp, 'png')

                # Add the model items
                cur.execute(iqry, [fname, directory, date, str(hsh),
                                   sqlite3.Binary(fp.getvalue())])

                fileId = cur.lastrowid
                pix = QtGui.QPixmap()
                pix.loadFromData(fp.getvalue())
                thumb = QtGui.QIcon(pix)
                values = ['', False, fname, date, str(hsh), fileId, '',
                          directory]
                self.model.insertRows(self.model.rowCount(), 0,
                                      Photo(self.fields, values, thumb))

                msg = 'Importing Photo %d of %d' % (k, len(images))
                self.statusbar.showMessage(msg)

                # Allow the application to stay responsive and show the progress
                QtGui.QApplication.processEvents()

        self.statusbar.showMessage('Done')

        if changeDir:
            dlg = WarningDialog('Matching Files Found', self)
            dlg.setText('The following files already exist in the database '+
                        'but are located in a different folder.\n'+
                        'Not yet equipped to handle this. These files were '+
                        'were ignored')
            detail = '\n'.join(changeDir)
            dlg.setDetailedText(detail)
            dlg.addButton(QtGui.QDialogButtonBox.Ok)
            dlg.exec_()

        self.setWidthHeight()
        QtCore.QTimer.singleShot(5000, self.statusbar.clearMessage)

    def openDatabase(self, dbfile):
        """ Open a database file and populate the album table

        Arguments:
            dbfile (str): The path to the database file
        """
        if not os.path.exists(dbfile):
            msg = 'Database File Not Found'
            warning_box(msg, self)
            return
        # Make sure table is visible
        if self.view.isHidden():
            self.mainWidget.setHidden(False)
            self.view.setHidden(False)
            self.labelNoDatabase.setHidden(True)
            self.labelNoPhotos.setHidden(True)

        self.album = Album(self.fields)
        self.model.changeDataSet(self.album)
        self.databaseFile = dbfile
        cnt = 'SELECT count(*) FROM File'
        qry = 'SELECT directory, filename, date, hash, thumbnail, FilId, '+\
              'tagged FROM File'
        with sqlite(dbfile) as con:
            cur = con.cursor()
            cur2 = con.cursor()
            cur.execute(cnt)
            count = cur.fetchone()[0]
            cur.execute(qry)
            k = 0
            for row in cur:
                k += 1
                directory = row[0]
                fname = row[1]
                date = row[2]
                hsh = row[3]
                data = row[4]
                fileId = row[5]
                tagged = bool(row[6])
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

                values = ['', tagged, fname, date, str(hsh), fileId, location,
                          directory]
                self.model.insertRows(self.model.rowCount(), 0,
                                      Photo(self.fields, values, thumb))

                msg = 'Importing Photo %d of %d' % (k, count)
                self.statusbar.showMessage(msg)

                # Allow the application to stay responsive and show the progress
                QtGui.QApplication.processEvents()

        self.statusbar.showMessage('Done')
        self.setWidthHeight()
        QtCore.QTimer.singleShot(5000, self.statusbar.clearMessage)
        self.actionImportFolder.setEnabled(True)

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

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_dataChanged(self, topLeft, bottomRight):
        """ Update the database when user changes data

        Slot for model.dataChanged
        """
        if topLeft != bottomRight:
            raise ValueError('Not equipped to handle multiple rows/columns')
        col = self.fields.index('FileId')
        row = topLeft.row()
        fileId = self.model.data(self.model.index(row, col)).toInt()[0]
        if topLeft.column() == self.fields.index('Tagged'):
            value = topLeft.data().toBool()
            q = 'UPDATE File SET Tagged = ? WHERE FilId == ?'
            with sqlite(self.databaseFile) as con:
                cur = con.cursor()
                cur.execute(q, (1 if value else 0, fileId))
        elif topLeft.column() == self.fields.index('Tags'):
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

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_doubleClick(self, index):
        """ Show the image viewer

        Slot for doubleclick on table view

        Arguments:
            index (QModelIndex)
        """
        # Get the file path
        if index.column() != 0:
            return
        mapped = self.proxy.mapToSource(index)
        fullfile = os.path.join(self.album[mapped.row(), 'Directory'],
                                self.album[mapped.row(), 'File Name'])
        self.imageViewer.setImage(fullfile)

        # Show the window
        if self.imageViewer.isHidden():
            self.imageViewer.show()
        else:
            # Restore it if minimized
            state = (self.imageViewer.windowState() &~
                     QtCore.Qt.WindowMinimized |
                     QtCore.Qt.WindowActive)
            self.imageViewer.setWindowState(state)
            # Bring it to the front
            self.imageViewer.raise_()

    @QtCore.pyqtSlot()
    def on_importFolder(self):
        """ Import photos from a folder

        Slot for actionImportFolder
        """
        folder = QtGui.QFileDialog.getExistingDirectory(self, "Import Folder",
                                                        QtCore.QDir.currentPath())
        if folder:
            if self.view.isHidden():
                self.view.setHidden(False)
                self.labelNoPhotos.setHidden(True)
            self.importFolder(str(folder), self.databaseFile)

    @QtCore.pyqtSlot()
    def on_newDatabase(self):
        """ Create a new empty database

        Slot for actionNewDatabase
        """
        # Prompt the user
        filt = "Photo Database (*.pdb)"
        filename = QtGui.QFileDialog.getSaveFileName(self, 'New Database File',
                                                     filter=filt)
        if not filename:
            return  # Canceled

        # Create the database and show the main widget
        dbfile = str(QtCore.QDir.toNativeSeparators(filename))
        create_database(dbfile)
        self.databaseFile = dbfile
        self.labelNoDatabase.setHidden(True)
        self.mainWidget.setHidden(False)
        self.actionImportFolder.setEnabled(True)

    @QtCore.pyqtSlot()
    def on_openDatabase(self):
        """ Open an existing database

        Slot for actionOpenDatabase
        """
        # Prompt the user
        filt = "Photo Database (*.pdb);; All Files (*.*)"
        filename = QtGui.QFileDialog.getOpenFileName(self, 'Open Database File',
                                                     filter=filt)
        if not filename:
            return  # Canceled

        # Create the database and show the main widget
        dbfile = str(QtCore.QDir.toNativeSeparators(filename))
        self.openDatabase(dbfile)

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
    main.openDatabase('TestDb2.pdb')

    sys.exit(app.exec_())
