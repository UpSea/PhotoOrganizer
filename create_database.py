import sqlite3

dbfile = "TestDb2.db"
with sqlite3.connect(dbfile) as con:
    con.execute('PRAGMA foreign_keys = 1')
    cur = con.cursor()
    with open('create_database.sql', 'r') as fid:
        script = fid.read()
    cur.executescript(script)
