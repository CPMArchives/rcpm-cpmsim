#!/usr/bin/env python3
"""Manage writable sysop archives and immutable caller publications."""
from contextlib import contextmanager
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid


CONFIG = "archive-publication.json"
SIZES = {"j": 255 * 128 * 128, "p": 512 * 1024**2}


@contextmanager
def console_lock(root):
    with (root / ".console.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("The local console is running. Exit CP/M with BYE first.") from None
        yield lock


def copy_image(source, target, mode):
    if sys.platform == "darwin":
        result = subprocess.run(["/bin/cp", "-c", str(source), str(target)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            shutil.copyfile(source, target)
    else:
        shutil.copyfile(source, target)
    target.chmod(mode)
    with target.open("rb") as stream:
        os.fsync(stream.fileno())


def atomic_link(target, link):
    temporary = link.with_name("." + link.name + "." + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target)
        os.replace(temporary, link)
    finally:
        temporary.unlink(missing_ok=True)


def catalog_images(root):
    if not root.is_dir():
        return []
    return sorted(path for path in root.iterdir()
                  if re.fullmatch(r"[A-Z0-9_]{1,8}\.dsk", path.name))


def install_sysop_commands(console, command):
    commands = {"MOUNT.COM": command, "BYE.COM": command.with_name("bye-sysop.com")}
    for source in commands.values():
        if not source.is_file():
            raise ValueError(f"Build the sysop commands first: {source}")
    boot = console / "disks/drivea.dsk"
    # An older launcher may have started cpmsim before console leases existed.
    # On macOS lsof also detects that legacy process before replacing its boot disk.
    lsof = shutil.which("lsof")
    if lsof is not None:
        opened = subprocess.run([lsof, "-t", "--", str(boot)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if opened.stdout.strip():
            raise RuntimeError("The local boot disk is open. Exit CP/M with BYE before setup.")
        if opened.returncode not in (0, 1):
            raise RuntimeError("Could not check whether the local boot disk is open")
    with tempfile.TemporaryDirectory(prefix=".sysop-boot-", dir=boot.parent) as temporary:
        staged = Path(temporary) / "drivea.dsk"
        copy_image(boot, staged, 0o644)
        options = ["-T", "raw", "-f", "ibm-3740", str(staged)]
        listing = subprocess.check_output(["cpmls", *options, "0:*"])
        for name, source in commands.items():
            if name.lower().encode() in listing.lower():
                subprocess.run(["cpmrm", *options, "0:" + name], check=True)
            subprocess.run(["cpmcp", *options, str(source), "0:" + name], check=True)
        os.replace(staged, boot)


def build_publication(console, callers):
    published = callers / "published"
    published.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".preparing-", dir=published) as temporary:
        staging = Path(temporary)
        disks = staging / "disks"
        disks.mkdir()
        volumes = staging / "volumes"
        volumes.mkdir()
        for drive, size in SIZES.items():
            source = console / "disks" / f"drive{drive}.dsk"
            if not source.is_file() or source.stat().st_size != size:
                raise ValueError(f"Unexpected archive geometry: {source}")
            copy_image(source, disks / source.name, 0o444)
        for source in catalog_images(console / "volumes"):
            if not source.is_file() or source.stat().st_size != SIZES["j"]:
                raise ValueError(f"Unexpected catalog image geometry: {source}")
            copy_image(source, volumes / source.name, 0o444)
        generation = published / uuid.uuid4().hex
        staging.rename(generation)
    # Readers select one complete generation through a single pointer change.
    atomic_link(generation.name, published / "current")
    return generation


def setup(console, callers, mount_command=None):
    console = console.resolve()
    callers = callers.resolve()
    if console == callers:
        raise ValueError("Console and caller installations must be separate directories")
    with console_lock(console):
        if mount_command is not None:
            install_sysop_commands(console, mount_command)
        config = console / CONFIG
        if config.exists():
            if Path(json.loads(config.read_text())["callers"]) != callers:
                raise ValueError("The console already publishes to a different caller installation")
            return (callers / "published/current").resolve(strict=True)
        # Copy the initial catalog into the sysop installation before redirecting
        # the caller catalog to its first immutable publication.
        volumes = console / "volumes"
        if volumes.is_symlink():
            raise ValueError("The sysop volumes directory must be independent of caller publications")
        if not volumes.exists():
            volumes.mkdir()
            for source in catalog_images(callers / "volumes"):
                copy_image(source, volumes / source.name, 0o644)
        generation = build_publication(console, callers)
        # Redirect both caller slots before making the sysop masters writable.
        for drive in SIZES:
            atomic_link(f"../published/current/disks/drive{drive}.dsk",
                        callers / "disks" / f"drive{drive}.dsk")
        catalog = callers / "volumes"
        if catalog.exists() and not catalog.is_symlink():
            backup = callers / "volumes-before-publication"
            if backup.exists():
                raise ValueError(f"Catalog rollback directory already exists: {backup}")
            catalog.rename(backup)
        atomic_link("published/current/volumes", catalog)
        # Use independent files, including when the old archives had hard links.
        for drive in SIZES:
            destination = console / "disks" / f"drive{drive}.dsk"
            with tempfile.TemporaryDirectory(prefix=".sysop-", dir=destination.parent) as temporary:
                staged = Path(temporary) / destination.name
                copy_image(destination, staged, 0o644)
                os.replace(staged, destination)
        metadata = {"version": 1, "callers": str(callers)}
        temporary = config.with_suffix(".json.new")
        temporary.write_text(json.dumps(metadata, indent=2) + "\n")
        os.replace(temporary, config)
        return generation


def publish(console):
    console = console.resolve()
    with console_lock(console):
        metadata = json.loads((console / CONFIG).read_text())
        return build_publication(console, Path(metadata["callers"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("setup", "publish", "status"))
    parser.add_argument("--console", type=Path, required=True)
    parser.add_argument("--callers", type=Path)
    parser.add_argument("--mount-command", type=Path, help="Install the sysop MOUNT.COM on console A:")
    args = parser.parse_args()
    console = args.console.expanduser().resolve()
    try:
        if args.operation == "setup":
            if args.callers is None:
                parser.error("setup requires --callers")
            command = args.mount_command.expanduser().resolve() if args.mount_command else None
            generation = setup(console, args.callers.expanduser().resolve(), command)
        elif args.operation == "publish":
            generation = publish(console)
        else:
            metadata = json.loads((console / CONFIG).read_text())
            generation = (Path(metadata["callers"]) / "published/current").resolve(strict=True)
        print(f"Caller archive publication: {generation}")
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Archive operation failed: {error}\n")


if __name__ == "__main__":
    main()
