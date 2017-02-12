import sqlite3


def create_database(dbfile):
    with sqlite3.connect(dbfile) as con:
        con.execute('PRAGMA foreign_keys = 1')
        cur = con.cursor()
        with open('create_database.sql', 'r') as fid:
            script = fid.read()
        cur.executescript(script)

if __name__ == "__main__":
    dbfile = 'TestDb2.db'
    create_database(dbfile)
