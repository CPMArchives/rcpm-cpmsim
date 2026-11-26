#!/usr/bin/env python3
"""Destructive qualification: ONLY a disposable VM with the explicit marker."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pty
import signal
import socket
import subprocess
import time
import tty

EVIDENCE = Path('/var/tmp/rcpm-vm-evidence')
INSTANCE = Path('/var/lib/rcpm/instance')


def run(*args, check=True, timeout=180):
    p = subprocess.run(list(map(str,args)), capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f'{args}: exit {p.returncode}: {p.stdout[-2000:]} {p.stderr[-2000:]}')
    return p


def ctl(*args, check=True):
    return run('runuser','-u','rcpm','--','/usr/local/bin/rcpmctl',*args,check=check,timeout=360)


def status():
    return json.loads(ctl('status').stdout)


def ready(timeout=180):
    deadline = time.monotonic()+timeout
    while time.monotonic()<deadline:
        if run('systemctl','is-active','rcpm',check=False).stdout.strip()=='active':
            try:
                if status()['ready']:
                    return status()
            except (RuntimeError,ValueError):
                pass
        time.sleep(.3)
    raise RuntimeError('RCP/M did not become ready: '+run('systemctl','status','rcpm','--no-pager',check=False).stdout)


def hashed(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


class Caller:
    def __init__(self):
        # The one modem line can briefly reject redial while BYE cleans up
        # the previous caller. Readiness confirms startup, not line availability.
        deadline=time.monotonic()+60
        last=None
        while time.monotonic()<deadline:
            try:
                self.s=socket.create_connection(('127.0.0.1',4000),timeout=5)
                self.s.settimeout(.25)
                self.until(b'A0:SYSTEM>',timeout=min(45,deadline-time.monotonic()))
                return
            except (OSError,RuntimeError) as error:
                last=error
                if hasattr(self,'s'):self.s.close()
                time.sleep(.5)
        raise RuntimeError('Caller redial never became ready') from last
    def until(self,marker,timeout=45):
        data=bytearray();deadline=time.monotonic()+timeout
        while marker not in data and time.monotonic()<deadline:
            try:
                block=self.s.recv(16384)
                if not block:raise RuntimeError('Caller disconnected: '+repr(data[-300:]))
                data.extend(block)
            except socket.timeout:pass
        if marker not in data:raise RuntimeError('Missing caller prompt: '+repr(data[-300:]))
        return bytes(data)
    def help(self):
        for b in b'HELP\r':self.s.sendall(bytes([b]));time.sleep(.03)
        data=self.until(b'A0:SYSTEM>')
        assert len(data)>100,data
        return len(data)
    def close(self):self.s.close()


def credentials():return hashed(INSTANCE/'SYSOP.DOC')


def record(name,result):
    EVIDENCE.mkdir(mode=0o755,exist_ok=True)
    (EVIDENCE/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


def install(package):
    assert not INSTANCE.exists()
    assert run('getent','passwd','rcpm',check=False).returncode!=0
    preflight=run(package/'Install-Service.sh','--check')
    assert not INSTANCE.exists()
    assert run('getent','passwd','rcpm',check=False).returncode!=0
    installed=run(package/'Install-Service.sh','--install')
    (EVIDENCE/'installer.log').write_text(preflight.stdout+installed.stdout+installed.stderr)
    assert run('systemctl','is-active','rcpm',check=False).stdout.strip()=='inactive'
    assert run('systemctl','is-enabled','rcpm',check=False).stdout.strip()=='disabled'
    assert run('systemctl','is-enabled','rcpm-backup.timer',check=False).stdout.strip()=='disabled'
    assert not (INSTANCE/'SYSOP.DOC').exists()
    user=json.loads(run('python3','-c','import pwd,json; p=pwd.getpwnam("rcpm"); print(json.dumps({"uid":p.pw_uid,"gid":p.pw_gid,"shell":p.pw_shell}))').stdout)
    assert 0<user['uid']<1000 and user['shell'].endswith('nologin')
    run('getent','group','rcpm')
    assert Path('/usr/local/lib/rcpm/rcpm_service.py').stat().st_uid==0
    assert Path('/etc/rcpm/service.conf').stat().st_uid==0
    verified=run('systemd-analyze','verify','/etc/systemd/system/rcpm.service','/etc/systemd/system/rcpm-backup.service','/etc/systemd/system/rcpm-backup.timer')
    before=hashed(INSTANCE/'disks/drivei.dsk')
    refused=run(package/'Install-Service.sh','--install',check=False)
    assert refused.returncode!=0
    assert before==hashed(INSTANCE/'disks/drivei.dsk')
    record('installer',dict(preflight_read_only=True,fresh_install=True,user=user,initially_stopped_disabled=True,
           root_owned_helpers=True,unit_verification=True,repeat_install_refused_without_data_change=True,
           systemd_verify_stderr=verified.stderr))


def startup():
    run('systemctl','start','rcpm',timeout=180)
    state=ready()
    c=Caller();amount=c.help();c.close()
    listeners=run('ss','-lntp').stdout
    for port in (4000,24000,25232):
        matches=[line for line in listeners.splitlines() if f':{port} ' in line]
        assert matches and all(f'127.0.0.1:{port}' in line for line in matches),matches
    pids=[state[k] for k in ('guest_pid','tcpser_pid')]
    run('systemctl','stop','rcpm')
    assert run('systemctl','is-active','rcpm',check=False).stdout.strip()=='inactive'
    for pid in pids:assert not Path(f'/proc/{pid}').exists()
    assert run('systemctl','show','rcpm','-p','Result','--value').stdout.strip()=='success'
    run('systemctl','start','rcpm');ready()
    # Attach with a private PTY, then detach without terminating the service.
    for _ in range(2):
        master,slave=pty.openpty();tty.setraw(slave)
        p=subprocess.Popen(['runuser','-u','rcpm','--','rcpmctl','attach'],stdin=slave,stdout=slave,stderr=slave)
        time.sleep(.5);assert p.poll() is None
        os.write(master,b'\x1d');assert p.wait(timeout=5)==0
        os.close(master);os.close(slave)
    c=Caller()
    stopping=subprocess.Popen(['systemctl','stop','rcpm'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    deadline=time.monotonic()+10
    while not status()['draining']:
        assert time.monotonic()<deadline;time.sleep(.1)
    assert stopping.poll() is None and status()['active']==1
    with socket.create_connection(('127.0.0.1',4000),timeout=3) as rejected:
        rejected.settimeout(3);assert rejected.recv(1)==b''
    c.help();c.close()
    assert stopping.wait(timeout=150)==0
    assert run('systemctl','show','rcpm','-p','Result','--value').stdout.strip()=='success'
    run('systemctl','enable','rcpm');run('systemctl','start','rcpm');ready()
    baseline=dict(credential_sha256=credentials(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    (EVIDENCE/'baseline.json').write_text(json.dumps(baseline))
    record('startup-shutdown',dict(real_systemd_notify_start=True,caller_HELP_bytes=amount,loopback_listeners=True,
           idle_stop_clean_no_child_processes=True,private_console_reattach=True,
           active_call_drains_without_interruption=True,new_calls_refused_during_stop=True,
           enabled_for_reboot=True))


def after_reboot(label):
    baseline=json.loads((EVIDENCE/'baseline.json').read_text())
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    assert boot!=baseline['boot_id']
    ready();assert credentials()==baseline['credential_sha256']
    c=Caller();c.help();c.close()
    baseline['boot_id']=boot
    (EVIDENCE/'baseline.json').write_text(json.dumps(baseline))
    record(label,dict(changed_kernel_boot_id=True,automatic_systemd_start=True,caller_HELP=True,credentials_preserved=True))


def backup():
    old=set(Path('/var/backups/rcpm').glob('snapshot-*'))
    since=str(int(time.time()))
    run('systemctl','start','rcpm-backup.service',timeout=600)
    assert run('systemctl','show','rcpm-backup.service','-p','Result','--value').stdout.strip()=='success'
    ready()
    journal=run('journalctl','-u','rcpm','--since','@'+since,'--no-pager').stdout
    (EVIDENCE/'backup-unit-journal.log').write_text(journal)
    assert 'Failed with result' not in journal and 'Control process exited' not in journal,journal
    new=set(Path('/var/backups/rcpm').glob('snapshot-*'))-old
    assert len(new)==1,new
    snapshot=new.pop();ctl('verify',snapshot)
    target=Path('/var/lib/rcpm/restored-vm-test')
    ctl('restore',snapshot,'--output',target)
    assert hashed(target/'SYSOP.DOC')==credentials()
    assert hashed(target/'disks/drivei.dsk')==hashed(snapshot/'instance/disks/drivei.dsk')
    # Boot the restored snapshot under the same real unit, preserving original media.
    run('systemctl','stop','rcpm')
    INSTANCE.rename('/var/lib/rcpm/original-vm-test-'+str(int(time.time())))
    target.rename(INSTANCE)
    run('systemctl','start','rcpm');ready()
    c=Caller();c.help();c.close()
    record('backup-restore',dict(real_systemd_backup_unit=True,verified_snapshot=True,automatic_restart_after_backup=True,
           restored_disk_hash=True,restored_credentials=True,restored_systemd_boot_and_caller=True))


def recover(component):
    previous=ready();old_main=int(run('systemctl','show','rcpm','-p','MainPID','--value').stdout)
    old_credentials=credentials()
    target={'tcpser':previous['tcpser_pid'],'guest':previous['guest_pid'],'supervisor':old_main}[component]
    os.kill(target,signal.SIGKILL)
    deadline=time.monotonic()+180;new=None
    while time.monotonic()<deadline:
        main=int(run('systemctl','show','rcpm','-p','MainPID','--value').stdout)
        if main and main!=old_main:
            try:
                new=ready(timeout=15);break
            except RuntimeError:pass
        time.sleep(.5)
    if not new:raise RuntimeError('Automatic recovery failed: '+run('systemctl','status','rcpm','--no-pager',check=False).stdout)
    assert credentials()==old_credentials
    c=Caller();c.help();c.close()
    # There must be exactly one current guest/modem pair and no old children.
    for key in ('guest_pid','tcpser_pid'):
        assert new[key]!=previous[key]
        assert not Path('/proc/'+str(previous[key])).exists(),(component,key,previous[key])
    record('recovery-'+component,dict(killed_only_disposable_component=component,automatic_systemd_restart=True,
           no_old_child_processes=True,credentials_preserved=True,caller_HELP=True))


def failed_backup():
    old_credentials=credentials()
    good=sorted(Path('/var/backups/rcpm').glob('snapshot-*'))[-1]
    before=hashed(good/'snapshot.json')
    target=Path('/var/backups/rcpm/existing-failure-target')
    target.mkdir(exist_ok=True)
    before_state=ready()
    failure=ctl('backup','--output',target,check=False)
    assert failure.returncode!=0
    time.sleep(15)  # exceeds RestartSec=10: a failed backup must stay stopped
    assert run('systemctl','is-active','rcpm',check=False).stdout.strip()=='inactive'
    assert run('systemctl','show','rcpm','-p','Result','--value').stdout.strip()=='success'
    for key in ('guest_pid','tcpser_pid'):assert not Path('/proc/'+str(before_state[key])).exists()
    assert hashed(good/'snapshot.json')==before
    ctl('verify',good)
    run('systemctl','start','rcpm');ready()
    assert credentials()==old_credentials
    record('failed-backup',dict(backup_error_reported=True,service_remained_stopped=True,
           no_false_unit_failure_or_restart=True,last_good_snapshot_unchanged_and_valid=True,
           credentials_preserved=True))


def timer():
    old=set(Path('/var/backups/rcpm').glob('snapshot-*'))
    since=str(int(time.time()))
    stamp=Path('/var/lib/systemd/timers/stamp-rcpm-backup.timer')
    stamp.parent.mkdir(parents=True,exist_ok=True)
    stamp.touch();os.utime(stamp,(time.time()-172800,time.time()-172800))
    run('systemctl','start','rcpm-backup.timer')
    try:
        deadline=time.monotonic()+180
        while not (set(Path('/var/backups/rcpm').glob('snapshot-*'))-old):
            assert time.monotonic()<deadline;time.sleep(.5)
        ready()
        new=set(Path('/var/backups/rcpm').glob('snapshot-*'))-old
        assert len(new)==1,new
        ctl('verify',new.pop())
        journal=run('journalctl','-u','rcpm','--since','@'+since,'--no-pager').stdout
        assert 'Failed with result' not in journal,journal
        assert run('systemctl','show','rcpm-backup.service','-p','Result','--value').stdout.strip()=='success'
        record('persistent-timer',dict(real_shipped_calendar_timer=True,missed_run_caught_up=True,
               verified_snapshot=True,service_restarted_cleanly=True))
    finally:
        run('systemctl','stop','rcpm-backup.timer')


def stop_timeout():
    override=Path('/etc/systemd/system/rcpm.service.d/vm-timeout-test.conf')
    override.parent.mkdir(exist_ok=True)
    override.write_text('[Service]\nTimeoutStopSec=5\n')
    run('systemctl','daemon-reload')
    caller=None
    stop_requested=False
    old_main=None
    try:
        old=ready();old_main=int(run('systemctl','show','rcpm','-p','MainPID','--value').stdout)
        caller=Caller()
        stop_requested=True
        stopping=run('systemctl','stop','rcpm',check=False,timeout=30)
        observed=dict(stop_timeout_reported_by_unit=run('systemctl','show','rcpm','-p','Result','--value').stdout.strip()=='timeout',
                      guest_alive_after_timeout=Path('/proc/'+str(old['guest_pid'])).exists(),
                      modem_alive_after_timeout=Path('/proc/'+str(old['tcpser_pid'])).exists())
        observed['caller_still_works']=caller.help()>100
        control=ctl('status',check=False)
        observed['private_control_still_accessible']=control.returncode==0
        record('stop-timeout-observations',observed)
        assert all(observed.values()),observed
    finally:
        if caller:caller.close()
        override.unlink(missing_ok=True)
        run('systemctl','daemon-reload')
        if stop_requested and old_main:
            deadline=time.monotonic()+30
            while Path('/proc/'+str(old_main)).exists() and time.monotonic()<deadline:time.sleep(.2)
            assert not Path('/proc/'+str(old_main)).exists(),'Old supervisor did not finish after caller drained'
        run('systemctl','reset-failed','rcpm')
        run('systemctl','start','rcpm');ready()
    record('stop-timeout',dict(shortened_timeout_fault_injection=True,no_forced_guest_termination=True,
           caller_continued=True,private_control_preserved=True,drained_later_and_restarted=True))


def main():
    if os.geteuid()!=0:
        raise SystemExit('Run only as root inside the marked disposable VM')
    marker=Path('/etc/rcpm-disposable-test')
    if not marker.is_file() or marker.read_text().strip()!='rcpm-local-qualification-v1' or not Path('/run/systemd/system').exists():
        raise SystemExit('Refusing to run without the disposable-VM marker and real systemd')
    EVIDENCE.mkdir(mode=0o755,exist_ok=True)
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['install','startup','after-reboot','backup','recover-tcpser','recover-guest','recover-supervisor','failed-backup','timer','stop-timeout'])
    p.add_argument('--package',type=Path)
    p.add_argument('--label',default='reboot')
    a=p.parse_args()
    if a.phase=='install':install(a.package)
    elif a.phase=='startup':startup()
    elif a.phase=='after-reboot':after_reboot(a.label)
    elif a.phase=='backup':backup()
    elif a.phase=='failed-backup':failed_backup()
    elif a.phase=='timer':timer()
    elif a.phase=='stop-timeout':stop_timeout()
    else:recover(a.phase.removeprefix('recover-'))


if __name__=='__main__':main()
