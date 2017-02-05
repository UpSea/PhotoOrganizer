#!/usr/bin/env python
# http://stackoverflow.com/questions/14068823/how-to-create-filters-for-qtableview-in-pyqt
# Image in standard item from https://forum.qt.io/topic/62180/resizing-image-to-display-in-tableview

from PyQt5 import QtCore, QtGui, QtWidgets
import os.path
from glob import glob
from PIL import Image
from io import BytesIO


class myWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.centralwidget = QtWidgets.QWidget(self)
        self.lineEdit = QtWidgets.QLineEdit(self.centralwidget)
        self.view = QtWidgets.QTableView(self.centralwidget)
        self.comboBox = QtWidgets.QComboBox(self.centralwidget)
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.view.setIconSize(QtCore.QSize(100, 100))

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal, self.centralwidget)
        self.slider.setRange(20, 400)
        self.slider.valueChanged.connect(self.setIconSize)
        self.slider.setValue(100)

        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 0, 1, 1, 1)
        self.gridLayout.addWidget(self.comboBox, 0, 2, 1, 1)
        self.gridLayout.addWidget(self.slider, 0, 3, 1, 1)
        self.gridLayout.addWidget(self.view, 1, 0, 1, 4)

        self.setCentralWidget(self.centralwidget)
        self.label.setText("Regex Filter")

        self.model = QtGui.QStandardItemModel(self)

        self.proxy = QtCore.QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.view.setModel(self.proxy)
        self.comboBox.addItems(["Column 1", "Column 2"])

        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.comboBox.currentIndexChanged.connect(self.on_comboBox_currentIndexChanged)
        self.comboBox.setCurrentIndex(1)

        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.sectionClicked.connect(self.on_view_horizontalHeader_sectionClicked)

        self.view.resizeColumnsToContents()
        self.view.resizeRowsToContents()

    def populate(self, directory):
        images = self.images(directory)
        for k, path in enumerate(images):
            im = Image.open(path)
            im.thumbnail((400, 400))

            fp = BytesIO()
            im.save(fp, 'png')
            pix = QtGui.QPixmap()
            pix.loadFromData(fp.getvalue())
            # qimage.loadFromData(fp.getvalue(), 'png')
            # item.setIcon(QIcon(QPixmap.fromImage(qimage)))
            imgItem = QtGui.QStandardItem()
            imgItem.setData(QtGui.QIcon(pix), QtCore.Qt.DecorationRole)
            self.model.setItem(k, 0, imgItem)
            fname = os.path.split(path)[1]
            self.model.setItem(k, 1, QtGui.QStandardItem(fname))
            self.model.setItem(k, 2, QtGui.QStandardItem(str(k//2)))
        self.setWidthHeight()

    def images(self, folder):
        ''' Return a list of file-names of all
            supported images in self._dirpath. '''

        # Start with an empty list
        images = []

        # Find the matching files for each valid
        # extension and add them to the images list.
        ext = [fmt.data().decode('utf-8')
               for fmt in QtGui.QImageReader().supportedImageFormats()]
        for extension in ext:
            pattern = os.path.join(folder, '*.%s' % extension)
            images.extend(glob(pattern))

        return images

    def setWidthHeight(self):
        self.view.setColumnWidth(0, self.iconSize)
        self.view.resizeRowsToContents()

    @QtCore.pyqtSlot(int)
    def setIconSize(self, size):
        self.view.setIconSize(QtCore.QSize(size, size))
        self.setWidthHeight()

    @QtCore.pyqtSlot(int)
    def on_view_horizontalHeader_sectionClicked(self, logicalIndex):
        self.logicalIndex = logicalIndex
        self.menuValues = QtWidgets.QMenu(self)
        self.signalMapper = QtCore.QSignalMapper(self)

        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentIndex(self.logicalIndex)
        self.comboBox.blockSignals(True)

        valuesUnique = [self.model.item(row, self.logicalIndex).text()
                        for row in range(self.model.rowCount())]

        actionAll = QtWidgets.QAction("All", self)
        actionAll.triggered.connect(self.on_actionAll_triggered)
        self.menuValues.addAction(actionAll)
        self.menuValues.addSeparator()

        for actionNumber, actionName in enumerate(sorted(list(set(valuesUnique)))):
            action = QtWidgets.QAction(actionName, self)
            self.signalMapper.setMapping(action, actionNumber)
            action.triggered.connect(self.signalMapper.map)
            self.menuValues.addAction(action)

        self.signalMapper.mapped.connect(self.on_signalMapper_mapped)

        headerPos = self.view.mapToGlobal(self.horizontalHeader.pos())

        posY = headerPos.y() + self.horizontalHeader.height()
        posX = headerPos.x() + self.horizontalHeader.sectionPosition(self.logicalIndex)

        self.menuValues.exec_(QtCore.QPoint(posX, posY))

    @QtCore.pyqtSlot()
    def on_actionAll_triggered(self):
        filterColumn = self.logicalIndex
        filterString = QtCore.QRegExp("",
                                      QtCore.Qt.CaseInsensitive,
                                      QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)
        self.setWidthHeight()

    @QtCore.pyqtSlot(int)
    def on_signalMapper_mapped(self, i):
        stringAction = self.signalMapper.mapping(i).text()
        filterColumn = self.logicalIndex
        filterString = QtCore.QRegExp(stringAction,
                                      QtCore.Qt.CaseSensitive,
                                      QtCore.QRegExp.FixedString)

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)
        self.setWidthHeight()

    @QtCore.pyqtSlot(str)
    def on_lineEdit_textChanged(self, text):
        search = QtCore.QRegExp(text,
                                QtCore.Qt.CaseInsensitive,
                                QtCore.QRegExp.RegExp)

        self.proxy.setFilterRegExp(search)
        self.setWidthHeight()

    @QtCore.pyqtSlot(int)
    def on_comboBox_currentIndexChanged(self, index):
        self.proxy.setFilterKeyColumn(index+1)
        self.setWidthHeight()

    @property
    def iconSize(self):
        size = self.view.iconSize()
        return max(size.width(), size.height())


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    main = myWindow()
    main.resize(800, 600)
    main.show()

    directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
    main.populate(directory)

    sys.exit(app.exec_())
