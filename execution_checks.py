"""Disposable fixtures for approved-command, resident-command and write gates."""
from pathlib import Path
import os
import shutil
import subprocess
import time

from shared_service_checks import until, read_packet, expect

MARKER = b'UNAPPROVED-CODE-RAN'
UNSAFE = bytes((0x11, 0x09, 0x01, 0x0e, 9, 0xcd, 5, 0, 0xc9)) + MARKER + b'\r\n$'
RBBS_MARKER = b'TRUSTED-BOARD-LOAD-TEST'
GUARD = b'COMMAND-DISK-MUST-NOT-CHANGE\r\n'.ljust(128, b'\x1a')


def prepare(source, tools, instance):
    def tool(name, *args):
        subprocess.run([str(tools / name), *map(str, args)], check=True)
    fixture = instance / 'UNSAFE.COM'
    fixture.write_bytes(UNSAFE)
    for drive, fmt, users in (('a', 'ibm-3740', (0, 1)), ('i', 'z80pack-hd', (1,)),
                              ('j', 'z80pack-hd', (0,)), ('p', 'z80pack-hdb', (0, 1))):
        image = instance / f'disks/drive{drive}.dsk'
        image.chmod(0o644)
        for user in users:
            tool('cpmcp', '-f', fmt, image, fixture, f'{user}:UNSAFE.COM')
            if not (drive == 'a' and user == 0):
                tool('cpmcp', '-f', fmt, image, fixture, f'{user}:TYPE.COM')
        if drive in ('j', 'p'):
            image.chmod(0o444)
    demo = instance / 'volumes/DEMO.dsk'
    demo.chmod(0o644)
    shutil.copyfile(instance / 'disks/drivej.dsk', demo)
    demo.chmod(0o444)
    a = instance / 'disks/drivea.dsk'
    # Test-only public launcher and trusted board stand-ins. The real-board
    # checks separately exercise the pinned alias and preserved RBBS binary.
    entry = instance / 'RBBS-STUB.COM'
    entry.write_bytes(b'\xc3\x00\x00')
    tool('cpmcp', '-f', 'ibm-3740', a, entry, '0:RBBS.COM')
    entry.write_bytes(bytes((0x11, 0x0b, 0x01, 0x0e, 9, 0xcd, 5, 0, 0xc3, 0, 0))
                      + RBBS_MARKER + b'\r\n$')
    tool('cpmcp', '-f', 'ibm-3740', a, entry, '15:RBBS37.COM')
    tool('cpmcp', '-f', 'ibm-3740', a, entry, '2:RBBS37.COM')
    entry.write_bytes(UNSAFE)
    tool('cpmcp', '-f', 'ibm-3740', a, entry, '15:UNSAFE.COM')
    guard = instance / 'GUARD.TXT'
    guard.write_bytes(GUARD)
    tool('cpmcp', '-f', 'ibm-3740', a, guard, '0:GUARD.TXT')
    shutil.copyfile(Path(__file__).parent / 'guest/executionprobe.asm', instance / 'executionprobe.asm')
    tool('cpmrm', '-f', 'ibm-3740', a, '0:HELP.COM')
    subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'executionprobe.asm'],
                   cwd=instance, check=True, stdout=subprocess.DEVNULL)
    tool('cpmcp', '-f', 'ibm-3740', a, instance / 'executionprobe.bin', '0:HELP.COM')
    script = instance / 'RUN.SUB'
    script.write_bytes(b'J:UNSAFE\r\n\x1a')
    tool('cpmcp', '-f', 'z80pack-hd', instance / 'disks/drivei.dsk', script, '1:RUN.SUB')


def local_setup(master, local):
    def command(text):
        os.write(master, text.encode() + b'\r')
        time.sleep(.1)
        return local()
    if MARKER not in command('A0:UNSAFE'):
        raise AssertionError('Unapproved-code positive control did not run locally')
    for text in ('B:PIP I:UNSAFE.COM=J:UNSAFE.COM', 'B:PIP I:TYPE.COM=J:UNSAFE.COM'):
        command(text)
    command('A0:HELP S')
    command('POKE 8000 00')
    if b'EXECUTION-BOUNDARY-FAIL' not in command('A0:HELP M'):
        raise AssertionError('POKE syntax positive control failed')
    command('A0:HELP S')
    # Leave an unapproved program as the previous transient for GO/JUMP.
    if MARKER not in command('A0:UNSAFE'):
        raise AssertionError('Previous-transient positive control failed')


