#!/usr/bin/env python3
"""On disposable release media: leave BYE, dial loopback, return to answering."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

from check_release import Guest, free_port


def run(package, probe):
    with tempfile.TemporaryDirectory(prefix='rcpm-board-dial-') as temporary, socket.socket() as hub:
        work = Path(temporary)
        root = work / 'instance'
        shutil.copytree(package, root)
        subprocess.run([str(root / 'runtime/cpmcp'), '-f', 'z80pack-hd',
                        str(root / 'disks/drivei.dsk'), str(probe), '13:DIALPRB.COM'],
                       env=dict(os.environ, DISKDEFS=str(root / 'runtime/diskdefs')), check=True)
        hub.bind(('127.0.0.1', 0))
        hub.listen(1)
        hub.settimeout(45)
        serial, caller_port = free_port(), free_port()
        with tempfile.TemporaryFile() as log:
            modem = subprocess.Popen([str(root / 'runtime/tcpser'), '-v', f'127.0.0.1:{serial}',
                '-p', f'127.0.0.1:{caller_port}', '-s', '2400', '-S', '2400',
                '-i', '&c1&d2', '-l', '0'], stdout=log, stderr=log)
            guest = None
            try:
                guest = Guest(root, work / 'guest', '--mode', 'ip232', '--port', str(serial))
                guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0\r\n0\r\n')
                guest.collect(3)
                start = len(guest.local)
                os.write(guest.master, b'\x03')
                guest.wait(b'<RET> for', start=start)
                os.write(guest.master, b'\r')
                guest.wait(b'A0:SYSTEM>', start=start)
                start = len(guest.local)
                for byte in f'SYSUTLS:DIALPRB 127.0.0.1:{hub.getsockname()[1]}\r'.encode():
                    os.write(guest.master, bytes([byte]))
                    guest.collect(.03)
                peer, _ = hub.accept()
                with peer:
                    peer.settimeout(20)
                    guest.wait(b'OUTBOUND CARRIER ON', start=start)
                    payload = bytes(range(256)) * 4
                    peer.sendall(payload)
                    received = bytearray()
                    while len(received) < len(payload):
                        block = peer.recv(len(payload) - len(received))
                        if not block:
                            raise RuntimeError('Premature outbound disconnect')
                        received.extend(block)
                    assert bytes(received) == payload
                    peer.sendall(b'Q')
                    assert peer.recv(1) == b''
                guest.wait(b'OUTBOUND PASS', start=start)
                guest.wait(b'A0:SYSTEM>', start=start)
                start = len(guest.local)
                for byte in b'BYE\r':
                    os.write(guest.master, bytes([byte]))
                    guest.collect(.05)
                guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0\r\n0\r\n', start=start)
                guest.collect(3)
                guest.connect(caller_port, kick=False)
                assert b'HELP' in guest.command('HELP').upper()
                guest.stop()
                result = dict(release_board_outbound_ATD=True, loopback_only=True,
                              binary_echo_bytes=1024, DTR_hangup=True,
                              returned_to_BYE=True, subsequent_inbound_HELP=True,
                              disposable_test_program_only=True)
                print(json.dumps(result, indent=2))
                return result
            finally:
                if guest:
                    guest.close()
                modem.terminate()
                modem.wait(timeout=5)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    p.add_argument('--probe', type=Path, required=True)
    a = p.parse_args()
    run(a.package.resolve(), a.probe.resolve())
