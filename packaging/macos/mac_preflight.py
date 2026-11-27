"""Read-only validation of the optional Mac add-on and standard base archive."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for b in iter(lambda:stream.read(1048576),b''):h.update(b)
    return h.hexdigest()


def verify(root,expected,manifest_name):
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink() or not (p.is_file() or p.is_dir()):raise ValueError('Unexpected package entry: '+str(p))
        if p.is_file() and p.name!='.DS_Store' and not p.name.startswith('._'):
            actual.add(p.relative_to(root).as_posix())
    if actual!=set(expected)|{manifest_name}:raise ValueError('Missing or unrecorded package files')
    for n,h in expected.items():
        name=Path(n)
        if name.is_absolute() or '..' in name.parts or digest(root/name)!=h:raise ValueError('Checksum mismatch: '+n)


def validate(addon,base):
    if sys.platform!='darwin':raise ValueError('macOS required')
    receipt=json.loads((addon/'metadata/ADDON.json').read_text())
    verify(addon,receipt['files'],'metadata/ADDON.json')
    manifest=json.loads((base/'metadata/MANIFEST.json').read_text())
    if manifest.get('platform')!='macos-arm64' or manifest.get('version')!='v1.2.2':
        raise ValueError('Use the standard macOS ARM64 v1.2.2 package')
    verify(base,{**manifest['common'],**manifest['host']},'metadata/MANIFEST.json')
    for n,h in receipt['base_runtime_media_sha256'].items():
        if digest(base/n)!=h:raise ValueError('Incompatible base package: '+n)
    subprocess.run([str(base/'runtime/rcpm'),'--check'],check=True)
    header=(base/'runtime/tcpser').read_bytes()[:8]
    if header[:4]!=b'\xcf\xfa\xed\xfe' or int.from_bytes(header[4:8],'little')!=0x100000c:
        raise ValueError('Expected the native ARM64 bundled modem')
    return receipt
