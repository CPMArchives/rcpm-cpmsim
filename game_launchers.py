"""Fixed game-data preparers followed by the pinned Z3PLUS command alias."""
import hashlib
from pathlib import Path
import subprocess
import tempfile

from prepare_z3plus import configure_startup
from rbbs_entry import ALIAS_SHA256

GAMES = (
    ('ADVENT', 1, 'ADV', ('ADVI.DAT', 'ADVI.PTR', 'ADVT.DAT', 'ADVT.PTR')),
    ('ANIMALS', 8, 'ANIMALS', ('BEASTS.QQQ', 'BEASTS.QQX')),
    ('MCHASE', 3, 'MCHASE', ('MCHASE.HLP',)),
)


def remove_system_launchers(tools, image):
    """Remove game launchers only from a stopped, staged A: image."""
    def tool(name, *args):
        return subprocess.run([str(tools / name), '-f', 'ibm-3740',
                               str(image), *args], check=True,
                              capture_output=True).stdout
    names = tool('cpmls', '0:*').decode('ascii').lower().split()
    for command, _, _, _ in GAMES:
        name = command + '.COM'
        if name.lower() in names:
            tool('cpmchattr', 'mr', '0:' + name)
            tool('cpmrm', '0:' + name)
    remaining = tool('cpmls', '0:*').decode('ascii').lower().split()
    if any((command + '.COM').lower() in remaining for command, _, _, _ in GAMES):
        raise ValueError('Game launcher remains on A0:')


def build(source, romwbw, output, games=GAMES):
    output.mkdir(parents=True, exist_ok=False)
    alias = romwbw / 'Source/Images/d_z3plus/u0/STARTZ3P.COM'
    if hashlib.sha256(alias.read_bytes()).hexdigest() != ALIAS_SHA256:
        raise ValueError('Expected the pinned Z3PLUS alias')
    for command, user, executable, files in games:
        program = bytearray(configure_startup(alias, f'I0:;J{user}:{executable}'))
        entry = int.from_bytes(program[1:3], 'little')
        origin = 0x100 + len(program)
        names = '\n'.join(" DB '" + name.partition('.')[0].ljust(8) + name.partition('.')[2].ljust(3) + "'" for name in files)
        asm = f''' ORG {origin}
START: LD C,49
 LD DE,DMAPB
 CALL 5
 LD (OLDDMA),HL
 LD C,49
 LD DE,MULPB
 CALL 5
 LD (OLDMULT),A
 LD C,44
 LD E,1
 CALL 5
 LD HL,NAMES
NEXT: LD A,(HL)
 OR A
 JP Z,DONE
 LD (NEXTPTR),HL
 LD HL,SRC
 LD B,72
 XOR A
ZERO: LD (HL),A
 INC HL
 DJNZ ZERO
 LD A,10
 LD (SRC),A
 LD A,9
 LD (DST),A
 LD HL,(NEXTPTR)
 LD DE,SRC+1
 LD BC,11
 LDIR
 LD HL,(NEXTPTR)
 LD DE,DST+1
 LD BC,11
 LDIR
 LD (NEXTPTR),HL
 CALL DEST
 LD DE,DST
 LD C,15
 CALL 5
 CP 255
 JP Z,CREATE
 LD DE,DST
 LD C,16
 CALL 5
 JP ADVANCE
CREATE: CALL SOURCE
 LD DE,SRC
 LD C,15
 CALL 5
 CP 255
 JP Z,FAILED
 CALL DEST
 LD DE,DST
 LD C,22
 CALL 5
 CP 255
 JP Z,FAILED
COPY: CALL SOURCE
 LD DE,BUFFER
 LD C,26
 CALL 5
 LD DE,SRC
 LD C,20
 CALL 5
 CP 1
 JP Z,FINISH
 OR A
 JP NZ,FAILED
 CALL DEST
 LD DE,BUFFER
 LD C,26
 CALL 5
 LD DE,DST
 LD C,21
 CALL 5
 OR A
 JP NZ,FAILED
 JP COPY
FINISH: LD DE,SRC
 LD C,16
 CALL 5
 CALL DEST
 LD DE,DST
 LD C,16
 CALL 5
 CP 255
 JP Z,FAILED
ADVANCE: LD HL,(NEXTPTR)
 JP NEXT
DONE: CALL RESTORE
 JP {entry}
FAILED: CALL SOURCE
 LD DE,SRC
 LD C,16
 CALL 5
 CALL DEST
 LD DE,DST
 LD C,16
 CALL 5
 LD DE,DST
 LD C,19
 CALL 5
 CALL RESTORE
 LD DE,ERROR
 LD C,9
 CALL 5
 RET
SOURCE: LD E,9
 LD C,14
 CALL 5
 LD E,{user}
 LD C,32
 JP 5
DEST: LD E,0
 LD C,32
 CALL 5
 LD E,8
 LD C,14
 JP 5
RESTORE: CALL DEST
 LD DE,(OLDDMA)
 LD C,26
 CALL 5
 LD A,(OLDMULT)
 LD E,A
 LD C,44
 JP 5
DMAPB: DB 60,0,0,0
MULPB: DB 74,0,0,0
OLDDMA: DW 0
OLDMULT: DB 1
NEXTPTR: DW 0
NAMES:
{names}
 DB 0
ERROR: DB 13,10,'Game preparation failed. MOUNT GAMES first; WORK must be writable.',13,10,'$'
SRC: DS 36
DST: DS 36
BUFFER: DS 128
'''
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            (work / 'prep.asm').write_text(asm)
            subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'prep.asm'],
                           cwd=work, check=True, capture_output=True)
            program[1:3] = origin.to_bytes(2, 'little')
            program += (work / 'prep.bin').read_bytes()
        (output / (command + '.COM')).write_bytes(program)
        (output / (command + '.ASM')).write_text(asm)
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        text = (Path(__file__).parent / 'guest/mchansi.asm').read_text()
        (work / 'mchansi.asm').write_text(text)
        subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'mchansi.asm'],
                       cwd=work, check=True, capture_output=True)
        (output / 'mchansi.bin').write_bytes((work / 'mchansi.bin').read_bytes())
