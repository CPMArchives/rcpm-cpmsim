#!/usr/bin/env python3
"""Play the packaged games through BYE; test exit, terminal and call recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess

from backup_rcpm import copy_file
from check_release import Guest, free_port


def run(args, mode):
    out = args.output / mode; out.mkdir()
    p = out / 'instance'
    shutil.copytree(args.package, p, copy_function=lambda a,b: copy_file(Path(a),Path(b),Path(a).stat().st_mode & 0o777) and b)
    env = dict(os.environ, DISKDEFS=str(p/'runtime/diskdefs'))
    def listing(image, fmt, pattern):
        return subprocess.check_output([str(p/'runtime/cpmls'), '-f', fmt,
                                        str(image), pattern], env=env).decode().lower().split()
    a0 = listing(p/'disks/drivea.dsk', 'ibm-3740', '0:*')
    j0 = listing(p/'disks/library/GAMES.dsk', 'z80pack-hd', '0:*')
    for name in ('advent.com', 'animals.com', 'mchase.com'):
        assert name not in a0 and name in j0, name
    port = free_port(); public = port; modem = None; log = None
    if mode == 'ip232':
        public = free_port(); log = (out/'tcpser.log').open('wb')
        modem = subprocess.Popen([str(args.tcpser), '-v', f'127.0.0.1:{port}', '-p',
                                  f'127.0.0.1:{public}', '-s','2400','-S','2400',
                                  '-i','&c1&d2','-l','0'], stdout=log, stderr=log, restore_signals=False)
    g = Guest(p, out/'console', '--mode', mode, '--port', str(port))
    games_hash = hashlib.sha256((p/'disks/library/GAMES.dsk').read_bytes()).digest()
    def wait(mark, start, timeout=60):
        return g.wait(mark, remote=True, start=start, timeout=timeout)
    def send(data):
        offset = len(g.remote)
        for c in data:
            g.caller.sendall(bytes([c])); g.collect(.025)
        return offset
    def line(text): return send((text+'\r').encode())
    def login():
        offset = len(g.remote)
        g.caller = socket.create_connection(('127.0.0.1', public), timeout=5)
        for _ in range(60):
            if mode == 'direct': g.caller.sendall(b'\r')
            g.collect(.4)
            if b'A0:SYSTEM>' in g.remote[offset:]: return
        raise AssertionError('Caller login failed')
    try:
        g.wait(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0')
        if mode == 'ip232': g.collect(3)
        login(); g.command('MOUNT GAMES')
        offset = line('J0:ADVENT'); wait(b'Would you like instructions?', offset)
        offset = line('N'); wait(b'small brick building.', offset); wait(b'>', offset)
        offset = line('LOOK'); wait(b'small brick building.', offset); wait(b'>', offset)
        offset = line('QUIT'); wait(b'Do you really want to quit now?', offset)
        offset = line('Y'); wait(b'I0:WORK>', offset)
        print(mode+': Adventure command/quit PASS', flush=True)
        offset = line('J0:ANIMALS'); wait(b'Would you like to play the animal guessing game?', offset); wait(b'\x1bk', offset)
        offset = send(b'Y\r'); wait(b'Does it live in the water?', offset); wait(b'\x1bk', offset)
        offset = send(b'Y'); wait(b'Is it an octopus?', offset); wait(b'\x1bk', offset)
        offset = send(b'Y'); wait(b'I WON!', offset)
        wait(b'Would you like to play another round', offset, timeout=90)
        wait(b'\x1bk', offset)
        offset = send(b'N'); wait(b'I0:WORK>', offset)
        print(mode+': Animals round/exit PASS', flush=True)
        offset = line('J0:MCHASE'); wait(b'Insert Coin:', offset)
        offset = send(b'1'); wait(b'Boss?', offset)
        positions = re.findall(rb'\x1b\[(\d+);(\d+)H', g.remote[offset:])
        assert positions and all(1 <= int(y) <= 24 and 1 <= int(x) <= 80 for y,x in positions)
        offset = send(b'P'); wait(b'Score:', offset)
        g.collect(1)
        send(b'6'); g.collect(.5)
        # Input during the initial board draw can be consumed before the game
        # loop is ready. Send Escape again only after the complete board appears.
        offset = send(b'\x1b')
        for _ in range(12):
            g.collect(.5)
            if b'Boss?' in g.remote[offset:]: break
            g.caller.sendall(b'\x1b')
        wait(b'Boss?', offset)
        offset = send(b'E'); wait(b'I0:WORK>', offset)
        print(mode+': Maze Chase ANSI/play/exit PASS', flush=True)
        offset = line('J0:ADVENT'); wait(b'Would you like instructions?', offset)
        local = len(g.local); os.write(g.master, b'\x02'); g.wait(b'[Remote off]', start=local)
        local = len(g.local); os.write(g.master, b'\x02'); g.wait(b'[Remote on]', start=local)
        local = len(g.local); g.caller.close(); g.caller = None
        g.wait(b'RCP/M modem ready.' if mode == 'direct' else b'ATE0Q0V0S0=0M0S10=25X1H0', start=local, timeout=60)
        if mode == 'ip232': g.collect(3)
        login()
        reply = g.command('DIR I0:BEASTS.*')
        assert b'QQQ' not in reply and b'QQX' not in reply, reply
        reply = g.command('SYSUTLS:PIP')
        assert (b'Directory access denied.' in reply or b'SYSUTLS:PIP?' in reply) and b'*' not in reply, reply
        g.stop()
        assert hashlib.sha256((p/'disks/library/GAMES.dsk').read_bytes()).digest() == games_hash
        result = dict(mode=mode, cpu_mhz=4, launchers_on_J0=True, no_A0_game_wrappers=True, adventure_play_quit=True,
                      animals_round_exit=True, maze_ansi_play_exit=True,
                      ansi_coordinates_valid=True, local_blank_controls=True,
                      game_carrier_loss_recovery=True, work_cleaned_between_calls=True,
                      private_tools_remain_denied=True)
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    finally:
        g.close()
        if modem:
            modem.terminate()
            try: modem.wait(timeout=3)
            except subprocess.TimeoutExpired: modem.kill(); modem.wait()
        if log: log.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tcpser', type=Path)
    p.add_argument('--mode', choices=('direct','ip232'), action='append')
    args = p.parse_args()
    for n in ('package','output','tcpser'):
        if getattr(args,n): setattr(args,n,getattr(args,n).resolve())
    args.output.mkdir(parents=True, exist_ok=False)
    for mode in args.mode or ('direct','ip232'):
        if mode == 'ip232' and not args.tcpser: p.error('IP232 requires --tcpser')
        run(args, mode)
