#!/usr/bin/env python3
"""Build fresh 1.2 media from qualified 1.1.1 packages and an RBBS41 seed.

First run build_rbbs41.py and prepare_rbbs41_system.py into a new seed folder.
The seed is only an input: credentials, launcher and test state are never copied.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from assemble_release_1_1 import build

ROOT=Path(__file__).resolve().parent


def prepare_common(common, seed, board, tools):
    for drive in 'ai':
        shutil.copy2(seed/'RBBS41-Test/disks'/f'drive{drive}.dsk', common/'disks'/f'drive{drive}.dsk')
    for mode in ('direct','ip232'):
        shutil.copy2(seed/'build-bye'/mode/'BYEDRIV.COM',common/'drivers'/mode/'BYEDRIV.COM')
    image=common/'disks/drivei.dsk'
    def tool(name,*args):
        return subprocess.run([str(tools/name),'-f','z80pack-hd',str(image),*map(str,args)],check=True,capture_output=True)
    def get(name):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'file';tool('cpmcp','15:'+name,path);return path.read_bytes()
    def put(name,data):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'file';path.write_bytes(data)
            tool('cpmrm','15:'+name);tool('cpmcp',path,'15:'+name)
    users=get('USERS.CCC')
    assert len(users)==256 and users[:13]==b'MAX REC:   1\0' and users[128:134]==b'SYSOP\0'
    users=bytearray(users);users[165:172]=b'UNINIT\0';put('USERS.CCC',users)
    def display(name,text):put(name,text.replace('\n','\r\n').encode('ascii')+b'\r\n\x1a')
    display('BULLETIN.CCC','HUMONGOUS RCP/M - RBBS 4.1.02\nGENERAL, CPM and TEST forums. F selects a forum; ? shows help.')
    display('WELCOME.CCC','Welcome to HUMONGOUS RCP/M.\nF selects a forum. C returns to CP/M. G disconnects.')
    subjects=get('SUBJECTS.CCC');assert subjects[:3]==b'04\0'
    areas=[subjects[n*8:n*8+8].decode().strip() for n in range(1,5)]
    assert areas==['PERSONAL','GENERAL','CPM','TEST']
    for area in areas:assert get(area+'.MSG')==b'',area+' contains messages'
    assert get('CALLERS.CCC').startswith(b'MAX CALR: 0 0\0')
    audit=dict(areas={a:0 for a in areas},accounts=['SYSOP'],callers=0,credential='generated-on-first-start')
    (common/'metadata/RBBS-FRESH.json').write_text(json.dumps(audit,indent=2)+'\n')
    for name in ('SYSOP-GUIDE.DOC','INSTALLATION.DOC'):
        shutil.copy2(ROOT/'packaging'/name,common/'docs'/name)
    target=common/'source/configured/rbbs41'
    shutil.copytree(board/'configured',target,ignore=shutil.ignore_patterns('C.CCC','*.CRL','*.COM'))
    shutil.copytree(seed/'build-bye/sources',common/'source/configured/bye5',dirs_exist_ok=True)
    upstream=common/'source/upstream/rbbs41';shutil.copytree(board/'original',upstream)
    shutil.copy2(board/'BUILD.json',target/'BUILD.json')
    (common/'source/BUILDING-1.2.DOC').write_text(
        'Build board with build_rbbs41.py using rbbs4102.zip and bdsc-all.zip.\n'
        'Prepare a fresh seed with prepare_rbbs41_system.py against 1.1.1.\n'
        'Build native launcher from packaging/launcher.c; cross-build Windows\n'
        'with windows/build_support.py. assemble_release_1_2.py assembles media\n'
        'and asserts all four message files are empty and only SYSOP exists.\n'
        'See source/rcpm/docs/rbbs41-test.md for compiler and integration details.\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','seed','board','tools','runtime','windows-launcher','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a=argparse.Namespace(**{k:v.resolve() for k,v in vars(a).items()})
    build(a.baseline/'rcpm-common',a.baseline/'RCPM-macOS-arm64',a.baseline/'RCPM-windows-x64',a.runtime,a.output,'1.2',
          prepare_common=lambda common:prepare_common(common,a.seed,a.board,a.tools),windows_launcher=a.windows_launcher)
