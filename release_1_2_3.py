#!/usr/bin/env python3
"""Build checked help/documentation overlays on immutable v1.2.2 packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import textwrap
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parent
BASES = {
 'macos-arm64': ('rcpm-v1.2.2-macos-arm64.zip','4f3168e61ecd7d8fa0bfe122286566636921605a03b154aff49b04457f286976'),
 'linux-arm64': ('rcpm-v1.2.2-linux-arm64.tar.gz','42f216006a447c210ff8212d2e194930710a5e0cd81cbc6087da0aa03937a763'),
 'linux-x64': ('rcpm-v1.2.2-linux-x64.tar.gz','3fda0161b02cd0626f28394089998638a08c6b7769ffc49ba5efeb4c7683d04a'),
 'windows-x64': ('rcpm-v1.2.2-windows-x64.zip','838e7a2b7e5d2574021226b2e1103ff56f8163639105f9ff441bf96d2becb7fe'),
 'common': ('rcpm-v1.2.2-common.zip','1bcd83f70f145e9a83d3c48aeee61fc1a04638bac90194e1d5f0b4048fa7127d')}
VIEWER_SHA='5dc510c41826a2152d8a72849ce5b4e5b91b74fe10cc2ec11444b7fab1c7b962'


def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()


def fetch(platform, folder):
 folder.mkdir(parents=True,exist_ok=True);name,expected=BASES[platform];p=folder/name
 if not p.exists():subprocess.run(['gh','release','download','v1.2.2','--repo','CPMArchives/rcpm-cpmsim','--pattern',name,'--dir',str(folder)],check=True)
 if sha(p)!=expected:raise ValueError('Published base hash mismatch: '+name)
 return p


def unpack(base, output, platform):
 if platform=='common':
  with zipfile.ZipFile(base) as z:
   for n in z.namelist():
    if Path(n).is_absolute() or '..' in Path(n).parts or not n.startswith('rcpm-common/'):raise ValueError('Unsafe common member')
   z.extractall(output)
  root=output/'rcpm-common';m=json.loads((root/'COMMON-MANIFEST.json').read_text());actual={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p.name!='COMMON-MANIFEST.json'}
 else:
  if os.name=='nt':
   from check_windows_release import unpack as extract
  else:
   from check_release import extract_package as extract
  root=extract(base,output);m=json.loads((root/'metadata/MANIFEST.json').read_text());m={**m['common'],**m['host']};actual={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p!=root/'metadata/MANIFEST.json'}
 if actual!=m:raise ValueError('Base contents differ from manifest')
 return root


def plain_manual(text):
 text=text.replace('\u2014',' - ').replace('\u2013','-').replace('\u2018',"'").replace('\u2019',"'").replace('\u201c','"').replace('\u201d','"').replace('\u2022','*').replace('\u2192','->')
 text=unicodedata.normalize('NFKD',text).encode('ascii','replace').decode()
 text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'\1 (\2)',text)
 lines=[]
 for line in text.splitlines():
  line=re.sub(r'^#{1,6} ','',line).replace('**','').replace('`','')
  if not line.strip():lines.append('')
  elif line.startswith('    '):lines.append(line)
  else:lines.extend(textwrap.wrap(line,78,break_long_words=False,break_on_hyphens=False))
 return '\n'.join(lines)+'\n'


def source_files():
 return subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()


def refresh_docs(root):
 for name in ('USER-GUIDE','SYSOP-GUIDE'):
  source=ROOT/'docs'/(name+'.md');(root/'docs'/(name+'.DOC')).write_text(plain_manual(source.read_text()),encoding='ascii');shutil.copy2(source,root/'docs'/(name+'.md'))
 shutil.copy2(ROOT/'docs/RELEASE-NOTES-1.2.3.md',root/'docs/RELEASE-NOTES-1.2.3.md')
 shutil.copy2(ROOT/'docs/RELEASE-NOTES-1.2.3.md',root/'docs/RELEASE-NOTES.md')
 (root/'docs/HELPC-1.5r-NOTICES.txt').write_text('HELPC 1.5r: continuation of Howard Goldstein\'s HELPC 1.5.\nOriginal embedded notice is preserved:\nCopyright (c) Steven Greenberg 8/31/86  201-670-8724. May be reproduced for non-profit use only.\nNo replacement license or commercial permission is asserted.\nThe whole-program/library redistribution grant remains unestablished.\nThe maintainer authorized this binary distribution with that uncertainty disclosed.\nHistorical HELPC source, libraries and proprietary build tools are excluded.\nSee https://github.com/CPMArchives/HELPC/releases/tag/v1.5r for build/test evidence and rights findings.\n')
 project=root/'source/rcpm'
 if project.exists():shutil.rmtree(project)
 for name in source_files():
  p=ROOT/name
  if p.is_file():
   dst=project/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)


def prepare_media(base, viewer, out):
 if sha(base)!=BASES['macos-arm64'][1] or sha(viewer)!=VIEWER_SHA:raise ValueError('Unpinned media/viewer input')
 out.mkdir(parents=True,exist_ok=False);root=unpack(base,out/'base','macos-arm64');tools=root/'runtime';os.environ['DISKDEFS']=str(root/'runtime/diskdefs')
 from caller_help import install
 # Native disk-tool inventory records verify that only viewers/HLP files change.
 def inventory(image,fmt):
  raw=subprocess.check_output([str(tools/'cpmls'),'-A','-f',fmt,str(image)],text=True);user=None;result={}
  for line in raw.splitlines():
   if re.fullmatch(r'\d+:',line.strip()):user=int(line.strip()[:-1])
   elif line.strip():
    attrs,name=line.split();p=out/'read.bin';p.unlink(missing_ok=True);spec=str(user)+':'+name
    subprocess.run([str(tools/'cpmcp'),'-f',fmt,str(image),spec,str(p)],check=True,capture_output=True)
    result[spec.upper()]={'sha256':sha(p),'attributes':attrs}
  return result
 before={d:inventory(root/'disks'/('drive'+d+'.dsk'),fmt) for d,fmt in [('a','ibm-3740'),('i','z80pack-hd')]}
 original_images={('drive'+d+'.dsk'):sha(root/'disks'/('drive'+d+'.dsk')) for d in ['a','i']}
 names=install(root,tools,viewer)
 after={d:inventory(root/'disks'/('drive'+d+'.dsk'),fmt) for d,fmt in [('a','ibm-3740'),('i','z80pack-hd')]}
 for d in before:
  allowed={'0:HELP.COM'} if d=='a' else {'13:ZHELP.COM',*('14:'+n for n in names)}
  assert {n:r for n,r in before[d].items() if n not in allowed}=={n:r for n,r in after[d].items() if n not in allowed}
 coverage=json.loads((ROOT/'docs/command-help-coverage.json').read_text())
 actual_com={(d.upper()+spec.split(':',1)[0]+':'+spec.split(':',1)[1][:-4]):info for d,files in after.items() for spec,info in files.items() if spec.endswith('.COM')}
 expected_com={row['invocation']:row for row in coverage if row['kind']=='COM'}
 assert actual_com.keys()==expected_com.keys(),(actual_com.keys()-expected_com.keys(),expected_com.keys()-actual_com.keys())
 for command,row in expected_com.items():
  assert actual_com[command]['sha256']==row['binary_sha256'],command
  if row['access']=='CALLER':assert actual_com[command]['attributes'][3]=='4',command
 payload=out/'media';payload.mkdir()
 for d in ['a','i']:shutil.copy2(root/'disks'/('drive'+d+'.dsk'),payload/('drive'+d+'.dsk'))
 record={'base_sha256':sha(base),'base_images':original_images,'viewer_sha256':sha(viewer),'topics':len(names),'unrelated_files_unchanged':True,'images':{p.name:sha(p) for p in payload.iterdir()}}
 (payload/'MEDIA.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))


def archive(root,dest):
 if dest.suffix=='.zip':
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
   for p in sorted(root.rglob('*')):z.write(p,p.relative_to(root.parent))
 else:
  with tarfile.open(dest,'w:gz') as z:z.add(root,arcname=root.name)


def build(platform, base, media, output):
 if sha(base)!=BASES[platform][1]:raise ValueError('Unpinned base')
 record=json.loads((media/'MEDIA.json').read_text());assert record['viewer_sha256']==VIEWER_SHA and record['topics']==120 and record['unrelated_files_unchanged']
 for n,h in record['images'].items():assert sha(media/n)==h
 output.mkdir(parents=True,exist_ok=False);root=unpack(base,output/'expanded',platform)
 manifest_path=root/('COMMON-MANIFEST.json' if platform=='common' else 'metadata/MANIFEST.json')
 old=json.loads(manifest_path.read_text());oldfiles=old if platform=='common' else {**old['common'],**old['host']}
 runtime={n:h for n,h in oldfiles.items() if n.startswith(('runtime/','drivers/')) or n=='disks/drivep.dsk'}
 for n in ['drivea.dsk','drivei.dsk']:
  if sha(root/'disks'/n)!=record['base_images'][n]:raise ValueError('Platform guest media differs from the qualified base: '+n)
  shutil.copy2(media/n,root/'disks'/n)
 refresh_docs(root)
 readme=root/'README.txt';text=readme.read_text().replace('1.2.2','1.2.3').replace('Guest media is unchanged from v1.2.1.', 'Guest media retains the verified base except for HELPC 1.5r and expanded help.');text+='\nHELPC 1.5r and 120 online HELP files are installed. Type HELP COMMANDS.\nRead docs/USER-GUIDE.DOC and docs/SYSOP-GUIDE.DOC for the complete manuals.\nFresh release media only: do not unpack over an existing board.\n';readme.write_text(text)
 for n in ['LINUX-README.txt','WINDOWS-README.txt']:
  if (root/n).exists():(root/n).write_text(text)
 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 receipt={'version':'v1.2.3','platform':platform,'source_commit':commit,'base_sha256':sha(base),'media':record,'runtime_and_drivers_unchanged':True,'retained_runtime_driver_sha256':runtime,'manual_sources':{n:sha(ROOT/'docs'/(n+'.md')) for n in ['USER-GUIDE','SYSOP-GUIDE']}}
 (root/'metadata').mkdir(exist_ok=True);(root/'metadata/RELEASE-1.2.3.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert not (root/'SYSOP.DOC').exists()
 assert all(sha(root/n)==h for n,h in runtime.items())
 assert not any(p.name.upper() in ['HELPC15.Z80','HELPCCFG.Z80','Z80ASM.COM','SLRNK.COM'] for p in root.rglob('*') if p.is_file())
 files={p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p!=manifest_path}
 if platform=='common':new=files
 else:
  common={n:h for n,h in files.items() if n in old['common'] or n.startswith(('docs/','source/rcpm/','metadata/RELEASE-1.2.3'))};new={**old,'version':'v1.2.3','status':'help-overlay-checks-pending','common':common,'host':{n:h for n,h in files.items() if n not in common}}
 manifest_path.write_text(json.dumps(new,indent=2)+'\n')
 suffix='.zip' if platform in ['common','macos-arm64','windows-x64'] else '.tar.gz';dest=output/('rcpm-v1.2.3-'+platform+suffix);archive(root,dest)
 result={'package':str(root.resolve()),'archive':str(dest.resolve()),'sha256':sha(dest),'receipt':receipt};(output/'BUILT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));return result


if __name__=='__main__':
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='action',required=True)
 a=s.add_parser('media');a.add_argument('--base',type=Path,required=True);a.add_argument('--viewer',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
 a=s.add_parser('package');a.add_argument('--platform',choices=BASES,required=True);a.add_argument('--media',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--inputs',type=Path,default=Path('inputs'))
 a=p.parse_args()
 if a.action=='media':prepare_media(a.base.resolve(),a.viewer.resolve(),a.output.resolve())
 else:build(a.platform,fetch(a.platform,a.inputs.resolve()),a.media.resolve(),a.output.resolve())
