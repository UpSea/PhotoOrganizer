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

        if imagefile:
            self.setImage(imagefile)
        else:
            self.originalPix = QtGui.QPixmap()

    def setImage(self, imagefile):
        """ Set the window's image """
        self.originalPix = QtGui.QPixmap(imagefile)
        self.imageLabel.setPixmap(self.originalPix)
        self.setWindowTitle(imagefile)
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

    def resizeEvent(self, event):
        """ Re-implemented to resize the image """
        super(ImageViewer, self).resizeEvent(event)
        self.fitImage()


if __name__ == "__main__":
    app = QtGui.QApplication([])
#     fname = r"C:\Users\Luke\Files\Python\gallery\Kids\247179_10153164371004281_372139085264929760_n.jpg"
    fname = r"C:\Users\Luke\Files\Python\gallery\Kids\IMAG0157(1).jpg"
    viewer = ImageViewer(None)
    viewer.show()
    app.exec_()
