#!/usr/bin/env python3
"""Check the actual packaged 1.2.3 help over a normal caller connection."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import time


def prepare_windows_console():
 import ctypes as c
 from ctypes import wintypes as w
 k=c.WinDLL('kernel32',use_last_error=True)
 k.FreeConsole()
 if not k.AllocConsole():raise c.WinError(c.get_last_error())
 # Hosted shells can leave redirected/invalid standard handles even after
 # AllocConsole. Bind explicit console devices before the guest inherits them.
 k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
 k.CreateFileW.restype=w.HANDLE
 k.SetStdHandle.argtypes=[w.DWORD,w.HANDLE];k.SetStdHandle.restype=w.BOOL
 for number,device in [(-10,'CONIN$'),(-11,'CONOUT$'),(-12,'CONOUT$')]:
  handle=k.CreateFileW(device,0xc0000000,3,None,3,0x80,None)
  if handle==c.c_void_p(-1).value or not k.SetStdHandle(number & 0xffffffff,handle):raise c.WinError(c.get_last_error())
 return k


def send(guest, data):
 for b in data:
  guest.caller.sendall(bytes([b]));guest.collect(.015)


def open_topic(guest, command, expected):
 start=len(guest.remote);send(guest,(command+'\r').encode())
 guest.wait(expected,remote=True,start=start)
 guest.wait(b'Enter Selection',remote=True,start=start)
 return bytes(guest.remote[start:])


def leave(guest):
 start=len(guest.remote);send(guest,b'\x03');guest.wait(b'A0:SYSTEM>',remote=True,start=start)


def check_session(guest, topics, all_topics=True):
 report={}
 r=guest.command('HELP //');assert b'Version 1.5r' in r,r
 checked=[]
 for p in sorted(topics.glob('*.HLP')) if all_topics else [topics/'COMMANDS.HLP']:
  title=p.read_text(encoding='ascii').splitlines()[1].encode();r=open_topic(guest,'HELP '+p.stem,title);leave(guest);checked.append(p.name)
 open_topic(guest,'HELP COMMANDS',b'COMPLETE INSTALLED COMMAND REFERENCE')
 for key,title in [(b'D',b'* PRIVATE UTILITIES ARUNZ TO HEXCOM'),(b'M',b'* GET.COM - REDIRECT CONSOLE INPUT')]:
  start=len(guest.remote);send(guest,key);guest.wait(title,remote=True,start=start);guest.wait(b'Enter Selection',remote=True,start=start)
 start=len(guest.remote);send(guest,b'^');guest.wait(b'PRIVATE UTILITIES ARUNZ',remote=True,start=start)
 start=len(guest.remote);send(guest,b'.');guest.wait(b'COMPLETE INSTALLED COMMAND REFERENCE',remote=True,start=start);leave(guest)
 for cmd in ['SYSUTLS:DATE','GET','GO','JUMP','POKE','PORT']:
  r=guest.command(cmd).replace(b'\0',b'');assert (cmd+'?').encode() in r or b'denied' in r.lower() or b'not found' in r.lower(),(cmd,r)
 r=guest.command('ECHO RELEASE-CALLER-OK').replace(b'\0',b'');assert b'\r\nRELEASE-CALLER-OK\r\n' in r
 report.update(passed=True,viewer_15r=True,topics_opened=len(checked),qualified_nested_links=True,parent_and_root=True,caller_restrictions=True,ordinary_echo=True)
 return report


def check(package, output):
 output.mkdir(parents=True,exist_ok=False)
 with tempfile.TemporaryDirectory(prefix='rcpm-help-release-') as temp:
  root=Path(temp)/'board with spaces';shutil.copytree(package,root)
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  conf=root/'RCPM.CONF';conf.write_text(conf.read_text().replace('PORT=4000','PORT='+str(port)))
  if os.name=='nt':
   import ctypes
   from check_windows_release import Guest
   prepare_windows_console()
   guest=Guest(root,output/'console',port)
  else:
   from check_release import Guest
   guest=Guest(root,output/'console')
  try:
   guest.wait(b'RCP/M modem ready.')
   if os.name=='nt':
    guest.caller=socket.create_connection(('127.0.0.1',port),timeout=5);deadline=time.monotonic()+35
    while b'A0:SYSTEM>' not in guest.remote:
     if time.monotonic()>deadline:raise RuntimeError('Caller login timeout')
     guest.caller.sendall(b'\r');guest.collect(.3)
   else:guest.connect(port)
   report=check_session(guest,package/'source/rcpm/guest/help');guest.stop()
  finally:guest.close()
 (output/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();check(a.package.resolve(),a.output.resolve())
