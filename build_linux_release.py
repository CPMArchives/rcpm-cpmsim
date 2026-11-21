#!/usr/bin/env python3
"""Build Linux x64/ARM64 host files around an unchanged, verified common payload."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from backup_rcpm import copy_file
from release_media import verify_public_development_media

REPO = Path(__file__).resolve().parent
NATIVE = ('rcpm', 'cpmsim', 'cpmcp', 'cpmls', 'cpmrm', 'cpmchattr', 'mkfs.cpm')


def host_architecture():
    if platform.system() == 'Linux':
        machine = platform.machine().lower()
        if machine in ('x86_64', 'amd64'):
            return 'x64'
        if machine in ('aarch64', 'arm64'):
            return 'arm64'
    raise ValueError('Build this package on a Linux x64 or ARM64 host')


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            result.update(block)
    return result.hexdigest()


def unpack_common(archive, output):
    """Accept only the builder's regular-file/directory common ZIP layout."""
    with zipfile.ZipFile(archive) as source:
        for entry in source.infolist():
            name = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (not name.parts or name.is_absolute() or '..' in name.parts
                    or name.parts[0] != 'rcpm-common' or '\\' in entry.filename
                    or stat.S_ISLNK(mode)):
                raise ValueError('Unexpected common archive member: ' + entry.filename)
        source.extractall(output)
        for entry in source.infolist():
            permissions = (entry.external_attr >> 16) & 0o777
            if permissions:
                (output / entry.filename).chmod(permissions)
    return output / 'rcpm-common'


def verify_common(common):
    expected = json.loads((common / 'COMMON-MANIFEST.json').read_text())
    actual = {str(path.relative_to(common)) for path in common.rglob('*') if path.is_file()}
    if actual != set(expected) | {'COMMON-MANIFEST.json'}:
        raise ValueError('Common payload contains missing or unrecorded files')
    for name, digest in expected.items():
        if sha(common / name) != digest:
            raise ValueError('Common payload hash mismatch: ' + name)
    if not (common / 'DEVELOPMENT-MEDIA.json').is_file():
        raise ValueError('Use the common payload with separated development tools')
    return expected


def audit_native(path, architecture):
    env = dict(os.environ, LC_ALL='C')
    header = subprocess.check_output(['readelf', '-h', str(path)], text=True, env=env)
    machine = r'X86-64' if architecture == 'x64' else r'AArch64'
    if 'ELF64' not in header or not re.search(r'Machine:.*' + machine, header, re.I):
        raise ValueError('Expected Linux ' + architecture + ' ELF executable: ' + str(path))
    dependencies = subprocess.check_output(['ldd', str(path)], text=True, env=env)
    if 'not found' in dependencies:
        raise ValueError('Missing native dependency: ' + dependencies)
    for line in dependencies.splitlines():
        if '=>' in line:
            target = line.split('=>', 1)[1].strip().split()[0]
            if not target.startswith(('/lib/', '/lib64/', '/usr/lib/', '/usr/lib64/')):
                raise ValueError('Non-system dependency: ' + target)
    versions = subprocess.check_output(['readelf', '--version-info', str(path)], text=True, env=env)
    glibc = set(re.findall(r'GLIBC_(\d+(?:\.\d+)+)', versions))
    return dict(dependencies=dependencies.splitlines(),
                required_glibc_symbols_through=max(glibc, key=lambda s: tuple(map(int, s.split('.'))))
                if glibc else None)


