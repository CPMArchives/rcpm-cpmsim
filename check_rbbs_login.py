#!/usr/bin/env python3
"""Check local SYSOP input/validation on a new disposable upper-area system."""
import argparse
import json
import os
from pathlib import Path
import pty
import select
import socket
import time
import subprocess
import tty
from unittest.mock import patch
import rbbs_sysop_login

from check_modem_runtime import free_port, stop
from prepare_shared_trial import create
from prepare_rbbs_trial import install
from prepare_system_trial import upper_layout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--romwbw', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--chat', action='store_true', help='Also check BYE live sysop message exit')
    args = p.parse_args()
    repo = Path(__file__).resolve().parent
    root = args.output.resolve()
    tools = repo / 'build/cpmtools/bin'
    create(args.source.resolve(), args.romwbw.resolve(), repo / 'build/modem/cpmsim',
           repo / 'build/bye5', tools, root)
    install(root, repo / 'build/rbbs37/original', tools, args.romwbw.resolve())
    upper_layout(root, tools, args.romwbw.resolve(), repo / 'build/ppip18')
    secrets = json.loads((root / 'rbbs-trial-passwords.json').read_text())
    master, slave = pty.openpty()
    tty.setraw(slave)
    port = free_port()
    env = dict(os.environ, RCPM_MODEM='direct', RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port))
    guest = subprocess.Popen([str(root / 'runtime/cpmsim'), '-f', '4'], cwd=root, env=env,
                             stdin=slave, stdout=slave, stderr=slave)
    caller = None
    with (root / 'sysop-check.log').open('wb') as log:
        captured = bytearray()
        def read(markers, kick=False, timeout=30):
            data = bytearray()
            end, next_return = time.monotonic() + timeout, 0
            while time.monotonic() < end:
                if kick and time.monotonic() >= next_return:
                    caller.sendall(b'\r')
                    next_return = time.monotonic() + .5
                ready = select.select([master] + ([caller] if caller else []), [], [], .05)[0]
                if caller and caller in ready:
                    caller.recv(8192)
                if master in ready:
                    block = os.read(master, 8192)
                    log.write(block)
                    log.flush()
                    captured.extend(block)
                    data.extend(block)
                    if any(marker in data for marker in markers):
                        time.sleep(.2)
                        return bytes(data)
            raise RuntimeError('Prompt timeout; see the disposable sysop-check.log')
        def send(value, markers, delay=.1):
            for byte in value.encode() + b'\r':
                os.write(master, bytes((byte,)))
                if delay:
                    time.sleep(delay)
            return read(markers)
        prompt = (b'A0:SYSTEM>',)
        first = (b'FIRST Name:',)
        last = (b'LAST Name:',)
        command = (b'?  Your Command:',)
        try:
            read((b'RCP/M modem ready.',))
            caller = socket.create_connection(('127.0.0.1', port))
            read(prompt, kick=True)
            os.write(master, b'\x02')
            read(prompt)
            send('SYSUTLS:RBBS', first)
            send('SYSOP', last)
            result = send(secrets['rbbs_sysop'], command + first, delay=0)
            burst_ok = b'?  Your Command:' in result
            if burst_ok:
                raise AssertionError('Burst no longer reproduces the input-loss issue; reassess the workaround')
            # Exercise the actual helper against this guest. Only the tmux
            # transport is substituted, because workspace policy prevents
            # access to host tmux sockets. Capture and typing reach the PTY.
            sends = []
            def tmux_run(argv, **kwargs):
                operation = argv[1]
                if operation == 'list-panes':
                    output = '%99\tcpmsim\t' + str(root) + '\n'
                elif operation == 'capture-pane':
                    while select.select([master], [], [], 0)[0]:
                        block = os.read(master, 8192)
                        captured.extend(block)
                        log.write(block)
                        log.flush()
                    if caller and select.select([caller], [], [], 0)[0]:
                        caller.recv(8192)
                    # tmux captures rendered text, not bell/CR control bytes.
                    output = captured.decode(errors='replace').replace('\x07', '').replace('\r', '')
                elif operation == 'send-keys':
                    sends.append(argv)
                    value = argv[-1].encode() if '-l' in argv else b'\r'
                    os.write(master, value)
                    output = ''
                else:
                    raise AssertionError('Unexpected tmux operation')
                return subprocess.CompletedProcess(argv, 0, output, '')
            with patch.object(rbbs_sysop_login.shutil, 'which', return_value='test-tmux'), \
                    patch.object(rbbs_sysop_login.subprocess, 'run', side_effect=tmux_run):
                try:
                    rbbs_sysop_login.login(root, pane='%100')
                except RuntimeError:
                    pass
                else:
                    raise AssertionError('Helper accepted an unrelated pane')
                if sends:
                    raise AssertionError('Refused pane received keystrokes')
                rbbs_sysop_login.login(root)
            if args.chat:
                os.write(master, b'\x11')
                read((b'Message from Sysop:',))
                send('CHAT-EXIT-CHECK', (b'CHAT-EXIT-CHECK',))
                os.write(master, b'\x18')
                read(command)
            send('P', (b"User's FIRST Name:",))
            send('', command)
            send('J', prompt)
            (root / 'login-result.json').write_text(json.dumps(dict(
                burst_login=burst_ok, paced_sysop_login=True,
                paced_helper=True, pane_selection_refusal=True,
                private_user_management=True, sysop_J=True), indent=2) + '\n')
            print('PASS: paced local SYSOP login and private P menu; burst login:', burst_ok)
        finally:
            if caller:
                caller.close()
            stop(guest)
            os.close(master)
            os.close(slave)


if __name__ == '__main__':
    main()
