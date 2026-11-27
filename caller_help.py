"""Install authored HELPC plain-text topics on fresh, stopped staging media."""
from pathlib import Path
import re
import subprocess
import tempfile


def validate_topics(topics):
    """Validate the authored subset of the HELPC 1.4 text format."""
    names = set(topics)
    for name, text in topics.items():
        lines = text.splitlines()
        if not lines or lines[0] != ';':
            raise ValueError('Invalid HELP header: ' + name)
        if any(len(line) > 78 for line in lines):
            raise ValueError('HELP line too long: ' + name)
        if any(ord(ch) < 32 or ord(ch) > 126
               for line in lines for ch in line):
            raise ValueError('Invalid HELP character: ' + name)
        selections = set()
        menu_lines = 0
        in_section = False
        for line in lines[1:]:
            if line.startswith(':'):
                match = re.fullmatch(r':([A-Z0-9])(?::([A-Z0-9_]{1,8}\.HLP))?', line)
                if not match:
                    raise ValueError('Invalid HELP directive: ' + name + ': ' + line)
                key, target = match.groups()
                if key in selections:
                    raise ValueError('Duplicate HELP selection: ' + name + ': ' + key)
                selections.add(key)
                if target:
                    if in_section:
                        raise ValueError('HELP links must precede sections: ' + name)
                    if target not in names:
                        raise ValueError('Missing HELP target: ' + name + ': ' + target)
                else:
                    in_section = True
            elif not in_section:
                menu_lines += 1
        # HELPC automatically paginates selected information sections.
        # Only the index (or a legacy standalone topic) must fit one screen.
        if menu_lines > 19:
            raise ValueError('Oversized HELP index: ' + name)


def install(instance, tools):
    topics = Path(__file__).resolve().parent / 'guest/help'
    image = Path(instance) / 'disks/drivei.dsk'
    installed = []
    authored = {p.name: p.read_text(encoding='ascii')
                for p in sorted(topics.glob('*.HLP'))}
    validate_topics(authored)
    with tempfile.TemporaryDirectory(prefix='rcpm-help-') as temporary:
        for name, text in authored.items():
            data = text.replace('\n', '\r\n').encode('ascii') + b'\x1a'
            data += b'\x1a' * (-len(data) % 128)
            stage = Path(temporary) / name
            stage.write_bytes(data)
            def tool(name, *args):
                subprocess.run([str(Path(tools)/name), *map(str,args)],
                               check=True, capture_output=True)
            tool('cpmrm', '-f', 'z80pack-hd', image, '14:'+name)
            tool('cpmcp', '-f', 'z80pack-hd', image, stage, '14:'+name)
            check = Path(temporary) / 'readback'
            tool('cpmcp', '-f', 'z80pack-hd', image, '14:'+name, check)
            if check.read_bytes() != data:
                raise ValueError('HELP readback mismatch: ' + name)
            check.unlink()
            installed.append(name)
    return installed
