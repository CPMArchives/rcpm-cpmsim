#!/usr/bin/env python3
"""Install reviewed caller tools on a stopped upper-area trial, preserving BBS data."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from caller_policy import digest
from prepare_z3plus import configure_startup
from rbbs_entry import BOARD_SHA256
from system_attributes import apply as apply_attributes
from runtime_features import require as require_runtime


def upgrade(instance, release, tools):
    with (instance/'.console.lock').open('a+b') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Trial is running; leave RBBS, blank the caller, and run SYSUTLS:BYEBYE first.')
        manifest=json.loads((instance/'trial-build.json').read_text())
        reference=json.loads((release/'trial-build.json').read_text())
        build=json.loads((Path(reference['builds'])/'build-result.json').read_text())
        require_runtime(instance/'runtime/cpmsim',build)
        if not manifest.get('upper_areas') or manifest.get('mode')!='direct':
            raise ValueError('This updater requires the direct-TCP I13/I14/I15 layout')
        if reference.get('caller_policy_sha256')!=digest() or not reference.get('caller_tools'):
            raise ValueError('Build a fresh caller-tools release first')
        release_a=release/'disks/drivea.dsk'
        if hashlib.sha256(release_a.read_bytes()).hexdigest()!=reference['hashes']['disks/drivea.dsk']:
            raise ValueError('Release boot image changed; use an unbooted release')
        for d in 'ai':
            p=instance/f'disks/drive{d}.dsk'
            if p.is_symlink() or not p.is_file():raise ValueError('Expected owned A/I disk images')
        a=instance/'disks/drivea.dsk';i=instance/'disks/drivei.dsk'
        def tool(name,*args):
            subprocess.run([str(tools/name),*map(str,args)],check=True,capture_output=True)
        with tempfile.TemporaryDirectory(prefix='.caller-tools-',dir=instance) as temp:
            work=Path(temp);sa=work/'drivea.dsk';si=work/'drivei.dsk'
            shutil.copyfile(a,sa);shutil.copyfile(i,si)
            def read(disk,fmt,user,name,optional=False):
                target=work/'extracted';target.unlink(missing_ok=True)
                try:tool('cpmcp','-f',fmt,disk,f'{user}:{name}',target)
                except subprocess.CalledProcessError:
                    if not optional:raise
                if not target.exists():
                    if optional:return None
                    raise ValueError('Missing '+name)
                return target.read_bytes()
            def put(disk,fmt,user,name,data):
                old=read(disk,fmt,user,name,optional=True)
                if old is not None:tool('cpmrm','-f',fmt,disk,f'{user}:{name}')
                p=work/'input';p.write_bytes(data)
                tool('cpmcp','-f',fmt,disk,p,f'{user}:{name}')
                if read(disk,fmt,user,name)!=data:raise ValueError('Verification failed: '+name)
            board=read(sa,'ibm-3740',15,'RBBS37.COM')
            if hashlib.sha256(board).hexdigest()!=BOARD_SHA256:raise ValueError('Unrecognized board executable')
            base=Path(manifest['romwbw'])/'Source/Images/d_z3plus/u0/STARTZ3P.COM'
            old=read(sa,'ibm-3740',0,'STARTZ3P.COM')
            new=configure_startup(base,'A0:PATH /C A0;I13:GET CONSOLE;A0:;A0:BYE')
            if old not in (new,configure_startup(base,'A0:PATH /C A0;A:GET CONSOLE;A:BYE')):
                raise ValueError('Custom STARTZ3P requires a manual merge')
            for name in ('DIR.COM','HELP.COM'):
                private=read(si,'z80pack-hd',13,'CPM'+name,optional=True)
                if private is None:put(si,'z80pack-hd',13,'CPM'+name,read(sa,'ibm-3740',0,name))
            get=read(release/'disks/drivei.dsk','z80pack-hd',13,'GET.COM')
            put(si,'z80pack-hd',13,'GET.COM',get)
            names={'zde16.com':'ZDE.COM','zdenst16.com':'ZDENST.COM',
                   'zde16.lbr':'ZDE16.LBR','zde16.new.txt':'ZDE16.NEW','zde16.for.txt':'ZDE16.FOR'}
            for row in reference['editor_sources']:
                data=read(release/'disks/drivei.dsk','z80pack-hd',13,names[row['path']])
                expected=reference['editor_configuration']['sha256'] if row['path']=='zde16.com' else row['sha256']
                if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Release editor changed')
                existing=read(si,'z80pack-hd',13,names[row['path']],optional=True)
                if existing is not None and existing!=data:
                    raise ValueError('Preserve your customized editor before updating: '+names[row['path']])
                put(si,'z80pack-hd',13,names[row['path']],data)
            for name in ('DIR.COM','SDZ.COM','HELP.COM','LDIR.COM','LT.COM','RBBS.COM','STARTZ3P.COM','BYE.COM','BYEDRIV.COM','WELCOME.TXT'):
                data=read(release/'disks/drivea.dsk','ibm-3740',0,name)
                if name in ('DIR.COM','SDZ.COM','HELP.COM','LDIR.COM','LT.COM'):
                    row=next(r for r in reference['caller_tools'] if r['name']==name)
                    if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Release tool changed: '+name)
                if name=='STARTZ3P.COM' and data!=new:raise ValueError('Unexpected release startup')
                if name in ('BYE.COM','BYEDRIV.COM'):
                    build=json.loads((Path(reference['builds'])/'build-result.json').read_text())
                    row=next(r for r in build['files'] if r['path']=='direct/'+name)
                    if build['caller_policy_sha256']!=digest() or hashlib.sha256(data).hexdigest()!=row['sha256']:
                        raise ValueError('Release BYE changed')
                put(sa,'ibm-3740',0,name,data)
                if name=='BYE.COM':put(sa,'ibm-3740',15,name,data)
            if read(sa,'ibm-3740',0,'GET.COM',optional=True) is not None:
                tool('cpmrm','-f','ibm-3740',sa,'0:GET.COM')
            # All persistent RBBS files and allocations remain byte-identical.
            original=i.read_bytes();updated=si.read_bytes()
            for off in range(0,1024*32,32):
                if original[off]==15:
                    if original[off:off+32]!=updated[off:off+32]:raise ValueError('BBS directory changed')
                    for n in range(off+16,off+32,2):
                        block=int.from_bytes(original[n:n+2],'little')
                        if block and original[block*2048:(block+1)*2048]!=updated[block*2048:(block+1)*2048]:
                            raise ValueError('BBS file data changed')
            backups=instance/'backups';backups.mkdir(mode=0o700,exist_ok=True)
            attributes=apply_attributes(sa,tools)
            backup=Path(tempfile.mkdtemp(prefix='before-caller-tools-',dir=backups))
            for p in (a,i,instance/'trial-build.json'):shutil.copyfile(p,backup/p.name)
            manifest.update(caller_policy_sha256=digest(),caller_tools=reference['caller_tools'],
                            builds=reference['builds'],public_rbbs=True,get_location='I13:',
                            editor_sources=reference['editor_sources'],
                            editor_configuration=reference['editor_configuration'],
                            a0_attributes=attributes,
                            caller_tools_backup=str(backup.relative_to(instance)))
            manifest['hashes']['disks/drivea.dsk']=hashlib.sha256(sa.read_bytes()).hexdigest()
            pending=work/'trial-build.json';pending.write_text(json.dumps(manifest,indent=2)+'\n')
            for p in (sa,si,pending):
                with p.open('r+b') as f:os.fsync(f.fileno())
            # I: receives only private additions first. Old A: still boots if
            # interrupted here; new A: never precedes its GET dependency.
            os.replace(si,i);os.replace(sa,a);os.replace(pending,instance/'trial-build.json')
        print('Installed caller tools; existing accounts/messages/passwords retained.')
        print('Rollback copies:',backup)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instance',type=Path,required=True)
    p.add_argument('--release',type=Path,default=Path('build/caller-tools-final'))
    p.add_argument('--cpmtools',type=Path,default=Path('build/cpmtools/bin'))
    a=p.parse_args();upgrade(*(getattr(a,n).resolve() for n in ('instance','release','cpmtools')))
