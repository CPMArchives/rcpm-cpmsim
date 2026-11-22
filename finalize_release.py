#!/usr/bin/env python3
"""Assemble reviewable 1.0 assets without rebuilding qualified runtime bytes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(folder):
    return {p.relative_to(folder).as_posix(): sha(p)
            for p in sorted(folder.rglob('*')) if p.is_file()}


def verify(folder, manifest):
    expected = dict(manifest['common'], **manifest.get('host', {}))
    for name, digest in expected.items():
        if sha(folder / name) != digest:
            raise ValueError('Candidate changed: ' + name)


def copy_tree(source, target):
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def refresh_source(target):
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in ('.py', '.md', '.zsh', '.json', '.command'):
            shutil.copy2(path, target / path.name)
    for name in ('guest', 'emulator', 'packaging', 'patches', 'docs', 'host', 'repro', 'windows'):
        if (target / name).exists():
            shutil.rmtree(target / name)
        copy_tree(ROOT / name, target / name)


def archive(folder, target):
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as stream:
        stream.write(folder, folder.name + '/')
        for path in sorted(folder.rglob('*')):
            stream.write(path, (Path(folder.name) / path.relative_to(folder)).as_posix())


def build(output):
    bases = {
        'macos-arm64': ROOT / 'build/release-runtime-separated/RCPM-macOS-arm64',
        'windows-x64': ROOT / 'build/windows-x64-final-candidate/RCPM-windows-x64',
    }
    manifests = {key: json.loads((folder / 'metadata/MANIFEST.json').read_text())
                 for key, folder in bases.items()}
    for key, folder in bases.items():
        verify(folder, manifests[key])
    if manifests['macos-arm64']['common'] != manifests['windows-x64']['common']:
        raise ValueError('Tested candidates do not share the same common payload')
    output.mkdir(parents=True, exist_ok=False)
    common = output / 'rcpm-common'
    copy_tree(ROOT / 'build/release-runtime-separated/rcpm-common', common)
    (common / 'COMMON-MANIFEST.json').unlink()
    refresh_source(common / 'source/rcpm')
    shutil.copy2(ROOT / 'docs/RELEASE-NOTES-1.0.md', common / 'docs/RELEASE-NOTES.md')
    shutil.copy2(ROOT / 'docs/distribution-review.md', common / 'docs/NOTICES/RELEASE-DECISIONS.md')
    (common / 'docs/DISTRIBUTION-STATUS.DOC').write_text(
        'RCP/M 1.0 - PREPARED FOR PUBLICATION REVIEW\n\n'
        'Component-specific terms apply; no uniform license is asserted.\n'
        'Original notices and corresponding source remain in this package.\n'
        'The maintainer retains Z3PLUS on later release evidence, retains\n'
        'configured ZDE with its original archive, and accepts proceeding with\n'
        'the modified BYE510. This is not a new grant from BYE/ZDE authors.\n'
        'SIG/M and CPMUG collection authorization is the accepted release basis.\n'
        'Preserve all component-specific noncommercial/no-fee conditions.\n'
        'See docs/NOTICES/RELEASE-DECISIONS.md for evidence and uncertainty.\n'
        'No blanket license has been selected for original project code.\n'
        'Source availability alone does not assert an open-source license.\n')
    common_files = inventory(common)
    frozen = {}
    for key, base in bases.items():
        payload = output / base.name
        copy_tree(base, payload)
        for name in manifests[key]['common']:
            (payload / name).unlink()
        for name in common_files:
            destination = payload / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(common / name, destination)
        if key == 'windows-x64':
            shutil.copy2(ROOT / 'check_windows_release.py', payload / 'qualification/check_windows_release.py')
            refresh_source(payload / 'source/host-windows')
            (payload / 'WINDOWS-README.txt').write_text(
                'RCP/M 1.0 Windows x64\n\n'
                'Extract the entire ZIP into a writable local NTFS folder.\n'
                'Double-click Start-RCPM.cmd; wait for RCP/M modem ready.\n'
                'Raw TCP callers connect to 127.0.0.1:4000 by default.\n'
                'No Python, WSL, Cygwin or compiler is needed to run RCP/M.\n'
                'Required suite PASS: Windows 11 ARM64 build 26300, with x64\n'
                'executables under Windows emulation. Native x64 hardware and\n'
                'optional Windows IP232 were not tested. See docs/RELEASE-NOTES.md.\n'
                'Use the local SYSUTLS:BYEBYE procedure for orderly shutdown.\n'
                'Generated SYSOP.DOC contains private credentials; do not share it.\n')
            metadata = json.loads((payload / 'metadata/BUILD-HOST.json').read_text())
            metadata.update(status='required-suite-passed-windows11-arm64-x64-emulation',
                            live_qualification='docs/performance/windows-runtime-2026-11-21.json',
                            redistribution='maintainer-decisions-and-component-terms-retained')
            (payload / 'metadata/BUILD-HOST.json').write_text(json.dumps(metadata, indent=2) + '\n')
        host_files = {name: digest for name, digest in inventory(payload).items()
                      if name not in common_files and name != 'metadata/MANIFEST.json'}
        manifest = dict(manifests[key], version='1.0',
                        status='prepared-for-publication-review', common=common_files, host=host_files)
        manifest.pop('common_archive_sha256', None)
        (payload / 'metadata/MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        for name, digest in manifests[key]['common'].items():
            if name.startswith(('disks/', 'drivers/', 'disks/library/', 'disks/library/offline/')):
                if sha(payload / name) != digest:
                    raise ValueError('Frozen guest media changed: ' + name)
        frozen[key] = {}
        for name, digest in {**manifests[key]['common'], **manifests[key]['host']}.items():
            if name.startswith('runtime/') or name.startswith('Start-RCPM') or name.endswith('.exe'):
                if sha(payload / name) != digest:
                    raise ValueError('Frozen host runtime changed: ' + name)
                frozen[key][name] = digest
        verify(payload, manifest)
        if set(inventory(payload)) != set(common_files) | set(host_files) | {'metadata/MANIFEST.json'}:
            raise ValueError('Unrecorded release files')
        archive(payload, output / ('rcpm-v1.0-' + key + '.zip'))
    (common / 'COMMON-MANIFEST.json').write_text(json.dumps(common_files, indent=2) + '\n')
    archive(common, output / 'rcpm-v1.0-common.zip')
    shutil.copy2(ROOT / 'docs/RELEASE-NOTES-1.0.md', output / 'RELEASE-NOTES.md')
    (output / 'SHA256SUMS').write_text(''.join(
        sha(path) + '  ' + path.name + '\n' for path in sorted(output.glob('*.zip'))))
    receipt = dict(version='1.0', publication='not-published',
                   guest_media='all-tested-images-and-drivers-unchanged',
                   frozen_host_runtime=frozen, common_files=len(common_files),
                   changes='documentation-source-snapshots-qualification-runner-and-metadata-only')
    (output / 'ASSEMBLY-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(output, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    build(parser.parse_args().output.resolve())
