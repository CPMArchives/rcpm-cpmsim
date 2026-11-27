"""Windows console, user-only IPC and process ownership for the optional add-on."""
import contextlib
import csv
import ctypes as c
from ctypes import wintypes as w
import difflib
import io
import os
from pathlib import Path
import subprocess


def kernel():
    return c.WinDLL('kernel32', use_last_error=True)


def sid():
    result=subprocess.run(['whoami','/user','/fo','csv','/nh'],check=True,
                          capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
    value=next(csv.reader(io.StringIO(result.stdout)))[1]
    if not value.startswith('S-1-'):raise RuntimeError('Cannot identify current Windows account')
    return value


def private_directory(path,owner):
    path=Path(path)
    if not path.is_absolute() or str(path).startswith('\\\\'):
        raise ValueError('Use a local absolute administration directory')
    k=kernel();volume=c.create_unicode_buffer(1024)
    k.GetVolumePathNameW.argtypes=[w.LPCWSTR,w.LPWSTR,w.DWORD]
    if not k.GetVolumePathNameW(str(path.parent),volume,len(volume)):
        raise c.WinError(c.get_last_error())
    flags=w.DWORD()
    k.GetVolumeInformationW.argtypes=[w.LPCWSTR,w.LPWSTR,w.DWORD,c.POINTER(w.DWORD),
                                    c.POINTER(w.DWORD),c.POINTER(w.DWORD),w.LPWSTR,w.DWORD]
    if not k.GetVolumeInformationW(volume.value,None,0,None,None,c.byref(flags),None,0):
        raise c.WinError(c.get_last_error())
    if not flags.value & 8:raise ValueError('The host volume must support persistent Windows ACLs')
    path.mkdir(parents=True,exist_ok=False)
    subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',
                    '*'+owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'],check=True,
                   capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)


@contextlib.contextmanager
def lease(path):
    """Match the launcher's share-none .console.lock, rather than a byte lock."""
    k=kernel();k.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,c.c_void_p,w.DWORD,w.DWORD,w.HANDLE]
    k.CreateFileW.restype=w.HANDLE;k.CloseHandle.argtypes=[w.HANDLE]
    handle=k.CreateFileW(str(path),0xC0000000,0,None,4,0x00200000,None)
    if handle==w.HANDLE(-1).value:raise c.WinError(c.get_last_error())
    try:yield
    finally:k.CloseHandle(handle)


def process_exited(pid,timeout=0):
    k=kernel();k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.CloseHandle.argtypes=[w.HANDLE]
    handle=k.OpenProcess(0x100000,False,pid)
    if not handle:
        if c.get_last_error()==87:return True
        raise c.WinError(c.get_last_error())
    try:return k.WaitForSingleObject(handle,int(timeout*1000))==0
    finally:k.CloseHandle(handle)


class Job:
    """All worker children die if the worker is lost; normal stop remains graceful."""
    def __init__(self):
        class Basic(c.Structure):
            _fields_=[('process_time',c.c_int64),('job_time',c.c_int64),('flags',w.DWORD),
                      ('minimum',c.c_size_t),('maximum',c.c_size_t),('count',w.DWORD),
                      ('affinity',c.c_size_t),('priority',w.DWORD),('scheduling',w.DWORD)]
        class IO(c.Structure):
            _fields_=[(n,c.c_uint64) for n in ('read_ops','write_ops','other_ops','read','write','other')]
        class Extended(c.Structure):
            _fields_=[('basic',Basic),('io',IO),('process_memory',c.c_size_t),
                      ('job_memory',c.c_size_t),('peak_process',c.c_size_t),('peak_job',c.c_size_t)]
        k=kernel();k.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD]
        k.GetCurrentProcess.restype=w.HANDLE
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        self.handle=k.CreateJobObjectW(None,None)
        if not self.handle:raise c.WinError(c.get_last_error())
        limits=Extended();limits.basic.flags=0x2000
        if not k.SetInformationJobObject(self.handle,9,c.byref(limits),c.sizeof(limits)):
            raise c.WinError(c.get_last_error())
        if not k.AssignProcessToJobObject(self.handle,k.GetCurrentProcess()):
            raise c.WinError(c.get_last_error())
        # Keep this non-inheritable handle alive until the worker process exits.


