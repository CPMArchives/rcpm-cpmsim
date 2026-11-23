# Software

Optional software disks for RCP/M. Download the collections you want and add
these alongside your existing volumes. They are distributed separately from
the [main RCP/M download](https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.0).

## Downloads

| Disk | Contents | Download | Test report |
| --- | --- | --- | --- |
| **BOSKUG** | 14 preserved BOSKG ARK archives; user 0 | [BOSKUG-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-labels-2026-11-23/BOSKUG-collection.zip) | [Inventory and scope](BOSKUG/README.md) |
| **GAMES expanded** | 76 tested titles; shared areas, J0 launchers | [GAMES-expanded.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-games-2026-11-22/GAMES-expanded.zip) | [Results and exclusions](GAMES/README.md) |
| **SADAMS** | 12 Scott Adams adventures and sampler; original CP/M interpreter, user 0 | [SADAMS-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-labels-2026-11-23/SADAMS-collection.zip) | [Results and controls](SCOTT/README.md) |
| **INFOCOM** | 27 Infocom games and five InvisiClues hint books; user 0 | [INFOCOM-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-labels-2026-11-23/INFOCOM-collection.zip) | [Results and exclusions](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-2026-11-21/INFOCOM-REPORT.txt) |
| **INTFICT** | 11 selected IFComp games: nine v5 and two v8; user 0 | [INTFICT-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-labels-2026-11-23/INTFICT-collection.zip) | [Results and exclusions](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-2026-11-21/MODERNIF-REPORT.txt) |
| **GUIDES** | Documentation-only disk; README, commands, DIR and LDIR guides | [GUIDES-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-images-2026-11-22/GUIDES-collection.zip) | [Contents and checks](GUIDES/README.md) |
| **WALNUT** | Complete Walnut Creek CP/M archive; 24,402 original files, 512 MiB P: image | [WALNUT-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-walnut-2026-11-23/WALNUT-collection.zip) | [Installation, layout and validation](WALNUT/README.md) |

[Image inventory and checksums](Images/README.md). Each image has its own download; choose only the collections you want.

The [expanded GAMES guide](GAMES/README.md) explains its replacement-image installation and limits.

Each collection ZIP contains one `volumes/*.dsk` image, its file manifest, usage notes,
validation results and accompanying component notices. INTFICT also
includes Gosling's original distribution with its host-side map and hints.

[Software release](https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/software-2026-11-21) ·
[SHA-256 checksums](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-2026-11-21/SHA256SUMS) ·
[Machine-readable catalog](catalog.json)

## Install a disk

The J: collections below require RCP/M 1.0 or later. **WALNUT uses the 512 MiB P: format and requires RCP/M 1.1.1**; follow its [separate installation instructions](WALNUT/README.md).

1. Stop RCP/M cleanly using its normal shutdown procedure.
2. Extract the collection ZIP somewhere convenient.
3. Copy its `.dsk` file into your installation's `disks/library/` folder (or `volumes/` on RCP/M 1.0). Keep the
   other volumes already in that folder.
4. Restart RCP/M. At `A0:SYSTEM>` enter `MOUNT /L` to see the available disks.

For SADAMS:

```text
MOUNT SADAMS
J0:SCOTT
```

Use a plain player name; SCOTT automatically saves in WORK. Its game menu
and save conventions are described in the [SCOTT guide](SCOTT/README.md).

For INFOCOM:

```text
A0:
MOUNT INFOCOM
J0:VEZZA J:ZORK1.DAT
```

For INTFICT:

```text
A0:
MOUNT INTFICT
J0:VEZZA J:PHOTOPIA.Z5
```

Substitute a filename from the disk's `README.TXT` or `INFOCOM.TXT`. These
collections use **user 0**. Vezza takes a drive-qualified story name such as
`J:ZORK1.DAT`; its story argument does not accept `J0:ZORK1.DAT`.

For INFOCOM and INTFICT, at a save/restore filename prompt, use **`I:NAME.SAV`** for temporary WORK.
WORK is cleared when the call ends, so download a save before logging off if
you want to keep it. Persistent per-caller storage has not been added.

