#!/usr/bin/env python3
"""Compare synthetic image extraction with POSIX, libdsk, and patched libdsk builds."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    parser.add_argument('--posix', required=True, type=Path)
    parser.add_argument('--libdsk', required=True, type=Path)
    parser.add_argument('--patched', required=True, type=Path)
    args = parser.parse_args()
    fixtures = args.fixtures.resolve()
    cases = json.loads((fixtures / 'cases.json').read_text())
    with tempfile.TemporaryDirectory(prefix='cpmtools-raw-check-') as temporary:
        for backend in ('posix', 'libdsk', 'patched'):
            executable = getattr(args, backend).resolve()
            for case in cases:
                output = Path(temporary) / (backend + '-' + case['image'] + '.bin')
                options = [] if backend == 'posix' else ['-T', 'raw']
                subprocess.run([str(executable), *options, '-f', case['format'],
                                case['image'], case['filespec'], str(output)],
                               cwd=fixtures, check=True)
                expected = (fixtures / case['expected']).read_bytes()
                actual = output.read_bytes()
                matches = actual == expected
                should_match = case['unpatched_matches'] if backend == 'libdsk' else True
                print(f'{backend:7} {case["image"]:23} matches={matches} bytes={len(actual)}')
                if matches != should_match:
                    raise SystemExit('Unexpected result; retain the output and investigate this build.')
    print('PASS expected failures reproduced and proposed patch passes all cases')


if __name__ == '__main__':
    main()
