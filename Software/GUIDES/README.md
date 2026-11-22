# GUIDES documentation disk

An optional 4 MB documentation-only image, supplied by the maintainer and
preserved byte-for-byte. User area 0 contains README.TXT, COMMANDS.TXT,
DIR.TXT, LDIR.TXT and the -GUIDES directory-name marker.

[Download GUIDES-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-images-2026-11-22/GUIDES-collection.zip)

Stop RCP/M, extract the ZIP, copy volumes/GUIDES.dsk into your installation's
disks/library/ folder, then restart. Enter:

```text
MOUNT GUIDES
DIR J:
LT J:README.TXT
```

This is also supplied with the base RCP/M system. The independent download
makes it available alongside the other Software collections. It uses raw
z80pack-hd geometry, exactly 4,177,920 bytes, compatible with RCP/M 1.0's J:
slot. Keep any original notices in the documents. No programs are installed
or approved by adding this disk.

Validation: image size, stable source/copy SHA-256, directory listing and
complete readback of all five files. See [the image inventory](../Images/manifest.json).
