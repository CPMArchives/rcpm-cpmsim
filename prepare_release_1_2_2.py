#!/usr/bin/env python3
"""Build the v1.2.2 foreground launcher and pinned tcpser for one platform."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile

from assemble_release_1_2_2 import build, sha

REPO = Path(__file__).resolve().parent
REVISION = 'fe7feff4862406b277e009d14c219f5d16cf1222'
SOURCE_SHA = 'b70e9b222e7dbdcc2fb0395caf444f1ddd329f5d9958b5895a5e921fed2bbc68'


def run(*args, **kwargs):
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def source(archive, destination):
    if sha(archive) != SOURCE_SHA:
        raise ValueError('Pinned tcpser source checksum mismatch')
    destination.mkdir(parents=True)
    with tarfile.open(archive) as stream:
        for entry in stream:
            parts = PurePosixPath(entry.name)
            if parts.is_absolute() or '..' in parts.parts or not (entry.isfile() or entry.isdir()):
                raise ValueError('Unsafe source archive')
            if len(parts.parts) < 2 or entry.isdir() or parts.suffix in ('.exe', '.o'):
                continue
            p = destination.joinpath(*parts.parts[1:]); p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(stream.extractfile(entry).read())
    p = destination / 'src/modem_core.c'; text = p.read_text()
    old = '    } else {\n      mdm_send_response(MDM_RESP_NO_CARRIER, cfg);\n      usleep(cfg->disconnect_delay * 1000);\n    }\n  }\n  return 0;\n}\n\nint mdm_listen'
    new = old.replace('      mdm_send_response', '      cfg->is_cmd_mode = TRUE;\n      cfg->is_off_hook = FALSE;\n      mdm_set_control_lines(cfg);\n      mdm_send_response', 1)
    if text.count(old) != 1: raise ValueError('Unrecognized modem source')
    p.write_text(text.replace(old, new))
    p = destination / 'src/bridge.c'; text = p.read_text()
    old = 'for(int i = 0; i < res ; i++) {\n        switch (buf[0]) {'
    if text.count(old) != 1: raise ValueError('Unrecognized bridge source')
    p.write_text(text.replace(old, old.replace('buf[0]', 'buf[i]')))
    (destination / 'RCPM-CHANGES.txt').write_text(
        'Base revision: '+REVISION+'\nFailed ATD restores command/on-hook state.\n'
        'Control-pipe event batches process each event in order.\n')


def prepare(platform, work, base=None, upstream=None, cygwin=None):
    work.mkdir(parents=True, exist_ok=False)
    if base is None:
        download = work / 'downloads'; download.mkdir()
        name = 'rcpm-v1.2.1-' + platform + ('.zip' if platform.startswith(('macos-', 'windows-')) else '.tar.gz')
        run('gh', 'release', 'download', 'v1.2.1', '--repo', 'CPMArchives/rcpm-cpmsim',
            '--pattern', name, '--pattern', 'SHA256SUMS', '--dir', download)
        base = download / name
        checks = {line.split()[1]: line.split()[0] for line in (download / 'SHA256SUMS').read_text().splitlines()
                  if len(line.split()) == 2}
        if checks.get(name) != sha(base): raise ValueError('Published base checksum mismatch')
    if upstream is None:
        upstream = work / 'tcpser-upstream.tar.gz'
        with upstream.open('wb') as stream:
            run('gh', 'api', 'repos/go4retro/tcpser/tarball/'+REVISION, stdout=stream)
    tcpser = work / 'tcpser'
    source(upstream, tcpser)
    extras = {'source/tcpser-upstream.tar.gz': upstream}
    if platform == 'macos-arm64':
        # The old Mac tools embed the builder's diskdefs path. Rebuild with
        # the existing package-local DISKDEFS fix used by the Linux tools.
        tool_source = work / 'cpmtools-source'
        tool_source.mkdir()
        with zipfile.ZipFile(base) as archive:
            for entry in archive.infolist():
                marker = '/source/upstream/cpmtools-2.23/'
                if marker not in entry.filename or entry.is_dir(): continue
                relative = PurePosixPath(entry.filename.split(marker, 1)[1])
                if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe tool source')
                target = tool_source.joinpath(*relative.parts); target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(entry))
        env = dict(os.environ, CFLAGS='-O2 -mmacosx-version-min=11.0')
        tools = work / 'cpmtools'
        run('python3', REPO / 'build_raw_cpmtools.py', tool_source, '--output', tools, env=env)
        for name in ('cpmcp', 'cpmls', 'cpmrm', 'cpmchattr', 'mkfs.cpm'):
            extras['runtime/'+name] = tools / 'bin' / name
    launcher = work / ('rcpm.exe' if platform.startswith('windows-') else 'rcpm')
    if platform.startswith('windows-'):
        if cygwin is None: raise ValueError('Windows build needs a build-only Cygwin toolchain path')
        os.environ['PATH'] = str(cygwin / 'bin') + os.pathsep + os.environ['PATH']
        from windows.build_support import launcher_source
        generated = work / 'launcher.c'; generated.write_text(launcher_source())
        gcc = cygwin / 'bin/x86_64-w64-mingw32-gcc.exe'
        resource = work / 'resource.o'
        run(cygwin / 'bin/x86_64-w64-mingw32-windres.exe', '-I', REPO / 'windows',
            REPO / 'windows/application.rc', '-o', resource)
        run(gcc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-D_FILE_OFFSET_BITS=64',
            '-I', REPO / 'windows', generated, resource, '-static', '-lws2_32', '-ladvapi32', '-lbcrypt', '-o', launcher)
        # POSIX modem dependency stays inside runtime/, never a sysop installation.
        bash = cygwin / 'bin/bash.exe'
        source_posix = subprocess.check_output([str(cygwin / 'bin/cygpath.exe'), '-u', str(tcpser)], text=True).strip()
        env = dict(os.environ); env['PATH'] = str(cygwin / 'bin') + os.pathsep + env['PATH']
        run(bash, '-lc', 'cd "$1" && make CC=gcc CFLAGS="-O2 -Wall -static-libgcc"', 'build', source_posix, env=env)
        modem = tcpser / 'tcpser.exe'
        extras['runtime/cygwin1.dll'] = cygwin / 'bin/cygwin1.dll'
        # Ship the exact runtime source package, rather than just a source offer.
        installed = (cygwin / 'etc/setup/installed.db').read_text()
        filename = next(line.split()[1] for line in installed.splitlines() if line.startswith('cygwin '))
        version = filename.removeprefix('cygwin-').split('.tar')[0]
        cygsrc = work / 'cygwin-source.tar.xz'
        urllib.request.urlretrieve('https://mirrors.kernel.org/sourceware/cygwin/x86_64/release/cygwin/cygwin-'+version+'-src.tar.xz', cygsrc)
        extras['source/cygwin-source.tar.xz'] = cygsrc
    else:
        flags = ['-mmacosx-version-min=11.0'] if platform.startswith('macos-') else ['-D_XOPEN_SOURCE=700']
        run('cc', *flags, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', REPO / 'packaging/launcher.c', '-o', launcher)
        run('make', '-C', tcpser, 'CC=cc', 'CFLAGS=-O2 -Wall '+(' '.join(flags) if platform.startswith('macos-') else ''))
        modem = tcpser / 'tcpser'
    root, archive = build(base, platform, launcher, modem, tcpser, work / 'package', extras)
    result = dict(platform=platform, package=str(root.resolve()), archive=str(archive.resolve()))
    (work / 'BUILT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--platform', required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--base', type=Path)
    p.add_argument('--upstream', type=Path)
    p.add_argument('--cygwin', type=Path)
    a = p.parse_args()
    prepare(a.platform, a.work.resolve(), a.base.resolve() if a.base else None,
            a.upstream.resolve() if a.upstream else None, a.cygwin.resolve() if a.cygwin else None)
