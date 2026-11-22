# Installed directory layout

The top level contains README.txt, the platform launcher, RCPM.CONF and private
SYSOP.DOC. SYSOP.DOC records locally generated credentials; it is distinct from
the administration guide in docs/SYSOP-GUIDE.DOC.

| Location | Contents |
| --- | --- |
| disks/ | Active A:, I:, startup J: and startup P: images |
| disks/library/ | Swappable 4 MB J: collections |
| disks/library/archives/ | Swappable 512 MiB P: collections |
| disks/library/offline/ | Development media outside both mount catalogs |
| docs/ | Operator documentation, release notes and NOTICES/ |
| metadata/ | Package manifest, collection inventory, provenance and checksums |
| uploads/inbox/ | Completed uploads and saved caller messages |
| uploads/staging/ | Transfers in progress |
| runtime/ | Native launcher, emulator, disk tools and supporting files |
| source/ | Source code and build instructions |
| state/ | Persistent initialization state; preserve during upgrades |

Mount listings are nonrecursive and retain exact geometry validation. J: and
P: have separate filename namespaces. Offline images never appear in either
catalog. Upload directories remain on the same filesystem for atomic commit.

The independent Software download ZIPs retain their published internal
volumes/ paths. Copy their images into disks/library/ in this layout.

## Migrating an existing Mac installation

Stop RCP/M through SYSUTLS:BYEBYE first. Rebuild cpmsim and the launcher from
this revision, then run:

```sh
python3 migrate_layout.py /path/to/RCPM --runtime /path/to/rebuilt/runtime
```

The script refuses a running installation or conflicting destinations. It
verifies that disk images, SYSOP.DOC, RCPM.CONF and initialization state remain
byte-identical, updates manifest paths and hashes, and saves the prior runtime,
manifest and changed document text under state/layout-before-reorg/. Its receipt
records moves and checksums. A repeated migration is refused. Keep a separate
stopped-system backup as well. Source snapshots remain historical build records;
the runtime replacement is identified in the local installation manifest.

New Mac, Windows and Linux packages use the same directory layout. The migration
script targets macOS and uses its native instance lock; it is not a Windows
migration command.
