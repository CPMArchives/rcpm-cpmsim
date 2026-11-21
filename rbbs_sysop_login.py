#!/usr/bin/env python3
"""Pace a local RBBS SYSOP login into the matching, blanked tmux console."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import time


def login(instance, pane=None, delay=.12):
    instance = instance.expanduser().resolve()
    secret = json.loads((instance / 'rbbs-trial-passwords.json').read_text())['rbbs_sysop']
    if not re.fullmatch(r'[A-Z0-9]{2,63}', secret) or secret[0] < 'A':
        raise ValueError('The saved password cannot pass this RBBS version\'s LAST Name check')
    tmux = shutil.which('tmux')
    if not tmux:
        raise RuntimeError('tmux is not on PATH in this Terminal')
    def command(*args):
        result = subprocess.run([tmux, *args], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError('Cannot access tmux: ' + result.stderr.strip())
        return result.stdout
    rows = command('list-panes', '-a', '-F', '#{pane_id}\t#{pane_current_command}\t#{pane_current_path}').splitlines()
    matches = []
    for row in rows:
        fields = row.split('\t', 2)
        if len(fields) == 3 and fields[1] == 'cpmsim' and Path(fields[2]).resolve() == instance:
            if pane is None or fields[0] == pane:
                matches.append(fields[0])
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one cpmsim tmux pane for this trial; no keys were sent')
    target = matches[0]
    def screen():
        return command('capture-pane', '-p', '-t', target, '-S', '-1000')
    def tail():
        return screen().rstrip().splitlines()[-1].strip()
    states = re.findall(r'\[Remote (off|on)\]', screen())
    if not states or states[-1] != 'off':
        raise RuntimeError('Blank the caller locally first, then retry; no keys were sent')
    current = tail()
    if not (current.endswith('FIRST Name:') or current.endswith('LAST Name:')):
        raise RuntimeError('RBBS must be at an empty FIRST Name or LAST Name prompt; no keys were sent')
    if current.endswith('LAST Name:'):
        names = re.findall(r'FIRST Name:\s*(\S+)', screen())
        if not names or names[-1].upper() != 'SYSOP':
            raise RuntimeError('The LAST Name prompt is not for SYSOP; no keys were sent')
    def wait_for(predicate):
        until = time.monotonic() + 15
        while time.monotonic() < until:
            current = tail()
            if predicate(current):
                return current
            time.sleep(.1)
        raise RuntimeError('RBBS did not reach the expected prompt; inspect the local console')
    def type_line(value):
        for char in value:
            command('send-keys', '-t', target, '-l', char)
            time.sleep(delay)
        command('send-keys', '-t', target, 'Enter')
        time.sleep(delay)
    if current.endswith('FIRST Name:'):
        type_line('SYSOP')
        wait_for(lambda line: line.endswith('LAST Name:'))
    type_line(secret)
    result = wait_for(lambda line: 'SYSOP?  Your Command:' in line or line.endswith('FIRST Name:'))
    if 'SYSOP?  Your Command:' not in result:
        raise RuntimeError('SYSOP login was rejected; no further keys were sent')
    print('Signed in to RBBS as SYSOP. Keep the caller blanked.')
    print('Enter P to validate a member. Leave with J before unblanking.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--pane', help='Optional tmux pane ID when selecting a console')
    args = parser.parse_args()
    try:
        login(args.instance, args.pane)
    except (OSError, KeyError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error) + '\n')
