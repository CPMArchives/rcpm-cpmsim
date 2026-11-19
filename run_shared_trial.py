#!/usr/bin/env python3
"""Run the private shared-machine trial on loopback TCP with a local console."""
import argparse
import fcntl
import os
from pathlib import Path
import socket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--port', type=int, default=4001)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be 1-65535')
    if not os.isatty(0) or not os.isatty(1):
        parser.error('Start the local console from an interactive Terminal window')
    root = args.instance.expanduser().resolve()
    runtime = root / 'runtime/cpmsim'
    if not os.access(runtime, os.X_OK):
        parser.error(f'Trial runtime unavailable: {runtime}')
    for drive in 'abijp':
        if not (root / f'disks/drive{drive}.dsk').is_file():
            parser.error(f'Trial drive {drive.upper()}: is missing')
    with (root / '.console.lock').open('a+b') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error('This trial is already running; use its current local console')
        try:
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(('127.0.0.1', args.port))
        except OSError as error:
            parser.error(f'Trial TCP port unavailable: {error}')
        os.set_inheritable(lock.fileno(), True)
        os.environ.update(RCPM_MODEM='direct', RCPM_MODEM_HOST='127.0.0.1',
                          RCPM_MODEM_PORT=str(args.port))
        os.chdir(root)
        print(f'Shared RCP/M trial: 127.0.0.1:{args.port}; this terminal is the local console.', flush=True)
        os.execv(runtime, [str(runtime), '-f', '4'])


if __name__ == '__main__':
    main()
