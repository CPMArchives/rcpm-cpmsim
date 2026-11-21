# RCP/M post-1.0 roadmap

## Configurable CPU speed

Add an operator-controlled startup setting for emulated CPU speed, retaining
**4 MHz as the default**. Document the difference between CPU speed and client
display/connection pacing. Higher clocks are an explicit operator choice and
may change game logic, busy-loop delays and terminal timing.

Use the existing cpmsim clock option; avoid a new guest timing framework.
Validate configuration input and qualify startup, BYE modem initialization,
autobaud, inactivity timeouts and disconnect recovery in both connection modes
at supported settings. Do not assume that the monotonic idle timer makes all
other legacy timing independent of CPU speed. Unlimited mode needs separate
qualification before being offered as a supported setting.

Investigating the remaining console overhead is a separate, optional engineering
task. It is not a reason to increase the default CPU clock. Current scrolling
is acceptable and contributes to the intended period experience.

## Online games: separate policy and qualification work

The GAMES image contains unpacked programs and supporting files. Caller
execution uses the [sysop-controlled program approval mechanism](online-games.md).
Additional game qualification is future work; the default CPU speed remains
4 MHz. Games requiring writes to the protected catalog are for download and
local play. Universal compatibility and persistent player saves/high scores
are outside the agreed scope; fixed launchers may use disposable WORK data.

## Additional swappable volumes from curated CP/M-era BBS collections

Use preserved catalogs and software from curated CP/M-era BBS collections to
guide additional J: images. The originating BBS need not have run RCP/M or CP/M;
the relevant material is its curated CP/M software collection. Tesseract RCPM+
is one starting example, not a restriction on eligible systems or collections.
Preserve useful original subject groupings,
descriptions and version information rather than assembling arbitrary samples.
Catalog-based selections may become themed volumes or documented reconstructions
of an original system's collection; distinguish those two forms explicitly.

- Locate the actual software behind each listing. A preserved catalog is evidence
  of what was listed, not proof that the corresponding files have been recovered.
- Retain original documentation/notices and record catalog provenance, retrieved
  file versions and checksums in the volume manifest. Identify later updates and
  substitutions instead of silently treating them as the historic snapshot.
- For ready-to-use volumes, unpack game/application files and their dependencies;
  label source-only, machine-specific and unqualified material accurately.
- Keep availability for browsing/download separate from caller execution approval.
  Sysop/private development tools remain subject to the existing access policy.

Starting references checked on 20 November 2026:

- [HUMONGOUS CP/M archives](https://cpmarchives.classiccmp.org//): the archive index
  lists a reconstructed Tesseract collection and a preserved site download.
- [Tesseract's former catalog URL](https://www.triton.vg/TesseractRCPM%2BCatalog.html):
  the current page is a historical summary linking to archived pages, not the
  original live file catalog. Follow preserved copies for the actual listings.

The first additional collections and their exact image contents remain to be
selected; this records the curation approach without adding unverified volumes.

## Caller access to temporary files

Deferred until after AUTH integration. Callers currently have no general copy
command or direct upload into I0:WORK; game launchers seed their fixed data and
caller applications can create workspace files. Consider a reviewed copy tool
and/or a separate temporary-upload service. Retain private review-inbox uploads
unless explicitly changing that policy. Caller-writable DUs remain non-executable.
