#!/usr/bin/env python3
"""Build the existing RCP/M cpmsim with isolated native Win32 host adapters."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from build_modem_runtime import prepare_service_source, integrate
from windows.build_support import resource, audit
REPO = Path(__file__).resolve().parent


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Unsupported Windows integration point: ' + old[:100])
    return text.replace(old, new)


def build(source, toolchain, output):
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'source'
    for directory in ('cpmsim/srcsim', 'z80core', 'iodevices'):
        shutil.copytree(source / directory, work / directory,
                        ignore=shutil.ignore_patterns('*.o', '*.d'))
    sim = work / 'cpmsim/srcsim'
    header = sim / 'sim.h'
    # Legacy Unix pipes and optional TCP serial boards are outside this release's
    # virtual hardware contract. The RCP/M modem ports 70-74 remain enabled.
    text = re.sub(r'^#define (?:PIPES|NETWORKING|TCPASYNC)\b.*\n', '', header.read_text(), flags=re.M)
    header.write_text(text)
    prepare_service_source(work)
    io = sim / 'simio.c'
    io.write_text(integrate(io.read_text()))
    for name in ('rcpm_modem.c', 'rcpm_transfer.c', 'rcpm_mount.c'):
        shutil.copy2(REPO / 'emulator' / name, sim / name)
    shutil.copytree(REPO / 'windows', work / 'windows')
    # Preserve API names used by the CPU; only the implementation is host-specific.
    (work / 'iodevices/unix_terminal.h').write_text(
        (REPO / 'windows/include/unix_terminal.h').read_text())
    (work / 'iodevices/unix_terminal.c').write_text('/* implemented in windows/host.c */\n')
    fun = work / 'z80core/simfun.c'
    text = fun.read_text()
    start = text.index('uint64_t get_clock_us(void)\n{')
    end = text.index('\n#ifdef WANT_ICE', start)
    text = text[:start] + 'uint64_t get_clock_us(void)\n{\n    return rcpm_monotonic_us();\n}\n' + text[end:]
    fun.write_text(text)
    main = work / 'z80core/simmain.c'
    main.write_text(replace_once(main.read_text(),
        'int main(int argc, char *argv[])\n#endif\n{',
        'int main(int argc, char *argv[])\n#endif\n{\n'
        '\t_set_fmode(_O_BINARY);\n\t_setmode(0, _O_BINARY);\n\t_setmode(1, _O_BINARY);'))
    # Windows CRT streams must not translate binary core/image bytes.
    for relative in ('z80core/simmain.c', 'z80core/simfun.c', 'cpmsim/srcsim/simio.c'):
        path = work / relative
        text = path.read_text()
        text = re.sub(r'(fopen\([^\n,]+,\s*)"([rwa])"', r'\1"\2b"', text)
        path.write_text(text)
    compiler = toolchain / 'bin/x86_64-w64-mingw32-gcc'
    flags = ['-std=c99', '-O2', '-Wall', '-Wextra', '-Wno-unused-parameter',
             '-D_WIN32_WINNT=0x0A00', '-D_FILE_OFFSET_BITS=64',
             '-DCONFDIR="./conf"', '-DDISKSDIR="./disks"',
             '-include', str(work / 'windows/host.h'),
             '-I' + str(work / 'windows/include'), '-I' + str(work / 'windows'),
             '-I' + str(sim), '-I' + str(work / 'z80core'), '-I' + str(work / 'iodevices')]
    core = ('sim8080 simcore simdis simfun simglb simice simint simmain simz80 '
            'simz80-cb simz80-dd simz80-ddcb simz80-ed simz80-fd simz80-fdcb').split()
    files = [work / 'z80core' / (name + '.c') for name in core]
    files += [sim / (name + '.c') for name in ('simcfg', 'simio', 'simmem', 'simctl')]
    files += [work / 'iodevices' / (name + '.c') for name in ('rtc80', 'simbdos')]
    host_object = output / 'host.o'
    host_flags = [flag for flag in flags]
    position = host_flags.index('-include')
    del host_flags[position:position + 2]
    subprocess.run([str(compiler), *host_flags, '-Werror', '-c', str(work / 'windows/host.c'),
                    '-o', str(host_object)], check=True)
    files += [host_object, resource(toolchain, output)]
    runtime = output / 'cpmsim.exe'
    command = [str(compiler), *flags, *map(str, files), '-static', '-lws2_32', '-o', str(runtime)]
    with (output / 'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    binary_audit = audit(toolchain, runtime, {'kernel32.dll', 'ws2_32.dll', 'msvcrt.dll'})
    receipt = dict(binary_audit=binary_audit, platform='windows-x64', status='cross-compiled-not-runtime-qualified',
                   sha256=hashlib.sha256(runtime.read_bytes()).hexdigest(),
                   command=command, guest_ports_unchanged=True, installation_layout=2,
                   legacy_unix_devices_disabled=['PIPES', 'NETWORKING', 'TCPASYNC'])
    (output / 'BUILD.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Built native Windows RCP/M emulator: ' + str(runtime))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source.resolve(), args.toolchain.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
