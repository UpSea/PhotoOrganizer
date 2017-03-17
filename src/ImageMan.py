from PyQt4 import QtGui
from PIL import Image
from io import BytesIO


def getThumbnailIcon(filePath, size=400):
    if isinstance(filePath, basestring):
        im = Image.open(filePath)
        im.thumbnail((size, size))
    elif isinstance(filePath, Image.Image):
        im = filePath.copy()
    else:
        raise TypeError('FILEPATH must be an Image or path to an image file')

    fp = BytesIO()
    im.save(fp, 'png')
    pix = QtGui.QPixmap()
    pix.loadFromData(fp.getvalue())
    return QtGui.QIcon(pix)
