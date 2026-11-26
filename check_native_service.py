#!/usr/bin/env python3
"""Qualify a service kit in disposable directories, private loopback ports only."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

from check_modem_runtime import free_port


def run(package):
    spec = importlib.util.spec_from_file_location('native_service', package / 'service/rcpm_service.py')
    service = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(service)
    result = {}
    with tempfile.TemporaryDirectory(prefix='rcpm-svc-', dir='/tmp') as temporary:
        work = Path(temporary)
        root = work / 'instance'
        shutil.copytree(package, root)
        private_marker = b'RCPM-SERVICE-PRIVATE-SENTINEL'
        fixture = work / 'private.txt'
        fixture.write_bytes(private_marker + b'\r\n')
        subprocess.run([str(root / 'runtime/cpmcp'), '-f', 'z80pack-hd',
                        str(root / 'disks/drivei.dsk'), str(fixture), '15:SVCPRIV.TXT'],
                       env=dict(os.environ, DISKDEFS=str(root / 'runtime/diskdefs')), check=True)
        run_dir = work / 'run'
        backup = work / 'snapshot'
        notify = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        notify.bind(str(work / 'notify.sock'))
        notify.settimeout(5)
        port, serial, internal = free_port(), free_port(), free_port()
        assert len({port, serial, internal}) == 3
        def launch(instance):
            log = (work / ('service-' + instance.name + '.log')).open('wb')
            p = subprocess.Popen([sys.executable, str(instance / 'service/rcpm_service.py'),
                '--run-dir', str(run_dir), 'run', '--instance', str(instance),
                '--tcpser', str(instance / 'runtime/tcpser'), '--port', str(port),
                '--modem-port', str(serial), '--caller-port', str(internal), '--trace-console', str(work / 'console.log')], stdout=log, stderr=log,
                env=dict(os.environ, NOTIFY_SOCKET=str(work / 'notify.sock')))
            end = time.monotonic() + 150
            while time.monotonic() < end:
                try:
                    if service.request(run_dir, 'status')['ready']:
                        assert notify.recv(128) == b'READY=1'
                        return p, log
                except (OSError, RuntimeError):
                    pass
                if p.poll() is not None:
                    log.close()
                    raise RuntimeError((work / ('service-' + instance.name + '.log')).read_text())
                time.sleep(.1)
            p.terminate()
            raise RuntimeError('Service never ready')
        def login():
            c = socket.create_connection(('127.0.0.1', port), timeout=3)
            c.settimeout(.5)
            data = bytearray()
            end = time.monotonic() + 45
            while b'A0:SYSTEM>' not in data and time.monotonic() < end:
                try:
                    data.extend(c.recv(16384))
                except socket.timeout:
                    pass
            if b'A0:SYSTEM>' not in data:
                raise RuntimeError('Caller login failed: ' + repr(data[-200:]))
            return c
        def command(c, text):
            for byte in (text + '\r').encode():
                c.sendall(bytes([byte]))
                time.sleep(.03)
            data = bytearray()
            end = time.monotonic() + 45
            while b'A0:SYSTEM>' not in data and time.monotonic() < end:
                try:
                    part = c.recv(16384)
                    if not part:
                        break
                    data.extend(part)
                except socket.timeout:
                    pass
            if b'A0:SYSTEM>' not in data:
                raise RuntimeError('Command failed: ' + repr(data[-300:]))
            return data
        process = log = caller = None
        try:
            process, log = launch(root)
            credentials = (root / 'SYSOP.DOC').read_bytes()
            result['unattended_boot_IP232'] = True
            result['systemd_READY_notification'] = True
            duplicate = subprocess.run([sys.executable, str(root / 'service/rcpm_service.py'),
                '--run-dir', str(run_dir), 'run', '--instance', str(root),
                '--tcpser', str(root / 'runtime/tcpser'), '--port', str(port),
                '--modem-port', str(serial), '--caller-port', str(internal)],
                capture_output=True, timeout=5)
            assert duplicate.returncode != 0
            result['duplicate_service_refused'] = True
            # Attach/detach twice through the authenticated private control socket.
            for _ in range(2):
                with socket.socket(socket.AF_UNIX) as client:
                    client.connect(str(run_dir / 'control.sock'))
                    client.sendall(b'{"action":"attach"}\n')
                    assert b'"ok":true' in client.recv(100)
                time.sleep(.3)
            result['console_reattach'] = True
            caller = login()
            assert b'HELP' in command(caller, 'HELP').upper()
            result['caller_HELP_via_tcpser'] = True
            denied = command(caller, 'LT I15:SVCPRIV.TXT')
            assert private_marker not in denied and b'Invalid or missing delimiter' not in denied, denied
            denied = command(caller, 'SYSUTLS:BYEBYE')
            assert process.poll() is None
            result['private_data_and_remote_shutdown_denied'] = True
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(service.request, run_dir, 'backup', str(backup))
                end = time.monotonic() + 5
                while not service.request(run_dir, 'status')['draining']:
                    assert time.monotonic() < end
                    time.sleep(.05)
                assert not future.done(), 'Backup must wait for the active caller'
                with socket.create_connection(('127.0.0.1', port), timeout=3) as rejected:
                    rejected.settimeout(3)
                    assert rejected.recv(1) == b''
                caller.close()
                response = future.result(timeout=180)
                assert response['stopped']
            assert process.wait(timeout=10) == 0
            log.close()
            process = log = None
            result['drain_rejects_new_calls_waits_for_existing'] = True
            result['graceful_shutdown_and_verified_snapshot'] = True
            service.verify(backup)
            restored = work / 'restored'
            service.restore(backup, restored)
            assert (restored / 'SYSOP.DOC').read_bytes() == credentials
            assert service.digest(restored / 'disks/drivei.dsk') == service.digest(backup / 'instance/disks/drivei.dsk')
            process, log = launch(restored)
            caller = login()
            command(caller, 'HELP')
            caller.close()
            result['restored_boot_login_credentials_and_disk_hash'] = True
            # Terminate only the modem launched by this disposable supervisor.
            # This checks crash reporting/cleanup, not database-consistent stop.
            state = service.request(run_dir, 'status')
            os.kill(state['tcpser_pid'], signal.SIGTERM)
            assert process.wait(timeout=15) != 0
            log.close()
            process = log = None
            assert (restored / 'SYSOP.DOC').read_bytes() == credentials
            process, log = launch(restored)
            caller = login()
            command(caller, 'HELP')
            caller.close()
            service.request(run_dir, 'stop')
            assert process.wait(timeout=10) == 0
            result['tcpser_failure_reported_pair_restart_preserves_credentials'] = True
            print(json.dumps(result, indent=2))
            return result
        finally:
            notify.close()
            if caller:
                caller.close()
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Disposable fixture only, never a production shutdown path.
                    process.kill()
                    process.wait()
            if log:
                log.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    a = p.parse_args()
    run(a.package.resolve())
