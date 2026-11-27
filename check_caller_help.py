#!/usr/bin/env python3
"""Read every shipped topic with the preserved HELPC viewer as a caller."""
import argparse
import json
from pathlib import Path
from caller_help import install
from check_bye_speed import prepare
from check_release import Guest, free_port


def run(args):
    args.output.mkdir(parents=True, exist_ok=False)
    instance = args.output / 'instance'
    prepare(args.package, instance, args.builds, args.runtime)
    topics = install(instance, args.tools)
    port = free_port()
    guest = Guest(instance, args.output/'console', '--port', str(port))
    outputs = {}
    try:
        guest.wait(b'RCP/M modem ready.')
        guest.connect(port)
        listing = guest.command('DIR HELP:')
        assert b'HELP' in listing and b'TRANSFER' in listing, listing
        for filename in topics:
            name = Path(filename).stem
            expected = (Path(__file__).parent/'guest/help'/filename).read_text().splitlines()[1].encode()
            command = 'HELP' if name == 'HELP' else 'HELP '+name
            reply = guest.help_topic(command, expected)
            assert expected in reply, (command, reply)
            outputs[command] = reply.decode('ascii', errors='replace')
            print(command+' PASS', flush=True)
        guest.stop()
    finally:
        guest.close()
    (args.output/'result.json').write_text(json.dumps(dict(passed=True, outputs=outputs),indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name, default in (('package','build/release-auth-guide/RCPM-macOS-arm64'),
                          ('tools','build/release-tools/bin'),
                          ('builds','build/bye5-writeonly'),
                          ('runtime','build/modem/cpmsim')):
        parser.add_argument('--'+name, type=Path, default=Path(default))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name,value in vars(args).items():
        setattr(args,name,value.resolve())
    run(args)
