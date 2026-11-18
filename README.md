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
2. Implement catalog-based, read-only live mounting on J:.
3. Add binary downloads, upload staging, and NOTE submissions.
4. Verify command execution restrictions, work-area access, and session
   cleanup before opening access.

Terminal-based games and CP/NET archive mappings are future expansions.
The repository contains setup code. Obtain CP/M 3 and Z3PLUS media from
their respective distributions.
