#!/usr/bin/env python3
"""Exercise CHAT46 with an actual local console and remote TCP caller."""
import argparse
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import time
from build_rbbs41 import Machine


def check(a):
    root = a.output
    root.mkdir(parents=True, exist_ok=False)
    for name in ('conf', 'runtime', 'drivers'):
        shutil.copytree(a.instance/name, root/name)
    (root/'disks').mkdir()
    for drive in 'aijp':
        shutil.copyfile(a.instance/f'disks/drive{drive}.dsk', root/f'disks/drive{drive}.dsk')
    def tool(name, *args):
        return subprocess.run([str(root/'runtime'/name), *map(str,args)], check=True, capture_output=True)
    image = root/'disks/drivea.dsk'
    tool('cpmcp', '-f', 'ibm-3740', image, a.chat, '0:CHAT.COM')
    tool('cpmchattr', '-f', 'ibm-3740', image, '4', '0:CHAT.COM')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0))
        port = probe.getsockname()[1]
    guest = Machine(root,root/'runtime/cpmsim',root/'local.log',
        dict(RCPM_MODEM='direct', RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port)),speed='4')
    caller = None
    local, remote = bytearray(), bytearray()
    result = {}
    remote_log = open(root/'caller.log','wb')
    def collect(duration=.05):
        end = time.monotonic()+duration
        while time.monotonic()<end:
            ready = select.select([guest.master]+([caller] if caller else []),[],[],.02)[0]
            if guest.master in ready:
                part=os.read(guest.master,65536)
                local.extend(part);guest.log.write(part);guest.log.flush()
            if caller and caller in ready:
                part=caller.recv(65536)
                if not part: raise RuntimeError('Unexpected caller disconnect')
                remote.extend(part);remote_log.write(part);remote_log.flush()
    def wait(marker, stream, start=0, timeout=45):
        end = time.monotonic()+timeout
        while marker not in stream[start:]:
            if time.monotonic()>end:
                raise RuntimeError('Waiting for %r: %r'%(marker,stream[start:][-2000:]))
            collect()
        return bytes(stream[start:])
    def send(value, local_input=False):
        for byte in value:
            if local_input: os.write(guest.master,bytes([byte]))
            else: caller.sendall(bytes([byte]))
            collect(.025)
    def command(value, marker=b'A0:SYSTEM>'):
        start=len(remote)
        send(value.encode()+b'\r')
        return wait(marker,remote,start)
    def login():
        nonlocal caller
        caller=socket.create_connection(('127.0.0.1',port),timeout=5)
        start=len(remote)
        end=time.monotonic()+25
        while b'A0:SYSTEM>' not in remote[start:]:
            if time.monotonic()>end:raise RuntimeError('Login timeout')
            send(b'\r');collect(.3)
    def page():
        start=len(local)
        command('CHAT',b'Ringing:')
        collect(.2)
        assert 7 in local[start:], 'No local page bell'
    def answer():
        start=len(remote)
        send(b'\x1b',True)
        wait(b'Operator is available',remote,start)
    try:
        wait(b'RCP/M modem ready.',local)
        login()
        page();answer()
        result['page_local_bell_and_local_escape_answer']=True
        startl,startr=len(local),len(remote)
        send(b'CALLER TO SYSOP\r')
        wait(b'CALLER TO SYSOP',local,startl)
        wait(b'CALLER TO SYSOP',remote,startr)
        startl,startr=len(local),len(remote)
        send(b'SYSOP TO CALLER\r',True)
        wait(b'SYSOP TO CALLER',local,startl)
        wait(b'SYSOP TO CALLER',remote,startr)
        result['two_way_text_visible_on_both_consoles']=True
        start=len(remote);send(b'\x18');wait(b'A0:SYSTEM>',remote,start)
        result['caller_ctrl_x_returns_to_cpm']=True
        page();answer()
        start=len(remote);send(b'\x18',True);wait(b'A0:SYSTEM>',remote,start)
        result['sysop_ctrl_x_returns_to_cpm']=True
        page()
        start=len(remote);send(b'\x03');wait(b'A0:SYSTEM>',remote,start)
        result['caller_ctrl_c_cancels_page']=True
        start=time.monotonic();command('CHAT',b'Ringing:')
        wait(b'operator is not available',remote,len(remote),timeout=45)
        wait(b'A0:SYSTEM>',remote,len(remote)-1000)
        elapsed=time.monotonic()-start
        assert 5 < elapsed < 45, elapsed
        result['unanswered_page_seconds']=round(elapsed,2)
        # Honor the existing local ^G page-availability toggle.
        send(b'\x07',True)
        text=command('CHAT')
        assert b'operator is not available' in text and b'Ringing:' not in text
        result['bye_bell_disabled_rejects_paging']=True
        send(b'\x07',True)
        command('WORK:',b'I0:WORK>')
        command('CHAT',b'Ringing:');answer()
        start=len(remote);send(b'\x18');wait(b'I0:WORK>',remote,start)
        result['chat_on_path_and_preserves_work_directory']=True
        command('A0:',b'A0:SYSTEM>')
        page();answer()
        caller.close();caller=None
        wait(b'RCP/M modem ready.',local,len(local),timeout=20)
        login()
        result['carrier_loss_in_conversation_and_reconnect']=True
        page()
        caller.close();caller=None
        wait(b'RCP/M modem ready.',local,len(local),timeout=20)
        login()
        result['carrier_loss_during_paging_and_reconnect']=True
    finally:
        if caller:caller.close()
        guest.close();remote_log.close()
        (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('instance','chat','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    check(argparse.Namespace(**{k:v.resolve() for k,v in vars(a).items()}))
