#!/usr/bin/env python3
"""Exercise built BYE5 configurations on disposable CP/M 3/Z3PLUS media."""
import argparse
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

from check_modem_runtime import free_port, stop
from build_bye5 import wait_prompt
from prepare_z3plus import prepare


def run(source, runtime, tools, builds, output, tcpser, romwbw=None):
    output.mkdir(parents=True, exist_ok=True)
    for mode in ('direct', 'ip232'):
        work = output / mode
        work.mkdir(exist_ok=True)
        (work / 'disks').mkdir(exist_ok=True)
        (work / 'conf').mkdir(exist_ok=True)
        for kind in ('server', 'client'):
            (work / f'conf/net_{kind}.conf').write_text('# Isolated BYE5 test.\n')
        disk = work / 'disks/drivea.dsk'
        if disk.exists():
            disk.unlink()
        stock = source / 'cpmsim/disks/library/cpm3-1.dsk'
        base = work / 'stock.dsk'
        shutil.copyfile(stock, base)
        subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                        str(base), '0:PROFILE.SUB'], check=True)
        if romwbw:
            prepare(romwbw / 'Source/Images', base, disk)
        else:
            shutil.copyfile(base, disk)
        subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                        str(disk), '0:BYE.COM', '0:ED.COM'], check=True)
        for name in ('BYE.COM', 'BYEDRIV.COM'):
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), str(builds / mode / name), '0:' + name], check=True)
        for name, content in (('PROBE.TXT', b'SHARED-CONSOLE-OK\r\n\x1a'),
                              ('PRIVATE.TXT', b'PRIVATE-OUTPUT-CHECK\r\n\x1a'),
                              ('USERCHK.TXT', b'CALLER-FILE-REMAINS\r\n\x1a'),
                              ('SYSCHK.TXT', b'SYSOP-FILE-TO-DELETE\r\n\x1a')):
            path = work / name
            path.write_bytes(content)
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), str(path), '0:' + name], check=True)
        port, call_port = free_port(), free_port()
        while port == call_port:
            call_port = free_port()
        env = dict(os.environ, RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1',
                   RCPM_MODEM_PORT=str(port))
        master, slave = pty.openpty()
        tty.setraw(slave)
        prompt = b'A0:SYSTEM>' if romwbw else b'A>'
        modem = None
        with (work / 'console.log').open('wb') as log, (work / 'tcpser.log').open('wb') as mlog:
            if mode == 'ip232':
                modem = subprocess.Popen([str(tcpser), '-v', f'127.0.0.1:{port}',
                    '-p', f'127.0.0.1:{call_port}', '-s', '2400', '-S', '2400',
                    '-i', '&c1&d2', '-l', '4'], stdout=mlog, stderr=mlog)
            guest = subprocess.Popen([str(runtime), '-f', '4'], cwd=work, env=env,
                                     stdin=slave, stdout=slave, stderr=slave)
            def local(marker, timeout=30):
                return wait_prompt(master, marker, log, timeout)
            def remote(client, marker, kick=False, timeout=30, after=None):
                data = bytearray()
                end = time.monotonic() + timeout
                next_kick = 0
                while time.monotonic() < end:
                    if kick and time.monotonic() >= next_kick:
                        client.sendall(b'\r')
                        next_kick = time.monotonic() + .5
                    ready = select.select([client, master], [], [], .05)[0]
                    if master in ready:
                        part = os.read(master, 8192)
                        log.write(part)
                        log.flush()
                    if client in ready:
                        part = client.recv(8192)
                        if not part:
                            raise RuntimeError(f'Unexpected caller disconnect: {bytes(data)!r}')
                        data.extend(part)
                        if marker in data and (after is None or after in data[data.index(marker) + len(marker):]):
                            return bytes(data)
                    if guest.poll() is not None:
                        raise RuntimeError('cpmsim exited during BYE test')
                raise RuntimeError(f'Remote timeout for {marker!r}: {bytes(data)!r}')
            try:
                local(prompt)
                os.write(master, b'BYE\r')
                local(b'BYE5')
                if not romwbw:
                    result = local(b'A>', timeout=30)
                    if b'requires a valid Z3PLUS environment' not in result:
                        raise RuntimeError('Expected refusal without Z3PLUS')
                    print(f'PASS {mode}: missing Z3PLUS is refused before answering', flush=True)
                    continue
                caller_port = port if mode == 'direct' else call_port
                for attempt in range(3):
                    if mode == 'ip232':
                        # Wait for Hayes initialization, including a potentially silent
                        # environment scan, before measuring the final quiet interval.
                        deadline = time.monotonic() + 30
                        marker = b'ATE0Q0V0S0=0M0S10=25X1H0'
                        while (work / 'console.log').read_bytes().count(marker) < attempt + 1:
                            if time.monotonic() > deadline:
                                raise RuntimeError('Hayes initialization command not observed')
                            if select.select([master], [], [], .05)[0]:
                                log.write(os.read(master, 8192)); log.flush()
                        quiet = time.monotonic()
                        deadline = quiet + 30
                        while time.monotonic() - quiet < 2:
                            if time.monotonic() > deadline:
                                raise RuntimeError('Modem initialization did not settle')
                            if select.select([master], [], [], .05)[0]:
                                log.write(os.read(master, 8192)); log.flush()
                                quiet = time.monotonic()
                    with socket.create_connection(('127.0.0.1', caller_port), timeout=3) as caller:
                        remote(caller, prompt, kick=mode == 'direct', timeout=45)
                        if romwbw:
                            caller.sendall(b'ERA USERCHK.TXT\r')
                            remote(caller, prompt)
                            caller.sendall(b'TYPE USERCHK.TXT\r')
                            remote(caller, b'CALLER-FILE-REMAINS', after=prompt)
                        # A real transient command verifies warm boot and console routing.
                        caller.sendall(b'TYPE PROBE.TXT\r')
                        remote(caller, b'SHARED-CONSOLE-OK', after=prompt)
                        if attempt == 0:
                            # Type a complete command from the local keyboard while connected.
                            os.write(master, b'TYPE PROBE.TXT\r')
                            remote(caller, b'SHARED-CONSOLE-OK', after=prompt)
                            os.write(master, b'\x02')
                            local(prompt)
                            if romwbw:
                                os.write(master, b'ERA SYSCHK.TXT\r')
                                local(prompt)
                            os.write(master, b'TYPE PRIVATE.TXT\r')
                            local(prompt)
                            os.write(master, b'\x02')
                            local(prompt)
                            # Unblanking can emit a prompt; private file contents must stay local.
                            captured = bytearray()
                            until = time.monotonic() + .25
                            while time.monotonic() < until:
                                if select.select([caller], [], [], .02)[0]:
                                    captured.extend(caller.recv(8192))
                            if b'PRIVATE-OUTPUT-CHECK' in captured:
                                raise RuntimeError('Private sysop output reached the caller')
                        if attempt == 1:
                            caller.close()
                            local(b'[Carrier lost]', timeout=20)
                        else:
                            if attempt == 2:
                                os.write(master, b'\x0e')  # BYE's local forced-disconnect key.
                            else:
                                caller.sendall(b'BYE\r')
                            end = time.monotonic() + 20
                            while time.monotonic() < end:
                                ready = select.select([caller, master], [], [], .05)[0]
                                if master in ready:
                                    log.write(os.read(master, 8192)); log.flush()
                                if caller in ready and not caller.recv(8192):
                                    break
                            else:
                                raise RuntimeError('BYE/forced disconnect did not hang up')
                        if guest.poll() is not None:
                            raise RuntimeError('Caller BYE terminated cpmsim')
                        time.sleep(.4)
                if romwbw:
                    listing = subprocess.check_output([str(tools / 'cpmls'), '-T', 'raw',
                        '-f', 'ibm-3740', str(disk), '0:*']).lower()
                    if b'userchk.txt' not in listing or b'syschk.txt' in listing:
                        raise RuntimeError('Wheel transition file checks failed')
                print(f'PASS {mode}: {"Z3PLUS" if romwbw else "CP/M 3"}, three calls in one guest, '
                      'transient commands, local typing, private blanking, BYE/carrier-loss/forced logoff', flush=True)
            finally:
                stop(guest)
                if modem:
                    stop(modem)
                os.close(master)
                os.close(slave)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--builds', type=Path, default=Path('build/bye5'))
    parser.add_argument('--output', type=Path, default=Path('build/bye5/checks'))
    parser.add_argument('--tcpser', type=Path, required=True)
    parser.add_argument('--romwbw', type=Path)
    args = parser.parse_args()
    run(args.source.resolve(), args.runtime.resolve(), args.cpmtools.resolve(),
        args.builds.resolve(), args.output.resolve(), args.tcpser.resolve(),
        args.romwbw.resolve() if args.romwbw else None)
