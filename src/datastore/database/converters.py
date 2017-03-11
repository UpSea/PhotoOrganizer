import sqlite3
import shutil
import os
import traceback
from shared import __release__


def _convert03to05(dbfile):
    """ Convert files between 0.3 and 0.5 to 0.5.x

    This is necessary because older versions used column named date in the file
    table which is an sqlite function, and that column contained an incorrectly
    formatted date time string. This converter changes the name of that column
    and converts the dates to datetime in the database.
    """
    # Create a backup copy
    p, f = os.path.split(dbfile)
    n, e = os.path.splitext(f)
    bu = os.path.join(p, n + '_backup0.3' + e)
    shutil.copyfile(dbfile, bu)

    try:
        with sqlite3.connect(dbfile) as con:
            ov = con.execute('SELECT AppFileVersion FROM AppData').fetchone()[0]
            # Create the new File table
            con.execute('DROP TABLE IF EXISTS TMP')
            cfq = ('CREATE TABLE TMP (FilId INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'tagged INTEGER, filename TEXT, directory TEXT, '
                   'filedate DATETIME, hash TEXT, thumbnail BLOB, '
                   'importTimeUTC DATETIME DEFAULT CURRENT_TIMESTAMP)')
            con.execute(cfq)

            # Copy the data from the old table to the new, converting the date
            mq = ('INSERT INTO TMP '
                  'SELECT FilId, tagged, filename, directory, '
                  'case substr(date, 5, 1) WHEN  ":" THEN substr(date, 1, 4) '
                  '|| "-" || substr(date,6,2)  || "-" || substr(date, 9,2) '
                  '|| " " || substr(date, 12) ELSE date END filedate, '
                  'hash, thumbnail, importTimeUTC FROM File')
            con.execute(mq)

            # Remove the old table and rename the new
            con.execute('DROP TABLE File')
            con.execute('ALTER TABLE TMP RENAME TO File')

            # Update the AppFileVersion
            u = 'UPDATE AppData SET AppFileVersion = ?'
            con.execute(u, (__release__,))

    except Exception as err:
        print('There was an error converting {} to 0.5'.format(n+e))
        traceback.print_exc()
        shutil(bu, dbfile)
        return False, str(err)

    return (True, "Converted {} to {}".format(ov, __release__))

