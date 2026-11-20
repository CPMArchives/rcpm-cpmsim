"""Protocol fixtures used by the disposable, single-machine BYE checks."""
from binascii import crc_hqx
from pathlib import Path
import shutil
import socket
import subprocess


DOWNLOAD = bytes(range(256)) * 9
XDATA = bytes(range(256)) * 5
YDATA = bytes(range(256)) * 9 + b'EXACT LENGTH\x00\xff'
MESSAGE = b'A persistent message from the shared machine.\r\n'
KEEP = b'OTHER USER AREAS MUST SURVIVE'.ljust(128, b'\x1a')


def prepare_work(source, tools, work, disk):
    i = work / 'disks/drivei.dsk'
    i.unlink(missing_ok=True)
    subprocess.run([str(tools / 'mkfs.cpm'), '-f', 'z80pack-hd', str(i)], check=True)
    fixture = work / 'KEEP.TXT'
    fixture.write_bytes(KEEP)
    for destination in ('0:BOOT.TXT', '1:KEEP.TXT'):
        subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'z80pack-hd', str(i),
                        str(fixture), destination], check=True)
    shutil.copyfile(Path(__file__).parent / 'guest/workprobe.asm', work / 'workprobe.asm')
    subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', 'workprobe.asm'],
                   cwd=work, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                    str(work / 'workprobe.bin'), '0:WORKPRB.COM'], check=True)


def verify_work_clean(tools, work):
    i = work / 'disks/drivei.dsk'
    # This fixture uses the known z80pack-hd layout: no reserved tracks,
    # 1024 directory entries. Avoid cpmls's unmatched-pattern crash.
    with i.open('rb') as image:
        directory = image.read(1024 * 32)
    if any(directory[offset] == 0 for offset in range(0, len(directory), 32)):
        raise RuntimeError('I0: WORK was not cleared at the call boundary')
    extracted = work / 'KEEP-CHECK.TXT'
    subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'z80pack-hd', str(i),
                    '1:KEEP.TXT', str(extracted)], check=True)
    if extracted.read_bytes() != KEEP:
        raise RuntimeError('WORK cleanup altered the I1: sentinel')


def prepare_services(source, tools, work, disk):
    subprocess.run([str(tools / 'cpmrm'), '-T', 'raw', '-f', 'ibm-3740',
                    str(disk), '0:DATE.COM'], check=True)
    for name in ('upload', 'message', 'ysend', 'serviceprobe'):
        shutil.copyfile(Path(__file__).parent / f'guest/{name}.asm', work / f'{name}.asm')
        subprocess.run([str(source / 'z80asm/z80asm'), '-fb', '-x', f'{name}.asm'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        target = 'SERVPRB' if name == 'serviceprobe' else name.upper()
        subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'ibm-3740', str(disk),
                        str(work / f'{name}.bin'), f'0:{target}.COM'], check=True)
    for name in ('upload-staging', 'upload-inbox'):
        path = work / name
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(mode=0o700)
    j = work / 'disks/drivej.dsk'
    j.unlink(missing_ok=True)
    subprocess.run([str(tools / 'mkfs.cpm'), '-f', 'z80pack-hd', str(j)], check=True)
    fixture = work / 'PAYLOAD.BIN'
    fixture.write_bytes(DOWNLOAD)
    subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', 'z80pack-hd', str(j),
                    str(fixture), '0:PAYLOAD.BIN'], check=True)
    j.chmod(0o444)


def exact(caller, count):
    output = bytearray()
    while len(output) < count:
        part = caller.recv(count - len(output))
        if not part:
            raise RuntimeError('Caller disconnected inside a protocol fixture')
        output.extend(part)
    return bytes(output)


def until(caller, marker):
    output = bytearray()
    while not output.endswith(marker):
        try:
            output.extend(exact(caller, 1))
        except (TimeoutError, socket.timeout) as error:
            raise RuntimeError(f'Timed out waiting for {marker!r}; received {bytes(output)!r}') from error
        if len(output) > 8192:
            raise RuntimeError(f'Protocol fixture did not see {marker!r}')


def expect(caller, expected):
    received = exact(caller, len(expected))
    if received != expected:
        raise RuntimeError(f'Protocol fixture expected {expected!r}, got {received!r}')


def packet(number, body):
    return bytes((1 if len(body) == 128 else 2, number, number ^ 255)) + body + crc_hqx(body, 0).to_bytes(2, 'big')


