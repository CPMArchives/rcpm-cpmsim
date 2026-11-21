"""Qualification helpers for the fresh upper-area profile; no live images."""
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parent
DATA = bytes(range(256)) * 257  # 65792 bytes: exceeds the entire TPA.
TOPIC = b'PRIVATE-TEST-HELP-TOPIC\r\n\x1a'


def prepare(args, root):
    def tool(name, *values):
        subprocess.run([str(args.cpmtools / name), *map(str, values)], check=True)
    fixture = root / 'fixture'
    fixture.write_bytes(TOPIC)
    tool('cpmcp', '-f', 'z80pack-hd', root / 'disks/drivei.dsk', fixture, '14:TOPIC.HLP')
    fixture.write_bytes(DATA)
    j = root / 'disks/drivej.dsk'
    j.chmod(0o600)
    tool('cpmcp', '-f', 'z80pack-hd', j, fixture, '0:BIG.COM')
    j.chmod(0o444)
    shutil.copyfile(REPO / 'guest/upperprobe.asm', root / 'upperprobe.asm')
    subprocess.run([str(args.source / 'z80asm/z80asm'), '-fb', '-x', 'upperprobe.asm'],
                   cwd=root, check=True, stdout=subprocess.DEVNULL)
    a = root / 'disks/drivea.dsk'
    tool('cpmrm', '-f', 'ibm-3740', a, '0:CLS.COM')
    tool('cpmcp', '-f', 'ibm-3740', a, root / 'upperprobe.bin', '0:CLS.COM')
    fixture.unlink()


def exercise(send, read, master, prompt):
    import os
    def public(command, marker=prompt):
        return send(command, marker, True)
    for command in ('I13:', 'SYSUTLS:', 'I15:', 'RBBS:'):
        if b'Directory access denied.' not in public(command):
            raise AssertionError('Private directory selection accepted: ' + command)
    if b'UPPER-ACCESS-PASS' not in public('A0:CLS'):
        raise AssertionError('I13/I15 FCB or I14 read-only/all-user-search guard failed')
    result = public('SYSUTLS:PPIP')
    if b'Verifying' in result or b'copy program' in result.lower():
        raise AssertionError('Caller started private PPIP')
    public('HELP:', b'I14:HELP>')
    if b'PRIVATE-TEST-HELP-TOPIC' not in public('TYPE TOPIC.HLP', b'I14:HELP>'):
        raise AssertionError('Public HELP topic read failed')
    public('A0:')
    os.write(master, b'\x02')
    read(prompt)
    # The bare PPIP name must resolve through the private path, not an
    # explicit private DU. Both filename syntaxes and copy-with-rename work.
    for command in ('PPIP WORK:NAMED.BIN=VOLUME:BIG.COM /V',
                    'PPIP I1:NAMED.BIN=WORK:NAMED.BIN /V',
                    'PPIP I1:NUMERIC.BIN=J0:BIG.COM /V'):
        result = send(command, prompt)
        if b'VERIFYING OK' not in result.upper():
            raise AssertionError(('PPIP named/DU copy or private search path failed', result))
    if b'I13:' not in send('PATH', prompt):
        raise AssertionError('Private search path omits I13:')
    send('I1:', b'I1>')
    pip = send('SYSUTLS:PIP I:PIP.COM=J:BIG.COM[G0]', b'I1>')
    if b'ERROR' in pip.upper():
        raise AssertionError(('Stock PIP copy failed', pip))
    send('A0:', prompt)
    pwd = send('PWD', prompt)
    if any(name not in pwd for name in (b'SYSUTLS', b'HELP', b'RBBS', b'SIGM', b'CPMUG')):
        raise AssertionError(('Extended named-directory table failed', pwd))
    for directory, marker in (('SYSUTLS:', b'I13:SYSUTLS>'), ('RBBS:', b'I15:RBBS>')):
        send(directory, marker)
        os.write(master, b'\x02')
        result = read(prompt)
        if result.count(b'Directory access denied.') > 1:
            raise AssertionError('Unblank from a private DU repeated denial')
        os.write(master, b'\x02')
        read(prompt)
    send('A0:', prompt)
    os.write(master, b'\x02')
    read(prompt)
    public('HELP:', b'I14:HELP>')
    if b'PRIVATE-TEST-HELP-TOPIC' not in public('TYPE TOPIC.HLP', b'I14:HELP>'):
        raise AssertionError('Help read failed after private mode')
    public('A0:')
    for command in ('PPIP', 'SYSUTLS:PIP', 'SYSUTLS:LX', 'SYSUTLS:ARUNZ'):
        result = public(command)
        if b'CP/M 3 PIP VERSION' in result or b'Verifying' in result:
            raise AssertionError('Private tool survived return to caller mode')


def verify(args, root):
    # Called only after the test's emulator has stopped.
    image = root / 'disks/drivei.dsk'
    for name, expected in (('NAMED.BIN', DATA), ('NUMERIC.BIN', DATA),
                           ('PIP.COM', DATA), ('TOPIC.HLP', TOPIC)):
        output = root / (name + '.check')
        user = 14 if name == 'TOPIC.HLP' else 1
        subprocess.run([str(args.cpmtools / 'cpmcp'), '-f', 'z80pack-hd', str(image),
                        f'{user}:{name}', str(output)], check=True)
        if output.read_bytes()[:len(expected)] != expected:
            raise AssertionError('Copied bytes or protected help topic differ: ' + name)
    return dict(ppip_named_copy=True, ppip_du_copy=True, private_path=True,
                help_read_only=True, upper_fcb_denial=True)
