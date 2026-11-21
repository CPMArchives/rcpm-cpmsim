"""Shared-instance validation and exclusive maintenance locks."""
from contextlib import contextmanager
import fcntl
import json
import os
import shlex


def write_helpers(directory, installation, repository, port=4002):
    """Write host entry points without touching guest media."""
    command = shlex.join(['/usr/bin/env', 'python3', str(repository / 'shared_launcher.py'),
                          '--instance', str(installation), '--port', str(port)])
    for name, arguments in (('Start-RCPM.command', ''), ('Backup-RCPM.command', ' --backup')):
        helper = directory / name
        helper.write_text('#!/bin/zsh\nset -eu\nexec ' + command + arguments + ' "$@"\n')
        helper.chmod(0o755)


def validate(root):
    if not root.is_dir():
        raise ValueError('Shared installation not found: ' + str(root))
    data = json.loads((root / 'trial-build.json').read_text())
    if data.get('mode') != 'direct':
        raise ValueError('This launcher requires a direct-TCP shared installation')
    for drive in ('aijp' if data.get('upper_areas') else 'abijp'):
        if not (root / f'disks/drive{drive}.dsk').is_file():
            raise ValueError('Missing drive ' + drive.upper() + ': in ' + str(root))
    if not os.access(root / 'runtime/cpmsim', os.X_OK):
        raise ValueError('Shared cpmsim executable is missing')
    return data


@contextmanager
def lock(root, name, message):
    with (root / name).open('a+b') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError(message) from None
        yield stream


def running(root):
    try:
        with lock(root, '.console.lock', 'running'):
            return False
    except RuntimeError:
        return True