class PipeServer:
    """Message pipe with an explicit current-user/SYSTEM DACL; remote clients refused."""
    def __init__(self,address,owner,authkey):
        self.address,self.owner,self.authkey=address,owner,authkey
        self.pending=self.new_handle(True)

    def new_handle(self,first=False):
        class Security(c.Structure):
            _fields_=[('length',w.DWORD),('descriptor',c.c_void_p),('inherit',w.BOOL)]
        adv=c.WinDLL('advapi32',use_last_error=True);k=kernel();descriptor=c.c_void_p()
        adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[w.LPCWSTR,w.DWORD,c.POINTER(c.c_void_p),c.c_void_p]
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                'D:P(A;;GA;;;SY)(A;;GA;;;'+self.owner+')',1,c.byref(descriptor),None):
            raise c.WinError(c.get_last_error())
        sa=Security(c.sizeof(Security),descriptor,False)
        k.CreateNamedPipeW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,w.DWORD,c.POINTER(Security)]
        k.CreateNamedPipeW.restype=w.HANDLE;k.LocalFree.argtypes=[c.c_void_p]
        try:
            handle=k.CreateNamedPipeW(self.address,3|0x40000000|(0x80000 if first else 0),
                                     4|2|8,255,65536,65536,0,c.byref(sa))
            if handle==w.HANDLE(-1).value:raise c.WinError(c.get_last_error())
            return handle
        finally:k.LocalFree(descriptor)

    def accept(self):
        import _winapi
        from multiprocessing.connection import PipeConnection,deliver_challenge,answer_challenge
        handle=self.pending;self.pending=self.new_handle()
        try:
            try:
                operation=_winapi.ConnectNamedPipe(handle,overlapped=True)
            except OSError as error:
                if error.winerror!=_winapi.ERROR_NO_DATA:raise
            else:
                _winapi.WaitForMultipleObjects([operation.event],False,_winapi.INFINITE)
                operation.GetOverlappedResult(True)
            connection=PipeConnection(handle)
        except BaseException:
            _winapi.CloseHandle(handle);raise
        try:
            deliver_challenge(connection,self.authkey)
            answer_challenge(connection,self.authkey)
            return connection
        except BaseException:connection.close();raise


