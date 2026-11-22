"""Actual mount-device protocol tests with sparse fixed-geometry images."""
import ctypes
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class MountDevice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        source = root / 'device.c'
        source.write_text('''#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <dirent.h>
#include <stdio.h>
#include <string.h>
typedef unsigned char BYTE;
static int j, p;
static struct {const char *fn; int *fd;} disks[16];
#include "emulator/rcpm_mount.c"
void start(void) {
 j=open("disks/drivej.dsk",O_RDWR); p=open("disks/drivep.dsk",O_RDWR);
 disks[9].fn="drivej.dsk"; disks[9].fd=&j;
 disks[15].fn="drivep.dsk"; disks[15].fd=&p;
 memset(mounted_volume,0,sizeof(mounted_volume));
 listing=0; mount_slot=0; mount_status=1;
}
void finish(void) { close_catalog(); close(j); close(p); }
void send_byte(int c) { mount_out((BYTE)c); }
int get_byte(void) { return mount_in(); }
int first_byte(int drive) {
 unsigned char c=0; int fd=drive==15?p:j;
 lseek(fd,0,SEEK_SET); return read(fd,&c,1)==1?c:-1;
}
''')
        lib = root / 'device.so'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-shared',
                        '-fPIC', '-I', str(Path(__file__).resolve().parent),
                        str(source), '-o', str(lib)], check=True)
        cls.dev = ctypes.CDLL(str(lib))

    def setUp(self):
        self.data = tempfile.TemporaryDirectory()
        self.addCleanup(self.data.cleanup)
        self.previous = os.getcwd()
        os.chdir(self.data.name)
        self.addCleanup(os.chdir, self.previous)
        for name in ('disks', 'disks/library', 'disks/library/archives'):
            Path(name).mkdir(parents=True, exist_ok=True)
        self.image('disks/drivej.dsk', 4177920, b'j')
        self.image('disks/drivep.dsk', 536870912, b'p')
        self.image('disks/library/GAMES.dsk', 4177920, b'J')
        self.image('disks/library/archives/ALPHA.dsk', 536870912, b'P')
        self.dev.start()
        self.addCleanup(self.dev.finish)

    def image(self, name, size, marker):
        with Path(name).open('wb') as stream:
            stream.write(marker)
            stream.truncate(size)

    def request(self, command, name=''):
        self.dev.send_byte(command)
        if name:
            for c in name.encode():
                self.dev.send_byte(c)
            self.dev.send_byte(0)
        return self.dev.get_byte()

    def catalog(self, command):
        self.dev.send_byte(command)
        result = bytearray()
        while c := self.dev.get_byte():
            result.append(c)
        return result.decode()

    def test_independent_drives_legacy_j_and_default_restore(self):
        self.assertEqual(self.request(0xfb), 0xa2)
        self.assertEqual(self.request(0xfd, 'ALPHA'), 0)
        self.assertEqual(self.dev.first_byte(15), ord('P'))
        self.assertEqual(self.request(0xff, 'GAMES'), 0)
        self.assertEqual(self.dev.first_byte(9), ord('J'))
        self.assertEqual(self.dev.first_byte(15), ord('P'))
        self.assertEqual(self.request(0xfa), 0)
        self.assertEqual(self.dev.first_byte(15), ord('p'))
        self.assertEqual(self.dev.first_byte(9), ord('J'))
        self.assertEqual(self.request(0xf9), 0)
        self.assertEqual(self.dev.first_byte(9), ord('j'))

    def test_wrong_geometries_do_not_replace_either_drive(self):
        self.image('disks/library/archives/SMALL.dsk', 4177920, b'x')
        self.image('disks/library/BIG.dsk', 536870912, b'x')
        self.assertEqual(self.request(0xfd, 'SMALL'), 3)
        self.assertEqual(self.request(0xff, 'BIG'), 3)
        self.assertEqual(self.dev.first_byte(9), ord('j'))
        self.assertEqual(self.dev.first_byte(15), ord('p'))
        self.assertNotIn('SMALL', self.catalog(0xfc))
        self.assertNotIn('BIG', self.catalog(0xfe))
        self.assertIn('ALPHA', self.catalog(0xfc))
        self.assertIn('GAMES', self.catalog(0xfe))

    def test_invalid_missing_nonregular_and_truncated_leave_media_unchanged(self):
        self.assertEqual(self.request(0xfd, '../BAD'), 1)
        self.assertEqual(self.request(0xfd, 'MISSING'), 2)
        Path('disks/library/archives/DIR.dsk').mkdir()
        self.assertEqual(self.request(0xfd, 'DIR'), 2)
        self.image('disks/library/archives/SHORT.dsk', 536870911, b'x')
        self.assertEqual(self.request(0xfd, 'SHORT'), 3)
        self.assertEqual(self.dev.first_byte(15), ord('p'))
        self.assertIn('P: <default>', self.catalog(0xfc))


if __name__ == '__main__':
    unittest.main()
