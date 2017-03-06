from PyQt4 import QtCore, QtGui
from datetime import datetime, MAXYEAR, MINYEAR
import re

# Place holder
edit_role = QtCore.Qt.EditRole
model_idx = QtCore.QModelIndex


class AlbumModel(QtCore.QAbstractTableModel):
    """ A model for an Album table view """

    albumDataChanged = QtCore.pyqtSignal(list, list)

    def __init__(self, dataset, parent=None):
        """ Initialize Model """
        super(AlbumModel, self).__init__(parent)
        self.dataset = dataset
        self.undoStack = QtGui.QUndoStack()

    def columnCount(self, index=model_idx()):
        """ Model required function that returns the number of columns """
        return len(self.dataset.fields)

    def rowCount(self, index=model_idx()):
        """ Model required function that returns the number of rows """
        return len(self.dataset)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """ Model required function that returns data for a given index """
        if (role == QtCore.Qt.DisplayRole) or (role == QtCore.Qt.EditRole):
            k = self.dataset[index.row(), self.dataset.fields[index.column()]]
            return QtCore.QVariant(k)
#         elif role == QtCore.Qt.BackgroundRole:
#             if self.dataset[index.row()].scrapped:
#                 return QtCore.QVariant(QtGui.QColor(255, 0, 0, 123))
        elif role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                photo = self.dataset[index.row()]
                return photo.thumb
        elif role == QtCore.Qt.TextAlignmentRole:
            return (QtCore.Qt.AlignCenter)
        else:
            return QtCore.QVariant()

    def insertColumns(self, position=None, columns=0,
                      index=QtCore.QModelIndex(), name=None):
        """ Model required function for inserting columns

        Arguments:
            position (int):
            columns (int):
            index (QModelIndex):
            name (str, FieldObject):
        """
        if (position is None) or (position == -1):
            position = self.columnCount()
        self.beginInsertColumns(index, position, position + columns)
        self.dataset.insertField(position, name)
        self.endInsertColumns()
        return True

    def removeColumns(self, position, columns=0, index=model_idx(),
                      force=False):
        """ Model Function for removing columns

        If the field is required this method will return a false but not
        cause and error. If the force argument is given as True the specified
        field will be deleted no matter its required status.

        """
        field = self.dataset.fields[position]
        if field.required and (not force):
            return False
        else:
            self.beginRemoveColumns(index, position, position + columns)
            self.dataset.removeField(position, force)
            self.endRemoveColumns()
            return True

    def removeField(self, field, force=False):
        """  Allows for removing of columns by name """
        idx = self.dataset.field_names.index(field)
        result = self.removeColumns(idx, force=force)
        return result

    def insertRows(self, position=None, rows=0, entry=None, uuid=''):
        """ Model required function for inserting rows """
        if position is None:
            position = self.rowCount()
        self.beginInsertRows(QtCore.QModelIndex(), position, position + rows)
        if entry:
            self.dataset.insert(position, entry)
        else:
            self.dataset.addEntry(uuid=uuid)
        self.endInsertRows()
        return True

    def removeRows(self, position, rows=0, index=model_idx()):
        """ Model required function for removing rows """
        self.beginRemoveRows(QtCore.QModelIndex(), position, position + rows)
        self.dataset.removeEntry(position)
        self.endRemoveRows()
        return True

    def deleteCells(self, indexes):
        """ Custom function to delete the values from cells """
        command = deleteCmd(self, indexes)
        self.undoStack.push(command)

    def _getSetValue(self, field, value):
        """ Get the appropriate value for setting data

        Arguments:
            field (FieldObject)
            value (QVariant)
        """
        if field.editor == field.CheckBoxEditor:
            cvalue = value.toBool()
        elif field.editor == field.DateEditEditor:
            if value.type() in (value.Date, value.DateTime):
                cvalue = str(value.toPyObject().toString('yyyy-MM-dd'))
            else:
                # Throw out any value that doesn't match the format
                try:
                    cvalue = str(value.toString())
                    datetime.strptime(cvalue, '%Y-%m-%d')
                except ValueError:
                    cvalue = ''
        else:
            cvalue = str(value.toString())
        return cvalue

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """ Model required function that sets data changes passed to model

        Arguments:
            index (QModelIndex):
            value (QVariant):
            role (Qt::ItemDataRole):
        """
        field = self.headerData(index.column(), QtCore.Qt.Horizontal, 0)
        if field and index.isValid():
            command = setDataCmd(self, index, value, role)
            self.undoStack.push(command)
            return True
        else:
            return False

    def _setData(self, index, value, role=QtCore.Qt.EditRole):
        """A private method for directly setting data outside undo/redo

        This method is used by the setDataCmd but can also be used when
        undo/redo should be bypassed (ie. within another QUndoCommand)

        Same arguments as the public method
        """
        row = index.row()
        field = self.headerData(index.column(), QtCore.Qt.Horizontal, 0)
        if field and index.isValid():
            field = self.dataset.fields[index.column()]
            cvalue = self._getSetValue(field, value)
            photo = self.dataset[row]
            photo[field] = cvalue
            self.dataChanged.emit(index, index)
            self.albumDataChanged.emit([photo.fileId], [field.name])
            return True
        else:
            return False

    def batchAddTags(self, rows, values):
        """ Add tags to multiple cells

        A variation on setData for batches. If a value is QVariant, all rows
        for that field will be set to the data in QVariant. This is used for
        bool fields as well as undo.

        Emits a custom data changed signal
        containing a list of file ids and the values dict

        Arguments:
            rows ([int]): A list of row indexes
            values (dict): A dictionary with field names as keys and lists of
                tag strings, or QVariant as values
        """
        command = batchAddCmd(self, rows, values)
        self.undoStack.push(command)

    def _batchAddTags(self, rows, values, keep=True):
        """ A private method for batch-adding tags

        Same description and arguments as the public method
        """
        left = float('inf')
        right = 0
        top = min(rows)
        bottom = max(rows)
        if not isinstance(values, list):
            values = [values]*len(rows)
        old = [{f: None for f in values[0]} for _ in rows]
        # Loop over columns then rows to set the data for each index
        for fieldname in values[0]:
            col = self.dataset.fields.index(fieldname)
            field = self.dataset.fields[col]
            left = min(left, col)
            right = max(right, col)
            for r, row in enumerate(rows):
                newTags = values[r][fieldname]
                index = self.index(row, col)
                # Store old value as QVariant. Then on undo we just set
                # directly rather than figuring out the new tags
                old[r][fieldname] = index.data()
                if isinstance(newTags, QtCore.QVariant):
                    # Handle case where caller provided QVariant
                    cvalue = self._getSetValue(field, newTags)
                    old[r][fieldname] = index.data()
                else:
                    # Get the new tag string and make QVariant
                    oldTagStr = str(index.data().toPyObject())
                    oldTags = [k.strip() for k in re.split(';|,', oldTagStr)
                               if k.strip() != '']
                    replace = oldTags + [k for k in newTags
                                         if k not in oldTags]
                    cvalue = self._getSetValue(field,
                                               QtCore.QVariant('; '.join(replace)))
                # Set the data
                self.dataset[row, field] = cvalue
        topLeft = self.index(top, left)
        bottomRight = self.index(bottom, right)
        self.dataChanged.emit(topLeft, bottomRight)

        # Emit the custom data changed signal
        fileIds = [self.dataset[k].fileId for k in rows]
        self.albumDataChanged.emit(fileIds, values[0].keys())

        return old

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        """ Model required function that returns header data information """
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.FontRole:
                font = QtGui.QFont()
                font.setBold(self.dataset.fields[section].required)
                return QtCore.QVariant(font)
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self.dataset.field_names[section])
            if role == QtCore.Qt.BackgroundRole:
                return QtCore.QVariant(QtGui.QColor(255, 0, 0))
        else:
            if role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(int(section + 1))
        return QtCore.QVariant()

    def getHeaders(self, orientation):
        """ Return a list of the header strings for the give orientation """
        if orientation is QtCore.Qt.Horizontal:
            vec = xrange(self.columnCount())
        elif orientation is QtCore.Qt.Vertical:
            vec = xrange(self.rowCount())
        return [str(self.headerData(k, orientation).toString()) for k in vec]

    def flags(self, index):
        """ Model function to set item flags """
        fieldobj = self.dataset.fields[index.column()]
        if not index.isValid():
            return QtCore.Qt.ItemEnabled
        if fieldobj.editable:
            return QtCore.Qt.ItemFlags(
                QtCore.QAbstractTableModel.flags(self, index) |
                QtCore.Qt.ItemIsEditable)
        else:
            return QtCore.Qt.ItemFlags(QtCore.Qt.ItemIsSelectable |
                                       QtCore.Qt.ItemIsEnabled)

    def changeDataSet(self, dataset):
        """ Function that changes models underlying dataset

        This function is to facilitate changing the dataset for the model
        to be used in cases such as loading a file.

        """
        self.beginResetModel()
        self.dataset = dataset
        self.endResetModel()

    def date(self, row):
        date = self.dataset[row].date
        return QtCore.QDate(date) if date else None


