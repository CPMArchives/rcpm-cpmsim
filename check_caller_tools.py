#!/usr/bin/env python3
"""Exercise the installed caller viewers in a disposable upper-area trial."""
import argparse
from binascii import crc_hqx
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import socket
import subprocess
import time
import tty

from check_modem_runtime import free_port, stop


def run(root, tools):
    def put(disk, fmt, name, content):
        path = root / 'fixture'
        path.write_bytes(content)
        subprocess.run([str(tools/'cpmcp'), '-f', fmt, str(disk), str(path), name], check=True)
    # Test topics are deliberately absent from the distributable empty HELP.
    put(root/'disks/drivei.dsk','z80pack-hd','14:HELP.HLP',
        b';\r\nCALLER-HELP-OK\r\n\x1a')
    put(root/'disks/drivei.dsk','z80pack-hd','13:SECRET.TXT', b'PRIVATE-CONTENT-MUST-NOT-LEAK\r\n\x1a')
    put(root/'disks/drivei.dsk','z80pack-hd','15:SECRET.TXT', b'PRIVATE-CONTENT-MUST-NOT-LEAK\r\n\x1a')
    # Use a preserved crunched help file to test the original decompressor.
    manifest=json.loads((root/'trial-build.json').read_text())
    original=(Path(manifest['romwbw'])/'Source/Images/Common/NZ3PLUS/u10/HLPFILES.LBR').read_bytes()
    ent=next(k for k in range(32,int.from_bytes(original[14:16],'little')*128,32)
             if original[k:k+12]==b'\0HELP    HZP')
    off=int.from_bytes(original[ent+12:ent+14],'little')*128
    size=int.from_bytes(original[ent+14:ent+16],'little')*128
    packed=original[off:off+size]
    directory=bytearray(b'\xff'*128)
    directory[:32]=bytes(32);directory[14:16]=(1).to_bytes(2,'little')
    text=b'CALLER-LIBRARY-TEXT-OK\r\n\x1a'.ljust(128,b'\x1a')
    for index,name,start,content in ((1,b'README  TXT',1,text),(2,b'HELP    HZP',2,packed)):
        n=index*32;directory[n:n+32]=bytes(32);directory[n+1:n+12]=name
        directory[n+12:n+14]=start.to_bytes(2,'little')
        directory[n+14:n+16]=(len(content)//128).to_bytes(2,'little')
        directory[n+16:n+18]=crc_hqx(content,0).to_bytes(2,'little')
    directory[16:18]=crc_hqx(directory,0).to_bytes(2,'little')
    j=root/'disks/drivej.dsk';j.chmod(0o600)
    put(j,'z80pack-hd','0:TOOLS.LBR',directory+text+packed);j.chmod(0o444)
    # A populated archive must report matched totals above 65535 KiB too.
    p=root/'disks/drivep.dsk';p.chmod(0o600)
    bulk=root/'bulk';bulk.write_bytes(b'X'*(4*1024*1024))
    for n in range(17):
        subprocess.run([str(tools/'cpmcp'),'-f','z80pack-hdb',str(p),str(bulk),f'0:BIG{n:02}.DAT'],check=True)
    p.chmod(0o444);bulk.unlink()
    before={d:hashlib.sha256((root/f'disks/drive{d}.dsk').read_bytes()).hexdigest() for d in 'ajp'}
    master,slave=pty.openpty();tty.setraw(slave);port=free_port()
    guest=subprocess.Popen([str(root/'runtime/cpmsim'),'-f','4'],cwd=root,
        env=dict(os.environ,RCPM_MODEM='direct',RCPM_MODEM_HOST='127.0.0.1',RCPM_MODEM_PORT=str(port)),
        stdin=slave,stdout=slave,stderr=slave)
    local=bytearray();remote=bytearray();caller=None;outputs={}
    def collect(duration):
        end=time.monotonic()+duration
        while time.monotonic()<end:
            for fd in select.select([master]+([caller] if caller else []),[],[],.02)[0]:
                if fd==master:local.extend(os.read(master,8192))
                else:
                    data=caller.recv(8192)
                    if not data:raise RuntimeError('Unexpected caller disconnect')
                    remote.extend(data)
    def wait(mark,buf,start=0,timeout=35):
        end=time.monotonic()+timeout
        while mark not in buf[start:]:
            if time.monotonic()>end:raise RuntimeError('Waiting for '+repr(mark)+': '+repr(buf[start:][-1800:]))
            collect(.05)
    def command(line,expect=None,exit_key=None):
        start=len(remote)
        for c in line.encode()+b'\r':caller.sendall(bytes([c]));collect(.06)
        if expect:wait(expect,remote,start)
        if exit_key:
            collect(.25)
            if b'A0:SYSTEM>' not in remote[start:]:caller.sendall(exit_key)
        wait(b'A0:SYSTEM>',remote,start)
        collect(.15)
        result=bytes(remote[start:]);outputs[line]=result.decode('ascii',errors='replace')
        print(line,repr(result[-1100:]),flush=True)
        if b'PRIVATE-CONTENT-MUST-NOT-LEAK' in result:raise AssertionError('Private data leaked')
        return result
    try:
        wait(b'RCP/M modem ready.',local)
        caller=socket.create_connection(('127.0.0.1',port))
        for _ in range(30):
            caller.sendall(b'\r');collect(.4)
            if b'A0:SYSTEM>' in remote:break
        wait(b'A0:SYSTEM>',remote);collect(1)
        # Boot processing removes its temporary submit file on A:.
        before={d:hashlib.sha256((root/f'disks/drive{d}.dsk').read_bytes()).hexdigest() for d in 'ajp'}
        command('DIR HELP:',b'HELP')
        command('DIR I14:',b'HELP')
        command('DIR P:',b'69632k')
        if b'454400k' not in outputs['DIR P:'].encode():raise AssertionError('Large archive free-space total wrong')
        command('LDIR J:TOOLS',b'README')
        command('LDIR VOLUME:TOOLS',b'README')
        assert b'R C P / M' in remote and b'MOUNT /L lists disks.' in remote
        command('SDZ HELP:',b'HELP')
        command('LT VOLUME:TOOLS README.TXT',b'CALLER-LIBRARY-TEXT-OK')
        command('LT J:HELLO.TXT',b'Hello from the shared')
        command('HELP //',b'Alternate DIR')
        command('HELP',b'CALLER-HELP-OK')
        # Compressed output may page; ^C aborts after proving decode.
        decoded=command('LT VOLUME:TOOLS HELP.HZP',b'The HELP command provides online documentation.',b'\x03')
        if b'Invalid crunched' in decoded:raise AssertionError('Compressed viewer failed')
        for cmd in ('DIR SYSUTLS:','DIR RBBS:','DIR I: /A',
                    'LDIR SYSUTLS:SECRET','LT SYSUTLS:SECRET.TXT',
                    'LT I15:SECRET.TXT','HELP SYSUTLS:SECRET'):
            command(cmd)
        command('DIR J: /F')
        after={d:hashlib.sha256((root/f'disks/drive{d}.dsk').read_bytes()).hexdigest() for d in 'ajp'}
        if before!=after:raise AssertionError('Caller viewers changed protected media')
        (root/'caller-tools-result.json').write_text(json.dumps(dict(passed=True,outputs=outputs,immutable=before==after),indent=2)+'\n')
    finally:
        if caller:caller.close()
        stop(guest);os.close(master);os.close(slave)
        (root/'caller-tools-console.log').write_bytes(local+remote)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instance',type=Path,required=True)
    p.add_argument('--cpmtools',type=Path,default=Path('build/cpmtools/bin'))
    a=p.parse_args();run(a.instance.resolve(),a.cpmtools.resolve())
