#!/usr/bin/env python3
"""Build isolated cpmsim with modem ports 70-72, reset 73 and idle timer 74."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def integrate(io_text):
    # Existing console and serial devices retain their handlers and semantics.
    for port in (70, 71, 72, 73, 74):
        if re.search(r'\[\s*' + str(port) + r'\s*\]\s*=', io_text):
            raise ValueError(f'I/O port {port} is already assigned')
    replacements = {
        'in_func_t *const port_in[256] = {': '#include "rcpm_modem.c"\n'
            '#include "rcpm_transfer.c"\n\n'
            '/* The host filesystem is never a guest disk in RCP/M mode. */\n'
            'static void rcpm_host_bdos_out(BYTE data)\n{\n'
            '\tif (rm_mode) { A = 0xff; return; }\n'
            '\thost_bdos_out(data);\n}\n\n'
            'in_func_t *const port_in[256] = {\n'
            '\t[70] = rcpm_modem_status,\n\t[71] = rcpm_modem_read,\n\t[72] = rcpm_modem_control_read,\n'
            '\t[74] = rcpm_idle_read,',
        'out_func_t *const port_out[256] = {': 'out_func_t *const port_out[256] = {\n'
            '\t[71] = rcpm_modem_write,\n\t[72] = rcpm_modem_control,\n'
            '\t[73] = rcpm_services_reset,\n\t[74] = rcpm_idle_reset,',
        '\n#ifdef PIPES\n\t/* check if /tmp/.z80pack exists */':
            '\n\tif (rcpm_modem_init() < 0) exit(EXIT_FAILURE);\n'
            '\n#ifdef PIPES\n\t/* check if /tmp/.z80pack exists */',
        'void exit_io(void)\n{\n\tregister int i;':
            'void exit_io(void)\n{\n\tregister int i;\n\n\trcpm_modem_close();',
        '[161] = host_bdos_out': '[161] = rcpm_host_bdos_out',
        'if (disks[drive].fd == NULL) {':
            'if (drive >= sizeof(disks) / sizeof(disks[0]) || disks[drive].fd == NULL) {',
    }
    for old, new in replacements.items():
        if io_text.count(old) != 1:
            raise ValueError('Unsupported simio.c integration point: ' + old.splitlines()[0])
        io_text = io_text.replace(old, new)
    # Keep protocol logic and guest service ports; replace only their wire I/O.
    start = io_text.index('static int upload_read(')
    end = io_text.index('static int upload_signal(', start)
    io_text = io_text[:start] + '''static int upload_read(BYTE *buffer, size_t size, int timeout)
{
    return rcpm_transfer_read(buffer, size, timeout);
}

''' + io_text[end:]
    start = io_text.index('/* Persistent uploads on guest port 61,')
    end = io_text.index('#include "rcpm_modem.c"', start)
    services = io_text[start:end]
    if services.count('write(STDOUT_FILENO, ') != 5:
        raise ValueError('Unsupported upload/YMODEM transport integration points')
    services = services.replace('write(STDOUT_FILENO, ', 'rcpm_transfer_write(')
    io_text = io_text[:start] + (
        'static int rcpm_transfer_read(BYTE *, size_t, int);\n'
        'static ssize_t rcpm_transfer_write(const void *, size_t);\n\n'
        + services + io_text[end:])
    old = 'fd = open(path, O_RDONLY | O_NONBLOCK);'
    if io_text.count(old) != 1:
        raise ValueError('Unexpected catalog open point')
    io_text = io_text.replace(old, 'fd = open(path, O_RDWR | O_NONBLOCK);\n\tif (fd == -1) fd = open(path, O_RDONLY | O_NONBLOCK);')
    return io_text.replace('cpu_state = STOPPED;', 'cpu_state = ST_STOPPED;')


def prepare_service_source(root):
    """Apply missing service patches to the isolated copy, in dependency order."""
    io = root / 'cpmsim/srcsim/simio.c'
    patches = Path(__file__).parent / 'patches'
    for name, marker in (
        ('cpmsim-live-mount.patch', 'static BYTE mount_in(void)'),
        ('cpmsim-uploads.patch', 'static int receive_upload(FILE *file)'),
        ('cpmsim-messages.patch', 'static void message_out(BYTE data)'),
        ('cpmsim-ymodem.patch', 'static int receive_y_batch(void)'),
    ):
        if marker not in io.read_text():
            subprocess.run(['git', 'apply', '--check', str(patches / name)], cwd=root, check=True)
            subprocess.run(['git', 'apply', str(patches / name)], cwd=root, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='z80pack source tree')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix='rcpm-modem-build-') as temporary:
        root = Path(temporary)
        for directory in ('cpmsim/srcsim', 'z80core', 'iodevices'):
            shutil.copytree(source / directory, root / directory,
                            ignore=shutil.ignore_patterns('*.o', '*.d'))
        sim = root / 'cpmsim/srcsim'
        header = sim / 'sim.h'
        text = header.read_text()
        text = re.sub(r'^#define PIPES\b.*\n', '', text, flags=re.MULTILINE)
        header.write_text(text)
        prepare_service_source(root)
        io = sim / 'simio.c'
        try:
            io.write_text(integrate(io.read_text()))
        except ValueError as error:
            parser.error(str(error))
        shutil.copyfile(Path(__file__).parent / 'emulator/rcpm_modem.c', sim / 'rcpm_modem.c')
        shutil.copyfile(Path(__file__).parent / 'emulator/rcpm_transfer.c', sim / 'rcpm_transfer.c')
        subprocess.run(['make', '-j4', 'all', f'SIM={root / "cpmsim-modem"}'], cwd=sim, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        staged = output.with_name(output.name + '.new')
        shutil.copy2(root / 'cpmsim-modem', staged)
        staged.replace(output)
        output.with_name(output.name + '.features.json').write_text(json.dumps(dict(
            format='rcpm-runtime-features-1', idle_timer_port=74, sysop_writable_catalog=True,
            sha256=hashlib.sha256(output.read_bytes()).hexdigest()), indent=2) + '\n')
    print(f'Built {output}')


if __name__ == '__main__':
    main()
