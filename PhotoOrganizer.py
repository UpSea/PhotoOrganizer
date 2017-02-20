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
from Dialogs import WarningDialog, warning_box, BatchTag
from database import PhotoDatabase
from create_database import create_database
from datetime import datetime
import pdb
from pkg_resources import parse_version
import time


class PhotoOrganizer(QtGui.QMainWindow, uiclassf):
    """An application for filtering image data and thumbnails"""

    def __init__(self, dbfile=None, parent=None):
        super(PhotoOrganizer, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Photo Organizer')
        self.db = PhotoDatabase(dbfile)
        self.mainWidget.setHidden(True)
        self.view.setHidden(True)

        # Setup application organization and application name
        app = QtGui.QApplication.instance()
        app.setOrganizationName(organization)
        app.setApplicationName(application)

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
        album = Album()
        self.model = AlbumModel(album)

        self.model.dataChanged.connect(self.on_dataChanged)
        self.proxy = AlbumSortFilterModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(2)

        self.view.setIconSize(QtCore.QSize(100, 100))
        self.view.setModel(self.proxy)
        self.view.setSortingEnabled(True)
        self.view.setItemDelegate(AlbumDelegate())
        self.view.rehideColumns()

        # Signal Connections
        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
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
        settings = QtCore.QSettings()
        self.restoreGeometry(settings.value("MainWindow/Geometry").toByteArray())
        dbfile = self.databaseFile or settings.value("lastDatabase").toString()
        if dbfile:
            self.openDatabase(str(dbfile), False)

    def closeEvent(self, event):
        """ Re-implemented to save settings """
        # Save general App settings
        settings = QtCore.QSettings()
        settings.clear()
        settings.setValue("MainWindow/Geometry", QtCore.QVariant(
                          self.saveGeometry()))
        settings.setValue("lastDatabase", QtCore.QVariant(self.databaseFile))

        # Close the current album
        self.closeDatabase()

    def closeDatabase(self):
        """ Close the current album to prepare to open another """
        # Close child windows
        self.imageViewer.close()

        # Save fields
        if self.databaseFile is None:
            return

        field_props = FieldObjectContainer.fieldProps
        props = ', '.join(field_props)
        i = 'INSERT INTO Fields ({}) VALUES (?,?,?,?,?,?,?)'.format(props)
        with self.db.connect() as con:
            cur = con.execute('SELECT Name FROM Fields')
            dbfields = [k[0] for k in cur]
            uparams = ', '.join(['{} = ?'.format(k) for k in field_props])
            u = ('UPDATE Fields SET {} WHERE Name=?'.format(uparams))
            icommands = []
            ucommands = []
            for f in self.fields:
                values = [f.name, f.required, f.editor, f.editable,
                          f.name_editable, f.hidden, f.filter]
                if f.name in dbfields:
                    ucommands.append(values+[f.name])
                else:
                    icommands.append(values)
            # Execute many for speed
            if icommands:
                con.executemany(i, icommands)
            if ucommands:
                con.executemany(u, ucommands)

            # Remove deleted fields
            df = [k for k in dbfields if k not in self.fields.names]
            dcommands = []
            for f in df:
                dcommands.append((f,))
            if dcommands:
                con.executemany('DELETE FROM Fields WHERE Name = ?', dcommands)

        # Save database-specific settings
        self.saveAppData()
        self.db.setDatabaseFile(None)

    def saveAppData(self):
        """ Save database-specific settings """
        if self.databaseFile is None:
            return
        with self.db.connect() as con:
            cur = con.cursor()
            q = ('UPDATE AppData SET AppFileVersion=?, AlbumTableState=?')
            headerState = sqlite3.Binary(self.horizontalHeader.saveState())
            cur.execute(q, (__release__, headerState))

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

    def openDatabase(self, dbfile, close=False):
        """ Open a database file and populate the album table

        Arguments:
            dbfile (str): The path to the database file
        """
        if not os.path.exists(dbfile):
            msg = 'Database File Not Found'
            warning_box(msg, self)
            return

        # Create the query strings
        cnt = 'SELECT count(*) FROM File'
        qry = 'SELECT directory, filename, date, hash, thumbnail, FilId, '+\
              'tagged, datetime(importTimeUTC, "localtime") FROM File'
        try:
            con = self.db.connect(dbfile)
        except:
            warning_box('Cannot open {}'.format(self.databaseFile), self)

        with con:
            q = 'SELECT AppFileVersion FROM AppData'
            try:
                version = con.execute(q).fetchone()[0]
            except:
                version = 0
            if compareRelease(version, '0.2') < 0:
                warning_box('This version of Photo Organizer is not ' +
                            'compatible with the database you chose.', self)
                return

            # Close the exiting database
            if close:
                self.closeDatabase()

            # Make sure table is visible
            if self.view.isHidden():
                self.mainWidget.setHidden(False)
                self.view.setHidden(False)
                self.labelNoDatabase.setHidden(True)
                self.labelNoPhotos.setHidden(True)

            # Set up the PhotoDatabase instance
            self.db.setDatabaseFile(dbfile)

            # Get the fields and create the new Album instance
            cur = con.execute('SELECT Name, Required, Editor, Editable, '+
                              'Name_Editable, Hidden, Filt FROM Fields')
            param_values = [list(k) for k in cur]
            params = [k[0].lower() for k in cur.description]
            vals = map(list, zip(*param_values))
            param_dicts = dict(zip(params, vals))
            fields = FieldObjectContainer(**param_dicts)
            self.model.changeDataSet(Album(fields))

            # Define the tag query string
            tqry = 'SELECT t.Value FROM File as f '+\
                   'JOIN TagMap as tm ON f.FilId == tm.FilId '+\
                   'JOIN Tags as t ON tm.TagId == t.TagId '+\
                   'JOIN Categories as c ON t.CatId == c.CatId '+\
                   'WHERE f.FilId == ? and c.Name == ?'

            # Get the categories and their fields
            categories = self.db.getTableAsDict('Categories', onePer=True)

            # Get the Photos and populate the Album
            cur2 = con.cursor()
            cur.execute(cnt)
            count = cur.fetchone()[0]
            fileCur = con.execute(qry)
            k = 0
            for row in fileCur:
                k += 1
                directory = row[0]
                fname = row[1]
                date = row[2]
                hsh = row[3]
                data = row[4]
                fileId = row[5]
                tagged = bool(row[6])
                insertDate = row[7]
                fp = BytesIO(data)

                # Create the QPixmap from the byte array
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
                updateValues(values, 'Tagged', tagged)
                updateValues(values, 'Import Date', insertDate)

                for cat in categories:
                    # Get the tags and group with categories
                    catname = cat['Name']
                    cur2.execute(tqry, [fileId, catname])
                    tagList = cur2.fetchall()
                    tags = '; '.join([t[0] for t in tagList])
                    updateValues(values, catname, tags)

                self.model.insertRows(self.model.rowCount(), 0,
                                      Photo(self.fields, values, thumb))

                msg = 'Importing Photo %d of %d' % (k, count)
                self.statusbar.showMessage(msg)

                # Allow the application to stay responsive and show the progress
                QtGui.QApplication.processEvents()

            # Restore the table geometry
            q_geo = 'SELECT AlbumTableState from AppData'
            cur.execute(q_geo)
            geometry = cur.fetchone()
            if geometry:
                hh = self.horizontalHeader
                hh.restoreState(QtCore.QByteArray(str(geometry[0])))

        self.statusbar.showMessage('Finished Loading', 4000)
        self.setWidthHeight()
        self.actionImportFolder.setEnabled(True)
        self.setDateRange()
        self.saveAppData()
        self.setWidgetVisibility()
        self.view.rehideColumns()
        self.updateWindowTitle()

    ######################
    #  Helper Functions  #
    ######################

    def clearFilters(self):
        self.groupDateFilter.setChecked(False)
        self.lineEdit.clear()

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

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_dataChanged(self, topLeft, bottomRight):
        """ Update the database when user changes data

        Slot for model.dataChanged
        """
        # Setup variables
        left = topLeft.column()
        right = bottomRight.column()
        top = topLeft.row()
        bottom = bottomRight.row()
        fidCol = self.fields.index('FileId')

        # Set up batch queries
        taggedQ = 'UPDATE File SET Tagged = ? WHERE FilId == ?'
        taggedParams = []

        insertQ = 'INSERT INTO Tags (CatId, Value) VALUES (?,?)'
        insertParams = []
        mapParams1 = []

        delMapQ = "DELETE From TagMap WHERE FilId == ? AND "+\
                  "(SELECT Value FROM Tags as t WHERE "+\
                  "t.TagId == TagMap.TagId AND t.CatId == ?) "+\
                  "NOT IN ({})"
        delMaps = []

        # Current categories and tags
        with self.db.connect() as con:
            # Get the category fields by ID and Column
            fieldnames = [self.fields[c].name for c in range(left, right+1)]
            fieldstr = ','.join([str('\''+k+'\'') for k in fieldnames])
            catQ = 'SELECT Name, CatId from Categories WHERE Name in (%s)' % fieldstr

            res = con.execute(catQ).fetchall()
            catNames = [k[0] for k in res]
            catIds = [k[1] for k in res]
            catCols = [self.fields.index(k) for k in catNames]

            # Get all tags for each category
            catstr = ','.join([str(k) for k in catIds])
            tagQ = 'SELECT CatId, TagId, Value FROM Tags WHERE CatId IN (%s)' % catstr
            alltags = con.execute(tagQ).fetchall()

        # Loop over each index in the range and prepare for database calls
        for row in range(top, bottom+1):
            # Get the FilId for the current row
            fileId = self.model.data(self.model.index(row, fidCol)).toInt()[0]

            for col in range(left, right+1):
                # Get the field and index of the current cell
                field = self.fields[col]
                index = self.model.index(row, col)
                if field.name == self.album.taggedField:
                    # Handle the "tagged" checkboxes
                    value = index.data().toBool()
                    taggedParams.append((1 if value else 0, fileId))
                else:
                    # Handle the tag cagetories
                    # Skip any field that isn't a tag category
                    if col not in catCols:
                        # Not a "category" field
                        continue
                    catDex = catCols.index(col)
                    catId = catIds[catDex]

                    # Get the current tags, including changes
                    cur_tags = [k.strip() for k in
                                re.split(';|,', str(index.data().toPyObject()))
                                if k.strip() != '']
                    existing = {k[2].lower(): k[1] for k in alltags
                                if k[0] == catId}
                    for tag in cur_tags:
                        if tag.strip() == '':
                            continue
                        cat_tag = (catId, tag)
                        if (tag.lower() not in existing and
                                cat_tag not in insertParams):
                            # INSERT new tag
                            insertParams.append(cat_tag)
                        mapParams1.append((fileId, cat_tag))

                    # Set up to remove deleted tags in this category and file
                    params = ','.join(['?'] * len(cur_tags))
                    q = delMapQ.format(params)
                    delMaps.append((q, [fileId, catId] + cur_tags))

        # Update the tagged status and insert the new tags
        with self.db.connect() as con:
            con.executemany(taggedQ, taggedParams)
            con.executemany(insertQ, insertParams)

            # Get the TagIds
            alltags = con.execute(tagQ).fetchall()
            tagIds = {(k[0], k[2]): k[1] for k in alltags}
            mapParams = [(k[0], tagIds[k[1]]) for k in mapParams1]

            # Insert Tag mapping (ON CONFLICT IGNORE)
            tagMapQ = 'INSERT OR IGNORE INTO TagMap (FilId, TagId) VALUES (?,?)'
            con.executemany(tagMapQ, mapParams)

            # Delete removed tags
            for q, params in delMaps:
                con.execute(q, params)

            # Remove them unused tags
            q = 'DELETE FROM Tags WHERE TagId NOT IN '+\
                '(SELECT TagId FROM TagMap)'
            con.execute(q)

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
                self.labelNoPhotos.setHidden(True)
            self.importFolder(str(folder), self.databaseFile)

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

        # Re-set the dataset
        self.model.changeDataSet(Album())

        # Store the database and set up window/menus
        self.db.setDatabaseFile(dbfile)
        self.labelNoDatabase.setHidden(True)
        self.mainWidget.setHidden(False)
        self.actionImportFolder.setEnabled(True)
        self.view.rehideColumns()

    @QtCore.pyqtSlot()
    def on_newField(self):
        """ Add a new field to the database and table """
        name = QtGui.QInputDialog.getText(self, 'New Field', 'Field Name')[0]
        if not name:
            return
        self.model.insertColumns(name=str(name))
        newfield = self.fields[-1]
        newfield.filter = True
        self.db.insertField(newfield)

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


def compareRelease(a, b):
    """Compares two release numbers. Returns 0 if versions are the same, -1 if
    the a is older than b and 1 if a is newer than b"""
    a = parse_version(re.sub('\(.*?\)', '', a))
    b = parse_version(re.sub('\(.*?\)', '', b))
    if a < b:
        return -1
    elif a == b:
        return 0
    else:
        return 1


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
