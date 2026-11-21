#!/usr/bin/env python3
"""Reproduce the optional expanded GAMES image using its checked payload.

Usage: build_image.py BASE_GAMES COLLECTION TOOLS OUTPUT
COLLECTION is the extracted optional ZIP, with payload/ and manifest.json.
TOOLS contains cpmcp, cpmrm, cpmchattr and diskdefs from RCP/M.
The released input must match the recorded hash. No mounted image is edited.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

base, collection, tools, output = (Path(s).resolve() for s in sys.argv[1:])
manifest = json.loads((collection / 'manifest.json').read_text())
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(base) == manifest['base_sha256'], 'Unexpected base image'
assert not output.exists(), 'Refusing to overwrite an image'
env = dict(os.environ, DISKDEFS=str(tools / 'diskdefs'))
def tool(name, *args):
    return subprocess.check_output([str(tools / name), '-f', 'z80pack-hd',
                                    *map(str, args)], env=env)
with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
    image = Path(tmp) / 'GAMES.dsk'
    shutil.copyfile(base, image)
    tool('cpmchattr', image, 'mr', '0:README.TXT')
    tool('cpmrm', image, '0:README.TXT')
    for row in manifest.get('remove_files', []):
        name = f"{row['user']}:{row['file']}"
        tool('cpmchattr', image, 'mr', name)
        tool('cpmrm', image, name)
    # Terminal adaptation notes are intentionally replaced with the guide.
    if any(row['user'] == 3 and row['file'] == 'ANSI.TXT' for row in manifest['payload']):
        tool('cpmchattr', image, 'mr', '3:ANSI.TXT')
        tool('cpmrm', image, '3:ANSI.TXT')
    for row in manifest['payload']:
        source = (collection / row['payload']).resolve()
        assert source.is_relative_to(collection / 'payload'), 'Unsafe payload path'
        assert sha(source) == row['sha256'], row['payload']
        name = f"{row['user']}:{row['file']}"
        tool('cpmcp', image, source, name)
        if row['approved']:
            tool('cpmchattr', image, 'r4', name)
    # Erase deleted content from free blocks, keeping all allocated blocks intact.
    data = bytearray(image.read_bytes())
    used = set(range(16))
    for offset in range(0, 32768, 32):
        entry = data[offset:offset + 32]
        if entry[0] < 16:
            used.update(int.from_bytes(entry[n:n + 2], 'little')
                        for n in range(16, 32, 2) if entry[n:n + 2] != b'\0\0')
    for block in range(2040):
        if block not in used:
            data[block * 2048:(block + 1) * 2048] = bytes(2048)
    image.write_bytes(data)
    assert sha(image) == manifest['image_sha256'], 'Rebuilt image differs'
    shutil.copyfile(image, output)
print('Verified image:', output)
