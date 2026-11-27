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


def until_prompt(caller):
    deadline=time.monotonic()+45;data=b''
    while b'A0:SYSTEM>' not in data:
        if time.monotonic()>=deadline:raise RuntimeError('Caller prompt deadline expired')
        part=caller.recv(16384)
        if not part:raise RuntimeError('Caller disconnected before prompt')
        data+=part
        if len(data)>65536:raise RuntimeError('Caller response exceeded limit')
    return data


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
        # Enable the supervisor's existing private trace in this disposable test
        # only; never enable console logging in an installed user's agent.
        diagnostic=home/'diagnostic.py'
        diagnostic.write_text('import sys\nsys.path.insert(0,'+repr(str(home/'helpers'))+')\nimport rcpm_admin as a\noriginal=a.service.main\ndef traced():\n sys.argv.extend(["--trace-console",'+repr(str(home/'private-console.log'))+'])\n original()\na.service.main=traced\na.main()\n')
        board_plist=home/'jobs/board.plist'
        values=plistlib.loads(board_plist.read_bytes());values['ProgramArguments'][2]=str(diagnostic)
        board_plist.write_bytes(plistlib.dumps(values))
        for name in ('board','backup','monitor'):
            assert run('/bin/launchctl','print',config['domain']+'/'+label+'.'+name,check=False).returncode
            assert not (Path.home()/'Library/LaunchAgents'/(label+'.'+name+'.plist')).exists()
        try:
            run(ctl,'start')
            assert json.loads(run(ctl,'status').stdout)['ready']
            print('Passed: launchd startup',flush=True)
            with socket.create_connection(('127.0.0.1',config['port']),timeout=5) as caller:
                caller.settimeout(40);until_prompt(caller)
                for byte in b'HELP\r':caller.sendall(bytes([byte]));time.sleep(.03)
                data=until_prompt(caller)
                assert len(data)>100
                print('Passed: caller HELP',flush=True)
                # Observe a fresh modem initialization after this caller leaves.
                # A fixed sleep can call back during BYE's carrier-loss cleanup.
                console=socket.socket(socket.AF_UNIX)
                console.connect(str(home/'run/control.sock'))
                console.sendall(b'{"action":"attach"}\n');reply=b''
                while not reply.endswith(b'\n'):reply+=console.recv(1)
                assert json.loads(reply)['ok']
            try:
                console.settimeout(60);reset=b''
                while b'ATE0Q0V0S0=0M0S10=25X1H0\r\n0\r\n' not in reset:
                    part=console.recv(16384)
                    if not part:raise RuntimeError('Console closed during carrier cleanup')
                    reset=(reset+part)[-65536:]
            finally:console.close()
            print('Passed: caller carrier cleanup',flush=True)
            time.sleep(12)
            probe=json.loads(run(ctl,'health','--probe').stdout)
            assert probe['status']=='passed'
            print('Probe timings:',json.dumps(probe),flush=True)
            print('Passed: idle probe',flush=True)
            run(ctl,'monitor')
            assert not json.loads((home/'monitor/state.json').read_text())['issues']
            run(ctl,'backup')
            print('Passed: backup and restart',flush=True)
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
            trace=home/'private-console.log'
            if trace.exists():
                data=trace.read_bytes();marker=b'ATE0Q0V0S0=0M0S10=25X1H0\r\n0\r\n'
                # Emit only fixed labels and counts, never any console bytes.
                print('Modem diagnostic counts:',json.dumps({
                    'initialized':data.count(marker),
                    'initialization_commands':data.count(b'ATE0Q0V0S0=0M0S10=25X1H0'),
                    'numeric_ok':data.count(b'\r\n0\r\n'),
                    'no_carrier':data.count(b'NO CARRIER'),
                    'numeric_no_carrier':data.count(b'\r\n3\r\n'),
                    'system_prompt':data.count(b'A0:SYSTEM>'),
                    'console_bytes':len(data)}),flush=True)
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
