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
                     Tags Integer,
                     UNIQUE (Name));

CREATE VIEW Categories AS
    SELECT FieldId as CatId, Name FROM Fields WHERE Tags == 1;

CREATE TABLE Tags (TagId INTEGER PRIMARY KEY AUTOINCREMENT,
                   CatId INTEGER,
                   Value TEXT,
                   FOREIGN KEY (CatId) REFERENCES Fields(FieldId),
                   UNIQUE (CatId, Value COLLATE NOCASE));

CREATE TABLE TagMap(FilId INTEGER,
                    TagId INTEGER,
                    FOREIGN KEY(FilId) REFERENCES File(FilId),
                    FOREIGN KEY(TagId) REFERENCES Tags(TagId),
                    UNIQUE (FilId, TagId));

CREATE TABLE AppData (AppFileVersion TEXT,
                      BuildDate TEXT,
                      LastClosed DATETIME,
                      AlbumTableState BLOB);
INSERT INTO AppData (AppFileVersion) VALUES (NULL);
