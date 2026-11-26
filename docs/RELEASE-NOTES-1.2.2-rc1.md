# RCP/M v1.2.2-rc1 — native Debian service prerelease

**Prerelease for local testing and evaluation. Not a production-ready public-VPS
release.** The stable v1.2.1 release and its existing assets remain unchanged.

## Downloads

- [Linux ARM64 service kit](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/v1.2.2-rc1/rcpm-v1.2.2-rc1-linux-arm64-service.tar.gz) — **Debian 12 ARM64 VM tested**.
- [Linux x64 service kit](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/v1.2.2-rc1/rcpm-v1.2.2-rc1-linux-x64-service.tar.gz) — updated host-service code; **x64 systemd VM/native hardware qualification pending**.
- `SHA256SUMS`, `NATIVE-DEBIAN-INSTALLATION.md`, `DEBIAN-VM-REPORT.md`,
  `VM-VALIDATION.json` and `RELEASE-PROVENANCE.json` accompany the kits.

Each kit is complete: guest media, native tools, patched tcpser and corresponding
source, root-level installer, persistent private console, systemd service and
verified stopped-backup/restore helpers. Requires Python 3.9+ and systemd;
no compiler or separate tcpser installation is needed.

[Read installation instructions online](https://github.com/CPMArchives/rcpm-cpmsim/blob/v1.2.2-rc1/docs/INSTALLATION-NATIVE-SERVICE.md).
Installation leaves services stopped/disabled and application access loopback-only.
These are fresh-install kits; do not overwrite an existing board or its data.

## Changes

- Supervise native RCP/M and a private tcpser/IP232 modem together, retaining an
  attachable operator console and gating new callers during shutdown.
- Stop through acknowledged BYE/CP/M stages before making a verified snapshot;
  restore complete snapshots into new directories.
- Fix false systemd stop failures after completed backups, orphan processes
  after supervisor death, and loss of operator control after stop timeout.
- Fix tcpser failed-dial command-mode recovery and batched DTR event handling.
- Add guarded disposable-VM qualification and loopback-only outbound dial probes.

The CP/M guest media and pre-existing native RCP/M binaries are unchanged from
v1.2.1. This prerelease versions the host-service integration. Existing internal
candidate/base-version labels are retained to preserve the tested archive bytes;
release asset names and provenance map them to this tag.

## Evidence and testing limits

Debian 12.15 **ARM64**, systemd 252 as PID 1, in a disposable local VM:
**12 integration groups and 10 Linux safety tests passed**. Coverage includes
fresh/repeated installation, startup, console reattachment, clean stop and caller
draining, reboot/cold start, idle hard reset, modem/emulator/supervisor failure
recovery, timeout safety, verified backup/restore and persistent timer catch-up.
The timeout fault used a temporary five-second override; the shipped 300-second
setting was restored. The full default-duration timeout was not waited out.

The freshly installed archive and delivered archive differ only through later
qualification-harness/documentation refinements. Installer, production helper,
units and native runtime were verified byte-identical; the report records both
archive digests. The source and kit mapping is in `RELEASE-PROVENANCE.json`.

**Not established by these tests:**

- x64 systemd VM or native x64 hardware operation. Earlier x64 runtime/modem
  testing used CPU emulation; timing variance was recorded.
- Active-write power-loss/database consistency; abrupt VM reset was idle-only.
- Sustained 72-hour operation, target-VPS/public-network behavior or off-host
  backup retention/disaster recovery.
- A full guest-program/BYE AUTH adversarial regression in the VM.

The test VM was removed. **No VPS deployment, CPMNet implementation or scheduled
outbound mail polling is included.** tcpser/outbound capability is preparation
for future CPMNet work, not evidence of an existing mail exchange system.

Original component notices and licensing terms remain applicable. GitHub's
source downloads point to the matching tagged source; the kits also retain
component source and tcpser provenance.
