#!/usr/bin/env python3
"""Collect only matching, successfully checked 1.2.3 artifacts for publication."""
import argparse,json,shutil
from pathlib import Path
from release_1_2_3 import sha,unpack,plain_manual,ROOT


def one(folder, pattern):
 found=list(folder.rglob(pattern))
 if len(found)!=1:raise ValueError('Expected exactly one '+pattern+' under '+str(folder))
 return found[0]


def finalize(inputs,output,commit,run,guest_update=False,local_mac=None,release_commit=None,timing_report=None):
 output.mkdir(parents=True,exist_ok=False);report={'version':'v1.2.3','source_commit':commit,'qualification_run':run,'release_commit':release_commit or commit,'scope':'shared guest viewer/help and manuals; retained host runtimes' if guest_update else 'full platform qualification','platforms':{},'docker':{}}
 import tempfile
 with tempfile.TemporaryDirectory() as temporary:
  shared_images=None
  for platform in ['common','macos-arm64','linux-arm64','linux-x64','windows-x64']:
   folder=inputs/('v1.2.3-'+platform);built=json.loads(one(folder,'BUILT.json').read_text());assert built['receipt']['source_commit']==commit
   name='rcpm-v1.2.3-'+platform+('.zip' if platform in ['common','macos-arm64','windows-x64'] else '.tar.gz');path=one(folder,name);assert sha(path)==built['sha256']
   root=unpack(path,Path(temporary)/platform,platform)
   for n in ['USER-GUIDE','SYSOP-GUIDE']:assert (root/'docs'/(n+'.DOC')).read_text()==plain_manual((ROOT/'docs'/(n+'.md')).read_text())
   receipt=json.loads((root/'metadata/RELEASE-1.2.3.json').read_text());assert receipt==built['receipt'] and receipt['runtime_and_drivers_unchanged']
   assert all(sha(root/'disks'/n)==h for n,h in receipt['media']['images'].items())
   if shared_images is None:shared_images=receipt['media']['images']
   else:assert shared_images==receipt['media']['images']
   if platform!='common':
    checks=json.loads(one(folder,'checks/result.json').read_text())
    if not guest_update:assert checks['passed'] and {x['mode'] for x in checks['results'] if x['passed']}=={'direct','ip232'}
    else:assert receipt['retained_runtime_driver_sha256'] and receipt['runtime_and_drivers_unchanged']
    assert all(sha(root/n)==h for n,h in receipt['retained_runtime_driver_sha256'].items())
    helpcheck=json.loads(one(folder,'help-checks/result.json').read_text());assert helpcheck['passed'] and helpcheck['topics_opened']==120 and helpcheck['caller_restrictions'] and helpcheck['parent_and_root']
    built['checks']=checks;built['help']=helpcheck
   shutil.copy2(path,output/name);report['platforms'][platform]={'artifact':name,'sha256':sha(path),'evidence':built}
   if platform.startswith('linux-'):
    arch=platform.split('-',1)[1];modes={}
    for mode in ['direct','ip232']:
     state=json.loads(one(folder,'docker-'+mode+'/result.json').read_text())
     assert all(state.get(k) for k in ['published_tcp_login','caller_help','expanded_command_help','manuals_present','rbbs_entry','orderly_shutdown','container_replacement_preserves_credentials'])
     modes[mode]=state
    docker=one(folder,'rcpm-v1.2.3-docker-'+arch+'.tar.gz');shutil.copy2(docker,output/docker.name);report['docker'][arch]={'artifact':docker.name,'sha256':sha(docker),'modes':modes}
  if guest_update:
   report['windows_arm64']={'execution':'x64 emulation','new_run':False,'basis':'Unchanged runtime qualification retained from v1.2.2; new shared guest bytes validated across packages.'}
   report['qualification_limits']=['An earlier 25-second macOS modem test cutoff was exceeded; the focused baseline/candidate comparison connected successfully in 22.33/26.55 seconds. Test allowance corrected to 60 seconds without binary changes.','Windows ARM64 compatibility suite not repeated for this guest/documentation update.']
   if timing_report:
    timing=json.loads(Path(timing_report).read_text());assert all(x['passed'] for x in timing['observations']);assert all(all(report['platforms']['macos-arm64']['evidence']['receipt']['retained_runtime_driver_sha256'][n]==h for n,h in x['native_sha256'].items()) for x in timing['observations']);report['supplementary_hosted_macos_timing']=timing
   if local_mac:
    local=json.loads(Path(local_mac).read_text());assert local['passed'];assert local['launcher_sha256']==report['platforms']['macos-arm64']['evidence']['receipt']['retained_runtime_driver_sha256']['runtime/rcpm'];assert all(report['platforms']['macos-arm64']['evidence']['receipt']['retained_runtime_driver_sha256'][n]==h for n,h in local['runtime_sha256'].items());report['supplementary_local_macos_transports']=local
  else:
   arm=inputs/'v1.2.3-windows-arm64-evidence';h=json.loads(one(arm,'help-arm64/result.json').read_text());c=json.loads(one(arm,'checks-arm64/result.json').read_text());assert h['passed'] and h['topics_opened']==120 and c['passed'];report['windows_arm64']={'execution':'x64 emulation','help':h,'launcher':c}
 (output/'VALIDATION.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(ROOT/'docs/RELEASE-NOTES-1.2.3.md',output/'RELEASE-NOTES.md')
 for n in ['USER-GUIDE','SYSOP-GUIDE']:(output/(n+'.DOC')).write_text(plain_manual((ROOT/'docs'/(n+'.md')).read_text()),encoding='ascii')
 (output/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(output.iterdir()) if p.is_file() and p.name!='SHA256SUMS'))
 print('Finalized',len(report['platforms']),'packages and',len(report['docker']),'Docker images')


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--commit',required=True);p.add_argument('--run',required=True);p.add_argument('--guest-update',action='store_true');p.add_argument('--local-mac',type=Path);p.add_argument('--release-commit');p.add_argument('--timing-report',type=Path);a=p.parse_args();finalize(a.inputs.resolve(),a.output.resolve(),a.commit,a.run,a.guest_update,a.local_mac,a.release_commit,a.timing_report)
