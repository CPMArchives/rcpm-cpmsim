# Walnut Creek CP/M archive

[Download WALNUT-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-walnut-2026-11-23/WALNUT-collection.zip) · [SHA-256 checksums](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-walnut-2026-11-23/SHA256SUMS) · [Validation](VALIDATION.json)

The complete Internet Archive Walnut Creek CD-ROM tar collection, repackaged as an optional **512 MiB P: archive image**. All 24,402 original file payloads are preserved, including original archives and their notices. This is archival browsing/download material; its programs have not all been qualified for execution on RCP/M.

## Install and mount

Use **RCP/M 1.1.1** with its swappable P: support and automatic named-directory refresh. Stop RCP/M cleanly, extract the ZIP, and copy `volumes/WALNUT.dsk` to `disks/library/archives/WALNUT.dsk`. Keep the default P: image and other collections. Restart RCP/M and enter:

```text
MOUNT WALNUT
BBS:
DIR
```

`MOUNT P: WALNUT` also works. A successful mount automatically runs NDSCAN in quiet mode; no separate scan is needed. Allow approximately 47–60 seconds at the normal emulated speed for disk relogging and scanning. This download does not change the RCP/M release number or require a Z3PLUS or disk-format change.

This image is raw **z80pack-hdb**, exactly **536,870,912 bytes**, for P:. It is larger than the J: collections and must go in the `archives/` subfolder. Its SHA-256 is `b7921b101e814313c7dc944c9c95f0d54e5e964702f7ccb97e4409650887c222`.

## Layout

| User area | Name |
| --- | --- |
| P0 | WALNUT |
| P1 | BEEHIVE |
| P2 | CPM |
| P3 | DEMON |
| P4 | EMULATR |
| P5 | ENTRPRS |
| P6 | FOG |
| P7 | JSAGE |
| P8 | LAMBDA |
| P9 | SIMTEL |
| P10 | STARLET |
| P11 | UTILS |
| P12 | ZSYS |
| P13 | BBS |
| P14 | SIGM |

P15 is empty. EMULATOR and ENTERPRS use the approved names EMULATR and ENTRPRS; the original `_BBS` directory uses BBS because Z3PLUS treats underscores as delimiters. The source manifest retains original source paths.

Top-level collections with subdirectories have their own user areas, with original loose files retained. Flat top-level collections are LBRs in P0. Subdirectories become nested LBRs, split into numbered parts where necessary; each generated library is at most 8,000,000 bytes and 512 members. There are 664 generated libraries in total.

SIG/M is flattened into P14: 302 volume libraries, SIGMV000.LBR through SIGMV310.LBR where present. Source volumes 184–192 are absent. The four grouping indexes are loose IDX-000.TXT, IDX-100.TXT, IDX-200.TXT and IDX-300.TXT; deeper volume subdirectories remain nested. No generated catalog or index was added inside the image.

`LDIR` lists library members and `LT` reads supported text. These utilities do not traverse nested paths directly. Download with the existing YSEND workflow and extract libraries one level at a time locally. Original unusual or malformed archives remain unchanged.

## Verification and provenance

A fresh independent readback verified every original payload SHA-256, generated LBR directory/member CRC, library bounds and padding, and disk allocation. The image contains 631 files including 15 markers, uses 4,179 of 8,192 directory entries, and has 25,886,720 bytes free. CP/M loose-file extraction can add ordinary 128-byte record padding; manifests record original payload lengths.

Native RCP/M checks covered mounting, automatic named-directory refresh, bare BBS: and library access, LDIR/LT boundary cases, YMODEM download, and nested extraction with unmodified LU 3.10. These checks establish archive compatibility and preservation, not general execution compatibility of the CD's programs.

Source: [Walnut_CDROM.tar](https://archive.org/download/Humongous_CPM_Archive_Collection/core_archives/Walnut_CDROM.tar), from the [Humongous CP/M Archive Collection](https://archive.org/details/Humongous_CPM_Archive_Collection). Source tar SHA-256: `0fd7114bb7396abef0dbba5cac22b7eccb0d1b198bf8e33fa0d6978392a5ab50`.

The ZIP includes the image, this guide, per-file source/destination manifest, library layout/checksums, disk layout, user-area map, and validation reports under `records/`. Preserve the original notices within the files and archives; this collection grants no new blanket license to third-party contents. Source payloads and the source tar remain unchanged.
