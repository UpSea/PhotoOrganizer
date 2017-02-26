import sqlite3
import shutil
import os
from shared import replace, __release__


def _convert02to03(dbfile):
    """ Convert files between 0.2 and 0.3 to 0.3 """
    # Create a backup copy
    p, f = os.path.split(dbfile)
    n, e = os.path.splitext(f)
    bu = os.path.join(p, n + '_backup0.2' + e)
    shutil.copyfile(dbfile, bu)

    try:
        with sqlite3.connect(dbfile) as con:
            # con.execute('PRAGMA Foreign_Keys="on"')
            # Get the sql for the new tables and views
            tmp = sqlite3.connect(':memory:')
            thisDir = os.path.split(__file__)[0]
            script = os.path.join(thisDir, 'create_database.sql')
            tmp.executescript(open(script, 'rb').read())
            cur = tmp.execute('SELECT tbl_name, sql FROM sqlite_master '
                              'WHERE Type == "table"')
            sql = dict(cur.fetchall())
            vsql = tmp.execute('SELECT sql FROM sqlite_master '
                               'WHERE Type == "view"').fetchall()

        #     rep = {'TagMap': 'TagMap2', 'Tags': 'Tags2'}
        #     tmSql = replace(sql['TagMap'], rep)
        #     con.execute(tmSql)
        #     con.execute('INSERT INTO TagMap2 SELECT * FROM TagMap')
        #     con.execute('DROP TABLE TagMap')

            # Create the table that will be renamed
            rep = {"Tags": "Tags2", "Categories": "Fields",
                   'CatId': 'FieldId'}
            tagSql = replace(sql['Tags'], rep)
            con.execute(tagSql)
            con.execute('INSERT INTO Tags2 SELECT * FROM Tags')

            # Replace CatIds with FieldIds
            con.execute('WITH Tmp(TagId, FieldId) AS '
                            '(Select TagId, FieldId FROM Tags '
                            'JOIN Categories ON Tags.CatId == Categories.CatId '
                            'JOIN Fields ON Fields.Name == Categories.Name) '
                        'UPDATE Tags2 SET FieldId == (SELECT FieldId FROM Tmp '
                            'WHERE Tags2.TagId == Tmp.TagId)')

            con.execute('DROP TABLE Tags')
            con.execute('ALTER Table Tags2 RENAME TO Tags')
            # Now Tags is correct schema

            # Add the new field to Fields
            con.execute('ALTER Table Fields ADD COLUMN Tags INTEGER')
            # Make the old categories "tags"
            con.execute('UPDATE Fields SET Tags=1 WHERE Name IN '
                        '(SELECT Name FROM Categories)')
            con.execute('DROP TABLE Categories')

            for s in vsql:
                con.execute(s[0])

            # Update the AppFileVersion
            u = 'UPDATE AppData SET AppFileVersion = ?'
            con.execute(u, (__release__,))
    except Exception as err:
        import pdb
        pdb.set_trace()
        return False, str(err)

    return (True, "Converted 0.2 to 0.3")
