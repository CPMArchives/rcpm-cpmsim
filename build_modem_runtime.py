#!/usr/bin/env python3
"""Build isolated cpmsim with an additive BYE modem device on ports 70-72."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def integrate(io_text):
    # Existing console and serial devices retain their handlers and semantics.
    for port in (70, 71, 72):
        if re.search(r'\[\s*' + str(port) + r'\s*\]\s*=', io_text):
            raise ValueError(f'I/O port {port} is already assigned')
    replacements = {
        'in_func_t *const port_in[256] = {': '#include "rcpm_modem.c"\n\n'
            '/* The host filesystem is never a guest disk in RCP/M mode. */\n'
            'static void rcpm_host_bdos_out(BYTE data)\n{\n'
            '\tif (rm_mode) { A = 0xff; return; }\n'
            '\thost_bdos_out(data);\n}\n\n'
            'in_func_t *const port_in[256] = {\n'
            '\t[70] = rcpm_modem_status,\n\t[71] = rcpm_modem_read,\n\t[72] = rcpm_modem_control_read,',
        'out_func_t *const port_out[256] = {': 'out_func_t *const port_out[256] = {\n'
            '\t[71] = rcpm_modem_write,\n\t[72] = rcpm_modem_control,',
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
    return io_text.replace('cpu_state = STOPPED;', 'cpu_state = ST_STOPPED;')


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
        io = sim / 'simio.c'
        try:
            io.write_text(integrate(io.read_text()))
        except ValueError as error:
            parser.error(str(error))
        shutil.copyfile(Path(__file__).parent / 'emulator/rcpm_modem.c', sim / 'rcpm_modem.c')
        subprocess.run(['make', '-j4', 'all', f'SIM={root / "cpmsim-modem"}'], cwd=sim, check=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        staged = output.with_name(output.name + '.new')
        shutil.copy2(root / 'cpmsim-modem', staged)
        staged.replace(output)
    print(f'Built {output}')


if __name__ == '__main__':
    main()
