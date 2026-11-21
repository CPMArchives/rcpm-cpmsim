# Development history and prototype setup

This is the former project README, preserved as an engineering record. It
contains successive prototypes, superseded layouts and historical test results.
Commands and status statements describe their original development stages;
they are not the installation instructions for the released system.

For the current project introduction and downloads, see the [project README](../README.md).
For current technical documentation, see the [documentation index](README.md).
The release ZIP includes INSTALLATION.DOC and SYSOP-GUIDE.DOC.

---

# RCP/M on cpmsim

The [1.0 release notes](RELEASE-NOTES-1.0.md) describe the macOS ARM64
and Windows x64 downloads, startup and tested limits. The
[release plan](release-1.0-plan.md) records qualification evidence.
The [source baseline](source-baseline.md) pins the qualified candidate's
inputs and documents the verified isolated rebuild.

Current administration: [AUTH drive/DU permissions](caller-execution.md).
All drives share one default-deny caller R/W policy. Private sysop mode permits
maintenance; caller execution requires R, no W, and F4. AUTH.COM in I13:
changes permissions and executable approval live; AUTH /SAVE persists the map.
Older build-history sections below describe preceding implementation stages.


The **distribution** is a foreground cpmsim session, without Python or tmux
prerequisites. The common A:/I:/P: payload includes all 310 SIGM and 93 CPMUG
libraries, with public GAMES and documentation-only GUIDES volumes for J:.
See [release packaging](release-packaging.md). The tmux launcher below
is the operator’s local convenience workflow, separate from the package.
See the [post-1.0 roadmap](roadmap.md) for configurable CPU speed, retaining
the 4 MHz default, and the [online-game execution policy](online-games.md) for
game-specific caller admission.

The default `launch_rcpm.zsh` now starts or attaches to one shared CP/M 3 /
Z3PLUS / BYE510 machine in tmux (`rcpm-shared`). The default installation is
`build/upper-system-final`, listening on **127.0.0.1:4002**. Its local console
and caller use the same guest and disks.

See [current operation and backup/restore](shared-operations.md) for the
one-time transition from a manually started console, detachment, shutdown,
verified backups, restoration and the `rcpm` wrapper update.

The [upper-area system profile](zsystem-utilities.md) builds fresh media
with I0:WORK, I13:SYSUTLS, I14:HELP and I15:RBBS. Callers enter `RBBS` from A0:;
system tools and board data remain private. Caller programs, A0: attributes,
ZDE configuration and the shared host helpers are included in new builds.

Backup/restore has been checked with populated RBBS media and a caller login
to the restored guest. Real tmux attachment still needs an operator check:
the development sandbox denies access to the tmux server.

## Earlier separate-instance prototype

The remainder records the earlier architecture and build investigations.
Commands referring to publication, separate caller instances, or the
`rcpm-console` / `rcpm-listener` sessions belong to **`launch_legacy_rcpm.zsh`**.
They are not the current shared launcher workflow. Historical trial instructions
may also describe the old B: / I2: layout; use the upper-area profile above.

A Remote CP/M system in development for the CPMArchives software collection.
Callers will land directly at the CP/M prompt. The local prototype uses
banked CP/M 3 on Udo Munk’s z80pack cpmsim and Z3PLUS for named directories.

| Drive | Role | Capacity |
| --- | --- | --- |
| I: | Writable work disk. One caller-writable user area is planned, with uploads and messages submitted through dedicated utilities. | Nominal 4 MB |
| J: | Rotating archive. Callers mount read-only published volumes. The sysop maintains writable masters after setup. | Nominal 4 MB |
| P: | Permanent software archive. Published read-only for callers, with a separate writable sysop master after setup. | 512 MiB |

## 1. Bring up CP/M 3

