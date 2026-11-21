#!/usr/bin/env python3
"""Unpack the release away from the checkout, then exercise both transports."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import socket
import struct
import subprocess
import termios
import time
import tty


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def free_port():
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        return server.getsockname()[1]


class Guest:
    def __init__(self, package, output, *args):
        self.package = package
        self.master, slave = pty.openpty()
        tty.setraw(slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 30, 80, 0, 0))
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('RCPM_', 'PYTHON')) and key not in ('TMUX', 'DISKDEFS')}
        env.update(PATH='/usr/bin:/bin', TERM='vt100')
        self.process = subprocess.Popen([str(package / 'Start-RCPM.command'), *args],
                                        cwd='/tmp', env=env, stdin=slave, stdout=slave, stderr=slave)
        # Keep a slave descriptor until logs are drained. Darwin can discard
        # unread PTY output when the last slave closes after a short refusal.
        self.slave = slave
        self.caller, self.local, self.remote = None, bytearray(), bytearray()
        self.output = output
    def collect(self, duration=.1):
        end = time.monotonic() + duration
        while time.monotonic() < end:
            ready = select.select([self.master] + ([self.caller] if self.caller else []), [], [], .03)[0]
            if self.master in ready:
                try:
                    data = os.read(self.master, 16384)
                except OSError:
                    data = b''
                self.local.extend(data)
            if self.caller and self.caller in ready:
                data = self.caller.recv(16384)
                if data:
                    self.remote.extend(data)
                else:
                    self.caller.close()
                    self.caller = None
    def wait(self, marker, remote=False, start=0, timeout=45):
        stream = self.remote if remote else self.local
        deadline = time.monotonic() + timeout
        while marker not in stream[start:]:
            if time.monotonic() > deadline or (self.process.poll() is not None and not remote):
                raise AssertionError('Waiting for ' + repr(marker) + ': ' + repr(bytes(stream[-1800:])))
            self.collect()
        return bytes(stream[start:])
    def connect(self, port, kick=True):
        print('Connecting caller on port ' + str(port) + '...', flush=True)
        self.caller = socket.create_connection(('127.0.0.1', port), timeout=5)
        deadline = time.monotonic() + 25
        while b'A0:SYSTEM>' not in self.remote:
            if time.monotonic() > deadline:
                raise AssertionError('Caller login: ' + repr(bytes(self.remote[-1800:])))
            if kick:
                self.caller.sendall(b'\r')
            self.collect(.4)
    def command(self, text):
        print('Checking ' + text + '...', flush=True)
        start = len(self.remote)
        for char in (text + '\r').encode():
            self.caller.sendall(bytes([char]))
            self.collect(.025)
        return self.wait(b'A0:SYSTEM>', remote=True, start=start)
    def stop(self):
        print('Disconnecting caller and shutting down guest...', flush=True)
        if self.caller:
            self.caller.close()
            self.caller = None
            self.collect(1)
        start = len(self.local)
        os.write(self.master, b'\x03')
        self.wait(b'<RET> for', start=start)
        os.write(self.master, b'\r')
        self.wait(b'A0:SYSTEM>', start=start)
        self.collect(1)
        for char in b'SYSUTLS:BYEBYE\r':
            os.write(self.master, bytes([char]))
            self.collect(.1)
        self.collect(1)
        if self.process.poll() is None:
            os.write(self.master, b'\r')
        end = time.monotonic() + 20
        while self.process.poll() is None and time.monotonic() < end:
            self.collect(.1)
        self.process.wait(timeout=1)
        assert self.process.returncode == 0
        self.collect(.2)
    def close(self):
        (self.output.with_suffix('.local.log')).write_bytes(self.local)
        (self.output.with_suffix('.caller.log')).write_bytes(self.remote)
        if self.caller:
            self.caller.close()
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        os.close(self.master)
        os.close(self.slave)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tcpser', type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    print('Results: ' + str(output), flush=True)
    extracted = output / 'Unpacked elsewhere with spaces'
    print('Extracting release archive...', flush=True)
    subprocess.run(['/usr/bin/ditto', '-x', '-k', str(args.archive.resolve()), str(extracted)], check=True)
    package = extracted / 'RCPM-macOS-arm64'
    manifest = json.loads((package / 'MANIFEST.json').read_text())
    print('Verifying packaged file hashes...', flush=True)
    for group in ('common', 'host'):
        for relative, digest in manifest[group].items():
            assert sha(package / relative) == digest, relative
    assert {path.name for path in (package / 'disks').iterdir()} == {'drivea.dsk', 'drivei.dsk', 'drivep.dsk'}
    assert not (package / 'SYSOP.DOC').exists()
    assert not (package / 'state/initialized').exists()
    assert not (package / 'rbbs-trial-passwords.json').exists()
    if (package / 'DEVELOPMENT-MEDIA.json').is_file():
        from release_media import verify_public_development_media
        print('Checking separated development tools...', flush=True)
        verify_public_development_media(package, package / 'runtime')
    config = subprocess.check_output([str(package / 'runtime/rcpm'), '--check'], cwd='/tmp', text=True)
    assert 'direct 127.0.0.1:4000' in config
    try:
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', 4000))
        port = 4000
    except OSError:
        port = free_port()
    arguments = () if port == 4000 else ('--port', str(port))
    print('Starting direct TCP guest...', flush=True)
    guest = Guest(package, output / 'direct', *arguments)
    result = dict(archive=str(args.archive.resolve()), relocated_with_spaces=True,
                  minimal_system_path=True, common_and_host_hashes=True,
                  shipped_disks=['A', 'I', 'P'], default_port=4000, tested_port=port)
    try:
        guest.wait(b'RCP/M modem ready.')
        assert f'RCP/M is now running on port {port}.'.encode() in guest.local
        assert 'Windows, Linux, macOS'.encode() in guest.local
        assert (package / 'disks/drivej.dsk').stat().st_size == 255*128*128
        assert (package / 'SYSOP.DOC').stat().st_mode & 0o777 == 0o600
        assert not b'Fresh RBBS passwords' in guest.remote
        duplicate = Guest(package, output / 'duplicate', '--port', str(port))
        print('Checking duplicate-instance refusal...', flush=True)
        try:
            duplicate.process.wait(timeout=8)
            duplicate.collect(.2)
            assert duplicate.process.returncode == 1
            assert b'already running' in duplicate.local
        finally:
            duplicate.close()
        guest.connect(port)
        assert b'R C P / M' in guest.remote
        # Exercise shipped media directly; do not install topics during this
        # check, which would conceal omissions from the release archive.
        topics = Path(__file__).resolve().parent / 'guest/help'
        for topic in sorted(topics.glob('*.HLP')):
            name = topic.stem
            expected = topic.read_text(encoding='ascii').splitlines()[1].encode('ascii')
            command = 'HELP' if name == 'HELP' else 'HELP ' + name
            assert expected in guest.command(command), command
        result['shipped_caller_help_topics'] = len(list(topics.glob('*.HLP')))
        listing = guest.command('DIR SIGM:SIGMV001.LBR')
        assert b'SIGMV001' in listing
        listing = guest.command('DIR CPMUG:CPMUG093.LBR')
        assert b'CPMUG093' in listing
        listing = guest.command('MOUNT /L')
        assert b'GAMES' in listing and b'GUIDES' in listing and b'DEVEL' not in listing
        guest.command('MOUNT GAMES')
        listing = guest.command('DIR J1:ADV.COM')
        assert b'ADV' in listing and b'COM' in listing
        text = guest.command('TYPE J:README.TXT [NO PAGE]')
        assert b'unpacked games' in text and b'WORK remains non-executable.' in text
        guest.command('MOUNT GUIDES')
        listing = guest.command('DIR J:')
        assert b'README' in listing and b'LDIR' in listing
        text = guest.command('LT J:README.TXT')
        assert b'documentation only' in text
        start = len(guest.remote)
        print('Checking RBBS entry...', flush=True)
        for char in b'RBBS\r':
            guest.caller.sendall(bytes([char])); guest.collect(.04)
        guest.wait(b'Enter your FIRST Name:', remote=True, start=start)
        assert b'RCPM RBBS 3.7 Trial' not in guest.remote[start:]
        guest.stop()
        result.update(direct_boot=True, caller_login=True, archive_named_directories=True,
                      both_public_volumes=True, documentation_read=True, rbbs_entry=True,
                      first_start_private_credentials=True, duplicate_guest_refused=True,
                      orderly_shutdown=True, no_python_tmux_or_homebrew_required=True)
    finally:
        guest.close()
    secrets = (package / 'SYSOP.DOC').read_bytes()
    print('Direct TCP checks passed; verifying private credential records...', flush=True)
    directory = (package / 'disks/drivei.dsk').read_bytes()[:32768]
    entries = [directory[n:n+32] for n in range(0, 32768, 32)
               if directory[n:n+12] == b'\x0fpwds       ']
    assert len(entries) == 1
    block = int.from_bytes(entries[0][16:18], 'little')
    with (package / 'disks/drivei.dsk').open('rb') as stream:
        stream.seek(block * 2048)
        password_record = stream.read(128)
    for kind in (b'sysop', b'validation', b'direct-CP/M'):
        value = re.search(b'RBBS ' + kind + b' password: ([A-Z0-9]+)', secrets).group(1)
        assert value in password_record
    result['generated_passwords_match_guest_record'] = True
    (output / 'first-start-credential-sha256.txt').write_text(hashlib.sha256(secrets).hexdigest() + '\n')
    if args.tcpser:
        print('Starting real tcpser and IP232 guest...', flush=True)
        endpoint, caller_port = free_port(), free_port()
        with (output / 'tcpser.log').open('wb') as log:
            modem = subprocess.Popen([str(args.tcpser.resolve()), '-v', f'127.0.0.1:{endpoint}',
                                     '-p', f'127.0.0.1:{caller_port}', '-s', '2400', '-S', '2400',
                                     '-i', '&c1&d2', '-l', '0'], stdout=log, stderr=log, restore_signals=False)
            guest = Guest(package, output / 'modem', '--mode', 'ip232', '--port', str(endpoint))
            try:
                guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0')
                assert b'virtual modem endpoint' in guest.local
                # Let Hayes initialization finish; caller typeahead during
                # modem result parsing can interfere with the numeric reply.
                guest.collect(3)
                guest.connect(caller_port, kick=False)
                assert b'R C P / M' in guest.remote
                guest.stop()
                assert (package / 'SYSOP.DOC').read_bytes() == secrets
                result.update(ip232_driver_switch=True, real_tcpser_caller_login=True,
                              credentials_preserved_on_restart=True)
            finally:
                guest.close()
                modem.terminate()
                modem.wait(timeout=5)
        guest = Guest(package, output / 'direct-again', '--port', str(port))
        print('Checking switch back to direct TCP...', flush=True)
        try:
            guest.wait(b'RCP/M modem ready.')
            guest.connect(port)
            guest.stop()
            result['switch_back_to_direct'] = True
        finally:
            guest.close()
    result['public_redistribution'] = 'not cleared; retained notices identify unresolved restrictions'
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Release package checks passed.', flush=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
