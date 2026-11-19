#!/usr/bin/env python3
"""Build a private 512 MiB P: archive from operator-supplied collections."""
import argparse
from binascii import crc_hqx
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def make_library(volume):
    """Package a directory as LUDEF5 LBR, retaining each member's exact bytes."""
    files = sorted(volume.iterdir())
    directory_records = (len(files) + 4) // 4
    directory = bytearray(directory_records * 128)
    for offset in range(0, len(directory), 32):
        directory[offset] = 0xff
    directory[:32] = bytes(32)
    directory[1:12] = b" " * 11
    directory[14:16] = directory_records.to_bytes(2, "little")
    records = directory_records
    payloads = []
    names = set()
    for index, file in enumerate(files, start=1):
        name = file.name.upper()
        if not file.is_file() or not re.fullmatch(r"[^.]{1,8}(\.[^.]{1,3})?", name):
            raise ValueError(f"Expected flat CP/M 8.3 member names in {volume}: {file}")
        if not name.isascii() or name in names:
            raise ValueError(f"Invalid or duplicate member name: {file}")
        names.add(name)
        stem, _, extension = name.partition(".")
        data = file.read_bytes()
        padding = -len(data) % 128
        payload = data + b"\x1a" * padding
        entry = bytearray(32)
        entry[1:12] = (stem.ljust(8) + extension.ljust(3)).encode("ascii")
        entry[12:14] = records.to_bytes(2, "little")
        entry[14:16] = (len(payload) // 128).to_bytes(2, "little")
        entry[16:18] = crc_hqx(payload, 0).to_bytes(2, "little")
        entry[26] = padding
        directory[index * 32:(index + 1) * 32] = entry
        payloads.append(payload)
        records += len(payload) // 128
    directory[16:18] = crc_hqx(directory, 0).to_bytes(2, "little")
    return directory + b"".join(payloads)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sigm", type=Path, required=True, help="Directory of SIGMVnnn.LBR files")
    parser.add_argument("--cpmug", type=Path, required=True, help="Parent of CPMUGnnn volume directories")
    parser.add_argument("output", type=Path, help="New disk image, must not already exist")
    args = parser.parse_args()
    sigm = sorted(args.sigm.glob("SIGMV[0-9][0-9][0-9].LBR"))
    cpmug = sorted(args.cpmug.glob("CPMUG[0-9][0-9][0-9]"))
    for label, entries, prefix in (("SIGM", sigm, "SIGMV"), ("CPMUG", cpmug, "CPMUG")):
        numbers = [int(file.stem[len(prefix):]) for file in entries]
        if not numbers or numbers != list(range(1, max(numbers) + 1)):
            parser.error(f"{label} must have consecutive volumes starting at 001")
    if args.output.exists():
        parser.error("Output already exists. Build a new image before publishing it.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cpmcp = shutil.which("cpmcp")
    if not cpmcp:
        parser.error("cpmcp is required")
    with tempfile.TemporaryDirectory(prefix="rcpm-archive-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        image = work / "archive.dsk"
        with image.open("wb") as stream:
            stream.write(b"\xe5" * (8192 * 32))
            stream.truncate(512 * 1024**2)
        manifest = []
        for user, volumes in ((0, sigm), (1, cpmug)):
            for volume in volumes:
                data = volume.read_bytes() if user == 0 else make_library(volume)
                filename = volume.stem.upper() + ".LBR"
                staged = work / filename
                staged.write_bytes(data)
                options = ["-T", "raw", "-f", "z80pack-hdb", str(image)]
                subprocess.run([cpmcp, *options, str(staged), f"{user}:{filename}"], check=True)
                retrieved = work / "verify.bin"
                subprocess.run([cpmcp, *options, f"{user}:{filename}", str(retrieved)], check=True)
                if retrieved.read_bytes() != data:
                    raise ValueError(f"Read-back mismatch for P{user}:{filename}")
                retrieved.unlink()
                manifest.append(f"{hashlib.sha256(data).hexdigest()}  P{user}:{filename}\n")
        image.chmod(0o444)
        # A hard link publishes the completed image without overwriting another build.
        os.link(image, args.output)
        args.output.with_suffix(".sha256").write_text("".join(manifest))
    print(f"Built {args.output}: P0 SIGM {len(sigm)} LBRs, P1 CPMUG {len(cpmug)} LBRs")


if __name__ == "__main__":
    main()
