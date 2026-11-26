#!/usr/bin/env python3
"""Rebuild service-only candidates from pinned rc1 kits without changing binaries."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile

REPO = Path(__file__).resolve().parent
BASE_HASHES = {
    'arm64': '0760949a7d2f5d5d8a70935d0b4fcf4844468523a419c78aecc3728795ae3b1e',
    'x64': '1bdae49d62568f494bde3af6fd4d30e52d2e33db6229594fc66c0391f769e9fb',
}
SOURCES = (
    'check_auth.py', 'check_chat46.py', 'check_flush_precaution.py',
    'check_debian_security.py', 'test_native_service.py',
    'rebuild_native_service_candidate.py', 'packaging/native/rcpm_service.py',
    'docs/native-service.md', 'docs/INSTALLATION-NATIVE-SERVICE.md',
    'docs/debian-caller-regression.md',
    'docs/performance/debian-caller-regression-2026-11-27.json',
    'docs/RELEASE-NOTES-1.2.2-rc2.md',
)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def verify(root):
    manifest = json.loads((root / 'metadata/MANIFEST.json').read_text())
    expected = {**manifest['common'], **manifest['host']}
    assert not set(manifest['common']) & set(manifest['host'])
    actual = set()
    for p in root.rglob('*'):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):
            raise ValueError('Unexpected package entry: ' + str(p))
        if p.is_file():
            actual.add(str(p.relative_to(root)))
    assert actual == set(expected) | {'metadata/MANIFEST.json'}
    for name, digest in expected.items():
        assert sha(root / name) == digest, name
    return manifest


def build(base_dir, output):
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = {name: sha(REPO / name) for name in SOURCES}
    provenance = dict(
        format='rcpm-service-candidate-2', version='v1.2.2-rc2', prerelease=True,
        published=False,
        checkout_base_commit=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
        source_identity='Exact working-tree source hashes; no new tag claimed',
        source_sha256=source_hashes, artifacts={},
    )
    for arch, expected_base in BASE_HASHES.items():
        base = base_dir / f'rcpm-v1.2.2-rc1-linux-{arch}-service.tar.gz'
        assert sha(base) == expected_base, 'Unexpected rc1 input: ' + str(base)
        stage = output / 'expanded' / arch
        stage.mkdir(parents=True)
        root = stage / ('RCPM-linux-' + arch)
        with tarfile.open(base) as archive:
            for m in archive.getmembers():
                name = PurePosixPath(m.name)
                if (name.is_absolute() or '..' in name.parts or not name.parts
                        or name.parts[0] != root.name
                        or not (m.isfile() or m.isdir())):
                    raise ValueError('Unsafe archive entry: ' + m.name)
                target = stage / str(name)
                if m.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(m) as incoming, target.open('wb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
                    target.chmod(m.mode & 0o777)
        manifest = verify(root)
        before = {**manifest['common'], **manifest['host']}
        overlays = {}

        def put(source, relative):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO / source, target)
            overlays[relative] = source

        put('packaging/native/rcpm_service.py', 'service/rcpm_service.py')
        put('docs/native-service.md', 'service/README.md')
        put('docs/debian-caller-regression.md', 'service/debian-caller-regression.md')
        for name in SOURCES:
            put(name, 'source/rcpm/' + name)
        for name in ('packaging/native/rcpm_service.py', 'test_native_service.py',
                     'docs/native-service.md'):
            put(name, 'source/host-linux/' + name)
        for name in ('docs/debian-caller-regression.md',
                     'docs/performance/debian-caller-regression-2026-11-27.json',
                     'docs/INSTALLATION-NATIVE-SERVICE.md',
                     'docs/RELEASE-NOTES-1.2.2-rc2.md'):
            put(name, name)
        changed = {name: dict(before=before.get(name), after=sha(root / name))
                   for name in overlays if before.get(name) != sha(root / name)}
        preserved = [name for name in before
                     if name.startswith(('runtime/', 'disks/', 'drivers/'))]
        assert preserved
        for name in preserved:
            assert sha(root / name) == before[name], name
        receipt = dict(version='v1.2.2-rc2', base_archive_sha256=expected_base,
                       unchanged_native_media_driver_files=len(preserved),
                       source_overlays=overlays, changed_files=changed)
        write_json(root / 'metadata/SERVICE-CANDIDATE.json', receipt)
        manifest['base_common_archive_sha256'] = manifest.pop('common_archive_sha256')
        manifest['service_candidate_version'] = 'v1.2.2-rc2'
        manifest['status'] = 'prerelease-candidate-not-vps-qualified'
        # Changed corresponding sources are service overlays on the base payload.
        for name in overlays:
            manifest['common'].pop(name, None)
        manifest['host'] = {
            str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and str(p.relative_to(root)) not in manifest['common']
            and p != root / 'metadata/MANIFEST.json'
        }
        write_json(root / 'metadata/MANIFEST.json', manifest)
        verify(root)
        target = output / f'rcpm-v1.2.2-rc2-linux-{arch}-service.tar.gz'
        with tarfile.open(target, 'w:gz') as archive:
            archive.add(root, arcname=root.name)
        provenance['artifacts'][target.name] = dict(
            sha256=sha(target), bytes=target.stat().st_size,
            base_archive_sha256=expected_base,
            unchanged_native_media_driver_files=len(preserved),
            changed_files=changed,
        )
    write_json(output / 'RELEASE-PROVENANCE.json', provenance)
    for source, name in (
        ('docs/INSTALLATION-NATIVE-SERVICE.md', 'NATIVE-DEBIAN-INSTALLATION.md'),
        ('docs/RELEASE-NOTES-1.2.2-rc2.md', 'RELEASE-NOTES.md'),
        ('docs/debian-caller-regression.md', 'CALLER-REGRESSION-REPORT.md'),
        ('docs/performance/debian-caller-regression-2026-11-27.json', 'CALLER-REGRESSION.json'),
    ):
        shutil.copy2(REPO / source, output / name)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.base_dir.resolve(), args.output.resolve())
