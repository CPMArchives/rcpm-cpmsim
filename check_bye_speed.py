#!/usr/bin/env python3
"""Exercise corrected BYE at 4 MHz in a disposable native-package copy."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from backup_rcpm import copy_file
from check_release import Guest, free_port

REPO = Path(__file__).resolve().parent


def prepare(package, output, builds, runtime):
    shutil.copytree(package, output, copy_function=lambda a,b: copy_file(Path(a), Path(b), Path(a).stat().st_mode & 0o777) and b)
    shutil.copy2(runtime, output / 'runtime/cpmsim')
    shutil.copy2(runtime.with_name(runtime.name + '.features.json'), output / 'runtime/cpmsim.features.json')
    for mode in ('direct','ip232'):
        shutil.copy2(builds / mode / 'BYEDRIV.COM', output / 'drivers' / mode / 'BYEDRIV.COM')


def run(package, output):
    port = free_port()
    guest = Guest(package, output / 'console', '--port', str(port))
    result = {}
    try:
        guest.wait(b'RCP/M modem ready.')
        guest.connect(port)
        # A real installed file-reading command, not a benchmark substitute.
        rates=[]
        for _ in range(3):
            offset=len(guest.remote)
            for c in b'TYPE A:WELCOME.TXT [NO PAGE]':
                guest.caller.sendall(bytes([c]));guest.collect(.01)
            began=time.monotonic();guest.caller.sendall(b'\r')
            text=guest.wait(b'A0:SYSTEM>',remote=True,start=offset)
            elapsed=time.monotonic()-began
            assert b'R C P / M' in text
            rates.append(dict(bytes=len(text),seconds=round(elapsed,4),bytes_per_second=round(len(text)/elapsed)))
        result['welcome_samples']=rates
        print(json.dumps({'welcome_samples': rates}),flush=True)
        # Directory scrolling must complete without a page-pause in the way.
        offset=len(guest.remote)
        for c in b'DIR P: /N':
            guest.caller.sendall(bytes([c]));guest.collect(.01)
        began=time.monotonic();guest.caller.sendall(b'\r')
        listing=guest.wait(b'A0:SYSTEM>',remote=True,start=offset,timeout=120)
        elapsed=time.monotonic()-began
        assert b'SIGMV001' in listing and b'SIGMV310' in listing
        result['archive_listing']=dict(bytes=len(listing),seconds=round(elapsed,4),bytes_per_second=round(len(listing)/elapsed))
        assert min(s['bytes_per_second'] for s in rates)>550, rates
        guest.stop()
        result.update(cpu_mhz=4,completed=True)
    finally:
        guest.close()
    (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--package',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--builds',type=Path,required=True)
    p.add_argument('--runtime',type=Path,required=True)
    a=p.parse_args()
    a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
    fixture=a.output/'RCPM test with spaces'
    prepare(a.package.resolve(),fixture,a.builds.resolve(),a.runtime.resolve())
    run(fixture,a.output)
