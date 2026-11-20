#!/usr/bin/env python3
"""Verify native host-file I/O is unavailable for both RCP/M transports."""
import argparse
import io
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tempfile
import tty

from check_modem_runtime import free_port, stop
from build_bye5 import wait_prompt


def run(source, runtime, tools):
    for mode in ('disabled', 'direct', 'ip232'):
        with tempfile.TemporaryDirectory(prefix='rcpm-host-boundary-') as temporary:
            work = Path(temporary)
            (work / 'disks').mkdir()
            (work / 'conf').mkdir()
            for kind in ('server', 'client'):
                (work / f'conf/net_{kind}.conf').write_text('# No legacy sockets.\n')
            disk = work / 'disks/drivea.dsk'
            shutil.copyfile(source / 'cpmsim/disks/library/cpm3-1.dsk', disk)
            subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                            str(disk), '0:PROFILE.SUB'], check=True)
            shutil.copyfile(Path(__file__).parent / 'guest/hostprobe.asm', work / 'hostprobe.asm')
            subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'hostprobe.asm'],
                           cwd=work, check=True, stdout=subprocess.DEVNULL)
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                            str(work / 'hostprobe.bin'), '0:HOSTPROB.COM'], check=True)
            original = b'HOST CONTENT MUST SURVIVE\n'
            (work / 'hostchk.txt').write_bytes(original)
            env = {key: value for key, value in os.environ.items()
                   if not key.startswith('RCPM_MODEM')}
            if mode != 'disabled':
                env.update(RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1',
                           RCPM_MODEM_PORT=str(free_port()))
            master, slave = pty.openpty()
            tty.setraw(slave)
            guest = None
            try:
                guest = subprocess.Popen([str(runtime)], cwd=work, env=env,
                                         stdin=slave, stdout=slave, stderr=slave)
                log = io.BytesIO()
                wait_prompt(master, b'A>', log)
                os.write(master, b'HOSTPROB\r')
                output = wait_prompt(master, b'A>', log)
                expected = b'ALLOWED' if mode == 'disabled' else b'DENIED'
                if b'INVALID FDC DRIVES REJECTED' not in output:
                    raise RuntimeError(f'{mode}: invalid FDC drive check failed: {output!r}')
                for operation in (b'OPEN', b'MAKE'):
                    if b'HOST ' + operation + b' ' + expected not in output:
                        raise RuntimeError(f'{mode}: unexpected host-file result: {output!r}')
                if (work / 'hostnew.txt').exists() != (mode == 'disabled'):
                    raise RuntimeError(f'{mode}: unexpected host-file creation')
                if (work / 'hostchk.txt').read_bytes() != original:
                    raise RuntimeError(f'{mode}: fixture content changed')
                print(f'PASS {mode}: native host OPEN/MAKE {expected.decode().lower()}; '
                      'all FDC drive values 16-255 rejected', flush=True)
            finally:
                if guest is not None:
                    stop(guest)
                os.close(master)
                os.close(slave)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    args = parser.parse_args()
    run(args.source.resolve(), args.runtime.resolve(), args.cpmtools.resolve())
