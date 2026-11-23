#!/usr/bin/env python3
"""Check fresh packaged RBBS media and native first-start/restart initialization."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parent


def check(package, tools, work):
    (work/'disks').mkdir(parents=True,exist_ok=False)
    (work/'state').mkdir()
    shutil.copy2(package/'disks/drivei.dsk',work/'disks/drivei.dsk')
    fresh=json.loads((package/'metadata/RBBS-FRESH.json').read_text())
    def get(name):
        target=work/'record'
        subprocess.run([str(tools/'cpmcp'),'-f','z80pack-hd',str(work/'disks/drivei.dsk'),'15:'+name,str(target)],check=True,capture_output=True)
        return target.read_bytes()
    for area in fresh['areas']:assert get(area+'.MSG')==b''
    assert len(get('USERS.CCC'))==256
    assert get('CALLERS.CCC').startswith(b'MAX CALR: 0 0\0')
    source=work/'check.c'
    source.write_text('#define main release_launcher_main\n#include "'+str(ROOT/'packaging/launcher.c')+'"\n#undef main\nint main(void) { initialize(); return 0; }\n')
    subprocess.run(['cc','-std=c99','-O2',str(source),'-o',str(work/'check')],check=True)
    subprocess.run([str(work/'check')],cwd=work,check=True)
    initial=hashlib.sha256((work/'disks/drivei.dsk').read_bytes()).hexdigest()
    doc=(work/'SYSOP.DOC').read_text();password=doc.split('RBBS sysop password: ')[1].splitlines()[0]
    assert len(password)==6 and all(c in 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789' for c in password)
    assert get('USERS.CCC')[165:172]==password.encode()+b'\0'
    subprocess.run([str(work/'check')],cwd=work,check=True)
    assert (work/'SYSOP.DOC').read_text()==doc
    assert hashlib.sha256((work/'disks/drivei.dsk').read_bytes()).hexdigest()==initial
    (work/'state/initialized').unlink()
    result=subprocess.run([str(work/'check')],cwd=work,capture_output=True)
    assert result.returncode!=0 and b'already contains operator state' in result.stderr
    assert hashlib.sha256((work/'disks/drivei.dsk').read_bytes()).hexdigest()==initial
    result=dict(first_start_password_matches_account=True,restart_preserves_password_and_database=True,
                missing_marker_does_not_reset_accounts=True,fresh=fresh)
    (work/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('package','tools','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check(a.package.resolve(),a.tools.resolve(),a.output.resolve())
