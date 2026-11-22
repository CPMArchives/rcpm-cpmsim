"""Host-independent checks for Windows archive extraction boundaries."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from check_windows_release import unpack


class WindowsArchiveChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rcpm-win-archive-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, extras=(), corrupt=False):
        archive = self.root / 'candidate.zip'
        content = b'unchanged common bytes\r\n\x1a'
        manifest = dict(platform='windows-x64', common={'README.txt': hashlib.sha256(content).hexdigest()}, host={})
        with zipfile.ZipFile(archive, 'w') as stream:
            stream.writestr('RCPM-windows-x64/metadata/MANIFEST.json', json.dumps(manifest))
            stream.writestr('RCPM-windows-x64/README.txt', b'corrupted' if corrupt else content)
            for name in extras:
                stream.writestr(name, b'bad')
        return archive

    def test_verified_extraction_supports_spaces_and_unicode(self):
        package = unpack(self.archive(), self.root / 'Space and Unicode é')
        self.assertEqual((package / 'README.txt').read_bytes(), b'unchanged common bytes\r\n\x1a')

    def test_missing_or_changed_payload_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            unpack(self.archive(corrupt=True), self.root / 'out')

    def test_windows_case_collision_is_rejected_before_extraction(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate Windows'):
            unpack(self.archive(['RCPM-windows-x64/readme.TXT']), self.root / 'out')
        self.assertFalse((self.root / 'out').exists())

    def test_windows_special_names_and_path_escapes_are_rejected(self):
        for number, name in enumerate(('../outside', 'RCPM-windows-x64/../outside',
                'RCPM-windows-x64/CON.txt', 'RCPM-windows-x64/LPT1',
                'RCPM-windows-x64/data:stream', 'RCPM-windows-x64/trailing.',
                'RCPM-windows-x64/a/./b', 'RCPM-windows-x64/path\\file')):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'Unsafe Windows'):
                unpack(self.archive([name]), self.root / str(number))
        self.assertFalse((self.root / 'outside').exists())

    def test_zip_symlink_is_rejected(self):
        archive = self.archive()
        with zipfile.ZipFile(archive, 'a') as stream:
            link = zipfile.ZipInfo('RCPM-windows-x64/link')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            stream.writestr(link, 'outside')
        with self.assertRaisesRegex(ValueError, 'Unsafe Windows'):
            unpack(archive, self.root / 'out')


if __name__ == '__main__':
    unittest.main()
