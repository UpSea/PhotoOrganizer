CREATE TABLE Database(Name TEXT);
INSERT INTO Database VAlUES (NULL);

CREATE TABLE File (FilId INTEGER PRIMARY KEY AUTOINCREMENT,
                   tagged INTEGER,
                   filename TEXT,
                   directory TEXT,
                   filedate DATETIME,
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

CREATE TABLE Tags (TagId INTEGER PRIMARY KEY AUTOINCREMENT,
                   FieldId INTEGER,
                   Value TEXT,
                   FOREIGN KEY (FieldId) REFERENCES Fields(FieldId),
                   UNIQUE (FieldId, Value COLLATE NOCASE));

CREATE TABLE TagMap(FilId INTEGER,
                    TagId INTEGER,
                    FOREIGN KEY(FilId) REFERENCES File(FilId),
                    FOREIGN KEY(TagId) REFERENCES Tags(TagId),
                    UNIQUE (FilId, TagId));

CREATE VIEW TagFields AS
    SELECT * FROM Fields WHERE Tags == 1;

CREATE VIEW TagList AS
    SELECT t.*, c.Name as Field FROM Tags as t
    JOIN TagFields AS c ON c.FieldId == t.FieldId;

CREATE VIEW AllTags AS
    SELECT m.FilId, t.* FROM TagList as t
    JOIN TagMap as m ON m.TagId == t.TagId
    ORDER BY m.FilId, t.TagId;

CREATE TABLE AppData (AppFileVersion TEXT,
                      BuildDate TEXT,
                      LastClosed DATETIME,
                      AlbumTableState BLOB);
INSERT INTO AppData (AppFileVersion) VALUES (NULL);
