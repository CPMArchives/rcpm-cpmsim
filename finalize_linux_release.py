#!/usr/bin/env python3
"""Finalize a qualified Linux candidate without changing shared release media."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
from build_linux_release import sha


def finalize(candidate, evidence, output, version):
    manifest = json.loads((candidate / 'metadata/MANIFEST.json').read_text())
    result = json.loads(evidence.read_text())
    for key in ('direct_boot', 'caller_login', 'rbbs_entry', 'orderly_shutdown',
                'common_and_host_hashes', 'generated_passwords_match_guest_record'):
        if result.get(key) is not True:
            raise ValueError('Missing qualification: ' + key)
    for name, digest in dict(manifest['common'], **manifest['host']).items():
        if sha(candidate / name) != digest:
            raise ValueError('Candidate changed after qualification: ' + name)
    package = output / candidate.name
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(candidate, package)
    (package / 'metadata/LINUX-VALIDATION.json').write_text(json.dumps(result, indent=2) + '\n')
    host = package / 'metadata/BUILD-HOST.json'
    identity = json.loads(host.read_text())
    identity.update(live_qualification='direct-tcp-passed',
                    redistribution='maintainer-authorized-release-component-terms-apply')
    host.write_text(json.dumps(identity, indent=2) + '\n')
    (package / 'LINUX-README.txt').write_text(
        'RCP/M ' + version + ' — ' + manifest['platform'] + '\n\n'
        'Extract into a writable folder and run ./Start-RCPM.sh in a terminal.\n'
        'Connect a raw TCP client to 127.0.0.1:4000 after modem ready appears.\n'
        'The terminal is the sysop console. Keep SYSOP.DOC private.\n'
        'No Python, compiler, tmux or installed CP/M tools are required.\n'
        'See metadata/BUILD-HOST.json for measured architecture and GLIBC requirements.\n'
        'Direct TCP was qualified in Debian 12 containers on an ARM64 Docker host;\n'
        'x64 runs use CPU emulation. Native x64 hardware and IP232 were not tested.\n'
        'Shared system media is identical to the published ' + version + ' common ZIP.\n'
        'Preserve all component notices and terms. See docs/DISTRIBUTION-STATUS.DOC.\n')
    manifest['status'] = 'published-direct-tcp-qualified'
    manifest['host'] = {str(p.relative_to(package)):sha(p) for p in package.rglob('*')
                        if p.is_file() and str(p.relative_to(package)) not in manifest['common']
                        and p != package / 'metadata/MANIFEST.json'}
    (package / 'metadata/MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    destination = output / ('rcpm-v' + version + '-' + manifest['platform'] + '.tar.gz')
    with tarfile.open(destination, 'w:gz') as archive:
        archive.add(package, arcname=package.name)
    print(destination)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('candidate','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--version',default='1.2.1')
    a=p.parse_args();finalize(a.candidate.resolve(),a.evidence.resolve(),a.output.resolve(),a.version)
