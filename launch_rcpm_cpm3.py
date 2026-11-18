#!/usr/bin/env python3
"""Initialize and launch a dedicated, local CP/M 3 RCP/M instance."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def initialize(root, simulator, cpmcp):
    with tempfile.TemporaryDirectory(prefix=".rcpm-init-", dir=root.parent) as temporary:
        instance = Path(temporary) / "instance"
        disks = instance / "disks"
        disks.mkdir(parents=True)
        # cpmsim prefers an existing local conf directory to its shared default.
        (instance / "conf").mkdir()
        (instance / "conf/net_server.conf").write_text("# Local console only.\n")
        (instance / "conf/net_client.conf").write_text("# No client sockets.\n")
        for drive, source in (("a", "cpm3-1"), ("b", "cpm3-2")):
            shutil.copyfile(simulator.parent / "disks/library" / f"{source}.dsk",
                            disks / f"drive{drive}.dsk")
        # The bundled profile adds writable I: to the executable search path
        # and probes for a VT100 terminal. Start this instance at a plain prompt.
        cpmrm = str(Path(cpmcp).with_name("cpmrm"))
        subprocess.run([cpmrm, "-T", "raw", "-f", "ibm-3740",
                        "disks/drivea.dsk", "0:PROFILE.SUB"], cwd=instance, check=True)
        for drive, geometry, size, entries, message in (
            ("i", "z80pack-hd", 255 * 128 * 128, 1024, "WORK DRIVE I"),
            ("j", "z80pack-hd", 255 * 128 * 128, 1024, "ROTATING ARCHIVE J"),
            ("p", "z80pack-hdb", 512 * 1024**2, 8192, "PERMANENT ARCHIVE P"),
        ):
            image = disks / f"drive{drive}.dsk"
            with image.open("wb") as stream:
                stream.write(b"\xe5" * (entries * 32))
                stream.truncate(size)
            marker = Path(temporary) / "volume.txt"
            marker.write_bytes(message.encode("ascii") + b"\r\n")
            subprocess.run([cpmcp, "-T", "raw", "-f", geometry, str(image.relative_to(instance)),
                            "../volume.txt", "0:VOLUME.TXT"], cwd=instance, check=True)
            if drive != "i":
                image.chmod(0o444)
        instance.rename(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path,
                        default=Path(__file__).resolve().parent / "rcpm-cpm3")
    parser.add_argument("--cpmsim", type=Path,
                        default=Path.home() / "Downloads/z80pack-master/cpmsim/cpmsim")
    parser.add_argument("--init-only", action="store_true")
    args = parser.parse_args()
    simulator = args.cpmsim.expanduser().resolve()
    root = args.instance.expanduser().resolve()
    if not os.access(simulator, os.X_OK):
        parser.error(f"cpmsim executable unavailable at {simulator}")
    if not root.exists():
        cpmcp = shutil.which("cpmcp") or "/opt/homebrew/bin/cpmcp"
        initialize(root, simulator, cpmcp)
    if not args.init_only:
        os.chdir(root)
        os.execv(simulator, [str(simulator)])


if __name__ == "__main__":
    main()
