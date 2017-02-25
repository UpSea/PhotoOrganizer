import sqlite3
import os


def create_database(dbfile):
    if os.path.exists(dbfile):
        raise ValueError('{} already exists'.format(dbfile))
    with sqlite3.connect(dbfile) as con:
        con.execute('PRAGMA foreign_keys = 1')
        cur = con.cursor()
        with open('create_database.sql', 'r') as fid:
            script = fid.read()
        cur.executescript(script)
        cur.execute('UPDATE Database SET Name = ?', (dbfile,))

if __name__ == "__main__":
    dbfile = 'TestDb2.db'
    if os.path.exists(dbfile):
        os.remove(dbfile)
    create_database(dbfile)
