#!/usr/bin/env python3
"""Qualify native approval/revocation and actual caller program loads."""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from check_bye_speed import prepare
from check_release import Guest, free_port

REPO = Path(__file__).resolve().parent
MARKER = b'CALLER-APPROVAL-CODE-RAN'


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    p = args.output / 'instance'
    prepare(args.package, p, args.builds, args.runtime)
    shutil.copy2(args.launcher, p / 'runtime/rcpm')
    tools = REPO / 'build/release-tools/bin'
    program = args.output / 'fixture.com'
    program.write_bytes(bytes([0x11, 9, 1, 0x0e, 9, 0xcd, 5, 0, 0xc9]) + MARKER + b'\r\n$')
    image = p / 'volumes/GAMES.dsk'
    image.chmod(0o600)
    def tool(name, *values):
        return subprocess.run([str(tools/name), *map(str, values)], check=True, capture_output=True)
    for name in ('DEMO', 'SYSDEMO', 'UNMARKED', 'F4ONLY', 'ROONLY'):
        tool('cpmcp', '-f', 'z80pack-hd', image, program, '9:' + name + '.COM')
    for name, attr in (('F4ONLY','4'), ('ROONLY','r')):
        tool('cpmchattr', '-f', 'z80pack-hd', image, attr, '9:' + name + '.COM')
    for disk, fmt, name in (('i','z80pack-hd','1:DEMO.COM'), ('a','ibm-3740','1:DEMO.COM')):
        target = p / f'disks/drive{disk}.dsk'
        tool('cpmcp', '-f', fmt, target, program, name)
        tool('cpmchattr', '-f', fmt, target, 'r4', name)
    image.chmod(0o444)
    # A trusted fixture attempts a load with forged FCB approval bits, using a
    # non-default DMA. Actual directory attributes must win, and DMA must survive.
    asm = ''' ORG 100H
 LD E,9
 LD C,32
 CALL 5
 LD DE,300H
 LD C,26
 CALL 5
 LD DE,FCB
 LD C,59
 CALL 5
 CP 255
 JR NZ,BAD
 LD C,49
 LD DE,SCB
 CALL 5
 LD A,L
 OR A
 JR NZ,BAD
 LD A,H
 CP 3
 JR NZ,BAD
 LD HL,GOOD
 JR DONE
BAD: LD HL,ERROR
DONE: PUSH HL
 LD C,32
 LD E,0
 CALL 5
 LD C,26
 LD DE,80H
 CALL 5
 POP DE
 LD C,9
 CALL 5
 RET
SCB: DB 60,0,0,0
FCB: DB 10,'DEM',0CFH,'    ',0C3H,'OM'
 DS 24
GOOD: DB 'FORGED-FLAGS-REJECTED-DMA-OK','$'
ERROR: DB 'FORGED-FLAGS-OR-DMA-FAILED','$'
'''
    (args.output/'forged.asm').write_text(asm)
    subprocess.run([str(args.source/'z80asm/z80asm'),'-fb','-x','forged.asm'],
                   cwd=args.output, check=True, capture_output=True)
    a = p/'disks/drivea.dsk'
    tool('cpmrm','-f','ibm-3740',a,'0:HELP.COM')
    tool('cpmcp','-f','ibm-3740',a,args.output/'forged.bin','0:HELP.COM')
    def native(*words, success=True):
        r = subprocess.run([str(p/'Start-RCPM.command'), *words], capture_output=True)
        if (r.returncode == 0) != success:
            raise AssertionError((words, r.stdout[-500:], r.stderr))
        return r
    unchanged = hashlib.sha256(image.read_bytes()).digest()
    native('--caller-allow', 'I:0:DEMO.COM', success=False)
    native('--caller-allow', 'GAMES:9:MISSING.COM', success=False)
    native('--caller-allow', 'GAMES:9:*.COM', success=False)
    assert hashlib.sha256(image.read_bytes()).digest() == unchanged
    native('--caller-allow', 'GAMES:9:DEMO.COM')
    native('--caller-deny', 'GAMES:9:DEMO.COM')
    flags = native('--caller-list', 'GAMES').stdout
    assert b'---4----- demo.com' not in flags
    native('--caller-allow', 'GAMES:9:SYSDEMO.COM')
    image.chmod(0o600)
    tool('cpmchattr', '-f', 'z80pack-hd', image, 's', '9:SYSDEMO.COM')
    image.chmod(0o444)
    before = args.output / 'code-before'
    tool('cpmcp', '-f', 'z80pack-hd', image, '9:DEMO.COM', before)
    port = free_port()
    g = Guest(p, args.output/'caller', '--port', str(port))
    try:
        g.wait(b'RCP/M modem ready.'); g.connect(port); g.command('MOUNT GAMES')
        r = native('--caller-allow', 'GAMES:9:DEMO.COM', success=False)
        assert b'Stop RCP/M' in r.stderr
        for command in ('J9:DEMO', 'J9:UNMARKED', 'J9:F4ONLY', 'J9:ROONLY', 'I1:DEMO'):
            reply = g.command(command)
            assert MARKER not in reply and (b'?' in reply or b'Directory access denied.' in reply), (command, reply)
        assert b'FORGED-FLAGS-REJECTED-DMA-OK' in g.command('HELP')
        assert MARKER in g.command('J9:SYSDEMO')
        assert MARKER in g.command('A1:DEMO')
        assert b'R C P / M' in g.command('TYPE A:WELCOME.TXT [NO PAGE]')
        g.stop()
    finally:
        g.close()
    native('--caller-allow', 'GAMES:9:DEMO.COM')
    after = args.output / 'code-after'
    tool('cpmcp', '-f', 'z80pack-hd', image, '9:DEMO.COM', after)
    assert before.read_bytes() == after.read_bytes()
    port = free_port(); g = Guest(p, args.output/'allowed', '--port', str(port))
    try:
        g.wait(b'RCP/M modem ready.'); g.connect(port); g.command('MOUNT GAMES')
        assert MARKER in g.command('J9:DEMO')
        g.stop()
    finally:
        g.close()
    result = dict(passed=True, approve_revoke_list=True, live_change_refused=True,
                  exact_existing_com_required=True, binary_bytes_preserved=True,
                  f4_and_readonly_required=True, sys_file_supported=True,
                  mutable_I_rejected=True, A_and_J_approved_loads=True, dma_preserved=True)
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('package','output','builds','runtime','launcher','source'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    for name in vars(args): setattr(args, name, getattr(args,name).resolve())
    run(args)
