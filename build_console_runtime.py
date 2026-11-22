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
        io_text = io_source.read_text().replace("cpu_state = STOPPED;", "cpu_state = ST_STOPPED;")
        mount_open = "fd = open(path, O_RDONLY | O_NONBLOCK);"
        if io_text.count(mount_open) != 1:
            parser.error("Expected the RCP/M live-mount patch in the source tree")
        io_source.write_text(io_text.replace(mount_open,
            "fd = open(path, O_RDWR | O_NONBLOCK);"))
        # The sysop MOUNT resets J: without marking it read-only in BDOS.
        guest = build / "guest"
        guest.mkdir()
        mount_source = (Path(__file__).resolve().parent / "guest/mount.asm").read_text()
        readonly = "\tLD\tC,28\n\tCALL\tBDOS\n"
        if mount_source.count(readonly) != 1:
            parser.error("Unexpected MOUNT drive-reset sequence")
        mount_source = mount_source.replace(readonly, "").replace(
            "Volume mounted read-only on J:.", "Volume mounted read-write on J:.")
        # The shared MOUNT source already flushes before replacing media.
        (guest / "mount.asm").write_text(mount_source)
        shutil.copyfile(Path(__file__).resolve().parent / "guest/sysbye.asm", guest / "sysbye.asm")
        subprocess.run([str(source / "z80asm/z80asm"), "-fb", "-x", "mount.asm"],
                       cwd=guest, check=True)
        subprocess.run([str(source / "z80asm/z80asm"), "-fb", "-x", "sysbye.asm"],
                       cwd=guest, check=True)
        subprocess.run(
            ["make", "-j4", "all", f"SIM={build / 'console-runtime'}"],
            cwd=header.parent, check=True,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        # Replace atomically so an existing process can finish with its old binary.
        staged = output.with_name(output.name + ".new")
        shutil.copy2(build / "console-runtime", staged)
        staged.replace(output)
        shutil.copy2(guest / "mount.bin", output.with_name("mount-sysop.com"))
        shutil.copy2(guest / "sysbye.bin", output.with_name("bye-sysop.com"))
    print(f"Built {output}")


if __name__ == "__main__":
    main()
