"""Monitor decision and idle-probe concurrency checks; no live installation."""
import importlib.util
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent/'packaging/native'))
import rcpm_monitor as monitor
import rcpm_service as service


class ProbeTests(unittest.TestCase):
    def supervisor(self):
        s=service.Supervisor(Path('/unused'),Path('/unused'),Path('/unused'),
                             '127.0.0.1',1,2,3)
        s.command_lock=threading.Lock();s.ready=True;s.idle_since=time.monotonic()-11
        return s

    def test_busy_states_never_open_modem_or_write_console(self):
        for attr,value in [('active',1),('attached',object()),('draining',True),('ready',False)]:
            with self.subTest(attr=attr):
                s=self.supervisor();setattr(s,attr,value)
                with patch.object(service.socket,'create_connection') as connect, patch.object(s,'write') as write:
                    self.assertEqual(s.probe()['status'],'deferred')
                    connect.assert_not_called();write.assert_not_called()
                self.assertFalse(s.probing)
        s=self.supervisor();s.command_lock.acquire()
        self.assertEqual(s.probe()['status'],'deferred')
        s.command_lock.release()

    def test_real_socket_probe_reserves_line_and_requires_cleanup(self):
        s=self.supervisor()
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
        self.addCleanup(listener.close);s.caller_port=listener.getsockname()[1]
        errors=[]
        def modem():
            try:
                with listener.accept()[0] as c:
                    self.assertTrue(s.probing);self.assertTrue(s.command_lock.locked())
                    c.sendall(b'A0:SYSTEM>')
                    command=b''
                    while not command.endswith(b'\r'):command+=c.recv(20)
                    self.assertEqual(command,b'HELP\r')
                    c.sendall(b'help text '*20+b'A0:SYSTEM>')
                    self.assertEqual(c.recv(1),b'')
                    with s.condition:
                        s.output.extend(service.MODEM_READY);s.condition.notify_all()
            except BaseException as e:errors.append(e)
        t=threading.Thread(target=modem,daemon=True);t.start()
        self.assertEqual(s.probe(3)['status'],'passed');t.join(3)
        self.assertFalse(t.is_alive());self.assertFalse(errors)
        self.assertFalse(s.probing);self.assertFalse(s.command_lock.locked())

    def test_failed_probe_releases_reservation_without_console_input(self):
        s=self.supervisor()
        with patch.object(service.socket,'create_connection',side_effect=OSError('unavailable')),patch.object(s,'write') as write:
            self.assertEqual(s.probe(1)['status'],'failed');write.assert_not_called()
        self.assertFalse(s.probing);self.assertFalse(s.command_lock.locked())


class MonitorTests(unittest.TestCase):
    def test_notifier_success_is_distinct_from_unhealthy_check(self):
        state={'issues':{'failure:rcpm.service':'Unit failure'},'guest':{'status':'deferred'}}
        with patch.object(monitor,'load_config',return_value=dict(monitor.DEFAULTS)),patch.object(monitor,'check',return_value=state),patch.object(sys,'argv',['monitor','failure','--unit','rcpm.service']):
            monitor.main()
        with patch.object(monitor,'load_config',return_value=dict(monitor.DEFAULTS)),patch.object(monitor,'check',return_value=state),patch.object(sys,'argv',['monitor','check']):
            with self.assertRaises(SystemExit) as raised:monitor.main()
            self.assertEqual(raised.exception.code,1)

    def test_lifetime_counter_is_not_a_restart_loop_and_reset_is_safe(self):
        c=dict(monitor.DEFAULTS)
        h,bad=monitor.restart_history([],100,1000,c);self.assertFalse(bad)
        h,bad=monitor.restart_history(h,103,1010,c);self.assertTrue(bad)
        h,bad=monitor.restart_history(h,0,1011,c);self.assertFalse(bad)
        self.assertEqual(h,[[1011,0]])
        _,bad=monitor.restart_history([[1,0]],20,1000,c);self.assertFalse(bad)

    def test_failure_alerts_are_deduplicated_and_recovery_recorded(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'state.json'
            one=monitor.save_state(p,{}, {'failure:backup':'Failed backup'}, {},1)
            two=monitor.save_state(p,one,{'failure:backup':'Failed backup'},{},2)
            self.assertEqual(len(two['events']),1)
            three=monitor.save_state(p,two,{}, {},3)
            self.assertEqual(three['events'][-1]['state'],'recovered')
            self.assertEqual(p.stat().st_mode&0o777,0o600)
            self.assertEqual(json.loads(p.read_text()),three)

    def test_backup_maintenance_does_not_probe_or_call_missing_control(self):
        with tempfile.TemporaryDirectory() as d:
            c={**monitor.DEFAULTS,'data_path':d,'backup_path':d,'min_free_bytes':0,'min_free_inodes':0,'min_free_percent':0}
            def unit(name):
                return dict(LoadState='loaded',ActiveState='activating' if name=='rcpm-backup.service' else 'active',Result='success',NRestarts='0')
            with patch.object(monitor,'properties',side_effect=unit),patch.object(monitor,'request') as request:
                state=monitor.check(c,Path(d)/'state.json',Path('/missing'))
                request.assert_not_called();self.assertEqual(state['guest']['reason'],'backup_maintenance')

    def test_storage_thresholds_and_unknown_config(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn('space:'+d,monitor.space_issues(d,{**monitor.DEFAULTS,'min_free_bytes':10**14}))
            p=Path(d)/'config.json';p.write_text('{"misspelled_threshold":1}')
            with self.assertRaises(ValueError):monitor.load_config(p)

    def test_deferred_probe_retains_guest_alert_until_positive_recheck(self):
        with tempfile.TemporaryDirectory() as d:
            c={**monitor.DEFAULTS,'data_path':d,'backup_path':d,'min_free_bytes':0,'min_free_inodes':0,'min_free_percent':0}
            p=Path(d)/'state.json'
            p.write_text(json.dumps({'issues':{'guest-unresponsive':'Caller probe failed'}}))
            def unit(name):
                return dict(LoadState='loaded',ActiveState='active' if name=='rcpm.service' else 'inactive',Result='success',NRestarts='0')
            with patch.object(monitor,'properties',side_effect=unit),patch.object(monitor,'request',return_value={'status':'deferred','reason':'caller_active'}):
                state=monitor.check(c,p,Path('/unused'))
                self.assertIn('guest-unresponsive',state['issues'])
                self.assertFalse(state['events'])
            with patch.object(monitor,'properties',side_effect=unit),patch.object(monitor,'request',return_value={'status':'passed'}):
                state=monitor.check(c,p,Path('/unused'))
                self.assertFalse(state['issues'])
                self.assertEqual(state['events'][-1]['state'],'recovered')


if __name__=='__main__':unittest.main()
