#!/usr/bin/env python3
"""Qualify a Windows candidate in a separate console; needs build-time Python only.

Run on Windows: python check_windows_release.py candidate.zip --output NEW_FOLDER
No commands are typed into the VM and no credentials are printed in the report.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import select
import socket
import stat
import subprocess
import sys
import tempfile
import time
import zipfile


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def unpack(archive, output):
    with zipfile.ZipFile(archive) as stream:
        seen = set()
        reserved = {'CON', 'PRN', 'AUX', 'NUL',
                    *(f'COM{k}' for k in range(1, 10)), *(f'LPT{k}' for k in range(1, 10))}
        for entry in stream.infolist():
            path = PurePosixPath(entry.filename)
            if (path.is_absolute() or '..' in path.parts or '\\' in entry.filename
                    or ':' in entry.filename or not path.parts
                    or path.parts[0] != 'RCPM-windows-x64'
                    or stat.S_ISLNK(entry.external_attr >> 16)
                    or any(part.endswith((' ', '.')) or part.split('.')[0].upper() in reserved
                           for part in path.parts)
                    or path.as_posix() + ('/' if entry.is_dir() else '') != entry.filename):
                raise ValueError('Unsafe Windows archive member: ' + entry.filename)
            key = entry.filename.casefold()
            if key in seen:
                raise ValueError('Duplicate Windows archive member: ' + entry.filename)
            seen.add(key)
        stream.extractall(output)
    package = output / 'RCPM-windows-x64'
    manifest = json.loads((package / 'MANIFEST.json').read_text())
    if manifest.get('platform') != 'windows-x64':
        raise ValueError('Expected Windows x64 package manifest')
    if set(manifest['common']) & set(manifest['host']):
        raise ValueError('Common and host manifest groups overlap')
    expected = dict(manifest['common'], **manifest['host'])
    actual = {p.relative_to(package).as_posix() for p in package.rglob('*') if p.is_file()}
    if actual != set(expected) | {'MANIFEST.json'}:
        raise ValueError('Missing or unrecorded package files')
    for name, digest in expected.items():
        if sha(package / name) != digest:
            raise ValueError('Package hash mismatch: ' + name)
    return package


class Guest:
    """Own a console in this isolated worker, and drive it through Win32 APIs."""
    def __init__(self, package, output, port):
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.kernel = c.WinDLL('kernel32', use_last_error=True)
        class COORD(c.Structure):
            _fields_ = [('X', w.SHORT), ('Y', w.SHORT)]
        class INFO(c.Structure):
            _fields_ = [('size', COORD), ('cursor', COORD), ('attributes', w.WORD),
                        ('window', w.SMALL_RECT), ('maximum', COORD)]
        class KEY(c.Structure):
            _fields_ = [('down', w.BOOL), ('repeat', w.WORD), ('virtual', w.WORD),
                        ('scan', w.WORD), ('character', w.WCHAR), ('control', w.DWORD)]
        class EVENT(c.Union):
            _fields_ = [('key', KEY), ('padding', c.c_byte * 16)]
        class RECORD(c.Structure):
            _fields_ = [('kind', w.WORD), ('event', EVENT)]
        self.COORD, self.INFO, self.KEY, self.RECORD = COORD, INFO, KEY, RECORD
        self.kernel.GetStdHandle.argtypes = [w.DWORD]
        self.kernel.GetStdHandle.restype = w.HANDLE
        self.kernel.GetConsoleScreenBufferInfo.argtypes = [w.HANDLE, c.POINTER(INFO)]
        self.kernel.GetConsoleScreenBufferInfo.restype = w.BOOL
        self.kernel.ReadConsoleOutputCharacterW.argtypes = [w.HANDLE, w.LPWSTR, w.DWORD,
                                                          COORD, c.POINTER(w.DWORD)]
        self.kernel.ReadConsoleOutputCharacterW.restype = w.BOOL
        self.kernel.WriteConsoleInputW.argtypes = [w.HANDLE, c.POINTER(RECORD), w.DWORD, c.POINTER(w.DWORD)]
        self.kernel.WriteConsoleInputW.restype = w.BOOL
        self.input = self.kernel.GetStdHandle(-10 & 0xffffffff)
        self.screen = self.kernel.GetStdHandle(-11 & 0xffffffff)
        info = INFO()
        if not self.kernel.GetConsoleScreenBufferInfo(self.screen, c.byref(info)):
            raise c.WinError(c.get_last_error())
        self.position = info.cursor.Y * info.size.X + info.cursor.X
        self.local, self.remote, self.caller = bytearray(), bytearray(), None
        self.output, self.package, self.port = output, package, port
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('RCPM_', 'PYTHON')) and key != 'DISKDEFS'}
        env['PATH'] = os.path.join(os.environ['SystemRoot'], 'System32')
        arguments = [] if port == 4000 else ['--port', str(port)]
        self.process = subprocess.Popen([str(package / 'runtime/rcpm.exe'), *arguments],
                                        cwd=tempfile.gettempdir(), env=env)

    def collect(self, duration=.1):
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            info = self.INFO()
            if not self.kernel.GetConsoleScreenBufferInfo(self.screen, self.c.byref(info)):
                raise self.c.WinError(self.c.get_last_error())
            end = info.cursor.Y * info.size.X + info.cursor.X
            if end < self.position:
                # Cursor-addressing output: retain the visible tail as diagnostic evidence.
                self.position = max(0, end - info.size.X * 30)
            length = end - self.position
            if length:
                text = self.c.create_unicode_buffer(length + 1)
                count = self.w.DWORD()
                origin = self.COORD(self.position % info.size.X, self.position // info.size.X)
                if not self.kernel.ReadConsoleOutputCharacterW(self.screen, text, length,
                                                               origin, self.c.byref(count)):
                    raise self.c.WinError(self.c.get_last_error())
                self.local.extend(text.value.encode('utf-8'))
                self.position = end
            if self.caller and select.select([self.caller], [], [], .02)[0]:
                data = self.caller.recv(16384)
                if data:
                    self.remote.extend(data)
                else:
                    self.caller.close()
                    self.caller = None
            else:
                time.sleep(.01)

    def wait(self, marker, remote=False, start=0, timeout=45):
        deadline = time.monotonic() + timeout
        stream = self.remote if remote else self.local
        while marker not in stream[start:]:
            if time.monotonic() > deadline or self.process.poll() is not None:
                raise AssertionError('Waiting for ' + repr(marker) + ': ' + repr(bytes(stream[-1800:])))
            self.collect()
        return bytes(stream[start:])

    def send_local(self, data):
        for value in data:
            record = self.RECORD()
            record.kind = 1
            record.event.key = self.KEY(True, 1, 0, 0, chr(value), 0)
            count = self.w.DWORD()
            if not self.kernel.WriteConsoleInputW(self.input, self.c.byref(record), 1, self.c.byref(count)) or count.value != 1:
                raise self.c.WinError(self.c.get_last_error())
            self.collect(.04)

    def connect(self):
        self.caller = socket.create_connection(('127.0.0.1', self.port), timeout=5)
        deadline = time.monotonic() + 30
        while b'A0:SYSTEM>' not in self.remote:
            if time.monotonic() > deadline:
                raise AssertionError('Caller login: ' + repr(bytes(self.remote[-1800:])))
            self.caller.sendall(b'\r')
            self.collect(.4)

    def command(self, text):
        start = len(self.remote)
        for value in (text + '\r').encode('ascii'):
            self.caller.sendall(bytes([value])); self.collect(.025)
        return self.wait(b'A0:SYSTEM>', remote=True, start=start)

    def stop(self):
        if self.caller:
            self.caller.close(); self.caller = None; self.collect(1)
        start = len(self.local)
        self.send_local(b'\x03')
        self.wait(b'<RET> for', start=start)
        self.send_local(b'\r')
        self.wait(b'A0:SYSTEM>', start=start)
        self.collect(1)
        self.send_local(b'SYSUTLS:BYEBYE\r')
        self.process.wait(timeout=25)
        assert self.process.returncode == 0
        self.collect(.2)

    def close(self):
        self.output.with_suffix('.local.log').write_bytes(self.local)
        self.output.with_suffix('.caller.log').write_bytes(self.remote)
        if self.caller:
            self.caller.close()
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


def worker(package, output):
    import ctypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetConsoleWindow.restype = ctypes.c_void_p
    window = kernel.GetConsoleWindow()
    if window:
        user = ctypes.WinDLL('user32', use_last_error=True)
        user.ShowWindow.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user.ShowWindow(window, 0)
    result = dict(platform=sys.platform, windows_version=sys.getwindowsversion().build,
                  runtime_qualified=False, tests={})
    machine = ctypes.c_ushort(); native_machine = ctypes.c_ushort()
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.IsWow64Process2.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ushort),
                                     ctypes.POINTER(ctypes.c_ushort)]
    if not kernel.IsWow64Process2(kernel.GetCurrentProcess(), ctypes.byref(machine),
                                 ctypes.byref(native_machine)):
        raise ctypes.WinError(ctypes.get_last_error())
    result['process_machine'] = hex(machine.value)
    result['native_machine'] = hex(native_machine.value)
    guest = None
    try:
        tools = package / 'runtime'
        env = dict(os.environ, DISKDEFS=str(tools / 'diskdefs'))
        env['PATH'] = os.path.join(os.environ['SystemRoot'], 'System32')
        def tool(name, *args):
            return subprocess.check_output([str(tools / (name + '.exe')), *map(str, args)],
                env=env, cwd=tempfile.gettempdir(), stderr=subprocess.STDOUT)
        assert b'direct 127.0.0.1:4000' in tool('rcpm', '--check')
        assert not (package / 'SYSOP.DOC').exists() and not (package / 'state/initialized').exists()
        probe_directory = output / 'host-probes'; probe_directory.mkdir()
        probe = package / 'qualification/host-probe.exe'
        tested = subprocess.check_output([str(probe)], cwd=probe_directory, stderr=subprocess.STDOUT)
        assert b'HOST-PROBES-PASS' in tested
        (output / 'host-probes.log').write_bytes(tested)
        result['tests']['native_host_probes'] = True
        image = output / 'roundtrip.dsk'
        image.write_bytes((package / 'disks/drivea.dsk').read_bytes())
        body = output / 'binary-source.bin'; body.write_bytes(bytes(range(256)) * 16)
        tool('cpmcp', '-f', 'ibm-3740', image, body, '0:PROBE.BIN')
        recovered = output / 'binary-recovered.bin'
        tool('cpmcp', '-f', 'ibm-3740', image, '0:PROBE.BIN', recovered)
        assert recovered.read_bytes() == body.read_bytes()
        tool('cpmchattr', '-f', 'ibm-3740', image, '4', '0:PROBE.BIN')
        assert b'PROBE' in tool('cpmls', '-A', '-f', 'ibm-3740', image).upper()
        tool('cpmrm', '-f', 'ibm-3740', image, '0:PROBE.BIN')
        assert b'PROBE' not in tool('cpmls', '-f', 'ibm-3740', image).upper()
        blank = output / 'blank.dsk'; tool('mkfs.cpm', '-f', 'ibm-3740', blank)
        tool('cpmls', '-f', 'ibm-3740', blank)
        result['tests']['disk_tool_roundtrip_and_relocation'] = True
        receipt = json.loads((package / 'DEVELOPMENT-MEDIA.json').read_text())
        assert sha(package / 'offline/BUILD.dsk') == receipt['build_image_sha256']
        for name, digest in receipt['retained'].items():
            target = output / ('development-' + name)
            tool('cpmcp', '-f', 'z80pack-hd', package / 'offline/BUILD.dsk', '0:' + name, target)
            assert sha(target) == digest
        result['tests']['retained_development_files'] = len(receipt['retained'])
        with socket.socket() as server:
            try:
                server.bind(('127.0.0.1', 4000))
            except OSError:
                server.bind(('127.0.0.1', 0))
            port = server.getsockname()[1]
        result['tested_port'] = port
        guest = Guest(package, output / 'direct', port)
        guest.wait(b'RCP/M modem ready.')
        guest.connect()
        start = len(guest.local)
        duplicate = subprocess.Popen([str(tools / 'rcpm.exe')], cwd=tempfile.gettempdir(), env=env)
        assert duplicate.wait(timeout=10) == 1
        guest.collect(.2)
        assert b'already running' in guest.local[start:]
        result['tests']['duplicate_refused'] = True
        topics = sorted((package / 'source/rcpm/guest/help').glob('*.HLP'))
        assert len(topics) == 9
        for topic in topics:
            expected = topic.read_text(encoding='ascii').splitlines()[1].encode('ascii')
            assert expected in guest.command('HELP' if topic.stem == 'HELP' else 'HELP ' + topic.stem)
        assert b'SIGMV001' in guest.command('DIR SIGM:SIGMV001.LBR')
        assert b'CPMUG093' in guest.command('DIR CPMUG:CPMUG093.LBR')
        listing = guest.command('MOUNT /L')
        assert b'GAMES' in listing and b'GUIDES' in listing
        guest.command('MOUNT GAMES')
        assert b'ADV' in guest.command('DIR J1:ADV.COM')
        guest.command('MOUNT GUIDES')
        assert b'documentation only' in guest.command('LT J:README.TXT')
        start = len(guest.remote)
        for value in b'RBBS\r':
            guest.caller.sendall(bytes([value])); guest.collect(.04)
        guest.wait(b'Enter your FIRST Name:', remote=True, start=start)
        subprocess.check_output([str(probe), '--private', str(package / 'SYSOP.DOC')], stderr=subprocess.STDOUT)
        subprocess.check_output([str(probe), '--private', str(package / 'disks/drivei.dsk')], stderr=subprocess.STDOUT)
        secrets = (package / 'SYSOP.DOC').read_bytes()
        directory = (package / 'disks/drivei.dsk').read_bytes()[:32768]
        entries = [directory[n:n+32] for n in range(0, 32768, 32)
                   if directory[n:n+12] == b'\x0fpwds       ']
        assert len(entries) == 1
        block = int.from_bytes(entries[0][16:18], 'little')
        with (package / 'disks/drivei.dsk').open('rb') as stream:
            stream.seek(block * 2048); record = stream.read(128)
        for kind in (b'sysop', b'validation', b'direct-CP/M'):
            value = re.search(b'RBBS ' + kind + b' password: ([A-Z0-9]+)', secrets).group(1)
            assert value in record
        guest.stop(); guest.close(); guest = None
        result['tests'].update(direct_boot_and_caller=True, shipped_help_topics=len(topics),
            archives_mounts_rbbs=True, private_credentials_match=True, orderly_shutdown=True)
        guest = Guest(package, output / 'restart', port)
        guest.wait(b'RCP/M modem ready.'); guest.connect()
        assert (package / 'SYSOP.DOC').read_bytes() == secrets
        guest.stop(); guest.close(); guest = None
        result['tests']['restart_preserves_credentials'] = True
        result['runtime_qualified'] = True
        result['optional_ip232'] = 'not-tested'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
        raise
    finally:
        if guest:
            guest.close()
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


def main():
    if os.name != 'nt':
        raise SystemExit('Run live qualification on Windows; cross-compilation is not qualification.')
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3])); return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    package = unpack(args.archive.resolve(), output / 'Unpacked with spaces and Unicode é')
    process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker',
                                str(package), str(output)], creationflags=subprocess.CREATE_NEW_CONSOLE)
    code = process.wait()
    report = output / 'result.json'
    if report.is_file():
        print(report.read_text(), flush=True)
    else:
        raise SystemExit('Qualification worker failed before producing a report; exit ' + str(code))
    if code:
        raise SystemExit(code)
    print('PASS: ' + str(report))


if __name__ == '__main__':
    main()
