#!/usr/bin/env python3
"""Build a local cpmsim console using per-instance auxiliary files."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="z80pack source tree")
    parser.add_argument("output", type=Path, help="Destination console executable")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="rcpm-console-build-") as temporary:
        build = Path(temporary)
        for directory in ("cpmsim/srcsim", "z80core", "iodevices"):
            shutil.copytree(source / directory, build / directory,
                            ignore=shutil.ignore_patterns("*.o", "*.d"))
        header = build / "cpmsim/srcsim/sim.h"
        lines = header.read_text().splitlines(keepends=True)
        definitions = [line for line in lines if line.startswith("#define PIPES")]
        if len(definitions) != 1:
            parser.error("Expected one PIPES definition in cpmsim/srcsim/sim.h")
        header.write_text("".join(line for line in lines if line not in definitions))
        # The file-backed AUX branch in cpmsim 1.39 uses the old state name.
        io_source = header.with_name("simio.c")
        io_source.write_text(io_source.read_text().replace(
            "cpu_state = STOPPED;", "cpu_state = ST_STOPPED;"))
        subprocess.run(
            ["make", "-j4", "all", f"SIM={build / 'console-runtime'}"],
            cwd=header.parent, check=True,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        # Replace atomically so an existing process can finish with its old binary.
        staged = output.with_name(output.name + ".new")
        shutil.copy2(build / "console-runtime", staged)
        staged.replace(output)
    print(f"Built {output}")


if __name__ == "__main__":
    main()
