#!/usr/bin/env python3
"""Back up a stopped shared RCP/M installation; restore into a new directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import stat
import tempfile

from shared_instance import lock, validate, write_helpers

REPO = Path(__file__).resolve().parent
EXCLUDED = {'backups', '.console.lock', '.launch.lock'}
ZERO = bytes(1024 * 1024)


def copy_file(source, target, mode):
    """Copy with SHA256 and sparse zero runs, including on non-APFS hosts."""
    before = source.stat()
    digest = hashlib.sha256()
    size = 0
    with source.open('rb') as incoming, target.open('xb') as outgoing:
        while block := incoming.read(len(ZERO)):
            digest.update(block)
            size += len(block)
            if block == ZERO[:len(block)]:
                outgoing.seek(len(block), 1)
            else:
                outgoing.write(block)
        outgoing.truncate(size)
        outgoing.flush()
        os.fsync(outgoing.fileno())
        os.fchmod(outgoing.fileno(), mode)
    after = source.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Source changed while copying: ' + str(source))
    return size, digest.hexdigest()


def backup(root, output, port=4002):
    root, output = root.resolve(), output.resolve()
    if not 1 <= port <= 65535:
        raise ValueError('Listener port must be 1-65535')
    validate(root)
    if output == root or root in output.parents:
        raise ValueError('Put backups outside the running installation directory')
    if output.exists():
        raise FileExistsError('Refusing to replace an existing backup: ' + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with lock(root, '.launch.lock', 'Another launch or backup is in progress'):
        with lock(root, '.console.lock', 'RCP/M is running. Stop it with SYSUTLS:BYEBYE before backing up.'):
            with tempfile.TemporaryDirectory(prefix='.rcpm-backup-', dir=output.parent) as temporary:
                stage = Path(temporary) / 'backup'
                payload = stage / 'instance'
                payload.mkdir(parents=True, mode=0o700)
                files, directories = [], []
                def visit(directory):
                    for path in sorted(directory.iterdir()):
                        relative = path.relative_to(root)
                        if relative.parts[0] in EXCLUDED:
                            continue
                        info = path.lstat()
                        mode = stat.S_IMODE(info.st_mode) & 0o777
                        target = payload / relative
                        if stat.S_ISLNK(info.st_mode):
                            raise ValueError('Backup requires owned files, not symlinks: ' + str(relative))
                        if stat.S_ISDIR(info.st_mode):
                            target.mkdir(mode=0o700)
                            directories.append(dict(path=relative.as_posix(), mode=mode))
                            visit(path)
                        elif stat.S_ISREG(info.st_mode):
                            size, sha = copy_file(path, target, mode)
                            files.append(dict(path=relative.as_posix(), mode=mode, bytes=size, sha256=sha))
                        else:
                            raise ValueError('Unsupported file in installation: ' + str(relative))
                visit(root)
                manifest = dict(format='rcpm-shared-backup-1',
                    created_utc=datetime.now(timezone.utc).isoformat(),
                    original_instance=str(root), port=port, files=files, directories=directories)
                (stage / 'backup.json').write_text(json.dumps(manifest, indent=2) + '\n')
                (stage / 'backup.json').chmod(0o600)
                # Detect incomplete or corrupt copies before publishing a backup.
                verify(stage)
                stage.rename(output)
    return output


def relative_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or path.as_posix() != value or value == '.':
        raise ValueError('Invalid path in backup manifest')
    return Path(*path.parts)


def manifest_at(backup):
    manifest = json.loads((backup / 'backup.json').read_text())
    if manifest.get('format') != 'rcpm-shared-backup-1':
        raise ValueError('Unrecognized RCP/M backup format')
    origin = manifest.get('original_instance')
    if not isinstance(origin, str) or not Path(origin).is_absolute():
        raise ValueError('Invalid original installation path')
    port = manifest.get('port')
    if not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError('Invalid backup listener port')
    for entry in manifest['files']:
        if (not isinstance(entry['bytes'], int) or entry['bytes'] < 0
                or not isinstance(entry['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            raise ValueError('Invalid backup file size or checksum')
    seen = set()
    for entry in manifest['directories'] + manifest['files']:
        path = relative_path(entry['path'])
        if path in seen:
            raise ValueError('Duplicate path in backup manifest')
        seen.add(path)
        mode = entry['mode']
        if not isinstance(mode, int) or not 0 <= mode <= 0o777:
            raise ValueError('Invalid file permissions in backup')
        candidate = backup / 'instance'
        for part in path.parts:
            candidate /= part
            if candidate.is_symlink():
                raise ValueError('Backup payload contains a symlink')
    return manifest


def verify(backup):
    backup = backup.resolve()
    if (backup / 'instance').is_symlink():
        raise ValueError('Backup payload must not be a symlink')
    manifest = manifest_at(backup)
    for entry in manifest['directories']:
        if not (backup / 'instance' / relative_path(entry['path'])).is_dir():
            raise ValueError('Backup directory missing: ' + entry['path'])
    for entry in manifest['files']:
        path = backup / 'instance' / relative_path(entry['path'])
        if not path.is_file() or path.stat().st_size != entry['bytes']:
            raise ValueError('Backup file missing or wrong size: ' + entry['path'])
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            while block := stream.read(len(ZERO)):
                digest.update(block)
        if digest.hexdigest() != entry['sha256']:
            raise ValueError('Backup checksum mismatch: ' + entry['path'])
    return manifest


def restore(backup_path, output):
    backup_path, output = backup_path.resolve(), output.resolve()
    if output.exists():
        raise FileExistsError('Restore requires a new directory: ' + str(output))
    if output == backup_path or backup_path in output.parents:
        raise ValueError('Restore outside the backup directory')
    manifest = verify(backup_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.rcpm-restore-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'instance'
        stage.mkdir(mode=0o700)
        for entry in sorted(manifest['directories'], key=lambda row: len(relative_path(row['path']).parts)):
            (stage / relative_path(entry['path'])).mkdir(mode=0o700)
        for entry in manifest['files']:
            path = relative_path(entry['path'])
            size, sha = copy_file(backup_path / 'instance' / path, stage / path, entry['mode'])
            if (size, sha) != (entry['bytes'], entry['sha256']):
                raise ValueError('Backup changed during restore: ' + entry['path'])
        # Host helpers must target the restored installation, not its source.
        old = manifest['original_instance'].encode()
        for helper in stage.glob('*.command'):
            data = helper.read_bytes()
            if old in data:
                helper.write_bytes(data.replace(old, str(output).encode()))
        port = int(manifest.get('port', 4002))
        if not 1 <= port <= 65535:
            raise ValueError('Invalid restored listener port')
        write_helpers(stage, output, REPO, port)
        data = json.loads((stage / 'trial-build.json').read_text())
        # These rollback paths point to history deliberately excluded above.
        for key in ('boot_backup', 'caller_tools_backup'):
            data.pop(key, None)
        data['restored_from'] = str(backup_path)
        (stage / 'trial-build.json').write_text(json.dumps(data, indent=2) + '\n')
        validate(stage)
        for entry in sorted(manifest['directories'], key=lambda row: len(relative_path(row['path']).parts), reverse=True):
            (stage / relative_path(entry['path'])).chmod(entry['mode'])
        stage.rename(output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    save = sub.add_parser('backup')
    save.add_argument('--instance', type=Path, required=True)
    save.add_argument('--output', type=Path, required=True)
    save.add_argument('--port', type=int, default=4002)
    read = sub.add_parser('verify')
    read.add_argument('backup', type=Path)
    load = sub.add_parser('restore')
    load.add_argument('backup', type=Path)
    load.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'backup':
            print('Backup verified:', backup(args.instance, args.output, args.port))
        elif args.action == 'verify':
            result = verify(args.backup)
            print('Backup verified:', len(result['files']), 'files')
        else:
            print('Restored:', restore(args.backup, args.output))
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
