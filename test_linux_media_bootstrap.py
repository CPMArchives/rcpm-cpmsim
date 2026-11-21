"""Exercise the CD bootstrap with the filenames actually exposed by ISO9660."""
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest


class MediaBootstrapChecks(unittest.TestCase):
    def test_read_only_media_and_both_archive_spellings(self):
        bootstrap = Path(__file__).resolve().parent / 'packaging/Build-Linux-from-media.sh'
        for filename in ('rcpm-linux-arm64-build-kit.tar.gz', 'rcpm-linux-arm64-build-kit.gz'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                media = root / 'media'
                media.mkdir()
                script = media / 'build-rcpm.sh'
                script.write_bytes(bootstrap.read_bytes())
                script.chmod(0o444)
                with tarfile.open(media / filename, 'w:gz') as archive:
                    data = b'echo MEDIA-RUNNER-REACHED\n'
                    info = tarfile.TarInfo('RCPM-linux-arm64-build-kit/Build-and-Check.sh')
                    info.size = len(data)
                    info.mode = 0o444
                    archive.addfile(info, io.BytesIO(data))
                fixture_bin = root / 'fixture-bin'
                fixture_bin.mkdir()
                # Host guard fixture only; the extracted runner is a marker,
                # not a Linux compiler or qualification stand-in.
                uname = fixture_bin / 'uname'
                uname.write_text('#!/bin/sh\nprintf "Linux\\n"\n')
                uname.chmod(0o755)
                env = dict(os.environ, PATH=str(fixture_bin) + ':' + os.environ['PATH'],
                           RCPM_BUILD_ROOT=str(root / 'results'))
                media.chmod(0o555)
                try:
                    result = subprocess.run(['bash', str(script)], env=env,
                                            capture_output=True, text=True, check=True)
                    self.assertIn('MEDIA-RUNNER-REACHED', result.stdout)
                    self.assertEqual(len(list((root / 'results').glob('kit.*'))), 1)
                finally:
                    media.chmod(0o755)


if __name__ == '__main__':
    unittest.main()
