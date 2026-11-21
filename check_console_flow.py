#!/usr/bin/env python3
"""Reproduce caller XOFF, local BYE message entry/exit, and caller XON."""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import socket
import subprocess
import time
import tty

from check_modem_runtime import free_port, stop
from prepare_shared_trial import create


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--romwbw', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    p.add_argument('--builds', type=Path, default=Path('build/bye5'))
    args = p.parse_args()
    repo, root = Path(__file__).resolve().parent, args.output.resolve()
    tools = repo / 'build/cpmtools/bin'
    create(args.source.resolve(), args.romwbw.resolve(), args.runtime.resolve(),
           args.builds.resolve(), tools, root)
    fixture = root / 'FLOW.TXT'
    fixture.write_bytes(b'FLOW-START\r\n' + b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789\r\n' * 120 + b'FLOW-END\r\n\x1a')
    j = root / 'disks/drivej.dsk'
    j.chmod(0o600)
    subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd', str(j), str(fixture), '0:FLOW.TXT'], check=True)
    j.chmod(0o444)
    master, slave = pty.openpty()
    tty.setraw(slave)
    port = free_port()
    env = dict(os.environ, RCPM_MODEM='direct', RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port))
    guest = subprocess.Popen([str(root / 'runtime/cpmsim'), '-f', '4'], cwd=root, env=env,
                             stdin=slave, stdout=slave, stderr=slave)
    caller = None
    local, remote = bytearray(), bytearray()
    with (root / 'flow.log').open('wb') as log:
        def collect(duration):
            end = time.monotonic() + duration
            while time.monotonic() < end:
                ready = select.select([master] + ([caller] if caller else []), [], [], .02)[0]
                if master in ready:
                    data = os.read(master, 8192)
                    local.extend(data)
                    log.write(data)
                    log.flush()
                if caller and caller in ready:
                    data = caller.recv(8192)
                    if not data:
                        raise RuntimeError('Unexpected disconnect')
                    remote.extend(data)
        def wait(marker, stream, start=0, timeout=45):
            until = time.monotonic() + timeout
            while marker not in stream[start:]:
                if time.monotonic() > until:
                    raise RuntimeError('Waiting for ' + repr(marker) + '; see flow.log')
                collect(.05)
        try:
            wait(b'RCP/M modem ready.', local)
            caller = socket.create_connection(('127.0.0.1', port))
            until = time.monotonic() + 20
            while b'A0:SYSTEM>' not in remote:
                if time.monotonic() > until:
                    raise RuntimeError('Login timeout')
                caller.sendall(b'\r')
                collect(.5)
            caller.sendall(b'TYPE J:FLOW.TXT [NO PAGE]\r')
            wait(b'FLOW-START', remote)
            caller.sendall(b'\x13')
            collect(.5)
            if b'FLOW-END' in remote:
                raise AssertionError('The fixture finished before XOFF; pause not reproduced')
            end = len(remote)
            collect(.5)
            if len(remote) != end:
                raise AssertionError('Caller XOFF did not stop output')
            start = len(local)
            os.write(master, b'a\r')
            collect(.4)
            beeps = local[start:].count(7)
            start = len(local)
            os.write(master, b'\x11')
            wait(b'Message from Sysop:', local, start)
            start = len(local)
            for char in b'FLOW-CHAT\r':
                os.write(master, bytes((char,)))
                collect(.1)
            wait(b'FLOW-CHAT', local, start)
            os.write(master, b'\x18')
            collect(.5)
            still_paused = b'FLOW-END' not in remote
            start = len(local)
            os.write(master, b'b\r')
            collect(.4)
            exit_beeps = local[start:].count(7)
            caller.sendall(b'\x11')
            wait(b'FLOW-END', remote)
            wait(b'A0:SYSTEM>', remote, end)
            result = dict(caller_xoff=True, local_regular_key_beeps=beeps,
                          local_key_beeps_after_message_exit=exit_beeps,
                          local_message_entry=True, message_exit_preserves_pause=still_paused,
                          caller_xon_resumes=True)
            (root / 'flow-result.json').write_text(json.dumps(result, indent=2) + '\n')
            print('PASS:', json.dumps(result))
        finally:
            if caller:
                caller.close()
            stop(guest)
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    main()
