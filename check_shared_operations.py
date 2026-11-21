#!/usr/bin/env python3
"""Exercise cold backup/restore with populated media and launcher ownership guards."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shutil
import socket
import subprocess
import sys
import time
import tty
from unittest.mock import patch

from backup_rcpm import backup, restore, verify, copy_file
from shared_instance import lock
from shared_launcher import ensure_session

REPO = Path(__file__).resolve().parent


def rejected(action, text):
    try:
        action()
    except (RuntimeError, ValueError, FileExistsError) as error:
        assert text in str(error), str(error)
    else:
        raise AssertionError('Expected refusal: ' + text)


class ExistingSession:
    def __init__(self, owner, port):
        self.owner, self.port, self.calls = owner, port, []
    def find(self, name):
        return '$42'
    def run(self, *args):
        self.calls.append(args)
        value = ('0\n' if args[0] == 'list-panes' else
                 str(self.owner) if args[-1] == '@rcpm_instance' else str(self.port))
        return subprocess.CompletedProcess(args, 0, value, '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = args.source.resolve()
    # Populate a disposable fixture; never edit the operator's running media.
    fixture = root / 'original'
    fixture.mkdir()
    for item in source.rglob('*'):
        relative = item.relative_to(source)
        if relative.parts[0] in ('backups', '.console.lock', '.launch.lock'):
            continue
        target = fixture / relative
        if item.is_dir():
            target.mkdir(exist_ok=True)
        elif item.is_file():
            copy_file(item, target, item.stat().st_mode & 0o777)
    inbox = fixture / 'upload-inbox/restore-check.bin'
    inbox.write_bytes(bytes(range(256)) * 4)
    (fixture / 'rbbs-trial-passwords.json').chmod(0o600)
    saved = backup(fixture, root / 'backup')
    data = verify(saved)
    restored = restore(saved, root / 'restored')
    for row in data['files']:
        if row['path'].endswith('.command') or row['path'] == 'trial-build.json':
            continue
        assert hashlib.sha256((restored / row['path']).read_bytes()).hexdigest() == row['sha256']
    assert (restored / 'rbbs-trial-passwords.json').stat().st_mode & 0o777 == 0o600
    assert str(restored) in (restored / 'Start-RCPM.command').read_text()
    assert (restored / 'disks/drivep.dsk').stat().st_blocks * 512 < 32 * 1024 * 1024
    rejected(lambda: restore(saved, restored), 'new directory')
    with lock(fixture, '.console.lock', 'test'):
        rejected(lambda: backup(fixture, root / 'must-not-exist'), 'running')
    assert not (root / 'must-not-exist').exists()
    manifest_path = saved / 'backup.json'
    original = manifest_path.read_bytes()
    broken = json.loads(original)
    broken['files'][0]['path'] = '../escape'
    manifest_path.write_text(json.dumps(broken))
    rejected(lambda: verify(saved), 'Invalid path')
    manifest_path.write_bytes(original)
    payload = saved / 'instance/upload-inbox/restore-check.bin'
    intact = payload.read_bytes()
    payload.write_bytes(b'X' + intact[1:])
    rejected(lambda: restore(saved, root / 'corrupt-restore'), 'checksum mismatch')
    assert not (root / 'corrupt-restore').exists()
    payload.write_bytes(intact)
    verify(saved)

    session = ExistingSession(restored, 4002)
    with patch('shared_launcher.running', return_value=True), patch('shared_launcher.port_busy', return_value=True):
        assert ensure_session(restored, 4002, 'rcpm-test', session) == '$42'
    assert all(call[0] not in ('new-session', 'kill-session') for call in session.calls)
    rejected(lambda: ensure_session(restored, 4002, 'rcpm-test', ExistingSession(source, 4002)), 'Cannot confirm ownership')
    class NoSession:
        def find(self, name): return None
        def run(self, *args): raise AssertionError('Must not spawn')
    with patch('shared_launcher.running', return_value=True):
        rejected(lambda: ensure_session(restored, 4002, 'rcpm-test', NoSession()), 'already running')
    with patch('shared_launcher.running', return_value=False), patch('shared_launcher.port_busy', return_value=True):
        rejected(lambda: ensure_session(restored, 4002, 'rcpm-test', NoSession()), 'occupied')

    # Boot the restored runtime, log in as a caller, and test live snapshot refusal.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    master, slave = pty.openpty()
    tty.setraw(slave)
    guest = subprocess.Popen([sys.executable, str(REPO / 'run_shared_trial.py'),
                             '--instance', str(restored), '--port', str(port)],
                            stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    local, remote = bytearray(), bytearray()
    caller = None
    def collect(duration):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            ready = select.select([master] + ([caller] if caller else []), [], [], .05)[0]
            if master in ready:
                local.extend(os.read(master, 8192))
            if caller and caller in ready:
                remote.extend(caller.recv(8192))
    try:
        deadline = time.monotonic() + 45
        while b'RCP/M modem ready.' not in local:
            assert time.monotonic() < deadline, bytes(local[-2000:])
            collect(.1)
        rejected(lambda: backup(restored, root / 'live-backup'), 'running')
        caller = socket.create_connection(('127.0.0.1', port), timeout=5)
        deadline = time.monotonic() + 20
        while b'A0:SYSTEM>' not in remote:
            assert time.monotonic() < deadline, bytes(remote[-2000:])
            caller.sendall(b'\r')
            collect(.4)
        assert b'R C P / M' in remote
        (root / 'restored-boot.log').write_bytes(local)
        (root / 'restored-caller.log').write_bytes(remote)
    finally:
        if caller:
            caller.close()
        guest.terminate()
        try:
            guest.wait(timeout=5)
        except subprocess.TimeoutExpired:
            guest.kill()
            guest.wait()
        os.close(master)
    result = dict(backup_files=len(data['files']), populated_source=str(source),
                  disk_and_data_hashes=True, inbox_restored=True, private_permissions=True,
                  sparse_archive=True, lock_refusal=True, corruption_refusal=True,
                  path_traversal_refusal=True, restore_overwrite_refusal=True,
                  session_reuse=True, foreign_session_refusal=True,
                  duplicate_guest_refusal=True, occupied_port_refusal=True,
                  restored_guest_boot=True, restored_caller_login=True,
                  real_tmux_attach='unverified: sandbox denies tmux server access')
    (root / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
