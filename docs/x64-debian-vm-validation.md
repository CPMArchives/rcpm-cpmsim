# Published x64 kit — Debian VM qualification

**PASS — 26 November 2026.** The published `v1.2.2-rc1` x64 service kit
passed 12 integration groups and all 10 Linux safety tests in a disposable
Debian VM. No kit changes or test timing adjustments were needed.

## Artifact and environment

Downloaded from the [published prerelease](https://github.com/CPMArchives/rcpm-cpmsim/releases/tag/v1.2.2-rc1):
`rcpm-v1.2.2-rc1-linux-x64-service.tar.gz`, 45,130,225 bytes.
Its SHA256 matched both published `SHA256SUMS` and GitHub's asset digest:

```text
1bdae49d62568f494bde3af6fd4d30e52d2e33db6229594fc66c0391f769e9fb
```

Matching tagged source: `36bfc1322a27974d095b09ee582182359a4ec4d6`.
The installer and qualification harness came directly from that downloaded kit.
Installed helpers, configuration, systemd units and runtime files were checked
against the archive after recovery testing and matched byte for byte.

The VM ran Debian 12.15, kernel `6.1.0-54-cloud-amd64`, systemd 252 as PID 1,
Python 3.11.2 and glibc 2.36, with no compiler installed. Lima 2.3.0 and
QEMU 11.1.3 provided two CPUs, 2 GiB RAM and a 16 GiB disk. Because the host
Mac is ARM64, QEMU used TCG CPU emulation. This tests the actual x64 binaries
and Debian kernel, but does not qualify native x64 hardware performance.

The official Debian cloud image's pinned SHA512 was verified. There were no
shared host folders. RCP/M's three listeners were checked as guest loopback
only, with application-port forwarding disabled; callers connected inside
the VM. Only VM management used host-loopback SSH. No VPS was used.

## Installation

Read-only preflight created neither an account nor instance. Fresh installation
created an unprivileged `rcpm` account with a nologin shell and root-owned
helpers/configuration. All three shipped units passed `systemd-analyze verify`.
The service and backup timer were initially stopped and disabled, with no
generated SYSOP credentials. Repeated installation refused to overwrite the
instance and left the data image unchanged.

## Systemd startup and shutdown

The notify service reached readiness and accepted a caller through tcpser/IP232;
HELP returned 906 bytes. Private console attachment, detachment and reattachment
worked. Idle stop succeeded and left no modem or emulator process.

With a caller connected, shutdown rejected new callers while the existing
caller continued to use HELP. It stopped cleanly after disconnection.
A temporary five-second stop timeout produced the expected unit timeout while
preserving the caller, guest, modem and private operator control. The caller
then drained and the service restarted successfully. The temporary override
was removed; the shipped 300-second timeout remained in effect.

## Reboot and recovery

The enabled service automatically returned to caller-ready operation after:

- A clean systemd reboot.
- Full systemd power-off, confirmed VM Stopped, then cold start.
- SIGKILL of the confirmed-idle VM's QEMU process, then restart.

Changed kernel boot IDs confirmed each boot. Credentials and caller HELP
survived. For the abrupt reset, the previous boot journal showed service start
without a clean service stop. Every existing snapshot still verified afterward.

SIGKILL tests separately targeted tcpser, cpmsim and the supervisor. Each time,
systemd automatically restarted the service, old child processes were absent,
credentials were unchanged and caller HELP worked.

## Backup and restore

The shipped backup service stopped RCP/M, produced a verified snapshot and
restarted without false unit failures. Restoring into a new directory preserved
the data image hash and credentials; the restored instance booted under the
real unit and accepted a caller.

A deliberately conflicting backup destination reported an error, left RCP/M
stopped beyond its restart delay and preserved the last good snapshot. The
shipped persistent timer caught up a missed run after its test timestamp was
moved into the past, produced a valid snapshot and restarted RCP/M cleanly.

## Evidence and limits

The [machine-readable report](https://github.com/CPMArchives/rcpm-cpmsim/releases/download/v1.2.2-rc1/X64-VM-VALIDATION.json)
contains the individual results, environment, artifact identity and image pin.
Sanitized journals, installer output and safety-test output are retained locally
under `build/x64-vm-qualification/evidence/final/`, with an evidence hash manifest,
archive and VM profile alongside them. Credentials, disk images, private keys
and the internal credential-hash baseline were excluded from exported evidence.
The disposable VM, its disk and isolated SSH keys were removed after export.

This supports the local unattended Debian x64 service lifecycle. It does not
establish native x64 performance, long-duration stability, high-load behavior,
Internet-facing security or crash consistency during active guest writes.
The full 300-second shutdown timeout was not waited out. Outbound dialing was
not rerun in this VM; these lifecycle tests exercised inbound tcpser/IP232.
No new BYE AUTH/security audit, VPS deployment, CPMNet implementation or CP/M
mail utility testing occurred. Testing did not modify the published release, kits or tag. This report
supplements the original ARM64 qualification evidence; publication adds separate
x64 reports and updates the release notes without changing existing assets or
the release tag.
