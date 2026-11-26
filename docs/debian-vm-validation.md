# Native Debian VM qualification — 26 November 2026

**PASS for the local Debian 12 ARM64 service profile after fixes.** This is
engineering qualification, not authorization or certification for public VPS
operation. No VPS deployment or CPMNet implementation occurred.

The disposable VM used Apple Virtualization.framework through Lima 2.3.0,
2 CPUs, 2 GiB RAM and a 12 GiB disk. Debian 12.15 ran systemd 252 as PID 1
and kernel 6.1.0-54-cloud-arm64. No compiler was installed. Host folders were
not shared; application-port forwarding was disabled and RCP/M listeners stayed
on guest loopback. The VM was deleted after sanitized evidence was exported.

## Installer

Preflight created neither an account nor installation state. Fresh installation
created the unprivileged `rcpm` account and root-owned helpers/configuration,
passed `systemd-analyze verify`, and left services stopped and disabled.
A repeated installation was refused without changing the data image.

## Systemd startup and shutdown

The real notify-type service became ready, accepted a caller through tcpser,
served HELP and supported private console attachment/reattachment. Idle stop
completed successfully with no remaining emulator or modem process.

With an active caller, stop refused new connections while allowing the existing
caller to continue. It finished cleanly after that caller disconnected.
A temporary five-second systemd stop timeout verified that the guest/modem
were not force-killed, the caller continued, and private operator status/control
remained accessible. The test override was removed afterward; the shipped
300-second timeout remained unchanged. The full default-duration timeout was
not waited out. `systemctl stop` can return zero while the unit Result is
`timeout`; automation must inspect the unit result/health.

## Reboot and power-cycle recovery

Changed kernel boot IDs confirmed actual reboot and cold-start events.
The enabled service automatically returned to caller-ready operation after:

- A clean systemd reboot.
- A complete systemd power-off followed by VM cold start.
- Abrupt termination of the idle VM's hypervisor process and subsequent start.

Credentials and caller HELP access survived each event. The preceding boot's
journal showed a running service without a clean stop for the abrupt-reset
case. Existing snapshots also verified afterward. No reset was induced during
an active message/database write.

## Process failure recovery

SIGKILL was applied separately to the test modem, emulator and supervisor.
Actual systemd restarted the pair automatically. Old child processes were gone,
credentials were preserved and a subsequent caller could use HELP.
These are crash-recovery checks, not proof that pending guest writes survive.

## Backup, restore and timer

The shipped backup unit stopped the guest, produced a checksum-verified snapshot
and restarted cleanly without a false unit failure. Restoration into a new
directory preserved the disk hash and credentials; restored media booted under
the real unit and accepted a caller.

An existing backup destination induced a controlled backup failure. The error
was reported, the service stayed stopped beyond RestartSec, and the last good
snapshot remained unchanged and valid. The shipped persistent calendar timer
also caught up one missed run after its test timestamp was moved into the past.
The resulting snapshot verified and the service restarted cleanly. The timer
was stopped after the test.

## Defects found and fixed

| Finding | Fix |
| --- | --- |
| A successful stopped backup caused ExecStop to contact an already-exited supervisor, producing a false unit failure and restart. | An idempotent systemd stop command accepts an absent endpoint only after the guest disk lock is free. |
| Killing the supervisor left the modem and emulator alive, blocking restart. | Linux parent-death signals terminate both children if the supervisor dies. |
| A stop timeout removed the private control directory while the caller and processes remained alive. | Preserve the runtime directory so operator control remains reachable. |

Failed control requests also now close their sockets on every exit path.
The updated Linux safety suite passed all 10 tests without resource warnings.
The guarded integration harness is `check_debian_vm.py`; it refuses to run
without the explicit disposable-VM marker and real systemd.

## Artifact identity and evidence

Updated kits and `VM-VALIDATION.json` are under `build/native-service-kit-vm/`.
Sanitized final reports, journals and initial failure evidence are under
`build/debian-vm-qualification/evidence/`. The machine-readable tracked report
is [debian-vm-2026-11-26.json](performance/debian-vm-2026-11-26.json).

The freshly installed archive and final delivery archive have different hashes
because qualification-harness and documentation refinements followed the fresh
installation. The installer, preflight, installed production helper, units and
native runtime were verified byte-identical to the delivered payload. The
final delivery manifest/preflight was also checked inside the VM. Native
binaries and common guest media were not changed by these lifecycle fixes.

## Remaining limits

Real-systemd VM coverage is ARM64 only. The x64 kit contains the same host
service fixes, but no x64 VM or native x64 hardware test is claimed. Public
network exposure, target-VPS behavior, off-host backup/retention/disaster restore,
72-hour soak and active-write power-loss consistency remain separate gates.
The full guest-program/BYE AUTH adversarial suite was not repeated in this VM.
