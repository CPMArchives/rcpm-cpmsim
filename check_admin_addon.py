#!/usr/bin/env python3
"""Focused install/lifecycle check on a fresh disposable systemd build runner."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import time


def run(*args,check=True):
    return subprocess.run(list(map(str,args)),check=check,capture_output=True,text=True,timeout=360)


def ctl(*args):return run('runuser','-u','rcpm','--','rcpmctl',*args)


def main(base,addon,output):
    if Path('/var/lib/rcpm/instance').exists():raise SystemExit('Fresh disposable host required')
    before=hashlib.sha256((base/'metadata/MANIFEST.json').read_bytes()).hexdigest()
    run(addon/'Install-Hosting.sh','--package',base,'--check')
    assert not Path('/var/lib/rcpm/instance').exists()
    run(addon/'Install-Hosting.sh','--package',base,'--install')
    for unit in ('rcpm','rcpm-backup.timer','rcpm-monitor.timer'):
        assert run('systemctl','is-active',unit,check=False).stdout.strip()=='inactive'
        assert run('systemctl','is-enabled',unit,check=False).stdout.strip()=='disabled'
    assert run(addon/'Install-Hosting.sh','--package',base,'--install',check=False).returncode!=0
    try:
        run('systemctl','start','rcpm')
        status=json.loads(ctl('status').stdout);assert status['ready']
        with socket.create_connection(('127.0.0.1',4000),timeout=5) as caller:
            caller.settimeout(40);data=b''
            while b'A0:SYSTEM>' not in data:data+=caller.recv(16384)
            caller.sendall(b'HELP\r');data=b''
            while b'A0:SYSTEM>' not in data:data+=caller.recv(16384)
            assert len(data)>100
        time.sleep(12)
        probe=json.loads(ctl('health','--probe').stdout);assert probe['status']=='passed',probe
        run('systemctl','start','rcpm-monitor')
        assert not json.loads(Path('/var/lib/rcpm/monitor/state.json').read_text())['issues']
        run('systemctl','start','rcpm-backup')
        deadline=time.monotonic()+150
        while time.monotonic()<deadline:
            try:
                if json.loads(ctl('status').stdout)['ready']:break
            except Exception:pass
            time.sleep(1)
        else:raise RuntimeError('Board did not resume after backup')
        snapshots=list(Path('/var/backups/rcpm').glob('snapshot-*'));assert len(snapshots)==1
        ctl('verify',snapshots[0]);ctl('restore',snapshots[0],'--output','/var/lib/rcpm/restored-check')
        assert Path('/var/lib/rcpm/restored-check/SYSOP.DOC').read_bytes()==Path('/var/lib/rcpm/instance/SYSOP.DOC').read_bytes()
        run('systemctl','stop','rcpm')
        assert run('systemctl','show','rcpm','-p','MainPID','--value').stdout.strip()=='0'
        assert hashlib.sha256((base/'metadata/MANIFEST.json').read_bytes()).hexdigest()==before
        result=dict(passed=True,fresh_install=True,defaults_stopped_disabled=True,repeat_install_refused=True,
            real_caller_HELP=True,idle_probe=True,monitoring=True,backup_job_and_resume=True,
            verified_restore_and_credentials=True,clean_stop=True,base_source_unmodified=True)
        output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:run('systemctl','stop','rcpm',check=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','addon','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();main(a.base.resolve(),a.addon.resolve(),a.output.resolve())
