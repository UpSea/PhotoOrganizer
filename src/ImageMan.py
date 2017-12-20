from PyQt4 import QtGui
from PIL import Image, ImageOps
from io import BytesIO


def getThumbnailIcon(filePath, size=200):
    if isinstance(filePath, basestring):
        im = Image.open(filePath)
        thumb = ImageOps.fit(im, (size, size), Image.ANTIALIAS)
    elif isinstance(filePath, Image.Image):
        thumb = filePath.copy()
    else:
        raise TypeError('FILEPATH must be an Image or path to an image file')

    fp = BytesIO()
    thumb.save(fp, 'png')
    pix = QtGui.QPixmap()
    pix.loadFromData(fp.getvalue())
    return QtGui.QIcon(pix)

if __name__ == "__main__":
    filePath = r"C:\Users\Luke\Desktop\Pictures\Screenshot.jpg"
    image = Image.open(filePath)
    size = (200, 200)
    thumb = ImageOps.fit(image, size, Image.ANTIALIAS)
    thumb.show()
