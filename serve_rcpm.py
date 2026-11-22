#!/usr/bin/env python3
"""Serve disposable CP/M 3 consoles over raw IPv4 TCP."""
import argparse
from contextlib import nullcontext
import errno
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import socket
import subprocess
import tempfile
import tty


def prepare_session(template, session):
    current = template / "published/current"
    archives = current.resolve(strict=True) if current.is_symlink() or current.exists() else template
    disks = session / "disks"
    disks.mkdir()
    conf = session / "conf"
    conf.mkdir()
    for kind in ("server", "client"):
        (conf / f"net_{kind}.conf").write_text("# TCP is handled by the host launcher.\n")
    volumes = archives / "disks/library"
    if volumes.is_dir():
        (session / "disks/library").symlink_to(volumes, target_is_directory=True)
    for drive in "abijp":
        name = f"drive{drive}.dsk"
        source = template / "disks" / name
        target = disks / name
        if drive in "jp":
            target.symlink_to((archives / "disks" / name).resolve(strict=True))
        else:
            shutil.copyfile(source, target)


def relay(client, terminal):
    to_client = b""
    to_guest = b""
    while True:
        readers = []
        writers = []
        if not to_guest:
            readers.append(client)
        else:
            writers.append(terminal)
        if not to_client:
            readers.append(terminal)
        else:
            writers.append(client)
        ready, writable, _ = select.select(readers, writers, [])
        if client in ready:
            to_guest = client.recv(4096)
            if not to_guest:
                return
        if terminal in ready:
            try:
                to_client = os.read(terminal, 4096)
            except OSError as error:
                if error.errno == errno.EIO:
                    return  # The PTY slave closed on platforms that report EIO.
                raise
            if not to_client:
                return
        if terminal in writable:
            try:
                to_guest = to_guest[os.write(terminal, to_guest):]
            except BlockingIOError:
                pass
        if client in writable:
            to_client = to_client[client.send(to_client):]


def serve_call(client, simulator, template, inbox=None):
    staging = (tempfile.TemporaryDirectory(prefix=".incoming-", dir=inbox)
               if inbox is not None else nullcontext())
    with staging as pending, tempfile.TemporaryDirectory(prefix="rcpm-session-") as temporary:
        session = Path(temporary)
        prepare_session(template, session)
        if pending is not None:
            (session / "uploads").mkdir(mode=0o700)
            (session / "uploads/staging").symlink_to(pending, target_is_directory=True)
            (session / "uploads/inbox").symlink_to(inbox, target_is_directory=True)
        receiver = simulator.parent / "srctools/cpmrecv"
        if os.access(receiver, os.X_OK):
            (session / "srctools").mkdir()
            (session / "srctools/cpmrecv").symlink_to(receiver)
        master, slave = pty.openpty()
        try:
            try:
                tty.setraw(slave)
                os.set_blocking(master, False)
                guest = subprocess.Popen([str(simulator)], cwd=session,
                                         stdin=slave, stdout=slave, stderr=slave,
                                         start_new_session=True)
            finally:
                os.close(slave)
            try:
                relay(client, master)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Caller hung up.
            finally:
                # Some cpmsim builds fork cpmrecv for the auxiliary device.
                # End the whole guest group when the caller disconnects.
                try:
                    os.killpg(guest.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    guest.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(guest.pid, signal.SIGKILL)
                    guest.wait()
        finally:
            os.close(master)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", type=Path,
                        default=Path(__file__).resolve().parent / "rcpm-cpm3")
    parser.add_argument("--cpmsim", type=Path,
                        default=Path.home() / "Downloads/z80pack-master/cpmsim/cpmsim")
    parser.add_argument("--inbox", type=Path, help="Enable persistent uploads to this directory")
    parser.add_argument("--bind-address", default="0.0.0.0",
                        help="Local IPv4 address, default 0.0.0.0 accepts all interfaces")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    try:
        socket.inet_pton(socket.AF_INET, args.bind_address)
    except OSError:
        parser.error("--bind-address must be an IPv4 address")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    template = args.instance.expanduser().resolve()
    simulator = args.cpmsim.expanduser().resolve()
    if not os.access(simulator, os.X_OK):
        parser.error(f"cpmsim executable unavailable at {simulator}")
    for drive in "abijp":
        image = template / "disks" / f"drive{drive}.dsk"
        if not image.is_file() or not os.access(image, os.R_OK):
            parser.error(f"disk image unavailable at {image}")
        if drive in "jp" and os.access(image, os.W_OK):
            parser.error(f"archive image must be read-only: {image}")
    inbox = args.inbox.expanduser().resolve() if args.inbox is not None else None
    if inbox is not None:
        inbox.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind_address, args.port))
            listener.listen(1)
            print(f"RCP/M listening on {args.bind_address}:{listener.getsockname()[1]}",
                  flush=True)
            while True:
                client, _ = listener.accept()
                with client:
                    serve_call(client, simulator, template, inbox)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