class Console:
    def __init__(self):
        class COORD(c.Structure):_fields_=[('X',w.SHORT),('Y',w.SHORT)]
        class INFO(c.Structure):
            _fields_=[('size',COORD),('cursor',COORD),('attributes',w.WORD),
                      ('window',w.SMALL_RECT),('maximum',COORD)]
        class KEY(c.Structure):
            _fields_=[('down',w.BOOL),('repeat',w.WORD),('virtual',w.WORD),
                      ('scan',w.WORD),('character',w.WCHAR),('control',w.DWORD)]
        class EVENT(c.Union):_fields_=[('key',KEY),('padding',c.c_byte*16)]
        class RECORD(c.Structure):_fields_=[('kind',w.WORD),('event',EVENT)]
        self.COORD,self.INFO,self.KEY,self.RECORD=COORD,INFO,KEY,RECORD
        self.k=kernel();self.k.GetStdHandle.argtypes=[w.DWORD];self.k.GetStdHandle.restype=w.HANDLE
        self.k.GetConsoleScreenBufferInfo.argtypes=[w.HANDLE,c.POINTER(INFO)]
        self.k.ReadConsoleOutputCharacterW.argtypes=[w.HANDLE,w.LPWSTR,w.DWORD,COORD,c.POINTER(w.DWORD)]
        self.k.WriteConsoleInputW.argtypes=[w.HANDLE,c.POINTER(RECORD),w.DWORD,c.POINTER(w.DWORD)]
        self.input=self.k.GetStdHandle(-10 & 0xffffffff);self.screen=self.k.GetStdHandle(-11 & 0xffffffff)
        self.k.SetConsoleWindowInfo.argtypes=[w.HANDLE,w.BOOL,c.POINTER(w.SMALL_RECT)]
        self.k.SetConsoleScreenBufferSize.argtypes=[w.HANDLE,COORD]
        rectangle=w.SMALL_RECT(0,0,79,23)
        if not self.k.SetConsoleWindowInfo(self.screen,True,c.byref(rectangle)):
            raise c.WinError(c.get_last_error())
        if not self.k.SetConsoleScreenBufferSize(self.screen,COORD(80,2000)):
            raise c.WinError(c.get_last_error())
        self.previous=self.rows()

    def rows(self):
        info=self.INFO()
        if not self.k.GetConsoleScreenBufferInfo(self.screen,c.byref(info)):raise c.WinError(c.get_last_error())
        first=max(0,info.cursor.Y-60);length=(info.cursor.Y-first)*info.size.X+info.cursor.X
        if not length:return []
        text=c.create_unicode_buffer(length+1);count=w.DWORD()
        if not self.k.ReadConsoleOutputCharacterW(self.screen,text,length,self.COORD(0,first),c.byref(count)):
            raise c.WinError(c.get_last_error())
        contents=text[:count.value]
        return [contents[n:n+info.size.X].rstrip() for n in range(0,len(contents),info.size.X)]

    def collect(self):
        current=self.rows();lines=[]
        for kind,_,_,first,last in difflib.SequenceMatcher(None,self.previous,current,autojunk=False).get_opcodes():
            if kind in ('insert','replace'):lines.extend(row for row in current[first:last] if row.strip())
        self.previous=current
        return ('\n'.join(lines)+'\n').encode('utf-8') if lines else b''

    def frame(self):
        info=self.INFO()
        if not self.k.GetConsoleScreenBufferInfo(self.screen,c.byref(info)):raise c.WinError(c.get_last_error())
        lines=[]
        for row in range(info.window.Top,info.window.Bottom+1):
            text=c.create_unicode_buffer(81);count=w.DWORD()
            if not self.k.ReadConsoleOutputCharacterW(self.screen,text,80,self.COORD(0,row),c.byref(count)):
                raise c.WinError(c.get_last_error())
            # Screen characters are rendered data, never terminal instructions.
            lines.append(''.join(ch if ord(ch)>=32 and ord(ch)!=127 else ' ' for ch in text[:count.value]).rstrip())
        return '\x1b[H'+'\x1b[K\r\n'.join(lines)+'\x1b[K\x1b['+str(info.cursor.Y-info.window.Top+1)+';'+str(info.cursor.X+1)+'H'

    def special(self,virtual):
        if virtual not in (33,34,35,36,37,38,39,40,45,46):raise ValueError('Unsupported console key')
        record=self.RECORD();record.kind=1;record.event.key=self.KEY(True,1,virtual,0,'\x00',0x100)
        count=w.DWORD()
        if not self.k.WriteConsoleInputW(self.input,c.byref(record),1,c.byref(count)) or count.value!=1:
            raise c.WinError(c.get_last_error())

    def write(self,data):
        for value in data:
            record=self.RECORD();record.kind=1
            record.event.key=self.KEY(True,1,0,0,chr(value),0);count=w.DWORD()
            if not self.k.WriteConsoleInputW(self.input,c.byref(record),1,c.byref(count)) or count.value!=1:
                raise c.WinError(c.get_last_error())


@contextlib.contextmanager
def terminal_output():
    k=kernel();k.GetStdHandle.argtypes=[w.DWORD];k.GetStdHandle.restype=w.HANDLE
    k.GetConsoleMode.argtypes=[w.HANDLE,c.POINTER(w.DWORD)];k.SetConsoleMode.argtypes=[w.HANDLE,w.DWORD]
    handle=k.GetStdHandle(-11 & 0xffffffff);mode=w.DWORD()
    if not k.GetConsoleMode(handle,c.byref(mode)) or not k.SetConsoleMode(handle,mode.value|4):
        raise RuntimeError('Attach requires a Windows terminal with virtual-terminal output')
    try:yield
    finally:k.SetConsoleMode(handle,mode.value)