Use Python 3, cpmtools with the `ibm-3740`, `z80pack-hd`, and `z80pack-hdb`
disk definitions, and a built [z80pack](https://github.com/udo-munk/z80pack)
cpmsim with its bundled CP/M 3 disk images. The prototype was verified on
macOS with cpmsim 1.39.

For raw cpmsim image maintenance, use the project's POSIX cpmtools build.
A same-source cpmtools 2.23 comparison showed that the libdsk-backed build
misread a guest-created 4 MB I: file, while the POSIX build returned all
324352 bytes correctly with the same disk definition. The guest-written
allocation blocks also matched the source bytes. Keep using `z80pack-hd`
for I:/J: and `z80pack-hdb` for P:.

Download and extract the official source, then build the local tools.
The source tarball used for this check has SHA-256
`7839b19ac15ba554e1a1fc1dbe898f62cf2fd4db3dcdc126515facc6b929746f`.

```sh
mkdir -p build
curl -L --fail https://www.moria.de/~michael/cpmtools/files/cpmtools-2.23.tar.gz \
  -o build/cpmtools-2.23.tar.gz
printf '%s  %s\n' \
  7839b19ac15ba554e1a1fc1dbe898f62cf2fd4db3dcdc126515facc6b929746f \
  build/cpmtools-2.23.tar.gz | shasum -a 256 -c -
tar -xzf build/cpmtools-2.23.tar.gz -C build
python3 build_raw_cpmtools.py build/cpmtools-2.23
export PATH="$PWD/build/cpmtools/bin:$PATH"
```

The builder copies the source into a temporary directory and selects its
default POSIX backend. It adds support for the explicit `-T raw` spelling
used by this guide. It installs the four maintenance commands and the
upstream disk definitions under `build/cpmtools`. It includes the upstream
license there. The tmux launcher adds this local tools directory to PATH.
For manual image commands, repeat the PATH export in new shells.

```sh
python3 launch_rcpm_cpm3.py --cpmsim /path/to/z80pack/cpmsim/cpmsim
```

The launcher copies the stock boot media, creates the three data drives, and
opens the local console. It starts CP/M 3 with network listeners disabled.
`TYPE I:VOLUME.TXT` and `TYPE J:VOLUME.TXT` identify the work and rotating
volumes. P: starts as an empty filesystem for the operator to populate.
The archive image files are created without host write permission.

## 2. Add Z3PLUS

Obtain [RomWBW](https://github.com/wwarthen/RomWBW). The input files were
verified at commit `cb887a1a2191072dff952bfa836a8dca201b1450`. After exiting
cpmsim, run the following commands from this repository.

```sh
python3 prepare_z3plus.py /path/to/RomWBW \
    rcpm-cpm3/disks/drivea.dsk rcpm-cpm3/drivea-z3plus.dsk
cp -n rcpm-cpm3/disks/drivea.dsk rcpm-cpm3/drivea-cpm3-original.dsk
cp rcpm-cpm3/drivea-z3plus.dsk rcpm-cpm3/disks/drivea.dsk
```

The new boot disk starts Z3PLUS at `A0:SYSTEM>`. It maps `WORK:` to `I0:`,
`VOLUME:` to `J0:`, and `ARCHIVE:` to `P0:`. To fit Z3PLUS, the
preparation step removes the stock `HELP.HLP` from the generated image.
The original boot image remains available for rollback.

The configured command search path is `A0:`. Explicitly qualified commands
on other drives are still possible. This configuration is a local prototype
and requires caller access controls before public operation.

## 3. Try a remote session on loopback

Exit the local cpmsim before starting this test. Some z80pack builds share
auxiliary-device FIFOs between instances on the same host. Use the verified
Z3PLUS instance as a template and leave it idle while the listener runs.
If your cpmsim build uses those FIFOs, build `srctools/cpmrecv` alongside it.

Start the listener in one terminal:

```sh
python3 serve_rcpm.py --cpmsim /path/to/z80pack/cpmsim/cpmsim --bind-address 127.0.0.1
```

This command accepts raw TCP on IPv4 loopback, port 4000 by default. In another
terminal, connect using a raw TCP terminal client that sends carriage returns.
With macOS netcat, use a subshell that sends Return as a single CR and
restores your terminal settings afterward:

```sh
(
    saved_tty=$(stty -g)
    trap 'stty "$saved_tty"' EXIT
    stty -icanon -echo -icrnl
    nc 127.0.0.1 4000
)
```

1. Wait for `A0:SYSTEM>`.
2. Enter `ARCHIVE:` and wait for `P0:ARCHIVE>`. Enter `DIR`.
   A new installation should report no files on P:.
3. Enter `VOLUME:` and wait for `J0:VOLUME>`. Enter `TYPE VOLUME.TXT`.
   The guest should print `ROTATING ARCHIVE J`.
4. Disconnect the client, then reconnect. A new guest should boot to
   `A0:SYSTEM>`. Stop the listener with Ctrl-C when finished.

Each call uses temporary copies of A:, B:, and I:. Writes to those copies
are discarded when the caller disconnects. J: and P: use the read-only
template images. Only one guest runs at a time. Persistent caller work,
login, guest logoff, and public access are still open.

## 4. Enable live mounting on J:

Use a separate checkout of [z80pack](https://github.com/udo-munk/z80pack)
at commit `91fd28eb04e675c2127df88ed3f40675e15282e2`. From the RCP/M
repository, set `z80pack` to the absolute path of that checkout, then build
the patched emulator and assemble the guest command.

```sh
z80pack=/absolute/path/to/z80pack
git -C "$z80pack" apply "$PWD/patches/cpmsim-live-mount.patch"
make -C "$z80pack/cpmsim/srcsim"
make -C "$z80pack/cpmsim/srctools" cpmrecv
make -C "$z80pack/z80asm"
mkdir -p build
cp guest/mount.asm build/
(cd build && "$z80pack/z80asm/z80asm" -fb -x mount.asm)
```

With the guest and listener stopped, install the command on the Z3PLUS
template's boot disk and put approved archive images in its volume catalog.

```sh
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/mount.bin 0:MOUNT.COM
mkdir -p rcpm-cpm3/volumes
cp /path/to/utilities.dsk rcpm-cpm3/volumes/UTILS.dsk
cp /path/to/games.dsk rcpm-cpm3/volumes/GAMES.dsk
```

Use raw `z80pack-hd` volumes, each exactly 4,177,920 bytes, and name them
with one to eight uppercase letters, digits, or underscores followed by
`.dsk`. The emulator checks the image type and size and opens the replacement
read-only. Check each volume in CP/M 3 before adding it to the catalog.
The byte-size check alone cannot validate the directory or allocation data.

Start the listener with the patched emulator:

```sh
python3 serve_rcpm.py --cpmsim "$z80pack/cpmsim/cpmsim"
```

1. Connect as in step 3. Enter `MOUNT /L` to see the current J: volume
   and the available names. Enter `MOUNT UTILS`, change to `VOLUME:`, and
   inspect the files on J:.
2. Enter `MOUNT GAMES` and inspect J: again. To verify that CP/M 3 relogs
   the drive, put a different `VOLUME.TXT` on each image and read it after
   each swap while staying at the J: prompt.
3. Enter `MOUNT MISSING`. J: should retain the previously mounted volume.
   `MOUNT /L` should still report that volume as current.
   `DIR P:` should show the permanent archive contents, or no files on a
   fresh installation.
4. Reconnect and verify J: starts with the default `drivej.dsk` again.

`MOUNT` replaces only J:. On success it resets J:'s BDOS login state and
marks it read-only again before restoring the original selected drive.
A failed request leaves the guest and emulator drive state intact.

## 5. Verify binary downloads

With the guest and listener stopped, extract M. Eberhard's XMODEM 2.7 from
the z80pack IMSAI communications image. On the prototype Z3PLUS boot disk,
remove the stock `HELP.COM` to free space for it and for startup scratch
files. The Z3PLUS preparation already removed the stock `HELP.HLP`.

```sh
cpmcp -T raw -f ibm-3740 "$z80pack/imsaisim/disks/library/comms.dsk" 0:XMODEM.COM build/xmodem.com
cpmrm -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk 0:HELP.COM
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/xmodem.com 0:XMODEM.COM
```

Start the listener as in step 4. From a raw-TCP terminal with XMODEM/CRC
receive support, enter `XMODEM P:PAYLOAD.BIN /S /Q /X0` and start
XMODEM/CRC receive when the guest says `Sending via CON`. For J:, mount
the desired volume first and substitute `J:PAYLOAD.BIN`.

For a reproducible byte check, put a known, record-aligned payload on each
archive and run these commands from the host. The checker connects, starts
the transfer, checks each packet CRC, and compares every byte against the
local fixture. XMODEM sends whole 128-byte records.

```sh
python3 check_rcpm_download.py P:PAYLOAD.BIN /path/to/p-reference.bin
python3 check_rcpm_download.py J:PAYLOAD.BIN /path/to/j-reference.bin --volume GAMES
```

If the host image writer and CP/M 3 disagree on the contents of a 4 MB
volume, populate a writable image of that geometry in the guest using
`PIP`, then stop cpmsim and copy the image into the volume catalog. We
used this procedure to prepare the verified J: binary fixture.

## 6. Enable persistent uploads

Apply the uploads patch **after the current live-mount patch** from step 4.
Rebuild cpmsim, assemble the guest command, and install it while the
listener and guest are stopped.

```sh
git -C "$z80pack" apply "$PWD/patches/cpmsim-uploads.patch"
make -C "$z80pack/cpmsim/srcsim"
cp guest/upload.asm build/
(cd build && "$z80pack/z80asm/z80asm" -fb -x upload.asm)
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/upload.bin 0:UPLOAD.COM
```

Start the loopback listener with the rebuilt emulator and an operator-owned
inbox on a filesystem that supports hard links.

```sh
python3 serve_rcpm.py --cpmsim "$z80pack/cpmsim/cpmsim" --inbox rcpm-cpm3/inbox
```

In a raw-TCP terminal client, enter `UPLOAD SAMPLE.BIN` and start
XMODEM/CRC send with 128-byte blocks when the guest says it is ready.
The upload goes directly to the host inbox. The receiver makes the file
visible in the inbox before acknowledging the end of the transfer. The
operator can find it under `SAMPLE.BIN.<unique suffix>`; repeat uploads
receive separate filenames. The receiver accepts up to 4 MiB. XMODEM
stores complete records, including any padding the sender adds.

Disconnect after a successful upload and verify that the inbox file
remains. Disconnect partway through a second transfer and verify that no
file for the interrupted transfer appears. Open a new session and check
that changes made to `WORK:` by the previous caller are gone. The session
starts from the operator's I: template on each connect.

The inbox is for operator review. Keep it outside the rotating-volume
catalog and inspect submissions there before adding any to the archives.

## 7. Enable private messages to the operator

Apply the messages patch after the uploads patch from step 6. With the
listener and guest stopped, rebuild cpmsim and install the guest command.

```sh
git -C "$z80pack" apply "$PWD/patches/cpmsim-messages.patch"
make -C "$z80pack/cpmsim/srcsim"
cp guest/message.asm build/
(cd build && "$z80pack/z80asm/z80asm" -fb -x message.asm)
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/message.bin 0:MESSAGE.COM
```

Start the loopback listener with `--inbox` as in step 6. From the guest,
enter `MESSAGE` to write up to 20 lines of 72 columns. Enter `/S` on its
own line to save or `/C` to discard the draft. The operator receives each
saved message as a separate `MESSAGE.TXT.<unique suffix>` file in the
inbox alongside completed uploads. Disconnecting before saving discards
the draft. Z-System's `NOTE` remains available for script comments.

## 8. Enable YMODEM

Apply the YMODEM patch after the messages patch and rebuild cpmsim.
With the listener and guest stopped, replace the installed upload command
and add the download command.

```sh
git -C "$z80pack" apply "$PWD/patches/cpmsim-ymodem.patch"
make -C "$z80pack/cpmsim/srcsim"
cp guest/upload.asm guest/ysend.asm build/
(cd build && "$z80pack/z80asm/z80asm" -fb -x upload.asm &&
    "$z80pack/z80asm/z80asm" -fb -x ysend.asm)
cpmrm -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk 0:UPLOAD.COM
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/upload.bin 0:UPLOAD.COM
cpmcp -T raw -f ibm-3740 rcpm-cpm3/disks/drivea.dsk build/ysend.bin 0:YSEND.COM
```

If boot startup reports a disk write error, check that the A: template has
room for Z3PLUS startup files. Section 5 removes the unused stock
`HELP.COM` from that image.

Restart the loopback listener with `--inbox` and use a raw-TCP client with
YMODEM batch support.

- **Upload:** Enter `UPLOAD /Y`, then send one or more files in YMODEM
  batch mode when the guest says it is ready. Use CP/M 8.3 names with
  letters, digits, and underscores. The sender must provide each file's
  length. The receiver accepts both 128-byte and 1 KiB blocks, and stores
  exactly the declared bytes, up to 4 MiB per file. Each file is committed
  before its EOF acknowledgement. If a batch is interrupted, files already
  committed remain in the inbox and the unfinished file is discarded.
- **Download:** Enter `YSEND P:PAYLOAD.BIN` or, after mounting a volume,
  `YSEND J:PAYLOAD.BIN`. Start YMODEM receive when the guest says it is
  ready. `YSEND` sends one file per command. It reads through CP/M 3 and
  uses the recorded byte count for the last record. A file stored as full
  records is sent at its full record length.
- **Verify:** Download a binary from each archive and compare it with its
  reference using `cmp`. Upload a two-file batch with lengths that aren't
  multiples of 128. Compare both inbox files, then repeat and disconnect
  midway through the second file. Check that only the completed file was
  added. Both directions have been tested with lrzsz 0.13.1.

## 9. Install the persistent console and background listener

With the prepared prototype, `./launch_rcpm.zsh` starts the caller listener
in a detached tmux session named `rcpm-listener`, then opens or reconnects to
`rcpm-console`. A process already listening on the configured address and port
is treated as the existing listener, including one started manually. The
launcher checks the port by binding briefly, avoiding a connection that would
boot a disposable caller. Listener output goes to `listener.log` in the caller
instance. Run the launcher again to return to the console. Detach with Ctrl-B
followed by D. Both services keep running after detachment.

Concurrent local-console and caller operation requires isolated auxiliary
I/O. cpmsim 1.39 normally uses fixed paths under `/tmp/.z80pack` for its
AUX FIFOs, so separate emulator processes share those devices regardless of
the terminal manager. tmux provides detachment and reattachment.

Our console executable uses auxiliary files in its own working directory.
The caller executable retains its existing AUX configuration. This console
build is required for the dual-instance configuration provided by this
launcher. A deployment running only one emulator does not require this
additional build. Build it from the pinned z80pack checkout after applying
the patches in steps 4, 6, 7, and 8. Install a C compiler, make, zsh, and tmux first.
On macOS, the compiler and make are supplied by Xcode Command Line Tools,
and tmux can be installed with `brew install tmux`.
The builder copies sources into a temporary directory, disables `PIPES`, and
updates the two obsolete `STOPPED` references in the file-backed AUX branch
to `ST_STOPPED` for cpmsim 1.39. In this console executable, catalog volumes
open read/write. It also assembles `mount-sysop.com` and `bye-sysop.com`
beside the executable. Setup in step 12 installs these on the local boot disk.
The caller executable and caller MOUNT retain read-only archive access.

```sh
mkdir -p build/runtime/srctools
cp "$z80pack/cpmsim/cpmsim" build/runtime/cpmsim
cp "$z80pack/cpmsim/srctools/cpmrecv" build/runtime/srctools/cpmrecv
python3 build_console_runtime.py "$z80pack" build/runtime/cpmsim-console

# Preserve the prepared installation as the persistent local console.
export RCPM_INSTANCE="$PWD/rcpm-cpm3"
export RCPM_CALLER_INSTANCE="$PWD/rcpm-cpm3-caller"
export RCPM_CPMSIM="$PWD/build/runtime/cpmsim-console"
export RCPM_CALLER_CPMSIM="$PWD/build/runtime/cpmsim"

# Create the caller template once, copying writable disks and linking archives.
python3 - <<'PYSETUP'
import os
from pathlib import Path
from serve_rcpm import prepare_session

console = Path(os.environ["RCPM_INSTANCE"])
caller = Path(os.environ["RCPM_CALLER_INSTANCE"])
if not caller.exists():
    caller.mkdir()
    prepare_session(console, caller)
PYSETUP

./launch_rcpm.zsh --check
./launch_rcpm.zsh
```

Default paths are relative to this repository. The local console uses
`../rcpm-cpm3` and `../rcpm-cpm3-trial/runtime/cpmsim-console`. The caller
listener uses `../rcpm-cpm3-trial`, its `runtime/cpmsim`, and its `inbox`.
Export `RCPM_INSTANCE`, `RCPM_CPMSIM`, `RCPM_CALLER_INSTANCE`,
`RCPM_CALLER_CPMSIM`, `RCPM_BIND_ADDRESS`, or `RCPM_PORT` to override these settings. The default
port is 4000 and the default bind address is `0.0.0.0`. `--check` validates prerequisites without starting either service.
The two installations have separate writable boot and work disks. Before
step 12, shared archives remain read-only. Step 12 gives the sysop independent
writable masters and publishes immutable caller snapshots. Wheel policies
and caller execution restrictions remain unfinished.

Repeat the four `export` commands in a new shell, or put them in a personal
wrapper that runs `launch_rcpm.zsh`. The local development defaults described above
refer to the original macOS trial layout. For another installation use the
explicit paths above.

## 10. Populate a private permanent archive

The project creates an empty 512 MiB P: image. Software collections and the
operator's populated disk image are excluded from Git. The default named
directory is `ARCHIVE:` at P0:. Operators choose their own contents and layout.

The first private collection layout for this installation is as follows.

| DU | Named directory | Contents |
| --- | --- | --- |
| P0: | SIGM: | SIGMV001.LBR through SIGMV310.LBR |
| P1: | CPMUG: | CPMUG001.LBR through CPMUG093.LBR |

`build_archive.py` accepts existing SIG/M volume LBRs and expanded CPMUG
volume directories supplied by the operator. It preserves SIG/M LBR bytes
and creates one LUDEF5 LBR per CPMUG volume, preserving member bytes and
recording padding and CRCs. Existing ARK members stay inside their volume
LBRs. The local ISO has CPMUG volumes 043, 044, and 046 in this form.
The library format follows [LUDEF5](https://www.seasip.info/Cpm/ludef5.html).

For example, extract operator-supplied collection ISOs and build a new image.
Run these commands from the repository. Keep staging in the ignored build tree.

```sh
mkdir -p build/archive-source
bsdtar -xf /path/to/sigm.iso -C build/archive-source 'LBR/*'
bsdtar -xf /path/to/cpmug.iso -C build/archive-source 'CPMUG*'
python3 build_archive.py \
  --sigm build/archive-source/LBR \
  --cpmug build/archive-source \
  build/drivep-populated.dsk
```

The builder requires consecutive volume numbers starting at 001 and reports
the number found. Compare that count with the source collection's catalog
before claiming completeness. It verifies every installed LBR by reading it
back from the image and emits a SHA-256 manifest alongside the new image.
It requires an unused output filename and builds a separate disk image.

To assign the names when initially preparing Z3PLUS, append
`--archive-directory SIGM --archive-directory CPMUG` to the step 2 command.
Each repeated option names the next P: user area, starting at P0:. The generic
installation retains `ARCHIVE:` unless the operator supplies these options.
The 128-byte DEFAULT.NDR member fits seven total names, including SYSTEM,
WORK, and VOLUME.

Publish a verified image by replacing the host file backing P: between
sessions. Existing emulator processes retain their already-open image. A
fresh connection or console restart opens the replacement. Apply matching
named-directory updates to both the local and caller boot images between
boots. Keep the previous disk and boot images for rollback. Before sysop publication is enabled, caller P: links to the local P: image
and follows its replacement on the next connection. After step 12, update
the local master and publish it to make changes available to new callers.

Validation of the private archive covered all 403 LBR read-backs, independent
member and CRC checks on all 93 generated CPMUG LBRs, CP/M named-directory
selection, and an exact 324352-byte YMODEM download of CPMUG001.LBR from P1:.
The I: host-read discrepancy was traced to the libdsk-backed cpmtools build.
The POSIX cpmtools build in step 1 extracted the entire guest-created
324352-byte I: file correctly. The existing disk definitions are retained.

## 11. Local and remote network connections

The listener defaults to `0.0.0.0:4000`, accepting connections on all local
IPv4 interfaces. Local SyncTERM clients can continue using `127.0.0.1:4000`.
Other machines use the host's LAN address. Internet callers use the router's
public address and an external TCP port forwarded to the host's LAN address
and listening port. Router forwarding and firewall configuration are managed
by the operator.

For a specific interface, pass `--bind-address IPv4_ADDRESS` to `serve_rcpm.py`
or export `RCPM_BIND_ADDRESS` before running `launch_rcpm.zsh`. For example,
`RCPM_BIND_ADDRESS=127.0.0.1 ./launch_rcpm.zsh` selects loopback access.
The default `0.0.0.0` accepts both local and remote connections. Clients
connect to a concrete host address.

Restart an existing listener to apply an address or port change. The launcher
reuses an occupied endpoint and cannot change an existing process's socket.
The server still handles one caller at a time. Caller isolation and access
controls remain unfinished.

## 12. Enable sysop archive writes and publication

Complete the runtime build and two-instance preparation in step 9 first.
Then exit the local CP/M console with `A0:` followed by `BYE`. Disconnect
callers and stop an older listener once so its next start loads the session
publication changes. Detaching from tmux leaves the console running and
keeps its archive lease active.

Run the setup command from the repository, using the same RCPM environment
variables as the launcher.

```sh
./launch_rcpm.zsh --setup-sysop
./launch_rcpm.zsh
```

Setup installs the sysop MOUNT.COM and BYE.COM on the local A: image,
creates the first read-only publication, redirects the caller J:/P: slots
and catalog to it, and creates independent writable local J:/P: masters.
If the local catalog is absent, it copies the existing caller catalog into
local `volumes/`. Existing local catalogs supply the masters. Setup keeps
the original caller catalog as `volumes-before-publication` when present.
It checks for an older process holding the boot disk on macOS through lsof.
Repeating setup with the same installation preserves the master's contents.

The local console can now use normal CP/M commands to write to P: and J:.
Its MOUNT opens catalog masters read/write. The sysop MOUNT flushes BDOS
buffers before changing media, resets J:, and leaves it writable. The sysop
BYE flushes pending writes with CP/M 3 BDOS function 48 before halting.
On a reported flush failure it returns to CP/M. Function 48 is documented in
Digital Research's [CP/M 3 Programmer's Guide](https://bitsavers.org/pdf/digitalResearch/cpm_plus/CPM_Plus_Programmers_Guide_Apr83.pdf).

After editing, return to A0: and exit with BYE, then publish from the host.

```sh
./launch_rcpm.zsh --publish
./launch_rcpm.zsh
```

The local launcher holds an exclusive console lease across exec into cpmsim.
Publication takes the same lease and refuses to copy while the managed
console is running. Run local instances through this launcher. Exit unmanaged
emulators and host image editors before changing the masters or publishing.
Forced termination does not provide the flush guarantee of the sysop BYE.

Each publication contains both default archive images and every valid catalog
image in a unique generation under the caller installation's `published/`.
An atomic `published/current` symlink update makes the completed generation
available. Each caller resolves that pointer once when its session is created,
pinning both archive images and the catalog. Existing callers retain their
previous generation, including during later MOUNT commands. New callers
receive the latest generation. The listener can remain running during
subsequent sysop edits and publication.

Publication validates image sizes and prepares the entire generation before
switching the current pointer. A failed preparation leaves the previous
publication selected and can be retried. Old generations remain available
for rollback and existing sessions. Their storage use depends on filesystem
copy-on-write support. macOS uses `cp -c` clones when supported, with ordinary
copying as a fallback. Filesystems without cloning keep full image copies.

To inspect the selected generation, run the status command.

```sh
./launch_rcpm.zsh --archive-status
```

A personal `rcpm` wrapper must forward arguments with `"$@"` to expose these
options. Calling the repository script directly always supports them.

Validation included actual CP/M writes to P:, default J:, and a mounted J:
master, refusal to publish while the console lease was held, an exact archive
read after publication, and rejection of a caller P: write. The host regression
checks also cover session/catalog pinning, idempotent setup, and retry after
failed publication.

```sh
python3 -m unittest -v test_archive_publication.py
```

This provides archive write access and publication. Z3PLUS wheel policy,
caller command restrictions, authentication, and broader host isolation remain
separate work items.

## Optional transport diagnostic

```sh
python3 check_rcpm_transport.py --cpmsim-dir /path/to/z80pack/cpmsim
```

The probe boots a disposable stock CP/M 2.2 disk and checks raw TCP byte
fidelity and reconnect after a client closes the connection. It connects
through loopback. Stock cpmsim listens on all IPv4 interfaces on the
temporary port for the duration of this echo-only test.

## Roadmap

1. The loopback prototype starts a fresh guest per caller. Decide how to
   handle login, guest logoff, and persistent work before public access.
2. Add a caller logoff command and short HELP/MAP.
3. Add ZMODEM and Kermit uploads and downloads.
4. Verify command execution restrictions, work-area access, and session
   cleanup before opening access.
5. Complete public deployment documentation alongside caller isolation and
   access controls. Configurable IPv4 listening addresses and ports are supported.

Terminal-based games and CP/NET archive mappings are future expansions.
The repository contains setup code. Obtain CP/M 3 and Z3PLUS media from
their respective distributions.
