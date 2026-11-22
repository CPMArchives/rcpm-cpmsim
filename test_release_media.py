"""Check that public development-media reconstruction removes file bodies too."""
from pathlib import Path
import tempfile
import unittest

from release_media import (EXTERNAL_FILES, STOCK_BUILD_DISK,
                           separate_development_tools, tool,
                           verify_public_development_media)


class ReleaseMediaChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='rcpm-media-test-')
        self.root = Path(self.temporary.name)
        self.tools = (Path(__file__).resolve().parent / 'build/release-tools/bin')
        self.source = self.root / 'source'
        library = self.source / 'cpmsim/disks/library'
        library.mkdir(parents=True)
        self.original = library / 'cpm3-2.dsk'
        tool(self.tools, 'mkfs.cpm', '-f', 'ibm-3740', self.original)
        self.forbidden = []
        for number, name in enumerate((*EXTERNAL_FILES, 'KEEP.DOC')):
            data = (f'FIXTURE-{name}-' * 16).encode().ljust(512, bytes([65 + number]))
            path = self.root / name
            path.write_bytes(data)
            tool(self.tools, 'cpmcp', '-f', 'ibm-3740', self.original, path, '0:' + name)
            if name in EXTERNAL_FILES:
                self.forbidden.append(data)
        self.output = self.root / 'package'
        (self.output / 'disks/library/offline').mkdir(parents=True)
        # Simulate an old generated image containing the excluded bodies even
        # if directory entries have already been erased.
        old = self.output / 'disks/library/offline/BUILD.dsk'
        old.write_bytes(b'OLD-IMAGE' + b''.join(self.forbidden))
        old.chmod(0o444)

    def tearDown(self):
        self.temporary.cleanup()

    def test_fresh_image_removes_bodies_and_preserves_retained_file(self):
        report = separate_development_tools(self.source, self.tools, self.output)
        self.assertEqual(set(report['retained']), {'KEEP.DOC'})
        raw = (self.output / 'disks/library/offline/BUILD.dsk').read_bytes()
        for data in self.forbidden:
            self.assertNotIn(data, raw)
        self.assertEqual(verify_public_development_media(self.output, self.tools), report)

    def test_unfiltered_source_disk_copy_is_rejected(self):
        separate_development_tools(self.source, self.tools, self.output)
        hidden = self.output / STOCK_BUILD_DISK
        hidden.parent.mkdir(parents=True)
        hidden.write_bytes(self.original.read_bytes())
        with self.assertRaisesRegex(ValueError, 'Unfiltered stock'):
            verify_public_development_media(self.output, self.tools)


if __name__ == '__main__':
    unittest.main()
