#!/usr/bin/env python3
"""Split a verified Linux service kit into independent base and hosting downloads."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from check_release import extract_package

REPO = Path(__file__).resolve().parent
HOST_SCRIPTS = {
    'build_native_service_kit.py', 'rebuild_native_service_candidate.py',
    'check_native_service.py', 'check_debian_vm.py', 'check_debian_security.py',
    'check_debian_monitor.py', 'check_release_acceptance.py', 'run_release_soak.py',
    'test_native_service.py', 'test_native_monitor.py',
    'build_hosting_addon.py', 'install_hosting_addon.py',
}
HOST_DOCS = {
    'native-service.md', 'operational-monitoring.md', 'INSTALLATION-NATIVE-SERVICE.md',
    'RELEASE-NOTES-1.2.2.md', 'RELEASE-NOTES-1.2.2-rc1.md',
    'stable-release-acceptance.md', 'debian-caller-regression.md',
    'native-service-candidate-rc2.md', 'debian-vm-validation.md',
    'x64-debian-vm-validation.md',
    'hosting-addon.md',
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n')


def files(root):
    result = {}
    for p in sorted(root.rglob('*')):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError('Unexpected package entry: ' + str(p))
        if p.is_file():
            result[p.relative_to(root).as_posix()] = sha(p)
    return result


def hosting_file(name):
    parts = Path(name).parts
    return (parts[0] == 'service' or 'packaging/native' in name
            or parts[-1] in HOST_SCRIPTS | HOST_DOCS
            or parts[-1] in {'Install-Service.sh', 'INSTALL-SERVICE.txt'}
            or (parts[0] == 'metadata' and parts[-1].startswith('SERVICE-')))


def split(root, output, version='v1.2.2'):
    original = json.loads((root / 'metadata/MANIFEST.json').read_text())
    expected = {**original['common'], **original['host']}
    if files(root) != {**expected, 'metadata/MANIFEST.json': sha(root / 'metadata/MANIFEST.json')}:
        raise ValueError('Input package manifest mismatch')
    platform = original['platform']
    if platform not in ('linux-arm64', 'linux-x64'):
        raise ValueError('Hosting add-on currently supports Linux ARM64 and x64 only')
    output.mkdir(parents=True, exist_ok=False)
    expanded = output / 'expanded'
    base = expanded / ('RCPM-' + platform)
    addon = expanded / ('RCPM-hosting-' + platform)
    base.mkdir(parents=True); addon.mkdir()
    for name in expected:
        # Service receipts describe the old combined kit; retain only in add-on source history.
        dest = addon / ('source/combined-kit/' + name) if hosting_file(name) else base / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / name, dest)
    # Install current hosting sources, never place them in the base package.
    shutil.copytree(REPO / 'packaging/native', addon / 'service',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(REPO / 'packaging/install_hosting_addon.py', addon / 'Install-Hosting.py')
    for name in ('build_hosting_addon.py', 'build_native_service_kit.py',
                 'packaging/install_hosting_addon.py'):
        dest = addon / 'source/current' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, dest)
    (addon / 'Install-Hosting.sh').write_text(
        '#!/bin/sh\nset -eu\nexec python3 "$(dirname "$0")/Install-Hosting.py" "$@"\n')
    (addon / 'Install-Hosting.sh').chmod(0o755)
    for name in ('INSTALLATION-NATIVE-SERVICE.md', 'operational-monitoring.md', 'native-service.md'):
        shutil.copy2(REPO / 'docs' / name, addon / name)
    shutil.copy2(REPO / 'docs/hosting-addon.md', addon / 'README.md')
    shutil.copy2(REPO / 'docs/hosting-addon.md', addon / 'hosting-addon.md')
    (base / 'docs').mkdir(exist_ok=True)
    shutil.copy2(REPO / 'packaging/SYSOP-GUIDE.DOC', base / 'docs/SYSOP-GUIDE.DOC')
    # Update the corresponding source copy too, where present.
    for p in base.glob('source/*/packaging/SYSOP-GUIDE.DOC'):
        shutil.copy2(REPO / 'packaging/SYSOP-GUIDE.DOC', p)
    identity = {name: digest for name, digest in expected.items()
                if name.startswith(('runtime/', 'disks/', 'drivers/'))}
    assert identity and all(sha(base / name) == digest for name, digest in identity.items())
    write_json(base / 'metadata/PACKAGE.json', dict(
        version=version, kind='standard', platform=platform,
        workflow='Unpack and run Start-RCPM.sh; no hosting add-on required',
        hosting_addon_required=False))
    contents = files(base)
    contents.pop('metadata/MANIFEST.json', None)
    # Changed manuals are host overlays; preserve only unchanged common identities.
    common = {name: digest for name, digest in original['common'].items()
              if contents.get(name) == digest}
    write_json(base / 'metadata/MANIFEST.json', dict(
        platform=platform, status='standard-package', version=version,
        common=common, host={n: h for n, h in contents.items() if n not in common}))
    write_json(addon / 'metadata/ADDON.json', dict(
        version=version, kind='optional-hosting-addon', platform=platform,
        requires='Matching freshly unpacked standard package; existing boards are not migrated',
        base_runtime_media_sha256=identity, files=files(addon)))
    archives = []
    for directory, suffix in ((base, platform), (addon, platform + '-hosting-addon')):
        target = output / ('rcpm-' + version + '-' + suffix + '.tar.gz')
        with tarfile.open(target, 'w:gz') as archive:
            archive.add(directory, arcname=directory.name)
        archives.append(dict(name=target.name, sha256=sha(target), bytes=target.stat().st_size))
    (output / 'SHA256SUMS').write_text(''.join(a['sha256'] + '  ' + a['name'] + '\n' for a in archives))
    write_json(output / 'PACKAGE-SPLIT.json', dict(
        platform=platform, version=version, artifacts=archives,
        unchanged_runtime_media_driver_files=len(identity),
        base_contains_hosting_files=any(hosting_file(n) for n in files(base)),
        published=False))
    return base, addon


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--version', default='v1.2.2')
    args = p.parse_args()
    if '/' in args.version or '\\' in args.version or args.version in ('.', '..'):
        raise ValueError('Invalid version')
    with tempfile.TemporaryDirectory(prefix='rcpm-package-split-') as temp:
        root = extract_package(args.kit.resolve(), Path(temp))
        split(root, args.output.resolve(), args.version)
    print(args.output)


if __name__ == '__main__':
    main()
