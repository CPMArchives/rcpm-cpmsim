#!/usr/bin/env python3
"""Exercise CHAT46 with an actual local console and remote TCP caller."""
import argparse
import json
import os
from pathlib import Path
import re
import select
import shutil
import socket
import subprocess
import time
from build_rbbs41 import Machine


def screen(data):
    """Interpret the small VT100 subset used by CHAT for screen assertions."""
    cells=[[' ']*80 for _ in range(24)]
    row=col=0
    i=0
    while i<len(data):
        if data[i:i+2]==b'\x1b[':
            m=re.match(rb'\x1b\[([0-9;]*)([A-Za-z])',data[i:])
            if not m:break
            args=[int(n) if n else 0 for n in m[1].split(b';')]
            if m[2]==b'H':
                row=max(0,min(23,(args[0] or 1)-1))
                col=max(0,min(79,((args[1] if len(args)>1 else 1) or 1)-1))
            elif m[2]==b'J' and args[0]==2:cells=[[' ']*80 for _ in range(24)]
            elif m[2]==b'K' and args[0]==2:cells[row]=[' ']*80
            i+=len(m[0]);continue
        ch=data[i];i+=1
        if ch==13:col=0
        elif ch==10:
            row+=1
            if row==24:cells.pop(0);cells.append([' ']*80);row=23
        elif ch==8:col=max(0,col-1)
        elif 32<=ch<127:
            cells[row][col]=chr(ch);col+=1
            if col==80:col=0;row=min(23,row+1)
    return [''.join(line) for line in cells]


