"""Integrity checks and stopped-board snapshots for Windows administration."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import os
import shutil
import tempfile
import time


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):h.update(block)
    return h.hexdigest()


def safe_name(name):
    path=PurePosixPath(name)
    reserved={'CON','PRN','AUX','NUL',*(f'COM{k}' for k in range(1,10)),*(f'LPT{k}' for k in range(1,10))}
    if (not path.parts or path.is_absolute() or path.as_posix()!=name or
        any(p in ('.','..') or p.endswith((' ','.')) or p.split('.')[0].upper() in reserved for p in path.parts)
        or ':' in name or '\\' in name):raise ValueError('Unsafe manifest path')
    return path


def ordinary(path):
    info=path.lstat()
    if path.is_symlink() or getattr(info,'st_file_attributes',0)&0x400:
        raise ValueError('Reparse points and symbolic links are refused')
    if not (path.is_dir() or path.is_file()):raise ValueError('Special files are refused')


def files(root):
    result={}
    ordinary(root)
    for path in sorted(root.rglob('*')):
        ordinary(path)
        if path.is_file():result[path.relative_to(root).as_posix()]=sha(path)
    return result


def verify_files(root,records,receipt=None):
    if not isinstance(records,dict) or not records:raise ValueError('Invalid empty manifest')
    for name in records:safe_name(name)
    actual=files(root)
    if receipt:actual.pop(receipt,None)
    if actual!=records:raise ValueError('Missing, changed or unrecorded files')
    return records


def validate(addon,base):
    receipt=json.loads((addon/'metadata/ADDON.json').read_text())
    verify_files(addon,receipt['files'],'metadata/ADDON.json')
    manifest=json.loads((base/'metadata/MANIFEST.json').read_text())
    if manifest.get('platform')!='windows-x64' or manifest.get('version')!='v1.2.2':
        raise ValueError('Use the standard Windows x64 RCP/M 1.2.2 package')
    records={**manifest['common'],**manifest['host']}
    verify_files(base,records,'metadata/MANIFEST.json')
    for name,h in receipt['base_runtime_media_sha256'].items():
        if records.get(name)!=h:raise ValueError('Incompatible base runtime or media')
    for name in ('runtime/rcpm.exe','runtime/tcpser.exe'):
        with (base/name).open('rb') as stream:
            header=stream.read(64)
            if header[:2]!=b'MZ':raise ValueError('Missing Windows executable')
            stream.seek(int.from_bytes(header[60:64],'little'))
            if stream.read(6)!=b'PE\0\0\x64\x86':raise ValueError('Expected Windows x64 executables')
    return receipt


def atomic(path,value):
    temporary=path.with_name(path.name+'.tmp-'+os.urandom(8).hex())
    try:
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        deadline=time.monotonic()+2
        while True:
            try:os.replace(temporary,path);break
            except PermissionError:
                if time.monotonic()>=deadline:raise
                time.sleep(.025)
    finally:temporary.unlink(missing_ok=True)


def snapshot(root,destination):
    from win_platform import lease,private_directory,sid
    root,destination=root.resolve(),destination.resolve()
    if destination.exists() or destination==root or root in destination.parents:
        raise ValueError('Snapshot requires a new destination outside the board')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with lease(root/'.console.lock'),tempfile.TemporaryDirectory(prefix='.rcpm-backup-',dir=destination.parent) as tmp:
        stage=Path(tmp)/'snapshot';private_directory(stage,sid())
        payload=stage/'instance';payload.mkdir();records={}
        for path in sorted(root.rglob('*')):
            relative=path.relative_to(root)
            if relative.parts[0] in ('.console.lock','.service.lock'):continue
            ordinary(path);target=payload/relative
            if path.is_dir():target.mkdir()
            else:
                before=path.stat()
                with path.open('rb') as src,target.open('xb') as dst:
                    for block in iter(lambda:src.read(1048576),b''):
                        if block.count(0)==len(block):dst.seek(len(block),1)
                        else:dst.write(block)
                    dst.truncate(before.st_size);dst.flush();os.fsync(dst.fileno())
                after=path.stat()
                if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
                    raise RuntimeError('Board changed during snapshot')
                records[relative.as_posix()]=sha(target)
        atomic(stage/'snapshot.json',records);verify(stage);stage.rename(destination)


def verify(backup):
    ordinary(backup)
    records=json.loads((backup/'snapshot.json').read_text())
    return verify_files(backup/'instance',records)


def restore(backup,destination):
    backup,destination=backup.resolve(),destination.resolve()
    if destination.exists() or destination==backup or backup in destination.parents:
        raise ValueError('Restore requires a new directory outside the snapshot')
    records=verify(backup);destination.parent.mkdir(parents=True,exist_ok=True)
    from win_platform import private_directory,sid
    with tempfile.TemporaryDirectory(prefix='.rcpm-restore-',dir=destination.parent) as tmp:
        stage=Path(tmp)/'board';private_directory(stage,sid())
        shutil.copytree(backup/'instance',stage,dirs_exist_ok=True)
        verify_files(stage,records);stage.rename(destination)