class AlbumSortFilterModel(QtGui.QSortFilterProxyModel):
    """ A proxy model subclass for filtering on any column """

    YearFilter = 0
    MonthFilter = 1
    DayFilter = 2

    def __init__(self, *args, **kwargs):
        super(AlbumSortFilterModel, self).__init__(*args, **kwargs)
        self.fromDate = QtCore.QDate(datetime(MINYEAR, 1, 1))
        self.toDate = QtCore.QDate(datetime(MAXYEAR, 1, 1))
        self._dateFilter = False
        self._dateBetween = True
        self._dateFilterType = self.DayFilter
        self._hideTagged = False

        self.filterList = None

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """ Re-implemented to apply the regular expression filter to all
        columns. If any column has a match, the row is accepted.

        Also applies a date range filter

        Arguments:
            sourceRow (int): The row in question
            sourceParent (QModelIndex): The index of the row's parent.
        """
        sourceModel = self.sourceModel()
        # Check date range first
        date = sourceModel.date(sourceRow)
        if date and self._dateFilter:
            # Round the dates to the desired resolution
            checkDate = self.roundDate(date)
            fromDate = self.roundDate(self.fromDate)
            toDate = self.roundDate(self.toDate)

            if self.dateBetween:
                if checkDate < fromDate or checkDate > toDate:
                    return False
            else:
                if checkDate != fromDate:
                    return False

        # Check the tagged field
        tagged = sourceModel.dataset[sourceRow][self.taggedField]
        if self._hideTagged and tagged:
            return False

        # Check the tag list
        listFilter = self.filterList.getCheckedTagDict(lower=True)
        for fieldName, tags in listFilter.iteritems():
            for t in tags:
                tagStr = sourceModel.dataset[sourceRow, fieldName]
                if t.lower() not in tagStr.lower():
                    return False

        # Here we want to match each word in the pattern individually. If all
        # sub-patterns match in any "filter" column, we'll accept

        # Find separate pattern strings
        pat = str(self.filterRegExp().pattern())

        PATTERN = re.compile(r'''((?:[^\s"]|"[^"]*")+)''')
        patterns = PATTERN.split(pat)[1::2]
        if self.filterList:
            patterns += self.filterList.getCheckedTagNames()
        pats = [QtCore.QRegExp(k.replace('"', ''), QtCore.Qt.CaseInsensitive,
                               QtCore.QRegExp.RegExp)
                for k in patterns]

        # Check each column for the regular expression
        out = [False]*len(pats)
        for k, pat in enumerate(pats):
            for c in range(sourceModel.columnCount()):
                # Don't filter non-filtered fields
                if not sourceModel.dataset.fields[c].filter:
                    continue

                # Apply regex
                index = sourceModel.index(sourceRow, c, sourceParent)
                if index.data().toString().contains(pat):
                    out[k] = True
                    break

        return all(out)

    def roundDate(self, date):
        """ Truncate the date to the year/month/day per dateFilterType

        Arguments:
            date (QDate):  The date to truncate
        """
        dateParts = [date.year(), date.month(), date.day()]
        if self.dateFilterType < self.DayFilter:
            dateParts[2] = 1
        if self.dateFilterType < self.MonthFilter:
            dateParts[1] = 1
        return QtCore.QDate(*dateParts)

    def setDateFilterType(self, filt):
        """ Set the date filter type

        Arguments:
            filt (int):  The argument type (YearFilter, MonthFilter or
                DayFilter class properties)
        """
        if filt not in [self.YearFilter, self.MonthFilter, self.DayFilter]:
            raise ValueError('{} not a valid filter type'.format(filt))
        self._dateFilterType = filt
        self.invalidate()

    def setDateBetween(self, value):
        """ Set filter to match date range or exact date

        Arguments:
            value (bool): True will filter a date range
        """
        self._dateBetween = bool(value)
        self.invalidate()

    def setFilterList(self, treeView):
        """ Associate the TagTreeView in FilterMode to be used for fitering """
        self.filterList = treeView

    @QtCore.pyqtSlot(bool)
    def on_hideTagged(self, checked):
        """ Set the hideTagged property and invalidate the model

        Slot for the Hide Tagged action
        Arguments:
            checked (bool): Checked state of the signaling action
        """
        self._hideTagged = checked
        self.invalidate()

    @QtCore.pyqtSlot(bool)
    def setDateFilterStatus(self, status):
        self._dateFilter = status
        self.invalidate()

    @QtCore.pyqtSlot(QtCore.QDate)
    def setFromDate(self, date):
        """ Set the from date """
        self.fromDate = date
        self.invalidate()

    @QtCore.pyqtSlot(QtCore.QDate)
    def setToDate(self, date):
        """ Set the to date """
        self.toDate = date
        self.invalidate()

    @property
    def dataset(self):
        return self.sourceModel().dataset

    @property
    def dateFilterType(self):
        return self._dateFilterType

    @property
    def dateBetween(self):
        return self._dateBetween

    @property
    def taggedField(self):
        return self.sourceModel().dataset.taggedField


