"""Optional per-user Windows RCP/M administration. Python standard library only."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import select
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid

import win_store as store
import win_platform as platform

READY=b'ATE0Q0V0S0=0M0S10=25X1H0\n0\n'


def default_home():return Path(os.environ['LOCALAPPDATA'])/'RCPMAdmin'
def config(home):return json.loads((home/'admin.json').read_text())
def emit(value):
    if sys.stdout is not None:print(json.dumps(value),flush=True)


def connect(home):
    from multiprocessing.connection import Client
    cfg=config(home)
    if cfg['owner_sid']!=platform.sid():raise RuntimeError('Use the Windows account that installed this board')
    return Client(cfg['pipe'],family='AF_PIPE',authkey=bytes.fromhex((home/'control.key').read_text()))


def receive(link,timeout=300):
    if not link.poll(timeout):raise RuntimeError('Administration request timed out; board was not forcibly stopped')
    reply=json.loads(link.recv_bytes(1048576))
    if not reply.get('ok'):raise RuntimeError(reply.get('error','Administration request failed'))
    return reply.get('result')


def request(home,action,**values):
    with connect(home) as link:
        link.send_bytes(json.dumps(dict(action=action,**values)).encode())
        return receive(link)


def install(addon,base,home):
    if sys.platform!='win32':raise RuntimeError('Windows required')
    store.validate(addon,base)
    if home.exists():raise ValueError('Existing administration home refused; preserve its board data')
    if any('%' in str(p) or '\n' in str(p) or '\r' in str(p) for p in (home,Path(sys.executable))):
        raise ValueError('Administration and Python paths cannot contain percent signs or newlines')
    owner=platform.sid();platform.private_directory(home,owner)
    for name in ('run','backups','monitor','helpers'):(home/name).mkdir()
    for path in (addon/'helpers').iterdir():shutil.copy2(path,home/'helpers'/path.name)
    shutil.copytree(base,home/'instance')
    identity=uuid.uuid4().hex
    cfg=dict(owner_sid=owner,python=sys.executable,pipe='\\\\.\\pipe\\rcpm-admin-'+identity,
             task_prefix='RCPM-'+identity,address='127.0.0.1',port=4000,
             caller_port=24000,modem_port=25232,probe_timeout=120)
    store.atomic(home/'admin.json',cfg)
    (home/'control.key').write_text(os.urandom(32).hex(),encoding='ascii')
    # cmd.exe expands percent signs even in double quotes. Refuse such install
    # paths rather than generating a misleading or unsafe command wrapper.
    (home/'rcpm-admin.cmd').write_bytes(('@echo off\r\nchcp 65001 >nul\r\n"'+sys.executable+'" -B "'+str(home/'helpers/win_admin.py')+
                                     '" --home "'+str(home)+'" %*\r\n').encode('utf-8'))
    emit(dict(installed=str(home),started=False,schedules_enabled=False))


class Worker:
    def __init__(self,home):
        self.home,self.cfg=home,config(home);self.root=home/'instance'
        self.mutex=threading.RLock();self.condition=threading.Condition(self.mutex)
        self.operation=threading.Lock();self.history=bytearray();self.marker_buffer=bytearray()
        self.total=0;self.ready_sequence=0;self.ready_at=0;self.active=0;self.cleaning=False
        self.attached=None;self.probing=False;self.draining=False;self.stopping=False
        self.ready=False;self.failure=None;self.guest=None;self.modem=None
        self.idle_since=time.monotonic();self.exit_code=1

    def status(self):
        with self.mutex:
            return dict(ready=self.ready and not(self.cleaning or self.probing or self.draining)
                        and time.monotonic()-self.ready_at>=3,
                        active=self.active,attached=self.attached is not None,draining=self.draining,
                        cleaning=self.cleaning,probing=self.probing,ready_sequence=self.ready_sequence,
                        worker_pid=os.getpid(),guest_pid=self.guest.pid if self.guest else None,
                        tcpser_pid=self.modem.pid if self.modem else None,failure=self.failure)

    def collect(self):
        data=self.console.collect()
        if not data:return
        with self.condition:
            self.history.extend(data);del self.history[:-131072];self.total+=len(data)
            self.marker_buffer.extend(data);del self.marker_buffer[:-65536]
            while READY in self.marker_buffer:
                position=self.marker_buffer.index(READY)+len(READY)
                del self.marker_buffer[:position]
                self.ready_sequence+=1;self.ready_at=time.monotonic();self.cleaning=False
            self.condition.notify_all()

    def wait_ready(self,sequence,deadline):
        with self.condition:
            while self.ready_sequence<=sequence or time.monotonic()-self.ready_at<3:
                if self.guest.poll() is not None or time.monotonic()>=deadline:
                    raise RuntimeError('Guest modem initialization was not acknowledged')
                self.condition.wait(.1)

    def relay(self,caller):
        peer=None
        try:
            peer=socket.create_connection(('127.0.0.1',self.cfg['caller_port']),timeout=5)
            caller.settimeout(5);peer.settimeout(5)
            while not self.stopping:
                for source in select.select([caller,peer],[],[],.2)[0]:
                    data=source.recv(16384)
                    if not data:return
                    (peer if source is caller else caller).sendall(data)
        except OSError:pass
        finally:
            with self.mutex:
                self.cleaning=True
                caller.close()
                if peer:
                    with contextlib.suppress(OSError):peer.shutdown(socket.SHUT_RDWR)
                    peer.close()
                self.active-=1;self.idle_since=time.monotonic()

    def callers(self):
        while not self.stopping:
            if not select.select([self.listener],[],[],.2)[0]:continue
            caller,_=self.listener.accept()
            with self.mutex:
                if not self.status()['ready'] or self.active:
                    caller.close();continue
                self.active+=1
            threading.Thread(target=self.relay,args=(caller,),daemon=True).start()

    def probe(self):
        if not self.operation.acquire(blocking=False):return dict(status='deferred',reason='operator_operation')
        started=time.monotonic();reserved=False;phase='reserve';timings={}
        try:
            with self.mutex:
                if self.active or self.attached or not self.status()['ready']:
                    return dict(status='deferred',reason='caller_console_or_maintenance')
                if time.monotonic()-self.idle_since<10:return dict(status='deferred',reason='carrier_cleanup')
                self.probing=reserved=True
            deadline=started+self.cfg['probe_timeout'];phase='login'
            with socket.create_connection(('127.0.0.1',self.cfg['caller_port']),timeout=5) as caller:
                caller.settimeout(.25)
                def prompt():
                    data=b''
                    while b'A0:SYSTEM>' not in data:
                        if time.monotonic()>=deadline:raise RuntimeError('Caller probe timed out')
                        try:part=caller.recv(16384)
                        except socket.timeout:continue
                        if not part:raise RuntimeError('Caller probe disconnected')
                        data+=part
                        if len(data)>65536:raise RuntimeError('Caller probe exceeded response limit')
                    return data
                prompt();timings['login_seconds']=round(time.monotonic()-started,3)
                phase='HELP'
                for byte in b'HELP\r':caller.sendall(bytes([byte]));time.sleep(.03)
                reply=prompt()
                if len(reply)<100 or b'HELP?' in reply:raise RuntimeError('Caller probe did not return HELP')
                timings['transaction_seconds']=round(time.monotonic()-started,3)
                with self.mutex:sequence=self.ready_sequence;self.cleaning=True
                caller.shutdown(socket.SHUT_RDWR)
            phase='carrier_cleanup';self.wait_ready(sequence,deadline)
            result=dict(status='passed',scope='caller HELP and carrier cleanup')
        except (OSError,RuntimeError) as error:result=dict(status='failed',phase=phase,error=str(error))
        finally:
            with self.mutex:
                if reserved:self.probing=False;self.idle_since=time.monotonic()
            self.operation.release()
        return dict(result,seconds=round(time.monotonic()-started,3),**timings)

    def marker(self,marker,start,timeout=120):
        deadline=time.monotonic()+timeout
        with self.condition:
            while True:
                offset=max(0,start-(self.total-len(self.history)))
                if marker in self.history[offset:]:return
                if self.guest.poll() is not None or time.monotonic()>=deadline:
                    raise RuntimeError('Guest did not acknowledge shutdown stage')
                self.condition.wait(.1)

    def stop(self):
        with self.mutex:
            if self.attached:raise RuntimeError('Detach the sysop console before stopping or backing up')
            if not self.ready:raise RuntimeError('Guest is not ready for graceful shutdown')
            self.draining=True
        deadline=time.monotonic()+120
        while self.active or self.cleaning or time.monotonic()-self.ready_at<3:
            if time.monotonic()>=deadline:raise RuntimeError('Caller or cleanup still active; left running with new calls disabled')
            time.sleep(.1)
        with self.mutex:start=self.total
        self.console.write(b'\x03');self.marker(b'<RET> for',start)
        with self.mutex:start=self.total
        self.console.write(b'\r');self.marker(b'A0:SYSTEM>',start)
        for byte in b'SYSUTLS:BYEBYE\r':self.console.write(bytes([byte]));time.sleep(.06)
        try:code=self.guest.wait(timeout=120)
        except subprocess.TimeoutExpired:raise RuntimeError('Guest shutdown timed out; no forced termination performed')
        if code:raise RuntimeError('Guest exited unsuccessfully')
        self.exit_code=0;self.stopping=True

    def handle(self,link):
        try:
            if not link.poll(5):raise ValueError('No administration request')
            message=json.loads(link.recv_bytes(8192));action=message['action']
            if action=='status':result=self.status()
            elif action=='probe':result=self.probe()
            elif action=='attach':
                identity=uuid.uuid4().hex
                with self.mutex:
                    if self.attached or self.operation.locked() or self.draining or not self.ready:
                        raise RuntimeError('Console is busy or board is stopping')
                    self.attached=identity;previous=None
                try:
                    link.send_bytes(b'{"ok":true}')
                    while not self.stopping:
                        frame=self.console.frame()
                        if frame!=previous:
                            link.send_bytes(json.dumps(dict(output=frame)).encode());previous=frame
                        if link.poll(.05):
                            command=json.loads(link.recv_bytes(8192))
                            if command.get('detach'):break
                            if 'special' in command:self.console.special(command['special']);continue
                            data=bytes.fromhex(command['input'])
                            if len(data)>1024:raise ValueError('Console input too large')
                            self.console.write(data)
                finally:
                    with self.mutex:
                        if self.attached==identity:self.attached=None
                return
            elif action=='resume':
                with self.operation,self.mutex:
                    if self.cleaning or self.guest.poll() is not None:raise RuntimeError('Return the guest to modem-ready state before resuming')
                    self.draining=False;self.failure=None
                result=dict(resumed=True)
            elif action in ('stop','backup'):
                with self.operation:
                    try:
                        self.stop()
                        if action=='backup':store.snapshot(self.root,Path(message['output']))
                        result=dict(stopped=True)
                        link.send_bytes(json.dumps(dict(ok=True,result=result)).encode())
                    except Exception as error:
                        self.failure=str(error)
                        link.send_bytes(json.dumps(dict(ok=False,error=str(error))).encode())
                return
            else:raise ValueError('Unknown administration action')
            link.send_bytes(json.dumps(dict(ok=True,result=result)).encode())
        except (Exception,) as error:
            with contextlib.suppress(Exception):link.send_bytes(json.dumps(dict(ok=False,error=str(error))).encode())
        finally:link.close()

    def controls(self):
        from multiprocessing import AuthenticationError
        while not self.stopping:
            try:link=self.server.accept()
            except (AuthenticationError,EOFError,OSError):continue
            threading.Thread(target=self.handle,args=(link,),daemon=True).start()

    def run(self):
        try:
            self.job=platform.Job();self.console=platform.Console()
            with platform.lease(self.home/'run/worker.lock'):
                for port in (self.cfg['port'],self.cfg['caller_port'],self.cfg['modem_port']):
                    with socket.socket() as test:
                        test.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
                        test.bind((self.cfg['address'] if port==self.cfg['port'] else '127.0.0.1',port))
                self.server=platform.PipeServer(self.cfg['pipe'],self.cfg['owner_sid'],
                                               bytes.fromhex((self.home/'control.key').read_text()))
                threading.Thread(target=self.controls,daemon=True).start()
                self.modem=subprocess.Popen([str(self.root/'runtime/tcpser.exe'),'-v','127.0.0.1:'+str(self.cfg['modem_port']),
                    '-p','127.0.0.1:'+str(self.cfg['caller_port']),'-s','2400','-S','2400','-i','e0v1&c1&d2','-l','0'],
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
                self.guest=subprocess.Popen([str(self.root/'runtime/rcpm.exe'),'--external-modem','--mode','ip232',
                    '--address','127.0.0.1','--port',str(self.cfg['modem_port'])],cwd=self.root)
                self.listener=socket.socket();self.listener.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
                self.listener.bind((self.cfg['address'],self.cfg['port']));self.listener.listen(4)
                deadline=time.monotonic()+120;last_state=0
                while not self.stopping:
                    self.collect()
                    if not self.ready and self.ready_sequence and time.monotonic()-self.ready_at>=3:
                        self.ready=True;threading.Thread(target=self.callers,daemon=True).start()
                    if self.modem.poll() is not None or (self.guest.poll() is not None and not self.draining):
                        raise RuntimeError('Guest or bundled modem exited unexpectedly')
                    if not self.ready and time.monotonic()>=deadline:raise RuntimeError('Guest startup was not acknowledged')
                    if time.monotonic()-last_state>=1:
                        store.atomic(self.home/'run/state.json',dict(self.status(),running=True));last_state=time.monotonic()
                    time.sleep(.025)
                with self.operation:pass
        except Exception as error:
            self.failure=str(error);self.exit_code=1
        finally:
            self.stopping=True;self.ready=False
            for child in (self.guest,self.modem):
                if child and child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
            store.atomic(self.home/'run/state.json',dict(running=False,worker_pid=os.getpid(),exit_code=self.exit_code,error=self.failure))
        return self.exit_code


def start(home,wait=False):
    with platform.lease(home/'run/start.lock'):
        try:
            existing=request(home,'status')
            if existing['ready']:return existing
            raise RuntimeError('A worker is already starting, busy or draining; inspect status')
        except (FileNotFoundError,ConnectionError):pass
        cfg=config(home);startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        child=subprocess.Popen([cfg['python'],'-B',str(home/'helpers/win_admin.py'),'--home',str(home),'worker'],
                               cwd=home,creationflags=subprocess.CREATE_NEW_CONSOLE|subprocess.CREATE_NEW_PROCESS_GROUP,
                               startupinfo=startup)
        deadline=time.monotonic()+150
        while time.monotonic()<deadline:
            if child.poll() is not None:
                state=json.loads((home/'run/state.json').read_text()) if (home/'run/state.json').exists() else {}
                raise RuntimeError('Worker failed to start: '+str(state.get('error','see run/state.json')))
            try:
                state=request(home,'status')
                if state['ready']:break
            except (OSError,RuntimeError):pass
            time.sleep(.25)
        else:raise RuntimeError('Worker startup timed out; inspect status before retrying')
    if wait:raise SystemExit(child.wait())
    return state


def wait_stopped(home,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        state_path=home/'run/state.json'
        if state_path.exists():
            state=json.loads(state_path.read_text())
            if not state.get('running',False) and platform.process_exited(state['worker_pid']):return
        time.sleep(.2)
    raise RuntimeError('Worker has not completed its stop')


def stop(home):
    try:result=request(home,'stop')
    except FileNotFoundError:return dict(already_stopped=True)
    wait_stopped(home);return result


def backup(home):
    with platform.lease(home/'run/administration.lock'):
        try:
            destination=home/'backups'/time.strftime('snapshot-%Y%m%dT%H%M%SZ',time.gmtime())
            (home/'run/maintenance').touch()
            request(home,'backup',output=str(destination));store.verify(destination);wait_stopped(home)
            start(home)
            store.atomic(home/'backup-status.json',dict(passed=True,snapshot=str(destination)))
            return dict(snapshot=str(destination),verified=True,board_resumed=True)
        except Exception as error:
            store.atomic(home/'backup-status.json',dict(passed=False,error=str(error)));raise
        finally:(home/'run/maintenance').unlink(missing_ok=True)


def monitor(home):
    with platform.lease(home/'run/monitor.lock'):
        issues={};guest=dict(status='deferred',reason='board_stopped')
        previous=json.loads((home/'monitor/state.json').read_text()) if (home/'monitor/state.json').exists() else {}
        settings=dict(min_free_bytes=536870912,min_free_percent=5)
        if (home/'monitor.json').exists():
            custom=json.loads((home/'monitor.json').read_text())
            if set(custom)-set(settings):raise ValueError('Unknown monitor setting')
            settings.update(custom)
        if any(not isinstance(v,(int,float)) or not 0<=v<10**15 for v in settings.values()):raise ValueError('Invalid monitor threshold')
        usage=shutil.disk_usage(home)
        if usage.free<settings['min_free_bytes'] or 100*usage.free/max(1,usage.total)<settings['min_free_percent']:
            issues['low-storage']='Low free storage on board volume'
        status_path=home/'backup-status.json'
        if status_path.exists() and not json.loads(status_path.read_text())['passed']:issues['backup-failed']='Last backup failed'
        if (home/'run/maintenance').exists():guest=dict(status='deferred',reason='backup_maintenance')
        else:
            try:
                state=request(home,'status')
                if state['ready'] and not state['active'] and not state['attached']:
                    guest=request(home,'probe')
                    if guest['status']=='failed':issues['guest-unresponsive']='Idle caller probe failed'
                else:guest=dict(status='deferred',reason='caller_console_or_maintenance')
            except OSError:
                state_path=home/'run/state.json'
                if state_path.exists():
                    state=json.loads(state_path.read_text())
                    if state.get('running') or state.get('exit_code'):issues['worker-failed']='Worker is unavailable or previously failed'
        if guest['status']=='deferred' and 'guest-unresponsive' in previous.get('issues',{}) and guest.get('reason')!='board_stopped':
            issues['guest-unresponsive']=previous['issues']['guest-unresponsive']
        events=previous.get('events',[])[-99:]
        if issues!=previous.get('issues',{}):events.append(dict(at=time.time(),issues=issues))
        result=dict(checked_at=time.time(),issues=issues,guest=guest,events=events)
        store.atomic(home/'monitor/state.json',result);return result


def task(home,name,mode):
    if mode=='disable' and name=='board':stop(home)
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',
                           str(home/'helpers/tasks.ps1'),'-AdminHome',str(home),'-Job',name,'-Mode',mode],
                          capture_output=True,text=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW,
                          env=platform.powershell_environment())
    if result.returncode:raise RuntimeError('Task Scheduler operation failed: '+result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else dict(completed=True)


def attach(home):
    import msvcrt
    with platform.terminal_output(),connect(home) as link:
        link.send_bytes(b'{"action":"attach"}');receive(link,10)
        while True:
            if link.poll(.025):
                message=json.loads(link.recv_bytes(1048576))
                if 'output' in message and sys.stdout is not None:
                    sys.stdout.write(message['output']);sys.stdout.flush()
            if msvcrt.kbhit():
                char=msvcrt.getwch()
                if char=='\x1d':link.send_bytes(b'{"detach":true}');return
                if char in ('\x00','\xe0'):
                    special={'H':38,'P':40,'K':37,'M':39,'G':36,'O':35,'I':33,'Q':34,'R':45,'S':46}.get(msvcrt.getwch())
                    if special:link.send_bytes(json.dumps(dict(special=special)).encode())
                    continue
                link.send_bytes(json.dumps(dict(input=char.encode('ascii',errors='replace').hex())).encode())


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--home',type=Path,default=default_home())
    sub=p.add_subparsers(dest='action',required=True)
    start_parser=sub.add_parser('start');start_parser.add_argument('--wait',action='store_true',help=argparse.SUPPRESS)
    for name in ('worker','stop','status','attach','resume','backup','monitor','alerts'):sub.add_parser(name)
    health=sub.add_parser('health');health.add_argument('--probe',action='store_true')
    for action in ('enable','disable','task-status'):
        item=sub.add_parser(action);item.add_argument('job',choices=('board','backup','monitor'))
    for action in ('verify','restore'):
        item=sub.add_parser(action);item.add_argument('snapshot',type=Path)
        if action=='restore':item.add_argument('--output',type=Path,required=True)
    a=p.parse_args();home=a.home.resolve();cfg=config(home)
    if cfg['owner_sid']!=platform.sid():raise RuntimeError('Use the account that installed this board')
    if len({cfg[k] for k in ('port','caller_port','modem_port')})!=3 or any(not isinstance(cfg[k],int) or not 1<=cfg[k]<=65535 for k in ('port','caller_port','modem_port')):
        raise ValueError('Choose three distinct valid TCP ports')
    if not isinstance(cfg['probe_timeout'],(int,float)) or not 1<=cfg['probe_timeout']<=120:raise ValueError('Probe timeout must be 1..120 seconds')
    if a.action=='worker':raise SystemExit(Worker(home).run())
    if a.action=='start':emit(start(home,a.wait))
    elif a.action=='stop':
        with platform.lease(home/'run/administration.lock'):emit(stop(home))
    elif a.action in ('status','resume'):emit(request(home,a.action))
    elif a.action=='health':
        result=request(home,'probe' if a.probe else 'status');emit(result)
        if result.get('status')=='failed' or not a.probe and not result['ready']:raise SystemExit(1)
    elif a.action=='attach':attach(home)
    elif a.action=='backup':emit(backup(home))
    elif a.action=='monitor':
        result=monitor(home);emit(dict(issues=result['issues'],guest=result['guest']))
        if result['issues']:raise SystemExit(1)
    elif a.action=='alerts':emit(json.loads((home/'monitor/state.json').read_text()))
    elif a.action in ('enable','disable','task-status'):emit(task(home,a.job,'status' if a.action=='task-status' else a.action))
    elif a.action=='verify':emit(dict(verified_files=len(store.verify(a.snapshot))))
    elif a.action=='restore':store.restore(a.snapshot,a.output);emit(dict(restored=str(a.output)))


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as error:
        if sys.stderr is not None:print(str(error),file=sys.stderr)
        raise SystemExit(1)
