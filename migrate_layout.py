#!/usr/bin/env python3
"""Reorganize a stopped macOS installation with matching rebuilt runtimes."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil

MOVES = {
    'volumes': 'disks/library',
    'archives': 'disks/library/archives',
    'offline': 'disks/library/offline',
    'upload-inbox': 'uploads/inbox',
    'upload-staging': 'uploads/staging',
    'NOTICES': 'docs/NOTICES',
    'NOTES': 'docs/NOTES',
}
for name in ('INSTALLATION.DOC', 'SYSOP-GUIDE.DOC', 'DISK-IMAGES.DOC',
             'DISTRIBUTION-STATUS.DOC', 'RELEASE-NOTES.md'):
    MOVES[name] = 'docs/' + name
for name in ('MANIFEST.json', 'VOLUMES.json', 'DEVELOPMENT-MEDIA.json',
             'BUILD-HOST.json', 'ARCHIVE.sha256'):
    MOVES[name] = 'metadata/' + name


def relocated(name):
    for old, new in MOVES.items():
        if name == old or name.startswith(old + '/'):
            return new + name[len(old):]
    return name


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def migrate(root, runtime):
    root, runtime = root.resolve(), runtime.resolve()
    if not (root / 'disks/drivea.dsk').is_file():
        raise ValueError('Not an RCP/M installation')
    if not (root / 'volumes').is_dir():
        raise ValueError('Expected the original volumes/ layout; refusing a second migration')
    required = ('rcpm', 'cpmsim', 'cpmsim.features.json')
    for name in required:
        if not (runtime / name).is_file():
            raise ValueError('Missing rebuilt runtime: ' + name)
    receipt = json.loads((runtime / 'cpmsim.features.json').read_text())
    if receipt.get('installation_layout') != 2:
        raise ValueError('Rebuild the emulator for installation layout 2 before migration')
    if receipt['sha256'] != sha(runtime / 'cpmsim'):
        raise ValueError('Runtime feature receipt hash mismatch')
    backup = root / 'state/layout-before-reorg'
    if backup.exists():
        raise ValueError('Previous layout backup already exists')
    for old, new in MOVES.items():
        if (root / old).exists() and (root / new).exists():
            raise ValueError('Destination already exists: ' + new)
    # The launcher retains this lock while cpmsim is running. Do not migrate
    # beneath an existing process, even if it currently has no caller.
    with (root / '.console.lock').open('a+b') as lease:
        try:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('RCP/M is running; stop with SYSUTLS:BYEBYE before migration') from None
        watched = {str(p.relative_to(root)): sha(p) for folder in ('disks', 'volumes', 'archives', 'offline')
                   for p in (root / folder).rglob('*.dsk')}
        for name in ('SYSOP.DOC', 'state/initialized', 'RCPM.CONF'):
            if (root / name).is_file():
                watched[name] = sha(root / name)
        backup.mkdir(parents=True, mode=0o700)
        shutil.copy2(root / 'MANIFEST.json', backup / 'MANIFEST.json')
        for name in required:
            if (root / 'runtime' / name).exists():
                shutil.copy2(root / 'runtime' / name, backup / name)
        moved, replaced = [], []
        try:
            for old, new in MOVES.items():
                source, target = root / old, root / new
                if source.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    source.rename(target)
                    moved.append((old, new))
            # Rewrite operator references while preserving local document text.
            for path in [root / 'README.txt', *list((root / 'docs').glob('*.DOC')),
                         *list((root / 'docs').glob('*.md')), root / 'source/BUILDING.DOC',
                         root / 'disks/library/offline/README.txt']:
                if not path.is_file():
                    continue
                text = path.read_text()
                import re
                for old, new in MOVES.items():
                    ending = r'(?=/)' if old in ('volumes', 'archives', 'offline', 'upload-inbox', 'upload-staging') else r'(?=/|\b)'
                    text = re.sub(r'(?<![\w/-])' + re.escape(old) + ending, new, text)
                if text != path.read_text():
                    saved = backup / 'documents' / path.relative_to(root)
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, saved)
                    replaced.append((path, saved))
                    path.write_text(text)
            for name in required:
                target = root / 'runtime' / name
                staged = target.with_name(name + '.new')
                shutil.copy2(runtime / name, staged)
                os.replace(staged, target)
            for name, digest in watched.items():
                if sha(root / relocated(name)) != digest:
                    raise ValueError('Disk or operator state changed: ' + name)
            manifest_path = root / 'metadata/MANIFEST.json'
            manifest = json.loads(manifest_path.read_text())
            for section in ('common', 'host'):
                manifest[section] = {relocated(name): sha(root / relocated(name))
                                     for name in manifest.get(section, {})}
            manifest['installation_layout'] = 2
            manifest['status'] = 'locally-reorganized-runtime-rebuilt'
            manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
            (backup / 'migration.json').write_text(json.dumps(dict(
                moves=moved, preserved_sha256=watched, runtime_sha256={
                    name: sha(root / 'runtime' / name) for name in required}), indent=2) + '\n')
        except BaseException:
            for path, saved in reversed(replaced):
                shutil.copy2(saved, path)
            for name in required:
                if (backup / name).exists():
                    shutil.copy2(backup / name, root / 'runtime' / name)
            for old, new in reversed(moved):
                (root / new).rename(root / old)
            shutil.copy2(backup / 'MANIFEST.json', root / 'MANIFEST.json')
            raise
    print('Reorganized:', root)
    print('Disk images, credentials, configuration and initialization state verified unchanged.')
    print('Previous runtime and migration receipt:', backup)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installation', type=Path)
    parser.add_argument('--runtime', type=Path, required=True)
    args = parser.parse_args()
    migrate(args.installation, args.runtime)
