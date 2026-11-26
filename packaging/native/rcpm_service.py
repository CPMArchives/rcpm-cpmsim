#!/usr/bin/env python3
"""Private PTY supervisor for a native RCP/M package (Python 3.9+, stdlib only).

Only the gated caller listener is public; tcpser and its IP232 endpoint are
loopback-only. No caller can access the Unix operator socket.
"""
import argparse
import contextlib
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty

# The IP232 BYE build reports its numeric Hayes acknowledgement rather
# than the direct driver's 'modem ready' banner. Require the exact sequence.
MODEM_READY = b'ATE0Q0V0S0=0M0S10=25X1H0\r\n0\r\n'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


@contextlib.contextmanager
def lease(path):
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        os.close(fd)


def snapshot(root, destination):
    """Called only after the guest exits; refuse concurrent manual launch too."""
    root, destination = root.resolve(), destination.resolve()
    if destination == root or root in destination.parents or destination.exists():
        raise ValueError('Backup requires a new destination outside the installation')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with lease(root / '.console.lock'), tempfile.TemporaryDirectory(
            prefix='.rcpm-backup-', dir=destination.parent) as temporary:
        stage = Path(temporary)
        payload = stage / 'instance'
        payload.mkdir(mode=0o700)
        records = {}
        for path in sorted(root.rglob('*')):
            relative = path.relative_to(root)
            if relative.parts[0] in {'.console.lock', '.service.lock'}:
                continue
            target = payload / relative
            if path.is_symlink():
                raise ValueError('Symlinks are not permitted in snapshots: ' + str(relative))
            if path.is_dir():
                target.mkdir(mode=0o700)
            elif path.is_file():
                before = path.stat()
                with path.open('rb') as src, target.open('xb') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        if block.count(0) == len(block):
                            dst.seek(len(block), 1)
                        else:
                            dst.write(block)
                    dst.truncate(before.st_size)
                    dst.flush()
                    os.fsync(dst.fileno())
                    os.fchmod(dst.fileno(), before.st_mode & 0o777)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise RuntimeError('Source changed during backup')
                records[str(relative)] = digest(target)
            else:
                raise ValueError('Unexpected special file: ' + str(relative))
        (stage / 'snapshot.json').write_text(json.dumps(records, indent=2) + '\n')
        verify(stage)
        stage.rename(destination)
        fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def verify(backup):
    if (backup / 'instance').is_symlink():
        raise ValueError('Symlink payload')
    records = json.loads((backup / 'snapshot.json').read_text())
    if not isinstance(records, dict) or not records:
        raise ValueError('Empty/invalid snapshot')
    for name, expected in records.items():
        path = Path(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name:
            raise ValueError('Unsafe snapshot path')
        target = backup / 'instance'
        for part in path.parts:
            target /= part
            if target.is_symlink():
                raise ValueError('Symlink snapshot path')
        if digest(target) != expected:
            raise ValueError('Snapshot checksum mismatch: ' + name)
    actual = {str(p.relative_to(backup / 'instance')) for p in (backup / 'instance').rglob('*') if p.is_file()}
    if actual != set(records):
        raise ValueError('Unrecorded snapshot files')
    return records


def restore(backup, destination):
    backup, destination = backup.resolve(), destination.resolve()
    if destination == backup or backup in destination.parents:
        raise ValueError('Restore outside the backup directory')
    records = verify(backup)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Restore requires a new directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.rcpm-restore-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'instance'
        shutil.copytree(backup / 'instance', stage)
        for name, expected in records.items():
            if digest(stage / name) != expected:
                raise ValueError('Snapshot changed during restore')
        stage.rename(destination)


def linux_parent_guard():
    """Arm child termination if the supervisor dies, including SIGKILL.

    Resolve libc before fork. Both guarded children are spawned before this
    supervisor starts any threads; this pre-exec hook does not take Python locks.
    """
    if not sys.platform.startswith('linux'):
        return None
    parent = os.getpid()
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
    prctl.restype = ctypes.c_int
    def arm():
        if prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent:
            os._exit(127)
    return arm


def systemd_stop(run_dir, instance):
    """ExecStop is also called after a completed snapshot or process exit."""
    try:
        return request(run_dir, 'stop')
    except (FileNotFoundError, ConnectionRefusedError):
        # Never declare a missing control socket safe while a guest holds disks.
        # A normal completed snapshot has already released this lock.
        deadline = time.monotonic() + 5
        while True:
            try:
                with lease(instance / '.console.lock'):
                    return {'already_stopped': True}
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Control endpoint unavailable but guest disks remain locked')
                time.sleep(.1)


class Supervisor:
    def __init__(self, root, run_dir, tcpser, address, port, modem_port, caller_port, timeout=120):
        self.root, self.run_dir = root, run_dir
        self.tcpser, self.address, self.port = tcpser, address, port
        self.modem_port, self.caller_port, self.timeout = modem_port, caller_port, timeout
        self.mutex = threading.Lock()
        self.active = 0
        self.draining = False
        self.stopping = False
        self.attached = None
        self.output = bytearray()
        self.condition = threading.Condition()
        self.guest = self.modem = None
        self.master = self.slave = None
        self.ready = False
        self.failed = None
        self.trace = None

    def collect(self):
        while self.guest.poll() is None:
            if select.select([self.master], [], [], .1)[0]:
                try:
                    data = os.read(self.master, 16384)
                except OSError:
                    break
                if not data:
                    break
                if self.trace:
                    with self.trace.open('ab') as trace:
                        os.chmod(self.trace, 0o600)
                        trace.write(data)
                with self.condition:
                    self.output.extend(data)
                    del self.output[:-65536]
                    self.condition.notify_all()
                # Do not journal console output: it may contain private mail/passwords.
                with self.mutex:
                    if self.attached:
                        try:
                            self.attached.sendall(data)
                        except OSError:
                            self.attached.close()
                            self.attached = None

    def wait_marker(self, marker, clear=False):
        deadline = time.monotonic() + self.timeout
        with self.condition:
            while marker not in self.output:
                if self.guest.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Guest did not acknowledge ' + repr(marker))
                self.condition.wait(.1)
            if clear:
                self.output.clear()

    def write(self, data):
        os.write(self.master, data)

    def relay(self, caller):
        peer = None
        try:
            peer = socket.create_connection(('127.0.0.1', self.caller_port), timeout=3)
            caller.settimeout(3)
            peer.settimeout(3)
            while self.guest.poll() is None:
                for source in select.select([caller, peer], [], [], .2)[0]:
                    data = source.recv(16384)
                    if not data:
                        return
                    (peer if source is caller else caller).sendall(data)
        except OSError:
            pass
        finally:
            caller.close()
            if peer:
                peer.close()
            with self.mutex:
                self.active -= 1

    def accept_callers(self):
        while not self.stopping:
            if not select.select([self.listener], [], [], .1)[0]:
                continue
            caller, _ = self.listener.accept()
            with self.mutex:
                if self.draining or self.active or not self.ready:
                    caller.close()
                    continue
                self.active += 1
            threading.Thread(target=self.relay, args=(caller,), daemon=True).start()

    def graceful_stop(self):
        if not self.ready:
            raise RuntimeError('Guest is not ready for graceful shutdown')
        with self.mutex:
            if self.attached:
                raise RuntimeError('Detach the operator console before stopping')
            self.draining = True
        deadline = time.monotonic() + self.timeout
        while self.active:
            if time.monotonic() > deadline:
                raise RuntimeError('Caller still active; left running with new calls disabled')
            time.sleep(.1)
        # Carrier-loss cleanup precedes entering the idle BYE menu. All command
        # stages require fresh acknowledgements; never type shutdown blindly.
        time.sleep(2)
        with self.condition:
            self.output.clear()
        self.write(b'\x03')
        self.wait_marker(b'<RET> for', clear=True)
        self.write(b'\r')
        self.wait_marker(b'A0:SYSTEM>', clear=True)
        for byte in b'SYSUTLS:BYEBYE\r':
            self.write(bytes([byte]))
            time.sleep(.06)
        try:
            code = self.guest.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Shutdown not completed; no forced termination performed')
        if code != 0:
            raise RuntimeError('Guest exited unsuccessfully')
        self.stopping = True

    def handle(self, client):
        client.settimeout(5)
        try:
            request = bytearray()
            while not request.endswith(b'\n'):
                b = client.recv(1)
                if not b or len(request) >= 4096:
                    raise ValueError('Invalid request')
                request.extend(b)
            request = json.loads(request)
            action = request['action']
            if action == 'status':
                result = dict(readiness_scope='Hayes initialization acknowledged; processes alive; not draining',
                              ready=self.ready and not self.draining and self.guest.poll() is None
                              and self.modem.poll() is None, active=self.active,
                              draining=self.draining, guest_exit=self.guest.poll(),
                              tcpser_exit=self.modem.poll(), guest_pid=self.guest.pid,
                              tcpser_pid=self.modem.pid, failure=self.failed)
            elif action == 'attach':
                with self.mutex:
                    if not self.ready or self.attached or self.command_lock.locked():
                        raise RuntimeError('Console busy or shutdown in progress')
                    client.sendall(b'{"ok":true}\n')
                    self.attached = client
                client.settimeout(.2)
                try:
                    while self.guest.poll() is None:
                        try:
                            data = client.recv(1024)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        self.write(data)
                finally:
                    with self.mutex:
                        if self.attached is client:
                            self.attached = None
                return
            elif action == 'resume':
                with self.command_lock, self.mutex:
                    if MODEM_READY not in self.output or self.guest.poll() is not None:
                        raise RuntimeError('Return to BYE modem-ready state before resuming callers')
                    self.draining = False
                    self.failed = None
                result = {'resumed': True}
            elif action in ('stop', 'backup'):
                with self.command_lock:
                    try:
                        self.graceful_stop()
                        if action == 'backup':
                            snapshot(self.root, Path(request['output']))
                        reply = dict(ok=True, result={'stopped': True, 'backup': request.get('output')})
                    except Exception as error:
                        self.failed = str(error)
                        reply = dict(ok=False, error=str(error))
                    # Send completion before releasing the lease/allowing the main
                    # thread to exit (control handlers are daemon threads).
                    client.sendall(json.dumps(reply).encode() + b'\n')
                return
            else:
                raise ValueError('Unknown action')
            client.sendall(json.dumps(dict(ok=True, result=result)).encode() + b'\n')
        except Exception as error:
            with contextlib.suppress(OSError):
                client.sendall(json.dumps(dict(ok=False, error=str(error))).encode() + b'\n')
        finally:
            client.close()

    def accept_admin(self, admin):
        while not self.stopping:
            if select.select([admin], [], [], .2)[0]:
                client, _ = admin.accept()
                threading.Thread(target=self.handle, args=(client,), daemon=True).start()

    def run(self):
        os.umask(0o077)
        self.run_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if self.run_dir.stat().st_uid != os.getuid() or self.run_dir.stat().st_mode & 0o077:
            raise ValueError('Runtime directory must be owned by this user and private (0700)')
        self.command_lock = threading.Lock()
        with lease(self.root / '.service.lock'):
            # Refuse existing internal listeners rather than accidentally using
            # another instance's modem. tcpser must own both endpoints.
            for port in (self.modem_port, self.caller_port):
                with socket.socket() as probe:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    probe.bind(('127.0.0.1', port))
            control = self.run_dir / 'control.sock'
            control.unlink(missing_ok=True)
            with socket.socket(socket.AF_UNIX) as admin, socket.socket() as listener:
                self.listener = listener
                admin.bind(str(control))
                admin.listen(4)
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.address, self.port))
                listener.listen(4)
                log = tempfile.TemporaryFile()
                try:
                    guard = linux_parent_guard()
                    self.modem = subprocess.Popen([str(self.tcpser), '-v', f'127.0.0.1:{self.modem_port}',
                        '-p', f'127.0.0.1:{self.caller_port}', '-s', '2400', '-S', '2400',
                        '-i', 'e0v1&c1&d2', '-l', '0'], stdout=log, stderr=log, preexec_fn=guard)
                    self.master, self.slave = pty.openpty()
                    tty.setraw(self.slave)
                    fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack('HHHH', 24, 80, 0, 0))
                    self.guest = subprocess.Popen([str(self.root / 'runtime/rcpm'), '--mode', 'ip232',
                        '--address', '127.0.0.1', '--port', str(self.modem_port)], cwd=self.root,
                        stdin=self.slave, stdout=self.slave, stderr=self.slave, start_new_session=True, preexec_fn=guard)
                    threading.Thread(target=self.collect, daemon=True).start()
                    threading.Thread(target=self.accept_admin, args=(admin,), daemon=True).start()
                    self.wait_marker(MODEM_READY)
                    time.sleep(3)  # BYE consumes trailing response before accepting rings
                    if self.modem.poll() is not None:
                        raise RuntimeError('tcpser failed to start')
                    self.ready = True
                    threading.Thread(target=self.accept_callers, daemon=True).start()
                    notify = os.environ.get('NOTIFY_SOCKET')
                    if notify:
                        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as notifier:
                            notifier.connect('\0' + notify[1:] if notify.startswith('@') else notify)
                            notifier.sendall(b'READY=1')
                    print('RCP/M service ready (IP232)', flush=True)
                    while not self.stopping:
                        if self.modem.poll() is not None or (self.guest.poll() is not None and not self.draining):
                            raise RuntimeError('Guest or tcpser exited unexpectedly')
                        time.sleep(.2)
                    # Wait for an in-flight stopped snapshot before releasing service lease.
                    with self.command_lock:
                        pass
                finally:
                    self.ready = False
                    self.stopping = True
                    # Abnormal exits are failures, never reported as consistent backups.
                    for process in (self.guest, self.modem):
                        if process and process.poll() is None:
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                    for fd in (self.master, self.slave):
                        if fd is not None:
                            os.close(fd)
                    log.close()
                    control.unlink(missing_ok=True)


