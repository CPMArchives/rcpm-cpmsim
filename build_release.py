#!/usr/bin/env python3
"""Build the common payload and relocatable macOS ARM64 engineering candidate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

from backup_rcpm import copy_file
from build_j_volumes import build as build_volumes
from prepare_shared_trial import create
from prepare_rbbs_trial import install, references
from prepare_system_trial import upper_layout
from game_launchers import build as build_game_launchers
from release_media import separate_development_tools, verify_public_development_media

REPO = Path(__file__).resolve().parent
NATIVE = ('rcpm', 'cpmsim', 'cpmcp', 'cpmls', 'cpmrm', 'cpmchattr', 'mkfs.cpm')


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else digest_stream(stream)


def digest_stream(stream):
    digest = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        digest.update(block)
    return digest.hexdigest()


def tool(tools, name, *args):
    return subprocess.run([str(tools / name), *map(str, args)], check=True, capture_output=True).stdout


def put(tools, image, user, name, data, fmt='ibm-3740'):
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / 'file'
        path.write_bytes(data)
        tool(tools, 'cpmrm', '-f', fmt, image, f'{user}:{name}')
        tool(tools, 'cpmcp', '-f', fmt, image, path, f'{user}:{name}')


def verify_archive(image, manifest, tools):
    expected = {f'P{user}:SIGMV{n:03}.LBR' for user in (0,) for n in range(1, 311)}
    expected.update(f'P1:CPMUG{n:03}.LBR' for n in range(1, 94))
    rows = [line.split() for line in manifest.read_text().splitlines() if line.strip()]
    if len(rows) != 403 or {entry for _, entry in rows} != expected:
        raise ValueError('Expected 310 SIGM and 93 CPMUG volumes')
    with tempfile.TemporaryDirectory() as temporary:
        result = Path(temporary) / 'readback.bin'
        for digest, entry in rows:
            user, name = entry[1:].split(':')
            tool(tools, 'cpmcp', '-f', 'z80pack-hdb', image, user + ':' + name, result)
            if sha(result) != digest:
                raise ValueError('P: archive checksum mismatch: ' + entry)
            result.unlink()
    return rows


def clean_common(args, output):
    if not json.loads((args.builds / 'build-result.json').read_text()).get('du_authorization'):
        raise ValueError('Rebuild BYE with unified AUTH policy first')
    references(REPO / 'build/rbbs37/original')
    create(args.source, args.romwbw, args.runtime, args.builds, args.tools, output)
    install(output, REPO / 'build/rbbs37/original', args.tools, args.romwbw, output)
    upper_layout(output, args.tools, args.romwbw, REPO / 'build/ppip18')
    separate_development_tools(args.source, args.tools, output)
    # Never use operator media. Remove development helpers and generated secrets.
    for path in output.glob('*.command'):
        path.unlink()
    for name in ('runtime/cpmsim', 'runtime/cpmsim.features.json', 'rbbs-trial-passwords.json', 'trial-build.json', 'README.txt'):
        (output / name).unlink(missing_ok=True)
    (output / 'disks/drivej.dsk').unlink()
    shutil.rmtree(output / 'volumes')
    print('Verifying every P: library against the preserved archive manifest...', flush=True)
    archive_rows = verify_archive(args.archive, args.archive.with_suffix('.sha256'), args.tools)
    target = output / 'disks/drivep.dsk'
    target.unlink()
    copy_file(args.archive, target, 0o600)
    if sha(target) != sha(args.archive):
        raise ValueError('P: image copy verification failed')
    shutil.copy2(args.archive.with_suffix('.sha256'), output / 'ARCHIVE.sha256')
    launchers = output / 'source/configured/game-launchers'
    build_game_launchers(args.source, args.romwbw, launchers)
    for name in ('ADVENT', 'ANIMALS', 'MCHASE'):
        put(args.tools, output / 'disks/drivea.dsk', 0, name + '.COM',
            (launchers / (name + '.COM')).read_bytes())
        tool(args.tools, 'cpmchattr', '-f', 'ibm-3740', output / 'disks/drivea.dsk',
             'r4', '0:' + name + '.COM')
    rows = build_volumes(args.sigm, args.tools, output / 'volumes', launchers / 'mchansi.bin')
    from auth_policy import install as install_auth
    install_auth(output, args.tools, args.source / 'z80asm/z80asm')
    (output / 'VOLUMES.json').write_text(json.dumps(rows, indent=2) + '\n')
    (output / 'volumes/volumes.json').unlink()
    for name in ('direct', 'ip232'):
        destination = output / 'drivers' / name
        destination.mkdir(parents=True)
        shutil.copy2(args.builds / name / 'BYEDRIV.COM', destination / 'BYEDRIV.COM')
    if (args.builds / 'direct/BYE.COM').read_bytes() != (args.builds / 'ip232/BYE.COM').read_bytes():
        raise ValueError('Expected one common BYE.COM loader')
    a = output / 'disks/drivea.dsk'
    for name, value in {
        'BOOTPWD': 'I:,I:,LOCAL,SYSOP,RCPM RBBS,N,N',
        'INFO': 'RCP/M bulletin board on CP/M 3, Z3PLUS and BYE510.',
        'BULLETIN': 'Welcome to the RCP/M bulletin board.',
        'NEWCOM': 'Welcome. New members require sysop verification before posting.',
    }.items():
        put(args.tools, a, 15, name, (value + '\r\n\x1a').encode('ascii'))
    # The canonical seed is not an installed board password. Native first-start
    # initialization replaces it with fresh local secrets before cpmsim boots.
    i = output / 'disks/drivei.dsk'
    with i.open('r+b') as stream:
        directory = stream.read(32768)
        entries = [directory[n:n+32] for n in range(0, len(directory), 32)
                   if directory[n:n+12] == b'\x0fpwds       ']
        if len(entries) != 1:
            raise ValueError('Missing fresh RBBS pwds entry')
        block = int.from_bytes(entries[0][16:18], 'little')
        stream.seek(block * 2048)
        seed = b'UNINITIALIZED,UNINITIALIZED,NOPASS,CPM,UNINITIALIZED,N\r\n10,24,1,0,0,1,1,0\r\n\x1a'
        stream.write(seed.ljust(128, b'\x1a'))
    (output / 'state').mkdir(mode=0o700)
    for name in ('INSTALLATION.DOC', 'SYSOP-GUIDE.DOC', 'DISK-IMAGES.DOC'):
        shutil.copy2(REPO / 'packaging' / name, output / name)
    (output / 'RCPM.CONF').write_text('MODE=direct\nADDRESS=127.0.0.1\nPORT=4000\n')
    shutil.copy2(REPO / 'build/cpmtools/share/diskdefs', output / 'runtime/diskdefs')
    (output / 'README.txt').write_text(
        'RCP/M engineering candidate\n\n'
        'Unpack and run your platform launcher (Start-RCPM.command on macOS).\n'
        'No tmux or Python is required to run the package.\n'
        'Direct raw TCP is the default: 127.0.0.1 port 4000.\n'
        'A:, I: and populated P: are included. J: is created on first start.\n'
        'MOUNT GAMES or MOUNT GUIDES selects the supplied J: volumes.\n'
        'Fresh RBBS passwords are generated locally in private SYSOP.DOC.\n'
        'See INSTALLATION.DOC for setup and SYSOP-GUIDE.DOC for administration.\n'
        'DISK-IMAGES.DOC covers image formats; see also DISTRIBUTION-STATUS.DOC.\n')
    return dict(sigm=310, cpmug=93, verified_libraries=len(archive_rows),
                archive_sha256=sha(target), j_volumes=['GAMES', 'GUIDES'])


def source_ignore(directory, names):
    ignored = set()
    for name in names:
        path = Path(directory) / name
        if name in ('.git', '__pycache__', 'autom4te.cache', 'config.log', 'config.status') or path.suffix in ('.o', '.d', '.a', '.pyc'):
            ignored.add(name)
        elif path.is_file():
            with path.open('rb') as stream:
                magic = stream.read(4)
            if magic in (b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf', b'\x7fELF'):
                ignored.add(name)
    return ignored


def sources_and_notices(args, output):
    sources = output / 'source'
    project = sources / 'rcpm'
    project.mkdir(parents=True)
    for path in REPO.iterdir():
        if path.is_file() and (path.suffix in ('.py', '.md', '.zsh', '.json', '.command')
                               or path.name == '.gitignore'):
            shutil.copy2(path, project / path.name)
    for name in ('guest', 'emulator', 'packaging', 'patches', 'docs', 'host', 'repro'):
        shutil.copytree(REPO / name, project / name)
    upstream = sources / 'upstream'
    for relative in ('cpmsim/srcsim', 'z80core', 'iodevices', 'z80asm'):
        shutil.copytree(args.source / relative, upstream / 'z80pack' / relative, ignore=source_ignore)
    for relative in ('LICENSE', 'README.md', 'HISTORY'):
        shutil.copy2(args.source / relative, upstream / 'z80pack' / relative)
    stock = upstream / 'z80pack/cpmsim/disks/library'
    stock.mkdir(parents=True)
    shutil.copy2(args.source / 'cpmsim/disks/library/cpm3-1.dsk', stock / 'cpm3-1.dsk')
    (stock / 'BUILD-INPUTS.DOC').write_text(
        'The original cpm3-2.dsk is a separately supplied build input.\n'
        'It contains Microsoft M80/L80 and MicroPro WM and is not bundled here.\n'
        'Its required SHA256 and relative path are in rcpm/docs/release-baseline.json.\n'
        'See source/BUILDING.DOC for assembling the complete build-input tree.\n')
    shutil.copytree(args.cpmtools_source, upstream / 'cpmtools-2.23', ignore=source_ignore)
    shutil.copytree(args.bye_reference, upstream / 'bye510', ignore=source_ignore)
    shutil.copytree(REPO / 'build/rbbs37/original/rbbs37-2', upstream / 'rbbs37-source')
    shutil.copytree(REPO / 'build/ztools', upstream / 'utility-references')
    configured = sources / 'configured'
    configured.mkdir(exist_ok=True)
    shutil.copytree(args.builds / 'sources', configured / 'bye5')
    for name in ('ppip18', 'caller-tools', 'sysop-editor'):
        directory = configured / name
        directory.mkdir()
        for path in (REPO / 'build' / name).iterdir():
            if path.is_file() and path.suffix.lower() not in ('.log',):
                shutil.copy2(path, directory / path.name)
    notices = output / 'NOTICES'
    notices.mkdir()
    for original, name in ((args.source / 'LICENSE', 'z80pack-LICENSE.txt'),
                           (args.source / 'z80core/COPYING', 'z80core-COPYING.txt'),
                           (args.cpmtools_source / 'COPYING', 'cpmtools-COPYING.txt'),
                           (args.romwbw / 'LICENSE', 'RomWBW-LICENSE.txt'),
                           (args.romwbw / 'LEGAL.md', 'RomWBW-LEGAL.md'),
                           (args.romwbw / 'Source/Images/d_z3plus/u0/!(C)1988', 'Z3PLUS-original.txt'),
                           (args.bye_reference / 'bye510.asm', 'BYE510-original.asm')):
        shutil.copy2(original, notices / name)
    (output / 'DISTRIBUTION-STATUS.DOC').write_text(
        'ENGINEERING CANDIDATE - NOT CLEARED FOR PUBLIC REDISTRIBUTION\n\n'
        'This local artifact tests packaging and operation. No release was published.\n'
        'Original notices remain in NOTICES/, source/ and preserved library members.\n\n'
        'Specific unresolved notices:\n'
        '- Z3PLUS original notice explicitly prohibits reproduction/distribution.\n'
        '- BYE510 original notice permits distribution unmodified; this driver is patched.\n'
        '- PPIP, ZDE, HELPC and ZLT retain their individual noncommercial/other terms.\n'
        '- SIGM/CPMUG collections contain independently authored software; their\n'
        '  individual notices are retained, not replaced with a collection-wide grant.\n'
        '  Inclusion in a historical archive or another repository is not clearance.\n'
        '- Further source availability/rights checks for guest components remain.\n\n'
        'Do not describe the aggregate as uniformly open source or public domain.\n'
        'A documented later grant/permission or replacement is needed to resolve\n'
        'conflicting restrictive notices before public distribution.\n')
    (sources / 'BUILDING.DOC').write_text(
        'RCP/M CANDIDATE BUILD SOURCES\n\n'
        'For the pinned full build recipe, see rcpm/docs/source-baseline.md and\n'
        'rcpm/rebuild_release.py. Supply the exact inputs in release-baseline.json.\n'
        'The matching cpmsim host source snapshot is upstream/z80pack.\n'
        'For macOS ARM64 builds set MACOSX_DEPLOYMENT_TARGET=11.0 in the build environment.\n'
        'Our emulator integration sources and patches are in rcpm/emulator and\n'
        'rcpm/patches. From source/rcpm with Python 3 and a C compiler:\n'
        '  python3 build_modem_runtime.py ../upstream/z80pack build/release-runtime/cpmsim\n'
        '  cc -mmacosx-version-min=11.0 -std=c99 -O2 -Wall -Wextra -Werror packaging/launcher.c -o rcpm-launcher\n'
        '  python3 build_raw_cpmtools.py ../upstream/cpmtools-2.23\n'
        'The cpmtools builder applies the documented POSIX raw-image option fix.\n'
        'BYE configured assembly is in configured/bye5; pristine upstream and RBBS\n'
        'BASIC sources are under upstream/. offline/BUILD.dsk retains the DRI\n'
        'development files; Microsoft M80/L80 and MicroPro WM are excluded.\n'
        'Builders supply the pinned original cpm3-2.dsk outside this package,\n'
        'combining it with the source snapshot in their separate input tree.\n'
        'Utility sources and hashes are included. DEVELOPMENT-MEDIA.json records\n'
        'the separation and hashes of every retained development file.\n'
        'Reference downloads and their exact hashes are listed in rcpm/docs/*.json.\n'
        'Full fresh system generation uses prepare_system_trial.py; consult its\n'
        '--help and docs/zsystem-utilities.md for source/toolchain inputs.\n'
        'RomWBW image inputs come from commit cb887a1a2191072dff952bfa836a8dca201b1450.\n'
        'The P: image is verified using ARCHIVE.sha256; the original volume bytes\n'
        'are preserved inside P:. build_archive.py can rebuild it from the collections.\n'
        'The release builder separates the common payload from native host files.\n'
        'No developer checkout path is used by the running package.\n')


def archive(folder, destination):
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as result:
        result.write(folder, folder.name + '/')
        for path in sorted(folder.rglob('*')):
            result.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'romwbw', 'bye-reference', 'cpmtools-source', 'archive', 'sigm', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--builds', type=Path, required=True,
                   help='Explicit reviewed BYE output directory; no implicit historical build')
    p.add_argument('--runtime', type=Path, default=REPO / 'build/release-runtime/cpmsim')
    p.add_argument('--tools', type=Path, default=REPO / 'build/release-tools/bin')
    args = p.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.expanduser().resolve())
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        p.error('This initial host package must be built on macOS ARM64')
    if args.output.exists():
        p.error('Refusing to overwrite a release build')
    args.output.mkdir(parents=True)
    common = args.output / 'rcpm-common'
    collections = clean_common(args, common)
    sources_and_notices(args, common)
    verify_public_development_media(common, args.tools)
    common_files = {str(path.relative_to(common)): sha(path) for path in sorted(common.rglob('*')) if path.is_file()}
    payload = args.output / 'RCPM-macOS-arm64'
    shutil.copytree(common, payload, copy_function=lambda source, target: copy_file(Path(source), Path(target), Path(source).stat().st_mode & 0o777) and target)
    (payload / 'Start-RCPM.command').write_text('#!/bin/sh\nset -eu\ncd -P "$(dirname "$0")"\nexec ./runtime/rcpm "$@"\n')
    (payload / 'Start-RCPM.command').chmod(0o755)
    runtime = payload / 'runtime'
    shutil.copy2(args.runtime, runtime / 'cpmsim')
    features = args.runtime.with_name(args.runtime.name + '.features.json')
    if features.exists():
        shutil.copy2(features, runtime / 'cpmsim.features.json')
    for name in ('cpmcp', 'cpmls', 'cpmrm', 'cpmchattr', 'mkfs.cpm'):
        shutil.copy2(args.tools / name, runtime / name)
    subprocess.run(['cc', '-mmacosx-version-min=11.0', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                    str(REPO / 'packaging/launcher.c'), '-o', str(runtime / 'rcpm')], check=True)
    native = {str(path.relative_to(payload)): sha(path) for path in [runtime / name for name in NATIVE]}
    native['Start-RCPM.command'] = sha(payload / 'Start-RCPM.command')
    if (runtime / 'cpmsim.features.json').exists():
        native['runtime/cpmsim.features.json'] = sha(runtime / 'cpmsim.features.json')
    for name in NATIVE:
        result = subprocess.check_output(['otool', '-L', str(runtime / name)], text=True)
        for line in result.splitlines()[1:]:
            dependency = line.strip().split(' (', 1)[0]
            if not dependency.startswith(('/usr/lib/', '/System/Library/')):
                raise ValueError('Non-system native dependency: ' + dependency)
    manifest = dict(format='rcpm-release-candidate-1', platform='macos-arm64',
                    status='local-engineering-candidate-redistribution-not-cleared', minimum_macos='11.0',
                    collections=collections, common=common_files, host=native)
    (payload / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (common / 'COMMON-MANIFEST.json').write_text(json.dumps(common_files, indent=2) + '\n')
    archive(common, args.output / 'rcpm-common-candidate.zip')
    archive(payload, args.output / 'rcpm-macos-arm64-candidate.zip')
    (args.output / 'SHA256SUMS').write_text(''.join(f'{sha(path)}  {path.name}\n' for path in sorted(args.output.glob('*.zip'))))
    print('Built:', args.output / 'rcpm-macos-arm64-candidate.zip')
    print('Common payload:', args.output / 'rcpm-common-candidate.zip')


if __name__ == '__main__':
    main()
