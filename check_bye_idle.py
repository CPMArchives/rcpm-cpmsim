#!/usr/bin/env python3
"""Check actual guest idle expiry at 4 and 20 MHz, with one activity reset."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time

from check_bye_speed import prepare
from check_release import Guest, free_port

REPO=Path(__file__).resolve().parent


def run(args,mhz,reset_at):
    output=args.output/str(mhz);output.mkdir()
    package=output/'instance'
    prepare(args.package,package,args.builds,args.runtime)
    probe=output/'CLS.COM'
    # Trusted one-shot fixture: set the test CPU clock and BYE's timeout to
    # one minute, then return. It is never included in a release disk.
    # The speed latch commits only when its high-byte port (31) is written.
    # Read the low byte back and print it + '@' (D=4, T=20) for verification.
    probe.write_bytes(bytes([0x3e,mhz,0xd3,30,0xaf,0xd3,31,
                            0xdb,30,0xc6,64,0x5f,0x0e,2,0xcd,5,0,
                            0x0e,71,0x1e,1,0xcd,5,0,0xc9]))
    tools=REPO/'build/release-tools/bin'
    image=package/'disks/drivea.dsk'
    subprocess.run([str(tools/'cpmrm'),'-f','ibm-3740',str(image),'0:CLS.COM'],check=True)
    subprocess.run([str(tools/'cpmcp'),'-f','ibm-3740',str(image),str(probe),'0:CLS.COM'],check=True)
    port=free_port();guest=Guest(package,output/'idle','--port',str(port))
    try:
        guest.wait(b'RCP/M modem ready.');guest.connect(port)
        reply=guest.command('A0:CLS')
        assert b'\r\n'+bytes([64+mhz]) in reply.replace(b'\0',b''),reply
        began=time.monotonic();last=began;reset=False
        recovery_start=len(guest.local)
        while guest.caller is not None:
            elapsed=time.monotonic()-began
            if reset_at is not None and not reset and elapsed>=reset_at:
                guest.caller.sendall(b' ')
                guest.collect(.3)
                last=time.monotonic();reset=True
            if time.monotonic()-last>67:
                raise AssertionError('Guest did not expire one idle minute')
            guest.collect(.05)
            if time.monotonic()-last<58 and guest.caller is None:
                raise AssertionError('Guest timed out before one real minute')
        seconds=time.monotonic()-last
        guest.wait(b'RCP/M modem ready.',start=recovery_start)
        assert b'[Input timed out]' in guest.local[recovery_start:],guest.local[-600:]
        result=dict(cpu_mhz=mhz,activity_reset=reset,seconds_after_last_activity=round(seconds,3),passed=True)
        (output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
        return result
    finally:
        guest.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('package','output','runtime','builds'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    for n in ('package','output','runtime','builds'):setattr(a,n,getattr(a,n).resolve())
    a.output.mkdir(parents=True,exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run,a,4,30),pool.submit(run,a,20,None)]
        results=[f.result()for f in futures]
    (a.output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
