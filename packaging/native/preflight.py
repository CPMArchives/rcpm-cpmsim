#!/usr/bin/env python3
"""Read-only installation checks; does not open network endpoints or boot CP/M."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
manifest = json.loads((root / 'metadata/MANIFEST.json').read_text())
for path in root.rglob('*'):
    if path.is_symlink() or not (path.is_file() or path.is_dir()):
        raise SystemExit('Unexpected symlink/special file: ' + str(path))
expected_names = set(manifest['common']) | set(manifest['host']) | {'metadata/MANIFEST.json'}
actual_names = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
if expected_names != actual_names:
    raise SystemExit('Missing or unrecorded package files')
for section in ('common', 'host'):
    for name, expected in manifest[section].items():
        path = root / name
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(block)
        if h.hexdigest() != expected:
            raise SystemExit('Package checksum mismatch: ' + name)
# Reject the wrong architecture and missing loader/dependencies without booting.
subprocess.run([str(root / 'runtime/rcpm'), '--check'], check=True)
receipt = json.loads((root / 'metadata/TCPSER.json').read_text())
if hashlib.sha256((root / 'runtime/tcpser').read_bytes()).hexdigest() != receipt['sha256']:
    raise SystemExit('tcpser checksum mismatch')
header = (root / 'runtime/tcpser').read_bytes()[:20]
expected_machine = {'aarch64': 183, 'arm64': 183, 'x86_64': 62}.get(platform.machine())
if header[:4] != b'\x7fELF' or int.from_bytes(header[18:20], 'little') != expected_machine:
    raise SystemExit('Wrong tcpser ELF architecture')
print('Verified package manifests and tcpser build receipt on ' + platform.machine())
