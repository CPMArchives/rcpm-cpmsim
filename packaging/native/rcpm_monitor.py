#!/usr/bin/env python3
"""Local journal alerts and bounded private status; never restart or stop a board."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from rcpm_service import request

UNITS = ('rcpm.service', 'rcpm-backup.service')
DEFAULTS = dict(data_path='/var/lib/rcpm', backup_path='/var/backups/rcpm',
                min_free_bytes=512*1024*1024, min_free_inodes=1024,
                min_free_percent=5, restart_window=600, restart_limit=3,
                probe_timeout=30)


@contextlib.contextmanager
def monitor_lock(path):
    # Serialize timer and OnFailure writers, rather than losing a failure event
    # because an idle probe is already in progress. systemd bounds job duration.
    with path.open('a') as f:
        os.fchmod(f.fileno(), 0o600)
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        yield


def properties(unit):
    p = subprocess.run(['systemctl', 'show', unit, '--no-pager',
                        '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState',
                        '-p', 'Result', '-p', 'NRestarts'], capture_output=True,
                       text=True, timeout=10)
    if p.returncode:
        raise RuntimeError('Cannot read systemd state: ' + unit)
    return dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)


def space_issues(path, config):
    s = os.statvfs(path)
    free_bytes = s.f_bavail*s.f_frsize
    percent = 100*s.f_bavail/max(1, s.f_blocks)
    issues = {}
    if free_bytes < config['min_free_bytes'] or percent < config['min_free_percent']:
        issues['space:'+str(path)] = 'Low free storage: ' + str(path)
    if s.f_files and s.f_favail < config['min_free_inodes']:
        issues['inodes:'+str(path)] = 'Low free inodes: ' + str(path)
    return issues


def restart_history(previous, count, now, config):
    history = [p for p in previous if now-config['restart_window'] <= p[0] <= now]
    # Reset after a new boot/service counter reset; never treat a lifetime
    # NRestarts value as evidence of a recent loop on the first sample.
    if history and count < history[-1][1]:
        history = []
    history.append([now, count])
    return history[-100:], count-history[0][1] >= config['restart_limit']


def load_config(path):
    config = dict(DEFAULTS)
    if path.exists():
        values = json.loads(path.read_text())
        if not isinstance(values, dict) or set(values)-set(DEFAULTS):
            raise ValueError('Unknown monitor configuration')
        config.update(values)
    for name in ('data_path', 'backup_path'):
        if not isinstance(config[name], str) or not Path(config[name]).is_absolute():
            raise ValueError('Monitor paths must be absolute')
    for name in set(DEFAULTS)-{'data_path', 'backup_path'}:
        if not isinstance(config[name], (int, float)) or not 0 <= config[name] < 10**15:
            raise ValueError('Invalid monitor threshold: ' + name)
    if not 1 <= config['probe_timeout'] <= 120 or config['restart_limit'] < 1 or config['restart_window'] < 1:
        raise ValueError('Invalid monitor time/restart limit')
    return config


def save_state(path, previous, issues, details, now):
    old = previous.get('issues', {})
    events = previous.get('events', [])[-99:]
    for key in sorted(set(old) | set(issues)):
        if old.get(key) == issues.get(key):
            continue
        event = dict(at=now, key=key, state='alert' if key in issues else 'recovered',
                     message=issues.get(key, 'Recovered: ' + key))
        events.append(event)
        print(('<3>' if key in issues else '<5>') + json.dumps(event), flush=True)
    state = dict(checked_at=now, issues=issues, events=events[-100:], **details)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            os.fchmod(f.fileno(), 0o600)
            json.dump(state, f, indent=2)
            f.write('\n');f.flush();os.fsync(f.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    return state


def check(config, state_path, run_dir, failure_unit=None, probe=True):
    state_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with monitor_lock(state_path.parent/'monitor.lock'):
        previous = json.loads(state_path.read_text()) if state_path.exists() else {}
        now = time.time();issues = {};units = {}
        for unit in UNITS:
            try:
                units[unit] = properties(unit)
                if units[unit].get('LoadState') != 'loaded':
                    issues['unit:'+unit] = 'Unit unavailable: ' + unit
                if (units[unit].get('ActiveState') == 'failed' or
                        units[unit].get('Result', 'success') != 'success'):
                    issues['failure:'+unit] = 'Unit failure: ' + unit
            except (OSError, RuntimeError, subprocess.TimeoutExpired):
                issues['unit:'+unit] = 'Cannot inspect unit: ' + unit
        if failure_unit:
            issues['failure:'+failure_unit] = 'systemd OnFailure: ' + failure_unit
        for path in {config['data_path'], config['backup_path']}:
            try:
                issues.update(space_issues(path, config))
            except OSError:
                issues['storage:'+path] = 'Cannot inspect storage: ' + path
        count = int(units.get('rcpm.service', {}).get('NRestarts', 0))
        history, looping = restart_history(previous.get('restart_history', []), count, now, config)
        if looping:
            issues['restart-loop'] = 'Repeated RCP/M automatic restarts'
        guest = dict(status='deferred', reason='service_inactive')
        maintenance = units.get('rcpm-backup.service', {}).get('ActiveState') in ('activating', 'active', 'deactivating')
        if units.get('rcpm.service', {}).get('ActiveState') == 'active' and not maintenance and probe:
            try:
                guest = request(run_dir, 'probe', probe_timeout=config['probe_timeout'],
                                socket_timeout=config['probe_timeout']+5)
                if guest.get('status') == 'failed':
                    issues['guest-unresponsive'] = 'Caller responsiveness probe failed'
            except (OSError, RuntimeError, ValueError):
                issues['guest-unresponsive'] = 'Private control/probe unavailable'
                guest = dict(status='failed', error='Private control/probe unavailable')
        elif maintenance:
            guest['reason'] = 'backup_maintenance'
        elif not probe:
            guest['reason'] = 'failure_notification_only'
        # Busy/deferred is not a successful recheck. Keep an existing guest
        # alert until a real probe succeeds (or the service is stopped).
        if (guest.get('status') == 'deferred' and
                units.get('rcpm.service', {}).get('ActiveState') == 'active' and
                'guest-unresponsive' in previous.get('issues', {})):
            issues['guest-unresponsive'] = previous['issues']['guest-unresponsive']
        return save_state(state_path, previous, issues,
                          dict(units=units, guest=guest, restart_history=history), now)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('check', 'failure', 'status'))
    p.add_argument('--unit', choices=UNITS)
    p.add_argument('--config', type=Path, default=Path('/etc/rcpm/monitor.json'))
    p.add_argument('--state', type=Path, default=Path('/var/lib/rcpm/monitor/state.json'))
    p.add_argument('--run-dir', type=Path, default=Path('/run/rcpm'))
    a = p.parse_args();os.umask(0o077)
    if a.action == 'status':
        print(a.state.read_text());return
    if a.action == 'failure' and not a.unit:
        p.error('failure requires --unit')
    state = check(load_config(a.config), a.state, a.run_dir,
                  a.unit if a.action == 'failure' else None, a.action == 'check')
    print(json.dumps(dict(issues=len(state['issues']), guest=state['guest'])))
    # A failure notification succeeds when it records the alert. Only a
    # periodic health check returns failure for outstanding board issues.
    if state['issues'] and a.action == 'check':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
