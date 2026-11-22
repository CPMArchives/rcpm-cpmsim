#!/usr/bin/env python3
"""Assemble MOUNT.COM and standalone NDSCAN.COM with native z80asm."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def build(assembler, output):
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parent
    rows = {}
    for name in ('mount', 'ndscan'):
        source = output / (name + '.asm')
        shutil.copy2(root / 'guest' / source.name, source)
        subprocess.run([str(assembler), '-fb', '-x', source.name], cwd=output, check=True)
        target = output / (name.upper() + '.COM')
        source.with_suffix('.bin').replace(target)
        rows[target.name] = {'bytes': target.stat().st_size,
                             'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
    (output / 'BUILD.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--assembler', type=lambda s: Path(s).resolve(), required=True)
    p.add_argument('--output', type=lambda s: Path(s).resolve(), required=True)
    a = p.parse_args()
    print(json.dumps(build(a.assembler, a.output), indent=2))
