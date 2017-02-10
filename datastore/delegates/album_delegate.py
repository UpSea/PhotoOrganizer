from PyQt4 import QtCore, QtGui
from ..objects import FieldObject


class AlbumDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent=None):
        super(AlbumDelegate, self).__init__(parent)

    def paint(self, painter, option, index):
        editor = index.model().sourceModel().dataset.fields[index.column()].editor
        if editor == FieldObject.CheckBoxEditor:
            value = index.data().toBool()
            check_box_style_option = QtGui.QStyleOptionButton()

            # Set all the different state values for the Checkbox editor

            # Set Editable or Read Only
            if (index.flags() & QtCore.Qt.ItemIsEditable):
                check_box_style_option.state |= QtGui.QStyle.State_Enabled
            else:
                check_box_style_option.state |= QtGui.QStyle.State_ReadOnly

            # Checked/Unchecked
            if value:
                check_box_style_option.state |= QtGui.QStyle.State_On
            else:
                check_box_style_option.state |= QtGui.QStyle.State_Off

            # Active/Editable
            # This one is for if the box is actually active if not it will be
            # in a grayed out state.
            idx_flags = index.model().flags(index)
            check_box_style_option.rect = self.getCheckBoxRect(option)
            if not (idx_flags & QtCore.Qt.ItemIsEditable):
                check_box_style_option.state |= QtGui.QStyle.State_ReadOnly
            if value:
                check_box_style_option.state |= QtGui.QStyle.State_On
            else:
                check_box_style_option.state |= QtGui.QStyle.State_Off

            # This deals with the background color
            palette = QtGui.QApplication.palette()
            selectable = idx_flags & QtCore.Qt.ItemIsSelectable
            if (option.state & QtGui.QStyle.State_Selected and selectable):
                color = palette.highlight().color()
            elif (index.data(QtCore.Qt.BackgroundRole) != QtCore.QVariant()):
                color = QtGui.QColor(index.data(QtCore.Qt.BackgroundRole))
            else:
                color = QtGui.QColor(QtCore.Qt.transparent)

            # Here is where the box is actually painted
            painter.save()
            painter.fillRect(option.rect, color)
            QtGui.QApplication.style().drawControl(QtGui.QStyle.CE_CheckBox,
                                                   check_box_style_option,
                                                   painter)
            painter.restore()
        else:
            QtGui.QStyledItemDelegate.paint(self, painter, option, index)

    def createEditor(self, parent, option, index):
        model = index.model().sourceModel()
        fieldobj = model.dataset.fields[index.column()]
        editor = fieldobj.editor
        if editor == FieldObject.ComboBoxEditor:
            combobox = QtGui.QComboBox(parent)
            items = model.dataset.uniqueFieldValues(fieldobj)
            str_items = [str(k) for k in items]
            unique_list = list(set(str_items))
            unique_list = filter(None, unique_list)
            combobox.addItems(unique_list)
            combobox.setEditable(True)
            return combobox
        elif editor == FieldObject.DateEditEditor:
            dateedit = QtGui.QDateEdit(parent)
            dateedit.setDisplayFormat('yyyy-MM-dd')
            return dateedit
        elif editor == FieldObject.CheckBoxEditor:
            # The check box has no editor as it is always visible.
            return
        else:
            return QtGui.QStyledItemDelegate.createEditor(self, parent, option,
                                                          index)

    def setEditorData(self, editor, index):
        model = index.model().sourceModel()
        fieldobj = model.dataset.fields[index.column()]
        feditor = fieldobj.editor
        data = model.data(index, QtCore.Qt.DisplayRole)
        if data:
            text = data.toString()
        else:
            text = ''
        if feditor == FieldObject.ComboBoxEditor:
#             i = editor.findText(text)
#             editor.setCurrentIndex(i)
            editor.lineEdit().setText(text)
        else:
            QtGui.QStyledItemDelegate.setEditorData(self, editor, index)

    def editorEvent(self, event, model, option, index):
        editor = index.model().sourceModel().dataset.fields[index.column()].editor
        if editor == FieldObject.CheckBoxEditor:
            # Change the data in the model and the state of the check box
            # if the user presses the left mouse button or presses
            # Key_Space or Key_Select and this cell is editable.
            # Otherwise do nothing.
            if not (index.flags() & QtCore.Qt.ItemIsEditable):
                return False

            # Do not change the check box-state
            if (event.type() == QtCore.QEvent.MouseButtonRelease or
                    event.type() == QtCore.QEvent.MouseButtonDblClick):
                if (event.button() != QtCore.Qt.LeftButton or not
                        self.getCheckBoxRect(option).contains(event.pos())):
                    return False
                if event.type() == QtCore.QEvent.MouseButtonDblClick:
                    return True
            elif event.type() == QtCore.QEvent.KeyPress:
                if (event.key() != QtCore.Qt.Key_Space and
                        event.key() != QtCore.Qt.Key_Select):
                    return False
            else:
                return False

            # Change the check box-state
            self.setModelData(None, model, index)
            return True
        else:
            return QtGui.QStyledItemDelegate.editorEvent(self, event, model,
                                                         option, index)

    def setModelData(self, editor, model, index):
        feditor = index.model().sourceModel().dataset.fields[index.column()].editor
        if feditor == FieldObject.CheckBoxEditor:
            # The user wanted to change the old state in the opposite.
            value = index.data().toBool()
            newValue = not value
            model.setData(index, QtCore.QVariant(newValue), QtCore.Qt.EditRole)
            # Emit dataChanged here for all indices because if this field is
            # being copied the check box editor doesn't refresh the entire view
            # and then there will be a lag in the update of the copied data.
        elif feditor == FieldObject.ComboBoxEditor:
            model.setData(index, QtCore.QVariant(editor.currentText()))
        else:
            QtGui.QStyledItemDelegate.setModelData(self, editor, model, index)
        model.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def getCheckBoxRect(self, option):
        check_box_style_option = QtGui.QStyleOptionButton()
        check_box_rect = QtGui.QApplication.style().subElementRect(
            QtGui.QStyle.SE_CheckBoxIndicator, check_box_style_option, None)
        check_box_point = QtCore.QPoint(option.rect.x() +
                                        option.rect.width() / 2 -
                                        check_box_rect.width() / 2,
                                        option.rect.y() +
                                        option.rect.height() / 2 -
                                        check_box_rect.height() / 2)
        return QtCore.QRect(check_box_point, check_box_rect.size())
