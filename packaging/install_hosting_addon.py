#!/usr/bin/env python3
"""Explicit optional hosting installation using a separate pristine base package."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def validate(addon, package):
    receipt = json.loads((addon / 'metadata/ADDON.json').read_text())
    expected = receipt['files']
    actual = set()
    for p in addon.rglob('*'):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError('Unexpected add-on entry: ' + str(p))
        if p.is_file():
            actual.add(p.relative_to(addon).as_posix())
    if actual != set(expected) | {'metadata/ADDON.json'}:
        raise ValueError('Missing or unrecorded add-on files')
    for name, checksum in expected.items():
        if name.startswith('/') or '..' in Path(name).parts or digest(addon / name) != checksum:
            raise ValueError('Add-on checksum mismatch: ' + name)
    base = json.loads((package / 'metadata/MANIFEST.json').read_text())
    if base['platform'] != receipt['platform']:
        raise ValueError('Add-on and standard package architectures differ')
    for name, checksum in receipt['base_runtime_media_sha256'].items():
        if digest(package / name) != checksum:
            raise ValueError('Incompatible standard package: ' + name)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True,
                   help='Freshly unpacked matching standard RCP/M directory')
    actions = p.add_mutually_exclusive_group(required=True)
    actions.add_argument('--check', action='store_true')
    actions.add_argument('--install', action='store_true')
    args = p.parse_args()
    addon = Path(__file__).resolve().parent
    package = args.package.resolve()
    validate(addon, package)
    env = dict(os.environ, RCPM_PACKAGE_ROOT=str(package))
    subprocess.run(['sh', str(addon / 'service/Install-Service.sh'),
                    '--install' if args.install else '--check'], env=env, check=True)


if __name__ == '__main__':
    main()
