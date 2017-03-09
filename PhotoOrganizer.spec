# -*- mode: python -*-
a = Analysis([r'src\PhotoOrganizer.py'],
              pathex=['.'],
              hiddenimports=[],
              hookspath=[r'src\hooks'],
              runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='PhotoOrganizer.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon=r'src\icons\PO.ico')

#### USER ADDED #####
def add_folder(datas, exe_root, folder):
    for r, d, files in os.walk(folder):
        for f in files:
            if f.lower() != 'thumbs.db':
                exe_path = os.path.join(exe_root, r.replace(folder, ''), f)
                local_path = os.path.join(r, f)
                datas += [(exe_path, local_path, 'DATA')]

add_folder(a.datas, 'icons', r'src\icons')
a.datas += [(r'datastore\database\create_database.sql',
		     r'src\datastore\database\create_database.sql', 'DATA')]
a.datas += [('ChangeLog.txt', 'ChangeLog.txt', 'DATA')]
a.datas.append(('build_info', 'build_info', 'DATA'))
####################

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='PhotoOrganizer')
