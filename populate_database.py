import os.path
from glob import glob
from PIL import Image
from io import BytesIO
import imagehash
import sqlite3


supported_formats = ['jpg', 'jpeg', 'png']


def process_folder(directory, dbfile, calc_hash=False):
    """Populate the table with images from directory

    Arguments:
    directory (str): The directory containing the desired image files
    dbfile (str):    The path to the database file to be populated
    calc_hash (bool): (False) Whether or not to calculate the hash (faster without)
    """
    # Get the list of images with valid extensions
    images = []
    for extension in supported_formats:
        pattern = os.path.join(directory, '*.%s' % extension)
        images.extend(glob(pattern))

    iqry = 'INSERT INTO File (filename, directory, date, hash, ' + \
           'thumbnail) VALUES (?,?,?,?,?)'
    with sqlite3.connect(dbfile) as con:
        con.text_factory = str
        con.execute('PRAGMA foreign_keys = 1')
        cur = con.cursor()
        # Loop over all images and add to the table
        for path in images:
            # Read the scaled image into a byte array
            im = Image.open(path)
            exif = im._getexif()
            hsh = imagehash.average_hash(im) if calc_hash else ''
            date = exif[36867] if exif else "Unknown"
            sz = 400
            im.thumbnail((sz, sz))
            fp = BytesIO()
            im.save(fp, 'png')

            # Add the model items
            fname = os.path.split(path)[1]
            print(fname, str(hsh))
            cur.execute(iqry, [fname, directory, date, str(hsh),
                               sqlite3.Binary(fp.getvalue())])


if __name__ == "__main__":
    from create_database import create_database
    dbfile = 'TestDb2.db'
    create_database(dbfile)
    directory = r"C:\Users\Luke\Files\Python\gallery\Kids"
    process_folder(directory, dbfile, True)
