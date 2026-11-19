#!/usr/bin/env python3
"""Build configured BYE5 under CP/M 3 using the supplied RMAC/LINK/GENCOM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shutil
import subprocess
import time
import tty


def wait_prompt(fd, prompt, log, timeout=45):
    data = bytearray()
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if select.select([fd], [], [], .1)[0]:
            part = os.read(fd, 8192)
            log.write(part)
            log.flush()
            data.extend(part)
            if prompt in data:
                return bytes(data)
    raise RuntimeError(f'CP/M command timeout; received {bytes(data[-1500:])!r}')


def run(source, runtime, cpmtools, sources, output):
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'machine'
    work.mkdir(exist_ok=True)
    (work / 'disks').mkdir(exist_ok=True)
    (work / 'conf').mkdir(exist_ok=True)
    for kind in ('server', 'client'):
        (work / f'conf/net_{kind}.conf').write_text('# Isolated build machine.\n')
    for drive, image in (('a', 'cpm3-1.dsk'), ('b', 'cpm3-2.dsk')):
        shutil.copyfile(source / 'cpmsim/disks/library' / image, work / f'disks/drive{drive}.dsk')
    a = work / 'disks/drivea.dsk'
    i = work / 'disks/drivei.dsk'
    def tool(name, *args):
        subprocess.run([str(cpmtools / name), *map(str, args)], check=True)
    tool('cpmrm', '-T', 'raw', '-f', 'ibm-3740', a, '0:PROFILE.SUB')
    tool('mkfs.cpm', '-f', 'z80pack-hd', i)
    for file in sources.glob('*.ASM'):
        tool('cpmcp', '-T', 'raw', '-f', 'z80pack-hd', i, file, '0:' + file.name)
    master, slave = pty.openpty()
    tty.setraw(slave)
    env = {k:v for k,v in os.environ.items() if not k.startswith('RCPM_MODEM')}
    guest = subprocess.Popen([str(runtime)], cwd=work, env=env,
                             stdin=slave, stdout=slave, stderr=slave)
    try:
        with (output / 'build.log').open('wb') as log:
            wait_prompt(master, b'A>', log)
            os.write(master, b'I:\r')
            wait_prompt(master, b'I>', log)
            commands = [
                'B:RMAC B5ENTRY $PZ SZ', 'B:LINK B5ENTRY[NR]',
                'B:RMAC B5DRIVER $PZ SZ', 'B:LINK B5DRIVER[NR]',
                'B:RMAC BYEDIR $PZ SZ', 'B:LINK BYEDIR[OP,NR]',
                'A:RENAME BYEDIR.RSX=BYEDIR.PRL',
                'A:PIP DIRDRIV.COM=B5DRIVER.COM', 'A:GENCOM DIRDRIV BYEDIR',
                'B:RMAC BYEMDM $PZ SZ', 'B:LINK BYEMDM[OP,NR]',
                'A:RENAME BYEMDM.RSX=BYEMDM.PRL',
                'A:PIP MDMDRIV.COM=B5DRIVER.COM',
                'A:GENCOM MDMDRIV BYEMDM',
            ]
            for command in commands:
                print(command, flush=True)
                os.write(master, command.encode() + b'\r')
                result = wait_prompt(master, b'I>', log)
                if any(error in result.upper() for error in
                       (b'ERROR', b'NO FILE', b'NOT FOUND', b'UNDEFINED')):
                    raise RuntimeError(result.decode(errors='replace'))
    finally:
        guest.terminate()
        try:
            guest.wait(timeout=3)
        except subprocess.TimeoutExpired:
            guest.kill()
            guest.wait()
        os.close(master)
        os.close(slave)
    for mode, driver in (('direct', 'DIRDRIV.COM'), ('ip232', 'MDMDRIV.COM')):
        target = output / mode
        target.mkdir(exist_ok=True)
        for name, filename in (('B5ENTRY.COM', 'BYE.COM'), (driver, 'BYEDRIV.COM')):
            tool('cpmcp', '-T', 'raw', '-f', 'z80pack-hd', i, '0:' + name, target / filename)
    hashes = []
    for path in sorted(sources.glob('*.ASM')) + sorted(output.glob('*/*.COM')):
        hashes.append(dict(path=str(path.relative_to(sources if path.parent == sources else output)),
                           bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (output / 'build-result.json').write_text(json.dumps(dict(
        commands=commands, runtime_sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
        files=hashes), indent=2) + '\n')
    print(f'Built both BYE5 configurations in {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--sources', type=Path, default=Path('build/bye5/sources'))
    parser.add_argument('--output', type=Path, default=Path('build/bye5'))
    a = parser.parse_args()
    run(a.source.resolve(), a.runtime.resolve(), a.cpmtools.resolve(),
        a.sources.resolve(), a.output.resolve())
