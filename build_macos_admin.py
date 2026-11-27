#!/usr/bin/env python3
"""Build the separate per-user macOS administration add-on."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from check_release import extract_package
from build_hosting_addon import files,sha,write_json

REPO=Path(__file__).resolve().parent


def build(package,output):
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-mac-addon-') as temporary:
        base=extract_package(package,Path(temporary))
        manifest=json.loads((base/'metadata/MANIFEST.json').read_text())
        expected={**manifest['common'],**manifest['host']}
        if files(base)!={**expected,'metadata/MANIFEST.json':sha(base/'metadata/MANIFEST.json')}:
            raise ValueError('Base manifest mismatch')
        if manifest.get('platform')!='macos-arm64' or manifest.get('version')!='v1.2.2':
            raise ValueError('Use the standard macOS ARM64 v1.2.2 package')
        root=output/'RCPM-admin-macos-arm64';root.mkdir()
        (root/'helpers').mkdir()
        for name in ('rcpm_service.py','rcpm_monitor.py'):
            shutil.copy2(REPO/'packaging/native'/name,root/'helpers'/name)
        for name in ('rcpm_admin.py','mac_preflight.py'):
            shutil.copy2(REPO/'packaging/macos'/name,root/'helpers'/name)
        (root/'Install-Hosting.py').write_text('''import argparse,sys
from pathlib import Path
sys.dont_write_bytecode=True
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'helpers'))
from rcpm_admin import install,DEFAULT_HOME
from mac_preflight import validate
p=argparse.ArgumentParser(description="Optional macOS administration installation; no sudo")
p.add_argument('--package',type=Path,required=True)
p.add_argument('--home',type=Path,default=DEFAULT_HOME)
p.add_argument('--label',default='org.cpmarchives.rcpm')
action=p.add_mutually_exclusive_group(required=True)
action.add_argument('--check',action='store_true');action.add_argument('--install',action='store_true')
a=p.parse_args()
if a.check:
    validate(root,a.package.resolve());print('Preflight passed; nothing installed or started.')
else:install(root,a.package.resolve(),a.home.expanduser().absolute(),a.label)
''')
        (root/'Install-Hosting.sh').write_text('#!/bin/sh\nset -eu\nexec python3 -B "$(dirname "$0")/Install-Hosting.py" "$@"\n')
        (root/'Install-Hosting.sh').chmod(0o755)
        shutil.copy2(REPO/'docs/ADMINISTRATION-MACOS.md',root/'README.md')
        for name in ('build_macos_admin.py','build_hosting_addon.py','check_release.py','check_macos_admin.py'):
            target=root/'source'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(REPO/name,target)
        for area,names in [('packaging/native',('rcpm_service.py','rcpm_monitor.py')),
                           ('packaging/macos',('rcpm_admin.py','mac_preflight.py')),
                           ('docs',('ADMINISTRATION-MACOS.md',))]:
            for name in names:
                target=root/'source'/area/name;target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(REPO/area/name,target)
        write_json(root/'metadata/ADDON.json',dict(version='0.1.0',platform='macos-arm64',
            kind='optional-user-launchd-administration',compatible_rcpm='v1.2.2',
            base_archive_sha256=sha(package),files=files(root),
            base_runtime_media_sha256={n:h for n,h in expected.items() if n.startswith(('runtime/','disks/','drivers/'))}))
        archive=output/'rcpm-admin-v0.1.0-macos-arm64.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as target:
            for path in sorted(root.rglob('*')):target.write(path,path.relative_to(output))
        (output/'SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n')
        print(archive,flush=True)
        return root


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.package.resolve(),a.output.resolve())