def request(run_dir, action, output=None):
    connection = socket.socket(socket.AF_UNIX)
    try:
        connection.settimeout(300)
        connection.connect(str(run_dir / 'control.sock'))
        connection.sendall(json.dumps(dict(action=action, output=output)).encode() + b'\n')
        response = bytearray()
        while not response.endswith(b'\n'):
            b = connection.recv(1)
            if not b:
                raise RuntimeError('Service disconnected')
            response.extend(b)
        reply = json.loads(response)
        if not reply['ok']:
            raise RuntimeError(reply['error'])
        if action != 'attach':
            connection.close()
            return reply.get('result')
        if not os.isatty(0):
            raise ValueError('Attach requires a terminal')
        saved = termios.tcgetattr(0)
        try:
            tty.setraw(0)
            while True:
                for source in select.select([0, connection], [], [])[0]:
                    data = os.read(0, 1024) if source == 0 else connection.recv(16384)
                    if not data or (source == 0 and b'\x1d' in data):
                        return
                    if source == 0:
                        connection.sendall(data)
                    else:
                        os.write(1, data)
        finally:
            termios.tcsetattr(0, termios.TCSADRAIN, saved)
            connection.close()
    finally:
        connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=Path('/run/rcpm'))
    sub = parser.add_subparsers(dest='action', required=True)
    run = sub.add_parser('run')
    run.add_argument('--instance', type=Path, required=True)
    run.add_argument('--tcpser', type=Path, required=True)
    run.add_argument('--address', default='127.0.0.1')
    run.add_argument('--port', type=int, default=4000)
    run.add_argument('--modem-port', type=int, default=25232)
    run.add_argument('--caller-port', type=int, default=24000)
    run.add_argument('--trace-console', type=Path, help='Private diagnostic file; may contain passwords/mail')
    for action in ('status', 'health', 'attach', 'stop', 'resume'):
        sub.add_parser(action)
    stop_unit = sub.add_parser('systemd-stop')
    stop_unit.add_argument('--instance', type=Path, required=True)
    backup = sub.add_parser('backup')
    backup.add_argument('--output', required=True)
    for action in ('verify', 'restore'):
        p = sub.add_parser(action)
        p.add_argument('backup', type=Path)
        if action == 'restore':
            p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    if args.action == 'run':
        if len({args.port, args.modem_port, args.caller_port}) != 3 or any(
                not 1 <= p <= 65535 for p in (args.port, args.modem_port, args.caller_port)):
            raise ValueError('Three distinct ports in 1..65535 are required')
        service = Supervisor(args.instance.resolve(), args.run_dir.resolve(), args.tcpser.resolve(),
                             args.address, args.port, args.modem_port, args.caller_port)
        service.trace = args.trace_console
        def shutdown(signum, frame):
            # Run normal control path off the main thread; repeated signals do not
            # turn a blocked graceful stop into a misleading successful exit.
            # ExecStop has already acknowledged a successful stop. systemd may
            # deliver its final SIGTERM while run() is clearing readiness and
            # reaping the modem. That is cleanup, not an interrupted startup.
            if service.stopping:
                return
            if not service.ready:
                raise RuntimeError('Service stopped during startup; no consistent snapshot claimed')
            if not service.draining:
                def stop():
                    try:
                        with service.command_lock:
                            service.graceful_stop()
                    except Exception as error:
                        service.failed = str(error)
                        print(str(error), flush=True)
                threading.Thread(target=stop, daemon=True).start()
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
        service.run()
    elif args.action == 'systemd-stop':
        print(json.dumps(systemd_stop(args.run_dir, args.instance.resolve())))
    elif args.action == 'verify':
        print(json.dumps({'verified_files': len(verify(args.backup))}))
    elif args.action == 'restore':
        restore(args.backup, args.output)
        print('Restored into ' + str(args.output))
    else:
        result = request(args.run_dir, 'status' if args.action == 'health' else args.action,
                         getattr(args, 'output', None))
        print(json.dumps(result))
        if args.action == 'health' and not result['ready']:
            raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error))
