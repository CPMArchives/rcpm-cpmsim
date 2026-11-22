"""Construct release development media without separately supplied legacy tools."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

EXTERNAL_TOOLS = ('L80.COM', 'M80.COM', 'WM.COM')
EXTERNAL_FILES = (*EXTERNAL_TOOLS, 'WM.HLP')
STOCK_BUILD_DISK = 'source/upstream/z80pack/cpmsim/disks/library/cpm3-2.dsk'


def tool(tools, name, *arguments):
    definitions = Path(tools).parent / 'share/diskdefs'
    if not definitions.is_file():
        definitions = Path(tools) / 'diskdefs'
    env = dict(os.environ)
    if definitions.is_file():
        env['DISKDEFS'] = str(definitions.resolve())
    return subprocess.run([str(Path(tools) / name), *map(str, arguments)],
                          check=True, capture_output=True, env=env).stdout


def names(tools, image, fmt):
    return sorted(line.strip().upper() for line in
                  tool(tools, 'cpmls', '-f', fmt, image).decode('ascii').splitlines()
                  if line.strip() and not line.strip().endswith(':'))


def separate_development_tools(source, tools, output):
    """Only call on the new, stopped release staging tree, never live media."""
    original = Path(source) / 'cpmsim/disks/library/cpm3-2.dsk'
    (Path(output) / 'metadata').mkdir(parents=True, exist_ok=True)
    offline = Path(output) / 'disks/library/offline'
    offline.mkdir(parents=True, exist_ok=True)
    target = offline / 'BUILD.dsk'
    staged = offline / 'BUILD-public.new.dsk'
    source_names = names(tools, original, 'ibm-3740')
    if not set(EXTERNAL_FILES).issubset(source_names):
        raise ValueError('Expected the pinned stock build disk with M80/L80/WM')
    retained, excluded = {}, {}
    with tempfile.TemporaryDirectory(prefix='rcpm-public-build-') as temporary:
        work = Path(temporary)
        tool(tools, 'mkfs.cpm', '-f', 'z80pack-hd', staged)
        with staged.open('r+b') as disk:
            disk.truncate(255 * 128 * 128)
        removed_bytes = []
        for name in source_names:
            path = work / name
            tool(tools, 'cpmcp', '-f', 'ibm-3740', original, '0:' + name, path)
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if name in EXTERNAL_FILES:
                excluded[name] = digest
                removed_bytes.append(data)
                continue
            tool(tools, 'cpmcp', '-f', 'z80pack-hd', staged, path, '0:' + name)
            readback = work / 'readback'
            tool(tools, 'cpmcp', '-f', 'z80pack-hd', staged, '0:' + name, readback)
            if readback.read_bytes() != data:
                raise ValueError('Public BUILD readback mismatch: ' + name)
            readback.unlink()
            retained[name] = digest
        # Reconstructing a fresh image also removes deleted-file contents;
        # directory deletion alone would leave the excluded programs on disk.
        raw = staged.read_bytes()
        if any(data in raw for data in removed_bytes):
            raise ValueError('Excluded program bytes remain in public BUILD image')
    staged.chmod(0o444)
    staged.replace(target)
    (offline / 'README.txt').write_text(
        'BUILD.dsk contains the retained CP/M development files.\n'
        'Microsoft M80/L80 and MicroPro WM (including WM.HLP) are not bundled as build tools.\n'
        'Builders supply the original pinned toolchain disk separately.\n'
        'The runtime does not require those tools. See source/BUILDING.DOC.\n'
        'Keep private operator development media outside the MOUNT collection.\n')
    report = dict(format='rcpm-development-media-1',
                  policy='legacy-development-tools-supplied-by-builder',
                  source_disk_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                  excluded=excluded, retained=retained,
                  build_image_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                  rebuilt_from_fresh_image=True)
    (Path(output) / 'metadata/DEVELOPMENT-MEDIA.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def verify_public_development_media(output, tools):
    """Read back release media and reject the unfiltered source-disk copy."""
    output = Path(output)
    report = json.loads((output / 'metadata/DEVELOPMENT-MEDIA.json').read_text())
    if report['format'] != 'rcpm-development-media-1' or set(report['excluded']) != set(EXTERNAL_FILES):
        raise ValueError('Unsupported development-media separation receipt')
    if (output / STOCK_BUILD_DISK).exists():
        raise ValueError('Unfiltered stock development disk was included in package sources')
    image = output / 'disks/library/offline/BUILD.dsk'
    if hashlib.sha256(image.read_bytes()).hexdigest() != report['build_image_sha256']:
        raise ValueError('Public BUILD image differs from its receipt')
    actual = names(tools, image, 'z80pack-hd')
    if set(actual) & set(EXTERNAL_FILES) or set(actual) != set(report['retained']):
        raise ValueError('Unexpected files on public BUILD image')
    with tempfile.TemporaryDirectory(prefix='rcpm-build-readback-') as temporary:
        for name, digest in report['retained'].items():
            path = Path(temporary) / name
            tool(tools, 'cpmcp', '-f', 'z80pack-hd', image, '0:' + name, path)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('Retained development file changed: ' + name)
    return report
