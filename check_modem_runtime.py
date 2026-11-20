#!/usr/bin/env python3
"""Boot disposable CP/M 3 and verify the modem device through guest IN/OUT."""
import argparse
import os
from pathlib import Path
import pty
import shutil
import socket
import subprocess
import tempfile
import tty

from check_rcpm_transport import wait_for_terminal


def free_port():
    with socket.socket() as endpoint:
        endpoint.bind(('127.0.0.1', 0))
        return endpoint.getsockname()[1]


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def run(source, runtime, cpmcp, tcpser=None):
    modes = ('direct', 'ip232') if tcpser else ('direct',)
    for mode in modes:
        with tempfile.TemporaryDirectory(prefix='rcpm-modem-guest-') as temporary:
            root = Path(temporary)
            (root / 'disks').mkdir()
            (root / 'conf').mkdir()
            for kind in ('server', 'client'):
                (root / f'conf/net_{kind}.conf').write_text('# No legacy network devices.\n')
            disk = root / 'disks/drivea.dsk'
            shutil.copyfile(source / 'cpmsim/disks/library/cpm3-1.dsk', disk)
            # Disable the stock interactive PROFILE only in this disposable copy.
            subprocess.run([str(cpmcp.with_name('cpmrm')), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), '0:PROFILE.SUB'], check=True)
            shutil.copyfile(Path(__file__).parent / 'guest/modemprobe.asm', root / 'modemprobe.asm')
            subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'modemprobe.asm'],
                           cwd=root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([str(cpmcp), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                            str(root / 'modemprobe.bin'), '0:MODEMPRB.COM'], check=True)
            port, call_port = free_port(), free_port()
            while port == call_port:
                call_port = free_port()
            modem = None
            with (root / 'tcpser.log').open('wb') as log:
                if mode == 'ip232':
                    modem = subprocess.Popen([str(tcpser), '-v', f'127.0.0.1:{port}',
                        '-p', f'127.0.0.1:{call_port}', '-i', 'e0v1&c1&d2', '-l', '4'],
                        stdout=log, stderr=log)
                master, slave = pty.openpty()
                tty.setraw(slave)
                env = dict(os.environ, RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1',
                           RCPM_MODEM_PORT=str(port))
                guest = None
                try:
                    guest = subprocess.Popen([str(runtime)], cwd=root, env=env,
                                             stdin=slave, stdout=slave, stderr=slave)
                    wait_for_terminal(master, b'A>')
                    os.write(master, b'MODEMPRB' + (b' I' if mode == 'ip232' else b'') + b'\r')
                    wait_for_terminal(master, b'MODEM PROBE READY')
                    public_port = call_port if mode == 'ip232' else port
                    for attempt in range(3):
                        with socket.create_connection(('127.0.0.1', public_port), timeout=3) as caller:
                            wait_for_terminal(master, b'CARRIER ON')
                            payload = bytes(range(256)) * 4
                            caller.sendall(payload)
                            received = bytearray()
                            while len(received) < len(payload):
                                part = caller.recv(len(payload) - len(received))
                                if not part:
                                    raise RuntimeError('Call ended during binary echo')
                                received.extend(part)
                            if received != payload:
                                raise RuntimeError(f'Guest binary echo mismatch: {bytes(received[:50])!r}')
                            if attempt == 1:
                                os.write(master, b'D' if mode == 'ip232' else b'H')
                                if caller.recv(1) != b'':
                                    raise RuntimeError('Hangup did not close the call')
                        wait_for_terminal(master, b'CARRIER OFF')
                        if guest.poll() is not None:
                            raise RuntimeError('Emulator exited with caller')
                        os.write(master, b'A')
                    os.write(master, b'Q')
                    wait_for_terminal(master, b'A>')
                    print(f'PASS {mode}: CP/M 3, three calls, 1024-byte binary echo per call, '
                          'carrier loss, local hangup, same emulator, return to CP/M', flush=True)
                except Exception:
                    if mode == 'ip232':
                        print((root / 'tcpser.log').read_text(errors='replace'))
                    raise
                finally:
                    if guest is not None:
                        stop(guest)
                    os.close(master)
                    os.close(slave)
                    if modem is not None:
                        stop(modem)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--cpmcp', type=Path, default=Path('build/cpmtools/bin/cpmcp'))
    parser.add_argument('--tcpser', type=Path)
    args = parser.parse_args()
    run(args.source.resolve(), args.runtime.resolve(), args.cpmcp.resolve(),
        args.tcpser.resolve() if args.tcpser else None)
