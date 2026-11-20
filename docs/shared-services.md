# Transfers, persistent submissions and WORK in the shared machine

Status: verified on disposable CP/M 3/Z3PLUS/BYE media with direct TCP and
real tcpser. The live installation and launcher remain unchanged. This
completes part of the [architecture gates](architecture-status.md), not
the later caller-permission configuration.

## Transport and storage contract

The existing guest commands retain their service interfaces:

| Command | Guest ports, decimal | Shared-machine behavior |
| --- | --- | --- |
| `UPLOAD filename.ext` | 61 | Receive XMODEM/CRC, 128-byte records, into the operator inbox. |
| `UPLOAD /Y` | 61 | Receive a YMODEM batch; retain the declared file lengths, including empty files. |
| `YSEND J:filename.ext` or `YSEND P:filename.ext` | 63/64 | Read through guest BDOS, then send YMODEM over the modem device. |
| `MESSAGE` | 62 | Compose through BYE's console and persist the message only when saved. |

With either RCP/M backend selected, the upload/YMODEM helpers now exchange
binary bytes through the modem device. They do not read the local keyboard
or emit binary packets to the operator's terminal. The adapter polls carrier,
handles transmit backpressure and bounds protocol waits. IP232 framing remains
the modem device's responsibility. Without an RCP/M backend, the old console
transport is retained.

`upload-staging/` and `upload-inbox/` must exist in the instance directory.
They may be operator-created directories or links to directories on the same
filesystem: publication uses a hard link. Create them with private permissions.
The services retain the existing unique filename suffixes and do not replace
an existing upload. The inbox is outside the guest CP/M filesystem; uploading
does not create a caller-runnable file on I: or elsewhere in CP/M. Releasing
reviewed submissions is a later sysop workflow.

Acknowledgement of a completed upload follows file flush, fsync and atomic
publication. This is not a new claim of directory durability across power
failure. An interrupted file is unlinked from staging. YMODEM commits files
individually, so completed files remain if a later batch file is interrupted.
XMODEM cannot communicate an exact byte length; its received records retain
padding. YMODEM stores exactly the declared bytes.

OUT 73 (`49h`) discards session-only host service state: upload-name parsing,
unsaved message text and any prepared YMODEM download handle. It does not
erase committed inbox files. BYE invokes this reset during modem initialization,
LOGOFF and local exit. Private blank/unblank discards pending commands but
does not reset an in-progress message solely because its visibility changes.
Install matching newly built BYE drivers and the modem runtime together.

## Guest-safe WORK cleanup

The BYE insert now clears I0: before enabling answering, both at startup and
after a call. I0: is disposable, including during local use; store documents
that must survive in another user area. This routine never edits the mounted
disk image from the host or replaces it under the running guest.

The routine uses native CP/M 3 BDOS calls to select user zero, find individual
I: files, clear their attributes, erase them, verify the area is empty and
flush pending disk writes. Function 30 requires unambiguous filenames, so
the routine resolves each directory match before changing attributes. It
handles read-only/system files. It restores the prior user number and the
default DMA address before returning. Other I: user areas and the host inbox
are preserved. Removing files is not secure erasure of their old disk sectors.

BDOS errors are returned rather than allowed to prompt or terminate cleanup.
Failure prevents enabling answering and returns to local CP/M with
`WORK cleanup failed (step n); answering disabled.` Stages are search (1),
attribute update (2), erase (3), repeat search (4) and flush (5). File iteration
is bounded by the supported I: directory capacity. Fix the disk problem before
starting BYE again; the next attempt retries cleanup.

The direct insert prints `RCP/M modem ready.` locally after cleanup and
enabling its connection controls. Socket closure alone does not mean guest
recovery is finished. tcpser initialization likewise follows cleanup. Tests
wait for these stages before inspecting the disk or reconnecting.

The underlying BDOS contracts are documented in Digital Research's
[CP/M 3 Programmer's Guide](https://www.mrynet.com/FTP/os/CPM/manuals/cpm3-pgr.pdf),
functions 17, 19, 26, 30, 32, 45 and 48.

## Reproduce

Use the pinned z80pack and tcpser sources, the RomWBW Z3PLUS files, and the
verified raw cpmtools described elsewhere in this project:

```sh
export PATH="$PWD/build/cpmtools/bin:$PATH"
python3 build_modem_runtime.py /absolute/path/to/z80pack build/modem/cpmsim
python3 prepare_bye5.py --fetch
python3 build_bye5.py --source /absolute/path/to/z80pack
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser --romwbw /absolute/path/to/RomWBW \
  --autostart --services --output build/bye5/service-work-checks
python3 check_bye5.py --source /absolute/path/to/z80pack \
  --tcpser /absolute/path/to/tcpser --romwbw /absolute/path/to/RomWBW \
  --autostart --work-readonly --output build/bye5/work-readonly-checks
```

The runtime builder applies missing mount/upload/message/YMODEM patches in
dependency order to its temporary source copy. It accepts the already-patched
source as well. Unsupported patch contexts fail the build; the caller's
source checkout is not edited. The builder also installs the modem adapter,
service transport, host-file gate and FDC bounds check in that copy.

For each backend, the service check makes four calls in one emulator. It
verifies an XMODEM CRC rejection and duplicate-block retry, YMODEM batch
upload with exact length and an empty file, binary J: download, a saved
message, and persistent inbox contents. Later calls abort an upload midway
through a frame and abandon a message draft; neither becomes a submission.
A separate fixture tries to save any leftover draft to detect a missed reset.

Every call creates a read-only/system WORK file. Each recovery must erase it
while preserving an I1: sentinel's contents. The final recovery is checked
before shutdown too. The negative check supplies a read-only WORK disk and
requires local recovery with answering disabled. Test programs are installed
on disposable test media only; they are not the proposed caller program set.

## Remaining architecture limits

XMODEM downloads, ZMODEM and Kermit still require shared-machine integration
and protocol checks. The old console XMODEM binary must not be assumed to
work through BYE's seven-bit console. Existing raw serial interfaces can be
used by properly configured guest transfer programs.

The current host transfer helpers run synchronously during their guest OUT
call. BYE's ordinary keyboard/chat routines do not execute during that call;
immediate local cancellation and control handling during transfers remain
architecture work. Carrier loss aborts the helper and returns control to
BYE. Timeouts bound unresponsive peers; recovery from a guest that stops
polling remains a separate gate.

CHAT, live archive mounting/maintenance, host disk-write authority, local-only
shutdown, shell/ZEX/SUBMIT recovery, the single-machine launcher and final
disk-set packaging are not completed by these service checks. Caller program
and directory policy remain deferred to security configuration.
