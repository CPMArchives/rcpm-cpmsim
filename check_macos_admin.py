#!/usr/bin/env python3
"""Check a launchd add-on using an isolated disposable board and unique labels."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import tempfile
import time


def run(*args,check=True):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=360)
    if check and result.returncode:
        raise RuntimeError('Command failed: '+str(args)+'\n'+result.stdout+'\n'+result.stderr)
    return result


def free_port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def check(base,addon,output,session_only=False):
    if sys.platform!='darwin':raise SystemExit('macOS required')
    label='org.cpmarchives.rcpm.test'+str(os.getpid())
    before=hashlib.sha256((base/'metadata/MANIFEST.json').read_bytes()).hexdigest()
    output.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-la-',dir='/tmp') as temporary:
        home=Path(temporary)/'admin'
        install=addon/'Install-Hosting.py'
        ctl=home/'rcpm-admin'
        run(sys.executable,'-B',install,'--package',base,'--home',home,'--label',label,'--check')
        assert not home.exists()
        run(sys.executable,'-B',install,'--package',base,'--home',home,'--label',label,'--install')
        assert run(sys.executable,'-B',install,'--package',base,'--home',home,'--label',label,'--install',check=False).returncode
        config=json.loads((home/'admin.json').read_text())
        for n in ('port','caller_port','modem_port'):config[n]=free_port()
        assert len({config[n] for n in ('port','caller_port','modem_port')})==3
        (home/'admin.json').write_text(json.dumps(config))
        for name in ('board','backup','monitor'):
            assert run('/bin/launchctl','print',config['domain']+'/'+label+'.'+name,check=False).returncode
            assert not (Path.home()/'Library/LaunchAgents'/(label+'.'+name+'.plist')).exists()
        try:
            run(ctl,'start')
            assert json.loads(run(ctl,'status').stdout)['ready']
            with socket.create_connection(('127.0.0.1',config['port']),timeout=5) as caller:
                caller.settimeout(40);data=b''
                while b'A0:SYSTEM>' not in data:data+=caller.recv(16384)
                caller.sendall(b'HELP\r');data=b''
                while b'A0:SYSTEM>' not in data:data+=caller.recv(16384)
                assert len(data)>100
            time.sleep(12)
            assert json.loads(run(ctl,'health','--probe').stdout)['status']=='passed'
            run(ctl,'monitor')
            assert not json.loads((home/'monitor/state.json').read_text())['issues']
            run(ctl,'backup')
            assert json.loads(run(ctl,'status').stdout)['ready']
            snapshots=list((home/'backups').glob('snapshot-*'));assert len(snapshots)==1
            run(ctl,'verify',snapshots[0])
            recovered=Path(temporary)/'restored'
            run(ctl,'restore',snapshots[0],'--output',recovered)
            assert (recovered/'SYSOP.DOC').read_bytes()==(home/'instance/SYSOP.DOC').read_bytes()
            if not session_only:
                for name in ('backup','monitor','board'):
                    run(ctl,'enable',name)
                    assert (Path.home()/'Library/LaunchAgents'/(label+'.'+name+'.plist')).exists()
            backup=plistlib.loads((home/'jobs/backup.plist').read_bytes())
            monitoring=plistlib.loads((home/'jobs/monitor.plist').read_bytes())
            assert backup['StartCalendarInterval']=={'Hour':3,'Minute':0}
            assert monitoring['StartInterval']==300
            # An attached sysop must not be probed or stopped.
            sys.path.insert(0,str(home/'helpers'))
            import rcpm_service as service
            link=socket.socket(socket.AF_UNIX);link.connect(str(home/'run/control.sock'))
            link.sendall(b'{"action":"attach"}\n');reply=b''
            while not reply.endswith(b'\n'):reply+=link.recv(1)
            assert json.loads(reply)['ok']
            try:
                result=json.loads(run(ctl,'health','--probe').stdout);assert result['status']=='deferred'
                assert run(ctl,'stop',check=False).returncode
                assert json.loads(run(ctl,'status').stdout)['ready']
            finally:link.close()
            time.sleep(1)
            if session_only:run(ctl,'stop')
            else:
                run(ctl,'disable','monitor');run(ctl,'disable','backup');run(ctl,'disable','board')
            assert hashlib.sha256((base/'metadata/MANIFEST.json').read_bytes()).hexdigest()==before
            result=dict(passed=True,read_only_preflight=True,per_user_install=True,repeat_install_refused=True,
                stopped_disabled_defaults=True,launchd_start=True,caller_HELP=True,probe=True,monitor=True,
                verified_backup_restore=True,backup_restarts_board=True,login_and_schedules_opt_in=not session_only,
                schedules_plist_validated=True,
                attached_console_protected=True,clean_stop_and_disable=True,base_source_unchanged=True,
                scope='User launchd agent, not a boot-time system daemon')
            (output/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n')
            print(json.dumps(result,indent=2),flush=True)
        except Exception:
            for p in (home/'logs').glob('*'):
                print(p.name,p.read_text(errors='replace')[-6000:],flush=True)
            raise
        finally:
            for name in ('monitor','backup','board'):
                if session_only:
                    if name=='board':run(ctl,'stop',check=False)
                else:run(ctl,'disable',name,check=False)
                # Only this test's unique labels are eligible for final cleanup.
                run('/bin/launchctl','bootout',config['domain']+'/'+label+'.'+name,check=False)
                if not session_only:(Path.home()/'Library/LaunchAgents'/(label+'.'+name+'.plist')).unlink(missing_ok=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','addon','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--session-only',action='store_true',help='Use temporary agents only; do not write login registration files')
    a=p.parse_args();check(a.base.resolve(),a.addon.resolve(),a.output.resolve(),a.session_only)
