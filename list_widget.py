#http://pythoncentral.io/pyside-pyqt-tutorial-the-qlistwidget/
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import os.path
from glob import glob
from PIL import Image
from cStringIO import StringIO

def supported_image_extensions():
    ''' Get the image file extensions that can be read. '''
    formats = QImageReader().supportedImageFormats()
    # Convert the QByteArrays to strings
    return [str(fmt) for fmt in formats]


class ImageWidget(QWidget):
    def __init__(self, dirpath, parent=None):
        super(ImageWidget, self).__init__(parent)
        self.setWindowTitle('Image List')
        self.setMinimumSize(600, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)
     
        #Add a status label
        self.label = QLabel()
        layout.addWidget(self.label)
     
        #Add a slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(20, 400)
        layout.addWidget(self.slider)


        # Create one of our ImageFileList objects using the image
        # directory passed in from the command line
        self.lst = ImageFileList(dirpath, self)
        self.slider.valueChanged.connect(self.lst.setIconSize)
        self.slider.setValue(80)
        layout.addWidget(self.lst)
     
        self.entry = QLineEdit(self)
        layout.addWidget(self.entry)
 
        self.lst.currentItemChanged.connect(self.on_item_changed)
 
    def on_item_changed(self, curr, prev):
        self.entry.setText(curr.text())
    
    def populate(self):
        self.lst._populate(self.label)


class ImageFileList(QListWidget):
    ''' A specialized QListWidget that displays the list
        of all image files in a given directory. '''
    def __init__(self, dirpath, parent=None):
        QListWidget.__init__(self, parent)
        self.setDirpath(dirpath)
        print 'done init'

    def _images(self):
        ''' Return a list of file-names of all
            supported images in self._dirpath. '''
     
        # Start with an empty list
        images = []
     
        # Find the matching files for each valid
        # extension and add them to the images list.
        for extension in supported_image_extensions():
            pattern = os.path.join(self._dirpath,
                                   '*.%s' % extension)
            images.extend(glob(pattern))
     
        return images
    
    def _populate(self, label):
        ''' Fill the list with images from the
            current directory in self._dirpath. '''
     
        # In case we're repopulating, clear the list
        self.clear()
     
        # Create a list item for each image file,
        # setting the text and icon appropriately
        import time
        tic = time.time()
        images = self._images()
        numImages = len(images)
        for k, image in enumerate(images):
            label.setText('Reading {} of {}'.format(k+1, numImages))
            QApplication.processEvents()
            print('creating an image')
            
            item = QListWidgetItem(self)
            item.setText(image)
            print('setting icon')
            im = Image.open(image)
            im.thumbnail((400, 400))

            qimage = QImage()
            fp = StringIO()
            im.save(fp, 'png')
            qimage.loadFromData(fp.getvalue(), 'png')
            
            item.setIcon(QIcon(QPixmap.fromImage(qimage)))
        label.setText('')
        label.setVisible(False)
        print time.time() - tic
    
    def setIconSize(self, size):
        super(ImageFileList, self).setIconSize(QSize(size, size))
    
    def setDirpath(self, dirpath):
        ''' Set the current image directory and refresh the list. '''
        self._dirpath = dirpath

# if __name__ == "__main__":
    # imageList = ImageFileList(r"C:\Users\Luke\Files\Python\gallery\Kids")
    # imageList._populate()
    # app = QApplication([])
    # imageList.show()

if __name__ == '__main__':
    # The app doesn't receive sys.argv, because we're using
    # sys.argv[1] to receive the image directory
    app = QApplication([])
 
    # Create a window, set its size, and give it a layout
    rootDir = r"C:\Users\Luke\Files\Python\gallery\Kids"
    # rootDir = r"C:\Users\Luke\Files\Python\workspace\DjangoPhotoGallery\mediafiles"
    win = ImageWidget(rootDir)
    
    win.show()
    win.populate()
 
    print('showing')
    app.exec_()
    
# ll
# get_ipython().magic(u'ls ')
# im = Image.open('IMAG0132.jpg')
# th = im.thumbnail.([120, 120])
# th = im.thumbnail([120, 120])
# th
# im
# type(thumbnail)
# type(th)
# th = im.thumbnail((120, 120))
# th
# im.thumbnail()
# im.thumbnail(120, 120)
# th = im.thumbnail((120, 120))
# get_ipython().set_next_input(u'th = im.thumbnail');get_ipython().magic(u'pinfo im.thumbnail')
# im
# im.size
# im.save('thumbnail.jpg')
# from io import cStringIO
# import cStringIO
# cString()?
# get_ipython().magic(u'pinfo cString')
# get_ipython().magic(u'pinfo cStringIO')
# qimage = QImage()
# from PyQt4 import QtGui
# qimage = QtGui.Image()
# qimage = QtGui.QImage()
# fp = StringIO()
# im.save(fp)
# im.save(fp, 'png')
# fp
# qimage.loadFromData(fp.getvalue(), 'png')