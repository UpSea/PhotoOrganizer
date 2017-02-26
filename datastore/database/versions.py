import sqlite3
from utl import compareRelease
from shared import __release__
from converters import _convert02to03


def convertCheck(dbfile):
    """ Check a database file file

    Returns a tuple with the respective indexes corresponding to "readable",
    "convert" and "fileVersion" where readable indicates whether the field is
    readable, convert indicates whether it needs to be converted and
    fileVersion is the version used to save the file
    """
    with sqlite3.connect(dbfile) as con:
        q = 'Select AppFileVersion FROM AppData'
        try:
            fileVersion = con.execute(q).fetchone()[0]
        except:
            return False, None, 0

    if compareRelease(fileVersion, '0.2') < 0:
        return False, None, fileVersion
    if compareRelease(fileVersion, __release__) < 0:
        return True, True, fileVersion
    return True, False, fileVersion


def convertVersion(dbfile):
    """ Sort out which converter to use and call it

    Returns a tuple with the respective indexes corresponding to "success" and
    a message.
    """
    ver = convertCheck(dbfile)[2]
    if (compareRelease(ver, '0.2') > 0 and
            compareRelease(__release__, '0.3') >= 0):
        return _convert02to03(dbfile)


if __name__ == "__main__":
    dbfile = r'C:\Users\Luke\Files\Python\workspace\PicOrganizer\ConvertMe.pdb'
    convertVersion(dbfile)
