#!/usr/bin/env python3
"""Build the RCP/M SD137 variant with preserved source and native M80/L80."""
import argparse
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


def configure_sd(text):
    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('SD137 patch context changed: ' + old[:70])
        text = text.replace(old, new)
    change(';\tASEG', '\tASEG')
    for name, value in dict(ZCPR3P='YES', NDIRS='YES', DRVVEC='YES',
                            MAXDRV='YES', MAXUR='YES', WHEEL='YES',
                            USEF='NO', USEO='NO', USEP='NO', USER='NO',
                            USES='NO', USEA='NO').items():
        text, count = re.subn(r'(?m)^(' + name + r'\s+EQU\s+)\w+',
                              lambda m: m[1] + value, text)
        if count != 1:
            raise ValueError('Missing SD option: ' + name)
    # CP/M 3 returns a 24-bit record count. Preserve the high kilobyte
    # byte rather than wrapping free space above 65535 KiB.
    change('\tLHLD\tTBUF\t\t; Now get result in k',
           '\tLDA TBUF+2\n\tSTA FREEBY+2\n\tLHLD\tTBUF\t\t; Now get result in k')
    change('FREE20:\tMVI', 'FREE20:\tXRA A\n\tSTA FREEBY+2\n\tMVI')
    change('\tSHLD\tTOTFRE\n', '\tSHLD\tTOTFRE\n\tLDA TOTFRE+2\n\tMOV B,A\n\tLDA FREEBY+2\n\tADC B\n\tSTA TOTFRE+2\n')
    change('\tLHLD\tFREEBY\n\tCALL\tDECPRT', '\tLXI H,FREEBY\n\tCALL DEC24')
    change('\tLHLD\tTOTFRE\n\tCALL\tDECPRT', '\tLXI H,TOTFRE\n\tCALL DEC24')
    change('FREEBY:\tDS\t2', 'FREEBY:\tDS\t3')
    change('TOTFRE:\tDS\t2', 'TOTFRE:\tDS\t3')
    # Matched-size totals also exceed 16 bits on a populated archive.
    change('\tSHLD\tTOTSIZ\t\t; "  total size counter',
           '\tSHLD\tTOTSIZ\t\t; "  total size counter\n\tXRA A\n\tSTA TOTSIZ+2')
    change('\tSHLD\tTOTSIZ\n', '\tSHLD\tTOTSIZ\n\tLDA TOTSIZ+2\n\tACI 0\n\tSTA TOTSIZ+2\n')
    change('\tSHLD\tTOTSZ1\t\t; And put it back',
           '\tSHLD\tTOTSZ1\t\t; And put it back\n\tLDA TOTSZ1+2\n\tMOV B,A\n\tLDA TOTSIZ+2\n\tADC B\n\tSTA TOTSZ1+2')
    change('\tCALL\tDECPRT\t\t; Print file size', '\tLXI H,TOTSIZ\n\tCALL DEC24\t\t; Print file size')
    change('\tLHLD\tTOTSZ1\t\t; Total \'k\' found\n\tCALL\tDECPRT',
           '\tLXI H,TOTSZ1\n\tCALL DEC24')
    change('TOTSIZ:\tDS\t2', 'TOTSIZ:\tDS\t3')
    change('TOTSZ1:\tDS\t2', 'TOTSZ1:\tDS\t3')
    # Convert a little-endian 24-bit value at HL, retaining full precision.
    # Repeated subtraction needs at most 9 iterations per decimal digit.
    routine = '''
DEC24:  MOV E,M
        INX H
        MOV D,M
        INX H
        MOV A,M
        STA DN24+2
        XCHG
        SHLD DN24
        XRA A
        STA DZ24
        LXI H,DP24
DLO24:  MVI B,'0'
DSU24:  LDA DN24
        SUB M
        MOV E,A
        INX H
        LDA DN24+1
        SBB M
        MOV D,A
        INX H
        LDA DN24+2
        SBB M
        DCX H
        DCX H
        JC DOU24
        STA DN24+2
        XCHG
        SHLD DN24
        XCHG
        INR B
        JMP DSU24
DOU24:  MOV A,B
        CPI '0'
        JNZ DPR24
        LDA DZ24
        ORA A
        JNZ DCH24
        MOV A,M
        CPI 1
        JNZ DNE24
DCH24:  MOV A,B
DPR24:  PUSH H
        MVI B,1
        MOV C,A
        MOV A,B
        STA DZ24
        MOV A,C
        CALL PUTCHR
        POP H
DNE24:  INX H
        INX H
        INX H
        MOV A,M
        INX H
        ORA M
        INX H
        ORA M
        DCX H
        DCX H
        JNZ DLO24
        RET
DN24:   DS 3
DZ24:   DS 1
DP24:
'''
    for n in (10000000, 1000000, 100000, 10000, 1000, 100, 10, 1, 0):
        routine += '        DB ' + ','.join(str(x) for x in n.to_bytes(3, 'little')) + '\n'
    change('DECPRT:\tXRA', routine + '\nDECPRT:\tXRA')
    return text


