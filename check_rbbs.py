#!/usr/bin/env python3
"""Exercise RBBS on newly created disposable shared-machine trial images."""
import argparse
import hashlib
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
from prepare_rbbs_trial import install, references
from prepare_system_trial import upper_layout
import upper_tool_checks

MENU = b'( or ? ):'
PROMPT = b'A0:SYSTEM>'
BODY = b'PERSISTENT RBBS MESSAGE TEST'


def run(args, mode):
    root = args.output / mode
    create(args.source, args.romwbw, args.runtime, args.builds, args.cpmtools, root)
    install(root, args.cache, args.cpmtools, args.romwbw)
    if args.upper_areas:
        upper_layout(root, args.cpmtools, args.romwbw, args.ppip)
    if args.tools:
        upper_tool_checks.prepare(args, root)
    user = 15 if args.upper_areas else 2
    private = 'SYSUTLS:' if args.upper_areas else 'B:'
    # Exercise the modem-specific binary, retaining identical caller policy.
    for name in ('BYE.COM', 'BYEDRIV.COM'):
        for installed_user in ((0, user) if name == 'BYE.COM' else (0,)):
            for command in (
                [str(args.cpmtools / 'cpmrm'), '-f', 'ibm-3740', str(root / 'disks/drivea.dsk'), f'{installed_user}:{name}'],
                [str(args.cpmtools / 'cpmcp'), '-f', 'ibm-3740', str(root / 'disks/drivea.dsk'),
                 str(args.builds / mode / name), f'{installed_user}:{name}'],
            ):
                subprocess.run(command, check=True)
    port, public = free_port(), free_port()
    master, slave = pty.openpty()
    tty.setraw(slave)
    caller, guest, modem = None, None, None
    with (args.output / (mode + '.log')).open('wb') as log:
        remote_output = bytearray()
        def read(marker, kick=False, timeout=30, allow_disconnect=False):
            data = bytearray()
            disconnected = False
            end, next_kick = time.monotonic() + timeout, 0
            while time.monotonic() < end:
                if kick and time.monotonic() >= next_kick:
                    caller.sendall(b'\r')
                    next_kick = time.monotonic() + .5
                ready = select.select([master] + ([caller] if caller and not disconnected else []), [], [], .05)[0]
                if caller and caller in ready:
                    block = caller.recv(16384)
                    if block:
                        remote_output.extend(block)
                    elif not allow_disconnect:
                        raise RuntimeError('Unexpected caller disconnect')
                    else:
                        disconnected = True
                if master in ready:
                    block = os.read(master, 16384)
                    log.write(block)
                    log.flush()
                    data.extend(block)
                    if marker in data:
                        time.sleep(.15)
                        return bytes(data)
            raise RuntimeError(f'{mode}: waiting for {marker!r}: {data[-1600:]!r}')
        def send(text, marker, remote=False):
            # RBBS polls for pause/abort while printing: avoid flooding its
            # period character-at-a-time input/echo loops with typeahead.
            for byte in text.encode('ascii') + b'\r':
                if remote:
                    caller.sendall(bytes((byte,)))
                else:
                    os.write(master, bytes((byte,)))
                time.sleep(.08)
            return read(marker, timeout=90 if text.startswith('PPIP ') else 30)
        def board():
            if args.operator_entry or not args.upper_areas:
                os.write(master, b'\x02')
                read(PROMPT)
                send(private + 'RBBS', b'FIRST Name:')
                os.write(master, b'\x02')
                read(b'FIRST Name:')
            else:
                send('RBBS', b'FIRST Name:', True)
        def login(new):
            send('TRIAL', b'LAST Name:', True)
            send('CALLER', b'New User' if new else b'Enter your PASSWORD:', True)
            if new:
                send('Y', b'for your PASSWORD:', True)
                send('DEMO123', b'Now enter it again:', True)
                send('DEMO123', b'City, State:', True)
                send('TAIWAN', b'misspelled?', True)
                send('N', MENU, True)
            else:
                send('DEMO123', MENU, True)
        def connect():
            nonlocal caller
            if mode == 'ip232':
                quiet = time.monotonic()
                end = quiet + 30
                while time.monotonic() - quiet < 2:
                    if time.monotonic() > end:
                        raise RuntimeError('Modem initialization did not settle')
                    if select.select([master], [], [], .05)[0]:
                        log.write(os.read(master, 8192))
                        quiet = time.monotonic()
            caller = socket.create_connection(('127.0.0.1', port if mode == 'direct' else public), timeout=5)
            read(PROMPT, kick=mode == 'direct')
        try:
            if mode == 'ip232':
                modem = subprocess.Popen([str(args.tcpser), '-v', f'127.0.0.1:{port}',
                    '-p', f'127.0.0.1:{public}', '-s', '2400', '-S', '2400',
                    '-i', '&c1&d2', '-l', '0'], stdout=log, stderr=log, restore_signals=False)
            env = dict(os.environ, RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port))
            guest = subprocess.Popen([str(args.runtime), '-f', '4'], cwd=root, env=env,
                                     stdin=slave, stdout=slave, stderr=slave)
            read(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0')
            if mode == 'ip232':
                quiet = time.monotonic()
                deadline = quiet + 30
                while time.monotonic() - quiet < 2:
                    if time.monotonic() > deadline:
                        raise RuntimeError('Modem initialization did not settle')
                    if select.select([master], [], [], .05)[0]:
                        log.write(os.read(master, 8192))
                        quiet = time.monotonic()
            caller = socket.create_connection(('127.0.0.1', port if mode == 'direct' else public), timeout=5)
            read(PROMPT, kick=mode == 'direct')
            if args.tools:
                upper_tool_checks.exercise(send, read, master, PROMPT)
            # Default entry is now caller initiated, without wheel elevation.
            denied = send(f'A{user}:RBBS37', PROMPT, True)
            if b'Lillypond Software' in denied:
                raise AssertionError('Direct private board load bypassed the public entry')
            denied = send(private + 'RBBS', PROMPT, True)
            if b'Lillypond Software' in denied:
                raise AssertionError('Private SYSUTLS launcher became public')
            send('WORK:', b'I0:WORK>', True)
            board()
            login(True)
            send('E', b'(MM/DD|HH:MM)', True)
            send('11/19|21:00', b'To (RETURN for ALL):', True)
            send('', b'Subject:', True)
            send('RBBS integration test', b'for Private):', True)
            send('', b'1>', True)
            send(BODY.decode(), b'2>', True)
            send('', b'(S)ave:', True)
            send('S', MENU, True)
            send('J', b'SYSOP <Y or N>', True)
            send('N', PROMPT, True)
            denied = send('B:', PROMPT, True)
            if b'Directory access denied.' not in denied or b'B0>' in denied:
                raise AssertionError('Denied B: selection left a false prompt')
            denied = send(f'I{user}:', b'>', True)
            if b'Directory access denied.' not in denied or f'I{user}>'.encode() in denied:
                raise AssertionError('Caller selected private I2: or received a false prompt')
            # An explicit I: filename from user 2 must also be refused, even
            # though A2: itself holds only protected static program material.
            send(f'A{user}:', f'A{user}>'.encode(), True)
            denied = send('TYPE I:USERS', f'A{user}>'.encode(), True)
            if b'TRIAL;CALLER' in denied.upper():
                raise AssertionError('Caller read private user records after J')
            send('A0:', PROMPT, True)
            denied = send(private + 'PIP', PROMPT, True)
            if b'CP/M 3 PIP VERSION' in denied:
                raise AssertionError('BBS exit left caller privileges enabled')
            denied = send(f'A{user}:RBBS37', PROMPT, True)
            if b'Lillypond Software' in denied:
                raise AssertionError('Private BBS program became caller-loadable')
            # Reopen the board and verify the same user/message database.
            board()
            login(False)
            send('R', b'Retrieve', True)
            result = send('1', b'Retrieve', True)
            if BODY not in result:
                raise AssertionError('Saved message was not retrieved')
            send('', MENU, True)
            send('G', b'SYSOP <Y or N>', True)
            # G closes database files and invokes the actual BYE entrypoint.
            for byte in b'N\r':
                caller.sendall(bytes((byte,)))
                time.sleep(.08)
            read(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0',
                 allow_disconnect=True)
            caller.settimeout(5)
            while caller.recv(16384):
                pass
            caller.close()
            caller = None
            if BODY not in remote_output:
                raise AssertionError('Caller did not receive the retrieved message')
            # Lose carrier while the trusted board context is active. A
            # subsequent caller must receive neither its DU nor privileges.
            connect()
            board()
            login(False)
            caller.close()
            caller = None
            ready = b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0'
            read(ready)
            connect()
            denied = send(f'I{user}:', b'>', True)
            if b'Directory access denied.' not in denied or f'I{user}>'.encode() in denied:
                raise AssertionError('BBS context survived carrier loss')
            send('A0:', PROMPT, True)
            if b'CP/M 3 PIP VERSION' in send(private + 'PIP', PROMPT, True):
                raise AssertionError('Private privileges survived carrier loss')
            for byte in b'BYE\r':
                caller.sendall(bytes((byte,)))
                time.sleep(.08)
            read(ready, allow_disconnect=True)
            caller.close()
            caller = None
            # Native file extraction after all RBBS handles have closed.
            stop(guest)
            guest = None
            tools_result = upper_tool_checks.verify(args, root) if args.tools else None
            extracted = root / 'MESSAGES.check'
            subprocess.run([str(args.cpmtools / 'cpmcp'), '-f', 'z80pack-hd',
                            str(root / 'disks/drivei.dsk'), f'{user}:MESSAGES', str(extracted)], check=True)
            if BODY not in extracted.read_bytes():
                raise AssertionError(f'Message did not persist in I{user}: disk image')
            result = dict(mode=mode, bbs_user=user, upper_areas=args.upper_areas, tools=tools_result, registration=True, post=True, retrieve=True,
                          caller_entry=args.upper_areas and not args.operator_entry,
                          jump_to_cpm=True, private_reentry=True, persistent_data=True,
                          private_B_denied=True, unapproved_board_load_denied=True, rbbs_G_hangup=True,
                          private_data_denied=True, denied_selection_prompt_correct=True,
                          private_data_after_carrier_loss=True,
                          rbbs_sha256=hashlib.sha256((args.cache / 'rbbs37-1/rbbs37.com').read_bytes()).hexdigest())
            (args.output / (mode + '-result.json')).write_text(json.dumps(result, indent=2) + '\n')
            print(f'PASS {mode}: RBBS registration, post/read, I{user} persistence, J to CP/M, restrictions and call recovery', flush=True)
        finally:
            if caller:
                caller.close()
            if guest:
                stop(guest)
            if modem:
                stop(modem)
            os.close(master)
            os.close(slave)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--romwbw', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--builds', type=Path, default=Path('build/bye5'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--cache', type=Path, default=Path('build/rbbs37/original'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tcpser', type=Path)
    parser.add_argument('--upper-areas', action='store_true')
    parser.add_argument('--operator-entry', action='store_true', help='Retain the private operator-entry regression path')
    parser.add_argument('--tools', action='store_true', help='Also qualify private PPIP/path and upper-area file protection')
    parser.add_argument('--ppip', type=Path, default=Path('build/ppip18'))
    parser.add_argument('--mode', choices=('direct', 'ip232'), action='append')
    args = parser.parse_args()
    for key in ('source', 'romwbw', 'runtime', 'builds', 'cpmtools', 'cache', 'output', 'tcpser', 'ppip'):
        value = getattr(args, key)
        if value is not None:
            setattr(args, key, value.expanduser().resolve())
    modes = args.mode or (('direct', 'ip232') if args.tcpser else ('direct',))
    if args.tools and not args.upper_areas:
        parser.error('--tools requires --upper-areas')
    if 'ip232' in modes and not args.tcpser:
        parser.error('--tcpser is required for ip232')
    if args.output.exists():
        parser.error('Refusing to overwrite existing results')
    references(args.cache)
    args.output.mkdir(parents=True)
    for mode in modes:
        run(args, mode)


if __name__ == '__main__':
    main()
