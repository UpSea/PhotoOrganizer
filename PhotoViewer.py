#http://doc.qt.io/qt-5/qtwidgets-widgets-imageviewer-example.html
from PyQt4 import QtCore, QtGui
from UIFiles import Ui_ImageViewer


class ImageViewer(QtGui.QMainWindow, Ui_ImageViewer):
    """ An image viewer """

    def __init__(self, imagefile=None, parent=None):
        super(ImageViewer, self).__init__(parent)
        self.setupUi(self)

        # Ignore size hint and give the image as much space as possible
        self.imageLabel.setSizePolicy(QtGui.QSizePolicy.Ignored,
                                      QtGui.QSizePolicy.Ignored)

        # Resize the window
        self.resize(QtGui.qApp.desktop().screenGeometry().size()*3/5)

        # Create next/back actions
        self.actionBack = QtGui.QAction('<', self)
        self.actionBack.triggered.connect(self.on_back)
        self.toolBar.addAction(self.actionBack)
        self.actionNext = QtGui.QAction('>', self)
        self.actionNext.triggered.connect(self.on_next)
        self.toolBar.addAction(self.actionNext)

        # Set the first image
        self.imageList = []
        self.imageShowing = None
        if imagefile:
            self.setImage(imagefile)
        else:
            self.originalPix = QtGui.QPixmap()

    def setImage(self, imagefile, index=0):
        """ Set the window's image """
        if isinstance(imagefile, list):
            self.imageList = imagefile
            self.imageShowing = index
            imagefile = self.imageList[self.imageShowing]
        elif isinstance(imagefile, int):
            self.imageShowing = imagefile
            imagefile = self.imageList[imagefile]
        else:
            self.imageList = []
            self.imageShowing = None
            self.actionBack.setEnabled(False)
            self.actionNext.setEnabled(False)

        if self.imageList:
            self.actionBack.setEnabled(True)
            self.actionNext.setEnabled(True)

        self.originalPix = QtGui.QPixmap(imagefile)
        self.imageLabel.setHidden(True)
        self.imageLabel.setPixmap(self.originalPix)
        self.setWindowTitle(imagefile)
        if self.imageList:
            self.statusbar.showMessage('%d of %d' % (self.imageShowing+1,
                                                     len(self.imageList)))
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
        if self.imageShowing == 0:
            index = len(self.imageList) - 1
        else:
            index = self.imageShowing - 1
        self.setImage(index)

    @QtCore.pyqtSlot()
    def on_next(self):
        if self.imageShowing == len(self.imageList) - 1:
            index = 0
        else:
            index = self.imageShowing + 1
        self.setImage(index)


if __name__ == "__main__":
    app = QtGui.QApplication([])
    imageList = [r"C:\Users\Luke\Files\Python\gallery\Kids\247179_10153164371004281_372139085264929760_n.jpg",
                 r"C:\Users\Luke\Files\Python\gallery\Kids\IMAG0157(1).jpg"]
    viewer = ImageViewer(imageList)
    viewer.show()
    app.exec_()
