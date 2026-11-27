#!/usr/bin/env python3
"""Assemble checked v1.2.2 downloads; refresh documentation without changing runtime."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
import zipfile
import subprocess

from check_release import extract_package
from assemble_release_1_2_2 import sha

REPO = Path(__file__).resolve().parent
PLATFORMS = ('macos-arm64', 'linux-arm64', 'linux-x64', 'windows-x64')
SOURCE_FILES = (
    'packaging/launcher.c', 'packaging/modem_host.h', 'packaging/RCPM.CONF',
    'packaging/INSTALLATION.DOC', 'packaging/SYSOP-GUIDE.DOC',
    'assemble_release_1_2_2.py', 'prepare_release_1_2_2.py', 'finalize_release_1_2_2.py',
    'build_raw_cpmtools.py', 'check_bundled_modem_launcher.py', 'check_docker_release.py',
    'packaging/native/TCPSER-COPYING',
    'docs/RELEASE-NOTES-1.2.2.md',
)


def refresh_docs(root):
    for name in ('INSTALLATION.DOC', 'SYSOP-GUIDE.DOC'):
        shutil.copy2(REPO / 'packaging' / name, root / 'docs' / name)
    shutil.copy2(REPO / 'docs/RELEASE-NOTES-1.2.2.md', root / 'docs/RELEASE-NOTES-1.2.2.md')
    project = root / 'source/rcpm'
    for name in SOURCE_FILES:
        target = project / name; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, target)
    shutil.copytree(REPO / 'windows', project / 'windows', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (project / 'BUILD-1.2.2.md').write_text(
        'Build on the matching operating system using prepare_release_1_2_2.py.\n'
        'It verifies v1.2.1 inputs and pinned tcpser sources, then builds only host updates.\n'
        'Windows needs a build-only Cygwin gcc/make and MinGW toolchain (--cygwin ROOT).\n'
        'Runtime dependencies and source are packaged; sysops install no build tools.\n'
        'See .github/workflows/build-v1.2.2.yml at the release tag for exact hosted build commands.\n')


def archive(root, destination):
    if destination.suffix == '.zip':
        with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as output:
            for p in sorted(root.rglob('*')):
                output.write(p, p.relative_to(root.parent))
    else:
        with tarfile.open(destination, 'w:gz') as output:
            output.add(root, arcname=root.name)


def finalize(inputs, output, run_ids):
    output.mkdir(parents=True, exist_ok=False)
    report = dict(version='v1.2.2', build_runs=run_ids, platforms={}, docker={},
                  scope='Bundled foreground modem, commented defaults and corrected manuals; no hosting add-on',
                  published=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-final-') as temporary:
        for platform in PLATFORMS:
            folder = inputs / ('v1.2.2-' + platform)
            checks = json.loads((folder / 'checks/result.json').read_text())
            if checks.get('passed') is not True or {r['mode'] for r in checks['results'] if r['passed']} != {'direct', 'ip232'}:
                raise ValueError('Missing successful mode checks: ' + platform)
            suffix = '.zip' if platform.startswith(('macos-', 'windows-')) else '.tar.gz'
            name = 'rcpm-v1.2.2-' + platform + suffix
            candidates = list(folder.rglob(name))
            if len(candidates) != 1: raise ValueError('Expected one ' + name)
            root = extract_package(candidates[0], Path(temporary) / platform)
            manifest_path = root / 'metadata/MANIFEST.json'
            manifest = json.loads(manifest_path.read_text())
            expected = {**manifest['common'], **manifest['host']}
            actual = {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p != manifest_path}
            if actual != expected: raise ValueError('Candidate manifest mismatch: ' + platform)
            runtime = {n:h for n,h in expected.items() if n.startswith(('runtime/', 'disks/', 'drivers/'))}
            launcher = 'runtime/rcpm.exe' if platform == 'windows-x64' else 'runtime/rcpm'
            if checks['launcher_sha256'] != runtime[launcher]: raise ValueError('Untested launcher')
            if platform == 'windows-x64':
                arm = json.loads((inputs / 'v1.2.2-windows-arm64-evidence/result.json').read_text())
                if arm.get('passed') is not True or arm['launcher_sha256'] != runtime[launcher]:
                    raise ValueError('Missing Windows 11 ARM64 compatibility checks')
                report['windows_arm64'] = dict(execution='x64 emulation', checks=arm)
            refresh_docs(root)
            validation = dict(platform=platform, checks=checks, runtime_media_sha256=runtime,
                              tested_archive_sha256=sha(candidates[0]),
                              finalization='Documentation/source overlays only; native/runtime/media bytes unchanged')
            (root / 'metadata/LAUNCHER-VALIDATION.json').write_text(json.dumps(validation, indent=2)+'\n')
            if any(root.rglob('*.service')) or any(root.rglob('*.timer')):
                raise ValueError('Hosting units leaked into standard package')
            # Keep the original audit identified as a base record, never as an audit of new binaries.
            old = root / 'metadata/BUILD-HOST.json'
            base_audit = 'BASE-BUILD-HOST.json' if old.exists() else None
            if old.exists(): old.rename(root / 'metadata/BASE-BUILD-HOST.json')
            old.write_text(json.dumps(dict(version='v1.2.2', platform=platform,
                runtime_sha256={n:h for n,h in runtime.items() if n.startswith('runtime/')},
                qualification='LAUNCHER-VALIDATION.json', base_audit=base_audit), indent=2)+'\n')
            contents = {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file() and p != manifest_path}
            common = {n:h for n,h in manifest['common'].items() if contents.get(n)==h}
            manifest.update(version='v1.2.2', status='qualified-standard-foreground-package', common=common,
                            host={n:h for n,h in contents.items() if n not in common})
            manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
            assert all(sha(root/n)==h for n,h in runtime.items())
            archive(root, output / name)
            report['platforms'][platform] = dict(artifact=name, sha256=sha(output/name), **validation)
            if platform.startswith('linux-'):
                for mode in ('direct', 'ip232'):
                    state = json.loads((folder / ('docker-'+mode) / 'result.json').read_text())
                    if not all(state.get(k) is True for k in ('published_tcp_login','caller_help','rbbs_entry','orderly_shutdown','container_replacement_preserves_credentials')):
                        raise ValueError('Missing Docker check: ' + platform + '/' + mode)
                arch = platform.removeprefix('linux-')
                docker_name = 'rcpm-v1.2.2-docker-'+arch+'.tar.gz'
                path = next(folder.rglob(docker_name))
                shutil.copy2(path, output / docker_name)
                report['docker'][arch] = dict(artifact=docker_name, sha256=sha(path),
                    modes=['direct','ip232'], persistent_volume=True,
                    note='Image bytes retained from the checked build; updated manuals also accompany the release')
    # Refresh the optional developer/common download too, retaining every disk.
    with tempfile.TemporaryDirectory(prefix='rcpm-common-final-') as temporary:
        work = Path(temporary)
        subprocess.run(['gh','release','download','v1.2.1','--repo','CPMArchives/rcpm-cpmsim',
                        '--pattern','rcpm-v1.2.1-common.zip','--pattern','SHA256SUMS','--dir',str(work)],check=True)
        old_common = work / 'rcpm-v1.2.1-common.zip'
        sums = {l.split()[1]:l.split()[0] for l in (work/'SHA256SUMS').read_text().splitlines() if len(l.split())==2}
        if sha(old_common) != sums[old_common.name]: raise ValueError('Common input checksum mismatch')
        with zipfile.ZipFile(old_common) as source:
            for entry in source.infolist():
                p = Path(entry.filename)
                if p.is_absolute() or '..' in p.parts or p.parts[0] != 'rcpm-common':
                    raise ValueError('Unexpected common archive member')
            source.extractall(work)
        root = work / 'rcpm-common'
        manifest = root / 'COMMON-MANIFEST.json'; before = json.loads(manifest.read_text())
        if any(sha(root/n)!=h for n,h in before.items()): raise ValueError('Common input manifest mismatch')
        refresh_docs(root)
        shutil.copy2(REPO / 'packaging/RCPM.CONF', root / 'RCPM.CONF')
        (root / 'README.txt').write_text('RCP/M 1.2.2 common developer payload. Not a runnable platform download.\nUse the complete platform package for unpack-and-launch installation.\nGuest media is unchanged from v1.2.1.\n')
        (root / 'docs/RELEASE-NOTES.md').write_text((REPO/'docs/RELEASE-NOTES-1.2.2.md').read_text())
        assert all(sha(root/n)==h for n,h in before.items() if n.startswith(('disks/','drivers/')))
        manifest.write_text(json.dumps({p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*'))
                                      if p.is_file() and p!=manifest},indent=2)+'\n')
        common_name = 'rcpm-v1.2.2-common.zip'; archive(root, output / common_name)
        report['common'] = dict(artifact=common_name, sha256=sha(output/common_name), media_unchanged=True)
    # Small build kit: reproducible host refresh around the verified public base.
    kit = output / 'rcpm-v1.2.2-linux-docker-build-sources.zip'
    with zipfile.ZipFile(kit,'w',zipfile.ZIP_DEFLATED) as source:
        for name in (*SOURCE_FILES, 'check_release.py','check_windows_release.py'):
            source.write(REPO/name, 'rcpm-build-1.2.2/'+name)
        for area in ('windows','packaging/docker'):
            for p in (REPO/area).rglob('*'):
                if p.is_file() and '__pycache__' not in p.parts:
                    source.write(p,'rcpm-build-1.2.2/'+p.relative_to(REPO).as_posix())
        source.writestr('rcpm-build-1.2.2/README.txt',
            'On the target Linux architecture, install build-time cc/make/python3/gh.\n'
            'Run python3 prepare_release_1_2_2.py --platform linux-arm64 --work out\n'
            '(use linux-x64 on x64). It verifies and downloads public pinned inputs.\n'
            'Build the container with packaging/docker/Dockerfile and PACKAGE set to\n'
            'out/package/expanded/RCPM-linux-arm64 (or RCPM-linux-x64).\n'
            'Sysops use the prebuilt downloads and need none of these build tools.\n')
    shutil.copy2(REPO / 'docs/RELEASE-NOTES-1.2.2.md', output / 'RELEASE-NOTES.md')
    report_path = output / 'VALIDATION.json'
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    (output / 'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(output.iterdir())
        if p.is_file() and p.name != 'SHA256SUMS'))
    print('Finalized verified packages in', output, flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--runs', required=True)
    a = p.parse_args(); finalize(a.inputs.resolve(), a.output.resolve(), json.loads(a.runs))
