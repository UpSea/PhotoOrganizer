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
from UIFiles import Ui_PicOrganizer as uiclassf
from shared import resource_path, __release__, organization, application
import platform
import os
from glob import glob
from PIL import Image
from io import BytesIO
import imagehash
import sqlite3
import re
from datastore import (AlbumModel, Album, Photo, FieldObjectContainer,
                       FieldObject, AlbumDelegate, AlbumSortFilterModel)
from PhotoViewer import ImageViewer
from FilterTree import TagItemModel, TagFilterProxyModel
from Dialogs import WarningDialog, warning_box, BatchTag, UndoDialog
from database import PhotoDatabase
from create_database import create_database
from datetime import datetime
import undo
import pdb


class PhotoOrganizer(QtGui.QMainWindow, uiclassf):
    """An application for filtering image data and thumbnails"""

    def __init__(self, dbfile=None, parent=None):
        super(PhotoOrganizer, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Photo Organizer')
        self.db = PhotoDatabase(dbfile)
        self.mainWidget.setHidden(True)
        self.view.setHidden(True)
        self.treeView.setHidden(True)

        # Setup application organization and application name
        app = QtGui.QApplication.instance()
        app.setOrganizationName(organization)
        app.setApplicationName(application)

        # Set up the widgets
        self.slider.setRange(20, 400)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.on_sliderValueChanged)

        # Add icons
        actionicons = [(self.actionNewDatabase, r'icons\New.ico'),
                       (self.actionOpenDatabase, r'icons\Open.ico'),
                       (self.actionUndo, r'icons\Undo.png'),
                       (self.actionRedo, r'icons\Redo.png')]
        for action, iconPath in actionicons:
            icon = QtGui.QIcon(resource_path(iconPath))
            action.setIcon(icon)

        # Instantiate the Undo Stack
        self.undoStack = QtGui.QUndoStack(self)
        self.undoDialog = UndoDialog(self.undoStack, self)

        # Edit Menu
        self.actionUndo = self.undoStack.createUndoAction(self.menuEdit, 'Undo')
        undoIcon = QtGui.QIcon(resource_path(r'icons\undo.png'))
        self.actionUndo.setIcon(undoIcon)
        self.actionUndo.setShortcut('Ctrl+Z')
        self.menuEdit.addAction(self.actionUndo)

        self.actionRedo = self.undoStack.createRedoAction(self.menuEdit, 'Redo')
        redoIcon = QtGui.QIcon(resource_path(r'icons\redo.png'))
        self.actionRedo.setIcon(redoIcon)
        self.actionRedo.setShortcut('Ctrl+Y')
        self.menuEdit.addAction(self.actionRedo)

        # Instantiate an empty dataset and model
        album = Album()
        self.model = AlbumModel(album)
        self.model.undoStack = self.undoStack

        self.model.albumDataChanged.connect(self.on_albumDataChanged)
        self.proxy = AlbumSortFilterModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(2)

        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegate(AlbumDelegate())
        self.view.rehideColumns()

        # Set up the toolbar
        self.toolBar.addAction(self.actionUndo)
        self.toolBar.addAction(self.actionRedo)

        def add_shortcut(action):
            shortcut = action.shortcut().toString()
            if shortcut:
                sc = action.toolTip() + ' ({})'.format(shortcut)
                action.setToolTip(sc)
        map(add_shortcut, self.toolBar.actions())

        # Set up tree view model
        self.treeModel = TagItemModel()
        self.treeProxy = TagFilterProxyModel()
        self.treeProxy.setSourceModel(self.treeModel)
        self.treeProxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.treeView.setModel(self.treeProxy)
        self.treeView.setDb(self.db)

        # Signal Connections
        self.editFilter.textChanged.connect(self.on_editFilter_textChanged)
        self.view.doubleClicked.connect(self.on_doubleClick)
        self.actionImportFolder.triggered.connect(self.on_importFolder)
        self.actionNewDatabase.triggered.connect(self.on_newDatabase)
        self.actionOpenDatabase.triggered.connect(self.on_openDatabase)
        self.actionBatchTag.triggered.connect(self.on_actionBatchTag)
        self.view.actionBatchTag.triggered.connect(self.on_actionBatchTag)
        self.actionAbout.triggered.connect(self.on_helpAbout)
        self.dateFrom.dateChanged.connect(self.proxy.setFromDate)
        self.dateFrom.dateChanged.connect(self.dateTo.setMinimumDate)
        self.dateTo.dateChanged.connect(self.proxy.setToDate)
        self.checkDateRange.stateChanged.connect(self.on_checkDateChanged)
        self.comboDateFilter.currentIndexChanged[int].connect(self.on_comboDate)
        self.actionHideTagged.toggled.connect(self.proxy.on_hideTagged)
        self.view.newFieldSig.connect(self.on_newField)
        self.actionNewField.triggered.connect(self.on_newField)
        self.actionChangeLog.triggered.connect(self.on_changeLog)
        self.groupDateFilter.toggled.connect(self.proxy.setDateFilterStatus)
        self.treeModel.dataChanged.connect(self.on_treeDataChanged)
        self.buttonClearFilter.clicked.connect(self.on_clearFilter)
        self.actionUndoList.triggered.connect(self.on_undoList)
        self.db.newDatabase.connect(self.treeView.newConnection)
        self.db.databaseChanged.connect(self.treeView.updateTree)

        # Set the horizontal header for a context menu
        self.horizontalHeader = self.view.horizontalHeader()
        self.verticalHeader = self.view.verticalHeader()

        # Create the image viewer window
        self.imageViewer = ImageViewer()

        # Setup the date filters
        self.comboDateFilter.addItems(['Year', 'Month', 'Day'])
        self.comboDateFilter.setCurrentIndex(1)
        self.on_comboDate(self.proxy.MonthFilter)
        self.checkDateRange.setChecked(True)
        self.on_checkDateChanged(QtCore.Qt.Checked)
        self.proxy.setDateFilterStatus(self.groupDateFilter.isChecked())

    def showEvent(self, event):
        """ Re-implemented to restore window geometry when shown """
        # Restore the window geometry
        settings = QtCore.QSettings()
        self.restoreGeometry(settings.value("MainWindow/Geometry").toByteArray())
        # Restore the toolbar settings
        tb = settings.value('toolbarShowing')
        state = tb.toBool() if tb else True
        self.actionToolbar.setChecked(state)
        # Restore the database
        dbfile = self.databaseFile or settings.value("lastDatabase").toString()
        if dbfile:
            self.openDatabase(str(dbfile))

    def closeEvent(self, event):
        """ Re-implemented to save settings """
        # Save general App settings
        settings = QtCore.QSettings()
        settings.clear()
        # Save the window geometry
        settings.setValue("MainWindow/Geometry", QtCore.QVariant(
                          self.saveGeometry()))
        # Save the database
        settings.setValue("lastDatabase", QtCore.QVariant(self.databaseFile))
        # Save the toolbar settings
        settings.setValue("toolbarShowing",
                          QtCore.QVariant(self.actionToolbar.isChecked()))

        # Close the current album
        self.closeDatabase()

    def closeDatabase(self):
        """ Close the current album to prepare to open another """
        # Close child windows
        self.imageViewer.close()
        self.undoDialog.close()

        if self.databaseFile is None:
            return

        # Save fields
        self.db.setFields(self.fields)

        # Save database-specific settings
        self.saveAppData()
        self.db.setDatabaseFile(None)

    def saveAppData(self):
        """ Save database-specific settings """
        headerState = sqlite3.Binary(self.horizontalHeader.saveState())
        kwargs = {'AppFileVersion': __release__,
                  'AlbumTableState': headerState}
        self.db.updateAppData(**kwargs)

    ########################
    #   Album Operations   #
    ########################

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
                # Try to get date from exif
                if exif and 36867 in exif:
                    date = exif[36867]
                else:
                    # Use modified time (not as reliable)
                    timestamp = os.path.getmtime(path)
                    dt = datetime.fromtimestamp(timestamp)
                    date = dt.strftime('%Y:%m:%d %H:%M:%S')
                sz = 400
                im.thumbnail((sz, sz))
                fp = BytesIO()
                im.save(fp, 'png')

                # Add the model items
                cur.execute(iqry, [fname, directory, date, str(hsh),
                                   sqlite3.Binary(fp.getvalue())])
                fileId = cur.lastrowid
                cur.execute('SELECT importTimeUTC FROM File WHERE FilId=?',
                            (fileId,))
                importTime = cur.fetchone()[0]

                pix = QtGui.QPixmap()
                pix.loadFromData(fp.getvalue())
                thumb = QtGui.QIcon(pix)

                # Create the values list based on the order of fields
                def updateValues(values, name, val):
                    values[self.fields.index(name)] = val

                values = ['' for _ in self.fields]
                updateValues(values, 'Directory', directory)
                updateValues(values, 'File Name', fname)
                updateValues(values, 'Date', date)
                updateValues(values, 'Hash', str(hsh))
                updateValues(values, 'FileId', fileId)
                updateValues(values, 'Tagged', False)
                updateValues(values, 'Import Date', importTime)

                self.model.insertRows(self.model.rowCount(), 0,
                                      Photo(self.fields, values, thumb))

                msg = 'Importing Photo %d of %d' % (k+1, len(images))
                self.statusbar.showMessage(msg)

                # Allow the application to stay responsive and show the progress
                QtGui.QApplication.processEvents()

        self.statusbar.showMessage('Finished Import', 5000)

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
        self.clearFilters()

    def openDatabase(self, dbfile):
        """ Open a database file and populate the album table

        Arguments:
            dbfile (str): The path to the database file
        """
        if not os.path.exists(dbfile):
            msg = 'Database File Not Found'
            warning_box(msg, self)
            return

        # Load the database into an Album
        album, geometry = self.db.load(dbfile)
        if album in (False, None):
            # There was an error
            warning_box(geometry, self)

        # Close the exiting database
        self.closeDatabase()

        # Set up the PhotoDatabase instance
        self.db.setDatabaseFile(dbfile)

        # Set the new dataset
        self.model.changeDataSet(album)

        # Make sure table is visible
        if self.view.isHidden():
            self.mainWidget.setHidden(False)
            self.view.setHidden(False)
            self.treeView.setHidden(False)
            self.labelNoDatabase.setHidden(True)
            self.labelNoPhotos.setHidden(True)

        # Restore the table geometry
        if geometry:
            hh = self.horizontalHeader
            hh.restoreState(QtCore.QByteArray(str(geometry)))

        self.statusbar.showMessage('Finished Loading', 4000)
        self.setWidthHeight()
        self.actionImportFolder.setEnabled(True)
        self.setDateRange()
        self.saveAppData()
        self.setWidgetVisibility()
        self.view.rehideColumns()
        self.updateWindowTitle()

        self.treeView.expandAll()

    ######################
    #  Helper Functions  #
    ######################

    def clearFilters(self):
        self.groupDateFilter.setChecked(False)
        self.editFilter.clear()

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
            self.editFilter.setText(pattern)

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

    def setDateRange(self):
        """ Set the date edits for a range """
        def timestamp(x):
            try:
                dt = datetime.strptime(x['Date'], '%Y:%m:%d %H:%M:%S')
                return dt.toordinal()
            except ValueError:
                return

        timestamps = [k for k in map(timestamp, self.album) if k]
        if timestamps:
            self.dateFrom.setDate(datetime.fromordinal(min(timestamps)))
            self.dateTo.setDate(datetime.fromordinal(max(timestamps)))

    def setWidgetVisibility(self):
        """
        Set the visibility of widgets based on other widget or data states
        """
        checkDate = self.checkDateRange.isChecked()
        self.labelTo.setVisible(checkDate)
        self.dateTo.setVisible(checkDate)

    def updateWindowTitle(self):
        """ Set the window title """
        if self.databaseFile:
            with self.db.connect() as con:
                cur = con.execute('SELECT Name from Database')
                name = os.path.splitext(cur.fetchone()[0])[0]
                self.setWindowTitle('Photo Organizer - {}'.format(name))

    #####################
    #       SLOTS       #
    #####################

    @QtCore.pyqtSlot()
    def on_actionBatchTag(self):
        """ Add tags to a batch of files

        Slot for actionBatchTag
        """
        # Show the dialog and get the new tags
        selection = self.view.selectedIndexes()
        source = [self.proxy.mapToSource(i) for i in selection]
        selectedRows = list(set([k.row() for k in source]))
        fields = [k.name for k in self.fields if k.editable and
                  k.editor == FieldObject.LineEditEditor]
        dlg = BatchTag(fields, self)
        st = dlg.exec_()
        if st == dlg.Rejected:
            return

        markTagged = dlg.checkMarkTagged.isChecked()

        # Get a dictionary of new tags with field namess as keys
        newTags = {}
        for field in fields:
            newTagStr = str(dlg.edits[field].text())
            if newTagStr:
                newTags[field] = [k.strip() for k in re.split(';|,', newTagStr)
                                  if k.strip() != '']

        if markTagged:
            newTags[self.album.taggedField] = QtCore.QVariant(True)

        # Batch-add the tags
        self.model.batchAddTags(selectedRows, newTags)

    @QtCore.pyqtSlot()
    def on_changeLog(self):
        os.startfile('ChangeLog.txt')

    @QtCore.pyqtSlot(int)
    def on_checkDateChanged(self, state):
        """ Set whether the proxy  model matches a date or date range

        A slot for the range checkbox's stateChanged signal

        Arguments:
            state (int): QtCore.Qt.CheckState (Checked means use range)
        """
        self.setWidgetVisibility()
        self.proxy.setDateBetween(state == QtCore.Qt.Checked)

    @QtCore.pyqtSlot()
    def on_clearFilter(self):
        """ Clear the line edit and tree view """
        self.editFilter.clear()
        self.treeView.uncheckAll()

    @QtCore.pyqtSlot(int)
    def on_comboDate(self, filt):
        """ Set the proxy model's date filter type

        A slot for the combobox's currentIndexChanged signal

        Arguments:
            filt (int): The filter setting. Should align with
                AlbumSortFilterModel.<>Filter properties.
        """
        self.proxy.setDateFilterType(filt)
        displayFormats = {0: 'yyyy', 1: 'yyyy-MM', 2: 'yyyy-MM-dd'}
        self.dateFrom.setDisplayFormat(displayFormats[filt])
        self.dateTo.setDisplayFormat(displayFormats[filt])

    @QtCore.pyqtSlot(list, list)
    def on_albumDataChanged(self, fileIds, fieldnames):
        """ Update the database when user changes data

        Slot for model.dataChanged

        Arguments:
            fileIds (list): A list of database file ids
            fieldnames (list): A list of field names
        """
        QtGui.qApp.processEvents()
        self.db.updateAlbum(self.album, fileIds, fieldnames)

        self.treeView.updateTree()
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
        row = index.row()
        allFiles = []
        for k in range(self.proxy.rowCount()):
            i = self.proxy.mapToSource(self.proxy.index(k, 0))
            r = i.row()
            allFiles.append(os.path.join(self.album[r, 'Directory'],
                                         self.album[r, 'File Name']))

        self.imageViewer.setImage(allFiles, row)

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
    def on_helpAbout(self):
        """ Create the program about menu and display it """
        mess_str = ("<b>Photo Organizer</b> v{}"
                    "<p>Developed by Luke McNinch (lcmcinch@yahoo.com)"
                    "<p>Python {} - Qt {} - PyQt {}")
        mess_format = mess_str.format(__release__, platform.python_version(),
                                      QtCore.QT_VERSION_STR,
                                      QtCore.PYQT_VERSION_STR)
        QtGui.QMessageBox.about(self, "About Photo Organizer", mess_format)

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
                self.treeView.setHidden(False)
                self.labelNoPhotos.setHidden(True)
            self.importFolder(str(folder), self.databaseFile)

    @QtCore.pyqtSlot(str)
    def on_editFilter_textChanged(self, pattern):
        """Set the filter

        Slot for the line edit

        Arguments:
            pattern (str): The pattern for the regular expression
        """
        search = QtCore.QRegExp(pattern,
                                QtCore.Qt.CaseInsensitive,
                                QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(search)

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
        self.closeDatabase()
        if os.path.exists(dbfile):
            os.remove(dbfile)
        create_database(dbfile)

        # Re-set the dataset
        self.model.changeDataSet(Album())

        # Store the database and set up window/menus
        self.db.setDatabaseFile(dbfile)
        self.db.setFields(self.fields)
        self.labelNoDatabase.setHidden(True)
        self.mainWidget.setHidden(False)
        self.actionImportFolder.setEnabled(True)
        self.view.rehideColumns()
        self.updateWindowTitle()

    @QtCore.pyqtSlot()
    def on_newField(self):
        """ Add a new field to the database and table """
        name = QtGui.QInputDialog.getText(self, 'New Field', 'Field Name')[0]
        if not name:
            return
        if name.toLower() in [k.lower() for k in self.field_names]:
            msg = 'Duplicate field "{}"'.format(name)
            warning_box(msg, self)
            return
        command = undo.newFieldCmd(self, name)
        self.undoStack.push(command)

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

    @QtCore.pyqtSlot(int)
    def on_sliderValueChanged(self, size):
        """Resize the image thumbnails. Slot for the slider

        Arguments:
            size (int): The desired square size of the thumbnail in pixels
        """
        self.setWidthHeight(size)

    @QtCore.pyqtSlot()
    def on_treeDataChanged(self):
        """ Handle changes to the tree view data"""
        self.treeProxy.invalidate()

        # Set the line edit filter
        tags = self.treeModel.getCheckedTagNames()
        self.editFilter.setText(' '.join(tags))

    @QtCore.pyqtSlot()
    def on_undoList(self):
        """ Display the undo dialog

        Slot for the menu action
        """
        self.undoDialog.show()

    #####################
    #     PROPERTIES    #
    #####################

    @property
    def album(self):
        return self.model.dataset

    @property
    def databaseFile(self):
        return self.db.dbfile

    @property
    def fields(self):
        return self.album.fields

    @property
    def field_names(self):
        return self.album.field_names

    @property
    def iconSize(self):
        size = self.view.iconSize()
        return max(size.width(), size.height())


if __name__ == "__main__":
    import sys

    app = QtGui.QApplication(sys.argv)
    main = PhotoOrganizer()
#     main = PhotoOrganizer('TestDb2.db')
    main.resize(800, 600)
    main.show()

#     directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
#     main.populate(directory)
#     main.openDatabase('WithImportTime.pdb')
#     main.on_newDatabase()

    sys.exit(app.exec_())
