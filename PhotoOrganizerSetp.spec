# -*- mode: python -*-
a = Analysis(['PhotoOrganizerSetp.py'],
             pathex=['.'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None)

##### Added by Lucas McNinch #######
def extra_datas(root, mydir):
    def rec_glob(p, files):
        import os
        import glob
        for d in glob.glob(p):
            if os.path.isfile(d):
                files.append(d)
            rec_glob("%s/*" % d, files)
    files = []
    rec_glob("%s/*" % os.path.join(root, mydir), files)
    extra_datas = []
    for f in files:
        local = f.replace('{}\\'.format(root), '')
        extra_datas.append((local , f, 'DATA'))

    return extra_datas

a.datas.append(('PhotoOrganizer.zip', 'dist/PhotoOrganizer.zip', 'DATA'))
a.datas.append(('build_info', 'build_info', 'DATA'))

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='PhotoOrganizerSetp.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon=r'POSetp.ico')
