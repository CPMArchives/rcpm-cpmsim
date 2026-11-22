#!/usr/bin/env python3
"""Add one user-0 directory marker to a copy of a J: collection image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def label_image(source, output, label, tools):
    if not re.fullmatch('[A-Z0-9_]{1,7}', label):
        raise ValueError('A directory marker name must contain 1-7 uppercase letters/digits/underscores')
    if source.stat().st_size != 4177920:
        raise ValueError('Expected an exact 4177920-byte J: image')
    if output.exists():
        raise FileExistsError(output)
    env = dict(os.environ)
    definitions = tools.parent / 'share/diskdefs'
    if definitions.exists():env['DISKDEFS'] = str(definitions.resolve())
    def run(tool, *args):
        return subprocess.check_output([str(tools / tool), '-f', 'z80pack-hd', *map(str, args)], env=env)
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def inventory(image, folder):
        rows=[];user=None
        for line in run('cpmls', image).decode('ascii').splitlines():
            name=line.strip()
            if not name:continue
            if name.endswith(':'):user=int(name[:-1]);continue
            if user is None:raise ValueError('Unrecognized directory listing')
            path=folder/(str(user)+'-'+name)
            run('cpmcp', image, str(user)+':'+name, path)
            rows.append(dict(user=user,name=name.upper(),record_bytes=path.stat().st_size,sha256=sha(path)))
        return rows
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp);(work/'before').mkdir();(work/'after').mkdir()
        before=inventory(source,work/'before')
        markers=[r['name'] for r in before if r['user']==0 and r['name'].startswith('-') and '.' not in r['name']]
        if markers and markers != ['-'+label]:
            raise ValueError('Unexpected existing user-0 marker: '+str(markers))
        original=sha(source);output.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,output)
        if sha(output)!=original or sha(source)!=original:raise ValueError('Source changed during copy')
        if not markers:
            marker=work/('-'+label);marker.write_bytes(b'\x1a')
            run('cpmcp',output,marker,'0:-'+label)
            run('cpmchattr',output,'r','0:-'+label)
        after=inventory(output,work/'after')
        old={(r['user'],r['name']):r for r in before}
        new={(r['user'],r['name']):r for r in after}
        if any(new.get(k)!=v for k,v in old.items()):raise ValueError('Existing file contents changed')
        if set(new)-set(old) != (set() if markers else {(0,'-'+label)}):raise ValueError('Unexpected added file')
        return dict(id=label,image=output.name,image_bytes=output.stat().st_size,format='z80pack-hd',
                    base_image_sha256=original,image_sha256=sha(output),directory_marker='-'+label,
                    marker_added=not bool(markers),existing_files_unchanged=True,files=after)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--label',required=True);p.add_argument('--tools',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(label_image(a.source.resolve(),a.output.resolve(),a.label,a.tools.resolve()),indent=2))
