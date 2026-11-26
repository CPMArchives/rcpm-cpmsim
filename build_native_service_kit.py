#!/usr/bin/env python3
"""Build an offline-installable native Linux service kit; never install/start it."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import tempfile

from build_linux_release import audit_native, host_architecture, sha
from check_release import extract_package

REVISION = 'fe7feff4862406b277e009d14c219f5d16cf1222'
SOURCE_SHA256 = 'b70e9b222e7dbdcc2fb0395caf444f1ddd329f5d9958b5895a5e921fed2bbc68'
REPO = Path(__file__).resolve().parent



def patch_tcpser(source):
    """Restore command mode after failed ATD; upstream otherwise eats next command."""
    path = source / 'src/modem_core.c'
    text = path.read_text()
    old = '    } else {\n      mdm_send_response(MDM_RESP_NO_CARRIER, cfg);\n      usleep(cfg->disconnect_delay * 1000);\n    }\n  }\n  return 0;\n}\n\nint mdm_listen'
    new = old.replace('      mdm_send_response',
        '      cfg->is_cmd_mode = TRUE;\n'
        '      cfg->is_off_hook = FALSE;\n'
        '      mdm_set_control_lines(cfg);\n'
        '      mdm_send_response', 1)
    if text.count(old) != 1:
        raise ValueError('Unrecognized pinned tcpser failed-dial implementation')
    path.write_text(text.replace(old, new))
    bridge = source / 'src/bridge.c'
    text = bridge.read_text()
    old = 'for(int i = 0; i < res ; i++) {\n        switch (buf[0]) {'
    if text.count(old) != 1:
        raise ValueError('Unrecognized pinned tcpser control-event loop')
    bridge.write_text(text.replace(old, old.replace('buf[0]', 'buf[i]')))


def build(package, source, output):
    architecture = host_architecture()
    if sha(source) != SOURCE_SHA256:
        raise ValueError('Expected the recorded pinned tcpser source archive; see docs/native-service.md')
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='rcpm-service-build-', dir=output) as temporary:
        work = Path(temporary)
        root = extract_package(package, work / 'package')
        manifest = json.loads((root / 'metadata/MANIFEST.json').read_text())
        if manifest['platform'] != 'linux-' + architecture:
            raise ValueError('Package architecture does not match build host')
        for section in ('common', 'host'):
            for name, expected in manifest[section].items():
                if sha(root / name) != expected:
                    raise ValueError('Input package checksum mismatch: ' + name)
        if (root / 'service').exists() or (root / 'runtime/tcpser').exists():
            raise ValueError('Use an unmodified base Linux package')
        shutil.copy2(source, root / 'source/tcpser-upstream.tar.gz')
        upstream = root / 'source/tcpser'
        upstream.mkdir()
        with tarfile.open(source) as archive:
            for entry in archive.getmembers():
                path = PurePosixPath(entry.name)
                if path.is_absolute() or '..' in path.parts or not (entry.isfile() or entry.isdir()):
                    raise ValueError('Unsafe tcpser archive entry')
                if len(path.parts) == 1:
                    continue
                relative = Path(*path.parts[1:])
                # Source only; omit upstream prebuilt Windows binaries.
                if relative.suffix.lower() in ('.exe', '.o'):
                    continue
                target = upstream / relative
                if entry.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.extractfile(entry) as incoming, target.open('wb') as outgoing:
                        shutil.copyfileobj(incoming, outgoing)
        patch_tcpser(upstream)
        (upstream / 'RCPM-CHANGES.txt').write_text(
            'RCP/M integration: failed ATD restores command mode and on-hook state before NO CARRIER.\n'
            'Control-event batches process every event, not the first event repeatedly.\n'
            'Original revision: ' + REVISION + '\n'
            'Complete patched corresponding source is included in this directory.\n')
        compile_root = work / 'tcpser-build'
        shutil.copytree(upstream, compile_root)
        subprocess.run(['make', '-C', str(compile_root)], check=True)
        shutil.copy2(compile_root / 'tcpser', root / 'runtime/tcpser')
        dependency_audit = audit_native(root / 'runtime/tcpser', architecture)
        shutil.copytree(REPO / 'packaging/native', root / 'service',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(REPO / 'docs/native-service.md', root / 'service/README.md')
        host_source = root / 'source/host-linux'
        for name in ('build_native_service_kit.py', 'check_native_service.py',
                     'check_outbound_modem.py', 'check_board_outbound.py', 'check_debian_vm.py', 'check_modem_runtime.py',
                     'check_rcpm_transport.py', 'test_native_service.py', 'test_modem_device.py'):
            shutil.copy2(REPO / name, host_source / name)
        shutil.copytree(REPO / 'packaging/native', host_source / 'packaging/native',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        (host_source / 'docs').mkdir(exist_ok=True)
        shutil.copy2(REPO / 'docs/native-service.md', host_source / 'docs/native-service.md')
        (host_source / 'guest').mkdir(exist_ok=True)
        for name in ('dialprobe.asm', 'modemprobe.asm'):
            shutil.copy2(REPO / 'guest' / name, host_source / 'guest' / name)
        # Include a full GPL text as well as tcpser's retained original notices.
        shutil.copy2(REPO / 'packaging/native/TCPSER-COPYING', upstream / 'COPYING')
        installer = root / 'Install-Service.sh'
        installer.write_text('#!/bin/sh\nset -eu\nexec "$(dirname "$0")/service/Install-Service.sh" "$@"\n')
        installer.chmod(0o755)
        (root / 'INSTALL-SERVICE.txt').write_text(
            'Native Debian service engineering candidate\n\n'
            'Requires Python 3.9+ and systemd; tcpser and its source are bundled.\n'
            '1. ./Install-Service.sh --check\n'
            '2. sudo ./Install-Service.sh --install\n'
            'Installation leaves all services stopped/disabled and access loopback-only.\n'
            'See service/README.md for startup, qualification, backups and restore.\n'
            'Do not overwrite an existing board. No CPMNet software is included.\n')
        receipt = dict(revision=REVISION, patches=['failed-dial-command-mode-recovery', 'coalesced-control-event-index'], source_archive_sha256=SOURCE_SHA256,
                       sha256=sha(root / 'runtime/tcpser'), native=dependency_audit,
                       license='GPL-2.0-or-later; original notices in source/tcpser',
                       source_url='https://github.com/go4retro/tcpser/tree/' + REVISION)
        (root / 'metadata/TCPSER.json').write_text(json.dumps(receipt, indent=2) + '\n')
        manifest['host'] = {str(p.relative_to(root)): sha(p) for p in root.rglob('*')
                            if p.is_file() and str(p.relative_to(root)) not in manifest['common']
                            and p != root / 'metadata/MANIFEST.json'}
        manifest['status'] = 'native-service-engineering-candidate-not-vps-qualified'
        (root / 'metadata/MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        target = output / ('rcpm-service-linux-' + architecture + '-candidate.tar.gz')
        with tarfile.open(target, 'w:gz') as archive:
            archive.add(root, arcname=root.name)
        (output / 'SHA256SUMS').write_text(sha(target) + '  ' + target.name + '\n')
        print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--tcpser-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.package.resolve(), args.tcpser_source.resolve(), args.output.resolve())
