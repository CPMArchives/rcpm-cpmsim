#!/usr/bin/env python3
"""Prepare a new, private shared-machine trial without altering an installation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

from prepare_z3plus import prepare


def create(source, romwbw, runtime, builds, tools, output):
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Refusing to replace an existing trial: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    repository = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='.shared-trial-', dir=output.parent) as temporary:
        work = Path(temporary)
        trial = work / 'instance'
        for name in ('disks', 'conf', 'runtime', 'volumes', 'upload-staging', 'upload-inbox'):
            (trial / name).mkdir(parents=True, mode=0o700)
        for kind in ('server', 'client'):
            (trial / f'conf/net_{kind}.conf').write_text('# No legacy network devices.\n')
        def tool(name, *args):
            subprocess.run([str(tools / name), *map(str, args)], check=True)
        stock = work / 'stock.dsk'
        shutil.copyfile(source / 'cpmsim/disks/library/cpm3-1.dsk', stock)
        tool('cpmrm', '-T', 'raw', '-f', 'ibm-3740', stock, '0:PROFILE.SUB', '0:ED.COM', '0:DATE.COM')
        a = trial / 'disks/drivea.dsk'
        # The existing preparer locates cpmtools on PATH.
        previous_path = os.environ.get('PATH', '')
        try:
            os.environ['PATH'] = str(tools) + os.pathsep + previous_path
            prepare(romwbw / 'Source/Images', stock, a, ('SIGM', 'CPMUG'),
                    'A0:PATH /C A0;A:GET CONSOLE;A:BYE')
        finally:
            os.environ['PATH'] = previous_path
        tool('cpmrm', '-T', 'raw', '-f', 'ibm-3740', a, '0:BYE.COM')
        for name in ('BYE.COM', 'BYEDRIV.COM', 'BYEBYE.COM'):
            tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', a, builds / 'direct' / name, '0:' + name)
        for name in ('upload', 'message', 'ysend', 'mount'):
            shutil.copyfile(repository / f'guest/{name}.asm', work / f'{name}.asm')
            subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', f'{name}.asm'],
                           cwd=work, check=True, stdout=subprocess.DEVNULL)
            tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', a, work / f'{name}.bin', f'0:{name.upper()}.COM')
        shutil.copyfile(source / 'cpmsim/disks/library/cpm3-2.dsk', trial / 'disks/driveb.dsk')
        (trial / 'disks/driveb.dsk').chmod(0o444)
        for drive in ('i', 'j'):
            image = trial / f'disks/drive{drive}.dsk'
            tool('mkfs.cpm', '-f', 'z80pack-hd', image)
            # Raw mkfs initializes the directory only. MOUNT validates the
            # complete geometry, so extend the sparse image to its full size.
            with image.open('r+b') as disk:
                disk.truncate(255 * 128 * 128)
        j = trial / 'disks/drivej.dsk'
        for name, content in (
            ('HELLO.TXT', b'Hello from the shared RCP/M trial.\r\n'),
            ('VOLUME.TXT', b'DEMO volume mounted on J:\r\n'),
            ('BINARY.BIN', bytes(range(256)) * 8),
        ):
            fixture = work / name
            fixture.write_bytes(content)
            tool('cpmcp', '-T', 'raw', '-f', 'z80pack-hd', j, fixture, '0:' + name)
        shutil.copyfile(j, trial / 'volumes/DEMO.dsk')
        j.chmod(0o444)
        (trial / 'volumes/DEMO.dsk').chmod(0o444)
        # Empty 512-MiB archive: initialize its directory and leave data sparse.
        with (trial / 'disks/drivep.dsk').open('xb') as disk:
            disk.write(b'\xe5' * (8192 * 32))
            disk.truncate(512 * 1024**2)
        (trial / 'disks/drivep.dsk').chmod(0o444)
        shutil.copy2(runtime, trial / 'runtime/cpmsim')
        command = ('#!/bin/zsh\nset -eu\nexec python3 '
                   + shlex.quote(str(repository / 'run_shared_trial.py'))
                   + ' --instance ' + shlex.quote(str(output)) + '\n')
        (trial / 'Start-RCPM.command').write_text(command)
        (trial / 'Start-RCPM.command').chmod(0o755)
        (trial / 'README.txt').write_text(
            'Private shared-machine trial: raw TCP 127.0.0.1:4001.\n'
            'Start-RCPM.command runs the one CP/M instance in the local terminal.\n'
            'Connect SyncTERM to port 4001; local and caller share that guest.\n'
            'J: has HELLO.TXT and BINARY.BIN; MOUNT /L lists DEMO.\n'
            'P: is empty, with P0:SIGM and P1:CPMUG names reserved.\n'
            'I0:WORK is cleared at startup and after calls.\n'
            'Completed uploads/messages stay in upload-inbox on the host.\n'
            'For YMODEM download: YSEND J:HELLO.TXT; upload: UPLOAD /Y.\n'
            'BYE logs a caller off. Locally, Ctrl-C between calls opens the BYE menu;\n'
            'press Return for local CP/M, then BYEBYE to stop the trial.\n'
            'In tmux, Ctrl-B Ctrl-B sends BYE one literal Ctrl-B for blank/unblank.\n'
            'Caller security settings and privileged J:/P: maintenance are unfinished.\n'
            'J:/P: are read-only in this trial; do not expose it to the Internet.\n')
        files = {}
        for path in (a, trial / 'runtime/cpmsim'):
            files[str(path.relative_to(trial))] = hashlib.sha256(path.read_bytes()).hexdigest()
        (trial / 'trial-build.json').write_text(json.dumps(dict(
            source=str(source), romwbw=str(romwbw), builds=str(builds), hashes=files,
            mode='direct', host='127.0.0.1', port=4001), indent=2) + '\n')
        trial.rename(output)
    print(f'Prepared {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--romwbw', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--builds', type=Path, default=Path('build/bye5'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    create(*(getattr(args, name).expanduser().resolve()
             for name in ('source', 'romwbw', 'runtime', 'builds', 'cpmtools', 'output')))