def caller_checks(command, caller, remote):
    if RBBS_MARKER in command('A15:RBBS37'):
        raise AssertionError('Board loaded without the public launcher')
    command('RBBS')
    if RBBS_MARKER in command('A2:RBBS37'):
        raise AssertionError('Public launcher admitted the legacy private board source')
    command('RBBS')
    if MARKER in command('A15:UNSAFE'):
        raise AssertionError('Launcher authorized a different executable')
    if RBBS_MARKER in command('A15:RBBS37'):
        raise AssertionError('A different load attempt did not consume the launcher authorization')
    command('RBBS')
    if RBBS_MARKER not in command('A15:RBBS37'):
        raise AssertionError('Launcher positive control failed')
    if RBBS_MARKER in command('A15:RBBS37'):
        raise AssertionError('Board permission survived its return to CP/M')
    forbidden = [
        'WHL SYSTEM', 'WHEEL SYSTEM', 'POKE 8000 00',
        'GET 100 J:UNSAFE.COM', 'GO', 'JUMP 100',
        'UNSAFE', 'A:UNSAFE', 'A0:UNSAFE', 'A1:UNSAFE',
        'I:UNSAFE', 'I0:UNSAFE', 'I1:UNSAFE', 'J:UNSAFE', 'P:UNSAFE', 'P1:UNSAFE',
        'I0:TYPE', 'I1:TYPE', 'J:TYPE', 'P:TYPE', 'P1:TYPE', 'A1:TYPE',
        'A0:GET CONSOLE', ':GET CONSOLE', '.GET CONSOLE',
        'A:PATH', 'A:SUBMIT I1:RUN', 'I1:RUN',
        'Z3PLUS', 'A:STARTZ3P', 'A:BYEDRIV',
    ]
    for text in forbidden:
        response = command(text)
        if MARKER in response or b'Z-System for CP/M PLUS' in response:
            raise AssertionError(f'Caller execution escaped through {text}: {response!r}')
    if b'EXECUTION-BOUNDARY-PASS' not in command('A0:HELP'):
        raise AssertionError('Memory or A: write boundary failed')
    if b'COMMAND-DISK-MUST-NOT-CHANGE' not in command('TYPE A:GUARD.TXT'):
        raise AssertionError('Command disk sentinel changed')
    if b'Volume mounted read-only' not in command('MOUNT DEMO'):
        raise AssertionError('Public MOUNT regressed')
    if MARKER in command('J:UNSAFE'):
        raise AssertionError('Mounted archive executed')
    # Executable archive files remain downloadable as bytes, including a
    # spoofed approved basename. No filename-based file-read prohibition.
    caller.sendall(b'YSEND J:TYPE.COM\r')
    until(caller, b'Ready for YMODEM download.\r\n')
    caller.sendall(b'C')
    header = read_packet(caller, 0).split(b'\0')
    length = int(header[1])
    caller.sendall(b'\x06C')
    result = bytearray()
    number = 1
    while len(result) < length:
        result.extend(read_packet(caller, number))
        caller.sendall(b'\x06')
        number = (number + 1) & 255
    if result[:len(UNSAFE)] != UNSAFE:
        raise AssertionError('Executable archive download changed')
    expect(caller, b'\x04')
    caller.sendall(b'\x15')
    expect(caller, b'\x04')
    caller.sendall(b'\x06C')
    if any(read_packet(caller, 0)):
        raise AssertionError('Missing YMODEM batch terminator')
    caller.sendall(b'\x06')
    remote()


def verify(tools, instance):
    out = instance / 'GUARD-VERIFY.TXT'
    subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740',
                    str(instance / 'disks/drivea.dsk'), '0:GUARD.TXT', str(out)], check=True)
    if out.read_bytes() != GUARD:
        raise AssertionError('A: protected file differs after shutdown')
