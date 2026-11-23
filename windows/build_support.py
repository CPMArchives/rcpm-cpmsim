"""Small shared helpers for native Windows cross-builds."""
from pathlib import Path
import hashlib
import re
import subprocess

REPO = Path(__file__).resolve().parent.parent


def resource(toolchain, output):
    target = output / 'application-resource.o'
    subprocess.run([str(toolchain / 'bin/x86_64-w64-mingw32-windres'),
                    '-I', str(REPO / 'windows'), str(REPO / 'windows/application.rc'),
                    '-o', str(target)], check=True)
    return target


def audit(toolchain, path, allowed):
    headers = subprocess.check_output([str(toolchain / 'bin/llvm-readobj'),
                '--file-headers', '--coff-imports', '--coff-resources', str(path)], text=True)
    if 'IMAGE_FILE_MACHINE_AMD64' not in headers:
        raise ValueError('Expected Windows x64 PE: ' + str(path))
    imports = re.findall(r'^\s*Name: ([\w.-]+\.dll)\s*$', headers, re.M | re.I)
    if not imports:
        raise ValueError('PE import audit returned no dependencies: ' + str(path))
    for name in imports:
        if name.lower() not in allowed and not name.lower().startswith('api-ms-win-crt-'):
            raise ValueError('Unexpected dependency: ' + name)
    if 'Type: MANIFEST' not in headers and 'Type: 24' not in headers:
        raise ValueError('Missing application manifest: ' + str(path))
    return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), imports=imports)


def launcher_source():
    text = (REPO / 'packaging/launcher.c').read_text()
    start = text.index('#define _POSIX_C_SOURCE')
    end = text.index('static void fail(', start)
    text = text[:start] + '#include "launcher_host.h"\n\n' + text[end:]
    for start_marker, end_marker in (
        ('static void run(char *const argv[]) {', 'static void atomic_text('),
        ('static void password(char result[25], char prefix) {', 'static void initialize('),
        ('static void location(const char *argv0) {', '/* F4 is an operator'),
    ):
        start = text.index(start_marker)
        end = text.index(end_marker, start)
        text = text[:start] + text[end:]
    for name in ('cpmrm', 'cpmcp', 'cpmchattr', 'cpmls', 'cpmsim'):
        text = text.replace('"runtime/' + name + '"', '"runtime/' + name + '.exe"')
    text = text.replace('if (lease < 0) io_fail("instance lock");',
                        'if (lease < 0) fail("This installation is already running or its lock is inaccessible.");')
    text = text.replace('initialize(); mount_disk(); driver(mode);',
        'win_private_directory("state");\n    win_private_directory("uploads");\n    win_private_directory("uploads/staging");\n'
        '    win_private_directory("uploads/inbox");\n    initialize(); mount_disk(); driver(mode);')
    text = text.replace('execv(guest[0], guest); io_fail("cpmsim"); return 1;', 'return win_process(guest, 1);')
    return text


def build_launcher(toolchain, output):
    output.mkdir(parents=True, exist_ok=False)
    source = output / 'launcher.c'
    source.write_text(launcher_source())
    res = resource(toolchain, output)
    executable = output / 'rcpm.exe'
    subprocess.run([str(toolchain / 'bin/x86_64-w64-mingw32-gcc'),
        '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-D_FILE_OFFSET_BITS=64',
        '-I', str(REPO / 'windows'), str(source), str(res),
        '-static', '-lws2_32', '-ladvapi32', '-lbcrypt', '-o', str(executable)], check=True)
    return executable


def build_probe(toolchain, output, host_object):
    output.mkdir(parents=True, exist_ok=False)
    res = resource(toolchain, output)
    executable = output / 'host-probe.exe'
    subprocess.run([str(toolchain / 'bin/x86_64-w64-mingw32-gcc'),
        '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function',
        '-D_FILE_OFFSET_BITS=64', '-I', str(REPO / 'windows'),
        str(REPO / 'windows/probe.c'), str(host_object), str(res),
        '-static', '-lws2_32', '-ladvapi32', '-lbcrypt', '-o', str(executable)], check=True)
    return executable
