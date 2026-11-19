#!/usr/bin/env python3
"""Build cpmtools with direct POSIX I/O for cpmsim raw disk images."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Extracted cpmtools 2.23 source directory")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parent / "build/cpmtools")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    programs = ("cpmcp", "cpmls", "cpmrm", "mkfs.cpm")
    with tempfile.TemporaryDirectory(prefix="rcpm-raw-tools-") as temporary:
        work = Path(temporary) / "source"
        shutil.copytree(source, work, ignore=shutil.ignore_patterns(
            "*.o", "*.a", "config.log", "config.status", "config.cache",
            "config.h", "Makefile", *programs))
        driver = work / "device_posix.c"
        text = driver.read_text()
        old = "if (deviceOpts != NULL)"
        if text.count(old) != 1:
            parser.error("Unexpected device_posix.c; this builder expects cpmtools 2.23")
        # Existing project commands explicitly select raw images with -T raw.
        driver.write_text(text.replace(old,
            'if (deviceOpts != NULL && strcmp(deviceOpts, "raw") != 0)'))
        # cpmtools 2.23 selects POSIX by default. --without-libdsk incorrectly
        # treats "no" as a library path, so omit that option entirely.
        subprocess.run(["/bin/sh", "./configure", f"--prefix={output}"],
                       cwd=work, check=True)
        subprocess.run(["make", "-j4", *programs], cwd=work, check=True)
        (output / "bin").mkdir(parents=True, exist_ok=True)
        (output / "share").mkdir(exist_ok=True)
        for name in programs:
            staged = output / "bin" / (name + ".new")
            shutil.copy2(work / name, staged)
            staged.replace(output / "bin" / name)
        shutil.copy2(work / "diskdefs", output / "share/diskdefs")
        shutil.copy2(work / "COPYING", output / "COPYING")
    print(f"Built raw-image tools in {output / 'bin'}")


if __name__ == "__main__":
    main()
