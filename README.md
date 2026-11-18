# RCP/M on cpmsim

A Remote CP/M system in development for the CPMArchives software collection.
Callers will land directly at the CP/M prompt. The local prototype uses
banked CP/M 3 on Udo Munk’s z80pack cpmsim and Z3PLUS for named directories.

| Drive | Role | Capacity |
| --- | --- | --- |
| I: | Writable work disk. One caller-writable user area is planned, with uploads and notes submitted through dedicated utilities. | Nominal 4 MB |
| J: | Read-only rotating archive. An in-session `MOUNT` command will select a volume from a host-configured catalog. | Nominal 4 MB |
| P: | Permanent read-only software archive. | 512 MiB |

## 1. Bring up CP/M 3

Use Python 3, cpmtools with the `ibm-3740`, `z80pack-hd`, and `z80pack-hdb`
disk definitions, and a built [z80pack](https://github.com/udo-munk/z80pack)
cpmsim with its bundled CP/M 3 disk images. The prototype was verified on
macOS with cpmsim 1.39.

```sh
python3 launch_rcpm_cpm3.py --cpmsim /path/to/z80pack/cpmsim/cpmsim
```

The launcher copies the stock boot media, creates the three data drives, and
opens the local console. It starts CP/M 3 with network listeners disabled.
`TYPE I:VOLUME.TXT`, `TYPE J:VOLUME.TXT`, and `TYPE P:VOLUME.TXT` identify
the three volumes. The archive image files are created without host write
permission.

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
python3 serve_rcpm.py --cpmsim /path/to/z80pack/cpmsim/cpmsim
```

It accepts raw TCP on IPv4 loopback only, port 4000 by default. In another
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
2. Enter `ARCHIVE:` and wait for `P0:ARCHIVE>`. Enter `TYPE VOLUME.TXT`.
   The guest should print `PERMANENT ARCHIVE P`.
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
   `TYPE P:VOLUME.TXT` should show the permanent archive marker.
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
2. Add upload staging and NOTE submissions.
3. Verify command execution restrictions, work-area access, and session
   cleanup before opening access.

Terminal-based games and CP/NET archive mappings are future expansions.
The repository contains setup code. Obtain CP/M 3 and Z3PLUS media from
their respective distributions.
