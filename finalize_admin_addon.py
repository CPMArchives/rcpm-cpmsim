#!/usr/bin/env python3
"""Finalize checked administration archives, preserving all installed-code hashes."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from build_hosting_addon import files, sha, write_json

REPO=Path(__file__).resolve().parent


def finalize(inputs,output,run_id):
    output.mkdir(parents=True,exist_ok=False)
    report=dict(version='0.1.0',compatible_rcpm='1.2.2',build_run=run_id,architectures={})
    for arch in ('arm64','x64'):
        folder=inputs/('admin-v0.1.0-linux-'+arch)
        result=json.loads((folder/'VALIDATION.json').read_text())
        if result.get('passed') is not True:raise ValueError('Missing successful installation check')
        name='rcpm-admin-v0.1.0-linux-'+arch+'.tar.gz'
        path=folder/name
        with tempfile.TemporaryDirectory(prefix='rcpm-admin-final-') as temporary:
            work=Path(temporary)
            with tarfile.open(path) as source:
                for item in source.getmembers():
                    p=Path(item.name)
                    if p.is_absolute() or '..' in p.parts or not (item.isfile() or item.isdir()):
                        raise ValueError('Unsafe add-on archive')
                source.extractall(work)
            root=work/('RCPM-admin-linux-'+arch)
            receipt=json.loads((root/'metadata/ADDON.json').read_text())
            expected=receipt['files']
            if files(root)!={**expected,'metadata/ADDON.json':sha(root/'metadata/ADDON.json')}:
                raise ValueError('Add-on manifest mismatch')
            operational={n:h for n,h in expected.items() if n.startswith('service/') or n.startswith('Install-Hosting')}
            for p in (REPO/'packaging/native').iterdir():
                if p.is_file() and operational.get('service/'+p.name)!=sha(p):
                    raise ValueError('Installed code changed after checks: '+p.name)
            if operational['Install-Hosting.py']!=sha(REPO/'packaging/install_hosting_addon.py'):
                raise ValueError('Installer changed after checks')
            # Complete the developer source export; operational bytes are retained.
            shutil.copy2(REPO/'build_admin_addon.py',root/'source/build_admin_addon.py')
            shutil.copy2(REPO/'check_release.py',root/'source/check_release.py')
            (root/'source/docs').mkdir(exist_ok=True)
            for n in ('hosting-addon.md','INSTALLATION-NATIVE-SERVICE.md','operational-monitoring.md'):
                shutil.copy2(REPO/'docs'/n,root/'source/docs'/n)
            receipt['files']={n:h for n,h in files(root).items() if n!='metadata/ADDON.json'}
            write_json(root/'metadata/ADDON.json',receipt)
            assert all(sha(root/n)==h for n,h in operational.items())
            with tarfile.open(output/name,'w:gz') as target:target.add(root,arcname=root.name)
            report['architectures'][arch]=dict(checks=result,artifact=name,sha256=sha(output/name),
                installed_code_sha256=operational,base_archive_sha256=receipt['base_archive_sha256'])
    shutil.copy2(REPO/'docs/hosting-addon.md',output/'README.md')
    shutil.copy2(REPO/'docs/INSTALLATION-NATIVE-SERVICE.md',output/'ADMINISTRATION.md')
    write_json(output/'VALIDATION.json',report)
    (output/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(output.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--run',required=True)
    a=p.parse_args();finalize(a.inputs.resolve(),a.output.resolve(),a.run)
