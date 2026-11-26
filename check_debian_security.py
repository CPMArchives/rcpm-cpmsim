#!/usr/bin/env python3
"""Destructive security qualification, ONLY in a marked disposable Debian VM.

Uses the installed, unchanged systemd unit/helper/runtime. Each case gets stopped
copies of initialized media with documented test-only fixtures. Never use on a board.
"""
import argparse
from binascii import crc_hqx
import hashlib
import json
import os
from pathlib import Path
import pty
import shutil
import socket
import subprocess
import time
import traceback
import tty
from types import SimpleNamespace
from unittest.mock import patch

from check_release import Guest

ROOT = Path('/var/lib/rcpm/security-qualification')
INSTANCE = Path('/var/lib/rcpm/instance')
BASE = ROOT / 'baseline'
MODEM_READY = b'ATE0Q0V0S0=0M0S10=25X1H0'
os.environ['DISKDEFS'] = str(BASE/'runtime/diskdefs')


def run(*args, check=True, timeout=360):
    p = subprocess.run(list(map(str, args)), capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError(f'{args}: {p.returncode}: {p.stderr[-1000:]!r}')
    return p


def ctl(*args):
    return run('runuser', '-u', 'rcpm', '--', 'rcpmctl', *args)


def ready():
    state = json.loads(ctl('status').stdout)
    assert state['ready'] and state['guest_exit'] is None and state['tcpser_exit'] is None, state
    return state


def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''): h.update(b)
    return h.hexdigest()


def copy_media(source, target):
    run('cp', '-a', '--reflink=auto', '--sparse=always', source, target)


def activate(p):
    state=run('systemctl','is-active','rcpm',check=False).stdout.strip()
    main=run('systemctl','show','rcpm','-p','MainPID','--value').stdout.strip()
    if state not in (b'inactive',b'failed') or main!=b'0':
        raise RuntimeError('Refusing to switch media while the service has processes')
    if not INSTANCE.is_symlink() or not p.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError('Refusing a target outside disposable qualification media')
    INSTANCE.unlink()
    INSTANCE.symlink_to(p)
    run('chown', '-R', 'rcpm:rcpm', p)


class InstalledGuest(Guest):
    """Reuse guest test I/O over rcpmctl attach, never launch another emulator."""
    def __init__(self, package, output, *args):
        self.package, self.output = package, output
        activate(package)
        run('systemctl', 'start', 'rcpm')
        state=ready()
        listeners=run('ss','-lnt').stdout.decode()
        for port in (4000,24000,25232):
            lines=[l for l in listeners.splitlines() if f':{port} ' in l]
            assert lines and all(f'127.0.0.1:{port}' in l for l in lines),lines
        env=Path(f"/proc/{state['guest_pid']}/environ").read_bytes().split(b'\0')
        assert b'RCPM_MODEM=ip232' in env,'Installed guest did not select IP232'
        proof=dict(systemd_MainPID=int(run('systemctl','show','rcpm','-p','MainPID','--value').stdout),
                   guest_pid=state['guest_pid'],tcpser_pid=state['tcpser_pid'],
                   backend='ip232',loopback_only_ports=[4000,24000,25232])
        output.with_suffix('.service.json').write_text(json.dumps(proof,indent=2)+'\n')
        self.master, self.slave = pty.openpty()
        tty.setraw(self.slave)
        self.process = subprocess.Popen(['runuser', '-u', 'rcpm', '--', 'rcpmctl', 'attach'],
                                        stdin=self.slave, stdout=self.slave, stderr=self.slave)
        self.caller, self.local, self.remote = None, bytearray(), bytearray()
        self.initial_wait = True
        self.log = output.with_suffix('.operator.log').open('wb')
        self.collect(.3)
        assert self.process.poll() is None, bytes(self.local)

    def wait(self, marker, remote=False, start=0, timeout=45):
        if not remote and marker == b'RCP/M modem ready.':
            if self.initial_wait:
                # Attach deliberately does not replay private boot history.
                # Readiness is the real systemd/Hayes acknowledgement instead.
                self.initial_wait = False
                ready()
                return bytes(self.local[start:])
            marker = MODEM_READY
        return super().wait(marker, remote, start, timeout)

    def connect(self, port=4000, kick=False):
        super().connect(4000, kick=False)
        self.caller.settimeout(15)

    def detach(self):
        if self.process.poll() is None:
            os.write(self.master, b'\x1d')
            self.process.wait(timeout=10)
        self.collect(.1)

    def stop(self):
        if self.caller:
            self.caller.close(); self.caller = None
            self.collect(1)
        self.detach()
        run('systemctl', 'stop', 'rcpm')
        assert run('systemctl', 'show', 'rcpm', '-p', 'Result', '--value').stdout.strip() == b'success'

    def close(self):
        if self.caller: self.caller.close(); self.caller = None
        self.detach()
        self.output.with_suffix('.local.log').write_bytes(self.local)
        self.output.with_suffix('.caller.log').write_bytes(self.remote)
        self.log.close()
        os.close(self.master); os.close(self.slave)
        # On a test failure preserve live media until the next explicit cleanup.


