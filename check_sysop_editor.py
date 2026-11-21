#!/usr/bin/env python3
"""Verify private ANSI editing and save on disposable A/I images."""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import shutil
import socket
import subprocess
import time
import tty
from check_modem_runtime import free_port, stop


def run(release, root, mode='direct', tcpser=None):
    if root.exists():raise FileExistsError(root)
    repo=Path(__file__).resolve().parent
    (root/'disks').mkdir(parents=True);(root/'conf').mkdir()
    for d in 'ai':shutil.copyfile(release/f'disks/drive{d}.dsk',root/f'disks/drive{d}.dsk')
    # Put the backup in the earlier directory slot. The original BYE
    # WELCOME.??? FCB otherwise opens this stale banner instead of TXT.
    tools=repo/'build/cpmtools/bin';a=root/'disks/drivea.dsk';welcome=root/'welcome-original'
    subprocess.run([str(tools/'cpmcp'),'-f','ibm-3740',str(a),'0:WELCOME.TXT',str(welcome)],check=True)
    current=welcome.read_bytes()
    subprocess.run([str(tools/'cpmrm'),'-f','ibm-3740',str(a),'0:WELCOME.TXT'],check=True)
    welcome.write_bytes(b'WELCOME-STALE-BACKUP\r\n\x1a')
    subprocess.run([str(tools/'cpmcp'),'-f','ibm-3740',str(a),str(welcome),'0:WELCOME.BAK'],check=True)
    welcome.write_bytes(b'WELCOME-CURRENT-TEXT\r\n'+current)
    subprocess.run([str(tools/'cpmcp'),'-f','ibm-3740',str(a),str(welcome),'0:WELCOME.TXT'],check=True)
    for k in ('server','client'):(root/f'conf/net_{k}.conf').write_text('# disposable editor test\n')
    m,s=pty.openpty();tty.setraw(s);port=free_port();public=port
    modem=None;modem_log=None
    if mode=='ip232':
        if tcpser is None:raise ValueError('tcpser is required for ip232')
        manifest=json.loads((release/'trial-build.json').read_text())
        tools=repo/'build/cpmtools/bin';a=root/'disks/drivea.dsk'
        for user,name in ((0,'BYE.COM'),(0,'BYEDRIV.COM'),(15,'BYE.COM')):
            subprocess.run([str(tools/'cpmrm'),'-f','ibm-3740',str(a),f'{user}:{name}'],check=True)
            subprocess.run([str(tools/'cpmcp'),'-f','ibm-3740',str(a),str(Path(manifest['builds'])/'ip232'/name),f'{user}:{name}'],check=True)
        public=free_port();modem_log=(root/'tcpser.log').open('wb')
        modem=subprocess.Popen([str(tcpser),'-v',f'127.0.0.1:{port}','-p',f'127.0.0.1:{public}',
                                '-s','2400','-S','2400','-i','&c1&d2','-l','0'],
                               stdout=modem_log,stderr=modem_log,restore_signals=False)
    p=subprocess.Popen([str(release/'runtime/cpmsim'),'-f','4'],cwd=root,
        env=dict(os.environ,RCPM_MODEM=mode,RCPM_MODEM_HOST='127.0.0.1',RCPM_MODEM_PORT=str(port)),
        stdin=s,stdout=s,stderr=s)
    local=bytearray();remote=bytearray();caller=None
    def collect(t):
        end=time.monotonic()+t
        while time.monotonic()<end:
            for fd in select.select([m]+([caller] if caller else []),[],[],.02)[0]:
                if fd==m:local.extend(os.read(m,8192))
                else:remote.extend(caller.recv(8192))
    def wait(mark,buf,start=0):
        end=time.monotonic()+40
        while mark not in buf[start:]:
            if time.monotonic()>end:raise RuntimeError('Editor test timed out: '+repr(buf[-600:]))
            collect(.1)
    def type_local(data):
        for x in data:os.write(m,bytes([x]));collect(.08)
    try:
        wait(b'RCP/M modem ready.' if mode=='direct' else b'ATE0Q0V0S0=0M0S10=25X1H0',local)
        if mode=='ip232':collect(3)
        caller=socket.create_connection(('127.0.0.1',public))
        for _ in range(30):
            caller.sendall(b'\r');collect(.5)
            if b'A0:SYSTEM>' in remote:break
        wait(b'A0:SYSTEM>',remote);collect(1)
        if b'WELCOME-CURRENT-TEXT' not in remote or b'WELCOME-STALE-BACKUP' in remote:
            raise AssertionError('BYE selected the backup banner instead of WELCOME.TXT')
        caller.sendall(b'SYSUTLS:ZDE\r');wait(b'Directory access denied.',remote)
        os.write(m,b'\x02');wait(b'[Remote off]',local)
        private_start=len(remote)
        start=len(local);type_local(b'SYSUTLS:ZDE A0:WELCOME.TXT\r');collect(2)
        if b'\x1b[' not in local[start:]:raise AssertionError('ANSI screen controls missing')
        if local[start:].count(12)>10:raise AssertionError('Generic terminal profile still active')
        # ^Q is ZDE's quick-command prefix, ^N inserts a line, ^G deletes
        # a character, ^O starts format commands. None may become BYE keys.
        type_local(b'\x11R')
        type_local(b'EDITOR-SAVE-OK\r')
        type_local(b'\x11R\x0e')
        type_local(b'X\x11S\x07')
        type_local(b'\x0fA\x0fA')
        type_local(b'\x0bS');collect(1)
        type_local(b'\x0bX');collect(.5)
        if b'Unchanged; save? (Y/N):' in local[start:]:
            type_local(b'N')  # ^KS already saved; no second save is needed.
        wait(b'A0:SYSTEM>',local,start)
        if b'Message from Sysop:' in local[start:]:raise AssertionError('BYE intercepted editor ^Q')
        if b'RCP/M modem ready.' in local[start:]:raise AssertionError('Editor ^N disconnected caller')
        if len(remote)!=private_start:raise AssertionError('Private editing leaked output to caller')
        # The blank toggle and the historic shared-mode message key survive.
        start=len(local);os.write(m,b'\x02');wait(b'[Remote on]',local,start)
        start=len(local);os.write(m,b'\x11');wait(b'Message from Sysop:',local,start)
        os.write(m,b'\x18');collect(.5)
    finally:
        if caller:caller.close()
        stop(p);os.close(m);os.close(s);(root/'editor.log').write_bytes(local)
        if modem:stop(modem)
        if modem_log:modem_log.close()
    out=root/'edited.txt'
    subprocess.run([str(repo/'build/cpmtools/bin/cpmcp'),'-f','ibm-3740',str(root/'disks/drivea.dsk'),'0:WELCOME.TXT',str(out)],check=True)
    if b'EDITOR-SAVE-OK' not in out.read_bytes():raise AssertionError('Saved text missing')
    (root/'result.json').write_text(json.dumps(dict(local_edit_save=True,ansi=True,caller_denied=True,
        quick_keys_reach_editor=True,boot_disk_save=True,private_output_hidden=True,
        blank_toggle_preserved=True,shared_message_key_preserved=True,mode=mode,
        welcome_txt_preferred_over_backup=True))+'\n')
    print('PASS: private editor control keys and A: save; blanking and shared BYE message controls preserved')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--release',type=Path,default=Path('build/caller-tools-final'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--mode',choices=('direct','ip232'),default='direct')
    p.add_argument('--tcpser',type=Path)
    a=p.parse_args();run(a.release.resolve(),a.output.resolve(),a.mode,a.tcpser.resolve() if a.tcpser else None)
