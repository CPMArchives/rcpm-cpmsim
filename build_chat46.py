#!/usr/bin/env python3
"""Build preserved CHAT46 for HUMONGOUS using native CP/M M80/L80."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from build_rbbs41 import Machine

SOURCE_SHA256 = 'a24acfd30bd2ad67d050b8bf22a1e7c410cc451db03fa1b8aa053db5a2e827a2'


def configure(text):
    # RBBS is optional; CHAT must work at the ordinary CP/M prompt.
    options = dict(NONE='YES', MBBS='NO', GETCALR='NO', BYBELL='YES',
                   LMBELL='NO', COMMENT='NO', TIMEON='NO', TGUIDE='NO')
    for name, value in options.items():
        text, n = re.subn(r'(?m)^(' + name + r'\s+EQU\s+)\S+',
                         lambda m: m[1] + value, text)
        if n != 1:
            raise ValueError('Unexpected CHAT option: ' + name)
    def change(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError('Unexpected CHAT display context: '+old[:50])
        text = text.replace(old, new)
    start = text.index('CHAT:\tCALL\tILPRT')
    end = text.index(';\n', start)
    text = text[:start] + """CHAT:   CALL ILPRT
        DB CR,LF
        DB '+--------------------------------------------------------+',CR,LF
        DB '|                 HUMONGOUS RCP/M CHAT                   |',CR,LF
        DB '+--------------------------------------------------------+',CR,LF,LF,0
""" + text[end:]
    change("\tDB\t'will page the operator (abort with ^C or ^X)',CR,LF\n\tDB\tCR,LF,LF,0",
           "        DB 'Paging the sysop. Please wait...',CR,LF\n"
           "        DB 'Cancel: Ctrl-C or Ctrl-X',CR,LF\n"
           "        DB 'Sysop: press Esc on the local console to answer.',CR,LF,LF,0")
    change("\tDB\tCR,LF,LF,'Sorry, operator is not available.',0",
           "        DB CR,LF,LF,'The sysop is not available. Try again later.',CR,LF,0")
    change("\tDB\tCR,LF,LF,'Back to CP/M...',0", "        DB CR,LF,0")
    change("\tDB\t'Operator is available, please go ahead...',CR,LF\n"
           "\tDB\t'(Use ^C or ^X to exit and return to CP/M)',CR,LF\n\tDB\tLF,0",
           "        DB '+-------------------- CHAT CONNECTED --------------------+',CR,LF\n"
           "        DB 'Take turns typing. Ctrl-C or Ctrl-X ends the conversation.',CR,LF\n"
           "        DB '----------------------------------------------------------',CR,LF,0")
    change('EXIT1:\n', "EXIT1: CALL ILPRT\n"
           "        DB CR,LF,'----------------------------------------------------------',CR,LF\n"
           "        DB 'Returning to CP/M.',CR,LF,0\n")
    # M80 needs an absolute segment for this ORG 100h transient.
    return '\tASEG\n' + text


def build(a):
    data = a.reference.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError('CHAT46 reference hash mismatch')
    a.output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(a.reference, a.output/'chat46-original.asm')
    configured = configure(data.decode('ascii').replace('\r\n', '\n'))
    mac = a.output/'CHAT.MAC'
    mac.write_bytes(configured.replace('\n', '\r\n').encode('ascii') + b'\x1a')
    machine = a.output/'machine'
    (machine/'disks').mkdir(parents=True)
    (machine/'conf').mkdir()
    for kind in ('server', 'client'):
        (machine/f'conf/net_{kind}.conf').write_text('# Offline CHAT build\n')
    for drive, name in (('a', 'cpm3-1.dsk'), ('b', 'cpm3-2.dsk')):
        shutil.copyfile(a.stock/'cpmsim/disks/library'/name, machine/f'disks/drive{drive}.dsk')
    def tool(name, *args):
        return subprocess.run([str(a.tools/name), *map(str,args)], check=True, capture_output=True)
    tool('cpmrm', '-f', 'ibm-3740', machine/'disks/drivea.dsk', '0:PROFILE.SUB')
    image = machine/'disks/drivei.dsk'
    tool('mkfs.cpm', '-f', 'z80pack-hd', image)
    tool('cpmcp', '-f', 'z80pack-hd', image, mac, '0:CHAT.MAC')
    guest = Machine(machine, a.runtime, a.output/'build.log')
    try:
        guest.read(b'A>')
        for cmd in ('I:', 'B:M80 =CHAT', 'B:L80 CHAT,CHAT/N/E'):
            print(cmd, flush=True)
            os.write(guest.master, cmd.encode()+b"\r")
            result = guest.read(b"I>")
            checked = result.upper().replace(b"NO FATAL ERROR(S)", b"")
            if any(x in checked for x in (b"ERROR", b"UNDEFINED", b"NO FILE")):
                raise RuntimeError(result.decode(errors="replace"))
    finally:
        guest.close()
    tool('cpmcp', '-f', 'z80pack-hd', image, '0:CHAT.COM', a.output/'CHAT.COM')
    (a.output/'BUILD.json').write_text(json.dumps(dict(
        reference_sha256=SOURCE_SHA256, clock_mhz=4, page_seconds=30,
        time_limit=False, bell='BYE BDOS 78',
        configured_sha256=hashlib.sha256(mac.read_bytes()).hexdigest(),
        executable_sha256=hashlib.sha256((a.output/'CHAT.COM').read_bytes()).hexdigest(),
        executable_bytes=(a.output/'CHAT.COM').stat().st_size), indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('reference', 'stock', 'tools', 'runtime', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    build(argparse.Namespace(**{k:v.resolve() for k,v in vars(a).items()}))