def fixture(output):
    output.mkdir()
    p = output / 'instance'
    copy_media(BASE, p)
    return p


def tool(p, name, *args, check=True):
    return run(p/'runtime'/name, *args, check=check)


def put(p, disk, fmt, user, name, data, attrs=''):
    f = ROOT/'put.bin'; f.write_bytes(data)
    image = p/'disks'/disk
    image.chmod(0o600)
    tool(p, 'cpmrm', '-f', fmt, image, f'{user}:{name}', check=False)
    tool(p, 'cpmcp', '-f', fmt, image, f, f'{user}:{name}')
    if attrs: tool(p, 'cpmchattr', '-f', fmt, image, attrs, f'{user}:{name}')


def asm(source, name, text):
    work=ROOT/'assembly';work.mkdir(exist_ok=True)
    (work/(name+'.asm')).write_text(text)
    r=subprocess.run([str(source/'z80asm/z80asm'),'-fb','-x',name+'.asm'],cwd=work,capture_output=True)
    assert r.returncode==0,r.stderr
    return (work/(name+'.bin')).read_bytes()


def local(g, text, marker=b'A0:SYSTEM>'):
    start=len(g.local)
    for c in text.encode()+b'\r':os.write(g.master,bytes([c]));g.collect(.008)
    return g.wait(marker,start=start)


def blank(g):
    start=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote off]',start=start)


def unblank(g):
    start=len(g.local);os.write(g.master,b'\x02');g.wait(b'[Remote on]',start=start)


def auth_suite(a, module):
    # Keep shipped AUTH/MOUNT/BYE/runtime. Only original suite probe files are
    # inserted; install() is bypassed so it cannot rebuild the AUTH under test.
    def prepare(package, output, builds, runtime):copy_media(BASE,output)
    args=SimpleNamespace(package=BASE,builds=BASE/'drivers',runtime=BASE/'runtime/cpmsim',
                         tools=BASE/'runtime',source=a.source,output=ROOT/module.__name__,
                         rbbs_prompt=b'Enter your name:')
    with patch.object(module,'prepare',prepare), patch.object(module,'install',lambda *args:None), patch.object(module,'Guest',InstalledGuest):
        module.run(args)
    return json.loads((args.output/'result.json').read_text())


