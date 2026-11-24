#!/usr/bin/env python3
"""Install CHAT46 on stopped media, with backups and file readback."""
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


def install(instance, build, tools):
    chat = (build/'CHAT.COM').read_bytes()
    identity = json.loads((build/'BUILD.json').read_text())
    if hashlib.sha256(chat).hexdigest() != identity['executable_sha256']:
        raise ValueError('CHAT executable changed since build')
    with (instance/'.console.lock').open('a+b') as lease:
        try: fcntl.flock(lease, fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Stop RCP/M before installing CHAT; use local Ctrl-C, Return, then SYSUTLS:BYEBYE.')
        for drive in 'ai':
            disk = instance/f'disks/drive{drive}.dsk'
            if disk.is_symlink() or not disk.is_file():
                raise ValueError('Expected owned A:/I: images')
        with tempfile.TemporaryDirectory(prefix='.chat46-',dir=instance) as temporary:
            stage = Path(temporary)
            disks = {d:stage/f'drive{d}.dsk' for d in 'ai'}
            for d,p in disks.items():shutil.copyfile(instance/f'disks/drive{d}.dsk',p)
            def tool(name,*args):
                return subprocess.run([str(tools/name),*map(str,args)],check=True,capture_output=True).stdout
            def read(d,user,name):
                fmt='ibm-3740' if d=='a' else 'z80pack-hd'
                path=stage/'readback';path.unlink(missing_ok=True)
                tool('cpmcp','-f',fmt,disks[d],f'{user}:{name}',path)
                return path.read_bytes()
            def put(d,user,name,data):
                fmt='ibm-3740' if d=='a' else 'z80pack-hd'
                data += b'\x1a'*(-len(data)%128)
                source=stage/'input';source.write_bytes(data)
                tool('cpmrm','-f',fmt,disks[d],f'{user}:{name}')
                tool('cpmcp','-f',fmt,disks[d],source,f'{user}:{name}')
                if read(d,user,name)!=data:raise ValueError('Readback failed: '+name)
            put('a',0,'CHAT.COM',chat)
            tool('cpmchattr','-f','ibm-3740',disks['a'],'4','0:CHAT.COM')
            flags=tool('cpmls','-A','-f','ibm-3740',disks['a'],'0:CHAT.COM').decode()
            if not any(len(line.split())==2 and line.split()[0][3]=='4' for line in flags.splitlines()):
                raise ValueError('CHAT caller approval attribute was not set')
            welcome=read('a',0,'WELCOME.TXT').split(b'\x1a')[0].rstrip(b'\0')
            if b'CHAT -' not in welcome:
                welcome=welcome.rstrip()+b'\r\n\r\nCHAT - page the sysop for a live conversation\r\n'
            put('a',0,'WELCOME.TXT',welcome+b'\x1a')
            helptext=(Path(__file__).parent/'guest/help/CHAT.HLP').read_text()
            put('i',14,'CHAT.HLP',helptext.replace('\n','\r\n').encode()+b'\x1a')
            def snapshot(image, fmt, excluded):
                # Ask cpmtools to handle floppy sector skew and extent mapping.
                listing=tool('cpmls','-A','-f',fmt,image).decode('ascii')
                files={};user=None
                for line in listing.splitlines():
                    if line.endswith(':') and line[:-1].isdigit():
                        user=int(line[:-1]);continue
                    fields=line.split()
                    if len(fields)!=2:continue
                    attributes,name=fields
                    if (user,name.upper()) in excluded:continue
                    path=stage/'snapshot';path.unlink(missing_ok=True)
                    tool('cpmcp','-f',fmt,image,f'{user}:{name}',path)
                    files[(user,name)]=(attributes,hashlib.sha256(path.read_bytes()).hexdigest())
                return files
            for d, changed in [('a',{(0,'CHAT.COM'),(0,'WELCOME.TXT')}),('i',{(14,'CHAT.HLP')})]:
                fmt='ibm-3740' if d=='a' else 'z80pack-hd'
                before=snapshot(instance/f'disks/drive{d}.dsk',fmt,changed)
                after=snapshot(disks[d],fmt,changed)
                if before!=after:raise ValueError('Unrelated files changed on '+d.upper()+':')
            backup=instance/'backups'/datetime.datetime.now().strftime('before-chat46-%Y%m%d-%H%M%S-%f')
            backup.mkdir(parents=True)
            for d in 'ai':shutil.copy2(instance/f'disks/drive{d}.dsk',backup/f'drive{d}.dsk')
            # Publish help first. Restore both disks if either replacement fails.
            try:
                for d in 'ia':os.replace(disks[d],instance/f'disks/drive{d}.dsk')
            except BaseException:
                for d in 'ai':shutil.copyfile(backup/f'drive{d}.dsk',instance/f'disks/drive{d}.dsk')
                raise
        target=instance/'source/configured/chat46'
        target.mkdir(parents=True,exist_ok=True)
        for name in ('CHAT.MAC','CHAT.COM','BUILD.json','chat46-original.asm'):
            shutil.copyfile(build/name,target/name)
        (instance/'docs').mkdir(exist_ok=True)
        shutil.copyfile(Path(__file__).parent/'docs/chat46.md',instance/'docs/CHAT46.md')
        (instance/'metadata').mkdir(exist_ok=True)
        (instance/'metadata/CHAT46.json').write_text(json.dumps(dict(
            build=identity,backup=str(backup),unrelated_files_preserved=True),indent=2)+'\n')
    print('Installed A0:CHAT.COM and HELP CHAT. Backup: '+str(backup))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('instance','build','tools'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();install(a.instance.resolve(),a.build.resolve(),a.tools.resolve())
