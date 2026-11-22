#!/usr/bin/env python3
"""Exercise live AUTH and the common caller ACL in a disposable real guest."""
import argparse
import json
import os
import re
from pathlib import Path
import shutil
import subprocess

from auth_policy import install
from check_bye_speed import prepare
from check_release import Guest, free_port

REPO = Path(__file__).resolve().parent
MARKER = b'AUTH-APPROVED-CODE-RAN'


def run(args):
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    p=out/'instance'
    prepare(args.package,p,args.builds,args.runtime)
    install(p,args.tools,args.source/'z80asm/z80asm')
    def tool(name,*a):
        return subprocess.run([str(args.tools/name),*map(str,a)],check=True,capture_output=True).stdout
    def put(disk,fmt,user,name,data,attrs=''):
        file=out/'put.bin';file.write_bytes(data)
        tool('cpmrm','-f',fmt,disk,f'{user}:{name}')
        tool('cpmcp','-f',fmt,disk,file,f'{user}:{name}')
        if attrs:tool('cpmchattr','-f',fmt,disk,attrs,f'{user}:{name}')
    def asm(name,text):
        (out/(name+'.asm')).write_text(text)
        subprocess.run([str(args.source/'z80asm/z80asm'),'-fb','-x',name+'.asm'],cwd=out,check=True,capture_output=True)
        return (out/(name+'.bin')).read_bytes()
    a=p/'disks/drivea.dsk';i=p/'disks/drivei.dsk';j=p/'disks/library/GAMES.dsk';pd=p/'disks/drivep.dsk'
    # Restore all catalog image opens to guest-controlled writable media.
    mount=asm('mount',(REPO/'guest/mount.asm').read_text())
    put(a,'ibm-3740',0,'MOUNT.COM',mount,'4')
    demo=bytes([0x11,9,1,0x0e,9,0xcd,5,0,0xc9])+MARKER+b'$'
    for disk,fmt,user in ((j,'z80pack-hd',3),(i,'z80pack-hd',0),(i,'z80pack-hd',1),(a,'ibm-3740',1),(pd,'z80pack-hdb',0)):
        put(disk,fmt,user,'DEMO.COM',demo)  # F4 deliberately OFF
    seed=asm('seed',""" ORG 100H
 LD DE,F
 LD C,22
 CALL 5
 LD DE,DATA
 LD C,26
 CALL 5
 LD DE,F
 LD C,21
 CALL 5
 LD DE,F
 LD C,16
 CALL 5
 LD DE,80H
 LD C,26
 CALL 5
 LD DE,MSG
 LD C,9
 CALL 5
 RET
F: DB 9,'DEMO    COM'
 DS 24,0
MSG: DB 'WORK-DEMO-CREATED','$'
DATA:
 DB """+','.join(str(n) for n in demo)+"\n DS 128,0\n")
    put(a,'ibm-3740',0,'SEED.COM',seed,'4')
    authfile=out/'authcopy.com';tool('cpmcp','-f','z80pack-hd',i,'13:AUTH.COM',authfile)
    put(a,'ibm-3740',0,'AUTHCOPY.COM',authfile.read_bytes(),'4')
    # A write-only DU must support the complete create/write/close lifecycle.
    # Read-only must still close an opened reader; NONE must deny both paths.
    lifecycle=asm('closeacl',''' ORG 100H
 LD DE,F
 LD C,22
 CALL 5
 CALL HEX
 LD DE,DATA
 LD C,26
 CALL 5
 LD DE,F
 LD C,21
 CALL 5
 CALL HEX
 LD DE,F
 LD C,16
 CALL 5
 CALL HEX
 LD DE,F
 LD C,15
 CALL 5
 CALL HEX
 LD DE,F
 LD C,20
 CALL 5
 CALL HEX
 LD DE,F
 LD C,17
 CALL 5
 CALL HEX
 LD DE,F
 LD C,16
 CALL 5
 CALL HEX
 LD DE,80H
 LD C,26
 CALL 5
 RET
HEX: PUSH AF
 RRCA
 RRCA
 RRCA
 RRCA
 AND 15
 CALL DIGIT
 POP AF
 AND 15
 CALL DIGIT
 LD E,' '
 LD C,2
 JP 5
DIGIT: ADD A,'0'
 CP '9'+1
 JR C,CHAR
 ADD A,7
CHAR: LD E,A
 LD C,2
 JP 5
F: DB 9,'WONLY   DAT'
 DS 24,0
DATA: DB 'WRITE-ONLY-CLOSE-PERSISTED'
 DS 128,0
''')
    put(a,'ibm-3740',0,'CLOSEACL.COM',lifecycle,'4')
    for letter,code in (('A',1),('I',9),('J',10),('P',16)):
        text=f''' ORG 100H
 LD DE,F
 LD C,15
 CALL 5
 CALL HEX
 LD DE,F
 LD C,21
 CALL 5
 CALL HEX
 LD DE,F
 LD C,30
 CALL 5
 CALL HEX
 LD DE,F
 LD C,23
 CALL 5
 CALL HEX
 LD DE,F
 LD C,19
 CALL 5
 CALL HEX
 LD DE,NEW
 LD C,22
 CALL 5
 CALL HEX
 LD DE,NEW
 LD C,16
 CALL 5
 LD DE,DONE
 LD C,9
 CALL 5
 RET
HEX: PUSH AF
 RRCA
 RRCA
 RRCA
 RRCA
 AND 15
 CALL DIGIT
 POP AF
 AND 15
 CALL DIGIT
 LD E,' '
 LD C,2
 JP 5
DIGIT: ADD A,'0'
 CP '9'+1
 JR C,CHAR
 ADD A,7
CHAR: LD E,A
 LD C,2
 JP 5
F: DB {code},'ACLTEST DAT'
 DS 4,0
 DB 0,'ACLRENA DAT'
 DS 8,0
NEW: DB {code},'ACLNEW  DAT'
 DS 24,0
DONE: DB 'ACL-PROBE-{letter}-DONE','$'
'''
        put(a,'ibm-3740',0,'WR'+letter+'.COM',asm('wr'+letter,text),'4')
    for disk,fmt in ((a,'ibm-3740'),(i,'z80pack-hd'),(j,'z80pack-hd'),(pd,'z80pack-hdb')):
        put(disk,fmt,0,'ACLTEST.DAT',b'TEST DATA\r\n\x1a')
    port=free_port();g=Guest(p,out/'console','--port',str(port))
    private=False
    def blank():
        nonlocal private
        start=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote off]',start=start);g.collect(.2);private=True
    def unblank():
        nonlocal private
        start=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote on]',start=start);g.collect(.2);private=False
    def local(command):
        start=len(g.local)
        for c in (command+'\r').encode():os.write(g.master,bytes([c]));g.collect(.005)
        return g.wait(b'A0:SYSTEM>',start=start)
    def auth(command):
        print('AUTH '+command,flush=True)
        reply=local('SYSUTLS:AUTH '+command)
        assert b'changed in memory' in reply or b'F4 updated' in reply or b'Policy ' in reply,reply
        return reply
    def executes(command,expected):
        reply=g.command(command)
        assert (MARKER in reply)==expected,(command,reply)
    results={}
    try:
        g.wait(b'RCP/M modem ready.');g.connect(port);g.command('MOUNT GAMES');print('Connected and mounted',flush=True)
        assert b'requires private sysop' in g.command('AUTHCOPY /MAP')
        for drive in ('A','J','P'):
            reply=g.command('WR'+drive)
            assert b'FF FF FF FF FF' in reply,(drive,reply)
        reply=g.command('WRI');assert b'FF FF FF FF FF' not in reply,reply
        results['caller_writes_denied_A_J_P']=True
        results['caller_WORK_writes_allowed']=True
        assert b'WORK-DEMO-CREATED' in g.command('SEED')
        blank();auth('I0: W');unblank()
        reply=g.command('CLOSEACL')
        assert b'00 00 00 FF FF FF 00' in reply,reply
        blank();auth('I0: R');unblank()
        reply=g.command('CLOSEACL')
        assert re.search(rb'FF FF 00 00 00 0[0-3] 00',reply),reply
        blank();auth('I0: NONE');unblank()
        reply=g.command('CLOSEACL')
        assert b'FF FF FF FF FF FF FF' in reply,reply
        blank()
        reply=local('TYPE I0:WONLY.DAT')
        assert b'WRITE-ONLY-CLOSE-PERSISTED' in reply,reply
        auth('I0: RW');unblank()
        results['write_only_create_write_close_and_read_denial']=True
        results['read_only_close_and_NONE_denial']=True
        print('Caller write gates PASS',flush=True)
        # I1 remains unreadable, yet selecting it transiently must not prevent
        # a qualified J3 load (Z3 selects user before drive).
        executes('J3:DEMO',False)
        blank()
        for target in ('J3:DEMO.COM','P0:DEMO.COM','I0:DEMO.COM','I1:DEMO.COM','A1:DEMO.COM'):
            auth(target+' +X')
        # Other attributes stay clear: F4-only must suffice, no RO required.
        reply=local('WRJ');assert b'00 00 00' in reply,reply
        reply=local('WRP');assert b'00 00 00' in reply,reply
        auth('I1: R');auth('A1: R')
        auth('/SAVE=I13:AUTH.DAT /Y');unblank()
        executes('J3:DEMO',True);executes('P0:DEMO',True)
        executes('I1:DEMO',True);executes('A1:DEMO',True)
        executes('I0:DEMO',False)
        results['F4_only_approval_all_drives']=True
        results['private_J_P_writes_allowed']=True
        blank();auth('I0: R');unblank();executes('I0:DEMO',True)
        blank();auth('I0: RW');auth('J3: RW');unblank()
        executes('I0:DEMO',False);executes('J3:DEMO',False)
        blank();auth('J: NONE');auth('J3: R');unblank();executes('J3:DEMO',True)
        blank();auth('J3: INHERIT');unblank();executes('J3:DEMO',False)
        blank();auth('J: R');auth('J3:DEMO.COM -X');unblank();executes('J3:DEMO',False)
        blank();auth('J3:DEMO.COM +X');auth('/SAVE=I13:AUTH.DAT /Y');auth('J: NONE');auth('/LOAD=I13:AUTH.DAT');unblank()
        executes('J3:DEMO',True)
        results.update(live_grant_revoke=True,DU_overrides_drive=True,inheritance=True,writable_DU_non_executable=True,save_reload=True)
        # Trusted RBBS must still enter with its private data inaccessible to
        # ordinary file commands; finish it through the normal carrier boundary.
        start=len(g.remote)
        for c in b'RBBS\r':g.caller.sendall(bytes([c]));g.collect(.01)
        g.wait(b'Enter your FIRST Name:',remote=True,start=start)
        g.caller.close();g.caller=None
        g.wait(b'RCP/M modem ready.',start=len(g.local),timeout=60)
        results['RBBS_scoped_private_data']=True
        # Stop using the ordinary local menu after caller disconnect.
        g.stop()
    finally:
        g.close()
    # Fresh process must load saved disk ACLs; F4 persists in each image.
    port=free_port();g=Guest(p,out/'restart','--port',str(port))
    try:
        g.wait(b'RCP/M modem ready.');g.connect(port);g.command('MOUNT GAMES');print('Connected and mounted',flush=True)
        executes('J3:DEMO',True);executes('I1:DEMO',True)
        results['restart_persistence']=True
        g.stop()
    finally:g.close()
    (out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name,default in (('package','build/release-games-final/RCPM-macOS-arm64'),('builds','build/bye5'),('runtime','build/modem/cpmsim'),('tools','build/release-tools/bin'),('source','/tmp/rcpm-z80pack.8ScWG5')):
        p.add_argument('--'+name,type=Path,default=Path(default))
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    for name,value in vars(args).items():setattr(args,name,value.resolve())
    run(args)
