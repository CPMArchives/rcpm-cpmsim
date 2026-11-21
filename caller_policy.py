"""Validate the installed caller-program policy and generate its RSX table."""
import hashlib
import json
from pathlib import Path
import re

POLICY = Path(__file__).parent / 'caller-programs.json'


def policy():
    data = json.loads(POLICY.read_text())
    if data['drive'] != 'A' or data['user'] != 0:
        raise ValueError('The protected caller command directory must be A0:')
    programs = data['programs']
    if not programs or len(programs) != len(set(programs)):
        raise ValueError('Caller policy must contain unique programs')
    if any(not re.fullmatch(r'[A-Z0-9_]{1,8}\.COM', name) for name in programs):
        raise ValueError('Expected uppercase 8.3 COM filenames in caller policy')
    return data


def assembly():
    lines = []
    for name in policy()['programs']:
        base, ext = name.split('.')
        lines.append("        DB '" + base.ljust(8) + ext + "'")
    return '\n'.join(lines) + '\n        DB 0'


def digest():
    policy()
    return hashlib.sha256(POLICY.read_bytes()).hexdigest()