def boundary(a):
    import execution_checks as ex
    import shared_service_checks as protocol
    out=ROOT/'boundary';p=fixture(out)
    # Modern released layout keeps utilities in I13, not the historical B:.
    sentinel=b'PRIVATE-SECURITY-SENTINEL'
    put(p,'drivei.dsk','z80pack-hd',15,'SECRET.TXT',sentinel+b'\r\n')
    put(p,'drivei.dsk','z80pack-hd',13,'UNSAFE.COM',ex.UNSAFE,'4')
    for disk,fmt,users in [('drivea.dsk','ibm-3740',[0,1]),('drivei.dsk','z80pack-hd',[0,1]),('drivep.dsk','z80pack-hdb',[0])]:
        for user in users:put(p,disk,fmt,user,'UNSAFE.COM',ex.UNSAFE)
    put(p,'drivei.dsk','z80pack-hd',1,'RUN.SUB',b'A0:UNSAFE\r\n\x1a')
    put(p,'drivea.dsk','ibm-3740',0,'GUARD.TXT',ex.GUARD)
    execprobe=asm(a.source,'execprobe',(Path(__file__).parent/'guest/executionprobe.asm').read_text())
    put(p,'drivea.dsk','ibm-3740',0,'EXECPRB.COM',execprobe,'4')
    hostprobe=asm(a.source,'hostprobe',(Path(__file__).parent/'guest/hostprobe.asm').read_text())
    put(p,'drivea.dsk','ibm-3740',0,'HOSTPROB.COM',hostprobe,'4')
    host_sentinel=b'HOST CONTENT MUST SURVIVE\n'
    (p/'hostchk.txt').write_bytes(host_sentinel)
    aclprobe=asm(a.source,'privateacl',""" ORG 100H
 LD E,15
 LD C,32
 CALL 5
 LD HL,FUNCS
LOOP: LD A,(HL)
 OR A
 JR Z,GOOD
 LD C,A
 PUSH HL
 LD DE,F
 CALL 5
 POP HL
 CP 255
 JR NZ,BAD
 INC HL
 JR LOOP
GOOD: LD DE,OK
 JR DONE
BAD: LD DE,ERROR
DONE: PUSH DE
 LD E,0
 LD C,32
 CALL 5
 LD DE,80H
 LD C,26
 CALL 5
 POP DE
 LD C,9
 CALL 5
 RET
FUNCS: DB 15,16,17,18,19,20,21,22,23,30,33,34,35,36,40,41,42,43,59,99,100,102,103,0
F: DB 9,'SECRET  TXT'
 DS 24,0
OK: DB 'PRIVATE-BDOS-ALL-DENIED','$'
ERROR: DB 'PRIVATE-BDOS-ESCAPE','$'
""")
    put(p,'drivea.dsk','ibm-3740',0,'PRIVACL.COM',aclprobe,'4')
    # Forged F4 request and non-default DMA must not authorize an unmarked load.
    forged=asm(a.source,'forged',""" ORG 100H
 LD DE,300H
 LD C,26
 CALL 5
 LD DE,F
 LD C,59
 CALL 5
 CP 255
 JR NZ,BAD
 LD DE,WILD
 LD C,59
 CALL 5
 CP 255
 JR NZ,BAD
 LD C,49
 LD DE,SCB
 CALL 5
 LD A,L
 OR A
 JR NZ,BAD
 LD A,H
 CP 3
 JR NZ,BAD
 LD DE,GOOD
 JR DONE
BAD: LD DE,ERROR
DONE: PUSH DE
 LD DE,80H
 LD C,26
 CALL 5
 POP DE
 LD C,9
 CALL 5
 RET
SCB: DB 60,0,0,0
F: DB 1,'UNS',0C1H,'FE  ',0C3H,'OM'
 DS 24,0
WILD: DB 1,'HOSTPROBC?M'
 DS 24,0
GOOD: DB 'FORGED-F4-DENIED-DMA-PRESERVED','$'
ERROR: DB 'FORGED-F4-OR-DMA-FAILED','$'
""")
    put(p,'drivea.dsk','ibm-3740',0,'FORGED.COM',forged,'4')
    # Test-only public copy remains unapproved, as required by the shipped
    # execution policy. Approving arbitrary native code grants its I/O powers;
    # this regression tests load admission, not isolation of trusted code.
    tmp=out/'byebye.com'
    tool(p,'cpmcp','-f','z80pack-hd',p/'disks/drivei.dsk','13:BYEBYE.COM',tmp)
    put(p,'drivea.dsk','ibm-3740',0,'BYEBYE.COM',tmp.read_bytes())
    g=InstalledGuest(p,out/'console');results={}
    try:
        g.connect();
        for text in ['TYPE I15:SECRET.TXT [NO PAGE]','LT I15:SECRET.TXT','DIR I15:','TYPE SYSUTLS:AUTH.DAT','AUTH /MAP','SYSUTLS:AUTH /MAP','SYSUTLS:BYEBYE','BYEBYE','WHL SYSTEM','WHEEL SYSTEM','POKE 100 00','GET 100 A:UNSAFE.COM','GO','JUMP 100','UNSAFE','A0:UNSAFE','A1:UNSAFE','I0:UNSAFE','I1:UNSAFE','P:UNSAFE','SYSUTLS:UNSAFE','A:PATH','SUBMIT I1:RUN','I1:RUN',':GET CONSOLE','.GET CONSOLE','Z3PLUS','A:STARTZ3P','A:BYEDRIV']:
            reply=g.command(text)
            assert sentinel not in reply and ex.MARKER not in reply and b'System halted' not in reply,(text,reply)
            assert ready()['active']==1
        assert b'PRIVATE-BDOS-ALL-DENIED' in g.command('PRIVACL')
        assert b'FORGED-F4-DENIED-DMA-PRESERVED' in g.command('FORGED')
        reply=g.command('HOSTPROB')
        for marker in (b'HOST OPEN DENIED',b'HOST MAKE DENIED',b'INVALID FDC DRIVES REJECTED'):
            assert marker in reply,reply
        assert not (p/'hostnew.txt').exists()
        assert (p/'hostchk.txt').read_bytes()==host_sentinel
        results.update(private_reads_denied=True,operator_commands_and_remote_shutdown_denied=True,
                       resident_memory_and_boot_commands_denied=True,unapproved_explicit_loads_denied=True,
                       forged_F4_denied_and_DMA_preserved=True,private_BDOS_read_write_metadata_loads_denied=True,
                       raw_BDOS_wildcard_executable_load_denied=True,native_host_file_channel_denied=True,
                       invalid_FDC_drives_16_through_255_rejected=True)
        blank(g)
        assert sentinel in local(g,'LT I15:SECRET.TXT')
        assert ex.MARKER in local(g,'A0:UNSAFE')
        assert b'EXECUTION-BOUNDARY-PASS' in local(g,'EXECPRB S')
        local(g,'POKE 8000 00')
        assert b'EXECUTION-BOUNDARY-FAIL' in local(g,'EXECPRB M')
        assert b'EXECUTION-BOUNDARY-PASS' in local(g,'EXECPRB S')
        # Remote bytes must not reach a private command prompt or see its output.
        start=len(g.remote);g.caller.sendall(b'LT I15:SECRET.TXT\r');g.collect(.5)
        assert sentinel not in g.remote[start:]
        assert b'changed in memory' in local(g,'SYSUTLS:AUTH I1: R')
        local(g,'I15:',b'I15:RBBS>')
        assert ex.MARKER in local(g,'A0:UNSAFE',b'I15:RBBS>')
        unblank(g)
        # Unblanking restores caller permissions, but preserves the current DU.
        # Verify denial there before explicitly returning to the public DU.
        start=len(g.remote)
        for c in b'LT I15:SECRET.TXT\r':g.caller.sendall(bytes([c]));g.collect(.025)
        assert sentinel not in g.wait(b'I15:RBBS>',remote=True,start=start)
        g.command('A0:')
        for text in ['GO','JUMP 100','POKE 8000 00','GET 100 A:UNSAFE.COM','A0:UNSAFE']:
            assert ex.MARKER not in g.command(text)
        assert b'EXECUTION-BOUNDARY-PASS' in g.command('EXECPRB')
        assert b'COMMAND-DISK-MUST-NOT-CHANGE' in g.command('TYPE A:GUARD.TXT [NO PAGE]')
        results.update(local_private_positive_controls=True,blanked_remote_input_and_output_isolated=True,
                       private_DU_unblank_restores_caller_permissions=True,previous_local_transient_not_executable=True,
                       caller_memory_and_command_disk_probe=True)
        # Real RBBS, no stub: private capability must clear on carrier loss.
        start=len(g.remote)
        for c in b'RBBS\r':g.caller.sendall(bytes([c]));g.collect(.02)
        g.wait(b'Enter your name:',remote=True,start=start)
        def board_send(value,marker):
            start=len(g.remote)
            for c in value:g.caller.sendall(bytes([c]));g.collect(.025)
            return g.wait(marker,remote=True,start=start)
        board_send(b'SYSOP\r',b'Password:')
        password=(p/'SYSOP.DOC').read_text().split('RBBS sysop password: ')[1].splitlines()[0]
        board_send(password.encode()+b'\r',b'Command:')
        board_send(b'C',b'A0:SYSTEM>')
        assert sentinel not in g.command('LT I15:SECRET.TXT')
        assert b'changed in memory' not in g.command('SYSUTLS:AUTH I15: R')
        results['RBBS_sysop_login_and_CPM_return_do_not_grant_wheel']=True
        board_send(b'RBBS\r',b'Enter your name:')
        start=len(g.local);g.caller.close();g.caller=None;g.wait(MODEM_READY,start=start,timeout=60)
        g.remote.clear();g.connect()
        assert sentinel not in g.command('LT I15:SECRET.TXT')
        for text in ['A15:RBBS41','I15:RBBS41','SYSUTLS:BYEBYE','AUTH /MAP']:
            reply=g.command(text);assert b'Enter your name:' not in reply and sentinel not in reply
        results['real_RBBS_carrier_loss_clears_private_context']=True
        g.stop()
        guard=out/'guard-verify.txt'
        tool(p,'cpmcp','-f','ibm-3740',p/'disks/drivea.dsk','0:GUARD.TXT',guard)
        assert guard.read_bytes()==ex.GUARD
    finally:g.close()
    return results


