#!/usr/bin/env python3
"""Cross-build the raw-image disk tools as native Windows x64 executables."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

PROGRAMS = ('cpmcp', 'cpmls', 'cpmrm', 'cpmchattr', 'mkfs.cpm')


def build(source, toolchain, output):
    compiler = toolchain / 'bin/x86_64-w64-mingw32-gcc'
    inspector = toolchain / 'bin/llvm-readobj'
    if not compiler.is_file() or not inspector.is_file():
        raise ValueError('Expected an existing LLVM-MinGW toolchain')
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'source'
    shutil.copytree(source, work, ignore=shutil.ignore_patterns(
        '*.o', '*.a', '*.exe', 'config.log', 'config.status', 'config.cache',
        'config.h', 'Makefile', *PROGRAMS))
    driver = work / 'device_posix.c'
    text = driver.read_text()
    if text.count('if (deviceOpts != NULL)') != 1:
        raise ValueError('Expected unmodified cpmtools 2.23 raw device driver')
    text = text.replace('if (deviceOpts != NULL)',
                        'if (deviceOpts != NULL && strcmp(deviceOpts, "raw") != 0)')
    if text.count('open(filename,mode)') != 1:
        raise ValueError('Unexpected image open implementation')
    # MS CRT text mode corrupts raw disk bytes (CR/LF and Ctrl-Z).
    text = text.replace('open(filename,mode)', 'open(filename,mode | O_BINARY)')
    driver.write_text(text)
    filesystem = work / 'cpmfs.c'
    text = filesystem.read_text()
    if text.count('fopen(DISKDEFS,"r")') != 1:
        raise ValueError('Unexpected diskdefs lookup implementation')
    # The launcher supplies an absolute path inside the relocated package.
    text = text.replace('fopen(DISKDEFS,"r")',
                        'fopen(getenv("DISKDEFS") ? getenv("DISKDEFS") : DISKDEFS,"r")')
    filesystem.write_text(text)
    env = dict(os.environ, CC=str(compiler),
               AR=str(toolchain / 'bin/x86_64-w64-mingw32-ar'),
               RANLIB=str(toolchain / 'bin/x86_64-w64-mingw32-ranlib'),
               CFLAGS='-O2 -D_FILE_OFFSET_BITS=64', LDFLAGS='-static')
    with (output / 'build.log').open('w') as log:
        for command in (
            ['/bin/sh', './configure', '--host=x86_64-pc-mingw32',
             '--with-diskdefs=diskdefs'],
            ['make', '-j4', *(name + '.exe' for name in PROGRAMS)],
        ):
            subprocess.run(command, cwd=work, env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    runtime = output / 'runtime'
    runtime.mkdir()
    audits = {}
    for name in PROGRAMS:
        path = runtime / (name + '.exe')
        shutil.copy2(work / path.name, path)
        headers = subprocess.check_output(
            [str(inspector), '--file-headers', '--coff-imports', str(path)], text=True)
        if 'IMAGE_FILE_MACHINE_AMD64' not in headers:
            raise ValueError('Expected Windows x64 PE: ' + name)
        imports = [line.split(':', 1)[1].strip() for line in headers.splitlines()
                   if line.strip().startswith('Name:')]
        if any(not (dll.lower() in ('kernel32.dll', 'msvcrt.dll')
                    or dll.lower().startswith('api-ms-win-crt-')) for dll in imports):
            raise ValueError('Unexpected tool DLL dependency: ' + repr(imports))
        audits[path.name] = dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                imports=imports)
    shutil.copy2(work / 'diskdefs', runtime / 'diskdefs')
    shutil.copy2(work / 'COPYING', output / 'COPYING')
    receipt = dict(platform='windows-x64', status='cross-compiled-not-runtime-qualified',
                   compiler=subprocess.check_output([str(compiler), '--version'], text=True),
                   changes=['accept explicit raw driver', 'open disk images in binary mode',
                            'honor launcher DISKDEFS environment for relocation'],
                   binaries=audits)
    (output / 'BUILD.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('Built and audited native Windows disk tools: ' + str(runtime))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.source.resolve(), args.toolchain.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
