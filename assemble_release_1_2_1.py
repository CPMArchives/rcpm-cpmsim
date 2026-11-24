#!/usr/bin/env python3
"""Add qualified split-screen CHAT to pristine 1.2 distribution media."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from assemble_release_1_1 import build
from install_chat46 import install
from caller_help import install as install_help

ROOT=Path(__file__).resolve().parent


def prepare(common, tools):
    install(common,ROOT/'guest/chat46',tools)
    install_help(common,tools)
    # Installer rollback files and local lock are not fresh distribution state.
    shutil.rmtree(common/'backups')
    (common/'.console.lock').unlink()
    identity=json.loads((ROOT/'guest/chat46/BUILD.json').read_text())
    (common/'metadata/CHAT46.json').write_text(json.dumps(dict(
        build=identity,qualification='macos-direct-tcp-split-and-scrolling-passed',
        deployment='fresh-distribution-media'),indent=2)+'\n')
    for name in ('SYSOP-GUIDE.DOC','INSTALLATION.DOC'):
        shutil.copy2(ROOT/'packaging'/name,common/'docs'/name)
    # Inspect the files themselves, not only the inherited fresh-media receipt.
    with tempfile.TemporaryDirectory() as temporary:
        def read(name):
            p=Path(temporary)/'data';p.unlink(missing_ok=True)
            subprocess.run([str(tools/'cpmcp'),'-f','z80pack-hd',
                str(common/'disks/drivei.dsk'),'15:'+name,str(p)],
                check=True,capture_output=True)
            return p.read_bytes()
        users=read('USERS.CCC')
        assert len(users)==256 and users[128:134]==b'SYSOP\0'
        assert users[165:172]==b'UNINIT\0'
        for area in ('PERSONAL','GENERAL','CPM','TEST'):assert read(area+'.MSG')==b''
        assert read('CALLERS.CCC').startswith(b'MAX CALR: 0 0\0')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();baseline=a.baseline.resolve()
    mac=baseline/'RCPM-macOS-arm64'
    build(baseline/'rcpm-common',mac,baseline/'RCPM-windows-x64',mac/'runtime',
          a.output.resolve(),'1.2.1',prepare_common=lambda common:prepare(common,mac/'runtime'))