The J: images retain the existing format: raw `z80pack-hd`, 4,177,920 bytes.
`VEZZA.COM` carries the existing per-file caller approval marker. J: remains
read-only to callers; these downloads do not require changing DU permissions,
replacing GAMES, or altering the released system disks.

## Collections and compatibility

### INFOCOM

The disk includes the Zork trilogy, Enchanter trilogy, Hitchhiker's Guide,
Planetfall, Stationfall, and other text adventures. Its 32 story files were
checked against their sources. Representative v3, v4 and v5 games were exercised;
this is not a claim that all 32 entries received individual gameplay tests.

The larger-memory AMFV, Beyond Zork and Trinity releases, the timed-input game
Border Zone, and the four graphical v6 titles are excluded. See the report for
the VT52 CP/M 3 alternative and its remaining qualification gaps.

### INTFICT

| Game | IFComp placement | Format |
| --- | --- | --- |
| A Change in the Weather | 1995, 1st in Inform division | v5 |
| The Meteor, the Stone and a Long Glass of Sherbet | 1996, 1st | v5 |
| The Edifice | 1997, 1st | v5 |
| She's Got a Thing for a Spring | 1997, 4th | v8 |
| Photopia | 1998, 1st | v5 |
| Muse: An Autumn Romance | 1998, 2nd | v5 |
| Winter Wonderland | 1999, 1st | v5 |
| Metamorphoses | 2000, 2nd | v5 |
| Ad Verbum | 2000, 4th | v5 |
| All Roads | 2001, 1st | v5 |
| Miss Gosling's Last Case | 2024, 6th | v8 |

Placements come from the [official IFComp results](https://ifcomp.org/history).
The supplied editions are identified in the manifest and may contain later
post-competition updates. All 11 entries passed startup, command input,
save/restore and quit checks at the normal 4 MHz clock. Caller recovery,
WORK cleanup and private-tool restrictions were also checked. These are
opening/session tests, not full playthroughs.

Choose **NO** to FRILLS in Winter Wonderland for the tested plain display mode.
Paused introductions may need SPACE more than once. All Roads' opening can be
advanced with `LOOK` then `WAKE UP` before saving in the main story.

No v7 title qualified. Lost Pig, Vespers and Violet exceed RW's memory limit;
both tested editions of The Wise-Woman's Dog stop on an unsupported instruction.
Custard was rejected by the interpreter at load time. The report records these
results rather than treating a suitable header as proof that a game runs.

### Interpreter and third-party material

Both disks use the unmodified upstream **Vezza RW serial 251222** build on
RCP/M's CP/M 3 system, with ANSI/VT100 output. Its advertised small-memory
limit is approximately 25 KiB of dynamic story memory. It has no timed input,
undo, graphics or sound support. The larger banked ANSI build does not fit the
program memory left by the released Z3PLUS/BYE configuration.

Game copyrights and component-specific notices remain with their authors;
these collections are not collectively relicensed as RCP/M code. Accompanying
notices, source links and the Vezza core license are retained in the downloads.

Sources: [Vezza](https://gitlab.com/sijnstra1/vezza),
[Infocom catalog](https://eblong.com/infocom/),
[the-infocom-files](https://github.com/the-infocom-files), and
[IF Archive](https://ifarchive.org/indexes/if-archive/games/zcode/).

## Future additions

New collections belong in this catalog with their own optional release assets,
installation notes, provenance and test results. Disk binaries stay out of Git
history and are not added to the base-system packaging inputs.

## Collection names

User area 0 carries the matching extensionless -NAME marker in every collection: -BOSKUG, -GAMES, -GUIDES, -INFOCOM, -INTFICT and -SADAMS. MOUNT chains to NDSCAN so the current J0 name follows the mounted collection. SCOTT.COM remains the Scott Adams launcher inside SADAMS.dsk.

Replace the former SCOTT.dsk and MODERNIF.dsk catalog entries with SADAMS.dsk and INTFICT.dsk while RCP/M is stopped. Do not keep both old and renamed copies in the public catalog.
