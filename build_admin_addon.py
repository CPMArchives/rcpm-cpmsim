#!/usr/bin/env python3
"""Build only the optional administration add-on for a verified standard package."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from check_release import extract_package
from build_hosting_addon import files, sha, write_json

REPO = Path(__file__).resolve().parent


def build(package, output, version='0.1.0'):
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-addon-build-') as temporary:
        base = extract_package(package, Path(temporary))
        manifest = json.loads((base/'metadata/MANIFEST.json').read_text())
        expected = {**manifest['common'], **manifest['host']}
        if files(base) != {**expected,'metadata/MANIFEST.json':sha(base/'metadata/MANIFEST.json')}:
            raise ValueError('Standard package manifest mismatch')
        platform = manifest['platform']
        if platform not in ('linux-arm64','linux-x64') or manifest.get('version') != 'v1.2.2':
            raise ValueError('This add-on requires standard RCP/M v1.2.2 for Linux')
        root = output / ('RCPM-admin-'+platform)
        root.mkdir()
        shutil.copytree(REPO/'packaging/native',root/'service',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        shutil.copy2(REPO/'packaging/install_hosting_addon.py',root/'Install-Hosting.py')
        (root/'Install-Hosting.sh').write_text('#!/bin/sh\nset -eu\nexec python3 "$(dirname "$0")/Install-Hosting.py" "$@"\n')
        (root/'Install-Hosting.sh').chmod(0o755)
        for source,target in [('hosting-addon.md','README.md'),('INSTALLATION-NATIVE-SERVICE.md','INSTALLATION-NATIVE-SERVICE.md'),('operational-monitoring.md','operational-monitoring.md')]:
            shutil.copy2(REPO/'docs'/source,root/target)
        sources=root/'source';sources.mkdir()
        for name in ('build_admin_addon.py','build_hosting_addon.py','test_native_service.py','test_native_monitor.py','check_admin_addon.py'):
            shutil.copy2(REPO/name,sources/name)
        shutil.copytree(root/'service',sources/'packaging/native')
        shutil.copy2(REPO/'packaging/install_hosting_addon.py',sources/'packaging/install_hosting_addon.py')
        write_json(root/'metadata/ADDON.json',dict(version=version,kind='optional-administration-addon',
            platform=platform,compatible_rcpm='v1.2.2',base_archive_sha256=sha(package),
            base_runtime_media_sha256={n:h for n,h in expected.items() if n.startswith(('runtime/','disks/','drivers/'))},
            files=files(root)))
        archive=output/('rcpm-admin-v'+version+'-'+platform+'.tar.gz')
        with tarfile.open(archive,'w:gz') as stream:stream.add(root,arcname=root.name)
        (output/'SHA256SUMS').write_text(sha(archive)+'  '+archive.name+'\n')
        print(archive,flush=True)
        return root


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();build(a.package.resolve(),a.output.resolve())
