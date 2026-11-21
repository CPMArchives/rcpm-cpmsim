"""Install authored HELPC plain-text topics on fresh, stopped staging media."""
from pathlib import Path
import subprocess
import tempfile


def install(instance, tools):
    topics = Path(__file__).resolve().parent / 'guest/help'
    image = Path(instance) / 'disks/drivei.dsk'
    installed = []
    with tempfile.TemporaryDirectory(prefix='rcpm-help-') as temporary:
        for topic in sorted(topics.glob('*.HLP')):
            text = topic.read_text(encoding='ascii')
            # HELPC's plain-text format begins with a semicolon line, as in
            # the preserved HLPFILES.LBR/MENU.HLP. Keep each topic one page.
            if not text.startswith(';\n') or len(text.splitlines()) > 20:
                raise ValueError('Invalid or oversized HELP topic: ' + topic.name)
            if any(len(line) > 78 for line in text.splitlines()):
                raise ValueError('HELP line too long: ' + topic.name)
            data = text.replace('\n', '\r\n').encode('ascii') + b'\x1a'
            data += b'\x1a' * (-len(data) % 128)
            stage = Path(temporary) / topic.name
            stage.write_bytes(data)
            def tool(name, *args):
                subprocess.run([str(Path(tools)/name), *map(str,args)],
                               check=True, capture_output=True)
            tool('cpmrm', '-f', 'z80pack-hd', image, '14:'+topic.name)
            tool('cpmcp', '-f', 'z80pack-hd', image, stage, '14:'+topic.name)
            check = Path(temporary) / 'readback'
            tool('cpmcp', '-f', 'z80pack-hd', image, '14:'+topic.name, check)
            if check.read_bytes() != data:
                raise ValueError('HELP readback mismatch: ' + topic.name)
            check.unlink()
            installed.append(topic.name)
    return installed
