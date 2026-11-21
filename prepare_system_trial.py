#!/usr/bin/env python3
"""Prepare fresh I13:SYSUTLS / I14:HELP / I15:RBBS media; never edit a live trial."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from prepare_shared_trial import create
from prepare_rbbs_trial import install, references
from prepare_z3plus import configure_library, configure_startup
from rbbs_entry import public_entry
from system_attributes import apply as apply_attributes
from shared_instance import write_helpers

REPO = Path(__file__).resolve().parent


def upper_layout(instance, tools, romwbw, ppip):
    """Only used on a newly built, unbooted instance inside a staging directory."""
    a, b, i = (instance / f'disks/drive{drive}.dsk' for drive in 'abi')
    manifest_path = instance / 'trial-build.json'
    manifest = json.loads(manifest_path.read_text())
    build = json.loads((Path(manifest['builds']) / 'build-result.json').read_text())
    if not build.get('upper_areas'):
        raise ValueError('Rebuild BYE with the I13/I14/I15 protections first')
    ppip_result = json.loads((ppip / 'build-result.json').read_text())
    ppip_file = ppip / 'PPIP.COM'
    if (not ppip_result['zcpr3'] or ppip_result['datestamper'] or ppip_result['z80dos']
            or hashlib.sha256(ppip_file.read_bytes()).hexdigest() != ppip_result['sha256']):
        raise ValueError('Expected the verified Z3PLUS PPIP build without foreign timestamps')
    def tool(name, *args):
        return subprocess.run([str(tools / name), *map(str, args)], check=True,
                              capture_output=True).stdout
    def put(disk, fmt, user, name, data, replace=False):
        temporary = instance / '.system-file'
        temporary.write_bytes(data)
        try:
            if replace:
                tool('cpmrm', '-f', fmt, disk, f'{user}:{name}')
            tool('cpmcp', '-f', fmt, disk, temporary, f'{user}:{name}')
        finally:
            temporary.unlink(missing_ok=True)
    # Import every private B0: file, retaining stock PIP and RBBS management.
    with tempfile.TemporaryDirectory(dir=instance) as temporary:
        work = Path(temporary)
        # GET is CP/M 3's input-redirection utility. Initialization runs before
        # caller restrictions are enabled, so it can live with private tools.
        target = work / 'GET.COM'
        tool('cpmcp', '-f', 'ibm-3740', a, '0:GET.COM', target)
        get_data = target.read_bytes()
        put(i, 'z80pack-hd', 13, 'GET.COM', get_data)
        verified = work / 'GET-CHECK.COM'
        tool('cpmcp', '-f', 'z80pack-hd', i, '13:GET.COM', verified)
        if verified.read_bytes() != get_data:
            raise ValueError('GET relocation verification failed')
        put(a, 'ibm-3740', 0, 'STARTZ3P.COM',
            configure_startup(romwbw / 'Source/Images/d_z3plus/u0/STARTZ3P.COM',
                              'A0:PATH /C A0;I13:GET CONSOLE;A0:;A0:BYE'), replace=True)
        tool('cpmrm', '-f', 'ibm-3740', a, '0:GET.COM')
        listing = tool('cpmls', '-f', 'ibm-3740', b).decode()
        for line in listing.splitlines():
            name = line.strip()
            if not name or name.endswith(':'):
                continue
            target = work / name
            tool('cpmcp', '-f', 'ibm-3740', b, '0:' + name, target)
            put(i, 'z80pack-hd', 13, name, target.read_bytes())
        # The IBM3740 disk has sector skew; use cpmtools rather than treating
        # its on-disk directory as a contiguous logical byte array.
        for name in ('RBBS37.COM', 'BYE.COM', 'MENURBBS', 'HELP', 'NEWS', 'TWIT',
                     'INFO', 'BULLETIN', 'NEWCOM', 'ENTERCPM', 'BOOTPWD'):
            target = work / name
            tool('cpmcp', '-f', 'ibm-3740', a, '2:' + name, target)
            put(a, 'ibm-3740', 15, name, target.read_bytes())
            tool('cpmrm', '-f', 'ibm-3740', a, '2:' + name)
    # Raw directory user-byte relocation preserves all filenames (including
    # RBBS's deliberately lowercase pwds) and all data/extent allocations.
    for disk, directory_start, count in ((i, 0, 1024),):
        with disk.open('r+b') as stream:
            stream.seek(directory_start)
            directory = bytearray(stream.read(count * 32))
            if any(directory[n] == 15 for n in range(0, len(directory), 32)):
                raise ValueError('Fresh RBBS destination user area is not empty')
            for offset in range(0, len(directory), 32):
                if directory[offset] == 2:
                    directory[offset] = 15
            stream.seek(directory_start)
            stream.write(directory)
    base = romwbw / 'Source/Images/d_z3plus/u0'
    library = configure_library(base / 'Z3PLUS.LBR', ('SIGM', 'CPMUG'),
                                ((9, 13, 'SYSUTLS'), (9, 14, 'HELP'), (9, 15, 'RBBS')))
    put(a, 'ibm-3740', 0, 'Z3PLUS.LBR', library, replace=True)
    welcome=(REPO/'guest/welcome.txt').read_text().replace('\n','\r\n').encode('ascii')+b'\x1a'
    put(a, 'ibm-3740', 0, 'WELCOME.TXT', welcome)
    # Reviewed caller viewers. Keep the original CP/M utilities privately.
    callers = json.loads((REPO / 'docs/caller-tool-binaries.json').read_text())
    for row in callers:
        source = REPO / row['source'] if row['source'].startswith('build/') else romwbw / row['source']
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Caller tool hash mismatch: ' + str(source))
        if row['name'] in ('DIR.COM', 'HELP.COM'):
            with tempfile.TemporaryDirectory(dir=instance) as temporary:
                old = Path(temporary) / row['name']
                tool('cpmcp', '-f', 'ibm-3740', a, '0:' + row['name'], old)
                put(i, 'z80pack-hd', 13, 'CPM' + row['name'], old.read_bytes())
        put(a, 'ibm-3740', 0, row['name'], data, replace=row['name'] in ('DIR.COM', 'HELP.COM'))
    put(a, 'ibm-3740', 0, 'RBBS.COM', public_entry(romwbw, 15))
    put(i, 'z80pack-hd', 13, 'RBBS.COM',
        configure_startup(base / 'STARTZ3P.COM', 'A15:;A15:RBBS37'), replace=True)
    put(a, 'ibm-3740', 15, 'ENTERCPM',
        b'\r\nReturning to CP/M. BBS data remains on I15:.\r\n\x1a', replace=True)
    put(i, 'z80pack-hd', 13, 'PPIP.COM', ppip_file.read_bytes())
    put(i, 'z80pack-hd', 13, 'PPIP.DOC', (ppip / 'PPIP.DOC').read_bytes())
    rows = json.loads((REPO / 'docs/zsystem-tool-sources.json').read_text())
    for row in rows:
        path = romwbw / 'Source/Images/Common/NZ3PLUS/u15' / row['path']
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Changed Z-System utility: ' + str(path))
        put(i, 'z80pack-hd', 13, row['path'], path.read_bytes(), replace=row['path'] == 'ZSHOW.COM')
    editor_rows=json.loads((REPO/'docs/zde-reference-sources.json').read_text())
    editor_config=json.loads((REPO/'build/sysop-editor/build-result.json').read_text())
    editor_names={'zde16.com':'ZDE.COM','zdenst16.com':'ZDENST.COM',
                  'zde16.lbr':'ZDE16.LBR','zde16.new.txt':'ZDE16.NEW','zde16.for.txt':'ZDE16.FOR'}
    for row in editor_rows:
        data=(REPO/'build/ztools/zde16'/row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Editor source changed: '+row['path'])
        if row['path']=='zde16.com':
            data=(REPO/'build/sysop-editor/ZDE.COM').read_bytes()
            if hashlib.sha256(data).hexdigest()!=editor_config['sha256']:
                raise ValueError('Configured editor hash mismatch')
        put(i,'z80pack-hd',13,editor_names[row['path']],data)
    for disk, fmt, user, name in ((a, 'ibm-3740', 0, 'SYSTEM'),
                                 (i, 'z80pack-hd', 0, 'WORK'),
                                 (i, 'z80pack-hd', 13, 'SYSUTLS'),
                                 (i, 'z80pack-hd', 15, 'RBBS')):
        put(disk, fmt, user, '-' + name, b'\x1a')
    from caller_help import install as install_help
    install_help(instance, tools)
    attributes = apply_attributes(a, tools)
    if build.get('du_authorization'):
        from auth_policy import install as install_auth
        assembler = Path(manifest['source']) / 'z80asm/z80asm'
        install_auth(instance, tools, assembler)
    # B: is no longer runtime media; original build tools remain offline/BUILD.
    b.unlink()
    (instance / 'README.txt').write_text(
        'Fresh single-machine RCP/M trial, raw TCP 127.0.0.1:4002.\n'
        'I13:SYSUTLS is private; I14:HELP contains public read-only caller topics.\n'
        'I15:RBBS is private; I0:WORK is disposable. B: is not used.\n'
        'Local Ctrl-B (twice in tmux) blanks the caller and enables private tools.\n'
        'Callers type RBBS to enter the board; SYSUTLS remains private.\n'
        'PIP and PPIP are private. Use SYSUTLS:BYEBYE to stop the guest.\n'
        'P0:SIGM and P1:CPMUG are reserved; the distributable archive is empty.\n'
        'This is a loopback evaluation; public admission/configuration remain pending.\n')
    manifest.update(upper_areas=True, bbs_data='I15:', sysutils='I13:', help='I14:', public_rbbs=True,
                    zsystem_tools=rows, caller_tools=callers, editor_sources=editor_rows,
                    editor_configuration=editor_config,
                    a0_attributes=attributes,
                    ppip_sha256=ppip_result['sha256'], get_location='I13:')
    manifest['hashes'].pop('disks/driveb.dsk', None)
    manifest['hashes']['disks/drivea.dsk'] = hashlib.sha256(a.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'romwbw', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    for name, default in (('runtime', 'build/modem/cpmsim'), ('builds', 'build/bye5'),
                          ('cpmtools', 'build/cpmtools/bin'), ('ppip', 'build/ppip18'),
                          ('cache', 'build/rbbs37/original')):
        parser.add_argument('--' + name, type=Path, default=Path(default))
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    for name, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, name, value.expanduser().resolve())
    if args.output.exists() or args.output.is_symlink():
        parser.error('Refusing to replace an existing installation')
    references(args.cache, args.fetch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.system-trial-', dir=args.output.parent) as temporary:
        stage = Path(temporary) / 'instance'
        create(args.source, args.romwbw, args.runtime, args.builds, args.cpmtools, stage)
        install(stage, args.cache, args.cpmtools, args.romwbw, args.output)
        upper_layout(stage, args.cpmtools, args.romwbw, args.ppip)
        write_helpers(stage, args.output, REPO)
        (stage / 'README-RBBS.txt').write_text((REPO / 'docs/zsystem-utilities.md').read_text())
        stage.rename(args.output)
    print('Prepared upper-area system:', args.output)


if __name__ == '__main__':
    main()
