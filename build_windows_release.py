#!/usr/bin/env python3
"""Cross-build an unqualified native Windows x64 RCP/M engineering candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

from backup_rcpm import copy_file
from build_linux_release import unpack_common, verify_common, sha
from build_windows_tools import build as build_tools
from build_windows_runtime import build as build_runtime
from windows.build_support import build_launcher, build_probe, audit

REPO = Path(__file__).resolve().parent
ALLOWED = {'kernel32.dll', 'ws2_32.dll', 'advapi32.dll', 'bcrypt.dll', 'msvcrt.dll'}


def build(common_archive, toolchain, output):
    output.mkdir(parents=True, exist_ok=False)
    common = unpack_common(common_archive, output / 'common-input')
    common_files = verify_common(common)
    native = output / 'native'
    native.mkdir()
    build_tools(common / 'source/upstream/cpmtools-2.23', toolchain, native / 'tools')
    build_runtime(common / 'source/upstream/z80pack', toolchain, native / 'emulator')
    executable = build_launcher(toolchain, native / 'launcher')
    payload = output / 'RCPM-windows-x64'
    shutil.copytree(common, payload, copy_function=lambda source, target:
                    copy_file(Path(source), Path(target), Path(source).stat().st_mode & 0o777) and target)
    (payload / 'COMMON-MANIFEST.json').unlink()
    probe = build_probe(toolchain, native / 'qualification', native / 'emulator/host.o')
    (payload / 'qualification').mkdir()
    shutil.copy2(probe, payload / 'qualification/host-probe.exe')
    shutil.copy2(REPO / 'check_windows_release.py', payload / 'qualification/check_windows_release.py')
    runtime = payload / 'runtime'
    for name in ('cpmcp.exe', 'cpmls.exe', 'cpmrm.exe', 'cpmchattr.exe', 'mkfs.cpm.exe'):
        shutil.copy2(native / 'tools/runtime' / name, runtime / name)
    shutil.copy2(native / 'emulator/cpmsim.exe', runtime / 'cpmsim.exe')
    shutil.copy2(executable, runtime / 'rcpm.exe')
    (payload / 'Start-RCPM.cmd').write_bytes(
        b'@echo off\r\n"%~dp0runtime\\rcpm.exe" %*\r\nexit /b %errorlevel%\r\n')
    (payload / 'WINDOWS-README.txt').write_text(
        'RCP/M Windows x64 engineering candidate - NOT RUNTIME QUALIFIED\n\n'
        'Extract the entire ZIP into a writable local NTFS directory.\n'
        'From Windows Terminal or Command Prompt, run Start-RCPM.cmd.\n'
        'The window is the local sysop console. Raw TCP callers connect to\n'
        '127.0.0.1 port 4000 after the modem-ready announcement.\n'
        'No Python, WSL, Cygwin, compiler or installed CP/M tools are required\n'
        'to run the package. Windows ACL support is required for private data.\n'
        'Windows 10 version 1903 or newer is the provisional API baseline;\n'
        'no Windows version has yet passed runtime qualification for this port.\n'
        'Stop with SYSUTLS:BYEBYE at the local CP/M console. Closing the window\n'
        'forcibly terminates the emulator and is not an orderly shutdown.\n'
        'See SYSOP-GUIDE.DOC; substitute Start-RCPM.cmd for the historical\n'
        'macOS launcher name. Generated SYSOP.DOC contains private credentials.\n'
        'Legacy Unix auxiliary pipes/TCP serial boards are disabled. The RCP/M\n'
        'modem, transfer and service ports retain their existing implementation.\n'
        'This candidate has only been cross-compiled and statically audited.\n'
        'It is not cleared for public redistribution. See DISTRIBUTION-STATUS.DOC.\n')
    host_source = payload / 'source/host-windows'
    host_source.mkdir()
    for name in ('build_windows_release.py', 'build_windows_runtime.py', 'build_windows_tools.py',
                 'build_modem_runtime.py', 'build_linux_release.py', 'backup_rcpm.py',
                 'shared_instance.py', 'release_media.py', 'check_windows_release.py'):
        shutil.copy2(REPO / name, host_source / name)
    for name in ('windows', 'emulator', 'patches'):
        shutil.copytree(REPO / name, host_source / name,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(REPO / 'docs/windows-host-build.md', host_source / 'README.md')
    (host_source / 'packaging').mkdir()
    shutil.copy2(REPO / 'packaging/launcher.c', host_source / 'packaging/launcher.c')
    for area in ('tools', 'emulator', 'launcher'):
        for name in ('BUILD.json', 'build.log', 'launcher.c'):
            source = native / area / name
            if source.is_file():
                destination = host_source / 'build-records' / area / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    binaries = {path.relative_to(payload).as_posix(): audit(toolchain, path, ALLOWED)
                for path in (*runtime.glob('*.exe'), payload / 'qualification/host-probe.exe')}
    metadata = dict(platform='windows-x64', common_archive_sha256=sha(common_archive),
        status='cross-compiled-not-runtime-qualified', native=binaries,
        minimum_windows='10-1903-provisional-unqualified', filesystem='NTFS-with-private-ACLs',
        guest_service_implementation='existing shared emulator/rcpm_modem.c and rcpm_transfer.c',
        live_qualification='not-run', redistribution='not-cleared')
    (payload / 'BUILD-HOST.json').write_text(json.dumps(metadata, indent=2) + '\n')
    for name, digest in common_files.items():
        if sha(payload / name) != digest:
            raise ValueError('Windows build changed common payload: ' + name)
    host_files = {path.relative_to(payload).as_posix(): sha(path) for path in payload.rglob('*')
                  if path.is_file() and path.relative_to(payload).as_posix() not in common_files}
    manifest = dict(format='rcpm-release-candidate-1', platform='windows-x64',
                    status='cross-compiled-not-runtime-qualified-redistribution-not-cleared',
                    launcher='Start-RCPM.cmd', common=common_files, host=host_files,
                    common_archive_sha256=sha(common_archive))
    (payload / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    archive = output / 'rcpm-windows-x64-candidate.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(payload.rglob('*')):
            stream.write(path, path.relative_to(output).as_posix())
    (output / 'SHA256SUMS').write_text(sha(archive) + '  ' + archive.name + '\n')
    print('Built Windows candidate; runtime qualification pending: ' + str(archive), flush=True)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--common', type=Path, required=True)
    parser.add_argument('--toolchain', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.common.resolve(), args.toolchain.resolve(), args.output.resolve())


if __name__ == '__main__':
    main()
