#!/usr/bin/env python3
"""Probe raw TCP console 1 using a disposable stock CP/M 2.2 disk."""
import argparse
import os
import pty
import select
import shutil
import socket
import subprocess
import tempfile
import time
from pathlib import Path

# IN A,(40); AND 1; JR Z,0100h; IN A,(41); OUT (41),A; JR 0100h.
ECHO_PROGRAM = bytes.fromhex("DB 28 E6 01 28 FA DB 29 D3 29 18 F4")


def wait_for_terminal(fd, marker):
    output = bytearray()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if select.select([fd], [], [], 0.1)[0]:
            output.extend(os.read(fd, 4096))
            if marker in output:
                return
    raise RuntimeError(f"Expected {marker!r}. Terminal output: {bytes(output)!r}")


def exchange(port, label, payload):
    with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
        client.sendall(payload)
        reply = bytearray()
        while len(reply) < len(payload):
            chunk = client.recv(len(payload) - len(reply))
            if not chunk:
                break
            reply.extend(chunk)
    if reply != payload:
        raise RuntimeError(f"{label}: expected exact echo, received {len(reply)} bytes")
    print(f"PASS: {label}, all {len(reply)} bytes echoed exactly", flush=True)


def run(source, cpmcp):
    with tempfile.TemporaryDirectory(prefix="rcpm-probe-") as tmp:
        work = Path(tmp)
        (work / "disks").mkdir()
        (work / "conf").mkdir()
        disk = work / "disks/drivea.dsk"
        shutil.copyfile(source / "disks/library/cpm22-1.dsk", disk)
        program = work / "probe.com"
        program.write_bytes(ECHO_PROGRAM)
        subprocess.run(
            [cpmcp, "-f", "ibm-3740", str(disk), str(program), "0:PROBE.COM"],
            check=True,
        )
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        (work / "conf/net_server.conf").write_text(f"1 0 {port}\n")
        master, slave = pty.openpty()
        try:
            process = subprocess.Popen(
                [str(source / "cpmsim")], cwd=work,
                stdin=slave, stdout=slave, stderr=slave,
            )
            try:
                wait_for_terminal(master, b"A>")
                print("PASS: CP/M 2.2 boot", flush=True)
                os.write(master, b"PROBE\r")
                exchange(port, "first connection", bytes(range(256)))
                time.sleep(0.25)
                if process.poll() is not None:
                    raise RuntimeError("cpmsim exited after the first caller disconnected")
                exchange(port, "reconnect after client close", bytes(range(255, -1, -1)))
            except Exception:
                if select.select([master], [], [], 0)[0]:
                    print(os.read(master, 8192).decode(errors="replace"), end="")
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        finally:
            os.close(slave)
            os.close(master)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpmsim-dir", type=Path,
                        default=Path.home() / "Downloads/z80pack-master/cpmsim")
    parser.add_argument("--cpmcp", default=shutil.which("cpmcp") or "/opt/homebrew/bin/cpmcp")
    args = parser.parse_args()
    run(args.cpmsim_dir.expanduser().resolve(), args.cpmcp)
