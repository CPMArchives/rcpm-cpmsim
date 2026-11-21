"""Check shared-payload integrity and portable Linux archive extraction."""
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from build_linux_release import unpack_common, verify_common, host_architecture, audit_native
from check_release import extract_package


class LinuxPackagingChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='rcpm-linux-package-test-')
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def common(self):
        source = self.root / 'rcpm-common'
        source.mkdir()
        files = {'README.txt': b'common-payload\n', 'DEVELOPMENT-MEDIA.json': b'{}\n'}
        for name, data in files.items():
            (source / name).write_bytes(data)
        manifest = {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
        (source / 'COMMON-MANIFEST.json').write_text(json.dumps(manifest))
        archive = self.root / 'common.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            for path in source.iterdir():
                output.write(path, 'rcpm-common/' + path.name)
        return archive, manifest

    def test_common_payload_hashes_detect_changed_content(self):
        archive, manifest = self.common()
        unpacked = unpack_common(archive, self.root / 'unpacked')
        self.assertEqual(verify_common(unpacked), manifest)
        (unpacked / 'README.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            verify_common(unpacked)

    def test_common_payload_rejects_unrecorded_files(self):
        archive, _ = self.common()
        unpacked = unpack_common(archive, self.root / 'unpacked')
        (unpacked / 'unexpected').write_text('not in the manifest')
        with self.assertRaisesRegex(ValueError, 'unrecorded'):
            verify_common(unpacked)

    def test_linux_tar_preserves_launcher_mode_and_package_root(self):
        package = self.root / 'RCPM-linux-x64'
        package.mkdir()
        (package / 'MANIFEST.json').write_text('{"platform":"linux-x64"}')
        launcher = package / 'Start-RCPM.sh'
        launcher.write_text('#!/bin/sh\nexit 0\n')
        launcher.chmod(0o755)
        archive = self.root / 'linux.tar.gz'
        with tarfile.open(archive, 'w:gz') as output:
            output.add(package, arcname=package.name)
        unpacked = extract_package(archive, self.root / 'relocated with spaces')
        self.assertEqual(unpacked.name, 'RCPM-linux-x64')
        self.assertEqual((unpacked / launcher.name).stat().st_mode & 0o777, 0o755)

    def test_path_escape_in_common_archive_is_rejected(self):
        archive = self.root / 'bad.zip'
        with zipfile.ZipFile(archive, 'w') as output:
            output.writestr('rcpm-common/../../outside', b'escape')
        with self.assertRaisesRegex(ValueError, 'Unexpected common archive member'):
            unpack_common(archive, self.root / 'unpacked')
        self.assertFalse((self.root / 'outside').exists())

    def test_native_host_architecture_is_selected_explicitly(self):
        with patch('build_linux_release.platform.system', return_value='Linux'):
            for machine, expected in [('aarch64', 'arm64'), ('arm64', 'arm64'), ('x86_64', 'x64')]:
                with patch('build_linux_release.platform.machine', return_value=machine):
                    self.assertEqual(host_architecture(), expected)
            with patch('build_linux_release.platform.machine', return_value='riscv64'):
                with self.assertRaisesRegex(ValueError, 'Linux x64 or ARM64'):
                    host_architecture()

    def test_arm64_audit_rejects_x64_binary_and_accepts_aarch64(self):
        with patch('build_linux_release.subprocess.check_output',
                   return_value='Class: ELF64\nMachine: Advanced Micro Devices X86-64\n'):
            with self.assertRaisesRegex(ValueError, 'arm64 ELF'):
                audit_native(self.root / 'program', 'arm64')
        with patch('build_linux_release.subprocess.check_output', side_effect=[
                'Class: ELF64\nMachine: AArch64\n',
                'libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x1000)\n',
                'Name: GLIBC_2.17\nName: GLIBC_2.34\n']):
            self.assertEqual(audit_native(self.root / 'program', 'arm64')
                             ['required_glibc_symbols_through'], '2.34')


if __name__ == '__main__':
    unittest.main()
