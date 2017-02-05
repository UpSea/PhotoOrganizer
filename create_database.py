import sqlite3

dbfile = "TestDb.db"
con = sqlite3.connect(dbfile)
cur = con.cursor()
with open('create_database.sql', 'r') as fid:
    script = fid.read()
cur.executescript(script)
con.close()