def invalid_policy(a):
    out=ROOT/'invalid-policy';p=fixture(out)
    put(p,'drivei.dsk','z80pack-hd',13,'AUTH.DAT',b'INVALID!'+bytes(376))
    g=InstalledGuest(p,out/'console')
    try:
        g.connect()
        for text in ['HELP','TYPE A:WELCOME.TXT','SYSUTLS:AUTH /MAP','SYSUTLS:BYEBYE']:
            reply=g.command(text)
            assert b'R C P / M' not in reply and b'RCP/M caller help' not in reply
        blank(g)
        # Recover through the real private AUTH, no replacement of resident code.
        # The file must exist before boot; use another shipped valid policy copy
        # seeded below in fixture setup (never write a mounted image here).
        assert b'Policy loaded' in local(g,'SYSUTLS:AUTH /LOAD=I13:GOOD.DAT')
        unblank(g)
        assert b'R C P / M' in g.command('TYPE A:WELCOME.TXT [NO PAGE]')
        g.stop()
    finally:g.close()
    return dict(invalid_startup_policy_fail_closed=True,private_recovery_without_restart=True)


def transfers(a):
    import shared_service_checks as protocol
    from execution_checks import UNSAFE, MARKER
    out=ROOT/'transfers';p=fixture(out)
    put(p,'drivej.dsk','z80pack-hd',0,'PAYLOAD.BIN',protocol.DOWNLOAD)
    g=InstalledGuest(p,out/'console');r={}
    try:
        g.connect();protocol.upload_x(g.caller);g.wait(b'A0:SYSTEM>',remote=True,start=len(g.remote))
        protocol.upload_y(g.caller);g.wait(b'A0:SYSTEM>',remote=True,start=len(g.remote))
        protocol.download_y(g.caller);g.wait(b'A0:SYSTEM>',remote=True,start=len(g.remote))
        r.update(XMODEM_upload_CRC_retry_duplicate=True,YMODEM_batch_upload_exact_length_empty_file=True,
                 YMODEM_download_all_byte_values=True)
        # An uploaded executable must stay in host quarantine, inaccessible as
        # caller CP/M code or a downloadable file, even with an approved basename.
        assert b'UNAPPROVED-CODE-RAN' not in g.command('XFILE')
        inbox=list((p/'uploads/inbox').iterdir())
        for name,data in [('XFILE.BIN',protocol.XDATA),('YFILE.BIN',protocol.YDATA),('EMPTY.TXT',b'')]:
            matches=[f for f in inbox if f.name.startswith(name+'.')]
            assert len(matches)==1 and matches[0].read_bytes()==data,(name,[f.name for f in inbox])
        r['uploads_quarantined_exact_bytes']=True
        # Upload actual executable bytes under an already approved basename.
        # Host quarantine must not replace HELP or publish the upload to CP/M.
        body=UNSAFE.ljust(128,b'\x1a')
        g.caller.sendall(b'UPLOAD HELP.COM\r')
        protocol.until(g.caller,b'Ready for XMODEM/CRC upload (128-byte blocks).\r\n')
        protocol.expect(g.caller,b'C')
        g.caller.sendall(protocol.packet(1,body));protocol.expect(g.caller,b'\x06')
        g.caller.sendall(b'\x04');protocol.expect(g.caller,b'\x06')
        g.wait(b'A0:SYSTEM>',remote=True,start=len(g.remote))
        matches=list((p/'uploads/inbox').glob('HELP.COM.*'))
        assert len(matches)==1 and matches[0].read_bytes()==body
        reply=g.command('HELP')
        assert MARKER not in reply and len(reply)>100,reply
        assert MARKER not in g.command('I0:HELP')
        assert b'Ready for YMODEM' not in g.command('YSEND I15:USERS.CCC')
        for name in ('../EVIL.COM','/tmp/EVIL.COM','I0:EVIL.COM'):
            assert b'Ready for XMODEM' not in g.command('UPLOAD '+name)
        r['uploaded_approved_basename_cannot_replace_or_execute']=True
        r['private_download_and_upload_path_traversal_denied']=True
        protocol.partial_upload(g.caller)
        start=len(g.local);g.caller.close();g.caller=None;g.wait(MODEM_READY,start=start,timeout=60)
        assert not list((p/'uploads/staging').iterdir())
        assert not any(f.name.startswith('BROKEN.BIN.') for f in (p/'uploads/inbox').iterdir())
        g.remote.clear();g.connect();assert len(g.command('HELP'))>100
        r['partial_upload_carrier_loss_cleanup_and_reconnect']=True
        g.stop()
    finally:g.close()
    return r


