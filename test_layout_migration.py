"""Check migration preserves operator state and refuses unsafe transitions."""
import fcntl
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from migrate_layout import migrate


class LayoutMigration(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'installation'
        self.runtime = Path(tmp.name) / 'rebuilt'
        for name in ('disks', 'volumes', 'offline', 'upload-inbox', 'upload-staging', 'state', 'runtime'):
            (self.root / name).mkdir(parents=True)
        self.runtime.mkdir()
        for name in ('rcpm', 'cpmsim'):
            (self.runtime / name).write_bytes(b'rebuilt-runtime')
            (self.root / 'runtime' / name).write_bytes(b'original-runtime')
        (self.runtime / 'cpmsim.features.json').write_text(json.dumps(dict(
            installation_layout=2, sha256=hashlib.sha256(b'rebuilt-runtime').hexdigest())))
        self.preserved = {'disks/drivea.dsk': b'operator disk', 'volumes/GAMES.dsk': b'collection',
                          'SYSOP.DOC': b'private fixture credentials', 'state/initialized': b'initialized',
                          'RCPM.CONF': b'PORT=4000'}
        for name, data in self.preserved.items():
            (self.root / name).write_bytes(data)
        (self.root / 'SYSOP.DOC').chmod(0o600)
        (self.root / 'MANIFEST.json').write_text(json.dumps(dict(common={}, host={})))

    def test_migration_preserves_credentials_and_disks_and_refuses_repeat(self):
        migrate(self.root, self.runtime)
        for name, data in self.preserved.items():
            destination = name.replace('volumes/', 'disks/library/')
            self.assertEqual((self.root / destination).read_bytes(), data)
        self.assertEqual((self.root / 'SYSOP.DOC').stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.root / 'state/layout-before-reorg/cpmsim').read_bytes(), b'original-runtime')
        with self.assertRaisesRegex(ValueError, 'second migration'):
            migrate(self.root, self.runtime)

    def test_running_instance_is_untouched(self):
        with (self.root / '.console.lock').open('a+b') as lease:
            fcntl.flock(lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'running'):
                migrate(self.root, self.runtime)
        self.assertTrue((self.root / 'volumes').is_dir())
        self.assertFalse((self.root / 'state/layout-before-reorg').exists())

    def test_old_runtime_is_rejected_before_changes(self):
        (self.runtime / 'cpmsim.features.json').write_text('{"installation_layout":1}')
        with self.assertRaisesRegex(ValueError, 'layout 2'):
            migrate(self.root, self.runtime)
        self.assertTrue((self.root / 'volumes').is_dir())