def build(source, runtime, tools, output, fetch=False):
    if output.exists():
        raise FileExistsError(output)
    cache = REPO / 'build/ztools/sd137'
    rows = json.loads((REPO / 'docs/sd137-reference-sources.json').read_text())
    for directory, references in ((cache, rows),
            (REPO/'build/ztools/ldirb15', json.loads((REPO/'docs/ldir-reference-sources.json').read_text())),
            (REPO/'build/ztools/zde16', json.loads((REPO/'docs/zde-reference-sources.json').read_text()))):
        for row in references:
            path=directory/row['path']
            if not path.exists() and fetch:
                directory.mkdir(parents=True,exist_ok=True)
                path.write_bytes(urllib.request.urlopen(row['url'],timeout=30).read())
            if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:
                raise ValueError('Missing or changed source: '+str(path))
    for row in rows:
        if hashlib.sha256((cache / row['path']).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Changed SD reference: ' + row['path'])
    text = configure_sd((cache / 'sd137.asm.txt').read_text())
    output.mkdir(parents=True)
    machine = output / 'machine'
    (machine / 'disks').mkdir(parents=True)
    (machine / 'conf').mkdir()
    for kind in ('server', 'client'):
        (machine / f'conf/net_{kind}.conf').write_text('# Isolated SD build\n')
    for drive, name in (('a', 'cpm3-1.dsk'), ('b', 'cpm3-2.dsk')):
        shutil.copyfile(source / 'cpmsim/disks/library' / name, machine / f'disks/drive{drive}.dsk')
    def tool(name, *args):
        subprocess.run([str(tools / name), *map(str, args)], check=True)
    tool('cpmrm', '-f', 'ibm-3740', machine / 'disks/drivea.dsk', '0:PROFILE.SUB')
    image = machine / 'disks/drivei.dsk'
    tool('mkfs.cpm', '-f', 'z80pack-hd', image)
    mac = output / 'SD.MAC'
    mac.write_bytes(text.replace('\n', '\r\n').encode() + b'\x1a')
    tool('cpmcp', '-f', 'z80pack-hd', image, mac, '0:SD.MAC')
    master, slave = pty.openpty()
    tty.setraw(slave)
    guest = subprocess.Popen([str(runtime)], cwd=machine,
        env={k:v for k,v in os.environ.items() if not k.startswith('RCPM_MODEM')},
        stdin=slave, stdout=slave, stderr=slave)
    try:
        with (output / 'build.log').open('wb') as log:
            wait_prompt(master, b'A>', log)
            for command in ('I:', 'B:M80 =SD', 'B:L80 SD,SDZ/N/E'):
                os.write(master, command.encode() + b'\r')
                result = wait_prompt(master, b'I>', log)
                checked = result.upper().replace(b'NO FATAL ERROR(S)', b'')
                if any(x in checked for x in (b'ERROR', b'UNDEFINED', b'NO FILE')):
                    raise RuntimeError(result.decode(errors='replace'))
    finally:
        stop(guest)
        os.close(master)
        os.close(slave)
    target = output / 'SDZ.COM'
    tool('cpmcp', '-f', 'z80pack-hd', image, '0:SDZ.COM', target)
    (output / 'build-result.json').write_text(json.dumps(dict(
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(), sources=rows,
        source_sha256=hashlib.sha256(mac.read_bytes()).hexdigest(),
        free_space_bits=24, matched_size_bits=24, zsystem=True,
        caller_file_output=False, caller_printer=False, caller_reset=False), indent=2)+'\n')
    print('Built', target)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    p.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    p.add_argument('--output', type=Path, default=Path('build/caller-tools'))
    p.add_argument('--fetch', action='store_true')
    a = p.parse_args()
    build(*(getattr(a,n).resolve() for n in ('source','runtime','cpmtools','output')), fetch=a.fetch)
