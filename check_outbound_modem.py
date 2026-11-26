#!/usr/bin/env python3
"""Run a disposable CP/M outbound dial probe against a loopback fixture only."""
import argparse
import json
import os
from pathlib import Path
import pty
import shutil
import socket
import subprocess
import tempfile
import tty

from check_modem_runtime import free_port, stop
from check_rcpm_transport import wait_for_terminal


def run(source, runtime, cpmcp, tcpser):
    with tempfile.TemporaryDirectory(prefix='rcpm-outbound-') as temporary, socket.socket() as hub:
        root = Path(temporary)
        (root / 'disks').mkdir()
        (root / 'conf').mkdir()
        for kind in ('server', 'client'):
            (root / f'conf/net_{kind}.conf').write_text('# No legacy network devices.\n')
        disk = root / 'disks/drivea.dsk'
        shutil.copyfile(source / 'cpmsim/disks/library/cpm3-1.dsk', disk)
        tool_env = dict(os.environ, DISKDEFS=str(cpmcp.with_name('diskdefs')))
        subprocess.run([str(cpmcp.with_name('cpmrm')), '-T', 'raw', '-f', 'ibm-3740',
                        str(disk), '0:PROFILE.SUB'], check=True, env=tool_env)
        shutil.copyfile(Path(__file__).parent / 'guest/dialprobe.asm', root / 'dialprobe.asm')
        subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'dialprobe.asm'],
                       cwd=root, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(cpmcp), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                        str(root / 'dialprobe.bin'), '0:DIALPRB.COM'], check=True, env=tool_env)
        hub.bind(('127.0.0.1', 0))
        hub.listen(1)
        hub.settimeout(30)
        modem_port, caller_port = free_port(), free_port()
        master, slave = pty.openpty()
        tty.setraw(slave)
        modem = guest = None
        with tempfile.TemporaryFile() as log:
            try:
                modem = subprocess.Popen([str(tcpser), '-v', f'127.0.0.1:{modem_port}',
                    '-p', f'127.0.0.1:{caller_port}', '-s', '38400', '-i', 'e0v1&c1&d2', '-l', '0'],
                    stdout=log, stderr=log)
                guest = subprocess.Popen([str(runtime), '-f', '4'], cwd=root,
                    env=dict(os.environ, RCPM_MODEM='ip232', RCPM_MODEM_HOST='127.0.0.1',
                             RCPM_MODEM_PORT=str(modem_port)), stdin=slave, stdout=slave, stderr=slave)
                wait_for_terminal(master, b'A>')
                os.write(master, f'DIALPRB 127.0.0.1:{hub.getsockname()[1]}\r'.encode())
                peer, _ = hub.accept()
                with peer:
                    peer.settimeout(20)
                    wait_for_terminal(master, b'OUTBOUND CARRIER ON')
                    payload = bytes(range(256)) * 4
                    peer.sendall(payload)
                    received = bytearray()
                    while len(received) < len(payload):
                        block = peer.recv(len(payload) - len(received))
                        if not block:
                            raise RuntimeError('Outbound connection closed during echo')
                        received.extend(block)
                    if bytes(received) != payload:
                        raise RuntimeError('Outbound binary echo mismatch')
                    peer.sendall(b'Q')
                    if peer.recv(1) != b'':
                        raise RuntimeError('DTR did not hang up')
                # One read can contain both PASS and the prompt; only require PASS
                # then issue a fresh local command to establish CP/M control.
                wait_for_terminal(master, b'OUTBOUND PASS')
                os.write(master, b'\r')
                wait_for_terminal(master, b'A>')
                result = dict(loopback_only=True, guest_ATD=True, binary_echo_bytes=1024,
                              dtr_hangup=True, returned_to_CPM=True, cpu_mhz=4)
                print(json.dumps(result))
                return result
            finally:
                if guest:
                    stop(guest)
                if modem:
                    stop(modem)
                os.close(master)
                os.close(slave)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'runtime', 'cpmcp', 'tcpser'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    run(a.source.resolve(), a.runtime.resolve(), a.cpmcp.resolve(), a.tcpser.resolve())
