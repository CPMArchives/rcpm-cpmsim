#!/usr/bin/env python3
"""Build unpacked GAMES and documentation-only GUIDES J: images."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

# Retain the existing collection slots without renaming historical members.
# Future games should share category/runtime areas when filenames permit;
# a new game does not require a new user area. SIGMV001 remains excluded.
GAME_SETS = (
    (1, 11, ('ADV.COM', 'ADVI.DAT', 'ADVI.PTR', 'ADVT.DAT', 'ADVT.PTR'),
     'Expanded Adventure: compiled game and runtime data'),
    (8, 134, ('ANIMALS.COM', 'BEASTS.QQQ', 'BEASTS.QQX'),
     'Animals: compiled game and seed data'),
    (3, 228, ('MCHASE.COM', 'MCHASE.DOC', 'MCHASE.HLP'),
     'Maze Chase: compiled game and playing instructions'),
)


def library_members(data):
    """Read record-aligned LU libraries without interpreting member paths."""
    if len(data) < 128 or data[0] != 0 or data[1:12] != b' ' * 11:
        raise ValueError('Invalid LU library header')
    limit = int.from_bytes(data[14:16], 'little') * 128
    if limit < 128 or limit > len(data):
        raise ValueError('Invalid LU library directory length')
    seen = set()
    for k in range(32, limit, 32):
        entry = data[k:k+32]
        if entry[0] in (0xfe, 0xff):
            continue
        if entry[0] != 0:
            raise ValueError('Invalid LU member status')
        stem = entry[1:9].decode('ascii').rstrip()
        ext = entry[9:12].decode('ascii').rstrip()
        name = stem + ('.' + ext if ext else '')
        offset = int.from_bytes(entry[12:14], 'little') * 128
        size = int.from_bytes(entry[14:16], 'little') * 128
        if not stem or name in seen or offset < limit or offset + size > len(data):
            raise ValueError('Invalid or duplicate LU member: ' + name)
        seen.add(name)
        yield name, data[offset:offset+size]


def unpack(data, source, depth=0):
    if depth > 8:
        raise ValueError('Excessively nested game library')
    for name, content in library_members(data):
        origin = source + '/' + name
        if name.endswith('.LBR'):
            yield from unpack(content, origin, depth + 1)
        else:
            # Historical SIG/M.LIB is a CP/M filename, not a host subdirectory.
            target = name.replace('/', '')
            if not target or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&'()-@^_`{}~.+" for c in target):
                raise ValueError('Unsupported game filename: ' + name)
            yield target, content, origin


def install_member(tools, image, work, user, name, content, pad=True):
    if pad:
        content += b'\x1a' * (-len(content) % 128)
    path = work / 'member.bin'
    path.write_bytes(content)
    subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd', str(image),
                    str(path), str(user) + ':' + name], check=True)
    check = work / 'check.bin'
    subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd', str(image),
                    str(user) + ':' + name, str(check)], check=True)
    if check.read_bytes() != content:
        raise ValueError('GAMES member readback mismatch: ' + name)
    check.unlink()
    return content


def build(sigm, tools, output, terminal_patch=None, launcher_dir=None):
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    image = output / 'GAMES.dsk'
    subprocess.run([str(tools / 'mkfs.cpm'), '-f', 'z80pack-hd', str(image)], check=True, capture_output=True)
    with image.open('r+b') as stream:
        stream.truncate(255 * 128 * 128)
    text = ['RCP/M GAMES - playable games', '',
            'J0: contains the guide and launchers; game files use J1: and above.',
            'Only compiled games, required data and playing instructions are included.',
            'SIGMV001 is omitted. SIGMV152 was not a game and is omitted.', '',
            'Compiled games:',
            'J1:ADV.COM     Expanded Adventure, with its four runtime data files.',
            'J8:ANIMALS.COM Animals, with BEASTS seed files; requires writable data.',
            'J3:MCHASE.COM  Maze Chase; read MCHASE.DOC for terminal installation.', '',
            'Inspect a game area: DIR J1:',
            'Download a file: YSEND J1:ADV.COM', '',
            'After MOUNT GAMES, use J0:ADVENT, J0:ANIMALS or J0:MCHASE.',
            'The fixed launchers copy seed data to WORK and run approved J: code.',
            'Saves/high scores in WORK last for this call only.',
            'WORK remains non-executable. Other programs require sysop approval.',
            'Do not run setup or save games on this read-only master.']
    with tempfile.TemporaryDirectory(prefix='j-volumes-') as temporary:
        work = Path(temporary)
        for user, number, selected, description in GAME_SETS:
            filename = f'SIGMV{number:03}.LBR'
            source = sigm / filename
            data = source.read_bytes()
            original = dict(library_members(data))
            if selected is not None:
                missing = set(selected) - set(original)
                if missing:
                    raise ValueError('Missing selected game members: ' + repr(missing))
            seen = set()
            for name, content in original.items():
                if selected is not None and name not in selected:
                    continue
                items = unpack(content, filename + '/' + name) if name.endswith('.LBR') else [(name.replace('/', ''), content, filename + '/' + name)]
                for target, payload, origin in items:
                    if target in seen:
                        raise ValueError('Unpacked filename collision: ' + target)
                    seen.add(target)
                    original_digest = hashlib.sha256(payload).hexdigest()
                    if user == 3 and target == 'MCHASE.COM' and terminal_patch is not None:
                        patched = bytearray(payload)
                        if patched[0x7f:0x82] != bytes([4, 27, 61]) or len(patched) > 0x62a0:
                            raise ValueError('Unexpected Maze Chase terminal patch layout')
                        patched[0x5a1:0x5a4] = bytes([0xc3, 0xa0, 0x63])
                        patched[0xb8:0xbd] = bytes([4, 27, 91, 50, 74])
                        patched += bytes(0x62a0-len(patched)) + terminal_patch.read_bytes()
                        payload = bytes(patched)
                    payload = install_member(tools, image, work, user, target, payload)
                    if (user, target) in ((1, 'ADV.COM'), (8, 'ANIMALS.COM'), (3, 'MCHASE.COM')):
                        subprocess.run([str(tools / 'cpmchattr'), '-f', 'z80pack-hd', str(image),
                                        'r4', f'{user}:{target}'], check=True)
                    rows.append(dict(volume='GAMES', user=user, file=target,
                                     sha256=hashlib.sha256(payload).hexdigest(),
                                     original_sha256=original_digest,
                                     source=origin, library_sha256=hashlib.sha256(data).hexdigest(),
                                     description=description))
        if terminal_patch is not None:
            note = (b'MCHASE.COM has the documented cursor hook adapted to ANSI/VT100.\r\n'
                    b'Original source/archive material is kept in the separate archives.\r\n'
                    b'MCHASE.DOC and MCHASE.HLP are unchanged. CPU setting remains 4 MHz.\r\n\x1a')
            data = install_member(tools, image, work, 3, 'ANSI.TXT', note)
            rows.append(dict(volume='GAMES', user=3, file='ANSI.TXT',
                             sha256=hashlib.sha256(data).hexdigest(), description='Terminal adaptation notes'))
        if launcher_dir is not None:
            for name in ('ADVENT', 'ANIMALS', 'MCHASE'):
                data = install_member(tools, image, work, 0, name + '.COM',
                                      (launcher_dir / (name + '.COM')).read_bytes(), pad=False)
                subprocess.run([str(tools / 'cpmchattr'), '-f', 'z80pack-hd',
                                str(image), 'r4', '0:' + name + '.COM'], check=True)
                rows.append(dict(volume='GAMES', user=0, file=name + '.COM',
                                 sha256=hashlib.sha256(data).hexdigest(),
                                 description='WORK-data preparation launcher; no A0 copy'))
        else:
            text[2] = 'J0: contains this guide; game files use J1: and above.'
            text = [line for line in text if not line.startswith(
                    ('After MOUNT GAMES, use ', 'The fixed launchers copy '))]
            text.append('Online preparation launchers are not included in this standalone build.')
        document = ('\r\n'.join(text) + '\r\n\x1a').encode('ascii')
        for name, data in (('README.TXT', document), ('-GAMES', b'\x1a')):
            data = install_member(tools, image, work, 0, name, data)
            rows.append(dict(volume='GAMES', user=0, file=name,
                             sha256=hashlib.sha256(data).hexdigest(), description='Volume guide'))
    image.chmod(0o600)
    # Public documentation volume: no compiler, interpreter or executable files.
    image = output / 'GUIDES.dsk'
    subprocess.run([str(tools / 'mkfs.cpm'), '-f', 'z80pack-hd', str(image)], check=True, capture_output=True)
    with image.open('r+b') as stream:
        stream.truncate(255 * 128 * 128)
    repo = Path(__file__).resolve().parent
    guide = ("RCP/M GUIDES\r\n\r\n"
             "This volume contains documentation only.\r\n"
             "LT J:COMMANDS.TXT shows the caller command guide.\r\n"
             "LT J:DIR.TXT reads SD's original manual; LDIR.TXT covers libraries.\r\n"
             "Some original SD options require sysop privileges here.\r\n"
             "P0:SIGM has SIGMV001 through SIGMV310.LBR.\r\n"
             "P1:CPMUG has CPMUG001 through CPMUG093.LBR.\r\n"
             "Example: LDIR SIGM:SIGMV001\r\n"
             "Example: LT SIGM:SIGMV001 -CATALOG.001\r\n"
             "YSEND SIGM:SIGMV001.LBR downloads using YMODEM.\r\n"
             "GAMES is a separate themed volume: MOUNT GAMES.\r\n"
             "Caller programs load from protected A0:, including when WORK is current.\r\n"
             "Additional protected-media programs require sysop F4 approval in a caller-read-only DU.\r\n"
             "WORK remains non-executable. MOUNT GAMES then J0:ADVENT, J0:ANIMALS or J0:MCHASE.\r\n\x1a").encode('ascii')
    documents = {'README.TXT': guide, '-GUIDES': b'\x1a',
                 'COMMANDS.TXT': (repo / 'guest/welcome.txt').read_bytes(),
                 'DIR.TXT': (repo / 'build/ztools/sd137/sd.doc.txt').read_bytes(),
                 'LDIR.TXT': (repo / 'build/ztools/ldirb15/ldir-b.doc.txt').read_bytes()}
    with tempfile.TemporaryDirectory(prefix='guides-') as temporary:
        for filename, data in documents.items():
            data += b'\x1a' * (-len(data) % 128)
            path = Path(temporary) / filename
            path.write_bytes(data)
            subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd', str(image), str(path), '0:' + filename], check=True)
            readback = Path(temporary) / 'verify.bin'
            subprocess.run([str(tools / 'cpmcp'), '-f', 'z80pack-hd', str(image), '0:' + filename, str(readback)], check=True)
            if readback.read_bytes() != data:
                raise ValueError('GUIDES readback mismatch: ' + filename)
            readback.unlink()
            rows.append(dict(volume='GUIDES', file=filename, sha256=hashlib.sha256(data).hexdigest(), description='Public documentation'))
    image.chmod(0o600)
    (output / 'volumes.json').write_text(json.dumps(rows, indent=2) + '\n')
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sigm', type=Path, required=True)
    p.add_argument('--tools', type=Path, default=Path('build/cpmtools/bin'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--launchers', type=Path, help='Built game-launcher directory for J0:')
    args = p.parse_args()
    rows = build(args.sigm.resolve(), args.tools.resolve(), args.output.resolve(),
                 launcher_dir=args.launchers.resolve() if args.launchers else None)
    print('Built GAMES and GUIDES:', len(rows), 'verified files')