def upload_x(caller):
    caller.sendall(b'UPLOAD XFILE.BIN\r')
    until(caller, b'Ready for XMODEM/CRC upload (128-byte blocks).\r\n')
    expect(caller, b'C')
    for offset in range(0, len(XDATA), 128):
        frame = packet(offset // 128 + 1, XDATA[offset:offset + 128])
        if offset == 0:
            caller.sendall(frame[:-1] + bytes((frame[-1] ^ 1,)))
            expect(caller, b'\x15')
        caller.sendall(frame)
        expect(caller, b'\x06')
        if offset == 0:
            caller.sendall(frame)  # Retransmitted block must not duplicate file data.
            expect(caller, b'\x06')
    caller.sendall(b'\x04')
    expect(caller, b'\x06')


def upload_y(caller):
    caller.sendall(b'UPLOAD /Y\r')
    until(caller, b'Ready for YMODEM batch upload.\r\n')
    for name, data in (('YFILE.BIN', YDATA), ('EMPTY.TXT', b'')):
        expect(caller, b'C')
        header = (name.encode() + b'\0' + str(len(data)).encode() + b'\0').ljust(128, b'\0')
        caller.sendall(packet(0, header))
        expect(caller, b'\x06C')
        for offset in range(0, len(data), 1024):
            body = data[offset:offset + 1024].ljust(1024, b'\x1a')
            caller.sendall(packet(offset // 1024 + 1, body))
            expect(caller, b'\x06')
        caller.sendall(b'\x04')
        expect(caller, b'\x15')
        caller.sendall(b'\x04')
        expect(caller, b'\x06')
    expect(caller, b'C')
    caller.sendall(packet(0, bytes(128)))
    expect(caller, b'\x06')


def read_packet(caller, number):
    start = exact(caller, 1)[0]
    if start not in (1, 2):
        raise RuntimeError(f'Invalid YMODEM packet start: {start}')
    length = 128 if start == 1 else 1024
    frame = exact(caller, length + 4)
    if frame[:2] != bytes((number, number ^ 255)) or crc_hqx(frame[2:-2], 0) != int.from_bytes(frame[-2:], 'big'):
        raise RuntimeError('Invalid YMODEM number or CRC')
    return frame[2:-2]


def download_y(caller):
    caller.sendall(b'YSEND J:PAYLOAD.BIN\r')
    until(caller, b'Ready for YMODEM download.\r\n')
    caller.sendall(b'C')
    header = read_packet(caller, 0)
    if header.split(b'\0')[:2] != [b'PAYLOAD.BIN', str(len(DOWNLOAD)).encode()]:
        raise RuntimeError(f'Incorrect YMODEM filename/length: {header!r}')
    caller.sendall(b'\x06C')
    received = bytearray()
    block = 1
    while len(received) < len(DOWNLOAD):
        received.extend(read_packet(caller, block))
        caller.sendall(b'\x06')
        block = (block + 1) & 255
    if received[:len(DOWNLOAD)] != DOWNLOAD:
        raise RuntimeError('Shared-machine YMODEM download differs from the disk fixture')
    expect(caller, b'\x04')
    caller.sendall(b'\x15')
    expect(caller, b'\x04')
    caller.sendall(b'\x06C')
    if any(read_packet(caller, 0)):
        raise RuntimeError('YMODEM batch terminator was not empty')
    caller.sendall(b'\x06')


def partial_upload(caller):
    caller.sendall(b'UPLOAD BROKEN.BIN\r')
    until(caller, b'Ready for XMODEM/CRC upload (128-byte blocks).\r\n')
    expect(caller, b'C')
    caller.sendall(b'\x01\x01\xfePARTIAL')


def verify_inbox(work):
    expected = {'XFILE.BIN': XDATA, 'YFILE.BIN': YDATA, 'EMPTY.TXT': b'', 'MESSAGE.TXT': MESSAGE}
    entries = list((work / 'upload-inbox').iterdir())
    if len(entries) != len(expected):
        raise RuntimeError(f'Unexpected inbox entries: {[entry.name for entry in entries]}')
    for name, data in expected.items():
        matching = [entry for entry in entries if entry.name.startswith(name + '.')]
        if len(matching) != 1 or matching[0].read_bytes() != data:
            raise RuntimeError(f'Persistent inbox differs for {name}')
    if list((work / 'upload-staging').iterdir()):
        raise RuntimeError('Unfinished upload staging survived call recovery')
