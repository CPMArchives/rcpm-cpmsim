#!/usr/bin/env python3
"""Use ZDE's original installer to select its ANSI standard terminal profile."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import shutil
import subprocess
import tty
from build_bye5 import wait_prompt
from check_modem_runtime import stop


def build(source, output):
    repo=Path(__file__).resolve().parent
    if output.exists():raise FileExistsError(output)
    rows=json.loads((repo/'docs/zde-reference-sources.json').read_text())
    cache=repo/'build/ztools/zde16'
    for row in rows:
        if hashlib.sha256((cache/row['path']).read_bytes()).hexdigest()!=row['sha256']:
            raise ValueError('Editor reference changed')
    output.mkdir(parents=True);machine=output/'machine'
    (machine/'disks').mkdir(parents=True);(machine/'conf').mkdir()
    for kind in ('server','client'):(machine/f'conf/net_{kind}.conf').write_text('# private editor setup\n')
    tools=repo/'build/cpmtools/bin'
    def tool(name,*args):subprocess.run([str(tools/name),*map(str,args)],check=True)
    a=machine/'disks/drivea.dsk';i=machine/'disks/drivei.dsk'
    shutil.copyfile(source/'cpmsim/disks/library/cpm3-1.dsk',a)
    tool('cpmrm','-f','ibm-3740',a,'0:PROFILE.SUB');tool('mkfs.cpm','-f','z80pack-hd',i)
    for name,dest in (('zde16.com','ZDE.COM'),('zdenst16.com','ZDENST.COM')):
        tool('cpmcp','-f','z80pack-hd',i,cache/name,'0:'+dest)
    m,s=pty.openpty();tty.setraw(s)
    p=subprocess.Popen([str(repo/'build/modem/cpmsim')],cwd=machine,
        env={k:v for k,v in os.environ.items() if not k.startswith('RCPM_MODEM')},
        stdin=s,stdout=s,stderr=s)
    try:
        with (output/'configure.log').open('wb') as log:
            wait_prompt(m,b'A>',log);os.write(m,b'I:\r');wait_prompt(m,b'I>',log)
            os.write(m,b'ZDENST ZDE\r');wait_prompt(m,b'elp:',log)
            os.write(m,b'T');wait_prompt(m,b'terminals:',log);os.write(m,b'L')
            # The heading ends in 'list:', but individual choices end ' :'.
            for _ in range(40):
                choice=wait_prompt(m,b' :',log)
                if b'ANSI standard' in choice:break
                os.write(m,b'\r')
            else:raise ValueError('ANSI terminal definition not found')
            os.write(m,b'Y');wait_prompt(m,b'Press <ESC>',log)
            os.write(m,b'\x1b');wait_prompt(m,b'elp:',log)
            # The old ANSI profile assigns ^K as an extra Up key, masking
            # WordStar's save/quit prefix. Disable those optional arrow keys.
            # Replace its obsolete cursor visibility codes with VT100 CSI.
            os.write(m,b'T');wait_prompt(m,b'terminals:',log);os.write(m,b'E')
            fields=(('Terminal ID:',b'\r'),('Viewable columns:',b'\r'),
                    ('Auto wrap at line end:',b'\r'),('Viewable lines:',b'\r'),
                    ('Extra DELete key:',b'\r'),('Extra arrow keys u/d/r/l:',b'FFFFFFFF'),
                    ('Clear to end of line [06]:',b'\r'),('Terminal init [07]:',b'\r'),
                    ('Terminal deinit [07]:',b'\r'),('Alternate video on [06]:',b'\r'),
                    ('Alternate video off [06]:',b'\r'),('Alt video uses high bit:',b'\r'),
                    ('Output filter limit:',b'\r'),('Cursor position mode (Std/Rev/ANSI/None):',b'\r'),
                    ('[Non-ANSI] Cursor position sequence:',b'\r'),
                    ('Delay after cursor positioning:',b'\r'),('Insert line [06]:',b'\r'),
                    ('Delete line [06]:',b'\r'),('Ins/del specific to line 1:',b'\r'),
                    ('Cursor off [06]:',b'061B5B3F32356C'),('Cursor on  [06]:',b'061B5B3F323568'))
            for prompt,value in fields:
                wait_prompt(m,prompt.encode(),log);os.write(m,value)
            wait_prompt(m,b'Press <ESC>',log);os.write(m,b'\x1b');wait_prompt(m,b'elp:',log)
            os.write(m,b'S');wait_prompt(m,b'I>',log)
    finally:stop(p);os.close(m);os.close(s)
    target=output/'ZDE.COM';tool('cpmcp','-f','z80pack-hd',i,'0:ZDE.COM',target)
    if target.read_bytes()[128:143]!=b'ANSI standard  ':
        raise ValueError('Installer did not select ANSI')
    (output/'build-result.json').write_text(json.dumps(dict(
        terminal='ANSI standard',wordstar_prefix_preserved=True,vt100_cursor_visibility=True,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        sources=rows),indent=2)+'\n')
    print('Configured',target)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('build/sysop-editor'))
    a=p.parse_args();build(a.source.resolve(),a.output.resolve())
