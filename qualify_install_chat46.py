#!/usr/bin/env python3
"""Test disposable CHAT media, then install on the stopped original instance."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path
from check_chat46 import check
from install_chat46 import install


if __name__ == '__main__':
    root=Path(__file__).resolve().parent
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--instance',type=Path,default=Path.home()/'CPM/RCPM')
    a=p.parse_args();instance=a.instance.resolve()
    build=root/'guest/chat46'
    output=root/'build'/datetime.datetime.now().strftime('chat-validation-%Y%m%d-%H%M%S-%f')
    with (instance/'.console.lock').open('a+b') as lease:
        try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Stop RCP/M first: local Ctrl-C, Return, then SYSUTLS:BYEBYE.')
        print('Testing CHAT on disposable media; logs: '+str(output),flush=True)
        check(argparse.Namespace(instance=instance,chat=build/'CHAT.COM',output=output))
    install(instance,build,instance/'runtime')
    (instance/'metadata/CHAT46-VALIDATION.json').write_text((output/'result.json').read_text())
    print('PASS: CHAT installed. Restart RCP/M; callers can type CHAT or HELP CHAT.')
