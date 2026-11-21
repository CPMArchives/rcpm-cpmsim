#!/usr/bin/env python3
"""Compile selected Creative Computing CP/M BASIC games as standalone COM files.

Supply your own compiler and tools. Compiler/interpreter/runtime-module binaries
are never copied into the output games/ directory. Built games remain candidates
until separately qualified under RCP/M. See MICROSOFT-RUNTIME-TERMS.txt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import shutil
import subprocess
import sys
import tty
import zipfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from build_bye5 import wait_prompt
from check_modem_runtime import stop


def normalize(data, console_printer=False):
    lines = []
    for line in data.split(b'\x1a')[0].decode('ascii').splitlines():
        if not line.strip():
            continue
        if re.match(r'^\d+ ', line):
            lines.append(line)
        elif lines:
            lines[-1] += ' ' + line.strip()
        else:
            raise ValueError('Text before the first numbered statement')
    source = '\r\n'.join(lines)
    source = re.sub(r'(?i)\bPRINT\s+CHR\$\(26\)',
                    'PRINT CHR$(27);"[2J";CHR$(27);"[H"', source)
    source = re.sub(r'(?i)\bRUN\s+"MENU"', 'END', source)
    if console_printer:
        source = re.sub(r'(?i)\bLPRINT\b', 'PRINT', source)
    # Keep every original line number, including existing line zero.
    number, separator, body = source.partition(' ')
    source = number + ' PRINT "PORTIONS COPYRIGHTED BY MICROSOFT, 1981":' + body
    return (source + '\r\n').encode('ascii') + b'\x1a'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('archive', 'compiler', 'tools', 'cpmsim', 'boot', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--console-printer', action='store_true',
                        help='Redirect LPRINT to terminal for reviewed online editions')
    parser.add_argument('--source-overrides', type=Path,
                        help='Reviewed numbered BASIC sources replacing selected archive members')
    parser.add_argument('--names', required=True, help='Comma-separated 8.3 stems')
    args = parser.parse_args()
    for name in ('archive', 'compiler', 'tools', 'cpmsim', 'boot', 'output'):
        setattr(args, name, getattr(args, name).resolve())
    names = args.names.upper().split(',')
    assert len(names) == len(set(names)) and all(re.fullmatch(r'[A-Z0-9_-]{1,8}', n) for n in names)
    out = args.output
    out.mkdir(parents=True, exist_ok=False)
    for folder in ('prepared', 'games', 'machine/disks', 'machine/conf'):
        (out / folder).mkdir(parents=True)
    env = dict(os.environ, DISKDEFS=str(args.tools / 'diskdefs'))
    def tool(name, *a):
        return subprocess.check_output([str(args.tools / name), *map(str, a)], env=env)
    machine = out / 'machine'
    for kind in ('server', 'client'):
        (machine / f'conf/net_{kind}.conf').write_text('# private BASIC compilation\n')
    disk = machine / 'disks/drivei.dsk'
    a = machine / 'disks/drivea.dsk'
    shutil.copyfile(args.boot, a)
    tool('cpmrm', '-f', 'ibm-3740', a, '0:PROFILE.SUB')
    tool('mkfs.cpm', '-f', 'z80pack-hd', disk)
    compiler_hashes = {}
    for name in ('BASCOM.COM', 'L80.COM', 'OBSLIB.REL'):
        f = args.compiler / name
        compiler_hashes[name] = hashlib.sha256(f.read_bytes()).hexdigest()
        tool('cpmcp', '-f', 'z80pack-hd', disk, f, '0:' + name)
    rows = []
    with zipfile.ZipFile(args.archive) as archive:
        for name in names:
            matches = [n for n in archive.namelist() if re.fullmatch(r'DISK[12]/' + name + r'\.BAS', n)]
            assert len(matches) == 1, (name, matches)
            # Historical ZIP uses the Implode method, unsupported by zipfile.
            original = subprocess.check_output(['unzip', '-p', str(args.archive), matches[0]])
            f = out / 'prepared' / (name + '.BAS')
            replacement = args.source_overrides / (name + '.BAS') if args.source_overrides else None
            source = replacement.read_bytes() if replacement and replacement.exists() else original
            f.write_bytes(normalize(source, args.console_printer))
            rows.append(dict(game=name, archive_member=matches[0], source_sha256=hashlib.sha256(original).hexdigest(), prepared_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), qualified_for_GAMES=False))
            if source != original:
                rows[-1]['reviewed_source_sha256'] = hashlib.sha256(source).hexdigest()
            tool('cpmcp', '-f', 'z80pack-hd', disk, f, '0:' + f.name)
    master, slave = pty.openpty()
    tty.setraw(slave)
    process = subprocess.Popen([str(args.cpmsim)], cwd=machine, stdin=slave,
                               stdout=slave, stderr=slave,
                               env={k:v for k,v in env.items() if not k.startswith('RCPM_')})
    try:
        with (out / 'compile.log').open('wb') as log:
            wait_prompt(master, b'A>', log)
            os.write(master, b'I:\r')
            wait_prompt(master, b'I>', log)
            for row in rows:
                name = row['game']
                os.write(master, f'BASCOM {name}={name}/O\r'.encode())
                result = wait_prompt(master, b'I>', log, 60)
                row['compiler_output'] = result.decode('latin1')
                if not re.search(rb'\b0+ Fatal Error\(s\)', result):
                    row['status'] = 'compile failed'
                else:
                    os.write(master, f'L80 {name},{name}/N/E\r'.encode())
                    try:
                        result = wait_prompt(master, b'I>', log, 30)
                        row['linker_output'] = result.decode('latin1')
                        row['status'] = 'built'
                    except RuntimeError as error:
                        row['status'] = 'link failed'
                        row['error'] = str(error)
                        os.write(master, b'\x03')
                        wait_prompt(master, b'I>', log)
                if row['status'] == 'built':
                    os.write(master, f'ERA {name}.REL\r'.encode())
                    wait_prompt(master, b'I>', log)
                print(name + ': ' + row['status'], flush=True)
                (out / 'build-results.json').write_text(json.dumps(rows, indent=2)+'\n')
    finally:
        stop(process)
        os.close(master)
        os.close(slave)
    for row in rows:
        if row['status'] == 'built':
            f = out / 'games' / (row['game'] + '.COM')
            tool('cpmcp', '-f', 'z80pack-hd', disk, '0:' + f.name, f)
            row.update(bytes=f.stat().st_size, sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    (out / 'build-results.json').write_text(json.dumps(dict(compiler_hashes=compiler_hashes, archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(), standalone_option='/O', runtime_library='OBSLIB.REL', console_printer=args.console_printer, gameplay_qualification_required=True, games=rows), indent=2)+'\n')
    print('Built', sum(r['status']=='built' for r in rows), 'standalone candidates; none admitted to GAMES without gameplay tests.')


if __name__ == '__main__':
    main()
