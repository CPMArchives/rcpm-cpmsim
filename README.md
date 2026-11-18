# RCP/M on cpmsim

A Remote CP/M system in development for the CPMArchives software collection.
Callers will land directly at the CP/M prompt. The local prototype uses
banked CP/M 3 on Udo Munk’s z80pack cpmsim and Z3PLUS for named directories.

| Drive | Role | Capacity |
| --- | --- | --- |
| I: | Writable work disk. One caller-writable user area is planned, with uploads and notes submitted through dedicated utilities. | Nominal 4 MB |
| J: | Read-only rotating archive. An in-session `MOUNT` command will select a volume from a host-configured catalog. | Nominal 4 MB |
| P: | Permanent read-only software archive. | 512 MiB |

## Run the local prototype

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

### Add Z3PLUS

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

## Transport probe

```sh
python3 check_rcpm_transport.py --cpmsim-dir /path/to/z80pack/cpmsim
```

The probe boots a disposable stock CP/M 2.2 disk and checks raw TCP byte
fidelity and reconnect after a client closes the connection. It connects
through loopback. Stock cpmsim listens on all IPv4 interfaces on the
temporary port for the duration of this echo-only test.

## Roadmap

1. Establish remote sessions and choose whether to keep one guest running
   or start a fresh guest for each caller.
2. Implement catalog-based, read-only live mounting on J:.
3. Add binary downloads, upload staging, and NOTE submissions.
4. Verify command execution restrictions, work-area access, and session
   cleanup before opening access.

Terminal-based games and CP/NET archive mappings are future expansions.
The repository contains setup code. Obtain CP/M 3 and Z3PLUS media from
their respective distributions.
