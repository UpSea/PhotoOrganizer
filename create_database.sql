DROP TABLE IF EXISTS TagMap;
DROP TABLE IF EXISTS Tags;
DROP TABLE IF EXISTS Categories;
DROP TABLE IF EXISTS Fields;
DROP TABLE IF EXISTS File;
DROP TABLE IF EXISTS Database;
CREATE TABLE Database(Name TEXT);
INSERT INTO Database VAlUES (NULL);

CREATE TABLE File (FilId INTEGER PRIMARY KEY AUTOINCREMENT,
                   tagged INTEGER,
                   filename TEXT,
                   directory TEXT,
                   date TEXT,
                   hash TEXT,
                   thumbnail BLOB,
                   importTimeUTC DATETIME DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE Fields (FieldId INTEGER PRIMARY KEY AUTOINCREMENT,
                     Number INTEGER,
                     Name TEXT,
                     Required INTEGER,
                     Editor INTEGER,
                     Editable INTEGER,
                     Name_Editable INTEGER,
                     Hidden INTEGER,
                     Type TEXT,
                     Filt INTEGER,
                     UNIQUE (Name));

CREATE TABLE Categories (CatId INTEGER PRIMARY KEY AUTOINCREMENT,
                         Name TEXT,
                         Plural INTEGER,
                         FOREIGN KEY (Name) REFERENCES Fields(Name),
                         UNIQUE (Name COLLATE NOCASE));

CREATE TABLE Tags (TagId INTEGER PRIMARY KEY AUTOINCREMENT,
                   CatId INTEGER,
                   Value TEXT,
                   FOREIGN KEY (CatId) REFERENCES Categories(CatId),
                   UNIQUE (CatId, Value COLLATE NOCASE));

CREATE TABLE TagMap(FilId INTEGER,
                    TagId INTEGER,
                    FOREIGN KEY(FilId) REFERENCES File(FilId),
                    FOREIGN KEY(TagId) REFERENCES Tags(TagId),
                    UNIQUE (FilId, TagId));

DROP TABLE IF EXISTS AppData;
CREATE TABLE AppData (AppFileVersion TEXT,
                      BuildDate TEXT,
                      LastClosed DATETIME,
                      AlbumTableState BLOB);
INSERT INTO AppData (AppFileVersion) VALUES (NULL);
