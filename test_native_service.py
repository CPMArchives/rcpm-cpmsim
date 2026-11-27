"""Local service safety tests; fixtures never touch an installed system."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).parent / 'packaging/native/rcpm_service.py'
spec = importlib.util.spec_from_file_location('rcpm_service', SCRIPT)
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rcpm-snapshot-', dir='/tmp')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'instance'
        self.root.mkdir(mode=0o700)
        (self.root / 'disks').mkdir()
        (self.root / 'disks/drivei.dsk').write_bytes(b'accounts' + bytes(2 * 1024 * 1024))
        (self.root / 'SYSOP.DOC').write_text('private test credential')
        (self.root / 'SYSOP.DOC').chmod(0o600)
        self.backup = self.base / 'backup'

    def test_round_trip_and_tamper_detection(self):
        service.snapshot(self.root, self.backup)
        self.assertEqual(len(service.verify(self.backup)), 2)
        restored = self.base / 'restored'
        service.restore(self.backup, restored)
        self.assertEqual((restored / 'SYSOP.DOC').read_bytes(), (self.root / 'SYSOP.DOC').read_bytes())
        self.assertEqual((restored / 'SYSOP.DOC').stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError):
            service.restore(self.backup, restored)
        (self.backup / 'instance/SYSOP.DOC').write_text('corrupt')
        with self.assertRaises(ValueError):
            service.verify(self.backup)

    def test_live_lock_and_inside_destination_refused(self):
        with service.lease(self.root / '.console.lock'):
            with self.assertRaises(BlockingIOError):
                service.snapshot(self.root, self.backup)
        self.assertFalse(self.backup.exists())
        with self.assertRaises(ValueError):
            service.snapshot(self.root, self.root / 'backup')

    def test_symlink_and_traversal_refused_without_publishing(self):
        (self.root / 'link').symlink_to(self.root / 'SYSOP.DOC')
        with self.assertRaises(ValueError):
            service.snapshot(self.root, self.backup)
        self.assertFalse(self.backup.exists())
        (self.root / 'link').unlink()
        service.snapshot(self.root, self.backup)
        (self.backup / 'snapshot.json').write_text(json.dumps({'../outside': 'bad'}))
        with self.assertRaises(ValueError):
            service.verify(self.backup)

    def test_failed_backup_preserves_previous(self):
        service.snapshot(self.root, self.backup)
        before = (self.backup / 'snapshot.json').read_bytes()
        with self.assertRaises(ValueError):
            service.snapshot(self.root, self.backup)
        self.assertEqual((self.backup / 'snapshot.json').read_bytes(), before)
        (self.backup / 'instance/extra').write_text('unrecorded')
        with self.assertRaises(ValueError):
            service.verify(self.backup)


class SupervisorTests(unittest.TestCase):
    def test_final_systemd_signal_during_cleanup_is_not_startup_failure(self):
        for stopping in (True,False):
            with self.subTest(stopping=stopping):
                handlers={}
                class FakeSupervisor:
                    def __init__(self,*args):
                        self.ready=False
                        self.stopping=stopping
                    def run(self):
                        handlers[signal.SIGTERM](signal.SIGTERM,None)
                argv=['service','run','--instance','/unused','--tcpser','/unused']
                with patch.object(sys,'argv',argv),patch.object(service,'Supervisor',FakeSupervisor), \
                     patch.object(service.signal,'signal',side_effect=lambda sig,fn:handlers.__setitem__(sig,fn)):
                    if stopping:
                        service.main()
                    else:
                        with self.assertRaisesRegex(RuntimeError,'stopped during startup'):
                            service.main()

    def test_systemd_stop_is_idempotent_when_guest_has_exited(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temporary:
            root = Path(temporary)
            result = service.systemd_stop(root / 'missing-control', root)
            self.assertEqual(result, {'already_stopped': True})

    def test_systemd_stop_does_not_accept_missing_control_with_live_lock(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temporary:
            root = Path(temporary)
            with service.lease(root / '.console.lock'):
                with self.assertRaisesRegex(RuntimeError, 'disks remain locked'):
                    service.systemd_stop(root / 'missing-control', root)

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux parent-death signal')
    def test_child_terminates_if_parent_is_killed(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temporary:
            root = Path(temporary)
            parent_script = root / 'parent.py'
            pid_file = root / 'child.pid'
            parent_script.write_text(
                'import importlib.util,subprocess,sys,time,pathlib\n'
                'spec=importlib.util.spec_from_file_location("svc",'+repr(str(SCRIPT.resolve()))+')\n'
                'svc=importlib.util.module_from_spec(spec);spec.loader.exec_module(svc)\n'
                'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(300)"],'
                'preexec_fn=svc.linux_parent_guard())\n'
                'stage=pathlib.Path('+repr(str(pid_file.with_suffix('.tmp')))+')\n'
                'stage.write_text(str(child.pid));stage.replace('+repr(str(pid_file))+')\n'
                'time.sleep(300)\n')
            parent = subprocess.Popen([sys.executable, str(parent_script)])
            child = None
            try:
                deadline=time.monotonic()+5
                while not pid_file.exists():
                    self.assertLess(time.monotonic(),deadline)
                    time.sleep(.02)
                child=int(pid_file.read_text())
                parent.kill();parent.wait(timeout=5)
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    stat=Path('/proc')/str(child)/'stat'
                    try:
                        state=stat.read_text()
                    except (FileNotFoundError, ProcessLookupError):
                        # Successful exit can remove /proc between lookup/read.
                        break
                    if state.rsplit(') ',1)[1].split()[0]=='Z':
                        break
                    time.sleep(.02)
                else:
                    self.fail('Child remained running after its parent was killed')
            finally:
                if parent.poll() is None:
                    parent.kill();parent.wait()
                if child:
                    try:os.kill(child,signal.SIGTERM)
                    except ProcessLookupError:pass

    def test_no_shutdown_injection_without_fresh_menu(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as temporary:
            s = service.Supervisor(Path(temporary), Path(temporary), Path('/no/tcpser'),
                                   '127.0.0.1', 1, 2, 3, timeout=.1)
            class Guest:
                def poll(self):
                    return None
            s.guest = Guest()
            s.ready = True
            sent = []
            s.write = sent.append
            with self.assertRaises(RuntimeError):
                s.graceful_stop()
            self.assertEqual(sent, [b'\x03'])
            self.assertTrue(s.draining)
            self.assertFalse(s.stopping)

    def test_active_caller_timeout_does_not_write_console(self):
        s = service.Supervisor(Path('/unused'), Path('/unused'), Path('/unused'),
                               '127.0.0.1', 1, 2, 3, timeout=.01)
        s.ready = True
        s.active = 1
        sent = []
        s.write = sent.append
        with self.assertRaises(RuntimeError):
            s.graceful_stop()
        self.assertEqual(sent, [])
        self.assertTrue(s.draining)

    def test_attached_console_refuses_stop(self):
        s = service.Supervisor(Path('/unused'), Path('/unused'), Path('/unused'),
                               '127.0.0.1', 1, 2, 3)
        s.ready = True
        s.attached = object()
        with self.assertRaises(RuntimeError):
            s.graceful_stop()
        self.assertFalse(s.draining)


if __name__ == '__main__':
    unittest.main()
