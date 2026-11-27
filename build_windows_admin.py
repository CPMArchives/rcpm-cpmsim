#!/usr/bin/env python3
"""Build the optional Windows administration package from published 1.2.2 media."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from check_windows_release import unpack

REPO=Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(REPO/'packaging/windows'))
from win_store import files,sha


def build(package,output):
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-windows-addon-') as tmp:
        base=unpack(package,Path(tmp));manifest=json.loads((base/'metadata/MANIFEST.json').read_text())
        if manifest.get('version')!='v1.2.2':raise ValueError('Use the published Windows 1.2.2 package')
        root=output/'RCPM-admin-windows-x64';(root/'helpers').mkdir(parents=True)
        for name in ('win_admin.py','win_platform.py','win_store.py','tasks.ps1'):
            shutil.copy2(REPO/'packaging/windows'/name,root/'helpers'/name)
        (root/'Install-Hosting.py').write_text('''import argparse,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'helpers'))
import win_admin as admin
import win_store as store
if sys.platform!='win32':raise SystemExit('Windows required')
p=argparse.ArgumentParser(description='Optional per-user Windows RCP/M administration')
p.add_argument('--package',type=Path,required=True)
p.add_argument('--home',type=Path,default=admin.default_home())
action=p.add_mutually_exclusive_group(required=True)
action.add_argument('--check',action='store_true');action.add_argument('--install',action='store_true')
a=p.parse_args()
if a.check:
    store.validate(root,a.package.resolve());print('Preflight passed; nothing installed or started.')
else:admin.install(root,a.package.resolve(),a.home.resolve())
''',encoding='utf-8')
        (root/'Install-Hosting.cmd').write_text('@echo off\nchcp 65001 >nul\npy -3 -B "%~dp0Install-Hosting.py" %*\n',encoding='utf-8')
        shutil.copy2(REPO/'docs/ADMINISTRATION-WINDOWS.md',root/'README.md')
        for name in ('build_windows_admin.py','check_windows_admin.py','check_windows_release.py'):
            target=root/'source'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(REPO/name,target)
        for area,names in [('packaging/windows',('win_admin.py','win_platform.py','win_store.py','tasks.ps1')),
                           ('docs',('ADMINISTRATION-WINDOWS.md',))]:
            for name in names:
                target=root/'source'/area/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(REPO/area/name,target)
        receipt=dict(version='0.1.0',platform='windows-x64',kind='optional-user-task-scheduler-administration',
                     compatible_rcpm='v1.2.2',base_archive_sha256=sha(package),files=files(root),
                     base_runtime_media_sha256={n:h for n,h in {**manifest['common'],**manifest['host']}.items()
                                                if n.startswith(('runtime/','disks/','drivers/'))})
        (root/'metadata').mkdir();(root/'metadata/ADDON.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        archive=output/'rcpm-admin-v0.1.0-windows-x64.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(root.rglob('*')):z.write(path,path.relative_to(output))
        (output/'SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n',encoding='ascii')
        print(archive)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.package.resolve(),a.output.resolve())
