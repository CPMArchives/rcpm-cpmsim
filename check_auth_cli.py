#!/usr/bin/env python3
"""Check AUTH query/permission spellings and named policy I/O in a real guest."""
import argparse, json, os, subprocess
from pathlib import Path
from check_bye_speed import prepare
from check_release import Guest,free_port
from auth_policy import install

REPO=Path(__file__).resolve().parent

def run(args):
 out=args.output;out.mkdir(parents=True,exist_ok=False);p=out/'instance'
 prepare(args.package,p,args.builds,args.runtime)
 install(p,args.tools,args.source/'z80asm/z80asm')
 # A malformed alternate policy and an unapproved COM for query tests.
 def put(user,name,data):
  f=out/'put.bin';f.write_bytes(data)
  for tool,values in [('cpmrm',['-f','z80pack-hd',p/'disks/drivei.dsk',f'{user}:{name}']),('cpmcp',['-f','z80pack-hd',p/'disks/drivei.dsk',f,f'{user}:{name}'])]:
   subprocess.run([str(args.tools/tool),*map(str,values)],check=True,capture_output=True)
 put(13,'BAD.DAT',b'BADFILE!'+bytes(376))
 put(13,'SHORT.DAT',b'RCPMAU01'+bytes(120))
 put(0,'DEMO.COM',b'\xc9') # startup WORK cleanup will remove this; seed elsewhere
 put(1,'DEMO.COM',b'\xc9')
 port=free_port();g=Guest(p,out/'console','--port',str(port))
 def local(command,mark=b'A0:SYSTEM>'):
  start=len(g.local)
  for c in (command+'\r').encode():os.write(g.master,bytes([c]));g.collect(.003)
  reply=g.wait(mark,start=start)
  return reply.replace(b'\r',b'')
 def answer(text,mark=b'A0:SYSTEM>'):
  start=len(g.local)
  for c in (text+'\r').encode():os.write(g.master,bytes([c]));g.collect(.003)
  return g.wait(mark,start=start).replace(b'\r',b'')
 def auth(text,expected=b'changed in memory'):
  print('AUTH '+text,flush=True)
  reply=local('SYSUTLS:AUTH '+text,expected if expected.endswith(b':') else b'A0:SYSTEM>')
  assert expected in reply,(text,reply)
  return reply
 def row(reply,drive):return next(l for l in reply.splitlines() if l.startswith(drive.encode()+b':'))
 result={}
 try:
  g.wait(b'RCP/M modem ready.');g.connect(port)
  n=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote off]',start=n);g.collect(.2)
  for target in ('J:','J3:'):
   reply=auth(target,b'Effective caller access')
   assert len([l for l in reply.splitlines() if len(l)>1 and l[1:2]==b':'])==1,reply
   assert b'J:' in reply
  for command in ('','/MAP'):
   reply=auth(command,b'Effective caller access')
   assert len([l for l in reply.splitlines() if len(l)>1 and l[1:2]==b':'])==16
  for value,cell in [('/RW',b'*RW'),('R-',b'*R-'),('/W',b'*-W'),('--',b'*--'),('RW',b'*RW'),('/R',b'*R-'),('-W',b'*-W'),('/NONE',b'*--'),('R',b'*R-'),('W',b'*-W'),('NONE',b'*--')]:
   auth('J3: '+value)
   assert row(auth('J3:',b'Effective caller access'),'J')[15:18]==cell,(value,reply)
  auth('J3: /INHERIT')
  assert row(auth('J:',b'Effective caller access'),'J')[15:18]==b' R-'
  result['queries_and_permission_spellings']=True
  # Existing files report actual effective caller executability, not just F4.
  auth('J1:ADV.COM',b'not found') # no GAMES mounted yet
  local('MOUNT GAMES')
  auth('J1:ADV.COM',b'is executable.')
  auth('J1:ADV.COM -X',b'F4 updated')
  auth('J1:ADV.COM',b'F4 is not set')
  auth('J1:ADV.COM +X',b'F4 updated')
  auth('J1: RW');auth('J1:ADV.COM',b'DU is caller-writable')
  auth('J1: NONE');auth('J1:ADV.COM',b'no caller read access')
  auth('J1: INHERIT')
  result['effective_file_status']=True
  auth('J: /NONE')
  auth('/SAVE=I13:PUBLIC.DAT',b'Policy saved to I13:PUBLIC.DAT')
  auth('J: /R')
  denied=auth('/SAVE=I13:PUBLIC.DAT',b'File exists; use /Y')
  auth('/LOAD=I13:PUBLIC.DAT',b'Policy loaded from I13:PUBLIC.DAT')
  assert b' R-' not in row(auth('J:',b'Effective caller access'),'J')
  auth('J: /R')
  auth('/SAVE=I13:PUBLIC.DAT /Y',b'Policy saved')
  auth('/LOAD=I13:PUBLIC.BAK',b'Policy loaded')
  assert b' R-' not in row(auth('J:',b'Effective caller access'),'J')
  auth('/LOAD=I13:PUBLIC.DAT',b'Policy loaded')
  assert b' R-' in row(auth('J:',b'Effective caller access'),'J')
  for file in ('BAD.DAT','SHORT.DAT'):
   before=row(auth('J:',b'Effective caller access'),'J')
   auth('/LOAD=I13:'+file,b'Invalid or incomplete policy')
   assert row(auth('J:',b'Effective caller access'),'J')==before
  auth('/LOAD=I13:NOFILE.DAT',b'not found')
  # Bare forms prompt; Enter chooses the fixed startup policy.
  auth('/SAVE',b'Save policy to [I13:AUTH.DAT]:')
  reply=answer('',b'Overwrite (Y/N)?');reply=answer('N')
  assert b'Cancelled' in reply
  auth('/SAVE',b'Save policy to [I13:AUTH.DAT]:')
  answer('I13:INTER.DAT')
  auth('/LOAD',b'Load policy from [I13:AUTH.DAT]:')
  reply=answer('I13:INTER.DAT');assert b'Policy loaded' in reply,reply
  auth('/LOAD',b'Load policy from [I13:AUTH.DAT]:')
  reply=answer('');assert b'Policy loaded from I13:AUTH.DAT' in reply,reply
  auth('/SAVE=I13:AUTH.DAT /Y',b'Policy saved')
  result.update(named_policy_save_load=True,no_prompt_overwrite_guard=True,overwrite_backup=True,invalid_load_preserves_live_map=True,interactive_names_and_cancel=True,startup_filename_unchanged=True)
  n=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote on]',start=n);g.collect(.2)
  g.stop()
 finally:g.close()
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n,default in [('package','build/release-auth-map/RCPM-macOS-arm64'),('builds','build/bye5'),('runtime','build/modem/cpmsim'),('tools','build/release-tools/bin'),('source','/tmp/rcpm-z80pack.8ScWG5')]:p.add_argument('--'+n,type=Path,default=Path(default))
 p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 for n,v in vars(a).items():setattr(a,n,v.resolve())
 run(a)
