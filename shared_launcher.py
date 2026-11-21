#!/usr/bin/env python3
"""Start or attach to the single shared RCP/M machine in tmux."""
import argparse
from datetime import datetime, timezone
import errno
import os
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time

from shared_instance import lock, running, validate

REPO = Path(__file__).resolve().parent


class Tmux:
    def __init__(self):
        executable = shutil.which('tmux')
        if executable is None:
            raise RuntimeError('tmux is unavailable; install it before running rcpm')
        self.command = [executable]
        if os.environ.get('RCPM_TMUX_SOCKET'):
            self.command += ['-S', os.environ['RCPM_TMUX_SOCKET']]

    def run(self, *args, check=True):
        result = subprocess.run([*self.command, *map(str, args)], capture_output=True, text=True)
        if 'Operation not permitted' in result.stderr or 'Permission denied' in result.stderr:
            raise RuntimeError('Cannot access the tmux server: ' + result.stderr.strip())
        if check and result.returncode:
            raise RuntimeError(result.stderr.strip() or 'tmux command failed')
        return result

    def find(self, session):
        # Resolve names ourselves, then use stable IDs for every target command.
        result = self.run('list-sessions', '-F', '#{session_id}\t#{session_name}', check=False)
        if result.returncode:
            if 'no server running' in result.stderr or 'No such file or directory' in result.stderr:
                return None
            raise RuntimeError(result.stderr.strip() or 'Cannot list tmux sessions')
        for line in result.stdout.splitlines():
            identifier, name = line.split('\t', 1)
            if name == session:
                return identifier
        return None


def port_busy(port):
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                return True
            raise
    return False


def guest_command(root, port):
    return 'exec ' + shlex.join([sys.executable, str(REPO / 'run_shared_trial.py'),
                                '--instance', str(root), '--port', str(port)])


def matches_guest_command(recorded, expected):
    """tmux may quote the single shell-command argument when formatting it."""
    try:
        words = shlex.split(recorded)
        if len(words) == 1:
            words = shlex.split(words[0])
        return words == shlex.split(expected)
    except ValueError:
        return False


