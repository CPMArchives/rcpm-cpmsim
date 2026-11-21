#!/usr/bin/env python3
"""Reproduce SCOTT.dsk from the checked collection payload using RCP/M cpmtools.
Usage: build_image.py COLLECTION TOOLS OUTPUT
"""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,shutil
collection,tools,output=(Path(s).resolve() for s in sys.argv[1:]);m=json.loads((collection/'manifest.json').read_text());assert not output.exists(),'Refusing to overwrite an image'
sha=lambda b:hashlib.sha256(b).hexdigest();env=dict(os.environ,DISKDEFS=str(tools/'diskdefs'))
def run(name,*args):return subprocess.check_output([str(tools/name),'-f','z80pack-hd',*map(str,args)],env=env)
with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
 im=Path(tmp)/'SCOTT.dsk';run('mkfs.cpm',im)
 with im.open('r+b') as f:f.truncate(4177920)
 seen=set()
 for row in m['payload']:
  name=row['file'];assert row['user']==0 and re.fullmatch(r'[A-Z0-9_-]{1,8}(?:\.[A-Z0-9]{1,3})?',name),name;assert name not in seen;seen.add(name);source=collection/row['payload'];assert sha(source.read_bytes())==row['sha256'],name
  run('cpmcp',im,source,'0:'+name);run('cpmchattr',im,'r4' if row['approved'] else 'r','0:'+name)
  check=Path(tmp)/'readback';run('cpmcp',im,'0:'+name,check);assert check.read_bytes()[:row['bytes']]==source.read_bytes(),name
 data=bytearray(im.read_bytes());used=set(range(16))
 for off in range(0,32768,32):
  e=data[off:off+32]
  if e[0]<16:used.update(int.from_bytes(e[i:i+2],'little') for i in range(16,32,2) if e[i:i+2]!=b'\0\0')
 for block in range(16,2040):
  if block not in used:data[block*2048:(block+1)*2048]=b'\0'*2048
 im.write_bytes(data)
 assert sha(data)==m['image_sha256'],'Rebuilt image differs'
 shutil.copyfile(im,output)
print('Verified image:',output)
