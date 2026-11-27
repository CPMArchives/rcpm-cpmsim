#!/usr/bin/env python3
"""Refresh a verified platform package with the foreground bundled modem launcher."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

import os
if os.name == 'nt':
    from check_windows_release import unpack as extract_package
else:
    from check_release import extract_package

REPO = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def build(base, platform, launcher, tcpser, tcpser_source, output, extras=None):
    output.mkdir(parents=True, exist_ok=False)
    root = extract_package(base, output / 'expanded')
    manifest = json.loads((root / 'metadata/MANIFEST.json').read_text())
    if manifest['platform'] != platform:
        raise ValueError('Wrong base platform')
    original = {**manifest['common'], **manifest['host']}
    actual = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()}
    if actual != {**original, 'metadata/MANIFEST.json': sha(root / 'metadata/MANIFEST.json')}:
        raise ValueError('Base manifest mismatch')
    if (root / 'service').exists():
        raise ValueError('Use a standard base package, not a hosting kit')
    suffix = '.exe' if platform.startswith('windows-') else ''
    shutil.copy2(launcher, root / ('runtime/rcpm' + suffix))
    shutil.copy2(tcpser, root / ('runtime/tcpser' + suffix))
    for name in ('INSTALLATION.DOC', 'SYSOP-GUIDE.DOC'):
        shutil.copy2(REPO / 'packaging' / name, root / 'docs' / name)
    shutil.copy2(REPO / 'packaging/RCPM.CONF', root / 'RCPM.CONF')
    source = root / 'source/tcpser'
    if source.exists():
        shutil.rmtree(source)
    shutil.copytree(tcpser_source, source, ignore=shutil.ignore_patterns('*.o', 'tcpser', '*.exe', '*.pyc', '__pycache__'))
    shutil.copy2(REPO / 'packaging/native/TCPSER-COPYING', source / 'COPYING')
    for name, path in (extras or {}).items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    for name in ('packaging/launcher.c', 'packaging/modem_host.h', 'packaging/RCPM.CONF',
                 'windows/launcher_host.h', 'windows/modem_host.h', 'windows/build_support.py',
                 'assemble_release_1_2_2.py', 'prepare_release_1_2_2.py'):
        target = root / 'source/release-1.2.2' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, target)
    launcher_name = {'macos-arm64': 'Start-RCPM.command', 'linux-arm64': 'Start-RCPM.sh',
                     'linux-x64': 'Start-RCPM.sh', 'windows-x64': 'Start-RCPM.cmd',
                     'windows-arm64': 'Start-RCPM.cmd'}[platform]
    readme = ('RCP/M 1.2.2 — ' + platform + '\n\nUnpack into a writable directory and run ' + launcher_name + '.\n'
              'No initial configuration is required. The terminal is the local sysop console.\n'
              'Defaults: direct TCP, 127.0.0.1, caller port 4000.\n'
              'Optional: edit the commented RCPM.CONF while stopped; MODE=ip232 uses bundled tcpser.\n'
              'The launcher starts/stops the modem. Internal connection settings are automatic.\n'
              'First start creates private credentials in SYSOP.DOC.\n'
              'See docs/INSTALLATION.DOC and docs/SYSOP-GUIDE.DOC.\n'
              'Host administration tools are a separate optional add-on.\n')
    (root / 'README.txt').write_text(readme)
    for name in ('LINUX-README.txt', 'WINDOWS-README.txt'):
        if (root / name).exists():
            (root / name).write_text(readme)
    retained = {n: h for n, h in original.items() if n.startswith(('disks/', 'drivers/'))}
    assert all(sha(root / n) == h for n, h in retained.items())
    receipt = dict(version='v1.2.2', platform=platform, published=False,
                   base_archive_sha256=sha(base), launcher_sha256=sha(launcher),
                   tcpser_sha256=sha(tcpser), unchanged_media_driver_files=len(retained),
                   runtime_qualification='Record separately; this builder makes no test claim')
    (root / 'metadata/PACKAGE.json').write_text(json.dumps(receipt, indent=2) + '\n')
    all_files = {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
                 if p.is_file() and p != root / 'metadata/MANIFEST.json'}
    common = {n: h for n, h in manifest['common'].items() if all_files.get(n) == h}
    manifest.update(version='v1.2.2', status='built-runtime-qualification-pending', common=common,
                    host={n: h for n, h in all_files.items() if n not in common})
    (root / 'metadata/MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    target = output / ('rcpm-v1.2.2-' + platform + ('.zip' if suffix or platform.startswith('macos-') else '.tar.gz'))
    if target.suffix == '.zip':
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
            for p in sorted(root.rglob('*')):
                archive.write(p, p.relative_to(root.parent))
    else:
        with tarfile.open(target, 'w:gz') as archive:
            archive.add(root, arcname=root.name)
    (output / 'SHA256SUMS').write_text(sha(target) + '  ' + target.name + '\n')
    return root, target


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'launcher', 'tcpser', 'tcpser-source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--platform', required=True)
    a = p.parse_args()
    print(build(a.base.resolve(), a.platform, a.launcher.resolve(), a.tcpser.resolve(),
                a.tcpser_source.resolve(), a.output.resolve())[1])