def build(common_archive, output):
    architecture = host_architecture()
    target = 'linux-' + architecture
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='native-build-', dir=output) as temporary:
        work = Path(temporary)
        common = unpack_common(common_archive, work)
        common_files = verify_common(common)
        upstream = common / 'source/upstream'
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(('RCPM_', 'DYLD_')) and key != 'MACOSX_DEPLOYMENT_TARGET'}
        env['PYTHONUNBUFFERED'] = '1'

        def run(*command):
            print('Building: ' + ' '.join(map(str, command)), flush=True)
            subprocess.run(list(map(str, command)), env=env, check=True)

        tools = work / 'cpmtools'
        emulator = work / 'cpmsim'
        run(sys.executable, REPO / 'build_raw_cpmtools.py', upstream / 'cpmtools-2.23', '--output', tools)
        run(sys.executable, REPO / 'build_modem_runtime.py', upstream / 'z80pack', emulator)
        payload = output / ('RCPM-' + target)
        shutil.copytree(common, payload, copy_function=lambda source, target:
                        copy_file(Path(source), Path(target), Path(source).stat().st_mode & 0o777) and target)
        (payload / 'COMMON-MANIFEST.json').unlink()
        runtime = payload / 'runtime'
        shutil.copy2(emulator, runtime / 'cpmsim')
        shutil.copy2(emulator.with_name('cpmsim.features.json'), runtime / 'cpmsim.features.json')
        for name in NATIVE[2:]:
            shutil.copy2(tools / 'bin' / name, runtime / name)
        run('cc', '-D_XOPEN_SOURCE=700', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
            REPO / 'packaging/launcher.c', '-o', runtime / 'rcpm')
        launcher = payload / 'Start-RCPM.sh'
        launcher.write_text('#!/bin/sh\nset -eu\ncd -P "$(dirname "$0")"\nexec ./runtime/rcpm "$@"\n')
        launcher.chmod(0o755)
        readme = payload / 'LINUX-README.txt'
        readme.write_text(
            'RCP/M Linux ' + architecture + ' engineering candidate\n\n'
            'In a terminal, run ./Start-RCPM.sh from this unpacked writable folder.\n'
            'The terminal remains the sysop console. Connect a raw TCP terminal\n'
            'client to 127.0.0.1 port 4000 after RCP/M modem ready appears.\n'
            'No Python, tmux, compiler or installed CP/M tools are needed to run.\n'
            'See SYSOP-GUIDE.DOC for operation; use Start-RCPM.sh where the shared\n'
            'historical macOS installation notes name Start-RCPM.command.\n'
            'BUILD-HOST.json records the actual build host and dependencies.\n'
            'This archive still requires Linux live qualification and is not\n'
            'cleared for public redistribution. Read DISTRIBUTION-STATUS.DOC.\n')
        # Preserve the actual host build scripts/flags alongside the common
        # upstream sources, without modifying the shared payload's source files.
        host_source = payload / 'source/host-linux'
        host_source.mkdir()
        for source in ('build_linux_release.py', 'build_raw_cpmtools.py', 'build_modem_runtime.py',
                       'backup_rcpm.py', 'shared_instance.py', 'release_media.py',
                       'check_release.py', 'packaging/launcher.c'):
            target = host_source / source
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / source, target)
        for folder in ('emulator', 'patches'):
            shutil.copytree(REPO / folder, host_source / folder)
        audit = {name: audit_native(runtime / name, architecture) for name in NATIVE}
        metadata = dict(platform=target, common_archive_sha256=sha(common_archive),
                        built_on=platform.platform(), libc=platform.libc_ver(),
                        compiler=subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
                        launcher_flags=['-D_XOPEN_SOURCE=700', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror'],
                        native=audit, live_qualification='not-run', redistribution='not-cleared')
        (payload / 'BUILD-HOST.json').write_text(json.dumps(metadata, indent=2) + '\n')
        verify_public_development_media(payload, runtime)
        for name, digest in common_files.items():
            if sha(payload / name) != digest:
                raise ValueError('Host build changed common payload: ' + name)
        host_files = {str(path.relative_to(payload)): sha(path) for path in payload.rglob('*')
                      if path.is_file() and str(path.relative_to(payload)) not in common_files}
        manifest = dict(format='rcpm-release-candidate-1', platform=target,
                        status='local-engineering-candidate-redistribution-not-cleared',
                        launcher='Start-RCPM.sh', common=common_files, host=host_files,
                        common_archive_sha256=metadata['common_archive_sha256'])
        (payload / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        destination = output / ('rcpm-' + target + '-candidate.tar.gz')
        with tarfile.open(destination, 'w:gz') as archive:
            archive.add(payload, arcname=payload.name)
        (output / 'SHA256SUMS').write_text(f'{sha(destination)}  {destination.name}\n')
        print('Built Linux candidate (live qualification pending): ' + str(destination), flush=True)


def prepare_kit(common_archive, output, architecture='x64'):
    """Prepare a transferable native-build kit without claiming a Linux binary."""
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='verify-common-', dir=output) as temporary:
        verify_common(unpack_common(common_archive, Path(temporary)))
    kit = output / ('RCPM-linux-' + architecture + '-build-kit')
    kit.mkdir()
    shutil.copy2(common_archive, kit / 'rcpm-common-candidate.zip')
    for source in ('build_linux_release.py', 'build_raw_cpmtools.py', 'build_modem_runtime.py',
                   'backup_rcpm.py', 'shared_instance.py', 'release_media.py',
                   'check_release.py', 'packaging/launcher.c'):
        target = kit / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / source, target)
    for folder in ('emulator', 'patches'):
        shutil.copytree(REPO / folder, kit / folder)
    runner = kit / 'Build-and-Check.sh'
    runner.write_text('''#!/bin/bash
set -euo pipefail
cd -P "$(dirname "$0")"
case "$(uname -m)" in
  aarch64|arm64) target=arm64 ;;
  x86_64|amd64) target=x64 ;;
  *) echo "Unsupported Linux architecture" >&2; exit 1 ;;
esac
mkdir -p "$HOME/rcpm-release-builds"
run_root="$(mktemp -d "$HOME/rcpm-release-builds/run.XXXXXX")"
echo "Build and qualification results: $run_root"
python3 build_linux_release.py --common rcpm-common-candidate.zip --output "$run_root/package" 2>&1 | tee "$run_root/build.log"
set -- python3 check_release.py "$run_root/package/rcpm-linux-$target-candidate.tar.gz" --output "$run_root/check"
if [ -n "${RCPM_TCPSER:-}" ]; then
  set -- "$@" --tcpser "$RCPM_TCPSER"
fi
"$@" 2>&1 | tee "$run_root/check.log"
echo "PASS: $run_root/check/result.json"
echo "Native package: $run_root/package/rcpm-linux-$target-candidate.tar.gz"
''')
    runner.chmod(0o755)
    (kit / 'README.txt').write_text(
        'RCP/M Linux ' + architecture + ' native build kit\n\n'
        'Run on Linux ' + architecture + ' with Python 3.9+, cc, make, binutils/readelf and ldd.\n'
        'All source inputs for the host build are included; no downloads occur.\n'
        'Microsoft/MicroPro guest development tools are not needed for this build.\n\n'
        'For one build and direct-TCP qualification pass, run:\n'
        '  bash ./Build-and-Check.sh\n'
        'It creates a fresh directory under ~/rcpm-release-builds and prints\n'
        'the native package and report paths. To include optional modem checks,\n'
        'set RCPM_TCPSER to an existing compatible tcpser executable path.\n\n'
        'Build native host files around the supplied common payload:\n'
        '  python3 build_linux_release.py --common rcpm-common-candidate.zip --output build/linux\n'
        'Qualify the extracted Linux package:\n'
        '  python3 check_release.py build/linux/rcpm-linux-' + architecture + '-candidate.tar.gz --output build/check\n'
        'For optional real-modem checks, append --tcpser /path/to/tcpser.\n'
        'Both commands require fresh output directories.\n\n'
        'The built runtime archive needs no Python, compiler, tmux or installed\n'
        'CP/M tools. Run its Start-RCPM.sh in a terminal after unpacking.\n'
        'Actual Linux build/live qualification is pending until these commands\n'
        'run on the target host. Public redistribution remains unresolved.\n')
    hashes = {str(path.relative_to(kit)): sha(path) for path in kit.rglob('*') if path.is_file()}
    (kit / 'KIT-MANIFEST.json').write_text(json.dumps(hashes, indent=2) + '\n')
    destination = output / ('rcpm-linux-' + architecture + '-build-kit.tar.gz')
    with tarfile.open(destination, 'w:gz') as archive:
        archive.add(kit, arcname=kit.name)
    (output / 'SHA256SUMS').write_text(f'{sha(destination)}  {destination.name}\n')
    print('Prepared Linux ' + architecture + ' build kit: ' + str(destination), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--common', type=Path, required=True, help='Verified rcpm-common-candidate.zip')
    parser.add_argument('--output', type=Path, required=True, help='New output directory')
    parser.add_argument('--prepare-kit', action='store_true',
                        help='Prepare a transferable build kit on the current host')
    parser.add_argument('--kit-architecture', choices=('x64', 'arm64'), default='x64')
    args = parser.parse_args()
    try:
        if args.prepare_kit:
            prepare_kit(args.common.expanduser().resolve(), args.output.expanduser().resolve(), args.kit_architecture)
        else:
            build(args.common.expanduser().resolve(), args.output.expanduser().resolve())
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
