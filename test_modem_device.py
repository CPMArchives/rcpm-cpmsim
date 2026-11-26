"""Exercise the actual C device with sockets; optionally use a real tcpser."""
import ctypes
import os
from pathlib import Path
import socket
import select
import subprocess
import struct
import tempfile
import time
import unittest
from unittest.mock import patch


def free_port():
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        return server.getsockname()[1]


class ModemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='rcpm-modem-tests-')
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        source = Path(__file__).resolve().parent / 'emulator/rcpm_modem.c'
        wrapper = root / 'device.c'
        wrapper.write_text('''#include <stdint.h>
static uint64_t test_now;
static uint64_t test_clock_now(void) { return test_now; }
#define RM_CLOCK_NOW test_clock_now
''' + f'#include "{source}"\n' + '''
int device_init(void) { return rcpm_modem_init(); }
void device_close(void) { rcpm_modem_close(); }
unsigned char device_status(void) { return rcpm_modem_status(); }
unsigned char device_read(void) { return rcpm_modem_read(); }
void device_write(unsigned char c) { rcpm_modem_write(c); }
void device_control(unsigned char c) { rcpm_modem_control(c); }
unsigned char device_control_read(void) { return rcpm_modem_control_read(); }
void device_clock_set(uint64_t now) { test_now = now; }
void device_idle_reset(void) { rcpm_idle_reset(0); }
unsigned char device_idle_read(void) { return rcpm_idle_read(); }
''')
        library = root / 'device.so'
        subprocess.run(['cc', '-std=c99', '-D_DEFAULT_SOURCE', '-Wall', '-Wextra', '-Werror',
                        '-shared', '-fPIC', str(wrapper), '-o', str(library)], check=True)
        cls.dev = ctypes.CDLL(str(library))
        for name in ('device_status', 'device_read', 'device_control_read'):
            getattr(cls.dev, name).restype = ctypes.c_ubyte
        cls.dev.device_write.argtypes = [ctypes.c_ubyte]
        cls.dev.device_control.argtypes = [ctypes.c_ubyte]
        cls.dev.device_clock_set.argtypes = [ctypes.c_uint64]
        cls.dev.device_idle_read.restype = ctypes.c_ubyte

    def setUp(self):
        self.dev.device_close()
        self.dev.device_clock_set(0)
        env = {k: v for k, v in os.environ.items() if not k.startswith('RCPM_MODEM')}
        self.env = patch.dict(os.environ, env, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.addCleanup(self.dev.device_close)

    def start(self, mode, port):
        os.environ.update(RCPM_MODEM=mode, RCPM_MODEM_HOST='127.0.0.1', RCPM_MODEM_PORT=str(port))
        self.assertEqual(self.dev.device_init(), 0)

    def wait(self, predicate, timeout=4):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            status = self.dev.device_status()
            if predicate(status):
                return status
            time.sleep(.001)
        self.fail('Device condition timed out')

    def receive(self, count):
        data = bytearray()
        end = time.monotonic() + 4
        while len(data) < count and time.monotonic() < end:
            if self.dev.device_status() & 1:
                data.append(self.dev.device_read())
            else:
                time.sleep(.001)
        self.assertEqual(len(data), count)
        return bytes(data)

    def send(self, data):
        for c in data:
            self.wait(lambda s: s & 2)
            self.dev.device_write(c)

    def wait_closed(self, client):
        def closed(status):
            if select.select([client], [], [], 0)[0]:
                self.assertEqual(client.recv(1), b'')
                return True
            return False
        self.wait(closed)

    def peer(self, port):
        client = socket.create_connection(('127.0.0.1', port), timeout=2)
        self.addCleanup(client.close)
        return client

    def test_disabled_device(self):
        self.assertEqual(self.dev.device_init(), 0)
        self.assertEqual(self.dev.device_status(), 0)
        self.assertEqual(self.dev.device_read(), 0)

    def test_idle_minutes_are_monotonic_latched_and_resettable(self):
        self.start('direct', free_port())
        minute = 60 * 1000**3
        self.dev.device_clock_set(17 * minute)
        self.dev.device_idle_reset()
        self.dev.device_clock_set(18 * minute - 1)
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [0, 0])
        self.dev.device_clock_set(18 * minute)
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [1, 0])
        self.dev.device_clock_set((17 + 255) * minute)
        self.assertEqual(self.dev.device_idle_read(), 255)
        self.dev.device_clock_set((17 + 256) * minute)
        self.assertEqual(self.dev.device_idle_read(), 0)  # high byte from the latched 255
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [0, 1])
        self.dev.device_idle_reset()
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [0, 0])
        self.dev.device_clock_set((17 + 256 + 70000) * minute)
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [255, 255])

    def test_idle_polls_do_not_advance_clock_or_wait(self):
        self.start('direct', free_port())
        self.dev.device_idle_reset()
        start = time.monotonic()
        for _ in range(10000):
            self.assertEqual(self.dev.device_idle_read(), 0)
        self.assertLess(time.monotonic() - start, .5)
        self.dev.device_clock_set(60 * 1000**3)
        self.assertEqual([self.dev.device_idle_read(), self.dev.device_idle_read()], [1, 0])

    def test_direct_bytes_busy_hangup_and_reconnect(self):
        port = free_port()
        self.start('direct', port)
        self.dev.device_control(3)
        client = self.peer(port)
        self.wait(lambda s: s & 4)
        data = bytes(range(256))
        client.sendall(data)
        self.assertEqual(self.receive(256), data)
        self.send(data)
        received = bytearray()
        while len(received) < 256:
            received.extend(client.recv(256 - len(received)))
        self.assertEqual(received, data)
        other = self.peer(port)
        self.dev.device_status()
        self.wait_closed(other)
        self.dev.device_control(7)
        self.wait_closed(client)
        self.assertFalse(self.dev.device_status() & 4)
        self.assertEqual(self.dev.device_control_read(), 3)
        replacement = self.peer(port)
        self.wait(lambda s: s & 4)
        replacement.sendall(b'next')
        self.assertEqual(self.receive(4), b'next')
        replacement.close()
        self.wait(lambda s: not s & 4)
        self.assertFalse(self.dev.device_status() & 1)

    def test_direct_burst_survives_full_receive_queue(self):
        port = free_port()
        self.start('direct', port)
        self.dev.device_control(3)
        caller = self.peer(port)
        self.wait(lambda s: s & 4)
        payload = bytes(range(256)) * 128
        caller.sendall(payload)
        # Fill the device queue without consuming it, then drain the burst.
        for _ in range(30):
            self.dev.device_status()
        self.assertEqual(self.receive(len(payload)), payload)

    def test_direct_reset_does_not_terminate_device(self):
        port = free_port()
        self.start('direct', port)
        self.dev.device_control(3)
        caller = self.peer(port)
        self.wait(lambda s: s & 4)
        caller.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        caller.close()
        # Both read and write paths must tolerate a reset without SIGPIPE.
        self.dev.device_write(0xff)
        self.wait(lambda s: not s & 4)
        replacement = self.peer(port)
        self.wait(lambda s: s & 4)
        replacement.sendall(b'alive')
        self.assertEqual(self.receive(5), b'alive')

    def test_direct_dtr_and_answer_controls(self):
        port = free_port()
        self.start('direct', port)
        for control in (0, 1, 2):
            self.dev.device_control(control)
            caller = self.peer(port)
            self.dev.device_status()
            self.wait_closed(caller)
        self.dev.device_control(3)
        caller = self.peer(port)
        self.wait(lambda s: s & 4)
        self.dev.device_control(1)  # Stop answering; keep the existing call.
        self.assertTrue(self.dev.device_status() & 4)
        self.dev.device_control(0)  # Drop DTR.
        self.wait_closed(caller)
        self.assertFalse(self.dev.device_status() & 4)

    def test_ip232_fragmented_controls_and_binary(self):
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0))
            server.listen()
            self.start('ip232', server.getsockname()[1])
            self.dev.device_status()
            client, _ = server.accept()
            self.addCleanup(client.close)
            client.settimeout(2)
            self.wait(lambda s: s & 8)
            self.assertEqual(client.recv(2), b'\xff\x00')
            self.assertFalse(self.dev.device_status() & 4)
            client.sendall(b'\xff')
            self.dev.device_status()
            self.assertFalse(self.dev.device_status() & 1)
            client.sendall(b'\x03')
            self.wait(lambda s: s & 4 and s & 64)
            data = bytes(range(256))
            client.sendall(data.replace(b'\xff', b'\xff\xff'))
            self.assertEqual(self.receive(256), data)
            self.send(data)
            wire = bytearray()
            while len(wire) < 257:
                wire.extend(client.recv(257 - len(wire)))
            self.assertEqual(wire, data.replace(b'\xff', b'\xff\xff'))
            self.dev.device_control(1)
            self.assertEqual(client.recv(2), b'\xff\x01')
            self.dev.device_control(0)
            self.assertEqual(client.recv(2), b'\xff\x00')
            client.sendall(b'\xff\x00')
            self.wait(lambda s: not s & 4 and not s & 64)
            self.assertTrue(self.dev.device_status() & 8)
            client.close()
            self.wait(lambda s: not s & 8)

    @unittest.skipUnless(os.environ.get('RCPM_TEST_TCPSER'), 'Set RCPM_TEST_TCPSER to test real tcpser')
    def test_real_tcpser_answer_carrier_and_dtr_hangup(self):
        executable = os.environ['RCPM_TEST_TCPSER']
        modem_port, call_port = free_port(), free_port()
        with tempfile.TemporaryFile() as log:
            proc = subprocess.Popen([executable, '-v', f'127.0.0.1:{modem_port}',
                '-p', f'127.0.0.1:{call_port}', '-s', '38400', '-i', 'e0v1&c1&d2', '-l', '4'],
                stdout=log, stderr=log)
            def stop():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            self.addCleanup(stop)
            self.start('ip232', modem_port)
            self.wait(lambda s: s & 8)
            self.assertFalse(self.dev.device_status() & 4)
            self.dev.device_control(1)
            self.send(b'AT E0 V1 &C1 &D2 S0=1\r')
            response = bytearray()
            end = time.monotonic() + 5
            while b'OK' not in response and time.monotonic() < end:
                if self.dev.device_status() & 1:
                    response.append(self.dev.device_read())
                else:
                    time.sleep(.005)
            self.assertIn(b'OK', response)
            caller = self.peer(call_port)
            self.wait(lambda s: s & 4)
            # Drain modem responses before checking the connected data path.
            end = time.monotonic() + .25
            while time.monotonic() < end:
                if self.dev.device_status() & 1:
                    self.dev.device_read()
                time.sleep(.001)
            caller.sendall(b'caller-data\x80\xff\x00')
            self.assertEqual(self.receive(14), b'caller-data\x80\xff\x00')
            self.send(b'sysop-data\x80\xff\x00')
            received = bytearray()
            while len(received) < 13:
                received.extend(caller.recv(13 - len(received)))
            self.assertEqual(received, b'sysop-data\x80\xff\x00')
            self.dev.device_control(0)
            self.wait(lambda s: not s & 4)
            self.wait_closed(caller)
            self.assertTrue(self.dev.device_status() & 8)


    @unittest.skipUnless(os.environ.get('RCPM_TEST_TCPSER'), 'Set RCPM_TEST_TCPSER to test real tcpser')
    def test_real_tcpser_outbound_binary_hangup_failed_dial_and_inbound_recovery(self):
        modem_port, call_port = free_port(), free_port()
        with tempfile.TemporaryFile() as log, socket.socket() as hub:
            hub.bind(('127.0.0.1', 0))
            hub.listen(1)
            hub.settimeout(5)
            proc = subprocess.Popen([os.environ['RCPM_TEST_TCPSER'], '-v', f'127.0.0.1:{modem_port}',
                '-p', f'127.0.0.1:{call_port}', '-s', '38400', '-i', 'e0v1&c1&d2', '-l', '0'],
                stdout=log, stderr=log)
            def stop():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            self.addCleanup(stop)
            self.start('ip232', modem_port)
            self.wait(lambda s: s & 8)
            self.dev.device_control(1)
            def response(marker):
                data = bytearray()
                end = time.monotonic() + 10
                while marker not in data and time.monotonic() < end:
                    if self.dev.device_status() & 1:
                        data.append(self.dev.device_read())
                    else:
                        time.sleep(.002)
                self.assertIn(marker, data)
                return data
            self.send(b'ATE0V1&C1&D2S0=0\r')
            response(b'OK\r\n')
            # tcpser samples control lines every 100 ms. Honor modem DTR
            # settling time so a complete short call cannot hide the high edge.
            time.sleep(.25)
            self.send(f'ATD127.0.0.1:{hub.getsockname()[1]}\r'.encode())
            peer, _ = hub.accept()
            self.addCleanup(peer.close)
            peer.settimeout(5)
            response(b'CONNECT 38400\r\n')
            self.wait(lambda s: s & 4)
            payload = bytes(range(256)) * 4
            peer.sendall(payload)
            self.assertEqual(self.receive(len(payload)), payload)
            self.send(payload)
            incoming = bytearray()
            while len(incoming) < len(payload):
                block = peer.recv(len(payload) - len(incoming))
                self.assertTrue(block)
                incoming.extend(block)
            self.assertEqual(incoming, payload)
            self.dev.device_control(0)
            self.wait(lambda s: not s & 4)
            self.wait_closed(peer)
            response(b'NO CARRIER\r\n')
            self.dev.device_control(1)
            time.sleep(.25)
            # A closed loopback port is a controlled failed destination, no external dialing.
            with socket.socket() as reserved:
                reserved.bind(('127.0.0.1', 0))
                failed_port = reserved.getsockname()[1]
            self.send(f'ATD127.0.0.1:{failed_port}\r'.encode())
            response(b'NO CARRIER\r\n')
            self.assertFalse(self.dev.device_status() & 4)
            self.send(b'ATS0=1\r')
            response(b'OK\r\n')
            caller = self.peer(call_port)
            response(b'CONNECT 38400\r\n')
            self.wait(lambda s: s & 4)
            caller.sendall(b'inbound-after-outbound')
            self.assertEqual(self.receive(len(b'inbound-after-outbound')), b'inbound-after-outbound')
            self.dev.device_control(0)
            self.wait(lambda s: not s & 4)
            self.wait_closed(caller)


if __name__ == '__main__':
    unittest.main()
