#!/usr/bin/env python3
"""Prepare an isolated RBBS 3.7 evaluation; never modify a running installation."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import secrets
import shlex
import subprocess
import tempfile
import urllib.request

from prepare_shared_trial import create
from prepare_z3plus import configure_startup

REPOSITORY = Path(__file__).resolve().parent


def references(cache, fetch=False):
    rows = json.loads((REPOSITORY / 'docs/rbbs37-reference-sources.json').read_text())
    def obtain(row):
        target = cache / row['path']
        if not target.exists() and fetch:
            target.parent.mkdir(parents=True, exist_ok=True)
            data = urllib.request.urlopen(row['url'], timeout=30).read()
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Download hash mismatch: ' + row['path'])
            target.write_bytes(data)
        if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Missing or changed reference: ' + str(target))
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(obtain, rows))
    return rows


def install(instance, cache, tools, romwbw, final_instance=None):
    """Install the legacy private board; upper_layout adds public admission."""
    build = json.loads((Path(json.loads((instance / 'trial-build.json').read_text())['builds']) / 'build-result.json').read_text())
    if not build.get('public_rbbs'):
        raise ValueError('Rebuild BYE with the public RBBS launcher boundary first')
    a = instance / 'disks/drivea.dsk'
    b = instance / 'disks/driveb.dsk'
    i = instance / 'disks/drivei.dsk'
    original = cache / 'rbbs37-1'
    def put(disk, user, name, data, fmt):
        temporary = instance / '.rbbs-file'
        temporary.write_bytes(data)
        try:
            subprocess.run([str(tools / 'cpmcp'), '-T', 'raw', '-f', fmt,
                            str(disk), str(temporary), f'{user}:{name}'], check=True)
        finally:
            temporary.unlink(missing_ok=True)
    for name in ('rbbs37.com', 'menurbbs', 'help', 'news', 'twit'):
        put(a, 2, name.upper(), (original / name).read_bytes(), 'ibm-3740')
    texts = {
        'INFO': 'RBBS 3.7 evaluation on CP/M 3, Z3PLUS and BYE510.',
        'BULLETIN': 'An isolated compatibility trial. Please use test credentials only.',
        'NEWCOM': 'Welcome. This evaluation permits messages and J to return to CP/M.',
        'ENTERCPM': 'Returning to the CP/M prompt. BBS data remains on I2:.',
    }
    for name, text in texts.items():
        put(a, 2, name, ('\r\n' + text + '\r\n\x1a').encode(), 'ibm-3740')
    # All three data groups use user 2; static display/configuration files A2:,
    # growing users/messages/callers I2:. Never import historical users/passwords.
    put(a, 2, 'BOOTPWD', b'I:,I:,LOCAL,SYSOP,RCPM RBBS 3.7 Trial,N,N\r\n\x1a', 'ibm-3740')
    for name, width, value in (
        ('USERS', 62, ' 0'), ('CALLERS', 60, ' 0'), ('COMMENTS', 65, ' 1'),
        ('SUMMARY', 30, ' 9999'), ('MESSAGES', 65, ' 9999'),
    ):
        put(i, 2, name, value.encode().ljust(width, b' '), 'z80pack-hd')
    put(i, 2, 'COUNTERS', b' 0    0    0   ', 'z80pack-hd')
    # RBBS rejects a last-name field lexically below "A" before comparing
    # its SYSOP password. Keep the generated password letter-prefixed.
    secret = {key: prefix + secrets.token_hex(12).upper()[1:]
              for key, prefix in (('direct_cpm', 'D'), ('rbbs_sysop', 'S'), ('validation', 'V'))}
    values = ','.join((secret['direct_cpm'], secret['rbbs_sysop'], 'NOPASS', 'CPM', secret['validation'], 'N'))
    put(i, 2, 'PWDS', (values + '\r\n10,24,1,0,0,1,1,0\r\n\x1a').encode(), 'z80pack-hd')
    # RBBS deliberately opens a lower-case CP/M filename, as documented.
    # This raw, unskewed format's 1024-entry directory starts at byte zero.
    with i.open('r+b') as disk:
        directory = bytearray(disk.read(1024 * 32))
        entries = [offset for offset in range(0, len(directory), 32)
                   if directory[offset:offset + 12] == b'\x02PWDS       ']
        if len(entries) != 1:
            raise ValueError('Expected one fresh I2:PWDS directory entry')
        directory[entries[0] + 1:entries[0] + 5] = b'pwds'
        disk.seek(0)
        disk.write(directory)
    # The BASIC RUN statement for G loads BYE from the application's DU.
    with tempfile.TemporaryDirectory(dir=instance) as temporary:
        bye = Path(temporary) / 'BYE.COM'
        subprocess.run([str(tools / 'cpmcp'), '-f', 'ibm-3740', str(a), '0:BYE.COM', str(bye)], check=True)
        put(a, 2, 'BYE.COM', bye.read_bytes(), 'ibm-3740')
    b.chmod(0o600)
    try:
        alias = configure_startup(romwbw / 'Source/Images/d_z3plus/u0/STARTZ3P.COM', 'A2:;A2:RBBS37')
        put(b, 0, 'RBBS.COM', alias, 'ibm-3740')
        for name in ('rbbsinst.com', 'rbbsinst.hlp', 'rbbsutil.com'):
            put(b, 0, name.upper(), (original / name).read_bytes(), 'ibm-3740')
    finally:
        b.chmod(0o444)
    credentials = instance / 'rbbs-trial-passwords.json'
    credentials.write_text(json.dumps(secret, indent=2) + '\n')
    credentials.chmod(0o600)
    # A distinct port lets the currently working shared-console trial continue.
    launcher = '#!/bin/zsh\nset -eu\nexec python3 ' + shlex.quote(str(REPOSITORY / 'run_shared_trial.py'))
    launcher += ' --instance ' + shlex.quote(str(final_instance or instance)) + ' --port 4002\n'
    (instance / 'Start-RCPM.command').write_text(launcher)
    updater = '#!/bin/zsh\nset -eu\nexec python3 ' + shlex.quote(str(REPOSITORY / 'upgrade_bye5_trial.py'))
    updater += ' --instance ' + shlex.quote(str(final_instance or instance))
    updater += ' --builds ' + shlex.quote(str(REPOSITORY / 'build/bye5'))
    updater += ' --cpmtools ' + shlex.quote(str(tools)) + '\n'
    (instance / 'Update-RCPM.command').write_text(updater)
    (instance / 'Update-RCPM.command').chmod(0o755)
    helper = '#!/bin/zsh\nset -eu\nexec python3 ' + shlex.quote(str(REPOSITORY / 'rbbs_sysop_login.py'))
    helper += ' --instance ' + shlex.quote(str(final_instance or instance)) + '\n'
    (instance / 'Login-SYSOP.command').write_text(helper)
    (instance / 'Login-SYSOP.command').chmod(0o755)
    enable = updater.rstrip('\n') + ' --enable-rbbs\n'
    (instance / 'Enable-RBBS.command').write_text(enable)
    (instance / 'Enable-RBBS.command').chmod(0o755)
    (instance / 'README.txt').write_text(
        'RBBS 3.7 evaluation: raw TCP 127.0.0.1:4002.\n'
        'Run Start-RCPM.command; this Terminal is the shared local console.\n'
        'Connect SyncTERM; use private B:RBBS for this legacy I2: evaluation.\n'
        'See README-RBBS.txt for the walkthrough and remaining integration work.\n'
        'Use test credentials only; this is not a public-service installation.\n')
    manifest = json.loads((instance / 'trial-build.json').read_text())
    manifest.update(port=4002, rbbs='3.7 evaluation', bbs_data='I2:', public_rbbs=False,
                    production_integration=False,
                    hashes={str(p.relative_to(instance)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (a, b, instance / 'runtime/cpmsim')})
    (instance / 'trial-build.json').write_text(json.dumps(manifest, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--romwbw', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, default=Path('build/modem/cpmsim'))
    parser.add_argument('--builds', type=Path, default=Path('build/bye5'))
    parser.add_argument('--cpmtools', type=Path, default=Path('build/cpmtools/bin'))
    parser.add_argument('--cache', type=Path, default=Path('build/rbbs37/original'))
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for key in ('source', 'romwbw', 'runtime', 'builds', 'cpmtools', 'cache', 'output'):
        setattr(args, key, getattr(args, key).expanduser().resolve())
    if args.output.exists() or args.output.is_symlink():
        parser.error('Refusing to replace an existing trial')
    if not json.loads((args.builds / 'build-result.json').read_text()).get('adapter_relocation_fixed'):
        parser.error('Regenerate and rebuild BYE with the adapter relocation correction first')
    if not json.loads((args.builds / 'build-result.json').read_text()).get('private_i2'):
        parser.error('Rebuild BYE with the private I2: application boundary first')
    rows = references(args.cache, args.fetch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.rbbs-trial-', dir=args.output.parent) as temporary:
        trial = Path(temporary) / 'instance'
        create(args.source, args.romwbw, args.runtime, args.builds, args.cpmtools, trial)
        install(trial, args.cache, args.cpmtools, args.romwbw, args.output)
        (trial / 'rbbs-reference-sources.json').write_text(json.dumps(rows, indent=2) + '\n')
        (trial / 'README-RBBS.txt').write_text((REPOSITORY / 'docs/rbbs-trial.md').read_text())
        trial.rename(args.output)
    print('RBBS evaluation prepared; consult docs/rbbs-trial.md for qualification status.')


if __name__ == '__main__':
    main()
