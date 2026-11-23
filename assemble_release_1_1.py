#!/usr/bin/env python3
"""Assemble versioned RCP/M packages, preserving tested runtime bytes."""
import argparse
import json
from pathlib import Path
import shutil
from backup_rcpm import copy_file
from finalize_release import inventory, verify, refresh_source, archive, ROOT, sha


def copy_tree(source, target):
    shutil.copytree(source, target, copy_function=lambda s, d:
                    copy_file(Path(s), Path(d), Path(s).stat().st_mode & 0o777) and d,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))


def build(common_base, mac_base, windows_base, runtime, output, version="1.1", prepare_common=None, windows_launcher=None):
    if version not in ("1.1", "1.1.1", "1.2"):
        raise ValueError("Unsupported release version")
    bases = {'macos-arm64': mac_base, 'windows-x64': windows_base}
    manifests = {}
    for platform, base in bases.items():
        manifests[platform] = json.loads((base / 'metadata/MANIFEST.json').read_text())
        verify(base, manifests[platform])
    output.mkdir(parents=True, exist_ok=False)
    common = output / 'rcpm-common'
    copy_tree(common_base, common)
    (common / 'COMMON-MANIFEST.json').unlink()
    refresh_source(common / 'source/rcpm')
    shutil.copy2(ROOT / 'README.md', common / 'README.txt')
    shutil.copy2(ROOT / ('docs/RELEASE-NOTES-' + version + '.md'), common / 'docs/RELEASE-NOTES.md')
    shutil.copy2(ROOT / 'docs/distribution-review.md', common / 'docs/NOTICES/RELEASE-DECISIONS.md')
    shutil.copy2(ROOT / 'docs/installation-layout.md', common / 'docs/INSTALLATION-LAYOUT.md')
    # Keep packaged overview links useful outside a repository checkout.
    readme = common / 'README.txt'
    text = readme.read_text().replace('(docs/RELEASE-NOTES-' + version + '.md)', '(docs/RELEASE-NOTES.md)')
    text = text.replace('(docs/README.md)', '(https://github.com/CPMArchives/rcpm-cpmsim/tree/v' + version + '/docs)')
    text = text.replace('(Software/README.md)', '(https://github.com/CPMArchives/rcpm-cpmsim/tree/v' + version + '/Software)')
    text = text.replace('(docs/distribution-review.md)', '(docs/NOTICES/RELEASE-DECISIONS.md)')
    readme.write_text(text)
    (common / 'docs/DISTRIBUTION-STATUS.DOC').write_text(
        f'RCP/M {version}\n\nComponent-specific terms apply; no uniform license is asserted.\n'
        'Original notices and corresponding source remain in this package.\n'
        'The maintainer retains the accepted SIG/M/CPMUG, later Z3PLUS release,\n'
        'configured ZDE and modified BYE510 decisions from 1.0. This does not\n'
        'assert a new permission grant from their original authors.\n'
        'Preserve component-specific noncommercial/no-fee conditions.\n'
        'See docs/NOTICES/RELEASE-DECISIONS.md and docs/RELEASE-NOTES.md.\n')
    if prepare_common:
        prepare_common(common)
    common_files = inventory(common)
    receipt = dict(version=version, installation_layout=2, platforms={})
    for platform, base in bases.items():
        payload = output / base.name
        copy_tree(base, payload)
        for name in manifests[platform]['common']:
            (payload / name).unlink()
        for name in common_files:
            target = payload / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(common / name, target)
        if platform == 'macos-arm64':
            for name in ('rcpm', 'cpmsim', 'cpmsim.features.json'):
                shutil.copy2(runtime / name, payload / 'runtime' / name)
            qualification = 'macos-rbbs41-local-direct-and-native-initializer-passed' if version == '1.2' else 'macos-live-suite-and-swappable-drive-checks-passed'
        else:
            if windows_launcher:
                shutil.copy2(windows_launcher, payload / 'runtime/rcpm.exe')
            qualification = 'cross-compiled-audited-live-windows-' + version + '-not-repeated'
            extra = payload / 'WINDOWS-README.txt'
            extra.unlink(missing_ok=True)
            (payload / 'docs/WINDOWS-README.txt').write_text(
                f'RCP/M {version} Windows x64 test build\n\n'
                'Extract the entire ZIP into a writable local NTFS folder.\n'
                'Run Start-RCPM.cmd. Read docs/INSTALLATION.DOC and docs/RELEASE-NOTES.md.\n'
                'No Python or separate compiler is needed to run RCP/M.\n'
                f'{version} binaries are cross-compiled and audited, not live-qualified on Windows.\n'
                'The 1.0 Windows qualification does not cover this rebuilt runtime.\n'
                'Generated SYSOP.DOC contains private local credentials.\n')
            metadata_path = payload / 'metadata/BUILD-HOST.json'
            metadata = json.loads(metadata_path.read_text())
            metadata.update(version=version, installation_layout=2,
                            status=qualification, redistribution='component-terms-and-maintainer-decisions-retained')
            metadata.pop('common_archive_sha256', None)
            metadata_path.write_text(json.dumps(metadata, indent=2) + '\n')
            refresh_source(payload / 'source/host-windows')
        manifest_path = payload / 'metadata/MANIFEST.json'
        host_files = {name: digest for name, digest in inventory(payload).items()
                      if name not in common_files and name != 'metadata/MANIFEST.json'}
        manifest = dict(manifests[platform], version=version, installation_layout=2,
                        status=qualification, common=common_files, host=host_files)
        manifest.pop('common_archive_sha256', None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
        verify(payload, manifest)
        if set(inventory(payload)) != set(common_files) | set(host_files) | {'metadata/MANIFEST.json'}:
            raise ValueError('Unrecorded files in final package')
        for name in ('volumes', 'archives', 'offline', 'upload-inbox', 'upload-staging', 'NOTICES'):
            if (payload / name).exists():
                raise ValueError('Legacy top-level directory: ' + name)
        for name in ('SYSOP.DOC', 'state/initialized', 'state/layout-before-reorg'):
            if (payload / name).exists():
                raise ValueError('Operator state found in fresh package: ' + name)
        binary_hashes = {name: digest for name, digest in host_files.items()
                         if name.startswith('runtime/')}
        receipt['platforms'][platform] = dict(qualification=qualification, runtime_sha256=binary_hashes)
        archive(payload, output / ('rcpm-v' + version + '-' + platform + '.zip'))
    (common / 'COMMON-MANIFEST.json').write_text(json.dumps(common_files, indent=2) + '\n')
    archive(common, output / ('rcpm-v' + version + '-common.zip'))
    (output / 'ASSEMBLY-RECEIPT.json').write_text(json.dumps(receipt, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text(''.join(
        sha(p) + '  ' + p.name + '\n' for p in sorted(output.iterdir())
        if p.suffix == '.zip' or p.name == 'ASSEMBLY-RECEIPT.json'))
    print('Assembled RCP/M ' + version + ':', output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('common', 'macos', 'windows', 'runtime', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument("--version", choices=("1.1", "1.1.1"), default="1.1")
    args = parser.parse_args()
    build(args.common.resolve(), args.macos.resolve(), args.windows.resolve(),
          args.runtime.resolve(), args.output.resolve(), args.version)
