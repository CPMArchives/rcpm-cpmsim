#!/usr/bin/env python3
"""Check the optional Windows add-on with one disposable, user-owned board."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


def run(*args,check=True,timeout=360):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=timeout)
    if check and result.returncode:raise RuntimeError('Command failed: '+str(args)+'\n'+result.stdout+'\n'+result.stderr)
    return result


def port():
    with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]


def until_prompt(caller):
    deadline=time.monotonic()+120;data=b'';caller.settimeout(.25)
    while b'A0:SYSTEM>' not in data:
        if time.monotonic()>=deadline:raise RuntimeError('Caller prompt timed out')
        try:part=caller.recv(16384)
        except socket.timeout:continue
        if not part:raise RuntimeError('Caller disconnected before prompt')
        data+=part
        if len(data)>65536:raise RuntimeError('Caller response limit exceeded')
    return data


def check(base,addon,output):
    if sys.platform!='win32':raise SystemExit('Windows required')
    output.mkdir(parents=True,exist_ok=False);stage='preflight';result={};home=None;admin=None
    with tempfile.TemporaryDirectory(prefix='rcpm-win-admin-') as tmp:
        home=Path(tmp)/'Private board with spaces'
        installer=addon/'Install-Hosting.py'
        try:
            run(sys.executable,'-B',installer,'--package',base,'--home',home,'--check')
            assert not home.exists()
            run(sys.executable,'-B',installer,'--package',base,'--home',home,'--install')
            assert run(sys.executable,'-B',installer,'--package',base,'--home',home,'--install',check=False).returncode
            sys.path.insert(0,str(home/'helpers'));import win_admin as admin
            before=admin.store.files(base)
            cfg=admin.config(home)
            for key in ('port','caller_port','modem_port'):cfg[key]=port()
            assert len({cfg[key] for key in ('port','caller_port','modem_port')})==3
            admin.store.atomic(home/'admin.json',cfg)
            controller=[sys.executable,'-B',home/'helpers/win_admin.py','--home',home]
            def ctl(*args,**kwargs):return run(*controller,*args,**kwargs)
            def state():return json.loads(ctl('status').stdout)
            def wait_for(predicate,timeout=150):
                deadline=time.monotonic()+timeout
                while time.monotonic()<deadline:
                    try:
                        value=predicate()
                        if value:return value
                    except (OSError,RuntimeError,json.JSONDecodeError):pass
                    time.sleep(.3)
                raise RuntimeError('Timed out at '+stage)
            for job in ('board','backup','monitor'):
                assert not json.loads(ctl('task-status',job).stdout)['registered']
            assert not (home/'run/state.json').exists()
            stage='worker startup';ctl('start');status=state();assert status['ready']
            worker_pid=status['worker_pid'];guest_pid=status['guest_pid'];modem_pid=status['tcpser_pid']
            print('Passed: private worker and modem startup',flush=True)
            stage='caller HELP';sequence=status['ready_sequence']
            with socket.create_connection(('127.0.0.1',cfg['port']),timeout=5) as caller:
                until_prompt(caller)
                for byte in b'HELP\r':caller.sendall(bytes([byte]));time.sleep(.03)
                assert len(until_prompt(caller))>100
                assert json.loads(ctl('health','--probe').stdout)['status']=='deferred'
            stage='caller cleanup'
            wait_for(lambda:state()['ready_sequence']>sequence and state()['ready'])
            print('Passed: caller HELP, probe deferral and carrier cleanup',flush=True)
            stage='idle probe';time.sleep(11)
            probe=json.loads(ctl('health','--probe').stdout);assert probe['status']=='passed'
            print('Probe timings:',json.dumps(probe),flush=True)
            stage='monitor';ctl('monitor');assert not json.loads((home/'monitor/state.json').read_text())['issues']
            stage='console protection'
            with admin.connect(home) as link:
                link.send_bytes(b'{"action":"attach"}');admin.receive(link,10)
                assert state()['attached']
                assert json.loads(ctl('health','--probe').stdout)['status']=='deferred'
                assert ctl('stop',check=False).returncode
                assert state()['ready']
                link.send_bytes(b'{"detach":true}')
            wait_for(lambda:not state()['attached'],timeout=10)
            stage='scheduled task registration'
            for job in ('backup','monitor','board'):
                ctl('enable',job);assert json.loads(ctl('task-status',job).stdout)['registered']
                xml=run('powershell.exe','-NoProfile','-NonInteractive','-Command',
                        'Export-ScheduledTask -TaskName "'+cfg['task_prefix']+'-'+job+'"').stdout
                tree=ET.fromstring(xml);ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
                assert tree.find('.//t:LogonType',ns).text=='InteractiveToken'
                assert tree.find('.//t:RunLevel',ns).text=='LeastPrivilege'
                if job=='board':assert tree.find('.//t:LogonTrigger',ns) is not None
                elif job=='backup':assert 'T03:00:00' in tree.find('.//t:StartBoundary',ns).text
                else:assert tree.find('.//t:Repetition/t:Interval',ns).text=='PT5M'
            print('Passed: per-user, limited-privilege task definitions',flush=True)
            stage='scheduled backup and restart'
            run('powershell.exe','-NoProfile','-NonInteractive','-Command',
                'Start-ScheduledTask -TaskName "'+cfg['task_prefix']+'-backup"')
            def backed_up():
                path=home/'backup-status.json'
                if not path.exists():return False
                value=json.loads(path.read_text())
                if not value['passed']:raise ValueError('Scheduled backup failed: '+value.get('error','unknown'))
                return state()['ready']
            wait_for(backed_up,timeout=360)
            print('Passed: Task Scheduler backup and board restart',flush=True)
            snapshots=list((home/'backups').glob('snapshot-*'));assert len(snapshots)==1
            stage='verified recovery';ctl('verify',snapshots[0])
            restored=Path(tmp)/'Recovered board';ctl('restore',snapshots[0],'--output',restored)
            assert (restored/'SYSOP.DOC').read_bytes()==(home/'instance/SYSOP.DOC').read_bytes()
            stage='scheduled monitor';previous=json.loads((home/'monitor/state.json').read_text())['checked_at']
            run('powershell.exe','-NoProfile','-NonInteractive','-Command',
                'Start-ScheduledTask -TaskName "'+cfg['task_prefix']+'-monitor"')
            wait_for(lambda:json.loads((home/'monitor/state.json').read_text())['checked_at']>previous,timeout=150)
            assert not json.loads((home/'monitor/state.json').read_text())['issues']
            stage='clean stop and task removal'
            for job in ('monitor','backup','board'):
                ctl('disable',job);assert not json.loads(ctl('task-status',job).stdout)['registered']
            final=json.loads((home/'run/state.json').read_text());assert not final['running'] and final['exit_code']==0
            assert admin.platform.process_exited(final['worker_pid'])
            # First worker/children also exited after the scheduled backup.
            assert all(admin.platform.process_exited(pid) for pid in (worker_pid,guest_pid,modem_pid))
            assert admin.store.files(base)==before
            stage='complete'
            result=dict(passed=True,windows_build=sys.getwindowsversion().build,
                        architecture=os.environ.get('PROCESSOR_ARCHITECTURE'),
                        read_only_preflight=True,private_per_user_install=True,repeat_install_refused=True,
                        defaults_stopped_disabled=True,background_console=True,caller_HELP=True,
                        carrier_cleanup=True,active_caller_probe_deferred=True,idle_probe=probe,
                        attached_console_protected=True,user_task_definitions=True,scheduled_backup_and_restart=True,
                        verified_restore_and_credentials=True,scheduled_monitor=True,clean_stop_and_task_removal=True,
                        child_processes_exited=True,base_package_unchanged=True,
                        scope='Per-user Windows administration, not a system service')
        except Exception as error:
            result=dict(passed=False,stage=stage,error=str(error))
            if home and (home/'run/state.json').exists():result['worker_state']=json.loads((home/'run/state.json').read_text())
            raise
        finally:
            (output/'VALIDATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print(json.dumps(result,indent=2),flush=True)
            if admin and home and (home/'admin.json').exists():
                # Only this disposable board's worker and unique tasks are eligible.
                try:run(*controller,'stop',check=False,timeout=160)
                except Exception:pass
                for job in ('monitor','backup','board'):
                    try:run(*controller,'disable',job,check=False,timeout=180)
                    except Exception:pass


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('base','addon','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();check(a.base.resolve(),a.addon.resolve(),a.output.resolve())
