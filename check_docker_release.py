#!/usr/bin/env python3
"""Exercise a loaded Docker image through its published TCP port and persisted data."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from check_release import Guest
from check_help_release import open_topic, leave


def check(image, output, docker, mode='direct'):
    output.mkdir(parents=True, exist_ok=False)
    suffix = image.rsplit(':', 1)[-1].replace('.', '-')
    name, volume = 'rcpm-check-' + suffix, 'rcpm-check-data-' + suffix
    def run(*args):
        return subprocess.check_output([docker, *args])
    run('volume', 'create', volume)
    try:
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            launcher = package / 'Start-RCPM.sh'
            launcher.write_text('#!/bin/sh\nexec ' + docker + ' run --rm -it --name ' + name +
                ' -p 127.0.0.1:14000:4000 -v ' + volume + ':/data ' + image + ' --mode ' + mode + '\n')
            launcher.chmod(0o755)
            prior = None
            for attempt in range(2):
                guest = Guest(package, output / ('run-' + str(attempt)))
                try:
                    guest.wait(b'RCP/M modem ready.' if mode == 'direct' else
                               b'ATE0Q0V0S0=0M0S10=25X1H0', timeout=120)
                    if mode == 'ip232': guest.collect(3)
                    guest.connect(14000, kick=mode == 'direct')
                    for manual in ('USER-GUIDE.DOC', 'SYSOP-GUIDE.DOC'):
                        data = run('exec', name, 'cat', '/opt/rcpm-seed/docs/'+manual)
                        assert b'1.2.3' in data and len(data)>10000, manual
                    assert b'CHAT -' in guest.remote
                    assert b'HELP' in re.sub(rb'\x1b\[[0-9;]*m', b'', guest.command('DIR')).upper()
                    chat_title = (Path(__file__).resolve().parent / 'guest/help/CHAT.HLP').read_text(encoding='ascii').splitlines()[1].encode('ascii')
                    assert b'CHAT' in open_topic(guest, 'HELP CHAT', chat_title)
                    leave(guest)
                    assert b'SYSOP ONLY' in open_topic(guest, 'HELP COMMANDS', b'COMPLETE INSTALLED COMMAND REFERENCE')
                    leave(guest)
                    start = len(guest.remote)
                    for char in b'RBBS\r':
                        guest.caller.sendall(bytes([char])); guest.collect(.04)
                    guest.wait(b'Enter your name:', remote=True, start=start)
                    target = output / ('SYSOP-' + str(attempt) + '.private')
                    run('cp', name + ':/data/SYSOP.DOC', str(target))
                    digest = hashlib.sha256(target.read_bytes()).hexdigest()
                    target.unlink()
                    if prior: assert prior == digest
                    prior = digest
                    if mode == 'ip232':
                        start = len(guest.local)
                        guest.caller.close(); guest.caller = None
                        guest.wait(b'ATE0Q0V0S0=0M0S10=25X1H0', start=start)
                        guest.collect(3)
                    guest.stop()
                finally:
                    guest.close()
                    subprocess.run([docker, 'rm', '-f', name], capture_output=True)
            result = dict(image=image, mode=mode, published_tcp_login=True, caller_help=True, expanded_command_help=True, manuals_present=True,
                          rbbs_entry=True, orderly_shutdown=True,
                          container_replacement_preserves_credentials=True,
                          persistent_volume=True)
            (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
            print(json.dumps(result))
    finally:
        run('volume', 'rm', volume)


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('image'); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--docker', default=shutil.which('docker'))
    p.add_argument('--mode', choices=['direct', 'ip232'], default='direct')
    a=p.parse_args();check(a.image,a.output.resolve(),a.docker,a.mode)
