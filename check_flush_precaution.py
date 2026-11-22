#!/usr/bin/env python3
"""Check pre-policy/pre-swap flush failures in a disposable real CP/M guest."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from backup_rcpm import copy_file
from check_release import Guest, free_port

ROOT = Path(__file__).resolve().parent


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    package = out / 'instance'
    shutil.copytree(args.package, package, copy_function=lambda a, b:
                    copy_file(Path(a), Path(b), Path(a).stat().st_mode & 0o777) and b)

    def tool(name, *values):
        return subprocess.run([str(args.tools / name), *map(str, values)],
                              check=True, capture_output=True).stdout

    def install(source, name, disk, fmt, user, fail=False):
        text = (ROOT / 'guest' / source).read_text()
        if fail:
            # Substitute only the BDOS entry point in this test executable.
            # Every call except function 48 reaches the real resident BDOS.
            text, count = re.subn(r'\b(CALL|JP)\s+BDOS\b', r'\1 TESTBDOS', text)
            assert count > 0
            hook = ('\nTESTBDOS:\n LD A,C\n CP 48\n JP NZ,5\n'
                    ' LD A,255\n RET\n')
            text, count = re.subn(r'^\s+END\s*$', hook + ' END\n', text,
                                 flags=re.MULTILINE)
            assert count == 1
        asm = out / (name + '.asm')
        asm.write_text(text)
        subprocess.run([str(args.assembler), '-fb', '-x', asm.name], cwd=out,
                       check=True, capture_output=True)
        tool('cpmrm', '-f', fmt, disk, f'{user}:{name}.COM')
        tool('cpmcp', '-f', fmt, disk, asm.with_suffix('.bin'), f'{user}:{name}.COM')
        tool('cpmchattr', '-f', fmt, disk, '4', f'{user}:{name}.COM')

    a = package / 'disks/drivea.dsk'
    i = package / 'disks/drivei.dsk'
    install('auth.asm', 'AUTH', i, 'z80pack-hd', 13)
    install('auth.asm', 'AUTHFAIL', i, 'z80pack-hd', 13, fail=True)
    install('mount.asm', 'MOUNT', a, 'ibm-3740', 0)
    install('mount.asm', 'MNTFAIL', a, 'ibm-3740', 0, fail=True)
    port = free_port()
    guest = Guest(package, out / 'console', '--port', str(port))

    def local(command, expected):
        start = len(guest.local)
        for byte in (command + '\r').encode():
            os.write(guest.master, bytes([byte]))
            guest.collect(.008)
        reply = guest.wait(b'A0:SYSTEM>', start=start).replace(b'\r', b'')
        assert expected in reply, (command, reply)
        return reply

    def permissions():
        reply = local('SYSUTLS:AUTH J:', b'Effective caller access')
        return next(line for line in reply.splitlines() if line.startswith(b'J:'))

    result = {}
    try:
        guest.wait(b'RCP/M modem ready.')
        guest.connect(port)
        start = len(guest.local)
        os.write(guest.master, b'\x02')
        guest.wait(b'[Remote off]', start=start)
        local('SYSUTLS:AUTH J: R', b'changed in memory')
        readonly = permissions()
        local('SYSUTLS:AUTH /SAVE=I13:READONLY.DAT /Y', b'Policy saved')
        local('SYSUTLS:AUTH J: RW', b'changed in memory')
        writable = permissions()
        assert writable != readonly
        local('SYSUTLS:AUTHFAIL J: R', b'Flush failed; live permissions unchanged.')
        assert permissions() == writable
        local('SYSUTLS:AUTHFAIL /LOAD=I13:READONLY.DAT',
              b'Flush failed; live permissions unchanged.')
        assert permissions() == writable
        result['failed_edit_and_load_preserve_live_policy'] = True
        # Cover per-DU overrides, inheritance, and successful policy loads.
        local('SYSUTLS:AUTH J3: RW', b'changed in memory')
        local('SYSUTLS:AUTH J3: R', b'changed in memory')
        local('SYSUTLS:AUTH J3: INHERIT', b'changed in memory')
        local('SYSUTLS:AUTH /LOAD=I13:READONLY.DAT', b'Policy loaded')
        assert permissions() == readonly
        result['normal_policy_transitions'] = True
        local('MOUNT GUIDES', b'Volume mounted on J:.')
        local('MNTFAIL GAMES', b'Flush failed. Mounted image unchanged.')
        local('MOUNT /L', b'J: GUIDES')
        result['failed_flush_preserves_mounted_volume'] = True
        local('MOUNT GAMES', b'Volume mounted on J:.')
        local('MOUNT /L', b'J: GAMES')
        local('DIR J1:ADV.COM', b'ADV')
        result['normal_swap_and_relog'] = True
        start = len(guest.local)
        os.write(guest.master, b'\x02')
        guest.wait(b'[Remote on]', start=start)
        assert b'Volume mounted on J:.' in guest.command('MOUNT GUIDES')
        assert b'J: GUIDES' in guest.command('MOUNT /L')
        result['caller_mount_with_default_readonly_policy'] = True
        guest.stop()
    finally:
        guest.close()
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'tools', 'assembler', 'output'):
        parser.add_argument('--' + name, type=lambda p: Path(p).resolve(), required=True)
    run(parser.parse_args())
