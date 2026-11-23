#!/usr/bin/env python3
"""Check board functions locally under CP/M 3 without network permissions."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from build_rbbs41 import Machine


def check(a):
    root=a.output.resolve();root.mkdir(parents=True)
    (root/'disks').mkdir();(root/'conf').mkdir()
    for kind in ('server','client'):(root/f'conf/net_{kind}.conf').write_text('# Offline test\n')
    shutil.copyfile(a.stock/'cpmsim/disks/library/cpm3-1.dsk',root/'disks/drivea.dsk')
    shutil.copyfile(a.instance/'disks/drivei.dsk',root/'disks/drivei.dsk')
    def tool(name,*args):
        return subprocess.run([str(a.tools/name),*map(str,args)],check=True,capture_output=True).stdout
    tool('cpmrm','-f','ibm-3740',root/'disks/drivea.dsk','0:PROFILE.SUB')
    tool('cpmcp','-f','z80pack-hd',root/'disks/drivei.dsk',a.board/'RBBS4.COM','0:RBBS41.COM')
    tool('cpmcp','-f','z80pack-hd',root/'disks/drivei.dsk',a.board/'UTIL.COM','0:RBUTIL41.COM')
    runtime=a.instance/'runtime/cpmsim'
    guest=Machine(root,runtime,root/'local.log')
    password=json.loads((a.instance/'TEST-CREDENTIALS.json').read_text())['sysop_password']
    result={}
    def send(value,marker):
        print('Sending '+('password' if value in (password,'TRIAL1','TRIAL2') else value),flush=True)
        for byte in value.encode('ascii')+b'\r':
            os.write(guest.master,bytes([byte]));time.sleep(.01)
        return guest.read(marker,20)
    def login(name,pwd,new=False):
        send('I:RBBS41',b'Enter your name:')
        if not new:
            send(name,b'Password:')
            return send(pwd,b'Command:')
        send(name,b'Is the name correct')
        send('Y',b'Enter your City, State:')
        send('TAIWAN',b'Is the name,')
        send('Y',b'Enter new password')
        send(pwd,b'Enter the new password again:')
        send(pwd,b'Command:')
        send('X',b'Command:')
    def forum(n):
        listing=send('F',b'Forum number:')
        return listing,send(str(n),b'Command:')
    def post(subject,body,to=''):
        send('E',b'To:')
        send(to,b'Subject:')
        send(subject,b' 1>:')
        send(body,b' 2>:')
        send('.',b'Choice:')
        return send('S',b'Command:')
    def readmsg():
        send('R',b'Message Number:')
        return send('1',b'Command:')
    try:
        guest.read(b'A>')
        initial=login('SYSOP',password)
        assert all(x in initial for x in (b'MESSAGES',b'INFORMATION',b'SESSION'))
        helptext=send('?',b'Command:')
        assert all(x in helptext for x in (b'R;123',b'R;1+',b'R;1*',b'UPLOAD'))
        expert=send('X',b'Command:')
        assert b'GENERAL Command:' in expert and b'INFORMATION' not in expert
        send('X',b'Command:')
        result['compact_menus_help_and_expert_prompt']=True
        result['sysop_login']=True
        listing=send('F',b'Forum number:')
        assert all(x in listing for x in (b'PERSONAL',b'GENERAL',b'CPM',b'TEST'))
        send('-1',b'Forum number:');send('9',b'Forum number:');send('4',b'Command:')
        result['forums_and_invalid_selection']=True
        post('TEST AREA MESSAGE','PERSISTENT TEST AREA CONTENT')
        forum(2)
        general=send('m',b'Command:')
        assert b'Active messages:  0' in general
        forum(4)
        assert b'PERSISTENT TEST AREA CONTENT' in readmsg()
        result['posting_readback_and_forum_separation']=True
        send('C',b'A>')
        login('TEST ONE','TRIAL1',True)
        send('C',b'A>')
        login('TEST TWO','TRIAL2',True)
        send('C',b'A>')
        login('SYSOP',password)
        forum(1)
        post('PRIVATE TEST','PRIVATE FOR TEST ONE',to='TEST ONE')
        send('C',b'A>')
        login('TEST ONE','TRIAL1')
        assert b'PRIVATE FOR TEST ONE' in readmsg()
        send('C',b'A>')
        login('TEST TWO','TRIAL2')
        _,personal=forum(1)
        assert b'PRIVATE FOR TEST ONE' not in personal
        send('R',b'Message Number:')
        private=send('1',b'Command:')
        assert b'PRIVATE FOR TEST ONE' not in private
        result['registration_and_private_mail_visibility']=True
        forum(4)
        assert b'PERSISTENT TEST AREA CONTENT' in readmsg()
        send('C',b'A>')
        result['account_and_message_persistence']=True
        maintenance=send('I:RBUTIL41',b'Choice:')
        assert all(x in maintenance for x in (b'MESSAGES',b'FORUMS',b'USERS',b'RESET DATABASE'))
        send('9',b'A>')
        result['maintenance_utility_starts']=True
    finally:
        guest.close()
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('instance','stock','tools','board','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    for name in ('instance','stock','tools','board','output'):setattr(a,name,getattr(a,name).resolve())
    check(a)
