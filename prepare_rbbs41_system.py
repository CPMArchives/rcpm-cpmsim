#!/usr/bin/env python3
"""Create an isolated RBBS 4.1 test installation from a clean release package."""
import argparse
import datetime
import json
from pathlib import Path
import secrets
import shutil
import string
import subprocess
import tempfile

from build_bye5 import run as build_bye


def prepare(a):
    repo = Path(__file__).resolve().parent
    work = a.output.resolve()
    if work.exists():
        raise ValueError('Use a new output directory; never overwrite a trial')
    work.mkdir(parents=True)
    bye = work/'build-bye'
    sources = bye/'sources'
    shutil.copytree(a.baseline/'source/configured/bye5', sources)
    for file in (sources/'BYEDIR.ASM', sources/'BYEMDM.ASM'):
        s = file.read_text()
        assert s.count("WXRBNAME:DB 'RBBS37  COM'") == 1
        s=s.replace("WXRBNAME:DB 'RBBS37  COM'", "WXRBNAME:DB 'RBBS41  COM'")
        file.write_bytes(s.replace('\n','\r\n').encode('ascii'))
    build_bye(a.stock, a.baseline/'runtime/cpmsim', a.tools, sources, bye)
    instance = work/'RBBS41-Test'
    instance.mkdir()
    for name in ('conf', 'runtime', 'drivers'):
        shutil.copytree(a.baseline/name, instance/name)
    (instance/'disks').mkdir()
    for drive in 'ai':
        shutil.copyfile(a.baseline/f'disks/drive{drive}.dsk', instance/f'disks/drive{drive}.dsk')
    for drive in 'jp':
        subprocess.run([str(a.tools/'mkfs.cpm'), '-f', 'z80pack-hd' if drive=='j' else 'z80pack-hdb',
                        str(instance/f'disks/drive{drive}.dsk')], check=True, capture_output=True)
        with (instance/f'disks/drive{drive}.dsk').open('r+b') as stream:
            stream.truncate(4177920 if drive=='j' else 536870912)
    for name in ('direct', 'ip232'):
        shutil.copyfile(bye/name/'BYEDRIV.COM', instance/'drivers'/name/'BYEDRIV.COM')
    def tool(name, *args):
        return subprocess.run([str(a.tools/name), *map(str,args)], check=True,
                              capture_output=True).stdout
    adisk, idisk = (instance/f'disks/drive{x}.dsk' for x in 'ai')
    def put(disk, user, name, data):
        fmt = 'ibm-3740' if disk==adisk else 'z80pack-hd'
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp)/'data'
            f.write_bytes(data)
            tool('cpmrm', '-f', fmt, disk, str(user)+':'+name)
            tool('cpmcp', '-f', fmt, disk, f, str(user)+':'+name)
    def get(disk, user, name):
        fmt = 'ibm-3740' if disk==adisk else 'z80pack-hd'
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'data'
            tool('cpmcp','-f',fmt,disk,str(user)+':'+name,f)
            return f.read_bytes()
    tool('cpmrm','-f','ibm-3740',adisk,'15:*')
    # The old board deliberately uses a lowercase pwds entry, which cpmrm
    # cannot address. Delete all U15 entries on this fresh, stopped copy.
    with idisk.open('r+b') as stream:
        directory=bytearray(stream.read(32768))
        for offset in range(0,len(directory),32):
            if directory[offset]==15: directory[offset]=0xe5
        stream.seek(0)
        stream.write(directory)
    put(adisk, 15, 'RBBS41.COM', (a.board/'RBBS4.COM').read_bytes())
    for user in (0,15):
        put(adisk,user,'BYE.COM',(bye/'direct/BYE.COM').read_bytes())
    put(adisk,0,'BYEDRIV.COM',(bye/'direct/BYEDRIV.COM').read_bytes())
    # Same fixed launcher, same-length target replacement, same admission boundary.
    for disk,user in ((adisk,0),(idisk,13)):
        data=get(disk,user,'RBBS.COM')
        assert data.count(b'RBBS37')==1
        put(disk,user,'RBBS.COM',data.replace(b'RBBS37',b'RBBS41'))
    put(idisk,13,'RBUTIL41.COM',(a.board/'UTIL.COM').read_bytes())
    tool('cpmrm','-f','z80pack-hd',idisk,'13:RBBSINST.*')
    tool('cpmrm','-f','z80pack-hd',idisk,'13:RBBSUTIL.COM')
    welcome=(repo/'guest/welcome.txt').read_text().replace('\n','\r\n').encode('ascii')+b'\x1a'
    put(adisk,0,'WELCOME.TXT',welcome)
    for f in (a.board/'configured').glob('*.CCC'):
        # C.CCC is the compiler runtime, not a board display file.
        if f.name!='C.CCC': put(idisk,15,f.name,f.read_bytes())
    def display(name, value):
        put(idisk,15,name,(value.replace('\n','\r\n')+'\r\n\x1a').encode('ascii'))
    display('BULLETIN.CCC','HUMONGOUS RCP/M - RBBS 4.1.02 TEST SYSTEM\nFresh test database; separate GENERAL, CPM and TEST forums.')
    display('WELCOME.CCC','Welcome to the HUMONGOUS RBBS 4.1 test.\nF selects a forum. C returns to CP/M. G disconnects.')
    display('EXIT2CPM.CCC','Returning to CP/M. Private board files remain protected.')
    subjects=('PERSONAL','GENERAL','CPM','TEST')
    record=bytearray(b' '*128)
    record[:3]=b'04\0'
    for n,name in enumerate(subjects,1): record[n*8:n*8+8]=name.ljust(8).encode()
    put(idisk,15,'SUBJECTS.CCC',record)
    for name in subjects: put(idisk,15,name+'.MSG',b'')
    password=''.join(secrets.choice(string.ascii_uppercase+string.digits) for _ in range(6))
    def rec(fields):
        result=bytearray(b' '*126+b'\r\n')
        for offset,value in fields:
            value=str(value).encode('ascii')+b'\0'
            result[offset:offset+len(value)]=value
        return bytes(result)
    today=datetime.datetime.now().strftime('%m/%d/%y')
    account=rec([(0,'SYSOP'),(31,'!'),(33,'0'),(35,'0'),(37,password),
                 (44,today),(67,'Chiayi, Taiwan')]+[(n,'000') for n in range(97,122,4)])
    put(idisk,15,'USERS.CCC',rec([(0,'MAX REC:   1')])+account)
    put(idisk,15,'CALLERS.CCC',rec([(0,'MAX CALR: 0 0')]))
    for name in ('RBBS.COM','BYE.COM','BYEDRIV.COM'):
        tool('cpmchattr','-f','ibm-3740',adisk,'4','0:'+name)
    (instance/'trial-build.json').write_text(json.dumps({'upper_areas':True,'rbbs':'4.1 Edit 02'})+'\n')
    shutil.copyfile(repo/'run_shared_trial.py', instance/'run_shared_trial.py')
    start=instance/'Start-RBBS41.command'
    start.write_text('#!/bin/sh\nset -eu\ncd -P "$(dirname "$0")"\nexec python3 ./run_shared_trial.py --instance . --port 4002\n')
    start.chmod(0o755)
    (instance/'TEST-CREDENTIALS.json').write_text(json.dumps({'sysop_name':'SYSOP','sysop_password':password})+'\n')
    (instance/'TEST-CREDENTIALS.json').chmod(0o600)
    (instance/'README.txt').write_text(
        'HUMONGOUS RCP/M - RBBS 4.1.02 isolated test system\n\n'
        'Run Start-RBBS41.command. Connect SyncTERM using Raw TCP, 127.0.0.1 port 4002.\n'
        'At the CP/M prompt type RBBS. SYSOP credentials are in TEST-CREDENTIALS.json.\n'
        'New callers can register their own account; passwords are limited to six characters.\n'
        'F selects PERSONAL, GENERAL, CPM or TEST. E enters a message. R reads it.\n'
        'End message text with a period on its own line, then S to store.\n'
        'C returns to CP/M; G disconnects. Ctrl-B in the local console toggles private sysop mode.\n'
        'The private maintenance command is SYSUTLS:RBUTIL41 (while locally blanked).\n'
        'This trial has empty J:/P: images; collections are not included.\n'
        'The release launcher runtime/rcpm is not used: it initializes legacy 3.7 files.\n'
        'Use only Start-RBBS41.command. This is a test, not a production upgrade.\n')
    print(instance,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','stock','tools','board','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in ('baseline','stock','tools','board','output'):
        setattr(a,name,getattr(a,name).resolve())
    prepare(a)