class batchAddCmd(QtGui.QUndoCommand):
    """Undo command for batch setting of cell data in the AlbumModel

    Arguments:
        model: (AlbumModel): The calling model
        rows ([int]): A list of row indexes
        values (dict): A dictionary with field names as keys and lists of
            tag strings as values
    """
    description = "Set Batch"

    def __init__(self, model, rows, values, parent=None):
        self.model = model
        self.rows = rows
        self.newvalues = values
        self.oldvalues = None
        cell = " ({} Photos)".format(len(rows))
        description = self.description + cell
        super(batchAddCmd, self).__init__(description, parent)

    def redo(self):
        old = self.model._batchAddTags(self.rows, self.newvalues)
        if self.oldvalues is None:
            self.oldvalues = old

    def undo(self):
        self.model._batchAddTags(self.rows, self.oldvalues, keep=False)


class deleteCmd(QtGui.QUndoCommand):

    description = "Delete Cells"

    def __init__(self, model, indexes, parent=None):
        self.indexes = indexes
        self.model = model
        self.old_values = [dex.data() for dex in self.indexes]
        super(deleteCmd, self).__init__(self.description, parent)

    def redo(self):
        # Delete the cells
        for cell in self.indexes:
            self.model.setData(cell, QtCore.QVariant(''))

    def undo(self):
        # Re-populate the cells
        for cell, val in zip(self.indexes, self.old_values):
            self.model.setData(cell, val)


class setDataCmd(QtGui.QUndoCommand):
    """Undo command for setting of cell data in the AlbumModel

    Arguments:
        model (TabularFieldModel):
        index (QModelIndex):
        value (QVariant):
    """
    description = "Set Tag Data"

    def __init__(self, model, index, value, role, parent=None):
        self.model = model
        self.index = index
        self.newvalue = value
        self.role = role
        self.oldvalue = index.data()
        field = model.dataset.fields[index.column()]
        cell = " ({}, {})".format(index.row()+1, field.name)
        description = self.description + cell
        super(setDataCmd, self).__init__(description, parent)

    def redo(self):
        self.model._setData(self.index, self.newvalue)

    def undo(self):
        self.model._setData(self.index, self.oldvalue)


if __name__ == "__main__":
    proxy = AlbumSortFilterModel()
    print proxy.roundDate(QtCore.QDate(datetime.now()))
