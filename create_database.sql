DROP TABLE IF EXISTS File;
CREATE TABLE File (FilId INTEGER PRIMARY KEY AUTOINCREMENT,
                   filename TEXT,
                   directory TEXT,
                   date TEXT,
                   hash TEXT,
                   thumbnail BLOB,
                   thumbsize INTEGER);

DROP TABLE IF EXISTS Location;
CREATE TABLE Location (LocId INTEGER PRIMARY KEY AUTOINCREMENT,
                       FilId INTEGER,
                       Location TEXT);

DROP TABLE IF EXISTS People;
CREATE TABLE People (PeoId INTEGER PRIMARY KEY AUTOINCREMENT,
                     FilId INTEGER,
                     Person TEXT);
