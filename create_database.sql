DROP TABLE IF EXISTS FileLoc;
DROP TABLE IF EXISTS File;
CREATE TABLE File (FilId INTEGER PRIMARY KEY AUTOINCREMENT,
                   tagged INTEGER,
                   filename TEXT,
                   directory TEXT,
                   date TEXT,
                   hash TEXT,
                   thumbnail BLOB,
                   importTimeUTC DATETIME DEFAULT CURRENT_TIMESTAMP);

DROP TABLE IF EXISTS Locations;
CREATE TABLE Locations (LocId INTEGER PRIMARY KEY AUTOINCREMENT,
                        Location Text,
                        UNIQUE (Location COLLATE NOCASE));

CREATE TABLE FileLoc(FilId INTEGER,
                     LocId INTEGER,
                     FOREIGN KEY(FilId) REFERENCES File(FilId),
                     FOREIGN KEY(LocId) REFERENCES Locations(LocId),
                     UNIQUE (FilId, LocId));

DROP TABLE IF EXISTS People;
CREATE TABLE People (PeoId INTEGER PRIMARY KEY AUTOINCREMENT,
                     FilId INTEGER,
                     Person TEXT);

DROP TABLE IF EXISTS AppData;
CREATE TABLE AppData (AppFileVersion TEXT,
                      AlbumTableState BLOB);
INSERT INTO AppData VALUES (NULL, NULL);
