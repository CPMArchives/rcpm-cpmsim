#!/usr/bin/env python3
"""Exercise a disposable copy of the RBBS 4.1 installation over raw TCP."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import socket
import time

from build_rbbs41 import Machine


def check(a):
    root=a.output.resolve()
    root.mkdir(parents=True)
    for name in ('conf','runtime','disks'):
        if name=='disks':
            (root/name).mkdir()
            for drive in 'ai': shutil.copyfile(a.instance/f'disks/drive{drive}.dsk',root/f'disks/drive{drive}.dsk')
            for drive in 'jp': os.symlink(a.instance.resolve()/f'disks/drive{drive}.dsk',root/f'disks/drive{drive}.dsk')
        else: shutil.copytree(a.instance/name,root/name)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0)); port=probe.getsockname()[1]
    guest=Machine(root,root/'runtime/cpmsim',root/'local.log',
                  dict(RCPM_MODEM='direct',RCPM_MODEM_HOST='127.0.0.1',RCPM_MODEM_PORT=str(port)),speed='4')
    caller=None
    remote_log=open(root/'caller.log','wb')
    result={}
    def read(marker,timeout=25,kick=False,disconnect=False):
        data=bytearray(); end=time.monotonic()+timeout; next_kick=0
        while time.monotonic()<end:
            if kick and time.monotonic()>=next_kick:
                caller.sendall(b'\r'); next_kick=time.monotonic()+.5
            ready=select.select([guest.master,caller],[],[],.05)[0]
            if guest.master in ready:
                part=os.read(guest.master,65536); guest.log.write(part);guest.log.flush()
            if caller in ready:
                part=caller.recv(65536)
                remote_log.write(part);remote_log.flush()
                if not part:
                    if disconnect:return bytes(data)
                    raise RuntimeError('Unexpected disconnect: '+repr(data[-1000:]))
                data.extend(part)
                if marker and marker in data:return bytes(data)
        raise RuntimeError('Waiting for %r: %r'%(marker,data[-2000:]))
    def send(value,marker,key=False):
        print('Sending '+('password' if value==password else value),flush=True)
        for b in value.encode('ascii')+(b'' if key else b'\r'):
            caller.sendall(bytes([b]));time.sleep(.025)
        return read(marker)
    password=json.loads((a.instance/'TEST-CREDENTIALS.json').read_text())['sysop_password']
    try:
        guest.read(b'RCP/M modem ready.')
        caller=socket.create_connection(('127.0.0.1',port),timeout=5)
        banner=read(b'A0:SYSTEM>',kick=True)
        assert b'H U M O N G O U S' in banner
        result['welcome_banner']=True
        denied=send('A15:RBBS41',b'A0:SYSTEM>')
        assert b'Enter your name:' not in denied
        result['direct_private_entry_denied']=True
        send('WORK:',b'I0:WORK>')
        send('RBBS',b'Enter your name:')
        send('SYSOP',b'Password:')
        send(password,b'Command:')
        result['public_entry_from_work']=True
        listing=send('F',b'Forum number:',key=True)
        assert all(x in listing for x in (b'PERSONAL',b'GENERAL',b'CPM',b'TEST'))
        send('9',b'Forum number:',key=True)
        send('9',b'Forum number:',key=True)
        send('4',b'Command:',key=True)
        result['forum_selection_and_invalid_input']=True
        send('E',b'To:',key=True)
        send('',b'Subject:')
        send('TEST AREA MESSAGE',b' 1>')
        send('PERSISTENT TEST AREA CONTENT',b' 2>')
        send('.',b'Choice:')
        send('S',b'Command:',key=True)
        send('F',b'Forum number:',key=True)
        send('2',b'Command:',key=True)
        general=send('m',b'Command:',key=True)
        assert b'Active messages:  0' in general
        send('F',b'Forum number:',key=True)
        send('4',b'Command:',key=True)
        send('R',b'Message Number:',key=True)
        body=send('1',b'Command:')
        assert b'PERSISTENT TEST AREA CONTENT' in body
        result['forum_separation_and_readback']=True
        send('X',b'Command:',key=True)
        shortcut=send('R;1',b'Command:')
        assert b'PERSISTENT TEST AREA CONTENT' in shortcut
        send('X',b'Command:')
        result['single_key_menus_and_expert_command_lines']=True
        send('C',b'A0:SYSTEM>',key=True)
        denied=send('TYPE I15:USERS.CCC',b'A0:SYSTEM>')
        assert b'SYSOP' not in denied
        result['cpm_return_revokes_private_access']=True
        send('RBBS',b'Enter your name:')
        send('SYSOP',b'Password:')
        send(password,b'Command:')
        send('F',b'Forum number:',key=True)
        send('4',b'Command:',key=True)
        send('R',b'Message Number:',key=True)
        body=send('1',b'Command:')
        assert b'PERSISTENT TEST AREA CONTENT' in body
        result['message_persists_after_board_reentry']=True
        send('G',b'Confirm',key=True)
        for byte in b'Y': caller.sendall(bytes([byte]));time.sleep(.025)
        read(None,disconnect=True)
        result['g_disconnect']=True
        caller.close()
        caller=socket.create_connection(('127.0.0.1',port),timeout=5)
        read(b'A0:SYSTEM>',kick=True)
        send('RBBS',b'Enter your name:')
        caller.close();caller=None
        # BYE carrier-loss recovery must return the listener to a fresh call.
        end=time.monotonic()+10
        while time.monotonic()<end:
            if select.select([guest.master],[],[],.1)[0]:
                part=os.read(guest.master,65536);guest.log.write(part);guest.log.flush()
                if b'RCP/M modem ready.' in part:break
        caller=socket.create_connection(('127.0.0.1',port),timeout=5)
        read(b'A0:SYSTEM>',kick=True)
        result['carrier_loss_recovery']=True
        for byte in b'BYE\r': caller.sendall(bytes([byte]));time.sleep(.025)
        read(None,disconnect=True)
    finally:
        if caller:caller.close()
        guest.close();remote_log.close()
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instance',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.instance=a.instance.resolve();check(a)
