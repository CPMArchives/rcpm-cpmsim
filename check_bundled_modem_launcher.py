#!/usr/bin/env python3
"""Check direct and launcher-owned tcpser using disposable copies of a package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import time
from check_help_release import open_topic, leave, prepare_windows_console

if os.name != 'nt':
    from check_release import Guest


def check(package, output):
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for mode in ('direct', 'ip232'):
        with tempfile.TemporaryDirectory(prefix='rcpm-foreground-check-') as temporary:
            root = Path(temporary) / 'board with spaces'
            root.mkdir()
            for name in ('runtime', 'drivers', 'disks', 'conf', 'state', 'uploads'):
                shutil.copytree(package / name, root / name)
            shutil.copy2(package / 'RCPM.CONF', root / 'RCPM.CONF')
            launcher = next(package / n for n in ('Start-RCPM.sh', 'Start-RCPM.command', 'Start-RCPM.cmd')
                            if (package / n).exists())
            shutil.copy2(launcher, root)
            # Exercise the file setting, not a command-line mode override.
            settings = (root / 'RCPM.CONF').read_text().replace('MODE=direct', 'MODE=' + mode)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0)); port = listener.getsockname()[1]
            (root / 'RCPM.CONF').write_text(settings.replace('PORT=4000', 'PORT=' + str(port)))
            if os.name == 'nt':
                import ctypes
                from check_windows_release import Guest as WindowsGuest
                prepare_windows_console()
                guest = WindowsGuest(root, output / mode, port)
            else:
                guest = Guest(root, output / mode)
            passed = False
            try:
                guest.wait(b'RCP/M modem ready.' if mode == 'direct' else
                           b'ATE0Q0V0S0=0M0S10=25X1H0', timeout=60)
                if mode == 'ip232':
                    guest.wait(b'\n0\n' if os.name == 'nt' else b'\n0\r\n')
                    guest.collect(3)
                if os.name == 'nt':
                    guest.caller = socket.create_connection(('127.0.0.1', port), timeout=5)
                    deadline = time.monotonic() + (60 if mode == 'ip232' else 35)
                    while b'A0:SYSTEM>' not in guest.remote:
                        if time.monotonic() > deadline: raise RuntimeError('Caller login timed out')
                        if mode == 'direct': guest.caller.sendall(b'\r')
                        guest.collect(.4)
                else:
                    guest.connect(port, kick=mode == 'direct', timeout=60 if mode == 'ip232' else 25)
                assert len(open_topic(guest, 'HELP', b'HUMONGOUS RCP/M - ONLINE HELP')) > 100
                leave(guest)
                local_start = len(guest.local)
                guest.caller.close(); guest.caller = None
                if mode == 'ip232':
                    guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0', start=local_start)
                    guest.wait(b'\n0\n' if os.name == 'nt' else b'\n0\r\n', start=local_start)
                guest.collect(3)
                guest.remote.clear()
                if os.name == 'nt':
                    guest.caller = socket.create_connection(('127.0.0.1', port), timeout=5)
                    deadline = time.monotonic() + (60 if mode == 'ip232' else 35)
                    while b'A0:SYSTEM>' not in guest.remote:
                        if time.monotonic() > deadline: raise RuntimeError('Caller reconnect timed out')
                        if mode == 'direct': guest.caller.sendall(b'\r')
                        guest.collect(.4)
                else:
                    guest.connect(port, kick=mode == 'direct', timeout=60 if mode == 'ip232' else 25)
                assert len(open_topic(guest, 'HELP', b'HUMONGOUS RCP/M - ONLINE HELP')) > 100
                leave(guest)
                if mode == 'ip232':
                    local_start = len(guest.local)
                    guest.caller.close(); guest.caller = None
                    guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0', start=local_start)
                    guest.wait(b'\n0\n' if os.name == 'nt' else b'\n0\r\n', start=local_start)
                    guest.collect(3)
                guest.stop()
                with socket.socket() as listener:
                    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    listener.bind(('127.0.0.1', port))
                passed = True
                results.append(dict(mode=mode, passed=True, HELP=True, reconnect=True,
                                    clean_shutdown=True, caller_port_released=True))
            finally:
                (output / (mode + '-console.log')).write_bytes(bytes(guest.local))
                (output / (mode + '-caller.log')).write_bytes(bytes(guest.remote))
                if (root / 'state/tcpser.log').exists():
                    shutil.copy2(root / 'state/tcpser.log', output / (mode + '-tcpser.log'))
                if guest.process.poll() is None:
                    guest.process.terminate()
                    try: guest.process.wait(timeout=5)
                    except Exception: guest.process.kill(); guest.process.wait()
                if os.name != 'nt':
                    os.close(guest.master); os.close(guest.slave)
                if not passed:
                    print('Failure console tail:', repr(bytes(guest.local[-3500:])), flush=True)
                    if (root / 'state/tcpser.log').exists():
                        print('Modem diagnostic tail:', (root / 'state/tcpser.log').read_text(errors='replace')[-3500:], flush=True)
                    (output / 'result.json').write_text(json.dumps(dict(passed=False, completed=results), indent=2)+'\n')
    value = dict(passed=True, results=results, launcher_sha256=hashlib.sha256(
        (package / ('runtime/rcpm.exe' if os.name == 'nt' else 'runtime/rcpm')).read_bytes()).hexdigest())
    (output / 'result.json').write_text(json.dumps(value, indent=2)+'\n')
    print(json.dumps(value, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); check(a.package.resolve(), a.output.resolve())
