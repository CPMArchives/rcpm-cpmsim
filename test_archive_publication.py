"""Regression checks for archive publication, session pinning, and write leases."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import archive_admin
from serve_rcpm import prepare_session


class ArchivePublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="rcpm-publication-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.console = self.root / "console"
        self.callers = self.root / "callers"
        for root in (self.console, self.callers):
            (root / "disks").mkdir(parents=True)
        for drive in "abijp":
            data = bytes(drive, "ascii") * 2048
            (self.console / "disks" / f"drive{drive}.dsk").write_bytes(data)
            (self.callers / "disks" / f"drive{drive}.dsk").symlink_to(
                self.console / "disks" / f"drive{drive}.dsk")
        (self.callers / "disks/library").mkdir()
        (self.callers / "disks/library/DEMO.dsk").write_bytes(b"v" * 2048)
        self.sizes = patch.dict(archive_admin.SIZES, {"j": 2048, "p": 2048}, clear=True)
        self.sizes.start()
        self.addCleanup(self.sizes.stop)

    def session(self, name):
        root = self.root / name
        root.mkdir()
        prepare_session(self.callers, root)
        return root

    def test_sessions_pin_archives_and_catalog_across_publication(self):
        first = archive_admin.setup(self.console, self.callers)
        self.assertEqual(archive_admin.setup(self.console, self.callers), first)
        old = self.session("old")
        master = self.console / "disks/drivep.dsk"
        self.assertTrue(master.stat().st_mode & 0o200)
        self.assertFalse((old / "disks/drivep.dsk").stat().st_mode & 0o222)
        with (old / "disks/drivep.dsk").open("rb") as reader:
            master.write_bytes(b"n" * 2048)
            (self.console / "disks/library/DEMO.dsk").write_bytes(b"w" * 2048)
            self.assertEqual((old / "disks/drivep.dsk").read_bytes(), b"p" * 2048)
            second = archive_admin.publish(self.console)
            new = self.session("new")
            self.assertNotEqual(first, second)
            self.assertEqual(reader.read(), b"p" * 2048)
            self.assertEqual((new / "disks/drivep.dsk").read_bytes(), b"n" * 2048)
            self.assertEqual((old / "disks/library/DEMO.dsk").read_bytes(), b"v" * 2048)
            self.assertEqual((new / "disks/library/DEMO.dsk").read_bytes(), b"w" * 2048)
            self.assertFalse((new / "disks/library/DEMO.dsk").stat().st_mode & 0o222)

    def test_active_console_blocks_publication(self):
        first = archive_admin.setup(self.console, self.callers)
        with archive_admin.console_lock(self.console):
            with self.assertRaisesRegex(RuntimeError, "local console is running"):
                archive_admin.publish(self.console)
        self.assertEqual((self.callers / "published/current").resolve(), first)

    def test_failed_publication_preserves_previous_generation_and_can_retry(self):
        first = archive_admin.setup(self.console, self.callers)
        (self.console / "disks/library/DEMO.dsk").write_bytes(b"bad size")
        with self.assertRaisesRegex(ValueError, "geometry"):
            archive_admin.publish(self.console)
        self.assertEqual((self.callers / "published/current").resolve(), first)
        self.assertFalse(list((self.callers / "published").glob(".preparing-*")))
        (self.console / "disks/library/DEMO.dsk").write_bytes(b"r" * 2048)
        self.assertNotEqual(archive_admin.publish(self.console), first)


if __name__ == "__main__":
    unittest.main()
