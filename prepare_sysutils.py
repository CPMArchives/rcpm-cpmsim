"""Build a small SYSUTILS B: and an offline 4-MB BUILD disk."""
import subprocess


PRIVATE = (
    'BYEBYE.COM', 'SID.COM', 'DUMP.COM', 'HEXCOM.COM', 'SAVE.COM',
    'GENCOM.COM', 'PIP.COM', 'ERASE.COM', 'RENAME.COM', 'SET.COM',
    'DEVICE.COM', 'PUT.COM', 'RESET.COM', 'SETDEF.COM',
    'HIST.COM', 'HIST.UTL', 'HISTCL.COM', 'TRACE.UTL', 'SHOW.COM', 'ZSHOW.COM',
)


def prepare_sysutils(source, tools, instance, work):
    def tool(name, *args, capture=False):
        return subprocess.run([str(tools / name), *map(str, args)], check=True,
                              stdout=subprocess.PIPE if capture else None)
    a = instance / 'disks/drivea.dsk'
    b = instance / 'disks/driveb.dsk'
    tool('mkfs.cpm', '-f', 'ibm-3740', b)
    with b.open('r+b') as disk:
        disk.truncate(77 * 26 * 128)
    label = work / 'SYSUTILS.TXT'
    label.write_bytes(b'SYSUTILS: private system maintenance tools.\r\n\x1a')
    tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', b, label, '0:VOLUME.TXT')
    for name in PRIVATE:
        extracted = work / name
        tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', a, '0:' + name, extracted)
        tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', b, extracted, '0:' + name)
        tool('cpmrm', '-T', 'raw', '-f', 'ibm-3740', a, '0:' + name)
    # These were omitted from the crowded trial A: before Z3PLUS was added.
    for name in ('ED.COM', 'DATE.COM'):
        extracted = work / name
        tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740',
             source / 'cpmsim/disks/library/cpm3-1.dsk', '0:' + name, extracted)
        tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', b, extracted, '0:' + name)
    # BUILD is deliberately outside disks/library/: MOUNT cannot discover it.
    offline = instance / 'disks/library/offline'
    offline.mkdir(parents=True, exist_ok=True)
    build = offline / 'BUILD.dsk'
    tool('mkfs.cpm', '-f', 'z80pack-hd', build)
    with build.open('r+b') as disk:
        disk.truncate(255 * 128 * 128)
    original = source / 'cpmsim/disks/library/cpm3-2.dsk'
    listing = tool('cpmls', '-f', 'ibm-3740', original, capture=True).stdout.decode()
    for line in listing.splitlines():
        name = line.strip()
        if not name or name.endswith(':'):
            continue
        extracted = work / ('build-' + name)
        tool('cpmcp', '-T', 'raw', '-f', 'ibm-3740', original, '0:' + name, extracted)
        tool('cpmcp', '-T', 'raw', '-f', 'z80pack-hd', build, extracted, '0:' + name)
    build.chmod(0o444)
    (offline / 'README.txt').write_text(
        'BUILD.dsk contains original CP/M 3 development/build files.\n'
        'Keep it offsite in normal operation. It is not in the MOUNT collection.\n'
        'When needed between calls, copy it into disks/library/, mount BUILD on J:,\n'
        'then restore a public volume and remove BUILD from disks/library/.\n')
