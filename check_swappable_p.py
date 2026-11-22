#!/usr/bin/env python3
"""Qualify P:/J: swaps and NDSCAN in disposable CP/M media."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from backup_rcpm import copy_file
from check_release import Guest, free_port
from prepare_z3plus import configure_library
from build_mount_tools import build

ROOT = Path(__file__).resolve().parent


def run(a):
    out = a.output
    out.mkdir(parents=True, exist_ok=False)
    package = out / 'instance'
    shutil.copytree(a.package, package, copy_function=lambda s, d:
                    copy_file(Path(s), Path(d), Path(s).stat().st_mode & 0o777) and d)
    shutil.copy2(a.runtime, package / 'runtime/cpmsim')
    shutil.copy2(a.runtime.with_name(a.runtime.name + '.features.json'), package / 'runtime/cpmsim.features.json')
    for mode in ('direct', 'ip232'):
        shutil.copy2(a.builds / mode / 'BYEDRIV.COM', package / 'drivers' / mode / 'BYEDRIV.COM')
    tools = build(a.assembler, out / 'tools')

    def tool(name, *v):
        return subprocess.run([str(a.tools / name), *map(str, v)], check=True,
                              capture_output=True).stdout

    def put(image, fmt, user, name, data, approved=False):
        file = out / 'put.bin'
        file.write_bytes(data)
        tool('cpmrm', '-f', fmt, image, f'{user}:{name}')
        tool('cpmcp', '-f', fmt, image, file, f'{user}:{name}')
        if approved:
            tool('cpmchattr', '-f', fmt, image, '4', f'{user}:{name}')

    # Test-only viewer: print the actual resident entries, not scanner output.
    env = (ROOT / 'guest/ndscan.asm').read_text().split('ENVFIND:\n', 1)[1].split('SPACE:\n', 1)[0]
    viewer = ''' ORG 100H
 JP VIEW
CHAR:PUSH AF
 PUSH BC
 PUSH DE
 PUSH HL
 LD E,A
 LD C,2
 CALL 5
 POP HL
 POP DE
 POP BC
 POP AF
 RET
VIEW:CALL ENVFIND
 RET C
 LD A,(CAPACITY)
 LD B,A
 LD HL,(NDRPTR)
VLOOP:PUSH BC
 PUSH HL
 LD A,(HL)
 OR A
 JR Z,VNEXT
 ADD A,'A'-1
 CALL CHAR
 INC HL
 LD A,(HL)
 CP 10
 JR C,VNUM
 ADD A,7
VNUM:ADD A,'0'
 CALL CHAR
 LD A,':'
 CALL CHAR
 INC HL
 LD B,8
VNAME:LD A,(HL)
 CALL CHAR
 INC HL
 DJNZ VNAME
 LD A,13
 CALL CHAR
 LD A,10
 CALL CHAR
VNEXT:POP HL
 POP BC
 LD DE,18
 ADD HL,DE
 DJNZ VLOOP
 RET
ENVFIND:
''' + env + '''CAPACITY:DB 0
NDRPTR:DW 0
NDRBYTES:DW 0
NEXTENTRY:DW 0
STAGE:DB 0
SIGNATURE:DB 'Z3ENV',80H
 END
'''
    (out / 'ndview.asm').write_text(viewer)
    subprocess.run([str(a.assembler), '-fb', '-x', 'ndview.asm'], cwd=out, check=True)
    boot = package / 'disks/drivea.dsk'
    put(boot, 'ibm-3740', 0, 'NDVIEW.COM', (out / 'ndview.bin').read_bytes(), True)
    for name in tools:
        put(boot, 'ibm-3740', 0, name, (out / 'tools' / name).read_bytes(), True)
    library = configure_library(a.romwbw / 'Source/Images/d_z3plus/u0/Z3PLUS.LBR',
                                ('SIGM', 'CPMUG'),
                                ((9, 13, 'SYSUTLS'), (9, 14, 'HELP'), (9, 15, 'RBBS')))
    put(boot, 'ibm-3740', 0, 'Z3PLUS.LBR', library)
    for user, name in ((0, '-SIGM'), (1, '-CPMUG')):
        put(package / 'disks/drivep.dsk', 'z80pack-hdb', user, name, b'\x1a')
    archives = package / 'disks/library/archives'
    archives.mkdir(exist_ok=True)

    def image(name, entries):
        path = archives / (name + '.dsk')
        tool('mkfs.cpm', '-f', 'z80pack-hdb', path)
        with path.open('r+b') as stream:
            stream.truncate(536870912)
        for user, file in entries:
            put(path, 'z80pack-hdb', user, file, b'ARCHIVE-FIXTURE\r\n\x1a')
        return path

    image('ALPHA', [(u, '-ARC' + str(u)) for u in range(16)] + [(0, '-CATALOG.011')])
    image('BETA', [(4, '-BETA')])
    image('MULTI', [(0, '-ONE'), (0, '-TWO')])
    image('COLLIDE', [(0, '-SYSTEM')])
    shutil.copyfile(package / 'disks/library/GAMES.dsk', archives / 'SMALL.dsk')
    with (package / 'disks/library/BIG.dsk').open('wb') as stream:
        stream.truncate(536870912)
    # An unapproved local file must remain unapproved after directory scanning.
    put(archives / 'BETA.dsk', 'z80pack-hdb', 4, 'NOEXEC.COM', bytes([0x11,9,1,0x0e,9,0xcd,5,0,0xc9])+b'UNAPPROVED-RAN$')
    immutable = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [archives / 'ALPHA.dsk', archives / 'BETA.dsk']}
    guest = Guest(package, out / 'console', '--port', str(free_port()))
    result = {}
    def command(text, expect):
        reply = guest.command(text)
        assert expect in reply, (text, reply)
        return reply
    try:
        guest.wait(b'RCP/M modem ready.')
        # The launcher's port is explicit and can be read from guest arguments.
        port = int(guest.process.args[-1])
        guest.connect(port)
        command('NDSCAN P:', b'NDSCAN P: names updated.')
        command('MOUNT P: /L', b'P: <default>')
        command('MOUNT P: SMALL', b'Wrong image geometry')
        command('MOUNT P: /L', b'P: <default>')
        command('MOUNT BIG', b'Wrong image geometry')
        command('MOUNT P: ALPHA', b'NDSCAN P: names updated.')
        view = command('NDVIEW', b'PF:ARC15')
        assert all(('P'+format(u,'X')+':ARC'+str(u)).encode() in view for u in range(16))
        assert b'ID:SYSUTLS' in view and b'IE:HELP' in view and b'IF:RBBS' in view
        command('DIR ARC15:', b'-ARC15')
        # Named-directory command resolution proves the rebuilt NDR is usable.
        command('DIR P15:*.*', b'-ARC15')
        command('MOUNT GAMES', b'NDSCAN J: names updated.')
        command('MOUNT P: /L', b'P: ALPHA')
        command('MOUNT /L', b'J: GAMES')
        result['independent_mounts_all_16_users_and_chaining'] = True
        command('MOUNT P: BETA', b'NDSCAN P: names updated.')
        command('DIR BETA:', b'NOEXEC')
        view = command('NDVIEW', b'P4:BETA')
        assert b'ARC' not in view
        assert b'ID:SYSUTLS' in view and b'J0:GAMES' in view
        result['marker_replacement_clears_absent_names_preserves_other_drives'] = True
        command('NDSCAN P:', b'NDSCAN P: names updated.')
        # Verify execution stays denied even when a previously named DU is used.
        denied = command('P4:NOEXEC', b'A0:SYSTEM>')
        assert b'UNAPPROVED-RAN' not in denied
        result['caller_scan_and_unapproved_execution_unchanged'] = True
        command('MOUNT P: MULTI', b'Multiple -NAME markers')
        # Rejected metadata leaves the old table, but the media swap is reported.
        command('MOUNT P: COLLIDE', b'Duplicate directory name')
        command('MOUNT P: /DEFAULT', b'NDSCAN P: names updated.')
        command('DIR SIGM:SIGMV001.LBR', b'SIGMV001')
        command('DIR CPMUG:CPMUG093.LBR', b'CPMUG093')
        command('MOUNT /L', b'J: GAMES')
        view = command('NDVIEW', b'P0:SIGM')
        assert b'P1:CPMUG' in view and b'P4:BETA' not in view and b'J0:GAMES' in view
        # A caller denied one DU cannot mistake inaccessible markers for absence.
        start = len(guest.local)
        os.write(guest.master, b'\x02')
        guest.wait(b'[Remote off]', start=start)
        def private(text):
            start = len(guest.local)
            for byte in (text+'\r').encode():
                os.write(guest.master, bytes([byte])); guest.collect(.008)
            return guest.wait(b'A0:SYSTEM>', start=start)
        private('SYSUTLS:AUTH P15: NONE')
        start = len(guest.local); os.write(guest.master, b'\x02')
        guest.wait(b'[Remote on]', start=start)
        command('NDSCAN P:', b'read access to every user area')
        after = command('NDVIEW', b'P0:SIGM')
        assert b'P1:CPMUG' in after and b'J0:GAMES' in after
        start = len(guest.local); os.write(guest.master, b'\x02')
        guest.wait(b'[Remote off]', start=start)
        private('SYSUTLS:AUTH P15: INHERIT')
        start = len(guest.local); os.write(guest.master, b'\x02')
        guest.wait(b'[Remote on]', start=start)
        result['denied_user_area_aborts_scan_without_changing_names'] = True
        result['invalid_names_default_restore_other_drive_preserved'] = True
        for path, digest in immutable.items():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
        result['scanner_does_not_write_images'] = True
        guest.stop()
    finally:
        guest.close()
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('package', 'runtime', 'builds', 'tools', 'assembler', 'romwbw', 'output'):
        p.add_argument('--' + name, type=lambda s: Path(s).resolve(), required=True)
    run(p.parse_args())
