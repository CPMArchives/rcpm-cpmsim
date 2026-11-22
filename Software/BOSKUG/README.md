# BOSKUG archive disk

An optional 4 MB archive image supplied by the maintainer, containing 14
BOSKG*.ARK archives in user area 0. The image is preserved byte-for-byte;
archive members have not been unpacked, modified or individually qualified.

[Download BOSKUG-collection.zip](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/software-images-2026-11-22/BOSKUG-collection.zip)

Stop RCP/M, extract the ZIP, copy volumes/BOSKUG.dsk into your installation's
volumes/ folder, then restart. Enter:

```text
MOUNT BOSKUG
DIR J:
```

Use a raw TCP client with file-transfer support to download an archive, e.g.
`YSEND J:BOSKG101.ARK`. The disk holds archives for browsing/download; this is
not a claim that their member programs are ready for online execution.

The image uses raw z80pack-hd geometry, exactly 4,177,920 bytes, compatible
with RCP/M 1.0's J: slot. It includes BOSKG101, 102, 103, 104, 131, 161, 163,
201, 302, 303, 304, 504, 505 and 801. Preserve the notices inside the archives;
this collection does not grant a new blanket license to their contents.

Validation: image size, stable source/copy SHA-256, directory listing and
complete readback of all 14 archive files. No new gameplay or execution
qualification is claimed. See [the image inventory](../Images/manifest.json).
