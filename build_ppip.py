#!/usr/bin/env python3
"""Build preserved PPIP 1.8 for Z3PLUS, without foreign timestamp extensions."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import shutil
import subprocess
import tty
import urllib.request

from build_bye5 import wait_prompt
from check_modem_runtime import stop

REPO = Path(__file__).resolve().parent


def build(source, runtime, tools, output, cache, fetch=False):
    if output.exists():
        raise FileExistsError(output)
    rows = json.loads((REPO / 'docs/ppip18-reference-sources.json').read_text())
    def obtain(row):
        path = cache / row['path']
        if not path.exists() and fetch:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(urllib.request.urlopen(row['url'], timeout=30).read())
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Missing or changed PPIP reference: ' + str(path))
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(obtain, rows))
    output.mkdir(parents=True)
    machine = output / 'machine'
    (machine / 'disks').mkdir(parents=True)
    (machine / 'conf').mkdir()
    for kind in ('server', 'client'):
        (machine / f'conf/net_{kind}.conf').write_text('# Isolated PPIP build.\n')
    for drive, name in (('a', 'cpm3-1.dsk'), ('b', 'cpm3-2.dsk')):
        shutil.copyfile(source / 'cpmsim/disks/library' / name, machine / f'disks/drive{drive}.dsk')
    def tool(name, *args):
        subprocess.run([str(tools / name), *map(str, args)], check=True)
    tool('cpmrm', '-f', 'ibm-3740', machine / 'disks/drivea.dsk', '0:PROFILE.SUB')
    image = machine / 'disks/drivei.dsk'
    tool('mkfs.cpm', '-f', 'z80pack-hd', image)
    for path in cache.glob('*.z80.txt'):
        text = path.read_text()
        name = path.name.removesuffix('.txt').upper()
        if name == 'PPIP18.Z80':
            text, count = re.subn(r'(?m)^Z80DOS\s+EQU\s+YES', 'Z80DOS EQU NO', text)
            if count != 1 or not re.search(r'(?m)^DATESTAMP EQU\s+NO', text):
                raise ValueError('Unexpected PPIP timestamp configuration')
            text = text.replace(';\tASEG', '\tASEG')
            name = 'PPIP18.MAC'
        target = output / name
        target.write_bytes(text.replace('\n', '\r\n').encode() + b'\x1a')
        tool('cpmcp', '-f', 'z80pack-hd', image, target, '0:' + name)
    master, slave = pty.openpty()
    tty.setraw(slave)
    env = {k: v for k, v in os.environ.items() if not k.startswith('RCPM_MODEM')}
    guest = subprocess.Popen([str(runtime)], cwd=machine, env=env,
                             stdin=slave, stdout=slave, stderr=slave)
    commands = ('I:', 'B:M80 =PPIP18', 'B:L80 PPIP18,PPIP/N/E')
    try:
        with (output / 'build.log').open('wb') as log:
            wait_prompt(master, b'A>', log)
            for command in commands:
                os.write(master, command.encode() + b'\r')
                result = wait_prompt(master, b'I>', log)
                checked = result.upper().replace(b'NO FATAL ERROR(S)', b'')
                if any(word in checked for word in (b'ERROR', b'UNDEFINED', b'NO FILE')):
                    raise RuntimeError(result.decode(errors='replace'))
    finally:
        stop(guest)
        os.close(master)
        os.close(slave)
    target = output / 'PPIP.COM'
    tool('cpmcp', '-f', 'z80pack-hd', image, '0:PPIP.COM', target)
    shutil.copyfile(cache / 'ppip.doc.txt', output / 'PPIP.DOC')
    (output / 'build-result.json').write_text(json.dumps(dict(
        program='PPIP 1.8', zcpr3=True, datestamper=False, z80dos=False,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(), commands=commands,
        runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
        toolchain_disks={name: hashlib.sha256((source / 'cpmsim/disks/library' / name).read_bytes()).hexdigest()
                         for name in ('cpm3-1.dsk', 'cpm3-2.dsk')},
        sources=rows), indent=2) + '\n')
    print('Built', target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--output', type=Path, default=Path('build/ppip18'))
    parser.add_argument('--cache', type=Path, default=Path('build/ztools/ppip18'))
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    build(*(getattr(args, name).resolve() for name in ('source', 'runtime', 'cpmtools', 'output', 'cache')), args.fetch)