def ensure_session(root, port, session, tmux):
    """Create or reuse the guest and return its tmux session ID."""
    validate(root)
    command = guest_command(root, port)
    with lock(root, '.launch.lock', 'Another RCP/M launch or backup is in progress; retry shortly'):
        target = tmux.find(session)
        if target:
            owner = tmux.run('show-options', '-qv', '-t', target, '@rcpm_instance').stdout.strip()
            selected_port = tmux.run('show-options', '-qv', '-t', target, '@rcpm_port').stdout.strip()
            if owner != str(root) or selected_port != str(port):
                # Recover a first launch interrupted before its metadata was set.
                # A matching name alone never authorizes adopting a live guest.
                started = tmux.run('list-panes', '-s', '-t', target,
                                   '-F', '#{pane_start_command}').stdout.splitlines()
                if (owner not in ('', str(root)) or selected_port not in ('', str(port))
                        or len(started) != 1 or not matches_guest_command(started[0], command)
                        or not running(root) or not port_busy(port)):
                    raise RuntimeError(
                        'Cannot confirm ownership of tmux session ' + session + '.\n'
                        + 'Expected installation: ' + str(root) + '; port: ' + str(port) + '\n'
                        + 'Recorded installation: ' + repr(owner) + '; port: ' + repr(selected_port) + '\n'
                        + 'Pane startup command: ' + repr(started) + '\n'
                        + 'Expected startup command: ' + repr(command))
                tmux.run('set-option', '-t', target, '@rcpm_instance', str(root))
                tmux.run('set-option', '-t', target, '@rcpm_port', str(port))
            dead = tmux.run('list-panes', '-s', '-t', target, '-F', '#{pane_dead}').stdout.splitlines()
            if dead and all(value == '1' for value in dead) and not running(root):
                tmux.run('kill-session', '-t', target)
            else:
                if not running(root) or not port_busy(port):
                    raise RuntimeError('The shared tmux session is not serving RCP/M; inspect that session before restarting')
                return target
        if running(root):
            raise RuntimeError('This installation is already running outside the managed tmux session. '
                               'Save your work, run SYSUTLS:BYEBYE there, then run rcpm again.')
        if port_busy(port):
            raise RuntimeError(f'Port {port} is occupied by another listener; no guest was started')
        target = tmux.run('new-session', '-d', '-P', '-F', '#{session_id}',
                          '-s', session, '-n', 'CP-M', '-c', root, command).stdout.strip()
        if not re.fullmatch(r'\$[0-9]+', target):
            raise RuntimeError('tmux did not return the new session ID')
        tmux.run('set-option', '-t', target, '@rcpm_instance', str(root))
        tmux.run('set-option', '-t', target, '@rcpm_port', str(port))
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            if tmux.find(session) != target:
                diagnostic = shlex.join([sys.executable, str(REPO / 'run_shared_trial.py'),
                                         '--instance', str(root), '--port', str(port)])
                raise RuntimeError('The shared guest exited during startup. Inspect it directly with: ' + diagnostic)
            if running(root) and port_busy(port):
                return target
            time.sleep(.1)
        raise RuntimeError('The shared guest did not open its listener; inspect tmux session ' + session)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path,
        default=Path(os.environ.get('RCPM_INSTANCE', REPO / 'build/upper-system-final')))
    parser.add_argument('--port', type=int, default=int(os.environ.get('RCPM_PORT', '4002')))
    parser.add_argument('--session', default=os.environ.get('RCPM_SESSION', 'rcpm-shared'))
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--check', action='store_true')
    action.add_argument('--backup', nargs='?', const='', metavar='DIRECTORY')
    action.add_argument('--verify-backup', type=Path, metavar='DIRECTORY')
    action.add_argument('--restore', type=Path, metavar='BACKUP')
    parser.add_argument('--output', type=Path, help='New installation directory for restore')
    args = parser.parse_args()
    try:
        root = args.instance.expanduser().resolve()
        if not 1 <= args.port <= 65535:
            raise ValueError('--port must be 1-65535')
        if args.output is not None and args.restore is None:
            raise ValueError('--output is only used with --restore')
        if args.backup is not None:
            from backup_rcpm import backup
            output = (Path(args.backup).expanduser() if args.backup else
                      REPO / 'build/backups' / datetime.now(timezone.utc).strftime('rcpm-%Y%m%dT%H%M%S%fZ'))
            print('Backup verified:', backup(root, output, args.port))
            return
        if args.verify_backup:
            from backup_rcpm import verify
            data = verify(args.verify_backup.expanduser())
            print('Backup verified:', len(data['files']), 'files')
            return
        if args.restore:
            from backup_rcpm import restore
            if args.output is None:
                raise ValueError('--restore requires --output pointing to a new directory')
            print('Restored:', restore(args.restore.expanduser(), args.output.expanduser()))
            return
        if not re.fullmatch(r'[A-Za-z0-9_-]+', args.session):
            raise ValueError('Session name must contain only letters, digits, underscores or hyphens')
        validate(root)
        tmux = Tmux()
        if args.check:
            print('Shared installation verified:', root)
            print(f'Listener: 127.0.0.1:{args.port}; tmux session: {args.session}')
            print('Guest state:', 'running' if running(root) else 'stopped')
            return
        if not os.isatty(0) or not os.isatty(1):
            raise ValueError('Run rcpm in an interactive Terminal window')
        if os.environ.get('TMUX'):
            tmux.run('display-message', '-p', '#{session_name}')
        target = ensure_session(root, args.port, args.session, tmux)
        command = 'switch-client' if os.environ.get('TMUX') else 'attach-session'
        os.execv(tmux.command[0], [*tmux.command, command, '-t', target])
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