def idle(a):
    out=ROOT/'idle';p=fixture(out)
    # Test-only approved transient: retain 4 MHz, set BYE idle limit to one minute.
    probe=bytes([0x3e,4,0xd3,30,0xaf,0xd3,31,0x0e,71,0x1e,1,0xcd,5,0,0xc9])
    put(p,'drivea.dsk','ibm-3740',0,'IDLESET.COM',probe,'4')
    g=InstalledGuest(p,out/'console')
    try:
        g.connect();g.command('IDLESET')
        began=last=time.monotonic();reset=False;start=len(g.local)
        while g.caller is not None:
            now=time.monotonic()
            if not reset and now-began>=30:
                g.caller.sendall(b' ');g.collect(.3);last=time.monotonic();reset=True
            assert time.monotonic()-last<67,'BYE idle expiry missing'
            g.collect(.05)
            if g.caller is None:assert time.monotonic()-last>=58,'Early idle expiry'
        seconds=time.monotonic()-last
        g.wait(MODEM_READY,start=start,timeout=60)
        assert b'[Input timed out]' in g.local[start:]
        g.remote.clear();g.connect();assert len(g.command('HELP'))>100
        g.stop()
        return dict(cpu_mhz=4,activity_reset=True,seconds_after_last_activity=round(seconds,3),
                    idle_expiry_and_reconnect=True)
    finally:g.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['setup','auth','auth-cli','flush','boundary','invalid-policy','transfers','chat','idle'])
    p.add_argument('--source',type=Path,required=True)
    a=p.parse_args()
    marker=Path('/etc/rcpm-disposable-test')
    if (os.geteuid()!=0 or not marker.is_file() or
        marker.read_text().strip()!='rcpm-local-qualification-v1' or
        not Path('/run/systemd/system').exists()):
        raise SystemExit('Refusing to run outside a root-marked disposable systemd VM')
    if a.phase=='setup':
        assert not ROOT.exists()
        assert run('systemctl','is-active','rcpm',check=False).stdout.strip()!=b'active'
        ROOT.mkdir(mode=0o700)
        run('chown','rcpm:rcpm',ROOT)
        INSTANCE.rename(BASE);INSTANCE.symlink_to(BASE)
        # Seed a valid policy for the fail-closed recovery case before boot.
        from auth_policy import MAGIC,defaults
        put(BASE,'drivei.dsk','z80pack-hd',13,'GOOD.DAT',(MAGIC+defaults()).ljust(384,b'\0'))
        print('Disposable initialized baseline retained; stopped case copies enabled.')
        return
    assert BASE.is_dir() and INSTANCE.is_symlink()
    result={}
    try:
        if a.phase in ('auth','auth-cli'):
            import check_auth,check_auth_cli
            result=auth_suite(a,check_auth if a.phase=='auth' else check_auth_cli)
        elif a.phase=='boundary':result=boundary(a)
        elif a.phase=='invalid-policy':result=invalid_policy(a)
        elif a.phase=='transfers':result=transfers(a)
        elif a.phase=='idle':result=idle(a)
        elif a.phase=='chat':
            import check_chat46
            out=ROOT/'chat';p=ROOT/'chat-instance';copy_media(BASE,p)
            check_chat46.check(SimpleNamespace(output=out),installed=lambda output:InstalledGuest(p,output))
            result=json.loads((out/'result.json').read_text())
            run('systemctl','stop','rcpm')
        elif a.phase=='flush':
            import check_flush_precaution
            # This original suite deliberately builds fault-injected AUTH/MOUNT
            # transients. They run only on copied media, never distributed.
            out=ROOT/'flush'
            with patch.object(check_flush_precaution,'Guest',InstalledGuest):
                check_flush_precaution.run(SimpleNamespace(package=BASE,tools=BASE/'runtime',assembler=a.source/'z80asm/z80asm',output=out))
            result=json.loads((out/'result.json').read_text())
        (ROOT/(a.phase+'-result.json')).write_text(json.dumps(dict(passed=True,checks=result),indent=2)+'\n')
        print(json.dumps(result,indent=2),flush=True)
    except Exception as e:
        (ROOT/(a.phase+'-failure.txt')).write_text(traceback.format_exc())
        raise


if __name__=='__main__':main()
