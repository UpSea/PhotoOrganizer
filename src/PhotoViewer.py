#http://doc.qt.io/qt-5/qtwidgets-widgets-imageviewer-example.html
from PyQt4 import QtCore, QtGui
from datastore import Album
from UIFiles import Ui_ImageViewer


class ImageViewer(QtGui.QMainWindow, Ui_ImageViewer):
    """ An image viewer """

    def __init__(self, imagefile=None, albumModel=None, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.setupUi(self)
        self.albumModel = albumModel
        self.treeView.header().setVisible(True)

        # Ignore size hint and give the image as much space as possible
        self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored,
                                      QtGui.QSizePolicy.Ignored)

        # Resize the window
        self.resize(QtGui.qApp.desktop().screenGeometry().size()*3/5)

        # Connect signals
        self.treeView.sourceModel.dataChanged.connect(self.on_filterChanged)

        # Create next/back actions
        backIcon = QtGui.QIcon(r'icons\prev_arrow.png')
        self.actionBack = QtGui.QAction(backIcon, 'Previous', self)
        self.actionBack.triggered.connect(self.on_back)
        self.toolBar.addAction(self.actionBack)
        nextIcon = QtGui.QIcon(r'icons\next_arrow.png')
        self.actionNext = QtGui.QAction(nextIcon, 'Next', self)
        self.actionNext.triggered.connect(self.on_next)
        self.toolBar.addAction(self.actionNext)

        # Set the first image
        self.imageList = []
        self.imageShowing = None
        if imagefile:
            self.setImage(imagefile)
        else:
            self.originalPix = QtGui.QPixmap()

    def setImage(self, photo, index=0):
        """ Set the window's image and tag view

        Arguments:
            photo (Photo, [Photo], int): The Photo(s) to show. If photo is a
                Photo instance, that photo will be shown without the option
                to move forward or backward. If photo is an int, the photo at
                that index in the list will be shown. If it is a list of Photos,
                the photo list will be set and the <index> photo will be shown.
            index (int): (0) The index to show in the given list of Photos
        """
        if isinstance(photo, list):
            self.imageList = photo
            self.imageShowing = index
            photo = self.imageList[self.imageShowing]
        elif isinstance(photo, int):
            self.imageShowing = photo
            photo = self.imageList[photo]
        else:
            self.imageList = []
            self.imageShowing = None
            self.actionBack.setEnabled(False)
            self.actionNext.setEnabled(False)

        if self.imageList:
            self.actionBack.setEnabled(True)
            self.actionNext.setEnabled(True)

        self.originalPix = QtGui.QPixmap(photo.filePath)
        self.imageLabel.setHidden(True)
        self.imageLabel.setPixmap(self.originalPix)
        self.setWindowTitle(photo.filePath)
        if self.imageList:
            self.statusbar.showMessage('%d of %d' % (self.imageShowing+1,
                                                     len(self.imageList)))

        # Check tags for file
        self.treeView.sourceModel.blockSignals(True)
        self.treeView.checkFileTags(photo.fileId)
        self.treeView.sourceModel.blockSignals(False)
        self.treeView.expandAll()
        fileName = photo[Album.fileNameField]
        self.treeView.sourceModel.setHorizontalHeaderLabels([fileName + ' Tags'])

        # Fit the image. This doesn't work unless it is done after
        # the method has returned, hence the singleshot timer
        QtCore.QTimer.singleShot(0, self.fitImage)

    def fitImage(self):
        """ Fit the image to the window while keeping aspect ratio """
        if self.originalPix.isNull():
            return
        pix = self.originalPix.copy()
        w = self.imageLabel.width()
        h = self.imageLabel.height()
        self.imageLabel.setPixmap(pix.scaled(w, h, QtCore.Qt.KeepAspectRatio))
        self.imageLabel.setHidden(False)

    def resizeEvent(self, event):
        """ Re-implemented to resize the image """
        super(ImageViewer, self).resizeEvent(event)
        self.fitImage()

    @QtCore.pyqtSlot()
    def on_back(self):
        """ Switch to the previous photo """
        if self.imageShowing == 0:
            index = len(self.imageList) - 1
        else:
            index = self.imageShowing - 1
        self.setImage(index)

    @QtCore.pyqtSlot(QtCore.QModelIndex)
    def on_filterChanged(self, index):
        """ Apply the changed tag state to the photo, both in the main window
        and the database.
        """
        item = self.treeView.sourceModel.itemFromIndex(index)
        if self.albumModel is None:
            return

        # Determine Album row of current file
        row = self.albumModel.dataset.index(self.imageList[self.imageShowing])

        # Add or remove the tag
        self.albumModel.setTagState(row, item.parent().text(), item.text(),
                                    item.checkState())

    @QtCore.pyqtSlot()
    def on_next(self):
        """ Switch to the next photo """
        if self.imageShowing == len(self.imageList) - 1:
            index = 0
        else:
            index = self.imageShowing + 1
        self.setImage(index)


if __name__ == "__main__":
    from datastore import PhotoDatabase
    app = QtGui.QApplication([])

    dbfile = '..\Fresh.pdb'
    db = PhotoDatabase(dbfile)
    album = db.load(dbfile)[0]

    viewer = ImageViewer()
    viewer.treeView.setDb(db)
    viewer.setImage([k for k in album])
    viewer.show()
    app.exec_()
