#!/usr/bin/env python3
"""Prepare a Z3PLUS boot disk from a launcher-created CP/M 3 image."""
import argparse
from binascii import crc_hqx
from pathlib import Path
import shutil
import subprocess
import tempfile


def configure_library(source):
    library = bytearray(source.read_bytes())
    directory_length = int.from_bytes(library[14:16], "little") * 128
    for entry in range(32, directory_length, 32):
        if library[entry:entry + 12] == b"\x00DEFAULT NDR":
            break
    else:
        raise ValueError("Z3PLUS.LBR has no DEFAULT.NDR member")
    offset = int.from_bytes(library[entry + 12:entry + 14], "little") * 128
    size = int.from_bytes(library[entry + 14:entry + 16], "little") * 128
    if size != 128 or not directory_length <= offset <= len(library) - size:
        raise ValueError("Unexpected DEFAULT.NDR layout")
    names = bytearray()
    for drive, name in ((1, b"SYSTEM"), (9, b"WORK"), (10, b"VOLUME"), (16, b"ARCHIVE")):
        names.extend(bytes((drive, 0)) + name.ljust(8) + b" " * 8)
    library[offset:offset + size] = names.ljust(size, b"\0")
    library[entry + 16:entry + 18] = crc_hqx(library[offset:offset + size], 0).to_bytes(2, "little")
    library[16:18] = b"\0\0"
    library[16:18] = crc_hqx(library[:directory_length], 0).to_bytes(2, "little")
    return library


def prepare(images, boot_disk, output):
    base = images / "d_z3plus/u0"
    cpmcp = shutil.which("cpmcp") or "/opt/homebrew/bin/cpmcp"
    cpmrm = str(Path(cpmcp).with_name("cpmrm"))
    options = ["-T", "raw", "-f", "ibm-3740", "drivea.dsk"]
    with tempfile.TemporaryDirectory(prefix="rcpm-z3plus-") as temporary:
        work = Path(temporary)
        shutil.copyfile(boot_disk, work / "drivea.dsk")
        (work / "Z3PLUS.LBR").write_bytes(configure_library(base / "Z3PLUS.LBR"))
        startup = (base / "STARTZ3P.COM").read_bytes()
        old = b"A15:PATH /C $$$$ A15 A0\0"
        if startup.count(old) != 1:
            raise ValueError("Unexpected STARTZ3P command line")
        new = b"A0:PATH /C A0"
        (work / "STARTZ3P.COM").write_bytes(startup.replace(old, new.ljust(len(old), b"\0")))
        (work / "PROFILE.SUB").write_bytes(b"Z3PLUS\r\n\x1a")
        for name in ("Z3PLUS.COM", "!(C)1988"):
            shutil.copyfile(base / name, work / name)
        for name in ("PATH.COM", "ZSHOW.COM"):
            shutil.copyfile(images / "Common/NZ3PLUS/u15" / name, work / name)
        subprocess.run([cpmrm, *options, "0:HELP.HLP"], cwd=work, check=True)
        for name in ("Z3PLUS.COM", "Z3PLUS.LBR", "STARTZ3P.COM", "PATH.COM",
                     "ZSHOW.COM", "!(C)1988", "PROFILE.SUB"):
            subprocess.run([cpmcp, *options, name, "0:" + name], cwd=work, check=True)
        with output.open("xb") as stream, (work / "drivea.dsk").open("rb") as image:
            shutil.copyfileobj(image, stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("romwbw", type=Path, help="RomWBW checkout root")
    parser.add_argument("boot_disk", type=Path, help="Stock RCP/M drive A image")
    parser.add_argument("output", type=Path, help="New Z3PLUS disk image")
    args = parser.parse_args()
    prepare(args.romwbw / "Source/Images", args.boot_disk, args.output)


if __name__ == "__main__":
    main()
