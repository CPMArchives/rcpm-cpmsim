#!/usr/bin/env python3
"""Exercise built BYE5 configurations on disposable CP/M 3/Z3PLUS media."""
import argparse
import os
from pathlib import Path
import pty
import select
import signal
import shutil
import socket
import subprocess
import tempfile
import time
import tty

from check_modem_runtime import free_port, stop
from build_bye5 import wait_prompt
from prepare_z3plus import prepare
import shared_service_checks as service_checks


def run(source, runtime, tools, builds, output, tcpser, romwbw=None, autostart=False,
        probe_remote_shutdown=False, services=False, work_readonly=False):
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
            prepare(romwbw / 'Source/Images', base, disk, startup_command=
                    'A0:PATH /C A0;A:GET CONSOLE;A:BYE' if autostart else 'A0:PATH /C A0')
        else:
            shutil.copyfile(base, disk)
        subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                        str(disk), '0:BYE.COM', '0:ED.COM'], check=True)
        for name in ('BYE.COM', 'BYEDRIV.COM', 'BYEBYE.COM'):
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), str(builds / mode / name), '0:' + name], check=True)
        # Test-only stand-in under an approved name; never installed in release media.
        subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                        str(disk), '0:CLS.COM'], check=True)
        shutil.copyfile(Path(__file__).parent / 'guest/queueprobe.asm', work / 'queueprobe.asm')
        subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'queueprobe.asm'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                        str(work / 'queueprobe.bin'), '0:CLS.COM'], check=True)
        for name, content in (('PROBE.TXT', b'SHARED-CONSOLE-OK\r\n\x1a'),
                              ('PRIVATE.TXT', b'PRIVATE-OUTPUT-CHECK\r\n\x1a'),
                              ('USERCHK.TXT', b'CALLER-FILE-REMAINS\r\n\x1a'),
                              ('SYSCHK.TXT', b'SYSOP-FILE-TO-DELETE\r\n\x1a'),
                              ('QUEUED.TXT', b'STALE-COMMAND-EXECUTED\r\n\x1a')):
            path = work / name
            path.write_bytes(content)
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), str(path), '0:' + name], check=True)
        if romwbw:
            service_checks.prepare_work(source, tools, work, disk)
            if work_readonly:
                (work / 'disks/drivei.dsk').chmod(0o444)
        if services:
            service_checks.prepare_services(source, tools, work, disk)
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
                    '-i', '&c1&d2', '-l', '4'], stdout=mlog, stderr=mlog,
                    restore_signals=False)
            guest = subprocess.Popen([str(runtime), '-s', '-f', '4'], cwd=work, env=env,
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
                            if marker == prompt or after == prompt:
                                # Pace scripted commands through CP/M's warm-boot
                                # and line-input setup, as a terminal user would.
                                time.sleep(.1)
                            return bytes(data)
                    if guest.poll() is not None:
                        raise RuntimeError('cpmsim exited during BYE test')
                raise RuntimeError(f'Remote timeout for {marker!r}: {bytes(data)!r}')
            try:
                if not autostart:
                    local(prompt)
                    os.write(master, b'BYE\r')
                startup = local(b'BYE510 -')
                if autostart and b'Getting console input from console' not in startup:
                    raise RuntimeError('BYE started without confirmation that GET redirection ended')
                if not romwbw:
                    result = local(b'A>', timeout=30)
                    if b'requires a valid Z3PLUS environment' not in result:
                        raise RuntimeError('Expected refusal without Z3PLUS')
                    print(f'PASS {mode}: missing Z3PLUS is refused before answering', flush=True)
                    continue
                caller_port = port if mode == 'direct' else call_port
                if work_readonly:
                    result = startup
                    if prompt not in result:
                        result += local(prompt)
                    if b'WORK cleanup failed' not in result or b'answering disabled' not in result:
                        raise RuntimeError('Read-only WORK did not stop answering')
                    with socket.create_connection(('127.0.0.1', caller_port), timeout=3) as caller:
                        caller.settimeout(.3)
                        caller.sendall(b'\r')
                        try:
                            reply = caller.recv(1024)
                        except socket.timeout:
                            reply = b''
                        if reply:
                            raise RuntimeError(f'Guest answered with failed WORK cleanup: {reply!r}')
                    if guest.poll() is not None:
                        raise RuntimeError('WORK cleanup failure terminated the machine')
                    print(f'PASS {mode}: read-only WORK disables answering and returns to local CP/M', flush=True)
                    continue
                def answer_ready(count):
                    marker = b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0'
                    deadline = time.monotonic() + 30
                    while (work / 'console.log').read_bytes().count(marker) < count:
                        if time.monotonic() > deadline:
                            status = modem.poll() if modem else None
                            raise RuntimeError(f'BYE did not finish recovery; tcpser exit status: {status}')
                        if select.select([master], [], [], .05)[0]:
                            log.write(os.read(master, 8192)); log.flush()
                    if mode == 'ip232':
                        quiet = time.monotonic()
                        deadline = quiet + 30
                        while time.monotonic() - quiet < 2:
                            if time.monotonic() > deadline:
                                raise RuntimeError('Modem initialization did not settle')
                            if select.select([master], [], [], .05)[0]:
                                log.write(os.read(master, 8192)); log.flush()
                                quiet = time.monotonic()
                calls = 4 if services else 3
                for attempt in range(calls):
                    answer_ready(attempt + 1)
                    with socket.create_connection(('127.0.0.1', caller_port), timeout=3) as caller:
                        if services:
                            caller.settimeout(15)
                        remote(caller, prompt, kick=mode == 'direct', timeout=45)
                        service_checks.verify_work_clean(tools, work)
                        caller.sendall(b'A0:HELP\r')
                        remote(caller, b'READONLY WORK FILE CREATED', after=prompt)
                        if services:
                            caller.sendall(b'A0:DIR\r')
                            remote(caller, b'SERVICE STATE RESET', after=prompt)
                            if attempt:
                                service_checks.verify_inbox(work)
                        if probe_remote_shutdown and attempt == 0:
                            # Deliberately destructive to this disposable guest only.
                            # A wheel-off caller must not be able to stop the machine.
                            caller.sendall(b'BYEBYE\r')
                            remote(caller, prompt, timeout=10)
                        if attempt == 0:
                            # Positive control: the seeded command really executes
                            # if the program returns without a lifecycle transition.
                            caller.sendall(b'A0:CLS\r')
                            remote(caller, b'PENDING COMMAND ARMED')
                            caller.sendall(b'x')
                            remote(caller, b'STALE-COMMAND-EXECUTED', after=prompt)
                        if romwbw:
                            caller.sendall(b'ERA USERCHK.TXT\r')
                            remote(caller, prompt)
                            caller.sendall(b'TYPE USERCHK.TXT\r')
                            remote(caller, b'CALLER-FILE-REMAINS', after=prompt)
                        # A real transient command verifies warm boot and console routing.
                        caller.sendall(b'TYPE PROBE.TXT\r')
                        remote(caller, b'SHARED-CONSOLE-OK', after=prompt)
                        if services and attempt == 0:
                            service_checks.upload_x(caller)
                            remote(caller, b'Upload saved to the operator inbox.', after=prompt)
                            service_checks.upload_y(caller)
                            remote(caller, b'Upload saved to the operator inbox.', after=prompt)
                            service_checks.download_y(caller)
                            remote(caller, b'YMODEM download complete.', after=prompt)
                            caller.sendall(b'MESSAGE\r')
                            remote(caller, b'> ')
                            caller.sendall(service_checks.MESSAGE.rstrip(b'\r\n') + b'\r')
                            remote(caller, b'> ')
                            caller.sendall(b'/S\r')
                            remote(caller, b'Message saved to the operator inbox.', after=prompt)
                            service_checks.verify_inbox(work)
                        if attempt == 0:
                            # Type a complete command from the local keyboard while connected.
                            os.write(master, b'TYPE PROBE.TXT\r')
                            remote(caller, b'SHARED-CONSOLE-OK', after=prompt)
                            caller.sendall(b'A0:CLS\r')
                            remote(caller, b'PENDING COMMAND ARMED')
                            os.write(master, b'\x02')
                            local(prompt)
                            if romwbw:
                                os.write(master, b'ERA SYSCHK.TXT\r')
                                local(prompt)
                            os.write(master, b'TYPE PRIVATE.TXT\r')
                            local(prompt)
                            os.write(master, b'A0:CLS\r')
                            local(b'PENDING COMMAND ARMED')
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
                        if attempt == 1 or (services and attempt == 2):
                            if services and attempt == 1:
                                service_checks.partial_upload(caller)
                            elif services:
                                caller.sendall(b'MESSAGE\r')
                                remote(caller, b'> ')
                                caller.sendall(b'THIS DRAFT MUST BE DISCARDED\r')
                                remote(caller, b'> ')
                            else:
                                caller.sendall(b'A0:CLS\r')
                                remote(caller, b'PENDING COMMAND ARMED')
                            caller.close()
                            local(b'[Carrier lost]', timeout=20)
                        else:
                            if attempt == calls - 1:
                                caller.sendall(b'A0:CLS\r')
                                remote(caller, b'PENDING COMMAND ARMED')
                                os.write(master, b'\x0e')  # BYE's local forced-disconnect key.
                            else:
                                caller.sendall(b'BYE;TYPE QUEUED.TXT\r')
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
                answer_ready(calls + 1)
                if services:
                    service_checks.verify_inbox(work)
                service_checks.verify_work_clean(tools, work)
                if romwbw:
                    listing = subprocess.check_output([str(tools / 'cpmls'), '-T', 'raw',
                        '-f', 'ibm-3740', str(disk), '0:*']).lower()
                    if b'userchk.txt' not in listing or b'syschk.txt' in listing:
                        raise RuntimeError('Wheel transition file checks failed')
                # Leave the resident remote service, then verify the preserved
                # renamed stock BYEBYE.COM still shuts down the single emulator.
                os.write(master, b'\x03')
                local(b'normal unpatched')
                os.write(master, b'\r')
                local(prompt)
                time.sleep(.1)
                os.write(master, b'BYEBYE\r')
                deadline = time.monotonic() + 10
                while guest.poll() is None and time.monotonic() < deadline:
                    if select.select([master], [], [], .05)[0]:
                        try:
                            log.write(os.read(master, 8192)); log.flush()
                        except OSError:
                            break
                if guest.poll() is None:
                    raise RuntimeError('Native BYEBYE did not shut down; see console.log')
                queued_count = (work / 'console.log').read_bytes().count(b'STALE-COMMAND-EXECUTED')
                if queued_count != 1:
                    raise RuntimeError(f'Expected only the queued-command positive control; got {queued_count}')
                print(f'PASS {mode}: {"Z3PLUS" if romwbw else "CP/M 3"}, {calls} calls in one guest, '
                      'transient commands, local typing, private blanking, BYE/carrier-loss/forced logoff; '
                      'pending-command/WORK cleanup; I1 preserved; BYEBYE shutdown', flush=True)
                if services:
                    print(f'PASS {mode}: XMODEM upload with CRC retry/duplicate; YMODEM batch '
                          'upload and J: download; saved MESSAGE; persistent inbox; '
                          'discarded partial upload/draft; service state reset', flush=True)
            except Exception:
                # Keep guest registers and RAM for diagnosing failed lifecycle tests.
                if guest.poll() is None:
                    guest.send_signal(signal.SIGINT)
                    try:
                        guest.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                raise
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
    parser.add_argument('--autostart', action='store_true')
    parser.add_argument('--probe-remote-shutdown', action='store_true',
                        help='Security probe on disposable media: a caller tries BYEBYE; '
                             'failure or disconnect means local-only shutdown is not established')
    parser.add_argument('--services', action='store_true',
                        help='Check modem-path transfers, messages and persistence across four calls')
    parser.add_argument('--work-readonly', action='store_true',
                        help='Verify failed WORK cleanup disables answering and returns to local CP/M')
    args = parser.parse_args()
    if args.autostart and not args.romwbw:
        parser.error('--autostart requires --romwbw')
    if args.probe_remote_shutdown and not args.romwbw:
        parser.error('--probe-remote-shutdown requires --romwbw')
    if args.services and not args.romwbw:
        parser.error('--services requires --romwbw')
    if args.work_readonly and (not args.romwbw or args.services or args.probe_remote_shutdown):
        parser.error('--work-readonly requires --romwbw and cannot be combined with other service probes')
    run(args.source.resolve(), args.runtime.resolve(), args.cpmtools.resolve(),
        args.builds.resolve(), args.output.resolve(), args.tcpser.resolve(),
        args.romwbw.resolve() if args.romwbw else None, args.autostart,
        args.probe_remote_shutdown, args.services, args.work_readonly)
