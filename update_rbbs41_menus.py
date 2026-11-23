#!/usr/bin/env python3
"""Install menu-only RBBS updates on a stopped test system, preserving data."""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def update(instance, board, tools):
    identity=json.loads((instance/'trial-build.json').read_text())
    if identity.get('rbbs')!='4.1 Edit 02':
        raise ValueError('Expected the isolated RBBS 4.1 test installation')
    with (instance/'.console.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('The test system is running. Stop it, then run this updater again.')
        def tool(name,*args):
            return subprocess.run([str(tools/name),*map(str,args)],check=True,capture_output=True).stdout
        with tempfile.TemporaryDirectory(prefix='.menu-update-',dir=instance) as temp:
            stage=Path(temp)
            images={}
            for drive in 'ai':
                images[drive]=stage/f'drive{drive}.dsk'
                shutil.copyfile(instance/f'disks/drive{drive}.dsk',images[drive])
            def read(drive,user,name):
                fmt='ibm-3740' if drive=='a' else 'z80pack-hd'
                dest=stage/'readback'
                dest.unlink(missing_ok=True)
                tool('cpmcp','-f',fmt,images[drive],f'{user}:{name}',dest)
                return dest.read_bytes()
            names=tool('cpmls','-f','z80pack-hd',images['i'],'15:*').decode().split()
            protected=[n for n in names if n.lower().endswith('.msg') or n.lower() in
                       ('users.ccc','callers.ccc','subjects.ccc')]
            before={name:hashlib.sha256(read('i',15,name)).hexdigest() for name in protected}
            replacements=[('a',15,'RBBS41.COM',board/'RBBS4.COM'),
                          ('i',13,'RBUTIL41.COM',board/'UTIL.COM')]
            replacements += [('i',15,n,board/'configured'/n)
                             for n in ('HELP.CCC','MSGHELP.CCC','SELHELP.CCC')]
            for drive,user,name,source in replacements:
                fmt='ibm-3740' if drive=='a' else 'z80pack-hd'
                tool('cpmrm','-f',fmt,images[drive],f'{user}:{name}')
                tool('cpmcp','-f',fmt,images[drive],source,f'{user}:{name}')
                assert read(drive,user,name).rstrip(b'\x1a')==source.read_bytes().rstrip(b'\x1a')
            after={name:hashlib.sha256(read('i',15,name)).hexdigest() for name in protected}
            if before!=after:
                raise ValueError('Account/forum/message data changed; update refused')
            backup=instance/'backups'/datetime.datetime.now().strftime('before-menus-%Y%m%d-%H%M%S')
            backup.mkdir(parents=True,exist_ok=False)
            for drive in 'ai':
                shutil.copyfile(instance/f'disks/drive{drive}.dsk',backup/f'drive{drive}.dsk')
            installed=[]
            try:
                for drive in 'ai':
                    os.replace(images[drive],instance/f'disks/drive{drive}.dsk')
                    installed.append(drive)
            except BaseException:
                for drive in installed:
                    shutil.copyfile(backup/f'drive{drive}.dsk',instance/f'disks/drive{drive}.dsk')
                raise
            receipt={'menu_build':json.loads((board/'BUILD.json').read_text()),
                     'account_forum_message_hashes_unchanged':before,'backup':str(backup)}
            (instance/'MENU-UPDATE.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Menu update installed. Accounts, forum definitions and messages are unchanged.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('instance','board','tools'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    update(a.instance.resolve(),a.board.resolve(),a.tools.resolve())
