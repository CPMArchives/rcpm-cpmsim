#!/usr/bin/env python3
"""Configure upstream BYE510 for cpmsim without changing the reference files."""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
import re
from caller_policy import assembly


def configure(reference, mode):
    text = (reference / 'bye510.asm').read_text()
    options = dict(CPM3='YES', HS2400='YES', IMODEM='YES' if mode == 'ip232' else 'NO',
                   B5IM='YES' if mode == 'ip232' else 'NO', SKTERM='YES', MHZ='4',
                   TOVALUE='255', ZCPR2='YES', WHEEL='WXLOCAL',
                   MAXDRIV='WXDRIVE', MAXUSER='WXUSER', MSPEED='WXSPD',
                   MAXDRV="'P'-'@'", MAXUSR='15', SYSDRV="'P'-'@'", SYSUSR='15',
                   WELFILE='YES', WELDRV="'A'", WELUSR='0')
    for name, value in options.items():
        pattern = rf'(?m)^({name}\s+EQU\s+)\S+'
        text, count = re.subn(pattern, lambda match: match[1] + value, text)
        if count != 1:
            raise ValueError(f'Unexpected option {name}: {count} definitions')
    # The upstream wildcard can open ZDE's WELCOME.BAK instead of the
    # edited WELCOME.TXT. Keep backups, but select the exact banner file.
    old = "WELFILN:DB\t0,'WELCOME ???'"
    if text.count(old) != 1:
        raise ValueError('Unexpected BYE welcome-file FCB')
    text = text.replace(old, "WELFILN:DB\t0,'WELCOME TXT'")
    # RMAC does not preserve these forward EQU aliases as relocatable
    # addresses. They otherwise become the RSX base, corrupting transient
    # stack storage during carrier/console checks. Reference the labels
    # directly so LINK generates relocation bits for each operand.
    for name, target, expected in (('MAXDRIV', 'WXDRIVE', 6),
                                   ('MAXUSER', 'WXUSER', 6),
                                   ('MSPEED', 'WXSPD', 10)):
        text, count = re.subn(r'(?m)^(\t(?:LDA|STA)\t)' + name + r'\b',
                              lambda match: match[1] + target, text)
        if count != expected:
            raise ValueError(f'Unexpected {name} adapter reference count: {count}')
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
    # Status polling must be nonblocking. Keep the existing timeout exit
    # and warning behavior, but count actual host minutes rather than calls.
    start = text.index('MSTAT1:')
    end = text.index('TMOUT:', start)
    text = text[:start] + 'MSTAT1: JMP WXIDPOLL\n;\n' + text[end:]
    text, count = re.subn(r'(?m)^(\tSTA\tMSFLAG[^\n]*\n)',
                         r'\1\tCALL\tWXIDRESET\n', text)
    if count != 4:
        raise ValueError(f'Unexpected no-activity reset count: {count}')
    marker = ';\t   ++++ Install your I/O port insert here ++++\n'
    if text.count(marker) != 1:
        raise ValueError('Machine insert point missing')
    # Replace only the four direct loads/stores of the old fixed wheel byte.
    for opcode, target in (('LDA', 'WXGET'), ('STA', 'WXSET')):
        text, count = re.subn(r'(?m)^\t' + opcode + r'\tWHEEL\b', '\tCALL\t' + target, text)
        if count != 4:
            raise ValueError('Unexpected BYE5 wheel reference count')
    # Clear queued Z-System commands before call recovery or authority changes.
    # The legacy DOZ3 assumes fixed addresses and also clears unrelated state.
    for old, new in (
        ('LOGOFF:\tLXI\tSP,STACK\t; Ensure valid stack',
         'LOGOFF:\tLXI\tSP,STACK\t; Ensure valid stack\n\tCALL\tWXRESET'),
        ('EXCPM:\t IF\tB5IM', 'EXCPM:\tCALL\tWXRESET\n\t IF\tB5IM'),
        ('BLNKTOG:LDA\tMDMOFF', 'BLNKTOG:CALL\tWXCLR\n\tLDA\tMDMOFF'),
        ('NULLP:\tCALL\tMDOUTST', 'NULLP:\tCALL\tCHECK\n\tCALL\tMDOUTST'),
        ('MBOOT:\tLDA\tOPTION', 'MBOOT: CALL WXRBCLEAR\n\tLDA\tOPTION'),
    ):
        if text.count(old) != 1:
            raise ValueError('Unexpected BYE5 lifecycle hook: ' + old.split(':')[0])
        text = text.replace(old, new)
    # A blanked caller gives the sysop the console. Other local function
    # keys must reach editors (notably ZDE's ^Q prefix, ^G and ^O). Retain
    # only the blank toggle while private; the original hotkeys still work
    # in shared caller mode. Test the blank state, not the mutable wheel.
    old = 'CKFUNC:\t IF\tLEADIN'
    if text.count(old) != 1:
        raise ValueError('Unexpected BYE function-key entry')
    text = text.replace(old, '''CKFUNC: PUSH PSW
        LDA MDMOFF
        ORA A
        JZ WXFNORM
        POP PSW
        CPI BLNKKEY
        RNZ
        PUSH PSW
        CALL MDCARCK
        ORA A
        JZ WXFNRET
        POP PSW
        JMP BLNKTOG
WXFNRET:POP PSW
        RET
WXFNORM:POP PSW
         IF LEADIN''')
    insert = (Path(__file__).parent / 'guest/bye5/cpmsim.ins').read_text()
    insert += '\n' + (Path(__file__).parent / 'guest/bye5/z3wheel.ins').read_text()
    insert += '\n' + (Path(__file__).parent / 'guest/bye5/work.ins').read_text()
    insert += '\n' + (Path(__file__).parent / 'guest/bye5/privateb.ins').read_text()
    insert += '\n' + (Path(__file__).parent / 'guest/bye5/rbbs.ins').read_text()
    insert += '\n' + (Path(__file__).parent / 'guest/bye5/auth.ins').read_text()
    execution = (Path(__file__).parent / 'guest/bye5/exec.ins').read_text()
    if execution.count('; @@CALLER_TABLE@@') != 1:
        raise ValueError('Missing caller policy assembly table')
    insert += '\n' + execution.replace('; @@CALLER_TABLE@@', assembly())
    if text.count('BYERSX:\n') != 1:
        raise ValueError('Unexpected BYE BDOS interceptor')
    text = text.replace('BYERSX:\n', 'BYERSX: JMP WXBCHK\nWXBGO:\n')
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
