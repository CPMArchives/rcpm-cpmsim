#!/usr/bin/env python3
"""Prepare a Z3PLUS boot disk from a launcher-created CP/M 3 image."""
import argparse
from binascii import crc_hqx
from pathlib import Path
import shutil
import subprocess
import tempfile
import hashlib
import re


def configure_library(source, archive_names=("ARCHIVE",), extra_directories=()):
    library = bytearray(source.read_bytes())
    directory_length = int.from_bytes(library[14:16], "little") * 128
    for cpr_record in range(32, directory_length, 32):
        if library[cpr_record:cpr_record + 12] == b'\x00DEFCP3  ZRL':
            break
    else:
        raise ValueError('Z3PLUS.LBR has no DEFCP3.ZRL member')
    cpr_start = int.from_bytes(library[cpr_record + 12:cpr_record + 14], 'little') * 128
    cpr_size = int.from_bytes(library[cpr_record + 14:cpr_record + 16], 'little') * 128
    cpr = library[cpr_start:cpr_start + cpr_size]
    if hashlib.sha256(cpr).hexdigest() != '8e7887432ccd2fc422dbe3502cf46f21bdcc25bd74d79bf359e6212801e7cc06':
        raise ValueError('Unsupported command processor; recheck GET/GO/JUMP wheel protection')
    # In this supplied RCP the high bit of a command's first character
    # requires wheel privileges. WHL must not elevate a caller using the
    # distribution's published default password. BYE owns local elevation.
    for record in range(32, directory_length, 32):
        if library[record:record + 12] == b'\x00DEFRCP  ZRL':
            break
    else:
        raise ValueError('Z3PLUS.LBR has no DEFRCP.ZRL member')
    rcp_start = int.from_bytes(library[record + 12:record + 14], 'little') * 128
    rcp_size = int.from_bytes(library[record + 14:record + 16], 'little') * 128
    rcp = library[rcp_start:rcp_start + rcp_size]
    if hashlib.sha256(rcp).hexdigest() != '3c23bc048b8933935bd2ef148928de3b7e2895542ee19bf6a643cc867ed728c0':
        raise ValueError('Unsupported DEFRCP.ZRL revision for local-only WHL configuration')
    token = b'\x03WHL \x81\xb8\x08'
    if len(rcp) != rcp_size or rcp.count(token) != 1:
        raise ValueError('Unrecognized RCP wheel-command table; refusing an unprotected build')
    # Exact table context identifies the command entry, not help/password text.
    rcp[rcp.index(token) + 1] |= 0x80
    library[rcp_start:rcp_start + rcp_size] = rcp
    library[record + 16:record + 18] = crc_hqx(rcp, 0).to_bytes(2, 'little')
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
    directories = [(1, 0, "SYSTEM"), (9, 0, "WORK"), (10, 0, "VOLUME")]
    directories.extend(extra_directories)
    directories.extend((16, user, name) for user, name in enumerate(archive_names))
    for config_record in range(32, directory_length, 32):
        if library[config_record:config_record + 12] == b'\x00DEFAULT Z3P':
            config_offset = int.from_bytes(library[config_record + 12:config_record + 14], 'little') * 128
            config_size = int.from_bytes(library[config_record + 14:config_record + 16], 'little') * 128
            descriptor = library[config_offset:config_offset + config_size].decode('ascii')
            capacity = re.search(r'(?m)^Z3NDIRS\s*=\s*(\d+)\s*;', descriptor)
            break
    else:
        raise ValueError('Missing DEFAULT.Z3P named-directory allocation')
    if not capacity or len(directories) > int(capacity[1]):
        raise ValueError('Names exceed the configured Z3PLUS NDR memory allocation')
    for drive, user, name in directories:
        if not 1 <= len(name) <= 7 or not name.isascii() or not name.isalnum():
            raise ValueError("Directory names must be 1 to 7 ASCII letters or digits")
        names.extend(bytes((drive, user)) + name.upper().encode().ljust(8) + b" " * 8)
    if len(names) > size:
        # Allocate whole records at EOF without moving any other member.
        # DEFAULT.Z3P already reserves 14 entries (256 bytes). Never exceed
        # that allocation merely by growing the file loaded into it.
        size = ((len(names) + 127) // 128) * 128
        offset = ((len(library) + 127) // 128) * 128
        library.extend(b'\0' * (offset + size - len(library)))
        library[entry + 12:entry + 14] = (offset // 128).to_bytes(2, 'little')
        library[entry + 14:entry + 16] = (size // 128).to_bytes(2, 'little')
    library[offset:offset + size] = names.ljust(size, b"\0")
    library[entry + 16:entry + 18] = crc_hqx(library[offset:offset + size], 0).to_bytes(2, "little")
    library[16:18] = b"\0\0"
    library[16:18] = crc_hqx(library[:directory_length], 0).to_bytes(2, "little")
    return library


def configure_startup(source, command):
    startup = bytearray(source.read_bytes())
    original = b"A15:PATH /C $$$$ A15 A0\0"
    if startup.count(original) != 1:
        raise ValueError("Unexpected STARTZ3P command line")
    offset = startup.index(original)
    # This supplied Z-System alias has a 256-byte command slot followed by
    # executable code. Validate that boundary rather than growing the file.
    if (offset != 30 or len(startup) <= offset + 256 or startup[19] != 0xC3
            or int.from_bytes(startup[20:22], 'little') != 0x21E):
        raise ValueError("Unexpected STARTZ3P alias layout")
    if any(startup[offset + len(original):offset + 256]):
        raise ValueError("STARTZ3P command slot contains unexpected data")
    encoded = command.encode('ascii')
    if not encoded or len(encoded) > 255 or b'\0' in encoded or b'\r' in encoded or b'\n' in encoded:
        raise ValueError("Startup command must be 1-255 ASCII characters on one line")
    startup[offset:offset + 256] = (encoded + b'\0').ljust(256, b'\0')
    return startup


def prepare(images, boot_disk, output, archive_names=("ARCHIVE",), startup_command="A0:PATH /C A0"):
    base = images / "d_z3plus/u0"
    cpmcp = shutil.which("cpmcp") or "/opt/homebrew/bin/cpmcp"
    cpmrm = str(Path(cpmcp).with_name("cpmrm"))
    options = ["-T", "raw", "-f", "ibm-3740", "drivea.dsk"]
    with tempfile.TemporaryDirectory(prefix="rcpm-z3plus-") as temporary:
        work = Path(temporary)
        shutil.copyfile(boot_disk, work / "drivea.dsk")
        (work / "Z3PLUS.LBR").write_bytes(configure_library(base / "Z3PLUS.LBR", archive_names))
        (work / "STARTZ3P.COM").write_bytes(configure_startup(base / "STARTZ3P.COM", startup_command))
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
    parser.add_argument("--archive-directory", action="append", dest="archive_names",
                        help="Name successive P: user areas, starting at P0 (repeatable)")
    parser.add_argument("--rcpm-startup", action="store_true", help="Stop GET redirection, then start BYE after Z3PLUS initialization")
    args = parser.parse_args()
    prepare(args.romwbw / "Source/Images", args.boot_disk, args.output,
            args.archive_names or ("ARCHIVE",),
            "A0:PATH /C A0;A:GET CONSOLE;A:BYE" if args.rcpm_startup else "A0:PATH /C A0")


if __name__ == "__main__":
    main()
