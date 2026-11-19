#!/usr/bin/env python3
"""Configure upstream BYE510 for cpmsim without changing the reference files."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import re


def configure(reference, mode):
    text = (reference / 'bye510.asm').read_text()
    options = dict(CPM3='YES', HS2400='YES', IMODEM='YES' if mode == 'ip232' else 'NO',
                   B5IM='YES' if mode == 'ip232' else 'NO', SKTERM='YES', MHZ='4',
                   TOVALUE='255')
    for name, value in options.items():
        pattern = rf'(?m)^({name}\s+EQU\s+)\S+'
        text, count = re.subn(pattern, lambda match: match[1] + value, text)
        if count != 1:
            raise ValueError(f'Unexpected option {name}: {count} definitions')
    # Apply Irv Hoff's August 4, 1986 local-keyboard correction.
    start = text.index('MINP2:')
    end = text.index('MINP3:', start)
    text = text[:start] + '''MINP2: CALL MSTAT
        ORA A
        JZ MINP2
        CALL CONSTAT
        ORA A
        JNZ CONIN
''' + text[end:]
    anchor = '\tLDA\tMDMOFF'
    start = text.index('MSTAT:')
    offset = text.index(anchor, start)
    text = text[:offset] + '''        CALL CONSTAT
        ORA A
        JNZ MSTAT0
''' + text[offset:]
    offset = text.index('\tPUSH\tPSW', offset)
    text = text[:offset] + 'MSTAT0:\n' + text[offset:]
    marker = ';\t   ++++ Install your I/O port insert here ++++\n'
    if text.count(marker) != 1:
        raise ValueError('Machine insert point missing')
    insert = (Path(__file__).parent / 'guest/bye5/cpmsim.ins').read_text()
    text = text.replace(marker, marker + insert + '\n')
    return text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, default=Path('build/bye5/reference'))
    parser.add_argument('--fetch', action='store_true', help='Download missing upstream sources into the build cache')
    parser.add_argument('--output', type=Path, default=Path('build/bye5/sources'))
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).parent / 'docs/bye510-reference-sources.json').read_text())
    args.reference.mkdir(parents=True, exist_ok=True)
    for name in ('bye510.asm', 'b5-cpm3.asm', 'b5-driv3.asm'):
        reference = next(item for item in manifest['sources'] if item['url'].endswith('/' + name + '.txt'))
        path = args.reference / name
        if not path.exists() and args.fetch:
            with tempfile.TemporaryDirectory(dir=args.reference) as temporary:
                downloaded = Path(temporary) / name
                subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location', '--max-time', '30',
                                '--output', str(downloaded), reference['url']], check=True)
                if hashlib.sha256(downloaded.read_bytes()).hexdigest() != reference['sha256']:
                    parser.error('Reference download hash mismatch: ' + name)
                downloaded.replace(path)
        if not path.is_file():
            parser.error('Missing reference ' + str(path) + '; provide it or use --fetch')
        if hashlib.sha256(path.read_bytes()).hexdigest() != reference['sha256']:
            parser.error('Expected the pristine reference source: ' + str(path))
    args.output.mkdir(parents=True, exist_ok=True)
    for mode, name in (('direct', 'BYEDIR'), ('ip232', 'BYEMDM')):
        text = configure(args.reference, mode)
        (args.output / (name + '.ASM')).write_bytes(text.replace('\n', '\r\n').encode() + b'\x1a')
    for name, target in (('b5-cpm3.asm', 'B5ENTRY.ASM'), ('b5-driv3.asm', 'B5DRIVER.ASM')):
        text = (args.reference / name).read_text()
        if name == 'b5-cpm3.asm':
            text = text.replace('A:B5-DRIV3.COM', 'A:BYEDRIV.COM')
        (args.output / target).write_bytes(text.replace('\n', '\r\n').encode() + b'\x1a')
    print(args.output.resolve())


if __name__ == '__main__':
    main()
