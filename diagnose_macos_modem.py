#!/usr/bin/env python3
"""Compare only modem answering on frozen baseline/candidate media; no publication."""
import argparse,hashlib,json,shutil,socket,time,tempfile
from pathlib import Path
from check_release import Guest,extract_package


def run(label,archive,out,timeout):
 out.mkdir(parents=True,exist_ok=False);record={'label':label,'timeout_seconds':timeout}
 with tempfile.TemporaryDirectory(prefix='rcpm-modem-diagnostic-') as temp:
  root=extract_package(archive,Path(temp)/'expanded')
  record['native_sha256']={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['runtime/rcpm','runtime/cpmsim','runtime/tcpser','drivers/ip232/BYEDRIV.COM']}
  with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
  c=root/'RCPM.CONF';c.write_text(c.read_text().replace('MODE=direct','MODE=ip232').replace('PORT=4000','PORT='+str(port)))
  g=Guest(root,out/'console');start=time.monotonic()
  try:
   g.wait(b'ATE0Q0V0S0=0M0S10=25X1H0',timeout=120);g.wait(b'\n0\r\n',timeout=120);g.collect(3)
   record['boot_seconds']=time.monotonic()-start
   g.caller=socket.create_connection(('127.0.0.1',port),timeout=5);connected=time.monotonic();milestones={}
   # No caller Return is injected. Observe the same connection beyond 25 s.
   while b'A0:SYSTEM>' not in g.remote and time.monotonic()-connected<timeout:
    g.collect(.1);elapsed=time.monotonic()-connected
    for name,needle in [('answer_command',b'ATA'),('connect_code',b'\n10'),('welcome',b'BYE510 (c)')]:
     if name not in milestones and needle in g.local:milestones[name]=elapsed
   record['milestones_seconds']=milestones;record['welcome_seconds']=time.monotonic()-connected if b'A0:SYSTEM>' in g.remote else None
   record['passed']=record['welcome_seconds'] is not None;record['within_old_25s_limit']=record['passed'] and record['welcome_seconds']<=25
   if record['passed']:
    g.stop()
   else:record['failure']='No caller prompt within observation window'
  except Exception as e:record['passed']=False;record['error']=repr(e)
  finally:
   record['console_tail']=bytes(g.local[-2500:]).decode('ascii',errors='replace');g.close()
   if (root/'state/tcpser.log').exists():shutil.copy2(root/'state/tcpser.log',out/'tcpser.log')
 (out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='console_tail'}),flush=True);return record


if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=120);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 reports=[run(label,path.resolve(),a.output/label,a.timeout) for label,path in [('baseline-1.2.2',a.baseline),('candidate-1.2.3',a.candidate)]]
 assert reports[0]['native_sha256']==reports[1]['native_sha256'],'Native binaries differ'
 (a.output/'comparison.json').write_text(json.dumps(reports,indent=2)+'\n')
