#!/usr/bin/env python3
"""Verify pinned inputs and replay the macOS candidate build in a new directory."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

REPO = Path(__file__).resolve().parent


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def verify_inputs(baseline, locations):
    count = 0
    for group, files in baseline['inputs'].items():
        root = locations[group]
        for relative, expected in files.items():
            path = root / relative
            if not path.is_file() or sha(path) != expected:
                raise ValueError('Missing or changed pinned input: ' + str(path))
            count += 1
    print(f'Verified {count} pinned input files.', flush=True)


def rebuild(baseline, locations, output):
    # Refuse replacement before copying sources or invoking any build tools.
    output.mkdir(parents=True, exist_ok=False)
    work = output / 'work'
    work.mkdir()
    if (REPO / '.git').exists():
        names = subprocess.check_output(
            ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
            cwd=REPO).split(b'\0')
    else:
        # The packaged source snapshot intentionally has no Git metadata.
        paths = [p for p in REPO.iterdir() if p.is_file() and
                 (p.suffix in ('.py', '.md', '.zsh', '.json', '.command') or p.name == '.gitignore')]
        for folder in ('guest', 'emulator', 'packaging', 'patches', 'docs', 'host', 'repro'):
            paths.extend(p for p in (REPO / folder).rglob('*') if p.is_file())
        names = [os.fsencode(p.relative_to(REPO)) for p in paths]
    for name in names:
        if not name:
            continue
        relative = Path(os.fsdecode(name))
        source = REPO / relative
        if source.is_file():
            destination = work / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    staged = {}
    for group, files in baseline['inputs'].items():
        root = work / 'build' if group == 'cache' else output / 'inputs' / group
        staged[group] = root
        for relative, expected in files.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(locations[group] / relative, target)
            if sha(target) != expected:
                raise ValueError('Input changed while staging: ' + str(target))
    env = dict(os.environ, MACOSX_DEPLOYMENT_TARGET='11.0')
    # These builds run local CP/M toolchain sessions, without modem/listeners.
    env = {key: value for key, value in env.items() if not key.startswith('RCPM_')}
    env['PYTHONUNBUFFERED'] = '1'
    source = staged['z80pack']

    def run(*command):
        print('Building: ' + ' '.join(map(str, command)), flush=True)
        subprocess.run(list(map(str, command)), cwd=work, env=env, check=True)

    def python(script, *arguments):
        run(sys.executable, script, *arguments)

    run('make', '-C', source / 'z80asm', '-j4')
    python('build_raw_cpmtools.py', staged['cpmtools'], '--output', 'build/cpmtools')
    python('build_modem_runtime.py', source, 'build/modem/cpmsim')
    python('prepare_bye5.py', '--reference', staged['bye'], '--output', 'build/release-bye/sources')
    python('build_bye5.py', '--source', source, '--sources', 'build/release-bye/sources',
           '--output', 'build/release-bye')
    python('build_ppip.py', '--source', source)
    python('build_caller_tools.py', '--source', source)
    python('build_sysop_editor.py', '--source', source, '--output', 'build/sysop-editor')
    actual = {relative: sha(work / relative) for relative in baseline['guest_outputs']}
    mismatches = {relative: digest for relative, digest in actual.items()
                  if digest != baseline['guest_outputs'][relative]}
    report = dict(inputs_verified=True, guest_outputs=actual, mismatches=mismatches)
    (output / 'rebuild-result.json').write_text(json.dumps(report, indent=2) + '\n')
    if mismatches:
        raise ValueError('Rebuilt guest binaries differ from the qualified candidate: '
                         + ', '.join(mismatches) + '. See rebuild-result.json; no package was made.')
    python('build_release.py', '--source', source, '--romwbw', staged['romwbw'],
           '--bye-reference', staged['bye'], '--cpmtools-source', staged['cpmtools'],
           '--archive', staged['archive'] / 'drivep-sigm-cpmug.dsk', '--sigm', staged['sigm'],
           '--builds', 'build/release-bye', '--runtime', 'build/modem/cpmsim',
           '--tools', 'build/cpmtools/bin', '--output', output / 'candidate')
    report['packages'] = {path.name: sha(path) for path in (output / 'candidate').glob('*.zip')}
    (output / 'rebuild-result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Rebuild complete: ' + str(output / 'rebuild-result.json'), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paths', type=Path, required=True,
                        help='JSON mapping input group names to local directories; see baseline documentation')
    parser.add_argument('--baseline', type=Path, default=REPO / 'docs/release-baseline.json')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--verify-only', action='store_true')
    action.add_argument('--output', type=Path, help='New directory for a fully isolated rebuild')
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text())
    if baseline.get('format') != 'rcpm-source-baseline-1':
        parser.error('Unsupported release baseline')
    locations = {key: Path(value).expanduser().resolve()
                 for key, value in json.loads(args.paths.read_text()).items()}
    verify_inputs(baseline, locations)
    if args.output:
        rebuild(baseline, locations, args.output.expanduser().resolve())


if __name__ == '__main__':
    main()
