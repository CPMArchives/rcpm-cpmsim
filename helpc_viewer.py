"""Require the locally supplied qualified-link viewer on stopped build media.

No historical HELPC source or executable is distributed by this module.
"""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import tempfile

QUALIFIED_SHA = '04d930c738cbfcfd3b1de3280a82d36991522ade0717ede740c83118869f01b4'
KNOWN = {
    '9780340ad55ee2b6abaeee5f08c123948cfc3f6367915d06c212453fdb149ca9',
    'a1d31e69be1320d64e1960eee56142ed2b1c4f9de9c157f7b99bf56c6afad58b',
    '8f496fd2f008b1a41156797b3f9be428771449508e26cb00be2acb5305398baf',
    '10402d5c81705b3a127617ca52a2fa0c7d2c90a997c7ab8969d7ad15ba83e77e',
    QUALIFIED_SHA,
}
TARGETS = [('drivea.dsk', 'ibm-3740', '0:HELP.COM'),
           ('drivei.dsk', 'z80pack-hd', '13:ZHELP.COM')]


def code_hash(data):
    """Ignore documented local configuration slots, including the version tag."""
    if len(data) < 42 or data[3:9] != b'Z3ENV\x01':
        raise ValueError('Not a recognized HELPC Z-System executable')
    data = bytearray(data)
    data[11:42] = bytes(31)
    return hashlib.sha256(data).hexdigest()


def ensure_qualified_viewer(instance, tools, viewer=None):
    """Validate both viewers or install a local 1.5r input on staging copies.

    Caller must own fresh, stopped build media. Live systems use the separate
    guarded local updater. Configuration and executable attributes are retained.
    """
    supplied = viewer or os.environ.get('RCPM_HELPC_VIEWER')
    candidate = Path(supplied).expanduser().read_bytes() if supplied else None
    if candidate is not None and code_hash(candidate) != QUALIFIED_SHA:
        raise ValueError('RCPM_HELPC_VIEWER must be the tested local HELPC 1.5r')
    instance = Path(instance)
    with tempfile.TemporaryDirectory(prefix='.helpc-build-', dir=instance) as directory:
        work = Path(directory)
        def tool(name, *args):
            return subprocess.run([str(Path(tools)/name), *map(str, args)],
                                  check=True, capture_output=True).stdout
        changes = []
        for image_name, fmt, spec in TARGETS:
            image = instance/'disks'/image_name
            original = work/('old-'+image_name+'.com')
            tool('cpmcp', '-f', fmt, image, spec, original)
            old = original.read_bytes()
            actual = code_hash(old)
            if actual == QUALIFIED_SHA:
                continue
            if candidate is None:
                raise ValueError('Qualified HELP links require local HELPC 1.5r at '
                                 + spec + '. Set RCPM_HELPC_VIEWER to your private '
                                 'HELPC15.COM build input before assembling staging media.')
            if actual not in KNOWN:
                raise ValueError('Refusing to replace code-modified HELPC: '+spec)
            listing = tool('cpmls', '-A', '-f', fmt, image, spec).decode('ascii')
            rows = [line.split()[0] for line in listing.splitlines()
                    if re.match(r'^[-1234sarw]{9}\s', line)]
            if len(rows) != 1 or rows[0][6:] != '---':
                raise ValueError('Unsupported HELPC attributes: '+spec)
            attrs = rows[0]
            modes = tool('cpmls', '-l', '-f', fmt, image, spec).decode('ascii')
            modes = [line.split()[0] for line in modes.splitlines() if line.startswith('-')]
            if len(modes) != 1:
                raise ValueError('Cannot determine HELPC read-only mode: '+spec)
            readonly = 'w' not in modes[0]
            data = bytearray(candidate)
            data[11:13] = old[11:13]
            data[21:42] = old[21:42]
            staged = work/image_name
            shutil.copy2(image, staged)
            tool('cpmchattr', '-f', fmt, staged, 'mr', spec)
            tool('cpmrm', '-f', fmt, staged, spec)
            replacement = work/'replacement.com'
            replacement.write_bytes(data)
            tool('cpmcp', '-f', fmt, staged, replacement, spec)
            flags = 'N'+''.join(c for c in attrs[:6] if c != '-')+('r' if readonly else '')
            tool('cpmchattr', '-f', fmt, staged, flags, spec)
            readback = work/'readback.com'
            readback.unlink(missing_ok=True)
            tool('cpmcp', '-f', fmt, staged, spec, readback)
            if readback.read_bytes() != data:
                raise ValueError('HELPC staging readback failed: '+spec)
            changes.append((image, staged))
        # Do not touch either original until every candidate has been validated.
        # A failed second rename is recoverable even on disposable build media.
        saved = []
        try:
            for image, staged in changes:
                backup = work/(image.name+'.original')
                shutil.copy2(image, backup)
                saved.append((image, backup))
                os.replace(staged, image)
        except BaseException:
            for image, backup in saved:
                os.replace(backup, image)
            raise
