#!/usr/bin/env python3
"""Build RBBS 4.1 Edit 02 with BDS C's supplied 1.50 compatibility library."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pty
import re
import select
import shutil
import subprocess
import time
import tty
import zipfile


class Machine:
    def __init__(self, root, runtime, log, env=None, speed='0'):
        self.master, slave = pty.openpty()
        tty.setraw(slave)
        self.log = open(log, 'wb')
        clean = {k: v for k, v in os.environ.items() if not k.startswith('RCPM_')}
        clean.update(env or {})
        self.proc = subprocess.Popen([str(runtime), '-f', speed], cwd=root,
                                     env=clean, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)

    def read(self, marker, timeout=45):
        data = bytearray()
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if select.select([self.master], [], [], .05)[0]:
                part = os.read(self.master, 65536)
                self.log.write(part)
                self.log.flush()
                data.extend(part)
                if marker in data:
                    return bytes(data)
        raise RuntimeError('Timeout waiting for %r: %r' % (marker, data[-2000:]))

    def command(self, command, prompt=b'I>'):
        print(command, flush=True)
        os.write(self.master, command.encode('ascii') + b'\r')
        data = self.read(prompt, 60)
        if re.search(rb'(?i)(undefined|error|not found|out of memory|missing|unmatched|bad constant|aborted|overflow|overlap)', data):
            raise RuntimeError(data.decode('ascii', 'replace'))
        return data

    def close(self):
        self.proc.terminate()
        try:
            self.proc.wait(3)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        os.close(self.master)
        self.log.close()


def text(data):
    return data.split(b'\x1a')[0].decode('ascii').replace('\r\n', '\n')


def configure(files):
    h = files['RBBS4.H']
    settings = dict(NEWFLAG="'+'", PCREND='TRUE', LASTREAD='FALSE',
                    LASTWRITE='FALSE', HANGUP='TRUE', HANG='"BYE"',
                    CHAINEXIT='FALSE', DATETIME='FALSE', ZONE='"TST"',
                    DRIVE='"15/I:"', SYSITE='"Chiayi, Taiwan"')
    for name, value in settings.items():
        h, n = re.subn(r'(?m)^(#define\s+' + name + r'\s+)(?:"[^"\n]*"|\S+)',
                       lambda m: m[1] + value, h)
        if n != 1:
            raise ValueError('Unexpected configuration: ' + name)
    h = h.replace('"15/A:fn"', '"15/I:fn"')
    files['RBBS4.H'] = h
    # The board is entered afresh through our fixed public launcher.
    files['RBBS4.C'] = files['RBBS4.C'].replace("rflg = peek(0x5d);", "rflg = ' ';")
    files['RBBS4.C'] = files['RBBS4.C'].replace('while ( (!choice) || (choice > n) )',
        'while ( (choice < 1) || (choice > n) || (choice > 8) )')
    files['UTILFN.C'] = files['UTILFN.C'].replace('sscanf(rec,"%d",&n);\n\tdispl_subj',
        'sscanf(rec,"%d",&n);\n\tif (n >= 8) { close(fd); outstr("Eight areas maximum.",2); return; }\n\tdispl_subj')
    files['LOGON.C'] = files['LOGON.C'].replace('char\tplace[SITELGTH];',
                                                               'char\tplace[SITELGTH+1];')
    # Use the identical CP/M 3 named-RSX logout request as B5ENTRY.ASM.
    # The old C library's CP/M 2 executable loader is unsuitable here.
    files['RBBSFN.C'] = files['RBBSFN.C'].replace('hexit()\n{',
        'hexit()\n{\n\tint request[3];\n\tchar args[2];')
    files['RBBSFN.C'] = files['RBBSFN.C'].replace('exec(HANG);',
        'args[0]=args[1]=0;\n\trequest[0]=0x0266;\n'
        '\trequest[1]="BYE5    ";\n\trequest[2]=args;\n\tbdos(60,request);')
    # Read the CP/M 3 clock instead of asking every visitor to set a date.
    start = files['RBBSFN.C'].index('get_date()')
    end = files['RBBSFN.C'].index('displ_subj(fd,n,rec)', start)
    files['RBBSFN.C'] = files['RBBSFN.C'][:start] + '''get_date()
{
    char stamp[5];
    unsigned days;
    int year, month, leap, size;
    int lengths[12];
    lengths[0]=31; lengths[1]=28; lengths[2]=31; lengths[3]=30;
    lengths[4]=31; lengths[5]=30; lengths[6]=31; lengths[7]=31;
    lengths[8]=30; lengths[9]=31; lengths[10]=30; lengths[11]=31;
    bdos(105,stamp);
    days=(stamp[0]&255)+((stamp[1]&255)<<8);
    if (days) --days;
    year=1978;
    while (TRUE) {
        leap=(!(year%4) && ((year%100) || !(year%400)));
        size=365+leap;
        if (days<size) break;
        days-=size; ++year;
    }
    month=0;
    while (TRUE) {
        size=lengths[month];
        if (month==1) size+=leap;
        if (days<size) break;
        days-=size; ++month;
    }
    sprintf(sysdate,"%02d/%02d/%02d",month+1,days+1,year%100);
}
/***************************************************************/
''' + files['RBBSFN.C'][end:]
    return files


def build(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    original, configured = out/'original', out/'configured'
    original.mkdir(exist_ok=True)
    configured.mkdir(exist_ok=True)
    with zipfile.ZipFile(args.rbbs) as z:
        files = {Path(n).name: text(z.read(n)) for n in z.namelist()
                 if n.startswith('rbbs4102/') and not n.endswith('/')}
    for name, content in files.items():
        (original/name).write_text(content)
    files = configure(files)
    for name, content in files.items():
        (configured/name).write_bytes(content.replace('\n', '\r\n').encode('ascii') + b'\x1a')
    with zipfile.ZipFile(args.compiler) as z:
        for name in ('CC.COM', 'CC2.COM', 'CLINK.COM', 'C.CCC', 'DEFF.CRL', 'DEFF2.CRL'):
            (configured/name).write_bytes(z.read('bdsc160/' + name))
        for name in ('BDSCIO.H', 'DEFF15.CRL'):
            (configured/name).write_bytes(z.read('extra/' + name))
    machine = out/'machine'
    (machine/'disks').mkdir(parents=True, exist_ok=True)
    (machine/'conf').mkdir(exist_ok=True)
    for kind in ('server', 'client'):
        (machine/f'conf/net_{kind}.conf').write_text('# Offline compiler machine\n')
    shutil.copyfile(args.stock/'cpmsim/disks/library/cpm3-1.dsk', machine/'disks/drivea.dsk')
    def tool(name, *values):
        return subprocess.run([str(args.tools/name), *map(str, values)], check=True,
                              capture_output=True).stdout
    tool('cpmrm', '-f', 'ibm-3740', machine/'disks/drivea.dsk', '0:PROFILE.SUB')
    image = machine/'disks/drivei.dsk'
    tool('mkfs.cpm', '-f', 'z80pack-hd', image)
    for file in configured.iterdir():
        if file.suffix.upper() in ('.C', '.H', '.COM', '.CCC', '.CRL'):
            tool('cpmcp', '-f', 'z80pack-hd', image, file, '0:'+file.name)
    guest = Machine(machine, args.runtime, out/'compile.log')
    try:
        guest.read(b'A>')
        guest.command('I:')
        for name in ('RBBS4', 'MAINOP', 'LOGON', 'ENTER', 'RBBSFN', 'RBBSCIO', 'UTIL', 'UTILFN'):
            guest.command('CC ' + name + ' -e9000')
        guest.command('CLINK RBBS4 -f MAINOP LOGON ENTER RBBSFN RBBSCIO DEFF15 -r 1000')
        guest.command('CLINK UTIL -f UTILFN LOGON MAINOP ENTER RBBSFN RBBSCIO DEFF15 -r 1000')
    finally:
        guest.close()
    for name in ('RBBS4.COM', 'UTIL.COM'):
        tool('cpmcp', '-f', 'z80pack-hd', image, '0:'+name, out/name)
    (out/'BUILD.json').write_text(json.dumps({
        'rbbs_version': '4.1 Edit 02', 'compiler': 'BDS C 1.60 with DEFF15',
        'inputs': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (args.rbbs, args.compiler)},
        'outputs': {n: hashlib.sha256((out/n).read_bytes()).hexdigest()
                    for n in ('RBBS4.COM', 'UTIL.COM')},
    }, indent=2)+'\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rbbs', type=Path, required=True)
    p.add_argument('--compiler', type=Path, required=True)
    p.add_argument('--stock', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--tools', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('build/rbbs41'))
    a = p.parse_args()
    for name in ('stock', 'runtime', 'tools'):
        setattr(a, name, getattr(a, name).resolve())
    build(a)
