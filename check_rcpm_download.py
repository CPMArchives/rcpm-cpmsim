#!/usr/bin/env python3
"""Verify an XMODEM/CRC download against a local record-aligned fixture."""
import argparse
from binascii import crc_hqx
from pathlib import Path
import re
import socket

PROMPT = b"A0:SYSTEM>"
RECORD_SIZE = 128


def wait_for(stream, marker):
    output = bytearray()
    while not output.endswith(marker):
        byte = stream.read(1)
        if not byte:
            raise RuntimeError(f"Connection closed while waiting for {marker!r}")
        output.extend(byte)
        if marker != PROMPT and output.endswith(PROMPT):
            raise RuntimeError(output.decode("ascii", errors="replace").strip())
    return bytes(output)


def verify(client, stream, filename, reference, volume):
    wait_for(stream, PROMPT)
    if volume:
        client.sendall(f"MOUNT {volume}\r".encode("ascii"))
        response = wait_for(stream, PROMPT)
        if b"Volume mounted read-only on J:." not in response:
            raise RuntimeError(response.decode("ascii", errors="replace").strip())

    client.sendall(f"XMODEM {filename} /S /Q /X0\r".encode("ascii"))
    wait_for(stream, b"Sending via CON")
    client.sendall(b"C")
    for offset in range(0, len(reference), RECORD_SIZE):
        block = (offset // RECORD_SIZE + 1) & 0xff
        header = bytes((1, block, block ^ 0xff))
        packet = stream.read(3 + RECORD_SIZE + 2)
        if len(packet) != 3 + RECORD_SIZE + 2 or packet[:3] != header:
            raise RuntimeError(f"Unexpected XMODEM header at byte {offset}")
        data = packet[3:-2]
        if crc_hqx(data, 0) != int.from_bytes(packet[-2:], "big"):
            raise RuntimeError(f"XMODEM CRC mismatch at byte {offset}")
        if data != reference[offset:offset + RECORD_SIZE]:
            raise RuntimeError(f"Reference mismatch at byte {offset}")
        client.sendall(b"\x06")
    if stream.read(1) != b"\x04":
        raise RuntimeError("Expected end of transfer after the last reference record")
    client.sendall(b"\x06")
    wait_for(stream, PROMPT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=str.upper, help="CP/M filespec on J: or P:")
    parser.add_argument("reference", type=Path, help="Local copy of the expected bytes")
    parser.add_argument("--volume", type=str.upper, help="Mount this J: volume first")
    parser.add_argument("--port", type=int, default=4000)
    args = parser.parse_args()
    if not re.fullmatch(r"[JP]:[A-Z0-9_]{1,8}(\.[A-Z0-9_]{1,3})?", args.file):
        parser.error("expected a J: or P: filespec using letters, digits, and underscores")
    if args.volume and (not args.file.startswith("J:") or
                        not re.fullmatch(r"[A-Z0-9_]{1,8}", args.volume)):
        parser.error("--volume requires a J: filespec and a valid volume name")
    reference = args.reference.read_bytes()
    if not reference or len(reference) % RECORD_SIZE:
        parser.error("reference must contain one or more complete 128-byte CP/M records")
    try:
        with socket.create_connection(("127.0.0.1", args.port), timeout=8) as client:
            with client.makefile("rb") as stream:
                verify(client, stream, args.file, reference, args.volume)
    except (RuntimeError, OSError) as error:
        parser.exit(1, f"Download check failed: {error}\n")
    print(f"PASS: {args.file}, {len(reference)} bytes match over XMODEM/CRC")


if __name__ == "__main__":
    main()