def check(a, installed=None):
    root = a.output
    root.mkdir(parents=True, exist_ok=False)
    if installed is None:
        for name in ('conf', 'runtime', 'drivers'):
            shutil.copytree(a.instance/name, root/name)
        (root/'disks').mkdir()
        for drive in 'aijp':
            shutil.copyfile(a.instance/f'disks/drive{drive}.dsk', root/f'disks/drive{drive}.dsk')
        def tool(name, *args):
            # Reuse already approved host executables; only media is disposable.
            command = [str(a.instance/'runtime'/name), *map(str,args)]
            result = subprocess.run(command, capture_output=True)
            if result.returncode:
                raise RuntimeError(name+': '+result.stderr.decode(errors='replace').strip())
            return result
        image = root/'disks/drivea.dsk'
        # A previously installed instance already contains CHAT. Replace it only
        # on this disposable copy, just as the stopped-media installer does.
        tool('cpmrm', '-f', 'ibm-3740', image, '0:CHAT.COM')
        tool('cpmcp', '-f', 'ibm-3740', image, a.chat, '0:CHAT.COM')
        tool('cpmchattr', '-f', 'ibm-3740', image, '4', '0:CHAT.COM')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',0))
            port = probe.getsockname()[1]
        guest = Machine(root,a.instance/'runtime/cpmsim',root/'local.log',
            dict(RCPM_MODEM='direct', RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port)),speed='4')
    else:
        port = 4000
        guest = installed(root / "operator")
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
            # Direct transport needs an initial character; the installed
            # tcpser/IP232 path answers through Hayes carrier negotiation.
            if installed is None:
                send(b'\r')
            collect(.3)
    def page():
        start=len(local)
        command('CHAT',b'Ringing:')
        collect(.2)
        assert 7 in local[start:], 'No local page bell'
    def answer():
        start=len(remote)
        send(b'\x1b',True)
        wait(b'CHAT CONNECTED',remote,start)
        wait(b'CALLER',remote,start)
    def pane_text(value,who,stream=remote,timeout=15):
        end=time.monotonic()+timeout
        while True:
            lines=screen(bytes(stream))
            pane=lines[3:11] if who=='sysop' else lines[13:21]
            if value in '\n'.join(pane):return lines
            if time.monotonic()>end:raise RuntimeError('Pane text missing: '+value+'\n'+'\n'.join(lines))
            collect()
    try:
        if installed is None:
            wait(b'RCP/M modem ready.',local)
        login()
        page();answer()
        result['page_local_bell_and_local_escape_answer']=True
        startl,startr=len(local),len(remote)
        send(b'CALLER TO SYSOP\r')
        pane_text('CALLER TO SYSOP','caller',local)
        pane_text('CALLER TO SYSOP','caller')
        startl,startr=len(local),len(remote)
        send(b'SYSOP TO CALLER\r',True)
        pane_text('SYSOP TO CALLER','sysop',local)
        pane_text('SYSOP TO CALLER','sysop')
        result['two_way_text_visible_on_both_consoles']=True
        for stream in (local,remote):
            lines=screen(bytes(stream))
            assert 'CALLER TO SYSOP' not in '\n'.join(lines[3:11])
            assert 'SYSOP TO CALLER' not in '\n'.join(lines[13:21])
        result['separate_sysop_and_caller_panes']=True
        # Queue both sources together rather than waiting for either echo.
        caller.sendall(b'REMOTE AT ONCE\r')
        os.write(guest.master,b'LOCAL AT ONCE\r')
        pane_text('REMOTE AT ONCE','caller')
        pane_text('LOCAL AT ONCE','sysop')
        send(b'\x12')
        pane_text('LOCAL AT ONCE','sysop')
        send(b'A\tB\r')
        pane_text('A       B','caller')
        result['concurrent_input_redraw_and_tab']=True
        send(b'FIXZ\x08!\r')
        pane_text('FIX!','caller')
        # More than a paneful scrolls only the originating participant.
        for n in range(12):send(('REMOTE LINE %02d\r'%n).encode())
        lines=pane_text('REMOTE LINE 11','caller')
        assert 'REMOTE LINE 00' not in '\n'.join(lines[13:21])
        assert 'SYSOP TO CALLER' in '\n'.join(lines[3:11])
        send(b'W'*80+b'\r',True)
        pane_text('W'*76,'sysop')
        pane_text('W'*4,'sysop')
        result['backspace_wrap_and_independent_scrolling']=True
        start=len(remote);send(b'\x18');wait(b'A0:SYSTEM>',remote,start)
        result['caller_ctrl_x_returns_to_cpm']=True
        page();answer()
        start=len(remote);send(b'\x18',True);wait(b'A0:SYSTEM>',remote,start)
        result['sysop_ctrl_x_returns_to_cpm']=True
        page()
        start=len(remote);send(b'\x03');wait(b'A0:SYSTEM>',remote,start)
        result['caller_ctrl_c_cancels_page']=True
        start=time.monotonic();command('CHAT',b'Ringing:')
        wait(b'The sysop is not available',remote,len(remote),timeout=45)
        wait(b'A0:SYSTEM>',remote,len(remote)-1000)
        elapsed=time.monotonic()-start
        assert 5 < elapsed < 45, elapsed
        result['unanswered_page_seconds']=round(elapsed,2)
        # Honor the existing local ^G page-availability toggle.
        send(b'\x07',True)
        text=command('CHAT')
        assert b'The sysop is not available' in text and b'Ringing:' not in text
        result['bye_bell_disabled_rejects_paging']=True
        send(b'\x07',True)
        command('WORK:',b'I0:WORK>')
        command('CHAT',b'Ringing:');answer()
        start=len(remote);send(b'\x18');wait(b'I0:WORK>',remote,start)
        result['chat_on_path_and_preserves_work_directory']=True
        command('A0:',b'A0:SYSTEM>')
        start=len(remote)
        command('CHAT /S',b'Ringing:')
        send(b'\x1b',True);wait(b'CHAT CONNECTED',remote,start)
        send(b'SCROLLING FALLBACK\r')
        wait(b'SCROLLING FALLBACK',remote,start)
        assert b'\x1b[2J' not in remote[start:]
        end=len(remote);send(b'\x18');wait(b'A0:SYSTEM>',remote,end)
        result['scrolling_fallback']=True
        page();answer()
        start=len(remote)
        send(b'\x02',True)
        wait(b'Returning to CP/M.',local,len(local)-500)
        collect(.2)
        assert b'Returning to CP/M.' not in remote[start:]
        send(b'\x02',True)
        collect(.1)
        # The returned private prompt is in I13; restore caller A0 explicitly.
        send(b'A0:\r',True)
        wait(b'A0:SYSTEM>',remote,len(remote)-500)
        result['private_blank_ends_chat_without_remote_private_output']=True
        page();answer()
        caller.close();caller=None
        wait(b'RCP/M modem ready.' if installed is None else b'ATE0Q0V0S0=0M0S10=25X1H0',local,len(local),timeout=30)
        login()
        result['carrier_loss_in_conversation_and_reconnect']=True
        page()
        caller.close();caller=None
        wait(b'RCP/M modem ready.' if installed is None else b'ATE0Q0V0S0=0M0S10=25X1H0',local,len(local),timeout=30)
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
