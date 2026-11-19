# cpmsim modem interface for BYE5

Status: implemented and tested as an isolated hardware device. Both [BYE5 builds](bye5-build.md) now pass initial Z3PLUS shared-console
checks. Wheel command-policy transitions and automatic startup now pass;
emulator privilege enforcement and production migration remain pending.
This is not a replacement remote-access program.

## Device selection

The device is additive. Existing console, serial, archive, upload and message
ports retain their handlers. Decimal ports 70-72 are reserved for the new
modem device. The build rejects conflicts with these ports.

The environment selects one backend before emulator startup:

| Variable | Meaning |
| --- | --- |
| `RCPM_MODEM` unset | Device disabled; no new sockets opened. |
| `RCPM_MODEM=direct` | Listen for callers on a raw IPv4 TCP endpoint. |
| `RCPM_MODEM=ip232` | Connect to tcpser's IP232 endpoint as an emulated computer. |
| `RCPM_MODEM_HOST` | Numeric IPv4 bind/target address; default `127.0.0.1`. |
| `RCPM_MODEM_PORT` | Required endpoint port, 1-65535. |

The direct listener is owned by cpmsim. IP232 has two distinct connections:
cpmsim connects to tcpser's virtual serial endpoint; remote callers connect
to tcpser's separate caller endpoint. An established IP232 socket is not
carrier detect. The carrier bit follows tcpser's DCD indication.

Direct mode starts with DTR and answering disabled. A guest must enable both
before a caller is admitted. Additional calls, or calls while answering is
disabled, are accepted and immediately closed. No text is injected into the
binary data channel. Device polling services acceptance and closure; there
is no network thread running guest controls asynchronously.

## Guest register contract

All port numbers below are decimal. Bits not listed read zero.

| Port | Direction | Meaning |
| --- | --- | --- |
| 70 (`46h`) | IN | Status bits below. |
| 71 (`47h`) | IN | Read one data byte; returns zero if no byte is ready. Test RX-ready first. |
| 71 (`47h`) | OUT | Send one eight-bit data byte. Test TX-ready first. |
| 72 (`48h`) | IN | Last persistent control value, bits 0/1 only. |
| 72 (`48h`) | OUT | Set DTR/answer flags; optional direct hangup pulse. |

| Status bit | Meaning |
| --- | --- |
| 0 | RX data available. |
| 1 | TX queue has space for another guest data byte. |
| 2 | Carrier detect. Direct: caller connected. IP232: tcpser DCD asserted. |
| 3 | Transport link established. IP232 can have this bit set without carrier. |
| 4 | Guest answer-enable latch. Controls admission in direct mode only. |
| 5 | Guest DTR latch. |
| 6 | Ring indication from tcpser. Direct mode has no ring/answer handshake. |

| Output control bit | Meaning |
| --- | --- |
| 0 | DTR value. Dropping it closes a direct call; IP232 sends the DTR transition to tcpser. |
| 1 | Direct answering enabled. Clearing it preserves an existing call. IP232 answering is configured through Hayes commands instead. |
| 2 | Direct hangup pulse. Does not change the two persistent control bits. IP232 hangup uses DTR low or Hayes commands. |

Examples: OUT 72 with 3 sets DTR and enables direct answering; 1 disables
new answers while keeping the current call; 0 drops DTR and disables
answering; 7 hangs up a direct caller while leaving DTR and answering enabled.

The BYE machine inserts must translate BYE's documented status conventions
onto these bits. BYE's intelligent-modem configuration handles Hayes commands
for tcpser. This device does not parse AT commands or synthesize Hayes replies.

## IP232 implementation

Reference implementation inspected and used for testing:
[go4retro/tcpser](https://github.com/go4retro/tcpser), commit
`fe7feff4862406b277e009d14c219f5d16cf1222`, `src/ip232.c` and `src/ip232.h`.

Computer-to-tcpser encodes DTR as FF 00 / FF 01. tcpser-to-computer uses
FF followed by DCD/RI flags. Literal FF data is doubled in both directions.
Control frames are removed from guest data. Parsing retains an unfinished
FF prefix across socket reads. Invalid control values are ignored.

An IP232 failure drops transport/carrier state and clears queued bytes;
subsequent guest polling retries the transport after approximately one second
and sends the current DTR state. Direct caller closure similarly clears
queues so data does not leak into the next call. There is no claim that
pending bytes are delivered after carrier loss.

Queues are bounded at 8192 bytes each. Receive backpressure leaves bytes in
the socket rather than silently overflowing the device. Nonblocking sends
retain unsent data, including partial IP232 frames. A guest writing while
TX-ready is clear violates the interface and may lose that byte, as with
an unserviced hardware transmitter. Guest code must poll readiness.

## Build and repeat the checks

From the repository root, use the pinned z80pack source described in README.
The builder copies sources to a temporary build directory, disables shared
AUX FIFOs there, integrates the device, and atomically installs only the
requested executable. It leaves the source checkout and live executables
untouched. Both stock and project-patched source layouts are supported when
the expected integration points and free ports are present.

```sh
python3 build_modem_runtime.py /path/to/z80pack build/modem/cpmsim
python3 -m unittest -v test_modem_device.py
```

The C tests compile the actual device with warnings treated as errors and
exercise sockets, including fragmented IP232 controls, all 256 byte values,
receive backpressure, reset, busy rejection and control transitions. To
include a real tcpser in those tests:

```sh
RCPM_TEST_TCPSER=/absolute/path/to/tcpser python3 -m unittest -v test_modem_device.py
```

Build tcpser from the referenced upstream checkout using `make`. It remains
an external dependency; this repository does not vendor its source or binary.
The real-tcpser test creates temporary loopback endpoints and terminates only
its own subprocess.

For actual Z80 IN/OUT verification under CP/M 3:

```sh
python3 check_modem_runtime.py --source /path/to/z80pack \
  --runtime build/modem/cpmsim \
  --cpmcp build/cpmtools/bin/cpmcp \
  --tcpser /absolute/path/to/tcpser
```

The probe assembles `guest/modemprobe.asm`, installs it on a temporary copy of
stock CP/M 3 drive A:, and removes PROFILE.SUB only from that copy to avoid
interactive startup commands. Each backend handles three calls in one
emulator process and echoes 1024 bytes per call, covering every byte value
four times. The checks observe carrier transitions, perform a local hangup,
reconnect, and return to the CP/M prompt without terminating the emulator.
The tcpser probe consumes the CONNECT result before echoing caller data.
This acceptance program is not a BYE replacement and has no caller security.

## Recorded validation, November 19, 2026

- Isolated cpmsim build succeeded on the current macOS host.
- Seven C-device tests passed with the real tcpser test enabled.
- CP/M 3 guest checks passed for direct and IP232 backends, three calls each.
- No live listener, installed disk image, or launcher configuration was changed.

## Remaining architecture and security work

The interface now supports the project machine insert and two BYE5 RSX
builds. Initial Z3PLUS, shared-keyboard and blanking checks pass. Chat,
privilege enforcement, call cleanup and the transfer/archive extensions
remain to be integrated. Current
host-console transfer helpers have not yet been moved to this modem channel.

Guest code can issue modem I/O directly. These registers do not grant sysop
archive write access, and DTR must not be treated as proof of sysop identity.
Host isolation, archive-write privilege enforcement and recovery from a guest
that stops polling remain security/lifecycle work. This isolated probe is
not a public-ready RCP/M installation.
