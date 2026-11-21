#!/usr/bin/env python3
"""Check private B: on disposable shared-console disks, with both modems."""
import argparse
import hashlib
import os
from pathlib import Path
import pty
import select
import shutil
import socket
import subprocess
import tempfile
import time
import tty
import execution_checks

from build_bye5 import wait_prompt
from check_modem_runtime import free_port, stop
from prepare_shared_trial import create


def run(source, romwbw, runtime, builds, tools, tcpser, modes=('direct', 'ip232'), execution=False):
    with tempfile.TemporaryDirectory(prefix='rcpm-sysutils-') as temporary:
        root = Path(temporary)
        for mode in modes:
            instance = root / mode
            create(source, romwbw, runtime, builds, tools, instance)
            a = instance / 'disks/drivea.dsk'
            b = instance / 'disks/driveb.dsk'
            b.chmod(0o644)
            # A harmless private executable distinguishes a rejected load from
            # successful execution without starting an interactive debugger.
            probe = root / 'BPROBE.COM'
            probe.write_bytes(bytes((0x11, 0x09, 0x01, 0x0e, 9, 0xcd, 5, 0, 0xc9))
                              + b'SYSUTILS-EXECUTED\r\n$')
            subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(b),
                            str(probe), '0:BPROBE.COM'], check=True)
            original_b = hashlib.sha256(b.read_bytes()).digest()
            private = root / 'USERS'
            private.write_bytes(b'PRIVATE-I2-DATA-MUST-STAY-PRIVATE\r\n')
            subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd',
                            str(instance / 'disks/drivei.dsk'), str(private), '2:USERS'], check=True)
            shutil.copyfile(Path(__file__).parent / 'guest/baccessprobe.asm', instance / 'baccessprobe.asm')
            subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'baccessprobe.asm'],
                           cwd=instance, check=True, stdout=subprocess.DEVNULL)
            # The test-only BDOS harness replaces one approved transient;
            # it is never installed in distributable/operator trial images.
            subprocess.run([str(tools / 'cpmrm'), '-f', 'ibm-3740', str(a), '0:CLS.COM'], check=True)
            subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(a),
                            str(instance / 'baccessprobe.bin'), '0:CLS.COM'], check=True)
            if execution:
                execution_checks.prepare(source, tools, instance)
            for name in ('BYE.COM', 'BYEDRIV.COM'):
                subprocess.run([str(tools / 'cpmrm'), '-f', 'ibm-3740', str(a), '0:' + name], check=True)
                subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(a),
                                str(builds / mode / name), '0:' + name], check=True)
            port, public = free_port(), free_port()
            master, slave = pty.openpty()
            tty.setraw(slave)
            modem = None
            with (root / f'{mode}.log').open('wb') as log:
                if mode == 'ip232':
                    modem = subprocess.Popen([str(tcpser), '-v', f'127.0.0.1:{port}',
                        '-p', f'127.0.0.1:{public}', '-s', '2400', '-S', '2400',
                        '-i', '&c1&d2', '-l', '0'], stdout=log, stderr=log,
                        restore_signals=False)
                env = dict(os.environ, RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1',
                           RCPM_MODEM_PORT=str(port))
                guest = subprocess.Popen([str(runtime), '-f', '4'], cwd=instance,
                    env=env, stdin=slave, stdout=slave, stderr=slave)
                caller = None
                prompt = b'A0:SYSTEM>'
                def local(marker=prompt):
                    result = wait_prompt(master, marker, log)
                    if marker == prompt:
                        time.sleep(.15)
                    return result
                def remote(marker=prompt, kick=False):
                    data = bytearray()
                    end, next_return = time.monotonic() + 30, 0
                    while time.monotonic() < end:
                        if kick and time.monotonic() >= next_return:
                            caller.sendall(b'\r')
                            next_return = time.monotonic() + .5
                        ready = select.select([caller, master], [], [], .05)[0]
                        if master in ready:
                            log.write(os.read(master, 8192))
                            log.flush()
                        if caller in ready:
                            block = caller.recv(8192)
                            if not block:
                                raise RuntimeError('Caller disconnected')
                            data.extend(block)
                            if data.count(b'Directory access denied.') > 1:
                                raise AssertionError('Directory-denial recovery loop reached the caller')
                            if marker in data:
                                time.sleep(.15)
                                return bytes(data)
                    raise RuntimeError(f'Remote timeout: {data[-1000:]!r}')
                def command(text):
                    caller.sendall(text.encode() + b'\r')
                    return remote()
                def settle_modem():
                    quiet = time.monotonic()
                    deadline = quiet + 30
                    while time.monotonic() - quiet < 2:
                        if time.monotonic() > deadline:
                            raise RuntimeError('Modem initialization did not settle')
                        if select.select([master], [], [], .05)[0]:
                            log.write(os.read(master, 8192))
                            log.flush()
                            quiet = time.monotonic()
                try:
                    local(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0')
                    if mode == 'ip232':
                        settle_modem()
                    for call in range(2):
                        caller = socket.create_connection(('127.0.0.1', port if mode == 'direct' else public), timeout=5)
                        remote(kick=mode == 'direct')
                        selection = command('B:')
                        if b'Directory access denied.' not in selection or b'B0>' in selection:
                            raise AssertionError('Denied B: selection did not restore the actual prompt')
                        if execution and execution_checks.MARKER in command('A0:UNSAFE'):
                            raise AssertionError('Execution restriction missing at login')
                        if b'B-ACCESS-DENIED-PASS' not in command('A0:CLS'):
                            raise AssertionError('BDOS B: access probe failed')
                        for text, forbidden in (
                            ('B:BPROBE', b'SYSUTILS-EXECUTED'),
                            ('B0:BPROBE', b'SYSUTILS-EXECUTED'),
                            ('TYPE B:VOLUME.TXT', b'private system maintenance'),
                            ('DIR B:BPROBE.COM', b'SYSUTILS-EXECUTED'),
                            ('B:SID', b'SID V'),
                        ):
                            result = command(text)
                            if forbidden in result:
                                raise AssertionError((mode, text, result))
                        if b'Hello from' not in command('TYPE J:HELLO.TXT'):
                            raise AssertionError('Public J: read regressed')
                        # Local private mode may use the exact same B: image.
                        os.write(master, b'\x02')
                        local()
                        os.write(master, b'B:BPROBE\r')
                        result = local()
                        if b'SYSUTILS-EXECUTED' not in result:
                            raise AssertionError('Local B: execution denied')
                        os.write(master, b'TYPE B:VOLUME.TXT\r')
                        if b'private system maintenance' not in local():
                            raise AssertionError('Local B: read denied')
                        os.write(master, b'A2:\r')
                        local(b'A2>')
                        os.write(master, b'TYPE I:USERS\r')
                        if b'PRIVATE-I2-DATA-MUST-STAY-PRIVATE' not in local(b'A2>'):
                            raise AssertionError('Private sysop could not read I2:')
                        # Reproduce takeover from a currently selected private
                        # DU, not merely a forbidden selection from A0:.
                        for directory, selected in ((b'I2:', b'I2>'), (b'B0:', b'B0>')):
                            os.write(master, directory + b'\r')
                            local(selected)
                            os.write(master, b'\x02')
                            recovered = remote()
                            if recovered.count(b'Directory access denied.') > 1:
                                raise AssertionError('Unblank caused a directory-denial loop')
                            if b'SYSUTILS-EXECUTED' in command('B:BPROBE'):
                                raise AssertionError('Unblank retained private privileges')
                            os.write(master, b'\x02')
                            local()
                        os.write(master, b'B:PIP I:LOCAL.TXT=J:HELLO.TXT\r')
                        local()
                        if execution:
                            execution_checks.local_setup(master, local)
                        os.write(master, b'\x02')
                        remote()
                        if b'SYSUTILS-EXECUTED' in command('B:BPROBE'):
                            raise AssertionError('B: remained public after unblank')
                        if execution:
                            execution_checks.caller_checks(command, caller, remote)
                        if b'Hello from' not in command('TYPE I:LOCAL.TXT'):
                            raise AssertionError('Local PIP did not work')
                        if call == 0:
                            caller.sendall(b'BYE\r')
                            deadline = time.monotonic() + 20
                            while time.monotonic() < deadline:
                                ready = select.select([caller, master], [], [], .05)[0]
                                if master in ready:
                                    log.write(os.read(master, 8192)); log.flush()
                                if caller in ready and not caller.recv(8192):
                                    break
                            else:
                                raise RuntimeError('Caller BYE did not hang up')
                        # Second call closes without BYE to test carrier loss.
                        if execution and call == 1:
                            command('RBBS')  # Arm an unused trusted-load permission.
                        caller.close()
                        caller = None
                        local(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0')
                        if mode == 'ip232':
                            settle_modem()
                    if execution:
                        caller = socket.create_connection(('127.0.0.1', port if mode == 'direct' else public), timeout=5)
                        remote(kick=mode == 'direct')
                        if execution_checks.RBBS_MARKER in command('A15:RBBS37'):
                            raise AssertionError('Launcher permission survived carrier loss')
                        caller.close()
                        caller = None
                        local(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0')
                        if mode == 'ip232':
                            settle_modem()
                    os.write(master, b'\x03')
                    local(b'normal unpatched')
                    os.write(master, b'\r')
                    local()
                    os.write(master, b'B:BYEBYE\r')
                    until = time.monotonic() + 10
                    while guest.poll() is None and time.monotonic() < until:
                        if select.select([master], [], [], .05)[0]:
                            log.write(os.read(master, 8192))
                            log.flush()
                    if guest.poll() is None:
                        raise RuntimeError('Local shutdown timeout: ' + repr((root / f'{mode}.log').read_bytes()[-1200:]))
                    if guest.returncode:
                        raise AssertionError('Local shutdown failed')
                    if hashlib.sha256(b.read_bytes()).digest() != original_b:
                        raise AssertionError('Private B: image changed')
                    if execution:
                        execution_checks.verify(tools, instance)
                    print(f'PASS {mode}: caller B: denial, local read/execute/PIP, rearm and local shutdown')
                    if execution:
                        print(f'PASS {mode}: approved A0: loads; other sources/boot tools denied; '
                              'resident privilege/memory controls; A: writes denied; executable YMODEM download')
                finally:
                    if caller:
                        caller.close()
                    stop(guest)
                    if modem:
                        stop(modem)
                    os.close(master)
                    os.close(slave)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--romwbw', type=Path, required=True)
    p.add_argument('--tcpser', type=Path, required=True)
    p.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    p.add_argument('--builds', type=Path, default=Path('build/bye5/sysutils'))
    p.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    p.add_argument('--mode', choices=('direct', 'ip232'), action='append')
    p.add_argument('--execution', action='store_true')
    a = p.parse_args()
    run(*(getattr(a, name).resolve() for name in ('source', 'romwbw', 'runtime', 'builds', 'cpmtools', 'tcpser')),
        modes=a.mode or ('direct', 'ip232'), execution=a.execution)
