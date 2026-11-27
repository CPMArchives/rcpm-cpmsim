#!/usr/bin/env python3
"""Optional, per-user macOS launchd administration. No root installation."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import time

import rcpm_service as service
import rcpm_monitor as monitor

DEFAULT_HOME=Path.home()/'Library/Application Support/RCPMAdmin'


def command(*args,check=True):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=30)
    if check and result.returncode:
        raise RuntimeError('Command failed: '+str(args)+'\n'+result.stdout+'\n'+result.stderr)
    return result


def load(home):return json.loads((home/'admin.json').read_text())


def job(home,name):
    config=load(home);return config['domain']+'/'+config['label']+'.'+name


def pid(home,name='board'):
    response=command('/bin/launchctl','print',job(home,name),check=False)
    match=re.search(r'^\s*pid = (\d+)',response.stdout,re.M)
    return int(match[1]) if match else None


def registered(home,name):
    return command('/bin/launchctl','print',job(home,name),check=False).returncode==0


def start(home,name='board'):
    if registered(home,name):
        if name=='board' and pid(home,name):return
        command('/bin/launchctl','kickstart',job(home,name))
    else:
        command('/bin/launchctl','bootstrap',load(home)['domain'],home/'jobs'/(name+'.plist'))
    if name=='board':
        deadline=time.monotonic()+150
        while time.monotonic()<deadline:
            try:
                if service.request(home/'run','status',socket_timeout=3)['ready']:return
            except (OSError,RuntimeError):pass
            time.sleep(.3)
        raise RuntimeError('Board did not become ready; see logs/board.err.log')


def stop(home):
    if pid(home):
        service.request(home/'run','stop')
        deadline=time.monotonic()+20
        while pid(home) and time.monotonic()<deadline:time.sleep(.2)
        if pid(home):raise RuntimeError('Board still running; agent was not unloaded')
    if registered(home,'board'):command('/bin/launchctl','bootout',job(home,'board'))


@contextlib.contextmanager
def exclusive(home):
    with (home/'administration.lock').open('a') as stream:
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield


def schedule(home,name,enabled):
    target=Path.home()/'Library/LaunchAgents'/(load(home)['label']+'.'+name+'.plist')
    if enabled:
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(home/'jobs'/(name+'.plist'),target)
        if not registered(home,name):command('/bin/launchctl','bootstrap',load(home)['domain'],target)
    else:
        if name=='board':stop(home)
        elif pid(home,name):raise RuntimeError('Scheduled job is active; wait before disabling it')
        elif registered(home,name):command('/bin/launchctl','bootout',job(home,name))
        target.unlink(missing_ok=True)


def backup(home):
    status=home/'backup-status.json'
    with exclusive(home):
        try:
            (home/'maintenance').touch()
            destination=home/'backups'/time.strftime('snapshot-%Y%m%dT%H%M%SZ',time.gmtime())
            service.request(home/'run','backup',str(destination))
            service.verify(destination)
            status.write_text(json.dumps(dict(passed=True,snapshot=str(destination)))+'\n')
            deadline=time.monotonic()+20
            while pid(home) and time.monotonic()<deadline:time.sleep(.2)
            start(home)
            print(destination)
        except Exception as error:
            status.write_text(json.dumps(dict(passed=False,error=str(error)))+'\n')
            raise
        finally:(home/'maintenance').unlink(missing_ok=True)


def check_monitor(home,probe=True):
    config=monitor.load_config(home/'monitor.json')
    if not (home/'monitor.json').exists() or 'probe_timeout' not in json.loads((home/'monitor.json').read_text()):
        config['probe_timeout']=120
    config.update(data_path=str(home),backup_path=str(home/'backups'))
    state_path=home/'monitor/state.json'
    with monitor.monitor_lock(home/'monitor/state.lock'):
        previous=json.loads(state_path.read_text()) if state_path.exists() else {}
        issues=monitor.space_issues(home,config)
        backup_state=home/'backup-status.json'
        if backup_state.exists() and not json.loads(backup_state.read_text())['passed']:
            issues['backup-failed']='Last backup failed; inspect backup-status.json'
        running=pid(home)
        guest=dict(status='deferred',reason='board_stopped')
        if (home/'maintenance').exists():guest=dict(status='deferred',reason='backup_maintenance')
        elif running and probe:
            try:
                guest=service.request(home/'run','probe',probe_timeout=config['probe_timeout'],socket_timeout=config['probe_timeout']+5)
                if guest.get('status')=='failed':issues['guest-unresponsive']='Idle caller probe failed'
            except (OSError,RuntimeError):
                issues['guest-unresponsive']='Private control unavailable';guest=dict(status='failed')
        if running and guest.get('status')=='deferred' and 'guest-unresponsive' in previous.get('issues',{}):
            issues['guest-unresponsive']=previous['issues']['guest-unresponsive']
        if registered(home,'board'):
            data=command('/bin/launchctl','print',job(home,'board')).stdout
            match=re.search(r'last exit code = (\d+)',data)
            if match and int(match[1]):issues['service-failed']='launchd reports an unsuccessful previous board exit'
        return monitor.save_state(state_path,previous,issues,dict(guest=guest,board_pid=running),time.time())


def install(addon,base,home,label='org.cpmarchives.rcpm'):
    if sys.platform!='darwin' or os.geteuid()==0:raise RuntimeError('Install as your ordinary macOS account, without sudo')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',label):raise ValueError('Invalid launchd label')
    from mac_preflight import validate
    receipt=validate(addon,base)
    if receipt['platform']!='macos-arm64':raise RuntimeError('macOS ARM64 package required')
    if home.exists():raise RuntimeError('Existing administration home refused; preserve its data')
    if len(str(home/'run/control.sock').encode())>=100:raise RuntimeError('Choose a shorter administration home path for the private socket')
    domain='gui/'+str(os.getuid())
    if command('/bin/launchctl','print',domain,check=False).returncode:domain='user/'+str(os.getuid())
    for name in ('board','backup','monitor'):
        if command('/bin/launchctl','print',domain+'/'+label+'.'+name,check=False).returncode==0:
            raise RuntimeError('An agent with this label is already registered')
        if (Path.home()/'Library/LaunchAgents'/(label+'.'+name+'.plist')).exists():
            raise RuntimeError('Existing login agent refused')
    home.mkdir(mode=0o700,parents=True)
    for name in ('jobs','logs','run','backups','monitor'): (home/name).mkdir(mode=0o700)
    shutil.copytree(addon/'helpers',home/'helpers')
    shutil.copytree(base,home/'instance')
    config=dict(domain=domain,label=label,address='127.0.0.1',port=4000,caller_port=24000,modem_port=25232)
    (home/'admin.json').write_text(json.dumps(config,indent=2)+'\n')
    python=sys.executable
    entry=home/'helpers/rcpm_admin.py'
    for name in ('board','backup','monitor'):
        values=dict(Label=label+'.'+name,ProgramArguments=[python,'-B',str(entry),'--home',str(home),'supervise' if name=='board' else name],
                    WorkingDirectory=str(home),Umask=0o077,
                    StandardOutPath=str(home/'logs'/(name+'.log')),StandardErrorPath=str(home/'logs'/(name+'.err.log')))
        if name=='board':values.update(RunAtLoad=True,KeepAlive=dict(SuccessfulExit=False),ThrottleInterval=10,ExitTimeOut=300)
        elif name=='backup':values['StartCalendarInterval']=dict(Hour=3,Minute=0)
        else:values['StartInterval']=300
        with (home/'jobs'/(name+'.plist')).open('wb') as stream:plistlib.dump(values,stream)
    import shlex
    (home/'rcpm-admin').write_text('#!/bin/sh\nexec '+shlex.quote(python)+' -B '+shlex.quote(str(entry))+' --home '+shlex.quote(str(home))+' "$@"\n')
    (home/'rcpm-admin').chmod(0o700)
    print('Installed, stopped, with login startup and schedules disabled.\nController: '+str(home/'rcpm-admin'))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home',type=Path,default=DEFAULT_HOME)
    sub=p.add_subparsers(dest='action',required=True)
    for name in ('start','stop','status','attach','resume','backup','monitor','alerts','supervise'):sub.add_parser(name)
    health=sub.add_parser('health');health.add_argument('--probe',action='store_true')
    for name in ('enable','disable'):
        s=sub.add_parser(name);s.add_argument('job',choices=('board','backup','monitor'))
    for name in ('verify','restore'):
        s=sub.add_parser(name);s.add_argument('snapshot',type=Path)
        if name=='restore':s.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv);home=a.home.expanduser().absolute();os.umask(0o077)
    if a.action=='supervise':
        original=service.Supervisor
        class LaunchdSupervisor(original):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs);self.child_new_session=False
        service.Supervisor=LaunchdSupervisor
        cfg=load(home)
        sys.argv=['rcpm-service','--run-dir',str(home/'run'),'run','--instance',str(home/'instance'),
            '--tcpser',str(home/'instance/runtime/tcpser'),'--address',cfg['address'],'--port',str(cfg['port']),
            '--caller-port',str(cfg['caller_port']),'--modem-port',str(cfg['modem_port'])]
        service.main()
    elif a.action=='start':start(home)
    elif a.action=='stop':
        with exclusive(home):stop(home)
    elif a.action in ('enable','disable'):schedule(home,a.job,a.action=='enable')
    elif a.action=='backup':backup(home)
    elif a.action=='monitor':
        result=check_monitor(home);print(json.dumps(dict(issues=len(result['issues']),guest=result['guest'])))
        if result['issues']:raise SystemExit(1)
    elif a.action=='alerts':print((home/'monitor/state.json').read_text())
    elif a.action=='verify':print(json.dumps(dict(verified_files=len(service.verify(a.snapshot)))))
    elif a.action=='restore':service.restore(a.snapshot,a.output)
    elif a.action=='attach':service.request(home/'run','attach')
    else:
        action='probe' if a.action=='health' and a.probe else a.action
        result=service.request(home/'run','status' if action=='health' else action,
                               probe_timeout=120,socket_timeout=125 if action=='probe' else 300)
        print(json.dumps(result))
        if a.action=='health' and (result.get('status')=='failed' or (action=='health' and not result['ready'])):raise SystemExit(1)


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as error:raise SystemExit(str(error))
