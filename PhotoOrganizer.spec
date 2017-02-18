# -*- mode: python -*-
a = Analysis(['PhotoOrganizer.py'],
             pathex=['C:\\Users\\Luke\\Files\\Python\\workspace\\PicOrganizer'],
             hiddenimports=[],
             hookspath=['.\\hooks\\'],
             runtime_hooks=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='PhotoOrganizer.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )

#### USER ADDED #####
def add_folder(datas, folder, exe_root):
    for r, d, files in os.walk(folder):
        for f in files:
            if f.lower() != 'thumbs.db':
                exe_path = os.path.join(exe_root, r.replace(folder, ''), f)
                local_path = os.path.join(r, f)
                datas += [(exe_path, local_path, 'DATA')]

add_folder(a.datas, 'icons', 'icons')
a.datas += [('create_database.sql', 'create_database.sql', 'DATA')]
a.datas += [('ChangeLog.txt', 'ChangeLog.txt', 'DATA')]

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='PhotoOrganizer')
