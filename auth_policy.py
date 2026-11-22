"""Shared caller ACL format and fresh-media AUTH installation."""
from pathlib import Path
import subprocess
import tempfile

MAGIC = b'RCPMAU01'
SIZE = 272


def defaults():
    table = bytearray(16) + bytearray([255] * 256)
    table[9] = table[15] = 1  # J:/P: caller read-only
    table[16] = 1           # A0: system commands
    table[16 + 8*16] = 3    # I0: WORK
    table[16 + 8*16 + 14] = 1  # I14: HELP
    return bytes(table)


def install(instance, tools, assembler):
    """Fresh, stopped staging media only; never modify an operator instance."""
    repo = Path(__file__).resolve().parent
    def tool(name, *args):
        return subprocess.run([str(tools/name), *map(str,args)], check=True, capture_output=True).stdout
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        (stage/'auth.asm').write_bytes((repo/'guest/auth.asm').read_bytes())
        subprocess.run([str(assembler), '-fb', '-x', 'auth.asm'], cwd=stage,
                       check=True, capture_output=True)
        i = instance/'disks/drivei.dsk'
        for name, data in (('AUTH.COM', (stage/'auth.bin').read_bytes()),
                           ('AUTH.DAT', (MAGIC+defaults()).ljust(384,b'\0'))):
            path=stage/name;path.write_bytes(data)
            tool('cpmrm','-f','z80pack-hd',i,'13:'+name)
            tool('cpmcp','-f','z80pack-hd',i,path,'13:'+name)
        # Every public command now follows the same actual-F4 test.
        a=instance/'disks/drivea.dsk'
        from caller_policy import policy
        for name in policy()['programs']:
            tool('cpmchattr','-f','ibm-3740',a,'4','0:'+name)
    for path in [instance/'disks/drivep.dsk', instance/'disks/drivej.dsk',
                 *list((instance/'disks/library').glob('*.dsk'))]:
        if path.exists(): path.chmod(0o600)
