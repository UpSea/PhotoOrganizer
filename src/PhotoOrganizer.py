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
from BatchDialog import BatchTag
from datastore import (AlbumModel, Photo, AlbumDelegate,
                       AlbumSortFilterModel, PhotoDatabase)
from datetime import datetime
from Dialogs import WarningDialog, warning_box, UndoDialog
from genericdialogs import skipFileDialog, ProgressDialog
from glob import glob
import imagehash
from ImageMan import getThumbnailIcon
from Log import LogWindow
from moveCopy import Mover
import os
from PhotoViewer import ImageViewer
from PIL import Image
import platform
from send2trash import send2trash
from shared import (resource_path, __release__, organization, application,
                    BUILD_TIME, frozen, installDir, trashDir)
import sqlite3
from TagEditor import TagEditor
import undo
import pdb


class PhotoOrganizer(QtGui.QMainWindow, uiclassf):
    """An application for filtering image data and thumbnails"""

    def __init__(self, dbfile=None, useLogWindow=True, parent=None):
        super(PhotoOrganizer, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Photo Organizer')
        poIcon = QtGui.QIcon(resource_path(r'icons\PO.ico'))
        self.setWindowIcon(poIcon)
        self.db = PhotoDatabase(dbfile, self)
        self.useLogWindow = useLogWindow
        self.mainWidget.setHidden(True)
        self.view.setHidden(True)
        self.treeView.setHidden(True)
        self.treeView.sourceModel.setHorizontalHeaderLabels(['Filter by Tags'])

        # Set up logging
        self._logfile = 'POLog.log'
        if frozen:
            self._logfile = os.path.join(installDir, self._logfile)
            if not os.path.exists(installDir):
                os.makedirs(installDir)
        self.logWindow = LogWindow(self._logfile, self)
        self.actionLog.triggered.connect(self.logWindow.showAndRestore)

        # Setup application organization and application name
        app = QtGui.QApplication.instance()
        app.setOrganizationName(organization)
        app.setApplicationName(application)

        # Default settings
        self.options = {'importFolder': os.path.expanduser("~")}

        # Set up the widgets
        self.slider.setRange(20, 400)
        self.slider.setValue(100)
        self.slider.valueChanged.connect(self.on_sliderValueChanged)

        # Set up menus
        self.menuOrganize.addAction(self.view.actionBatchTag)

        # Add icons
        actionicons = [(self.actionNewDatabase, r'icons\New.ico'),
                       (self.actionOpenDatabase, r'icons\Open.ico')]
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

        copy = QtGui.QIcon(resource_path(r'icons\copy.png'))
        self.actionCopyPhotos = QtGui.QAction(copy, 'Copy To', self.menuEdit)
        self.menuEdit.addAction(self.actionCopyPhotos)
#         move = QtGui.QIcon(resource_path(r'icons\move.png'))
#         self.actionMovePhotos = QtGui.QAction(move, 'Move To', self.menuEdit)
#         self.menuEdit.addAction(self.actionMovePhotos)

        # Instantiate an empty dataset and model
        self.model = AlbumModel(self.db)
        self.model.undoStack = self.undoStack
        # This connection is needed because when renaming tags, dataChanged
        # wouldn't result in updating the view.
        self.model.dataChanged.connect(self.view.viewport().repaint)

        self.proxy = AlbumSortFilterModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setDynamicSortFilter(True)

        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegate(AlbumDelegate())
        self.view.rehideColumns()

        # Set up the toolbar
        self.toolBar.addAction(self.actionUndo)
        self.toolBar.addAction(self.actionRedo)
        self.toolBar.addAction(self.actionCopyPhotos)
#         self.toolBar.addAction(self.actionMovePhotos)

        def add_shortcut(action):
            shortcut = action.shortcut().toString()
            if shortcut:
                sc = action.toolTip() + ' ({})'.format(shortcut)
                action.setToolTip(sc)
        map(add_shortcut, self.toolBar.actions())

        # Set up tree view model
        self.treeView.setDb(self.db)
        self.treeProxy = self.treeView.model()
        self.treeModel = self.treeProxy.sourceModel()
        self.proxy.setFilterList(self.treeView)

        # Create the image viewer window
        self.imageViewer = ImageViewer(albumModel=self.model, main=self)
        self.imageViewer.setWindowIcon(poIcon)
        self.imageViewer.treeView.setMode(self.treeView.TagMode)
        self.imageViewer.treeView.setDb(self.db)

        # Signal Connections
        self.editFilter.textChanged.connect(self.on_editFilterTextChanged)
        self.view.doubleClicked.connect(self.on_doubleClick)
        self.actionImportFolder.triggered.connect(self.on_importFolder)
        self.actionImportFiles.triggered.connect(self.on_importFiles)
        self.actionNewDatabase.triggered.connect(self.on_newDatabase)
        self.actionOpenDatabase.triggered.connect(self.on_openDatabase)
        self.view.actionBatchTag.triggered.connect(self.on_actionBatchTag)
        self.actionAbout.triggered.connect(self.on_helpAbout)
        self.actionKeyboard_Shortcuts.triggered.connect(self.on_keyboardShortcuts)
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
        self.treeModel.dataChanged.connect(self.treeProxy.invalidate)
        self.treeModel.dataChanged.connect(self.proxy.invalidate)
        self.buttonClearFilter.clicked.connect(self.on_clearFilter)
        self.actionUndoList.triggered.connect(self.on_undoList)
        self.db.sigNewDatabase.connect(self.treeView.newConnection)
        self.db.sigNewDatabase.connect(self.imageViewer.treeView.newConnection)
        self.actionCopyPhotos.triggered.connect(self.on_copyPhotos)
#         self.actionCopyPhotos.triggered.connect(self.on_movePhotos)
        self.actionEditTags.triggered.connect(self.on_editTags)

        # Set the horizontal header for a context menu
        self.horizontalHeader = self.view.horizontalHeader()
        self.verticalHeader = self.view.verticalHeader()

        # Setup the date filters
        self.comboDateFilter.addItems(['Year', 'Month', 'Day'])
        self.comboDateFilter.setCurrentIndex(1)
        self.on_comboDate(self.proxy.MonthFilter)
        self.checkDateRange.setChecked(True)
        self.on_checkDateChanged(QtCore.Qt.Checked)
        self.proxy.setDateFilterStatus(self.groupDateFilter.isChecked())

        QtCore.QTimer.singleShot(0, self.firstShow)

    def firstShow(self):
        """ Re-implemented to restore window geometry when shown """
        # Restore the window geometry
        settings = QtCore.QSettings()
        options = settings.value("options").toPyObject()
        if options:
            for k, v in options.iteritems():
                if str(k) in self.options:
                    if isinstance(v, QtCore.QString):
                        v = str(v)
                    self.options[str(k)] = v
        self.restoreGeometry(settings.value("MainWindow/Geometry").toByteArray())
        # Restore the toolbar settings
        tb = settings.value('toolbarShowing')
        state = tb.toBool() if tb.toPyObject() else True
        self.actionToolbar.setChecked(state)
        self.toolBar.setVisible(state)
        # Restore the database
        dbfile = self.databaseFile or settings.value("lastDatabase").toString()
        if dbfile:
            self.openDatabase(str(dbfile))

        # Redirect stdout and stderr
        # Do this now because if there's a failure before now, there won't be
        # any way to see it
        if self.useLogWindow:
            self.logWindow.setupOutput()

    def closeEvent(self, event):
        """ Re-implemented to save settings """
        # Handle trashed files
        trashfiles = os.listdir(trashDir)
        if trashfiles:
            dlg = WarningDialog('Trash Files', self)
            dlg.setText('The following files deleted by Photo Organizer '
                        'are stored here:\n{}'.format(trashDir))
            dlg.setQuestionText('Do you want to move them to the Recycle Bin?')
            dlg.setDetailedText('\n'.join(trashfiles))
            dlg.addButton("Don't Recycle", dlg.buttonBox.AcceptRole)
            rec = dlg.addButton('Recycle', dlg.buttonBox.AcceptRole)
            dlg.addButton(dlg.buttonBox.Cancel)
            rec.setDefault(True)
            if dlg.exec_():
                if dlg.clickedButton() == rec:
                    trsh = [os.path.join(trashDir, k) for k in trashfiles]
                    map(send2trash, trsh)
            else:
                event.setAccepted(False)
                return

        # Save general App settings
        settings = QtCore.QSettings()
        settings.clear()
        settings.setValue("options", QtCore.QVariant(self.options))
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

        # Reset the stdout and stderr
        self.logWindow.resetOutput()
        self.logWindow.close()

    def closeDatabase(self):
        """ Close the current album to prepare to open another """
        # Close child windows
        self.imageViewer.close()
        self.undoDialog.close()

        if self.databaseFile is None:
            return

        # Save database-specific settings
        self.saveAppData()
        # Close database connections
        self.treeView.con.close() #Need to figure out a way to have this in PhotoDatabase
        self.imageViewer.treeView.con.close()

        # Close the current album and database
        self.model.changeDatabase(None)
        
        # Clear the undo stack
        self.undoStack.clear()

    def saveAppData(self):
        """ Save database-specific settings """
        headerState = sqlite3.Binary(self.horizontalHeader.saveState())
        kwargs = {'AppFileVersion': __release__,
                  'BuildDate': BUILD_TIME,
                  'AlbumTableState': headerState}
        self.db.updateAppData(**kwargs)

    ########################
    #   Album Operations   #
    ########################

    def importFolder(self, directory):
        """Populate the table with images from directory

        Arguments:
        directory (str): The directory containing the desired image files
        """
        # Get the list of images with valid extensions
        images = []
        for extension in QtGui.QImageReader().supportedImageFormats():
            pattern = os.path.join(directory, '*.%s' % str(extension))
            images.extend(glob(pattern))

        self.importFiles(images)

    def importFiles(self, images):
        """ Populate the table with images from files

        Arguments:
            images ([str]): A list of full paths to image files
        """
        exHash = {(k['File Name'], k['Hash']): k.fileId for k in self.album}
        exFiles = [os.path.join(k['Directory'], k['File Name'])
                   for k in self.album]

        # Loop over all images and add to the table
        changeDir = []
        for k, path in enumerate(images):
            # See if this file is already in the database
            if path in exFiles:
                continue

            # Split off the filename
            directory, fname = os.path.split(path)

            # Read the scaled image into a byte array
            im = Image.open(path)
            try:
                exif = im._getexif()
            except Exception:
                exif = None
            hsh = imagehash.average_hash(im)
            exHashKey = (fname, str(hsh))
            if exHashKey in exHash:
                changeDir.append((path, exHash[exHashKey]))
                continue
            # Try to get date from exif
            date = None
            if exif and 36867 in exif:
                ds = exif[36867]
                try:
                    dt = datetime.strptime(ds, '%Y:%m:%d %H:%M:%S')
                    date = dt.strftime('%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass

            if date is None:
                # Use modified time (not as reliable)
                timestamp = os.path.getmtime(path)
                dt = datetime.fromtimestamp(timestamp)
                date = dt.strftime('%Y-%m-%d %H:%M:%S')

            thumb = getThumbnailIcon(path)

            # Create the values list based on the order of fields
            def updateValues(values, name, val):
                values[self.fields.index(name)] = val

            values = ['' for _ in self.fields]
            updateValues(values, 'Directory', directory)
            updateValues(values, 'File Name', fname)
            updateValues(values, 'Date', date)
            updateValues(values, 'Hash', str(hsh))
            updateValues(values, 'Tagged', False)

            self.model.insertRows(Photo(self.fields, values, thumb))

            msg = 'Importing Photo %d of %d' % (k+1, len(images))
            self.statusbar.showMessage(msg)

            # Allow the application to stay responsive and show the progress
            QtGui.QApplication.processEvents()

        self.statusbar.showMessage('Finished Import', 5000)

        if changeDir:
            dlg = WarningDialog('Matching Files Found', self)
            msg = 'The following {} files appear to exist in the database '+ \
                  'but are located in a different folder.\n'+ \
                  'Their location (directory) in the database can be updated. '+ \
                  "The image files won't be moved"
            dlg.setText(msg.format(len(changeDir)))
            dlg.setQuestionText('Do you want to update? Ignore to skip these '
                                'files')
            detail = '\n'.join([j[0] for j in changeDir])
            dlg.setDetailedText(detail)
            yesbut = dlg.addButton(QtGui.QDialogButtonBox.Yes)
            dlg.addButton(QtGui.QDialogButtonBox.Ignore)
            dlg.exec_()

            if dlg.clickedButton() == yesbut:
                col, rowrange = self.db.relocateFiles(changeDir)
                sidex = self.model.index(col, rowrange[0])
                eidex = self.model.index(col, rowrange[1])
                self.model.dataChanged.emit(sidex, eidex)

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

        # Close the exiting database
        self.closeDatabase()

        # Set the new dataset
        st, msg = self.model.changeDatabase(dbfile)
        if not st:
            warning_box('DB failed to open:\n%s' % msg, self)
            return

        # Make sure table is visible
        if self.view.isHidden():
            self.mainWidget.setHidden(False)
            self.view.setHidden(False)
            self.treeView.setHidden(False)
            self.labelNoDatabase.setHidden(True)
            self.labelNoPhotos.setHidden(True)

        # Restore the table geometry
        geometry = self.db.geometry()
        if geometry:
            hh = self.horizontalHeader
            hh.restoreState(QtCore.QByteArray(str(geometry)))

        self.statusbar.showMessage('Finished Loading', 4000)
        self.setWidthHeight()
        self.actionImportFolder.setEnabled(True)
        self.actionImportFiles.setEnabled(True)
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
                return x.datetime.toordinal()
            except (ValueError, TypeError, AttributeError):
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
        title = 'Photo Organizer'
        if self.databaseFile:
            title += ' - {}'.format(self.databaseFile)
        self.setWindowTitle(title)

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

        fileIds = [self.album[k].fileId for k in selectedRows]
        dlg = BatchTag(self.db, self)
        dlg.treeView.checkFileTags(fileIds)
        st = dlg.exec_()
        if st == dlg.Rejected:
            return

        markTagged = dlg.checkMarkTagged.isChecked()
        markUntagged = dlg.checkUnmarkTagged.isChecked()

        # Get a dictionary of new tags with field names as keys
        checkedTags = dlg.treeView.getCheckedTagDict(QtCore.Qt.Checked)
        uncheckedTags = dlg.treeView.getCheckedTagDict(QtCore.Qt.Unchecked)

        if markTagged:
            checkedTags[self.album.taggedField] = QtCore.QVariant(True)

        if markUntagged:
            checkedTags[self.album.taggedField] = QtCore.QVariant(False)

        # Batch-add the tags
        self.model.batchAddTags(selectedRows, checkedTags, uncheckedTags)

    @QtCore.pyqtSlot()
    def on_changeLog(self):
        os.startfile(resource_path('ChangeLog.txt'))

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

    @QtCore.pyqtSlot()
    def on_copyPhotos(self):
        """ Prompt the user to chose a directory and copy all files in current
        filter to that folder
        """
        # Prompt user
        gxd = QtGui.QFileDialog.getExistingDirectory
        folder = str(gxd(self, "Export Folder", self.options['importFolder']))
        if not folder:
            return  # Canceled

        # Get all the files
        doAll = False
        nFiles = self.proxy.rowCount()

        def getSrcDest(row):
            i = self.proxy.mapToSource(self.proxy.index(row, 0))
            r = i.row()
            src = self.album[r].filePath
            fn = os.path.split(src)[1]
            return (src, os.path.join(folder, fn))

        allFiles = [getSrcDest(r) for r in range(nFiles)]

        # Handle conflicts
        conflicts = [k for k in allFiles if os.path.exists(k[1])]
        for k, paths in enumerate(conflicts):
            thisPath = paths[0]
            remaining = len(conflicts) - k - 1
            if not doAll:
                msgBox = skipFileDialog('File(s) Exist', thisPath)
                msg = 'File Exists:\n{}!'
                msgBox.setText(msg.format(thisPath))
                if remaining > 0:
                    msgBox.setCheckBoxValue(remaining)
                msgBox.checkBox.setChecked(k == 0)
                msgBox.exec_()
                doAll = msgBox.checkBox.isChecked()
            if msgBox.canceled:
                return
            elif msgBox.keep:
                i = allFiles.index(paths)
                allFiles[i] = (thisPath, os.path.join(folder, msgBox.newName))
            elif msgBox.skip:
                allFiles.remove(paths)

        # Copy the files with progress dialog
        mover = Mover(allFiles, Mover.COPY)
        copyProgress = ProgressDialog(mover, 'Copying Files', 3, parent=self)
        copyProgress.exec_()

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
            allFiles.append(self.album[r])

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
    def on_editFilterTextChanged(self):
        """Set the filter

        Slot for the line edit

        Arguments:
            pattern (str): The pattern for the regular expression
        """
        QtGui.qApp.processEvents()
        pattern = self.editFilter.text()
        if pattern == self.proxy.filterRegExp().pattern():
            return
        search = QtCore.QRegExp(pattern,
                                QtCore.Qt.CaseInsensitive,
                                QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(search)

    @QtCore.pyqtSlot()
    def on_editTags(self):
        """ Launch the tag editor dialog

        Slot for the Edit Tags menu action
        """
        tagEditor = TagEditor(self.model, self)
        tagEditor.exec_()

    @QtCore.pyqtSlot()
    def on_helpAbout(self):
        """ Create the program about menu and display it """
        mess_str = ("<b>Photo Organizer</b> v{}"
                    "<p>Developed by Luke McNinch (lcmcninch@yahoo.com)"
                    "<p>Python {} - Qt {} - PyQt {} - sqlite3 {} - sqlite {}"
                    "<p> {}")
        mess_format = mess_str.format(__release__, platform.python_version(),
                                      QtCore.QT_VERSION_STR,
                                      QtCore.PYQT_VERSION_STR,
                                      sqlite3.version, sqlite3.sqlite_version,
                                      BUILD_TIME)
        QtGui.QMessageBox.about(self, "About Photo Organizer", mess_format)

    @QtCore.pyqtSlot()
    def on_importFiles(self):
        """ Import photos from selected files

        Slot for actionImportFiles
        """

        formats = ["*.{0}".format(unicode(fileExt).lower()) for fileExt in QtGui.QImageReader.supportedImageFormats()]

        gofn = QtGui.QFileDialog.getOpenFileNames
        files = gofn(self, 'Import Files', self.options['importFolder'],
                     "Image files ({})".format(" ".join(formats)))
        if files:
            self.options['importFolder'] = os.path.split(str(files[0]))[0]
            if self.view.isHidden():
                self.view.setHidden(False)
                self.treeView.setHidden(False)
                self.labelNoPhotos.setHidden(True)
            self.importFiles(map(str, files))

    @QtCore.pyqtSlot()
    def on_importFolder(self):
        """ Import photos from a folder

        Slot for actionImportFolder
        """
        gxd = QtGui.QFileDialog.getExistingDirectory
        folder = gxd(self, "Import Folder", self.options['importFolder'])
        if folder:
            self.options['importFolder'] = os.path.split(str(folder))[0]
            if self.view.isHidden():
                self.view.setHidden(False)
                self.treeView.setHidden(False)
                self.labelNoPhotos.setHidden(True)
            self.importFolder(str(folder))

    @QtCore.pyqtSlot()
    def on_keyboardShortcuts(self):
        """ Create a dialog listing the available keyboard shortcuts """
        mess_str = ("""<b>Photo Organizer Keyboard Shortcuts</b>
                    <p>
                    <table>
                    <tr>
                    <td width=85>Shortcut</td><td width=150>Description</td><td width=75>Context</td>
                    </tr>
                    <tr>
                    <td>CTRL-G</td><td>Group Tag Selected Rows</td><td>Anywhere</td>
                    </tr><tr>
                    <td>CTRL-I</td><td>Insert Tag Field</td><td>Anywhere</td>
                    </tr><tr>
                    <td>CTRL-Q</td><td>Exit</td><td>Anywhere</td>
                    </tr><tr>
                    <td>CTRL-Y</td><td>Redo</td><td>Anywhere</td>
                    </tr><tr>
                    <td>CTRL-Z</td><td>Undo</td><td>Anywhere</td>
                    </tr><tr>
                    </tr>
                    </table>""")
        box = QtGui.QMessageBox(self)
        box.setWindowTitle('Keyboard Shortcuts')
        box.setText(mess_str)
        box.exec_()

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

        # Create the new database
        self.model.changeDatabase(dbfile)
        self.saveAppData()

        # Set up window/menus
        self.labelNoDatabase.setHidden(True)
        self.mainWidget.setHidden(False)
        self.actionImportFolder.setEnabled(True)
        self.actionImportFiles.setEnabled(True)
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
    def on_undoList(self):
        """ Display the undo dialog

        Slot for the menu action
        """
        self.undoDialog.show()

    @QtCore.pyqtSlot(object)
    def on_viewerDelete(self, photo):
        """ Delete a single photo """
        cmd = undo.removeRowCmd(self, photo)
        self.undoStack.push(cmd)

    #####################
    #     PROPERTIES    #
    #####################

    @property
    def album(self):
        return self.model.dataset.album

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
#     main = PhotoOrganizer()

    print '*** Log Window Not Used ***'
    main = PhotoOrganizer(useLogWindow=False)

    main.resize(800, 600)
    main.show()

#     directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
#     main.populate(directory)
#     main.openDatabase('WithImportTime.pdb')
#     main.on_newDatabase()

    sys.exit(app.exec_())
